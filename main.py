from app.config import settings
from fastapi import FastAPI, UploadFile, File, HTTPException, Query, Request, BackgroundTasks  
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, RedirectResponse, JSONResponse
from app.video_engine import generate_sermon_video
import os
import httpx
import asyncio
from dotenv import load_dotenv
from app.publishers.tiktok import TikTokPublisher
from app.publishers.youtube import YouTubePublisher

load_dotenv()

app = FastAPI(
    title="HerGlory Content Engine API",
    version="1.0.0",
    description="Scalable automation backend for cross-posting ministry content."
)

# Shared RAM token state
TIKTOK_TOKENS = {"access_token": None, "refresh_token": None}
YOUTUBE_TOKENS = {"access_token": None, "refresh_token": None}

app.mount("/static", StaticFiles(directory="frontend"), name="frontend_assets")

@app.get("/")
async def serve_frontend():
    frontend_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "frontend", "index.html")
    if os.path.exists(frontend_path):
        return FileResponse(frontend_path)
    return JSONResponse(status_code=500, content={"status": "error", "message": "Could not find frontend/index.html file locally."})

# ===================================================
# TIKTOK PIPELINE MODULE
# ===================================================

@app.get("/api/auth/tiktok")
async def tiktok_login():
    client_key = os.getenv("TIKTOK_CLIENT_KEY")
    redirect_uri = "https://herglory-backend.onrender.com/api/callback/tiktok"
    scope = "user.info.basic,video.upload"
    
    auth_url = (
        f"https://www.tiktok.com/v2/auth/authorize/"
        f"?client_key={client_key}"
        f"&scope={scope}"
        f"&response_type=code"
        f"&redirect_uri={redirect_uri}"
    )
    return RedirectResponse(url=auth_url)

