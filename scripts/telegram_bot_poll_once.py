from __future__ import annotations

import os
import re
import requests
from pathlib import Path

# Paths
ROOT = Path(__file__).resolve().parent.parent
INBOX = ROOT / "inbox"
LINKS_PATH = INBOX / "links.txt"
OFFSET_PATH = INBOX / "telegram_offset.txt"

def extract_urls(text: str) -> list[str]:
    # Extract any URLs from the message text
    pattern = r'(https?://[^\s]+)'
    return re.findall(pattern, text)

def run_once():
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    if not token:
        print("Error: TELEGRAM_BOT_TOKEN environment variable not set.")
        return

    # Load offset
    offset = 0
    if OFFSET_PATH.exists():
        try:
            offset = int(OFFSET_PATH.read_text().strip())
        except Exception as e:
            print(f"Warning: Failed to read offset file: {e}")
            pass

    print(f"Polling Telegram updates with offset: {offset}...")
    url = f"https://api.telegram.org/bot{token}/getUpdates"
    try:
        resp = requests.get(url, params={"offset": offset, "timeout": 10}, timeout=15)
        if resp.status_code != 200:
            print(f"Error fetching updates: {resp.status_code} - {resp.text}")
            return
        
        data = resp.json()
        new_links = []
        new_offset = offset
        for result in data.get("result", []):
            new_offset = result["update_id"] + 1
            message = (
                result.get("message")
                or result.get("channel_post")
                or result.get("edited_message")
                or result.get("edited_channel_post")
            )
            if not message or "text" not in message:
                continue
            
            text = message["text"].strip()
            urls = extract_urls(text)
            if urls:
                new_links.extend(urls)
        
        # Write new offset
        if new_offset != offset:
            if not INBOX.exists():
                INBOX.mkdir(parents=True, exist_ok=True)
            OFFSET_PATH.write_text(str(new_offset))
            print(f"Updated offset to {new_offset}")

        # Write links
        if new_links:
            if not INBOX.exists():
                INBOX.mkdir(parents=True, exist_ok=True)
            current_links = []
            if LINKS_PATH.exists():
                current_links = [line.strip() for line in LINKS_PATH.read_text(encoding="utf-8").splitlines() if line.strip()]
            
            # Filter duplicates
            seen = set(current_links)
            added_links = []
            for link in new_links:
                if link not in seen:
                    seen.add(link)
                    added_links.append(link)
            
            if added_links:
                with open(LINKS_PATH, "a", encoding="utf-8") as f:
                    for link in added_links:
                        f.write(f"{link}\n")
                print(f"Added {len(added_links)} new links to links.txt.")
            else:
                print("No new unique links found.")
        else:
            print("No links found in updates.")

    except Exception as e:
        print(f"Error during Telegram update retrieval: {e}")

if __name__ == "__main__":
    run_once()
