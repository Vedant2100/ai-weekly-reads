from __future__ import annotations

import os
from pathlib import Path


def maybe_send_to_remarkable(file_path: Path) -> str:
    device_token = os.environ.get("REMARKABLE_DEVICE_TOKEN", "").strip()
    if not device_token:
        return "reMarkable delivery skipped: REMARKABLE_DEVICE_TOKEN environment variable is not set."

    if not file_path.exists():
        return f"reMarkable delivery skipped: File {file_path} does not exist."

    try:
        from rmapy import api
        from rmapy.api import Client
        from rmapy.document import ZipDocument

        api.USER_TOKEN_URL = "https://webapp.cloud.remarkable.com/token/json/2/user/new"
        api.DEVICE_TOKEN_URL = "https://webapp.cloud.remarkable.com/token/json/2/device/new"

        client = Client()
        client.token_set["devicetoken"] = device_token
        client.renew_token()

        doc = ZipDocument(docpath=str(file_path))
        if client.upload(doc):
            return f"✅ Sent {file_path.name} to reMarkable Cloud successfully!"
        else:
            return f"Notice: reMarkable upload returned False for {file_path.name}."
    except Exception as exc:
        return f"Notice: reMarkable delivery failed: {exc}"
