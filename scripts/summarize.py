from __future__ import annotations

import os
import time
from pathlib import Path

import requests

from config import Settings
from project_paths import PROMPTS, SUMMARIES
from sources import MediaItem
from transcript_store import read_transcript_text
from utils import read_text, write_text


SUMMARY_TEMPLATE = """# {title}

Source: {source_type}
Original link: {url}

## One-Paragraph Summary

{overview}

## Main Ideas

{main_ideas}

## Questions And Answers

{qa}

## Notable Details

{details}

## Actionable Takeaways

{takeaways}

## Reading Priority

{priority}
"""

REQUIRED_SUMMARY_HEADINGS = (
    "## One-Sentence Takeaway",
    "## Short Summary",
    "## Featured Speakers",
    "## Topics",
    "## Main Ideas",
    "## Questions And Answers",
    "## Notable Details",
    "## Actionable Takeaways",
    "## People, Companies, Tools, And Links Mentioned",
    "## Reading Priority",
)


def get_or_create_summary(item: MediaItem, transcript_path: Path, settings: Settings) -> Path:
    summary_path = SUMMARIES / f"{item.id}.md"
    if summary_path.exists() and not should_refresh_summary(summary_path, settings):
        return summary_path

    if item.source_type == "pdf_document" or str(transcript_path).lower().endswith(".pdf"):
        if settings.summary_provider == "gemini" or os.environ.get("GEMINI_API_KEY"):
            from gemini_ai import summarize_pdf_gemini
            summary = summarize_pdf_gemini(item, transcript_path, settings)
        else:
            summary = _local_summary(item, "PDF document requires Gemini API key.", settings)
        write_text(summary_path, summary)
        return summary_path

    transcript = read_transcript_text(transcript_path)
    if (settings.summary_provider == "gemini" or os.environ.get("GEMINI_API_KEY")) and _has_real_transcript(transcript):
        from gemini_ai import gemini_summary
        summary = gemini_summary(item, transcript, settings)
    elif settings.summary_provider == "mistral" and os.environ.get("MISTRAL_API_KEY") and _has_real_transcript(transcript):
        summary = _mistral_summary(item, transcript, settings)
    else:
        note = None
        if not _has_real_transcript(transcript):
            note = "Source content unavailable. The raw text fetched by the scraper was empty or insufficient, so no summary could be generated."
        summary = _local_summary(item, transcript, settings, note=note)

    write_text(summary_path, summary)
    return summary_path



def summary_path_for(item: MediaItem) -> Path:
    return SUMMARIES / f"{item.id}.md"


def should_refresh_summary(summary_path: Path, settings: Settings) -> bool:
    if not summary_path.exists():
        return True
    summary = read_text(summary_path)
    has_key = bool(os.environ.get("GEMINI_API_KEY") or os.environ.get("MISTRAL_API_KEY"))
    if has_key and is_placeholder_summary(summary):
        return True
    # Detect hollow summaries where Gemini returned empty sections
    if has_key and _is_hollow_summary(summary):
        return True
    return False


def _is_hollow_summary(summary: str) -> bool:
    """Check if a summary has the right headings but no actual content in them."""
    required = ["## One-Sentence Takeaway", "## Short Summary", "## Main Ideas"]
    for heading in required:
        idx = summary.find(heading)
        if idx == -1:
            continue
        # Get text between this heading and the next heading
        after = summary[idx + len(heading):]
        next_heading = after.find("\n## ")
        section = after[:next_heading] if next_heading != -1 else after
        # Strip whitespace and check if the section is empty
        section_text = section.strip()
        if not section_text:
            return True
    return False



def _has_real_transcript(transcript: str) -> bool:
    lowered = transcript.lower().strip()
    if "transcript unavailable" in lowered or "transcription failed" in lowered or "404 client error" in lowered or "not found" in lowered:
        return False
    # If the transcript is very short, or just a link reference, it's not a real content body
    lines = [line.strip() for line in transcript.splitlines() if line.strip()]
    non_link_lines = [
        l for l in lines 
        if not l.startswith("X (Twitter) Link:") 
        and not l.startswith("Title:") 
        and not l.startswith("URL:") 
        and not l.startswith("http")
    ]
    substantive_text = " ".join(non_link_lines).strip()
    if len(substantive_text.split()) < 15:
        return False
    return True



def is_placeholder_summary(summary: str) -> bool:
    return (
        "AI summary is not enabled yet" in summary
        or "Not generated in local fallback mode" in summary
        or "Mistral summary failed" in summary
        or "Gemini summary failed" in summary
        or "AI summary failed" in summary
        or "Model configuration issue:" in summary
        or "Authentication issue:" in summary
        or "Rate limit issue:" in summary
        or "Gemini API issue:" in summary
        or "Summary Unavailable" in summary
    )


def _mistral_summary(item: MediaItem, transcript: str, settings: Settings) -> str:
    try:
        response = _post_mistral_summary(item, transcript, settings)
        response.raise_for_status()
        payload = response.json()
        content = payload["choices"][0]["message"]["content"]
        return format_ai_summary(item, content)
    except Exception as exc:
        return _local_summary(item, transcript, settings, note=f"Mistral summary failed: {exc}")


