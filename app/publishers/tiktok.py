import os
import requests
from app.publishers.base import BasePublisher
from app.config import settings

class TikTokPublisher(BasePublisher):
    def __init__(self):
        self.client_key = settings.TIKTOK_CLIENT_KEY
        self.client_secret = settings.TIKTOK_CLIENT_SECRET

    def authenticate(self) -> bool:
        # Placeholder: This will check your access token validity from the database/Redis later
        return True

    def publish_video(self, video_path: str, title: str, description: str, **kwargs) -> dict:
        """
        Uploads an MP4 file to TikTok cleanly chunk-by-chunk using FILE_UPLOAD mode.
        Requires zero external cloud hosting.
        """
        # 1. Gather file specifications from the filesystem
        file_size = os.path.getsize(video_path)
        
        # --- DYNAMIC CHUNK SIZE CALCULATION ---
        # TikTok requires chunks to be between 5MB (5242880 bytes) and 64MB.
        MIN_CHUNK_SIZE = 5 * 1024 * 1024  
        DEFAULT_CHUNK_SIZE = 10 * 1024 * 1024  # 10MB default for large files

        if file_size <= DEFAULT_CHUNK_SIZE:
            # If the video is under 10MB, it MUST be uploaded as a single chunk 
            # where the declared chunk_size matches the exact file size.
            chunk_size = file_size
            total_chunk_count = 1
        else:
            chunk_size = DEFAULT_CHUNK_SIZE
            total_chunk_count = (file_size + chunk_size - 1) // chunk_size
            
            # Safety Check: If the very last remaining chunk is going to be less than 5MB, 
            # TikTok will reject it. We handle that by absorbing it into a slightly larger layout.
            remaining_bytes = file_size % chunk_size
            if remaining_bytes > 0 and remaining_bytes < MIN_CHUNK_SIZE:
                # Merge the final tiny remainder into the chunking calculation dynamically
                total_chunk_count = file_size // chunk_size
        # --------------------------------------
        
        # Retrieve the user token (passed down from your database/auth routing layer)
        access_token = kwargs.get("access_token", "MOCK_TOKEN")

        print(f"[TikTok] Initializing direct upload for local file: {video_path} ({file_size} bytes)")
        print(f"[TikTok] Calculated configurations: chunk_size={chunk_size}, total_chunks={total_chunk_count}")

        # 2. Initialize the Upload Link with TikTok
        init_url = "https://open.tiktokapis.com/v2/post/publish/inbox/video/init/"
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json; charset=UTF-8"
        }
        
        # Inform TikTok we are delivering raw binary chunks directly
        init_data = {
            "post_info": {
                "title": title,
                "privacy_level": "MUTUAL_FOLLOW_FRIENDS", # Sandbox default visibility fallback
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
            
            # Extract TikTok's temporary upload endpoint allocation
            upload_url = init_json["data"]["upload_url"]
            publish_id = init_json["data"]["publish_id"]
            
            print(f"[TikTok] Handshake verified. Chunking data into {total_chunk_count} segments...")

            # 3. Stream Chunks to TikTok via PUT requests
            with open(video_path, "rb") as f:
                for chunk_index in range(total_chunk_count):
                    # For the last chunk, we read whatever remaining bytes are left in the file stream
                    if chunk_index == total_chunk_count - 1:
                        chunk_data = f.read()  # Read until EOF
                    else:
                        chunk_data = f.read(chunk_size)
                        
                    bytes_read = len(chunk_data)
                    
                    # Compute chunk byte alignment for HTTP headers
                    start_byte = chunk_index * chunk_size
                    end_byte = start_byte + bytes_read - 1
                    
                    chunk_headers = {
                        "Content-Type": "video/mp4",
                        "Content-Length": str(bytes_read),
                        "Content-Range": f"bytes {start_byte}-{end_byte}/{file_size}"
                    }
                    
                    print(f"[TikTok] Uploading chunk {chunk_index + 1}/{total_chunk_count} ({start_byte}-{end_byte})")
                    
                    # Transfer chunk block to TikTok's bucket location
                    upload_res = requests.put(upload_url, data=chunk_data, headers=chunk_headers)
                    
                    if upload_res.status_code not in [200, 201, 308]:
                        return {"status": "failed", "error": f"Chunk {chunk_index + 1} upload failed with status {upload_res.status_code}."}

            print(f"[TikTok] Processing complete. Action ID: {publish_id}")
            return {"status": "success", "platform": "tiktok", "publish_id": publish_id}

        except Exception as e:
            print(f"[TikTok] Error during transfer pipeline: {str(e)}")
            return {"status": "failed", "error": str(e)}