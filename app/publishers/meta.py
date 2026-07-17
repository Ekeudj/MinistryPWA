"""
app/publishers/meta.py

Instagram and Facebook both run on Meta's Graph API, so they share one file
instead of being split like tiktok.py / youtube.py were.

Includes a helper to exchange a short-lived Graph API token (the one you
copy out of Graph API Explorer, which expires in ~1hr) for a long-lived
60-day token — you only ever need to do this exchange once manually,
after that the token lives in the database (see app/db.py) and can be
refreshed again before it expires.
"""

import os
import time
import requests
from app.publishers.base import BasePublisher

GRAPH_API_VERSION = "v19.0"
GRAPH_BASE = f"https://graph.facebook.com/{GRAPH_API_VERSION}"


def exchange_for_long_lived_token(short_lived_token: str) -> dict:
    """
    One-time helper: swaps a short-lived Graph API token for a long-lived
    (~60 day) one. Called from the /api/setup/meta endpoint in main.py.
    """
    app_id = os.getenv("META_APP_ID")
    app_secret = os.getenv("META_APP_SECRET")

    params = {
        "grant_type": "fb_exchange_token",
        "client_id": app_id,
        "client_secret": app_secret,
        "fb_exchange_token": short_lived_token,
    }
    res = requests.get(f"{GRAPH_BASE}/oauth/access_token", params=params, timeout=15)
    res.raise_for_status()
    return res.json()  # contains access_token, expires_in


class InstagramPublisher(BasePublisher):
    def __init__(self):
        self.ig_business_id = os.getenv("META_IG_BUSINESS_ID")

    def authenticate(self) -> bool:
        return True

    def publish_video(self, video_path: str, title: str, description: str, **kwargs) -> dict:
        access_token = kwargs.get("access_token")
        video_url = kwargs.get("video_url")  # Instagram needs a public URL, not a raw file

        if not access_token:
            return {"status": "failed", "error": "Missing Meta access token."}
        if not video_url:
            return {"status": "failed", "error": "Instagram requires a public video_url, not a local file path."}

        try:
            # Step 1: create a media container (Reels)
            container_res = requests.post(
                f"{GRAPH_BASE}/{self.ig_business_id}/media",
                data={
                    "media_type": "REELS",
                    "video_url": video_url,
                    "caption": description or title,
                    "access_token": access_token,
                },
                timeout=30,
            )
            container_data = container_res.json()
            if "id" not in container_data:
                return {"status": "failed", "error": f"Container creation failed: {container_data}"}

            container_id = container_data["id"]

            # Step 2: poll until the container finishes processing
            status = "IN_PROGRESS"
            for _ in range(20):  # up to ~60s of polling
                status_res = requests.get(
                    f"{GRAPH_BASE}/{container_id}",
                    params={"fields": "status_code", "access_token": access_token},
                    timeout=15,
                )
                status = status_res.json().get("status_code", "IN_PROGRESS")
                if status == "FINISHED":
                    break
                if status == "ERROR":
                    return {"status": "failed", "error": "Instagram failed to process the video container."}
                time.sleep(3)

            if status != "FINISHED":
                return {"status": "failed", "error": "Timed out waiting for Instagram to process the video."}

            # Step 3: publish the container
            publish_res = requests.post(
                f"{GRAPH_BASE}/{self.ig_business_id}/media_publish",
                data={"creation_id": container_id, "access_token": access_token},
                timeout=30,
            )
            publish_data = publish_res.json()
            if "id" not in publish_data:
                return {"status": "failed", "error": f"Publish failed: {publish_data}"}

            return {"status": "success", "platform": "instagram", "publish_id": publish_data["id"]}
        except Exception as e:
            return {"status": "failed", "error": str(e)}

    def publish_photo(self, image_path: str, caption: str, **kwargs) -> dict:
        access_token = kwargs.get("access_token")
        image_url = kwargs.get("image_url")
        if not access_token:
            return {"status": "failed", "error": "Missing Meta access token."}
        if not image_url:
            return {"status": "failed", "error": "Instagram requires a public image_url."}

        # Auto-correct aspect ratio to 1:1 (square) before sending.
        # Instagram accepts 4:5 to 1.91:1 — square (1:1) is always safe
        # and works universally for ministry content.
        try:
            from PIL import Image

            base, ext = os.path.splitext(image_path)
            corrected_path = f"{base}_ig{ext}"

            with Image.open(image_path) as img:
                w, h = img.size
                ratio = w / h
                # Only correct if outside Instagram's accepted range
                if ratio < 0.8 or ratio > 1.91:
                    size = min(w, h)
                    left = (w - size) // 2
                    top = (h - size) // 2
                    img = img.crop((left, top, left + size, top + size))
                img.save(corrected_path)

            # Swap the URL to point at the corrected file
            image_url = image_url.replace(
                os.path.basename(image_path),
                os.path.basename(corrected_path)
            )
        except Exception:
            pass  # If PIL fails, try with original and let Instagram decide

        try:
            container_res = requests.post(
                f"{GRAPH_BASE}/{self.ig_business_id}/media",
                data={
                    "image_url": image_url,
                    "caption": caption,
                    "access_token": access_token,
                },
                timeout=30,
            )
            container_data = container_res.json()
            if "id" not in container_data:
                return {"status": "failed", "error": f"Container creation failed: {container_data}"}
            publish_res = requests.post(
                f"{GRAPH_BASE}/{self.ig_business_id}/media_publish",
                data={"creation_id": container_data["id"], "access_token": access_token},
                timeout=30,
            )
            publish_data = publish_res.json()
            if "id" not in publish_data:
                return {"status": "failed", "error": f"Publish failed: {publish_data}"}
            return {"status": "success", "platform": "instagram", "publish_id": publish_data["id"]}
        except Exception as e:
            return {"status": "failed", "error": str(e)}


