from __future__ import annotations

import argparse
import json
import os
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import requests

from config import load_settings
from project_paths import INBOX, RESOURCES, ROOT, ensure_dirs
from research_delivery import (
    append_link_rows,
    classify_link,
    deliver_research_digest_via_apps_script,
    send_research_email,
)
from resources import write_resource
from sources import MediaItem, read_inbox, resolve_link
from summarize import (
    get_or_create_summary,
    is_placeholder_summary,
    strip_ai_response_wrappers,
    summary_quality_issue,
)
from transcript_store import find_raw_transcript, write_raw_transcript
from transcripts import get_or_create_transcript
from utils import load_dotenv, read_text, split_frontmatter, write_json, write_text


STATE_PATH = INBOX / "research_state.json"
CAPTURE_LOG_PATH = INBOX / "link_capture.jsonl"
ARCHIVE_PATH = INBOX / "archive.txt"
INTERVAL_DAYS = 1


def run_research_digest(*, force: bool = False) -> bool:
    ensure_dirs()
    load_dotenv(ROOT / ".env")
    settings = load_settings()
    state = _read_state()
    if not _uses_apps_script(settings):
        _retry_pending_sheet_rows(state, settings)
    links = read_inbox(INBOX / "links.txt", [])
    if not links:
        print("No queued research links.")
        return False

    now = datetime.now(timezone.utc)
    if not force and not _is_due(state, now):
        next_at = state.get("next_digest_at") or "the next three-day interval"
        print(f"Research digest not due yet; next run is {next_at}.")
        return False

    print(f"Building research reorientation for {len(links)} queued links.")
    records = _capture_records()
    processed_at = now.isoformat()
    items: list[dict[str, Any]] = []
    sheet_rows: list[dict[str, Any]] = []

    for link in links:
        resolved_items = _resolve_safely(link)
        if not resolved_items:
            resolved_items = [_unresolved_item(link)]
        for item in resolved_items:
            result = _process_item(item, settings)
            result["captured_at"] = records.get(link, {}).get("captured_at", processed_at)
            result["processed_at"] = processed_at
            result["link"] = link
            items.append(result)
            sheet_rows.append({
                "captured_at": result["captured_at"],
                "processed_at": processed_at,
                "type": classify_link(item.source_type, item.url),
                "title": item.title,
                "url": item.url,
                "source": item.source_name or item.source_type,
                "published": item.published or "",
                "transcript_method": result["transcript_method"],
                "summary_status": result["summary_status"],
                "digest_date": now.date().isoformat(),
            })

    previous = state.get("recent_items", [])
    reorientation = _generate_reorientation(items, previous, settings)
    email_body = _compose_email(items, reorientation, now)

    prefix = str(settings.email.get("subject_prefix") or "AI Research Reorientation")
    subject = f"{prefix} — {now.date().isoformat()} ({len(items)} links)"
    try:
        if _uses_apps_script(settings):
            rows_to_append = list(state.get("pending_sheet_rows", [])) + sheet_rows
            email_status = deliver_research_digest_via_apps_script(subject, email_body, rows_to_append, settings)
            sheet_status = "Google Sheets rows appended by Apps Script."
            pending_sheet_rows: list[dict[str, Any]] = []
        else:
            pending_sheet_rows = []
            rows_to_append = list(state.get("pending_sheet_rows", [])) + sheet_rows
            try:
                sheet_status = append_link_rows(rows_to_append, settings, state)
            except Exception as exc:
                pending_sheet_rows = rows_to_append
                print(f"Google Sheets update failed: {exc}")
                print("Keeping the inbox queued; no email will be sent until the Sheet is updated.")
                return False
            email_status = send_research_email(subject, email_body, settings)
    except Exception as exc:
        print(f"Research email failed: {exc}")
        return False
    if not email_status.startswith("Sent "):
        print(email_status)
        return False

    _archive_links(links, now)
    state.update({
        "last_digest_at": processed_at,
        "next_digest_at": (now + timedelta(days=INTERVAL_DAYS)).isoformat(),
        "last_digest_subject": subject,
        "last_item_count": len(items),
        "last_sheet_status": sheet_status,
        "pending_sheet_rows": pending_sheet_rows,
        "recent_items": _state_items(previous, items),
    })
    write_json(STATE_PATH, state)
    print(email_status)
    print(sheet_status)
    print(f"Archived {len(links)} Telegram links and cleared the queue.")
    return True


def _uses_apps_script(settings) -> bool:
    return str(settings.email.get("delivery_method") or "").strip().lower() in {"apps_script", "google_apps_script"}


def _retry_pending_sheet_rows(state: dict[str, Any], settings) -> None:
    pending = state.get("pending_sheet_rows", [])
    if not pending or not settings.google_sheets.get("enabled"):
        return
    try:
        status = append_link_rows(pending, settings, state)
    except Exception as exc:
        print(f"Pending Google Sheets rows still unavailable: {exc}")
        return
    state["pending_sheet_rows"] = []
    state["last_sheet_status"] = status
    write_json(STATE_PATH, state)
    print(status)


