from app.config import settings
from fastapi import FastAPI, UploadFile, File, HTTPException, Query   
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, RedirectResponse, JSONResponse
from app.video_engine import generate_sermon_video
import os
import httpx
from dotenv import load_dotenv
from app.publishers.tiktok import TikTokPublisher

load_dotenv()  # Load environment variables from .env file

app = FastAPI(
    title="HerGlory Content Engine API",
    version="1.0.0",
    description="Scalable automation backend for cross-posting ministry content."
)

# Global in-memory token store for tracking active upload authorizations
TIKTOK_TOKENS = {
    "access_token": None,
    "refresh_token": None
}

# 1. FRONTEND MOUNT
# Mounts the 'frontend' directory to serve application scripts and style assets
app.mount("/static", StaticFiles(directory="frontend"), name="frontend_assets")

# 2. CORE ROOT ROUTER
@app.get("/")
async def serve_frontend():
    """Serves the core Single Page Application UI from the frontend folder."""
    try:
        return FileResponse("frontend/index.html")
    except Exception as e:
        return {
            "status": "error",
            "message": f"Could not find frontend files: {str(e)}"
        }

# 3. TIKTOK OAUTH LOGIN ROUTE
@app.get("/api/auth/tiktok")
async def tiktok_login():
    """Redirects the browser to TikTok's secure OAuth consent screen."""
    client_key = os.getenv("TIKTOK_CLIENT_KEY")
    # Using your secure local dev routing domain for redirect routing
    redirect_uri ="https://kx871t4g-8000.inc1.devtunnels.ms/api/callback/tiktok"
    
    scope = "user.info.basic,video.upload"
    
    auth_url = (
        f"https://www.tiktok.com/v2/auth/authorize/"
        f"?client_key={client_key}"
        f"&scope={scope}"
        f"&response_type=code"
        f"&redirect_uri={redirect_uri}"
    )
    return RedirectResponse(url=auth_url)

# 4. UPDATED TIKTOK CALLBACK ROUTE (Matches your Developer Portal precisely)
@app.get("/api/callback/tiktok")
async def tiktok_callback(
    code: str = Query(None), 
    error: str = Query(None),
    state: str = Query(None)
):
    """Handles the redirect back from TikTok and exchanges the code for tokens."""
    if error:
        raise HTTPException(status_code=400, detail=f"TikTok Auth Error: {error}")
    if not code:
        raise HTTPException(status_code=400, detail="Missing required authorization verification token.")

    client_key = os.getenv("TIKTOK_CLIENT_KEY")
    client_secret = os.getenv("TIKTOK_CLIENT_SECRET")
    # This must match the exact string registered in the TikTok Dashboard
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

    # Handle errors sent back inside the TikTok payload
    if "error" in token_data or "access_token" not in token_data:
        err_msg = token_data.get("error_description", "Failed to retrieve access token")
        return JSONResponse(status_code=400, content={"error": err_msg, "details": token_data})

    # Save token payload directly into your memory configuration store
    TIKTOK_TOKENS["access_token"] = token_data["access_token"]
    TIKTOK_TOKENS["refresh_token"] = token_data.get("refresh_token")
    
    print(f"[Backend] Token handshake verified successfully. Storage synchronized.")
    
    # Redirect back to your root frontend domain with a success flag
    return RedirectResponse(url="https://kx871t4g-8000.inc1.devtunnels.ms/?tiktok_connected=true")

# 5. AUTHENTICATION STATUS TRACKER
@app.get("/api/auth/status/tiktok")
async def get_tiktok_status():
    """Checks if the backend currently possesses a valid working access token."""
    is_connected = TIKTOK_TOKENS["access_token"] is not None
    return {"connected": is_connected}

# 6. APPLICATION SYSTEM CONTEXT ROUTERS
@app.get("/sw.js")
async def serve_service_worker():
    """Serves the Service Worker from the root domain for proper PWA scope control."""
    try:
        return FileResponse("frontend/sw.js", media_type="application/javascript")
    except Exception as e:
        return {"status": "error", "message": f"Could not find sw.js: {str(e)}"}
    