class FacebookPublisher(BasePublisher):
    def __init__(self):
        self.page_id = os.getenv("META_PAGE_ID")

    def authenticate(self) -> bool:
        return True

    def publish_video(self, video_path: str, title: str, description: str, **kwargs) -> dict:
        access_token = kwargs.get("access_token")
        if not access_token:
            return {"status": "failed", "error": "Missing Meta access token."}
        if not os.path.exists(video_path):
            return {"status": "failed", "error": f"Source file not found at path: {video_path}"}

        try:
            with open(video_path, "rb") as f:
                res = requests.post(
                    f"{GRAPH_BASE}/{self.page_id}/videos",
                    data={
                        "title": title,
                        "description": description,
                        "access_token": access_token,
                    },
                    files={"source": f},
                    timeout=(10, 600),
                )
            data = res.json()
            if "id" not in data:
                return {"status": "failed", "error": f"Facebook upload failed: {data}"}
            return {"status": "success", "platform": "facebook", "publish_id": data["id"]}
        except Exception as e:
            return {"status": "failed", "error": str(e)}

    def publish_photo(self, image_path: str, caption: str, **kwargs) -> dict:
        access_token = kwargs.get("access_token")
        if not access_token:
            return {"status": "failed", "error": "Missing Meta access token."}
        if not os.path.exists(image_path):
            return {"status": "failed", "error": f"Image file not found: {image_path}"}
        try:
            with open(image_path, "rb") as f:
                res = requests.post(
                    f"{GRAPH_BASE}/{self.page_id}/photos",
                    data={
                        "caption": caption,
                        "access_token": access_token,
                    },
                    files={"source": f},
                    timeout=(10, 120),
                )
            data = res.json()
            if "id" not in data:
                return {"status": "failed", "error": f"Facebook photo upload failed: {data}"}
            return {"status": "success", "platform": "facebook", "publish_id": data["id"]}
        except Exception as e:
            return {"status": "failed", "error": str(e)}