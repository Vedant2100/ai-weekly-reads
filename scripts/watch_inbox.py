from __future__ import annotations

import time
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from process_inbox_batch import process_inbox_batch
from project_paths import INBOX
from sources import read_inbox


def watch_inbox(inbox_path: Path = INBOX / "links.txt", poll_interval: int = 10):
    print(f"👀 Watching {inbox_path} for new links (polling every {poll_interval}s)...")
    print("Drop any link (PDF, X thread, YouTube, article) into the file to generate your ebook!")
    print("Press Ctrl+C to stop.")

    while True:
        try:
            if inbox_path.exists():
                links = read_inbox(inbox_path, [])
                if links:
                    print(f"\n⚡ Detected {len(links)} new link(s) in inbox! Waiting 5s for any additional pastes...")
                    time.sleep(5)
                    # Re-read to include anything pasted during debounce
                    links = read_inbox(inbox_path, [])
                    if links:
                        try:
                            process_inbox_batch(inbox_path)
                        except Exception as exc:
                            print(f"❌ Error running batch processor: {exc}")
            time.sleep(poll_interval)
        except KeyboardInterrupt:
            print("\n🛑 Watcher stopped by user.")
            break
        except Exception as exc:
            print(f"Notice: Watcher error: {exc}")
            time.sleep(poll_interval)


if __name__ == "__main__":
    watch_inbox()
