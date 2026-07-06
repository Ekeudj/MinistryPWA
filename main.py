from app.config import settings
from fastapi import FastAPI, UploadFile, File, HTTPException, Query, Request, BackgroundTasks  
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, RedirectResponse, JSONResponse
from app.video_engine import generate_sermon_video
import os
import httpx
from dotenv import load_dotenv
from app.publishers.tiktok import TikTokPublisher
from app.publishers.youtube import YouTubePublisher
import requests

load_dotenv()

app = FastAPI(
    title="HerGlory Content Engine API",
    version="1.0.0",
    description="Scalable automation backend for cross-posting ministry content."
)

TIKTOK_TOKENS = {
    "access_token": None,
    "refresh_token": None
}

YOUTUBE_TOKENS = {
    "access_token": None,
    "refresh_token": None
}

app.mount("/static", StaticFiles(directory="frontend"), name="frontend_assets")

@app.get("/")
async def serve_frontend():
    try:
        return FileResponse("frontend/index.html")
    except Exception as e:
        return JSONResponse(status_code=500, content={"status": "error", "message": f"Could not find frontend files: {str(e)}"})

# =═════════════════════════════════════════════════
# 3. TIKTOK PIPELINE MODULE
# =═════════════════════════════════════════════════

@app.get("/api/auth/tiktok")
async def tiktok_login():
    client_key = os.getenv("TIKTOK_CLIENT_KEY")
    redirect_uri = "https://kx871t4g-8000.inc1.devtunnels.ms/api/callback/tiktok"
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
async def tiktok_callback(
    code: str = Query(None), 
    error: str = Query(None),
    state: str = Query(None)
):
    if error:
        raise HTTPException(status_code=400, detail=f"TikTok Auth Error: {error}")
    if not code:
        raise HTTPException(status_code=400, detail="Missing required authorization verification token.")

    client_key = os.getenv("TIKTOK_CLIENT_KEY")
    client_secret = os.getenv("TIKTOK_CLIENT_SECRET")
    redirect_uri = "https://kx871t4g-8000.inc1.devtunnels.ms/api/callback/tiktok"

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
        err_msg = token_data.get("error_description", "Failed to retrieve access token")
        return RedirectResponse(url="https://kx871t4g-8000.inc1.devtunnels.ms/?tiktok_connected=false")

    TIKTOK_TOKENS["access_token"] = token_data["access_token"]
    TIKTOK_TOKENS["refresh_token"] = token_data.get("refresh_token")
    
    return RedirectResponse(url="https://kx871t4g-8000.inc1.devtunnels.ms/?tiktok_connected=true")

@app.get("/api/auth/status/tiktok")
async def get_tiktok_status():
    is_connected = TIKTOK_TOKENS["access_token"] is not None
    return JSONResponse(content={"connected": is_connected})

@app.post("/api/test-publish/tiktok")
async def test_tiktok_publish():
    token = TIKTOK_TOKENS.get("access_token")
    if not token:
        return JSONResponse(status_code=400, content={"status": "failed", "error": "No active TikTok token found."})
        
    video_target = "test.mp4" 
    if not os.path.exists(video_target):
        return JSONResponse(status_code=404, content={"status": "failed", "error": f"Please drop a test video file named '{video_target}' in root."})

    publisher = TikTokPublisher()
    result = publisher.publish_video(
        video_path=video_target,
        title="Testing HerGlory Content Engine integration! #Ministry",
        description="Automated cross-posting platform deployment verification run.",
        access_token=token
    )
    
    if result.get("status") == "success":
        return JSONResponse(content={
            "status": "success",
            "message": "Video successfully pushed to TikTok chunk queue!",
            "publish_id": result.get("publish_id")
        })
    else:
        return JSONResponse(status_code=500, content=result)


# =═════════════════════════════════════════════════
# 4. YOUTUBE PIPELINE MODULE
# =═════════════════════════════════════════════════

@app.get("/api/auth/youtube")
def youtube_auth_login():
    redirect_uri = "https://kx871t4g-8000.inc1.devtunnels.ms/api/callback/youtube"
    client_id = os.getenv("YOUTUBE_CLIENT_KEY")
    
    google_oauth_url = (
        f"https://accounts.google.com/o/oauth2/v2/auth?"
        f"client_id={client_id}&"
        f"redirect_uri={redirect_uri}&"
        f"response_type=code&"
        f"scope=https://www.googleapis.com/auth/youtube.upload&"
        f"access_type=offline&prompt=select_account"
    )
    return RedirectResponse(url=google_oauth_url, status_code=307)

@app.get("/api/auth/status/youtube")
async def get_youtube_status():
    is_connected = YOUTUBE_TOKENS["access_token"] is not None
    return JSONResponse(content={"connected": is_connected})

