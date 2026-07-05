from __future__ import annotations

import os
import re
import sys
import time
from pathlib import Path

import requests
from process_inbox_batch import process_inbox_batch
from project_paths import INBOX, OUTPUT
from sources import read_inbox


def load_env():
    env_path = Path(__file__).resolve().parent.parent / ".env"
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip("'\""))


def get_token() -> str:
    load_env()
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    if not token:
        print("❌ Error: TELEGRAM_BOT_TOKEN environment variable not set.")
        print("Please create a bot with @BotFather on Telegram and set export TELEGRAM_BOT_TOKEN='your_token'")
        sys.exit(1)
    return token


def api_url(token: str, method: str) -> str:
    return f"https://api.telegram.org/bot{token}/{method}"


def send_message(token: str, chat_id: int, text: str):
    try:
        requests.post(api_url(token, "sendMessage"), json={"chat_id": chat_id, "text": text}, timeout=10)
    except Exception as exc:
        print(f"Notice: Failed to send Telegram message: {exc}")


def send_document(token: str, chat_id: int, doc_path: Path, caption: str = ""):
    try:
        with open(doc_path, "rb") as f:
            requests.post(
                api_url(token, "sendDocument"),
                data={"chat_id": chat_id, "caption": caption},
                files={"document": f},
                timeout=60,
            )
    except Exception as exc:
        print(f"Notice: Failed to send Telegram document: {exc}")


def extract_urls(text: str) -> list[str]:
    return re.findall(r"https?://[^\s]+", text)


def add_to_inbox(links: list[str]) -> int:
    inbox_path = INBOX / "links.txt"
    if not inbox_path.exists():
        inbox_path.parent.mkdir(parents=True, exist_ok=True)
        inbox_path.write_text("# Add links here (one per line). Run scripts/process_inbox_batch.py to process.\n", encoding="utf-8")
    with open(inbox_path, "a", encoding="utf-8") as f:
        for link in links:
            f.write(f"{link.strip()}\n")
    return len(read_inbox(inbox_path, []))


def run_telegram_bot():
    token = get_token()
    print("🤖 Telegram Bot started! Listening for links and commands...")
    print("Send any URL (PDF, YouTube, X tweet, article) to your bot in Telegram.")
    print("Send /ebook or /generate to compile and receive your EPUB ebook directly in chat!")
    
    offset = 0
    while True:
        try:
            resp = requests.get(api_url(token, "getUpdates"), params={"offset": offset, "timeout": 20}, timeout=30)
            if resp.status_code == 200:
                data = resp.json()
                for result in data.get("result", []):
                    offset = result["update_id"] + 1
                    message = result.get("message") or result.get("channel_post")
                    if not message or "text" not in message:
                        continue
                    
                    chat_id = message["chat"]["id"]
                    text = message["text"].strip()
                    print(f"\n📩 Received message from chat {chat_id}: {text}")

                    if text.lower() in {"/start", "/help"}:
                        help_msg = (
                            "👋 Welcome to AI Weekly Reads Bot!\n\n"
                            "📥 Drop ANY link here (arXiv PDF, YouTube video, X thread, blog article).\n"
                            "📚 Send /ebook (or /run) when you're ready to compile them all into a topic-categorized EPUB ebook!"
                        )
                        send_message(token, chat_id, help_msg)
                        continue

                    if text.lower() in {"/ebook", "/run", "/generate", "/build"}:
                        inbox_path = INBOX / "links.txt"
                        links = read_inbox(inbox_path, []) if inbox_path.exists() else []
                        if not links:
                            send_message(token, chat_id, "📭 Your reading inbox is currently empty! Send me some links first.")
                            continue
                        
                        send_message(token, chat_id, f"🚀 Generating topic-categorized AI ebook from {len(links)} link(s) using Gemini 3.1 Flash...\n⏳ Please wait ~30-60 seconds!")
                        
                        before_epubs = set(OUTPUT.glob("*.epub"))
                        try:
                            success = process_inbox_batch(inbox_path)
                            if success:
                                after_epubs = set(OUTPUT.glob("*.epub")) - before_epubs
                                if not after_epubs:
                                    all_epubs = sorted(OUTPUT.glob("*.epub"), key=lambda p: p.stat().st_mtime, reverse=True)
                                    newest_epub = all_epubs[0] if all_epubs else None
                                else:
                                    newest_epub = sorted(after_epubs, key=lambda p: p.stat().st_mtime, reverse=True)[0]
                                
                                if newest_epub and newest_epub.exists():
                                    send_message(token, chat_id, "✅ Ebook compiled successfully! Uploading your EPUB file now...")
                                    send_document(token, chat_id, newest_epub, caption=f"📘 {newest_epub.stem}\n\nTap to open in Apple Books or Kindle!")
                                else:
                                    send_message(token, chat_id, "✅ Processing finished, but could not locate the output EPUB file.")
                            else:
                                send_message(token, chat_id, "❌ Batch processing encountered an error or no valid summaries were produced.")
                        except Exception as exc:
                            send_message(token, chat_id, f"❌ Error running batch processor: {exc}")
                        continue

                    urls = extract_urls(text)
                    if urls:
                        total_count = add_to_inbox(urls)
                        msg = f"✅ Added {len(urls)} link(s) to inbox! (Total queued: {total_count})\n💡 Reply /ebook anytime to generate your EPUB ebook!"
                        send_message(token, chat_id, msg)
                    else:
                        send_message(token, chat_id, "ℹ️ Please send valid URLs (starting with http:// or https://) or send /ebook to build your ebook.")
            time.sleep(1)
        except KeyboardInterrupt:
            print("\n🛑 Telegram Bot stopped by user.")
            break
        except Exception as exc:
            print(f"Notice: Telegram polling error: {exc}")
            time.sleep(5)


if __name__ == "__main__":
    run_telegram_bot()
