from __future__ import annotations

import os
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

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

    # Silently stage, commit, and push to GitHub
    import subprocess
    try:
        subprocess.run(["git", "add", str(inbox_path)], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        subprocess.run(["git", "commit", "-m", "🤖 Add link(s) via Telegram bot"], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        subprocess.run(["git", "push"], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        print(f"🚀 Silently synced {len(links)} link(s) to GitHub repository.")
    except Exception as exc:
        print(f"Notice: Automated git push failed: {exc}")

    return len(read_inbox(inbox_path, []))


def run_telegram_bot():
    token = get_token()
    print("🤖 Telegram Bot started! Listening silently for links and channel posts...")
    
    offset = 0
    while True:
        try:
            resp = requests.get(api_url(token, "getUpdates"), params={"offset": offset, "timeout": 20}, timeout=30)
            if resp.status_code == 200:
                data = resp.json()
                for result in data.get("result", []):
                    offset = result["update_id"] + 1
                    message = (
                        result.get("message")
                        or result.get("channel_post")
                        or result.get("edited_message")
                        or result.get("edited_channel_post")
                    )
                    if not message or "text" not in message:
                        continue
                    
                    chat_id = message["chat"]["id"]
                    text = message["text"].strip()
                    print(f"\n📩 Ingesting update from chat {chat_id}...")

                    urls = extract_urls(text)
                    if urls:
                        add_to_inbox(urls)
            time.sleep(1)
        except KeyboardInterrupt:
            print("\n🛑 Telegram Bot stopped by user.")
            break
        except Exception as exc:
            print(f"Notice: Telegram polling error: {exc}")
            time.sleep(5)


if __name__ == "__main__":
    run_telegram_bot()
