import os
import requests
from app.publishers.base import BasePublisher
from app.config import settings

class TikTokPublisher(BasePublisher):
    def __init__(self):
        self.client_key = settings.TIKTOK_CLIENT_KEY
        self.client_secret = settings.TIKTOK_CLIENT_SECRET

    def authenticate(self) -> bool:
        return True

    def publish_video(self, video_path: str, title: str, description: str, **kwargs) -> dict:
        file_size = os.path.getsize(video_path)
        MIN_CHUNK_SIZE = 5 * 1024 * 1024  
        DEFAULT_CHUNK_SIZE = 10 * 1024 * 1024

        if file_size <= DEFAULT_CHUNK_SIZE:
            chunk_size = file_size
            total_chunk_count = 1
        else:
            chunk_size = DEFAULT_CHUNK_SIZE
            total_chunk_count = (file_size + chunk_size - 1) // chunk_size
            remaining_bytes = file_size % chunk_size
            if remaining_bytes > 0 and remaining_bytes < MIN_CHUNK_SIZE:
                total_chunk_count = file_size // chunk_size
        
        access_token = kwargs.get("access_token", "MOCK_TOKEN")

        init_url = "https://open.tiktokapis.com/v2/post/publish/inbox/video/init/"
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json; charset=UTF-8"
        }
        
        init_data = {
            "post_info": {
                "title": title,
                "privacy_level": "PUBLIC_TO_EVERYONE",
                "disable_comment": False,
                "disable_duet": False,
                "disable_stitch": False
            },
            "source_info": {
                "source": "FILE_UPLOAD",
                "video_size": file_size,
                "chunk_size": chunk_size,
                "total_chunk_count": total_chunk_count
            }
        }

        try:
            init_res = requests.post(init_url, json=init_data, headers=headers)
            init_json = init_res.json()
            
            if init_json.get("error", {}).get("code") != "ok":
                return {"status": "failed", "error": init_json.get("error", {}).get("message")}
            
            upload_url = init_json["data"]["upload_url"]
            publish_id = init_json["data"]["publish_id"]

            with open(video_path, "rb") as f:
                for chunk_index in range(total_chunk_count):
                    if chunk_index == total_chunk_count - 1:
                        chunk_data = f.read()
                    else:
                        chunk_data = f.read(chunk_size)
                        
                    bytes_read = len(chunk_data)
                    start_byte = chunk_index * chunk_size
                    end_byte = start_byte + bytes_read - 1
                    
                    chunk_headers = {
                        "Content-Type": "video/mp4",
                        "Content-Length": str(bytes_read),
                        "Content-Range": f"bytes {start_byte}-{end_byte}/{file_size}"
                    }
                    
                    upload_res = requests.put(upload_url, data=chunk_data, headers=chunk_headers)
                    if upload_res.status_code not in [200, 201, 308]:
                        return {"status": "failed", "error": f"Chunk upload failed code {upload_res.status_code}"}

            return {"status": "success", "platform": "tiktok", "publish_id": publish_id}
        except Exception as e:
            return {"status": "failed", "error": str(e)}