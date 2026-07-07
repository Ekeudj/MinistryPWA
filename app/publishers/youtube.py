import os
import requests
from app.publishers.base import BasePublisher

class YouTubePublisher(BasePublisher):
    def __init__(self):
        pass

    # BUG FIX 8: BasePublisher requires every publisher to implement authenticate()
    # (TikTokPublisher already does this — see tiktok.py). YouTubePublisher was
    # missing it entirely, so Python couldn't even instantiate the class and the
    # background worker thread crashed with "Can't instantiate abstract class".
    # We already have the access_token by the time publish_video() runs (it's
    # fetched via the OAuth flow in main.py), so this just confirms that.
    def authenticate(self) -> bool:
        return True

    def publish_video(self, video_path: str, title: str, description: str, **kwargs) -> dict:
        if not os.path.exists(video_path):
            return {"status": "failed", "error": f"Source file not found at path: {video_path}"}

        file_size = os.path.getsize(video_path)
        access_token = kwargs.get("access_token")

        if not access_token:
            return {"status": "failed", "error": "Missing valid Google OAuth access token."}

        # Step 1: Initialize Resumable Upload Session
        init_url = "https://www.googleapis.com/upload/youtube/v3/videos?uploadType=resumable&part=snippet,status"
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json; charset=UTF-8",
            "X-Upload-Content-Length": str(file_size),
            "X-Upload-Content-Type": "video/mp4"
        }

        metadata = {
            "snippet": {
                "title": title or "Ministry Sermon Clip",
                "description": description or "Transformational faith insights. #shorts",
                "categoryId": "22"
            },
            "status": {
                "privacyStatus": "public" # BUG FIX 6: Change layout status to public for production visibility transparency
            }
        }

        try:
            init_res = requests.post(init_url, json=metadata, headers=headers, timeout=(10, 30))
            if init_res.status_code != 200:
                return {"status": "failed", "error": f"Google connection refused: {init_res.text}"}

            upload_url = init_res.headers.get("Location")
            if not upload_url:
                return {"status": "failed", "error": "Dynamic session storage tracking header missing."}

            # Step 2: Stream Data Payload
            with open(video_path, "rb") as f:
                video_data = f.read()

            upload_headers = {
                "Content-Type": "video/mp4",
                "Content-Length": str(file_size)
            }

            upload_res = requests.put(upload_url, data=video_data, headers=upload_headers, timeout=(10, 600))

            if upload_res.status_code in [200, 201]:
                response_data = upload_res.json()
                return {"status": "success", "platform": "youtube", "publish_id": response_data.get("id")}
            return {"status": "failed", "error": f"Data transfer disconnected: {upload_res.text}"}
        except Exception as e:
            return {"status": "failed", "error": str(e)}