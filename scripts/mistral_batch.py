from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from pathlib import Path

from config import Settings
from project_paths import SUMMARIES
from sources import MediaItem
from summarize import format_ai_summary, mistral_chat_payload, summary_quality_issue
from transcript_store import read_transcript_text
from utils import write_text


@dataclass(frozen=True)
class SummaryBatchItem:
    item: MediaItem
    transcript_path: Path


def summarize_with_mistral_batch(
    batch_items: list[SummaryBatchItem],
    settings: Settings,
    *,
    model: str | None = None,
    poll_seconds: int = 20,
    timeout_seconds: int = 60 * 60,
) -> dict[str, Path]:
    if not batch_items:
        return {}
    if not os.environ.get("MISTRAL_API_KEY"):
        raise RuntimeError("MISTRAL_API_KEY is required for Mistral batch summarization.")

    try:
        from mistralai.client import Mistral
    except ImportError as exc:
        raise RuntimeError("Install the Mistral SDK with `pip install mistralai`.") from exc

    client = Mistral(api_key=os.environ["MISTRAL_API_KEY"])
    batch_model = model or settings.summary_model
    requests = [_batch_request(batch_item, settings) for batch_item in batch_items]
    return _run_batch_job(client, batch_items, requests, batch_model, poll_seconds, timeout_seconds)


def _run_batch_job(
    client,
    batch_items: list[SummaryBatchItem],
    requests: list[dict],
    model: str,
    poll_seconds: int,
    timeout_seconds: int,
) -> dict[str, Path]:
    job = client.batch.jobs.create(
        endpoint="/v1/chat/completions",
        model=model,
        requests=requests,
        metadata={"project": "ai-weekly-reads", "job_type": "resource-summary"},
    )
    job_id = _get_attr(job, "id")
    if not job_id:
        raise RuntimeError(f"Mistral batch job was created without an id: {job!r}")

    print(f"Mistral batch job submitted: {job_id} using {model} ({len(batch_items)} summaries)")
    try:
        job = _wait_for_batch(client, job_id, poll_seconds, timeout_seconds)
        status = str(_get_attr(job, "status", "")).upper()
        if status not in {"SUCCESS", "SUCCEEDED", "COMPLETED"}:
            raise RuntimeError(f"Mistral batch job {job_id} finished with status {status}: {job!r}")

        output_file = _get_attr(job, "output_file")
        if not output_file:
            raise RuntimeError(f"Mistral batch job {job_id} did not return an output file.")

        response = client.files.download(file_id=output_file)
        results = _parse_jsonl_response(response)
        item_by_id = {batch_item.item.id: batch_item.item for batch_item in batch_items}
        content_by_id: dict[str, str] = {}
        for row in results:
            custom_id = str(row.get("custom_id", ""))
            item = item_by_id.get(custom_id)
            if not item:
                continue
            content = _extract_content(row)
            if not content:
                raise RuntimeError(f"Mistral batch result for {custom_id} did not include summary text: {row!r}")
            issue = summary_quality_issue(content)
            if issue:
                raise RuntimeError(f"Mistral batch result for {custom_id} was not usable: {issue}")
            content_by_id[item.id] = content

        missing = sorted(set(item_by_id) - set(content_by_id))
        if missing:
            raise RuntimeError(f"Mistral batch output was missing summaries for: {', '.join(missing)}")

        summary_paths: dict[str, Path] = {}
        for item_id, content in content_by_id.items():
            item = item_by_id[item_id]
            summary_path = SUMMARIES / f"{item.id}.md"
            write_text(summary_path, format_ai_summary(item, content))
            summary_paths[item.id] = summary_path
        return summary_paths
    except Exception:
        _cancel_batch_job(client, job_id, model)
        raise


def _batch_request(batch_item: SummaryBatchItem, settings: Settings) -> dict:
    transcript = read_transcript_text(batch_item.transcript_path)
    payload = mistral_chat_payload(batch_item.item, transcript, settings)
    payload.pop("model", None)
    return {
        "custom_id": batch_item.item.id,
        "body": payload,
    }


def _wait_for_batch(client, job_id: str, poll_seconds: int, timeout_seconds: int):
    deadline = time.monotonic() + timeout_seconds
    poll_failures = 0
    while True:
        try:
            job = client.batch.jobs.get(job_id=job_id)
        except Exception as exc:
            # A transient network error must not abandon a batch job that is
            # still running (and billing) server-side.
            poll_failures += 1
            if poll_failures >= 3 or time.monotonic() >= deadline:
                raise
            print(f"Mistral batch poll failed ({exc}); retrying in {poll_seconds}s")
            time.sleep(poll_seconds)
            continue
        poll_failures = 0
        status = str(_get_attr(job, "status", "")).upper()
        print(f"Mistral batch job {job_id}: {status}")
        if status in {"SUCCESS", "SUCCEEDED", "COMPLETED", "FAILED", "CANCELLED", "CANCELED", "TIMEOUT_EXCEEDED"}:
            return job
        if time.monotonic() >= deadline:
            raise TimeoutError(f"Mistral batch job {job_id} did not finish within {timeout_seconds}s")
        time.sleep(poll_seconds)


def _cancel_batch_job(client, job_id: str, model: str) -> None:
    try:
        client.batch.jobs.cancel(job_id=job_id)
        print(f"Mistral batch job cancelled: {job_id} ({model})")
    except Exception as exc:
        print(f"Mistral batch job cancellation skipped for {job_id} ({model}): {exc}")


def _parse_jsonl_response(response) -> list[dict]:
    if hasattr(response, "read"):
        content = response.read()
    elif hasattr(response, "content"):
        content = response.content
    else:
        content = response
    text = content.decode("utf-8") if isinstance(content, bytes) else str(content)
    rows = []
    for line in text.splitlines():
        line = line.strip()
        if line:
            rows.append(json.loads(line))
    return rows


def _extract_content(row: dict) -> str:
    body = (row.get("response") or {}).get("body") or row.get("body") or row
    choices = body.get("choices") or []
    if not choices:
        return ""
    message = choices[0].get("message", {})
    return message.get("content", "")


def _get_attr(obj, name: str, default=None):
    if isinstance(obj, dict):
        return obj.get(name, default)
    return getattr(obj, name, default)