def _process_item(item: MediaItem, settings) -> dict[str, Any]:
    print(f"Processing {item.title} ({item.source_type})")
    transcript_path, method = get_or_create_transcript(item, settings)
    if not transcript_path or not transcript_path.exists():
        fallback = f"Title: {item.title}\nURL: {item.url}\n\nThe source text could not be extracted.\n\n{item.description or ''}"
        transcript_path = write_raw_transcript(item, fallback, find_raw_transcript(item.id))
        method = "unavailable"

    summary_path = get_or_create_summary(item, transcript_path, settings)
    summary = read_text(summary_path)
    summary_status = "needs_summary" if is_placeholder_summary(summary) else "summarized"
    if summary_status == "needs_summary":
        print(f"Summary unavailable for {item.title}; keeping an honest source note.")
    else:
        issue = summary_quality_issue(summary)
        if issue:
            summary_status = f"quality_warning: {issue}"
    resource_path = write_resource(item, summary_path, transcript_path, method)
    return {
        "item": item,
        "summary": summary,
        "summary_status": summary_status,
        "transcript_method": method,
        "resource_path": str(resource_path),
    }


def _generate_reorientation(items: list[dict[str, Any]], previous: list[dict[str, Any]], settings) -> str:
    current_context = "\n\n".join(_item_context(item) for item in items)
    recent_context = "\n".join(
        f"- {entry.get('title', 'Untitled')}: {entry.get('takeaway', '')}"
        for entry in previous[-40:]
    ) or "No earlier digest context is available."
    knowledge_base_context = _knowledge_base_context(items)
    prior_context = f"Recent digest context:\n{recent_context}\n\nAccumulated Obsidian research context:\n{knowledge_base_context}"
    prompt_template = read_text(ROOT / "prompts" / "research_reorientation.md")
    prompt = f"""{prompt_template}

Previous and accumulated research context:
{prior_context[:36000]}

Current source notes:
{current_context[:60000]}
"""

    if settings.summary_provider == "gemini" and os.environ.get("GEMINI_API_KEY"):
        try:
            from gemini_ai import _get_genai_client

            client = _get_genai_client()
            models = _unique([settings.summary_model, settings.summary_fallback_model, "gemini-2.5-flash"])
            for model in models:
                for delay in (0, 5, 15):
                    if delay:
                        time.sleep(delay)
                    try:
                        response = client.models.generate_content(
                            model=model,
                            contents=[
                                "You are a careful research editor. Use only the supplied notes.",
                                prompt,
                            ],
                            config={"temperature": 0.15},
                        )
                        if response and response.text and _reorientation_is_usable(response.text):
                            return response.text.strip()
                        break
                    except Exception as exc:
                        if _should_retry(exc):
                            continue
                        break
        except Exception as exc:
            print(f"Research reorientation model unavailable: {exc}")

    if settings.summary_provider == "mistral" and os.environ.get("MISTRAL_API_KEY"):
        try:
            payload = {
                "model": settings.summary_model,
                "temperature": 0.15,
                "messages": [
                    {"role": "system", "content": "You are a careful research editor. Use only supplied notes."},
                    {"role": "user", "content": prompt},
                ],
            }
            response = requests.post(
                "https://api.mistral.ai/v1/chat/completions",
                headers={"Authorization": f"Bearer {os.environ['MISTRAL_API_KEY']}", "Content-Type": "application/json"},
                json=payload,
                timeout=180,
            )
            response.raise_for_status()
            text = response.json()["choices"][0]["message"]["content"]
            if _reorientation_is_usable(text):
                return text.strip()
        except Exception as exc:
            print(f"Research reorientation model unavailable: {exc}")

    return _fallback_reorientation(items, previous)


def _knowledge_base_context(items: list[dict[str, Any]], limit: int = 24000) -> str:
    """Build historical context from durable Obsidian notes without sending raw transcripts."""
    if not RESOURCES.exists():
        return "No accumulated Obsidian resource notes are available yet."
    current_ids = {record["item"].id for record in items}
    candidates: list[tuple[float, str]] = []
    for path in RESOURCES.glob("*.md"):
        try:
            fields, body = split_frontmatter(read_text(path))
        except OSError:
            continue
        if str(fields.get("id") or "") in current_ids:
            continue
        title = str(fields.get("title") or path.stem)
        note = _email_summary(body)
        if not note:
            continue
        candidates.append((path.stat().st_mtime, f"Title: {title}\n{note[:2200]}"))
    if not candidates:
        return "No earlier Obsidian resource notes are available yet."
    candidates.sort(reverse=True)
    selected: list[str] = []
    used = 0
    for _mtime, note in candidates:
        if used + len(note) > limit and selected:
            break
        selected.append(note)
        used += len(note)
    return "\n\n---\n\n".join(selected)


