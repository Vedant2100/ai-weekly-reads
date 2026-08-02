import sys
import json
import re
from datetime import datetime, timezone
from pathlib import Path

# Paths
ROOT = Path(__file__).resolve().parent.parent
INBOX = ROOT / "inbox"
LINKS_PATH = INBOX / "links.txt"
CAPTURE_LOG_PATH = INBOX / "link_capture.jsonl"

def extract_urls(text: str) -> list[str]:
    # Extract any URLs from the message text
    pattern = r'(https?://[^\s]+)'
    return [url.rstrip(".,!?;:)]}") for url in re.findall(pattern, text)]

def extract_urls_from_message(message: dict) -> list[str]:
    urls = []
    # Text and Caption fields
    combined_text = (message.get("text") or "") + " " + (message.get("caption") or "")
    if combined_text.strip():
        urls.extend(extract_urls(combined_text))

    # Formatted Hyperlink Entities
    entities = (message.get("entities") or []) + (message.get("caption_entities") or [])
    for entity in entities:
        if isinstance(entity, dict) and entity.get("type") == "text_link" and entity.get("url"):
            urls.append(entity["url"])

    return list(dict.fromkeys(urls))

def main():
    if len(sys.argv) < 2:
        print("Usage: python handle_webhook.py <payload.json>")
        sys.exit(1)

    payload_path = Path(sys.argv[1])
    if not payload_path.exists():
        print(f"Error: {payload_path} does not exist.")
        sys.exit(1)

    try:
        update = json.loads(payload_path.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"Failed to parse payload: {e}")
        sys.exit(1)

    message = (
        update.get("message")
        or update.get("channel_post")
        or update.get("edited_message")
        or update.get("edited_channel_post")
    )
    
    if not message:
        print("No message found in payload.")
        sys.exit(0)

    # Security Check: Only allow messages from the authorized user
    AUTHORIZED_USER_ID = 8370406344
    sender_id = message.get("from", {}).get("id")
    if sender_id != AUTHORIZED_USER_ID:
        print(f"SECURITY ALERT: Unauthorized access attempt from Telegram User ID: {sender_id}. Ignoring message.")
        sys.exit(0)

    # Extract links
    urls = extract_urls_from_message(message)
    
    if urls:
        if not INBOX.exists():
            INBOX.mkdir(parents=True, exist_ok=True)
            
        current_links = []
        if LINKS_PATH.exists():
            current_links = [line.strip() for line in LINKS_PATH.read_text(encoding="utf-8").splitlines() if line.strip()]
        
        # Filter duplicates
        seen = set(current_links)
        added_links = []
        for link in urls:
            if link not in seen:
                seen.add(link)
                added_links.append(link)
        
        if added_links:
            with open(LINKS_PATH, "a", encoding="utf-8") as f:
                for link in added_links:
                    f.write(f"{link}\n")
            captured_at = datetime.now(timezone.utc).isoformat()
            with open(CAPTURE_LOG_PATH, "a", encoding="utf-8") as f:
                for link in added_links:
                    f.write(json.dumps({
                        "url": link,
                        "captured_at": captured_at,
                        "telegram_update_id": update.get("update_id"),
                        "telegram_message_id": message.get("message_id"),
                    }, ensure_ascii=False) + "\n")
            print(f"Added {len(added_links)} new links to links.txt.")
        else:
            print("No new unique links found.")
    else:
        print("No URLs found in the message.")

    print("Queued for the next three-day research digest; Telegram no longer triggers immediate ebook generation.")

if __name__ == "__main__":
    main()
