from __future__ import annotations

import argparse
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from config import load_settings
from digest import build_digest
from ebook import build_kindle_file
from project_paths import INBOX
from resources import write_resource
from send_to_kindle import maybe_send_to_kindle
from sources import MediaItem, read_inbox, resolve_link
from summarize import get_or_create_summary
from transcripts import get_or_create_transcript


def process_inbox_batch(inbox_path: Path = INBOX / "links.txt") -> bool:
    if not inbox_path.exists():
        print(f"No inbox file found at {inbox_path}")
        return False
    links = read_inbox(inbox_path, [])
    if not links:
        print("No new links in inbox to process.")
        return False

    settings = load_settings()
    print(f"\n========================================================")
    print(f"🚀 Starting Gemini Batch Pipeline for {len(links)} links...")
    print(f"========================================================\n")

    all_items: list[MediaItem] = []
    for link in links:
        print(f"🔗 Resolving link: {link}")
        try:
            resolved = resolve_link(link)
            all_items.extend(resolved)
        except Exception as exc:
            print(f"Notice: Could not resolve link {link}: {exc}")

    if not all_items:
        print("❌ No valid media items resolved from links.")
        return False

    resource_paths: list[Path] = []
    for item in all_items:
        print(f"\n📑 Processing: {item.title} ({item.source_type})")
        try:
            transcript_path, method = get_or_create_transcript(item, settings)
            if not transcript_path or not transcript_path.exists():
                print(f"Notice: Could not acquire transcript/content for {item.title}")
                continue
            summary_path = get_or_create_summary(item, transcript_path, settings)
            if summary_path and summary_path.exists():
                res_path = write_resource(item, summary_path, transcript_path, method)
                resource_paths.append(res_path)
                print(f"✅ Summary created: {res_path.name}")
        except Exception as exc:
            print(f"❌ Failed processing {item.title}: {exc}")

    if not resource_paths:
        print("❌ No summaries generated.")
        return False

    print(f"\n📚 Compiling Topic-Categorized Master Ebook for {len(resource_paths)} items...")
    digest_path = build_digest(
        resource_paths,
        settings,
        output_prefix="gemini-inbox-batch",
        write_public_latest=True,
        write_weekly_book=True,
    )
    print(f"📄 Markdown Digest written: {digest_path}")

    kindle_path = build_kindle_file(digest_path, settings)
    print(f"📘 Categorized Ebook File written: {kindle_path}")

    if isinstance(settings.kindle, dict) and settings.kindle.get("enabled"):
        print("📧 Sending to Kindle...")
        try:
            maybe_send_to_kindle(kindle_path, settings)
            print("✅ Sent to Kindle successfully!")
        except Exception as exc:
            print(f"Notice: Kindle delivery failed: {exc}")

    # Archive processed links
    archive_path = INBOX / "archive.txt"
    stamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    archive_entry = f"\n# Batch processed on {stamp}\n" + "\n".join(links) + "\n"
    with open(archive_path, "a", encoding="utf-8") as f:
        f.write(archive_entry)

    # Empty inbox links file while keeping comment instructions
    header = "# Add links here (one per line). Run python3 scripts/process_inbox_batch.py to process.\n"
    inbox_path.write_text(header, encoding="utf-8")
    print(f"\n🎉 Batch processing complete! Inbox archived to {archive_path.name} and cleared.")
    return True


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Process links in inbox via Gemini AI into a single categorized ebook.")
    parser.add_argument("--inbox", type=Path, default=INBOX / "links.txt", help="Path to links text file")
    args = parser.parse_args()
    success = process_inbox_batch(args.inbox)
    sys.exit(0 if success else 1)