@app.get("/api/callback/youtube")
async def youtube_oauth_callback(code: str = Query(None)):
    if not code:
        print("[YouTube] Authorization code missing from callback parameters.")
        return RedirectResponse(url="https://kx871t4g-8000.inc1.devtunnels.ms/?youtube_connected=false", status_code=307)

    redirect_uri = "https://kx871t4g-8000.inc1.devtunnels.ms/api/callback/youtube"
    token_url = "https://oauth2.googleapis.com/token"
    
    payload = {
        "code": code,
        "client_id": os.getenv("YOUTUBE_CLIENT_KEY"),
        "client_secret": os.getenv("YOUTUBE_CLIENT_SECRET"),
        "redirect_uri": redirect_uri,
        "grant_type": "authorization_code"
    }

    try:
        # Use httpx to prevent network thread deadlocks over tunnels
        async with httpx.AsyncClient() as client:
            token_res = await client.post(token_url, data=payload, timeout=15.0)
            
        if token_res.status_code == 200:
            tokens = token_res.json()
            YOUTUBE_TOKENS["access_token"] = tokens.get("access_token")
            YOUTUBE_TOKENS["refresh_token"] = tokens.get("refresh_token")
            print("[YouTube] OAuth Token exchanges completed successfully.")
            return RedirectResponse(url="https://kx871t4g-8000.inc1.devtunnels.ms/?youtube_connected=true", status_code=307)
        else:
            print(f"[YouTube] Token gate rejected request: {token_res.text}")
    except Exception as e:
        print(f"[YouTube] Callback exception caught: {str(e)}")

    return RedirectResponse(url="https://kx871t4g-8000.inc1.devtunnels.ms/?youtube_connected=false", status_code=307)


# Helper function to process the upload in the background
def run_youtube_upload(video_path: str, access_token: str):
    try:
        print(f"[YouTube Background Task] Heavy upload started for: {video_path}")
        publisher = YouTubePublisher()
        result = publisher.publish_video(
            video_path=video_path,
            title="Pastor Mrs. Lubega Live Sermon Clip",
            description="Powerful spiritual insight for today. #shorts #faith",
            access_token=access_token
        )
        print(f"[YouTube Background Task] Execution completed: {result}")
    except Exception as e:
        print(f"[YouTube Background Task] Processing crashed: {str(e)}")


@app.post("/api/test-publish/youtube")
async def production_publish_youtube(request: Request, background_tasks: BackgroundTasks):
    access_token = YOUTUBE_TOKENS.get("access_token")
    
    if not access_token:
        return JSONResponse(status_code=400, content={"status": "failed", "error": "User channel is not authenticated. Please run OAuth loop first."})

    try:
        body = await request.json()
        video_file_path = body.get("video_file", "test.mp4")
    except Exception:
        video_file_path = "test.mp4"

    if not os.path.exists(video_file_path):
        BASE_DIR = os.path.dirname(os.path.abspath(__file__))
        alternative_path = os.path.join(BASE_DIR, "uploads", video_file_path)
        if os.path.exists(alternative_path):
            video_file_path = alternative_path
        else:
            return JSONResponse(status_code=404, content={"status": "failed", "error": f"Missing operational source file content: '{video_file_path}'"})

    #  THE FIX: Hand the processing over to the background worker pool
    background_tasks.add_task(run_youtube_upload, video_file_path, access_token)
    
    # Return a 202 Accepted status instantly to beat the 60s devtunnel gateway timeout
    return JSONResponse(status_code=202, content={
        "status": "processing", 
        "message": "Video upload dispatched to system background workers successfully!"
    })
    access_token = YOUTUBE_TOKENS.get("access_token")
    
    if not access_token:
        return JSONResponse(status_code=400, content={"status": "failed", "error": "User channel is not authenticated. Please run OAuth loop first."})

    try:
        body = await request.json()
        video_file_path = body.get("video_file", "test.mp4")
    except Exception:
        video_file_path = "test.mp4"

    if not os.path.exists(video_file_path):
        BASE_DIR = os.path.dirname(os.path.abspath(__file__))
        alternative_path = os.path.join(BASE_DIR, "uploads", video_file_path)
        if os.path.exists(alternative_path):
            video_file_path = alternative_path
        else:
            return JSONResponse(status_code=404, content={"status": "failed", "error": f"Missing operational source file content: '{video_file_path}'"})

    print(f"[YouTube] Direct publishing engine triggered for: {video_file_path}")
    
    publisher = YouTubePublisher()
    result = publisher.publish_video(
        video_path=video_file_path,
        title="Pastor Mrs. Lubega Live Sermon Clip",
        description="Powerful spiritual insight for today. #shorts #faith",
        access_token=access_token
    )
    
    status_code = 200 if result.get("status") == "success" else 500
    return JSONResponse(status_code=status_code, content=result)
# =═════════════════════════════════════════════════
# 5. CORE SYSTEM UTILITIES & UTILS
# =═════════════════════════════════════════════════

@app.get("/sw.js")
async def serve_service_worker():
    try:
        return FileResponse("frontend/sw.js", media_type="application/javascript")
    except Exception as e:
        return JSONResponse(status_code=404, content={"status": "error", "message": f"Could not find sw.js: {str(e)}"})
    
@app.get("/favicon.ico")
async def serve_favicon():
    try:
        return FileResponse("frontend/assets/logo.webp")
    except Exception:
        from fastapi.responses import Response
        return Response(status_code=204)

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
        
        rendered_video_path = generate_sermon_video(
            audio_path=upload_path, 
            output_filename=output_video_name
        )
        
        return JSONResponse(content={
            "status": "success",
            "message": "Audio successfully converted to video clip!",
            "video_file": output_video_name,
            "full_path": rendered_video_path
        })
    except Exception as e:
        return JSONResponse(status_code=500, content={"status": "error", "message": f"Server processing failed: {str(e)}"})

@app.get("/api/health")
async def health_check():
    return JSONResponse(content={
        "status": "online",
        "loaded_modules": ["Config Engine", "Static Frontend Assets Router", "TikTok Handshake Vector", "YouTube Handshake Vector"]
    })

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)