from __future__ import annotations

import base64
import json
import mimetypes
import os
import requests
from pathlib import Path


def maybe_send_to_remarkable(file_path: Path) -> str:
    device_token = os.environ.get("REMARKABLE_DEVICE_TOKEN", "").strip()
    if not device_token:
        return "reMarkable delivery skipped: REMARKABLE_DEVICE_TOKEN environment variable is not set."

    if not file_path.exists():
        return f"reMarkable delivery skipped: File {file_path} does not exist."

    try:
        # Step 1: Exchange Device Token for User Token
        user_auth_url = "https://webapp.cloud.remarkable.com/token/json/2/user/new"
        user_resp = requests.post(
            user_auth_url,
            headers={"Authorization": f"Bearer {device_token}"},
            timeout=15,
        )
        user_resp.raise_for_status()
        user_token = user_resp.text.strip()

        # Step 2: Upload File to reMarkable Cloud via WebLibrary API (/doc/v2/files)
        upload_url = "https://internal.cloud.remarkable.com/doc/v2/files"
        meta = json.dumps({"parent": "", "file_name": file_path.name})
        meta_b64 = base64.b64encode(meta.encode("utf-8")).decode("utf-8")

        content_type = mimetypes.guess_type(file_path.name)[0] or "application/epub+zip"

        headers = {
            "Authorization": f"Bearer {user_token}",
            "rm-source": "WebLibrary",
            "rm-meta": meta_b64,
            "Content-Type": content_type,
        }

        resp = requests.post(upload_url, headers=headers, data=file_path.read_bytes(), timeout=60)
        resp.raise_for_status()
        result = resp.json()
        doc_id = result.get("docID", "unknown")
        return f"✅ Successfully uploaded {file_path.name} (DocID: {doc_id}) to reMarkable Cloud!"
    except Exception as exc:
        return f"Notice: reMarkable delivery failed: {exc}"