def _post_mistral_summary(item: MediaItem, transcript: str, settings: Settings) -> requests.Response:
    payload = mistral_chat_payload(item, transcript, settings)
    headers = {
        "Authorization": f"Bearer {os.environ['MISTRAL_API_KEY']}",
        "Content-Type": "application/json",
    }
    backoffs = [0, 10, 30, 60]
    response: requests.Response | None = None
    for delay in backoffs:
        if delay:
            print(f"Mistral rate limit/backoff: waiting {delay}s before retrying {item.title}")
            time.sleep(delay)
        response = requests.post(
            "https://api.mistral.ai/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=120,
        )
        if response.status_code != 429:
            return response
    assert response is not None
    return response


def mistral_chat_payload(item: MediaItem, transcript: str, settings: Settings) -> dict:
    return {
        "model": settings.summary_model,
        "temperature": 0.2,
        "messages": [
            {
                "role": "system",
                "content": "You create precise, readable Markdown knowledge-base notes from long media transcripts.",
            },
            {
                "role": "user",
                "content": _summary_prompt(item, transcript),
            },
        ],
    }


def format_ai_summary(item: MediaItem, content: str) -> str:
    content = strip_ai_response_wrappers(content)
    return f"# {item.title}\n\nSource: {item.source_type}\nOriginal link: {item.url}\n\n{content.strip()}\n"


def strip_ai_response_wrappers(content: str) -> str:
    stripped = strip_outer_markdown_fence(content).strip()
    fenced = _extract_markdown_fence(stripped)
    if fenced:
        stripped = fenced.strip()
    heading_index = _first_summary_heading_index(stripped)
    if heading_index > 0:
        prefix = stripped[:heading_index].strip().lower()
        if not prefix or "markdown" in prefix or "here is" in prefix or len(prefix.split()) <= 20:
            stripped = stripped[heading_index:]
    return stripped.strip()


def summary_quality_issue(content: str) -> str | None:
    stripped = strip_ai_response_wrappers(content)
    if len(stripped.split()) < 80:
        return "summary is unexpectedly short"
    missing = [heading for heading in REQUIRED_SUMMARY_HEADINGS if heading not in stripped]
    if missing:
        return f"missing required headings: {', '.join(missing)}"
    return None


def strip_outer_markdown_fence(content: str) -> str:
    stripped = content.strip()
    if not stripped.startswith("```"):
        return content
    lines = stripped.splitlines()
    if len(lines) >= 2 and lines[0].startswith("```") and lines[-1].strip() == "```":
        return "\n".join(lines[1:-1]).strip()
    return content


def _extract_markdown_fence(content: str) -> str | None:
    lines = content.splitlines()
    for start, line in enumerate(lines):
        marker = line.strip().lower()
        if marker not in {"```", "```markdown", "```md"}:
            continue
        for end in range(start + 1, len(lines)):
            if lines[end].strip() == "```":
                candidate = "\n".join(lines[start + 1 : end]).strip()
                if "## " in candidate:
                    return candidate
                break
    return None


def _first_summary_heading_index(content: str) -> int:
    heading_markers = [
        "## One-Sentence Takeaway",
        "## Short Summary",
        "## Main Ideas",
    ]
    indexes = [content.find(marker) for marker in heading_markers if content.find(marker) != -1]
    return min(indexes) if indexes else -1


def _summary_prompt(item: MediaItem, transcript: str) -> str:
    prompt_template = read_text(_prompt_path_for(item))
    return f"""
{prompt_template}

Title: {item.title}
URL: {item.url}
Source type: {item.source_type}
Published: {item.published or "unknown"}
Description:
{item.description or ""}

Transcript:
{transcript[:60000]}
"""


def _prompt_path_for(item: MediaItem) -> Path:
    if item.source_type in {"podcast", "youtube"}:
        return PROMPTS / "summarize_podcast.md"
    return PROMPTS / "summarize_resource.md"


def _local_summary(item: MediaItem, transcript: str, settings: Settings, note: str | None = None) -> str:
    # If the transcript was unavailable or empty, write a clean, brief notice
    # rather than a giant empty template
    if note and "unavailable" in note.lower():
        return f"""# {item.title}

Source: {item.source_type}
Original link: {item.url}

## Summary Unavailable

{note}
"""

    # If it is a real fallback (e.g. API keys are missing but transcript exists),
    # show a cleaner excerpt-based page without the placeholder text
    words = transcript.split()
    excerpt = " ".join(words[:250])
    if len(words) > 250:
        excerpt += "..."
    
    overview = note or "AI summary is not enabled. Set GEMINI_API_KEY to generate structured summaries with Google Gemini."
    
    return f"""# {item.title}

Source: {item.source_type}
Original link: {item.url}

## One-Paragraph Summary

{overview}

## Content Excerpt

{excerpt or "No text content available."}
"""

