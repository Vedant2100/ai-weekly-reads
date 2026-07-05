from __future__ import annotations

import os
import time
from pathlib import Path

from config import Settings
from sources import MediaItem
from utils import read_text


def _load_env():
    env_path = Path(__file__).resolve().parent.parent / ".env"
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip("'\""))


def _get_genai_client():
    _load_env()
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY environment variable is required for Gemini summarization/transcription.")
    try:
        from google import genai
    except ImportError as exc:
        raise RuntimeError("Install the Google GenAI SDK with `pip install google-genai`.") from exc
    return genai.Client(api_key=api_key)


def can_use_gemini() -> bool:
    _load_env()
    return bool(os.environ.get("GEMINI_API_KEY"))


def gemini_summary(item: MediaItem, transcript: str, settings: Settings) -> str:
    from summarize import _local_summary, _summary_prompt, format_ai_summary

    try:
        client = _get_genai_client()
        prompt = _summary_prompt(item, transcript)
        model = settings.summary_model if settings.summary_provider == "gemini" else "gemini-2.5-flash"
        
        backoffs = [0, 10, 30, 60]
        response = None
        for delay in backoffs:
            if delay:
                print(f"Gemini rate limit/backoff: waiting {delay}s before retrying {item.title}")
                time.sleep(delay)
            try:
                response = client.models.generate_content(
                    model=model,
                    contents=[
                        "You create precise, readable Markdown knowledge-base notes from long media transcripts or articles.",
                        prompt,
                    ],
                    config={"temperature": 0.2},
                )
                if response and response.text:
                    break
            except Exception as exc:
                if _should_retry(exc):
                    continue
                raise
        if not response or not response.text:
            raise RuntimeError("Gemini returned empty response.")
        return format_ai_summary(item, response.text)
    except Exception as exc:
        return _local_summary(item, transcript, settings, note=f"Gemini summary failed: {exc}")


def summarize_pdf_gemini(item: MediaItem, pdf_path: Path, settings: Settings) -> str:
    from summarize import _local_summary, _summary_prompt, format_ai_summary

    if not pdf_path.exists():
        return _local_summary(item, "PDF file missing.", settings, note="PDF file not found for summarization.")
    try:
        client = _get_genai_client()
        print(f"Uploading PDF to Gemini File API: {pdf_path.name}")
        uploaded_file = client.files.upload(file=pdf_path)
        try:
            model = settings.summary_model if settings.summary_provider == "gemini" else "gemini-2.5-flash"
            prompt = _summary_prompt(item, f"[Full PDF Document: {pdf_path.name}]")
            
            backoffs = [0, 10, 30, 60]
            response = None
            for delay in backoffs:
                if delay:
                    print(f"Gemini backoff: waiting {delay}s before retrying {item.title}")
                    time.sleep(delay)
                try:
                    response = client.models.generate_content(
                        model=model,
                        contents=[
                            "You create precise, readable Markdown knowledge-base notes from research papers, reports, or PDF documents.",
                            uploaded_file,
                            prompt,
                        ],
                        config={"temperature": 0.2},
                    )
                    if response and response.text:
                        break
                except Exception as exc:
                    if _should_retry(exc):
                        continue
                    raise
            if not response or not response.text:
                raise RuntimeError("Gemini returned empty response for PDF.")
            return format_ai_summary(item, response.text)
        finally:
            try:
                client.files.delete(name=uploaded_file.name)
            except Exception as exc:
                print(f"Notice: Failed to delete temporary uploaded PDF from Gemini: {exc}")
    except Exception as exc:
        return _local_summary(item, f"PDF upload/summarization failed: {exc}", settings, note=f"Gemini PDF summary failed: {exc}")


def transcribe_media_file_gemini(media_path: Path | None, settings: Settings) -> str | None:
    if not media_path or not media_path.exists() or not can_use_gemini():
        return None
    try:
        client = _get_genai_client()
        print(f"Uploading audio/video file to Gemini for transcription: {media_path.name}")
        uploaded_file = client.files.upload(file=media_path)
        try:
            model = settings.transcription_model if settings.transcription_provider == "gemini" else "gemini-2.5-flash"
            backoffs = [0, 15, 45, 90]
            for delay in backoffs:
                if delay:
                    print(f"Gemini transcription backoff: waiting {delay}s")
                    time.sleep(delay)
                try:
                    response = client.models.generate_content(
                        model=model,
                        contents=[
                            uploaded_file,
                            "Please generate a verbatim, complete, and accurate text transcript of the speech in this audio/video recording. Do not summarize or skip sections. Write out the exact spoken words.",
                        ],
                        config={"temperature": 0.1},
                    )
                    if response and response.text:
                        return response.text.strip()
                except Exception as exc:
                    if _should_retry(exc):
                        continue
                    print(f"Gemini transcription failed for {media_path.name}: {exc}")
                    return None
            print(f"Gemini transcription rate-limited for {media_path.name} after retries")
            return None
        finally:
            try:
                client.files.delete(name=uploaded_file.name)
            except Exception as exc:
                print(f"Notice: Failed to delete temporary uploaded media from Gemini: {exc}")
    except Exception as exc:
        print(f"Gemini media transcription failed: {exc}")
        return None


def transcribe_audio_url_gemini(audio_url: str, settings: Settings) -> str | None:
    if not can_use_gemini():
        return None
    from transcription.media import download_direct_media
    import tempfile

    with tempfile.TemporaryDirectory() as tmp_dir:
        media_path = download_direct_media(audio_url, Path(tmp_dir) / "temp_audio")
        if media_path and media_path.exists():
            return transcribe_media_file_gemini(media_path, settings)
    return None


def _should_retry(exc: Exception) -> bool:
    message = str(exc).lower()
    return "429" in message or "rate limit" in message or "exhausted" in message or "quota" in message