@app.get("/favicon.ico")
async def serve_favicon():
    """Serves the favicon icon to the browser tab to clear the 404 error log."""
    try:
        return FileResponse("frontend/assets/logo.webp")
    except Exception:
        from fastapi.responses import Response
        return Response(status_code=204)

# 7. AUDIO TRANSCRIPTION & VIDEO TRANSFORMATION ENGINE
@app.post("/api/upload-audio")
async def upload_sermon_audio(file: UploadFile = File(...)):
    """Receives an audio file from the frontend, saves it, and compiles the video asset."""
    try:
        print(f"[API] Received upload request for file: {file.filename}")
        
        BASE_DIR = os.path.dirname(os.path.abspath(__file__))
        upload_path = os.path.join(BASE_DIR, "uploads", file.filename)
        
        # Ensure target directories exist dynamically to protect the pipeline
        os.makedirs(os.path.dirname(upload_path), exist_ok=True)
        
        with open(upload_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)
            
        print(f"[API] Successfully saved raw audio to disk: {upload_path}")
        
        filename_without_ext = os.path.splitext(file.filename)[0]
        output_video_name = f"{filename_without_ext}_render.mp4"
        
        # Execution of video composition logic via moviepy engine layer
        rendered_video_path = generate_sermon_video(
            audio_path=upload_path, 
            output_filename=output_video_name
        )
        
        return {
            "status": "success",
            "message": "Audio successfully converted to video clip!",
            "video_file": output_video_name,
            "full_path": rendered_video_path
        }
        
    except Exception as e:
        print(f"[API] Error handling media upload: {str(e)}")
        return {"status": "error", "message": f"Server processing failed: {str(e)}"}

@app.get("/api/health")
async def health_check():
    """Returns the online status of core application subsystems."""
    return {
        "status": "online",
        "loaded_modules": ["Config Engine", "Static Frontend Assets Router", "TikTok Handshake Vector"],
        "security": "JWT Protected (Pending)"
    }

@app.post("/api/test-publish/tiktok")
async def test_tiktok_publish():
    """
    Manually triggers a chunked video upload test to TikTok 
    using the active access token stored in memory.
    """
    # 1. Verify we actually have a token saved from your successful login
    token = TIKTOK_TOKENS.get("access_token")
    if not token:
        raise HTTPException(
            status_code=400, 
            detail="No active TikTok token found. Please connect your account first!"
        )
        
    # 2. Point to a real, short video clip on your computer to test with
    # PLACE A REAL 5-10 SECOND MP4 FILE IN YOUR PROJECT ROOT AND NAME IT 'test.mp4'
    video_target = "test.mp4" 
    
    if not os.path.exists(video_target):
        raise HTTPException(
            status_code=404, 
            detail=f"Please drop a test video file named '{video_target}' in your project folder first."
        )

    print("[Test] Initializing TikTok publisher module...")
    publisher = TikTokPublisher()
    
    # 3. Call your chunked uploader pipeline
    result = publisher.publish_video(
        video_path=video_target,
        title="Testing HerGlory Content Engine integration! #Ministry",
        description="Automated cross-posting platform deployment verification run.",
        access_token=token  # Pass the token we just captured
    )
    
    if result.get("status") == "success":
        return {
            "status": "success",
            "message": "Video successfully pushed to TikTok chunk queue!",
            "publish_id": result.get("publish_id")
        }
    else:
        return JSONResponse(status_code=500, content=result)
        
# Boot engine directly if python file is executed via terminal
# This simply means each and evry python file is secetly has a varibale called __name__
# When you run a python file directly, the __name__ variable is set to "__main__" so this prevents you from accidenatllly starting the browrser from likr importing this into a diffrent file
if __name__ == "__name__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)