@app.get("/api/callback/tiktok")
async def tiktok_callback(code: str = Query(None), error: str = Query(None)):
    if error:
        raise HTTPException(status_code=400, detail=f"TikTok Auth Error: {error}")
    if not code:
        raise HTTPException(status_code=400, detail="Missing authorization token.")

    client_key = os.getenv("TIKTOK_CLIENT_KEY")
    client_secret = os.getenv("TIKTOK_CLIENT_SECRET")
    redirect_uri = "https://herglory-backend.onrender.com/api/callback/tiktok"

    token_url = "https://open.tiktokapis.com/v2/oauth/token/"
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    data = {
        "client_key": client_key,
        "client_secret": client_secret,
        "code": code,
        "grant_type": "authorization_code",
        "redirect_uri": redirect_uri
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(token_url, headers=headers, data=data)
        token_data = response.json()

    if "error" in token_data or "access_token" not in token_data:
        return RedirectResponse(url="https://herglory-backend.onrender.com/?tiktok_connected=false")

    TIKTOK_TOKENS["access_token"] = token_data["access_token"]
    TIKTOK_TOKENS["refresh_token"] = token_data.get("refresh_token")
    return RedirectResponse(url="https://herglory-backend.onrender.com/?tiktok_connected=true")

@app.get("/api/auth/status/tiktok")
async def get_tiktok_status():
    return JSONResponse(content={"connected": TIKTOK_TOKENS["access_token"] is not None})

@app.post("/api/test-publish/tiktok")
async def test_tiktok_publish(request: Request):
    token = TIKTOK_TOKENS.get("access_token")
    if not token:
        return JSONResponse(status_code=400, content={"status": "failed", "error": "No active TikTok token found."})
        
    # BUG FIX 5: Extract the actual uploaded video file path dynamically instead of hardcoding test.mp4
    try:
        body = await request.json()
        video_target = body.get("video_file", "test.mp4")
    except Exception:
        video_target = "test.mp4"

    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    video_file_path = os.path.join(BASE_DIR, "uploads", video_target)

    if not os.path.exists(video_file_path):
        if os.path.exists(os.path.join(BASE_DIR, video_target)):
            video_file_path = os.path.join(BASE_DIR, video_target)
        else:
            return JSONResponse(status_code=404, content={"status": "failed", "error": f"Media target file '{video_target}' not found on server."})

    publisher = TikTokPublisher()
    result = publisher.publish_video(
        video_path=video_file_path,
        title="Ministry Live Sermon Clip",
        description="Automated cross-posting platform delivery.",
        access_token=token
    )
    
    if result.get("status") == "success":
        return JSONResponse(content={"status": "success", "publish_id": result.get("publish_id")})
    return JSONResponse(status_code=500, content=result)


# ===================================================
# YOUTUBE PIPELINE MODULE
# ===================================================

@app.get("/api/auth/youtube")
def youtube_auth_login():
    redirect_uri = "https://herglory-backend.onrender.com/api/callback/youtube"
    client_id = os.getenv("YOUTUBE_CLIENT_KEY")
    
    google_oauth_url = (
        f"https://accounts.google.com/o/oauth2/v2/auth?"
        f"client_id={client_id}&"
        f"redirect_uri={redirect_uri}&"
        f"response_type=code&"
        f"scope=https://www.googleapis.com/auth/youtube.upload&"
        f"access_type=offline&prompt=consent"
    )
    return RedirectResponse(url=google_oauth_url)

@app.get("/api/auth/status/youtube")
async def get_youtube_status():
    return JSONResponse(content={"connected": YOUTUBE_TOKENS["access_token"] is not None})

@app.get("/api/callback/youtube")
async def youtube_oauth_callback(code: str = Query(None)):
    if not code:
        return RedirectResponse(url="https://herglory-backend.onrender.com/?youtube_connected=false")

    redirect_uri = "https://herglory-backend.onrender.com/api/callback/youtube"
    token_url = "https://oauth2.googleapis.com/token"
    
    payload = {
        "code": code,
        "client_id": os.getenv("YOUTUBE_CLIENT_KEY"),
        "client_secret": os.getenv("YOUTUBE_CLIENT_SECRET"),
        "redirect_uri": redirect_uri,
        "grant_type": "authorization_code"
    }

    try:
        async with httpx.AsyncClient() as client:
            token_res = await client.post(token_url, data=payload, timeout=15.0)
            
        if token_res.status_code == 200:
            tokens = token_res.json()
            YOUTUBE_TOKENS["access_token"] = tokens.get("access_token")
            YOUTUBE_TOKENS["refresh_token"] = tokens.get("refresh_token")
            # BUG FIX 1: Use standard clear response instead of keeping the PWA locked in an auth loop state
            return RedirectResponse(url="https://herglory-backend.onrender.com/?youtube_connected=true")
    except Exception as e:
        print(f"[YouTube Callback Exception]: {str(e)}")

    return RedirectResponse(url="https://herglory-backend.onrender.com/?youtube_connected=false")


# BUG FIX 2: Run blocking requests executor in a separate operational worker thread
def run_youtube_upload(video_path: str, access_token: str):
    try:
        publisher = YouTubePublisher()
        publisher.publish_video(
            video_path=video_path,
            title="Pastor Mrs. Lubega Live Sermon Clip",
            description="Powerful spiritual insight for today. #shorts #faith",
            access_token=access_token
        )
    except Exception as e:
        print(f"[YouTube Worker Thread Crash]: {str(e)}")


@app.post("/api/test-publish/youtube")
async def production_publish_youtube(request: Request, background_tasks: BackgroundTasks):
    access_token = YOUTUBE_TOKENS.get("access_token")
    if not access_token:
        return JSONResponse(status_code=400, content={"status": "failed", "error": "User channel is not authenticated."})

    try:
        body = await request.json()
        video_file_path = body.get("video_file", "test.mp4")
    except Exception:
        video_file_path = "test.mp4"

    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    alternative_path = os.path.join(BASE_DIR, "uploads", video_file_path)
    
    if os.path.exists(alternative_path):
        video_file_path = alternative_path
    elif os.path.exists(os.path.join(BASE_DIR, "uploads", f"{os.path.splitext(video_file_path)[0]}_render.mp4")):
        # BUG FIX 3: Route audio fallbacks correctly if the frontend passes the base audio reference title
        video_file_path = os.path.join(BASE_DIR, "uploads", f"{os.path.splitext(video_file_path)[0]}_render.mp4")
    elif not os.path.exists(video_file_path):
        return JSONResponse(status_code=404, content={"status": "failed", "error": f"Missing operational source file content: '{video_file_path}'"})

    # Offload execution safely to background threads
    background_tasks.add_task(run_youtube_upload, video_file_path, access_token)
    return JSONResponse(status_code=202, content={"status": "processing", "message": "Video upload dispatched to system background workers successfully!"})

# ===================================================
# SYSTEM UTILITIES
# ===================================================

@app.get("/sw.js")
async def serve_service_worker():
    return FileResponse("frontend/sw.js", media_type="application/javascript")

@app.post("/api/upload-audio")
async def upload_sermon_audio(file: UploadFile = File(...)):
    try:
        BASE_DIR = os.path.dirname(os.path.abspath(__file__))
        upload_path = os.path.join(BASE_DIR, "uploads", file.filename)
        os.makedirs(os.path.dirname(upload_path), exist_ok=True)
        
        with open(upload_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)
            
        filename_without_ext = os.path.splitext(file.filename)[0]
        output_video_name = f"{filename_without_ext}_render.mp4"
        
        # BUG FIX 7: generate_sermon_video() runs ffmpeg/moviepy under the hood, which
        # is slow and CPU-heavy. Calling it directly here blocked the whole async
        # event loop until rendering finished — and while blocked, the devtunnel
        # proxy would time the connection out, which is what threw the
        # "Network processing failed" error in the browser.
        # Same fix already applied to the YouTube publish flow (see run_youtube_upload) —
        # just offload the blocking call to a worker thread with asyncio.to_thread.
        await asyncio.to_thread(
            generate_sermon_video,
            audio_path=upload_path,
            output_filename=output_video_name
        )
        
        return JSONResponse(content={
            "status": "success",
            "video_file": output_video_name
        })
    except Exception as e:
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})

@app.post("/api/upload-video")
async def upload_sermon_video(file: UploadFile = File(...)):
    try:
        BASE_DIR = os.path.dirname(os.path.abspath(__file__))
        upload_path = os.path.join(BASE_DIR, "uploads", file.filename)
        os.makedirs(os.path.dirname(upload_path), exist_ok=True)
        
        with open(upload_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)
            
        return JSONResponse(content={"status": "success", "video_file": file.filename})
    except Exception as e:
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=False)