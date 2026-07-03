import os
import requests
from app.publishers.base import BasePublisher

class YouTubePublisher(BasePublisher):
    def __init__(self):
        pass

    def publish_video(self, video_path: str, title: str, description: str, **kwargs) -> dict:
        """
        Streams a local MP4 file directly to YouTube Shorts using Google's resumable upload protocol.
        """
        if not os.path.exists(video_path):
            return {"status": "failed", "error": "Source file not found on local machine."}

        file_size = os.path.getsize(video_path)
        access_token = kwargs.get("access_token")

        if not access_token:
            return {"status": "failed", "error": "Missing valid Google OAuth access token."}

        print(f"[YouTube] Initializing media stream for: {video_path} ({file_size} bytes)")

        # 1. Resumable Upload Handshake URL
        init_url = "https://www.googleapis.com/upload/youtube/v3/videos?uploadType=resumable&part=snippet,status"
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json; charset=UTF-8",
            "X-Upload-Content-Length": str(file_size),
            "X-Upload-Content-Type": "video/mp4"
        }

        metadata = {
            "snippet": {
                "title": title or "Pastor Mrs. Lubega Sermon Clip",
                "description": description or "Transformational faith insights. #shorts",
                "categoryId": "22"  # People & Blogs / Church Content
            },
            "status": {
                "privacyStatus": "private"  # Drops into account privately first for staging safety
            }
        }

        try:
            init_res = requests.post(init_url, json=metadata, headers=headers)
            if init_res.status_code != 200:
                return {"status": "failed", "error": f"Google gateway rejected connection: {init_res.text}"}

            upload_url = init_res.headers.get("Location")
            if not upload_url:
                return {"status": "failed", "error": "Failed to extract dynamic upload URL locator from Google."}

            print("[YouTube] Authorization link verified. Sending binary stream payload...")

            # 2. Upload file content bytes directly
            with open(video_path, "rb") as f:
                video_data = f.read()

            upload_headers = {
                "Content-Type": "video/mp4",
                "Content-Length": str(file_size)
            }

            upload_res = requests.put(upload_url, data=video_data, headers=upload_headers)

            if upload_res.status_code in [200, 201]:
                response_data = upload_res.json()
                video_id = response_data.get("id")
                print(f"[YouTube] Delivery complete! Video ID: {video_id}")
                return {"status": "success", "platform": "youtube", "publish_id": video_id}
            else:
                return {"status": "failed", "error": f"Data stream interrupted: {upload_res.text}"}

        except Exception as e:
            print(f"[YouTube] Fatal exception encountered: {str(e)}")
            return {"status": "failed", "error": str(e)}