def _compose_email(items: list[dict[str, Any]], reorientation: str, now: datetime) -> str:
    lines = [
        "# AI Research Reorientation",
        "",
        f"Digest date: {now.date().isoformat()}",
        f"Links processed: {len(items)}",
        "",
        reorientation.strip(),
        "",
        "## Link Notes",
        "",
    ]
    for index, record in enumerate(items, start=1):
        item: MediaItem = record["item"]
        lines.extend([
            f"### {index}. {item.title}",
            "",
            f"Type: {classify_link(item.source_type, item.url)}",
            f"Source link: [{item.url}]({item.url})",
            *([] if not getattr(item, "image_url", None) else [f"![Thumbnail]({item.image_url})"]),
            f"Summary status: {record['summary_status']}",
            "",
            _email_summary(record["summary"]),
            "",
        ])
    return "\n".join(lines).strip() + "\n"


def _email_summary(summary: str) -> str:
    body = strip_ai_response_wrappers(summary).strip()
    lines = body.splitlines()
    first_section = next((index for index, line in enumerate(lines) if line.startswith("## ")), len(lines))
    return "\n".join(lines[first_section:]).strip()


def _item_context(record: dict[str, Any]) -> str:
    item: MediaItem = record["item"]
    summary = _email_summary(record["summary"])
    return f"Title: {item.title}\nType: {classify_link(item.source_type, item.url)}\nURL: {item.url}\nNotes:\n{summary[:9000]}"


def _fallback_reorientation(items: list[dict[str, Any]], previous: list[dict[str, Any]]) -> str:
    prior_titles = ", ".join(entry.get("title", "") for entry in previous[-5:] if entry.get("title"))
    current_titles = ", ".join(record["item"].title for record in items[:8])
    return f"""## Batch Reorientation

### What Was Already True

The available prior digest context includes {prior_titles or 'no earlier processed items'}, so this run cannot establish a stronger historical baseline without model-generated synthesis.

### What This Batch Adds

This batch adds the sources {current_titles or 'listed below'}. The individual notes distinguish each source's stated contribution from background; claims that could not be verified from extracted source text are marked accordingly.

### How The Links Fit Together

The links are presented by source and type below. No cross-source connection is asserted without enough evidence in the notes.

### Open Questions And Signals

Check the caveats and "What To Watch" subsections in each note before treating a claim as established.
"""


def _reorientation_is_usable(text: str) -> bool:
    required = [
        "## Batch Reorientation",
        "### What Was Already True",
        "### What This Batch Adds",
        "### How The Links Fit Together",
        "### Open Questions And Signals",
    ]
    return len(text.split()) >= 100 and all(marker in text for marker in required)


def _state_items(previous: list[dict[str, Any]], items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    current = [
        {
            "title": record["item"].title,
            "url": record["item"].url,
            "type": classify_link(record["item"].source_type, record["item"].url),
            "takeaway": _takeaway(record["summary"]),
        }
        for record in items
    ]
    return (previous + current)[-100:]


def _takeaway(summary: str) -> str:
    marker = "## One-Sentence Takeaway"
    if marker not in summary:
        return ""
    value = summary.split(marker, 1)[1].split("\n## ", 1)[0].strip()
    return " ".join(value.split())[:500]


def _archive_links(links: list[str], now: datetime) -> None:
    stamp = now.astimezone().strftime("%Y-%m-%d %H:%M:%S %Z")
    with ARCHIVE_PATH.open("a", encoding="utf-8") as handle:
        handle.write(f"\n# Research digest sent on {stamp}\n")
        handle.write("\n".join(links) + "\n")
    write_text(INBOX / "links.txt", "# Telegram research links waiting for the next digest.\n")


def _read_state() -> dict[str, Any]:
    if not STATE_PATH.exists():
        return {}
    try:
        value = json.loads(STATE_PATH.read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else {}
    except json.JSONDecodeError:
        return {}


def _is_due(state: dict[str, Any], now: datetime) -> bool:
    raw = state.get("next_digest_at")
    if not raw:
        return True
    try:
        return now >= datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
    except ValueError:
        return True


def _capture_records() -> dict[str, dict[str, Any]]:
    records: dict[str, dict[str, Any]] = {}
    if not CAPTURE_LOG_PATH.exists():
        return records
    for line in CAPTURE_LOG_PATH.read_text(encoding="utf-8").splitlines():
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        url = str(row.get("url") or "")
        if url:
            records.setdefault(url, row)
    return records


def _resolve_safely(link: str) -> list[MediaItem]:
    try:
        return resolve_link(link)
    except Exception as exc:
        print(f"Could not resolve {link}: {exc}")
        return []


def _unresolved_item(link: str) -> MediaItem:
    return MediaItem(
        id=link.encode("utf-8").hex()[:16],
        url=link,
        source_type="link",
        title=link,
        origin=link,
        description="The link could not be resolved before this digest.",
    )


def _unique(values: list[str]) -> list[str]:
    result: list[str] = []
    for value in values:
        if value and value not in result:
            result.append(value)
    return result


def _should_retry(exc: Exception) -> bool:
    message = str(exc).lower()
    return any(marker in message for marker in ("429", "rate limit", "quota", "exhausted"))


def main() -> None:
    parser = argparse.ArgumentParser(description="Send the queued Telegram research links as a three-day email digest.")
    parser.add_argument("--force", action="store_true", help="Send now even if the three-day interval has not elapsed.")
    args = parser.parse_args()
    raise SystemExit(0 if run_research_digest(force=args.force) else 1)


if __name__ == "__main__":
    main()
