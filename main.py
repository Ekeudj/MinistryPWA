from app.config import settings
from fastapi import FastAPI, UploadFile, File, HTTPException, Query, Request, BackgroundTasks  
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, RedirectResponse, JSONResponse
from app.video_engine import generate_sermon_video
import os
import httpx
import asyncio
from dotenv import load_dotenv
load_dotenv()
from app.publishers.tiktok import TikTokPublisher
from app.publishers.youtube import YouTubePublisher
from app.publishers.meta import InstagramPublisher, FacebookPublisher, exchange_for_long_lived_token
from app import db


PUBLIC_BASE_URL = os.getenv("PUBLIC_BASE_URL", "https://herglory-backend.onrender.com")
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOADS_DIR = os.path.join(BASE_DIR, "uploads")
os.makedirs(UPLOADS_DIR, exist_ok=True)

app = FastAPI(
    title="HerGlory Content Engine API",
    version="1.0.0",
    description="Scalable automation backend for cross-posting ministry content."
)

db.init_db()

app.mount("/static", StaticFiles(directory="frontend"), name="frontend_assets")
app.mount("/uploads", StaticFiles(directory=UPLOADS_DIR), name="uploads")


def resolve_video_path(video_file: str):
    candidate = os.path.join(UPLOADS_DIR, video_file)
    if os.path.exists(candidate):
        return candidate
    rendered = os.path.join(UPLOADS_DIR, f"{os.path.splitext(video_file)[0]}_render.mp4")
    if os.path.exists(rendered):
        return rendered
    if os.path.exists(video_file):
        return video_file
    return None


# ===================================================
# FRONTEND
# ===================================================

@app.get("/")
async def serve_frontend():
    frontend_path = os.path.join(BASE_DIR, "frontend", "index.html")
    if os.path.exists(frontend_path):
        return FileResponse(frontend_path)
    return JSONResponse(status_code=500, content={"status": "error", "message": "Could not find frontend/index.html."})


# ===================================================
# APP AUTH  (login + password management)
# ===================================================

@app.post("/api/auth/login")
async def login(request: Request):
    """
    Checks credentials. Password is read from the DB first (so changes
    take effect immediately without a redeploy), falling back to the
    APP_PASSWORD env var on first use before she has ever changed it.
    """
    body = await request.json()
    email = body.get("email", "").strip().lower()
    password = body.get("password", "")

    valid_email = os.getenv("APP_EMAIL", "").strip().lower()
    display_name = os.getenv("APP_DISPLAY_NAME", "Pastor Mrs. Lubega")

    # DB password wins if set; env var is the fallback for first-time use
    stored_pw = await asyncio.to_thread(db.get_app_password)
    valid_password = stored_pw if stored_pw else os.getenv("APP_PASSWORD", "")

    if email == valid_email and password == valid_password:
        return JSONResponse(content={"ok": True, "name": display_name})
    return JSONResponse(status_code=401, content={"ok": False})


@app.post("/api/auth/change-password")
async def change_password(request: Request):
    """
    Lets the client change the app password from the login screen.
    Verifies the current password first, then stores the new one in the DB.
    No redeploy needed — takes effect on the next login attempt.
    """
    body = await request.json()
    current = body.get("current_password", "")
    new_pw = body.get("new_password", "")

    if not new_pw or len(new_pw) < 6:
        return JSONResponse(status_code=400, content={"ok": False, "error": "Password must be at least 6 characters."})

    stored_pw = await asyncio.to_thread(db.get_app_password)
    valid_password = stored_pw if stored_pw else os.getenv("APP_PASSWORD", "")

    if current != valid_password:
        return JSONResponse(status_code=401, content={"ok": False, "error": "Incorrect current password."})

    await asyncio.to_thread(db.save_app_password, new_pw)
    return JSONResponse(content={"ok": True})


# ===================================================
# TIKTOK PIPELINE MODULE
# ===================================================

@app.get("/api/auth/tiktok")
async def tiktok_login():
    client_key = os.getenv("TIKTOK_CLIENT_KEY")
    redirect_uri = f"{PUBLIC_BASE_URL}/api/callback/tiktok"
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
    redirect_uri = f"{PUBLIC_BASE_URL}/api/callback/tiktok"

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
        return RedirectResponse(url=f"{PUBLIC_BASE_URL}/?tiktok_connected=false")

    await asyncio.to_thread(
        db.save_token, "tiktok", token_data["access_token"], token_data.get("refresh_token")
    )
    return RedirectResponse(url=f"{PUBLIC_BASE_URL}/?tiktok_connected=true")

@app.get("/api/auth/status/tiktok")
async def get_tiktok_status():
    token = await asyncio.to_thread(db.get_token, "tiktok")
    return JSONResponse(content={"connected": token is not None and token.access_token is not None})

@app.post("/api/test-publish/tiktok")
async def test_tiktok_publish(request: Request):
    stored_token = await asyncio.to_thread(db.get_token, "tiktok")
    token = stored_token.access_token if stored_token else None
    if not token:
        return JSONResponse(status_code=400, content={"status": "failed", "error": "No active TikTok token found."})

    try:
        body = await request.json()
        video_target = body.get("video_file", "test.mp4")
        post_title = body.get("title") or "Ministry Live Sermon Clip"
        post_description = body.get("description") or "Automated cross-posting platform delivery."
    except Exception:
        video_target = "test.mp4"
        post_title = "Ministry Live Sermon Clip"
        post_description = "Automated cross-posting platform delivery."

    video_file_path = resolve_video_path(video_target)
    if not video_file_path:
        return JSONResponse(status_code=404, content={"status": "failed", "error": f"Media target file '{video_target}' not found on server."})

    publisher = TikTokPublisher()
    result = publisher.publish_video(
        video_path=video_file_path,
        title=post_title,
        description=post_description,
        access_token=token
    )

    await asyncio.to_thread(
        db.save_post, post_title, "video", ["tiktok"],
        "success" if result.get("status") == "success" else "failed"
    )

    if result.get("status") == "success":
        return JSONResponse(content={"status": "success", "publish_id": result.get("publish_id")})
    return JSONResponse(status_code=500, content=result)


# ===================================================
# YOUTUBE PIPELINE MODULE
# ===================================================

@app.get("/api/auth/youtube")
def youtube_auth_login():
    redirect_uri = f"{PUBLIC_BASE_URL}/api/callback/youtube"
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
    token = await asyncio.to_thread(db.get_token, "youtube")
    return JSONResponse(content={"connected": token is not None and token.access_token is not None})

@app.get("/api/callback/youtube")
async def youtube_oauth_callback(code: str = Query(None)):
    if not code:
        return RedirectResponse(url=f"{PUBLIC_BASE_URL}/?youtube_connected=false")

    redirect_uri = f"{PUBLIC_BASE_URL}/api/callback/youtube"
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
            await asyncio.to_thread(
                db.save_token, "youtube", tokens.get("access_token"), tokens.get("refresh_token")
            )
            return RedirectResponse(url=f"{PUBLIC_BASE_URL}/?youtube_connected=true")
    except Exception as e:
        print(f"[YouTube Callback Exception]: {str(e)}")

    return RedirectResponse(url=f"{PUBLIC_BASE_URL}/?youtube_connected=false")


def run_youtube_upload(video_path: str, access_token: str, title: str, description: str):
    try:
        publisher = YouTubePublisher()
        result = publisher.publish_video(
            video_path=video_path,
            title=title,
            description=description,
            access_token=access_token
        )
        db.save_post(title, "video", ["youtube"], "success" if result.get("status") == "success" else "failed")
    except Exception as e:
        print(f"[YouTube Worker Thread Crash]: {str(e)}")


@app.post("/api/test-publish/youtube")
async def production_publish_youtube(request: Request, background_tasks: BackgroundTasks):
    stored_token = await asyncio.to_thread(db.get_token, "youtube")
    access_token = stored_token.access_token if stored_token else None
    if not access_token:
        return JSONResponse(status_code=400, content={"status": "failed", "error": "User channel is not authenticated."})

    try:
        body = await request.json()
        video_file_path = body.get("video_file", "test.mp4")
        post_title = body.get("title") or "Pastor Mrs. Lubega Live Sermon Clip"
        post_description = body.get("description") or "Powerful spiritual insight for today. #shorts #faith"
    except Exception:
        video_file_path = "test.mp4"
        post_title = "Pastor Mrs. Lubega Live Sermon Clip"
        post_description = "Powerful spiritual insight for today. #shorts #faith"

    resolved_path = resolve_video_path(video_file_path)
    if not resolved_path:
        return JSONResponse(status_code=404, content={"status": "failed", "error": f"Missing operational source file content: '{video_file_path}'"})
    video_file_path = resolved_path

    background_tasks.add_task(run_youtube_upload, video_file_path, access_token, post_title, post_description)
    return JSONResponse(status_code=202, content={"status": "processing", "message": "Video upload dispatched to system background workers successfully!"})


# ===================================================
# META (INSTAGRAM + FACEBOOK) PIPELINE MODULE
# ===================================================

@app.get("/api/auth/meta")
async def meta_connect():
    long_lived_token = os.getenv("LONG_LIVED_TOKEN")
    page_id = os.getenv("META_PAGE_ID")
    if not long_lived_token:
        return RedirectResponse(url=f"{PUBLIC_BASE_URL}/?meta_connected=false")
    await asyncio.to_thread(db.save_token, "meta", long_lived_token, extra_id=page_id)
    return RedirectResponse(url=f"{PUBLIC_BASE_URL}/?meta_connected=true")


@app.post("/api/setup/meta")
async def setup_meta_token(request: Request):
    body = await request.json()
    short_lived_token = body.get("short_lived_token")
    if not short_lived_token:
        return JSONResponse(status_code=400, content={"status": "failed", "error": "Missing short_lived_token."})

    try:
        exchanged = await asyncio.to_thread(exchange_for_long_lived_token, short_lived_token)
        long_lived_token = exchanged.get("access_token")
        if not long_lived_token:
            return JSONResponse(status_code=500, content={"status": "failed", "error": f"Exchange failed: {exchanged}"})
        await asyncio.to_thread(db.save_token, "meta", long_lived_token, extra_id=body.get("page_id"))
        return JSONResponse(content={"status": "success", "message": "Long-lived Meta token stored successfully.", "expires_in": exchanged.get("expires_in")})
    except Exception as e:
        return JSONResponse(status_code=500, content={"status": "failed", "error": str(e)})


@app.get("/api/auth/status/meta")
async def get_meta_status():
    token = await asyncio.to_thread(db.get_token, "meta")
    return JSONResponse(content={"connected": token is not None and token.access_token is not None})


@app.post("/api/test-publish/instagram")
async def test_instagram_publish(request: Request):
    stored_token = await asyncio.to_thread(db.get_token, "meta")
    access_token = stored_token.access_token if stored_token else None
    if not access_token:
        return JSONResponse(status_code=400, content={"status": "failed", "error": "No active Meta token found."})

    body = await request.json()
    video_target = body.get("video_file", "")
    title = body.get("title") or "Ministry Sermon Clip"
    description = body.get("description", "")
    media_type = body.get("media_type", "video")

    resolved_path = resolve_video_path(video_target)
    if not resolved_path:
        return JSONResponse(status_code=404, content={"status": "failed", "error": f"File '{video_target}' not found."})

    public_url = f"{PUBLIC_BASE_URL}/uploads/{os.path.basename(resolved_path)}"
    publisher = InstagramPublisher()

    if media_type == "photo":
        result = await asyncio.to_thread(
            publisher.publish_photo, resolved_path, description or title,
            access_token=access_token, image_url=public_url
        )
    else:
        result = await asyncio.to_thread(
            publisher.publish_video, "", title, description,
            access_token=access_token, video_url=public_url
        )

    await asyncio.to_thread(
        db.save_post, title, media_type, ["instagram"],
        "success" if result.get("status") == "success" else "failed"
    )
    if result.get("status") == "success":
        return JSONResponse(content=result)
    return JSONResponse(status_code=500, content=result)


@app.post("/api/test-publish/facebook")
async def test_facebook_publish(request: Request):
    stored_token = await asyncio.to_thread(db.get_token, "meta")
    access_token = stored_token.access_token if stored_token else None
    if not access_token:
        return JSONResponse(status_code=400, content={"status": "failed", "error": "No active Meta token found."})

    body = await request.json()
    video_target = body.get("video_file", "")
    title = body.get("title") or "Ministry Sermon Clip"
    description = body.get("description", "")
    media_type = body.get("media_type", "video")

    video_file_path = resolve_video_path(video_target)
    if not video_file_path:
        return JSONResponse(status_code=404, content={"status": "failed", "error": f"File '{video_target}' not found."})

    publisher = FacebookPublisher()

    if media_type == "photo":
        result = await asyncio.to_thread(
            publisher.publish_photo, video_file_path, description or title,
            access_token=access_token
        )
    else:
        result = await asyncio.to_thread(
            publisher.publish_video, video_file_path, title, description,
            access_token=access_token
        )

    await asyncio.to_thread(
        db.save_post, title, media_type, ["facebook"],
        "success" if result.get("status") == "success" else "failed"
    )
    if result.get("status") == "success":
        return JSONResponse(content=result)
    return JSONResponse(status_code=500, content=result)


# ===================================================
# POST HISTORY
# ===================================================

@app.get("/api/posts")
async def get_recent_posts():
    posts = await asyncio.to_thread(db.list_recent_posts, 20)
    return JSONResponse(content={"posts": [
        {
            "title": p.title,
            "media_type": p.media_type,
            "platforms": p.platforms.split(","),
            "status": p.status,
            "created_at": p.created_at.isoformat(),
        } for p in posts
    ]})


# ===================================================
# SYSTEM UTILITIES
# ===================================================

@app.get("/sw.js")
async def serve_service_worker():
    return FileResponse("frontend/sw.js", media_type="application/javascript")

@app.post("/api/upload-audio")
async def upload_sermon_audio(file: UploadFile = File(...)):
    try:
        upload_path = os.path.join(UPLOADS_DIR, file.filename)
        with open(upload_path, "wb") as buffer:
            while chunk := await file.read(1024 * 1024):
                buffer.write(chunk)

        filename_without_ext = os.path.splitext(file.filename)[0]
        output_video_name = f"{filename_without_ext}_render.mp4"

        await asyncio.to_thread(
            generate_sermon_video,
            audio_path=upload_path,
            output_filename=output_video_name
        )

        return JSONResponse(content={"status": "success", "video_file": output_video_name})
    except Exception as e:
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})

@app.post("/api/upload-video")
async def upload_sermon_video(file: UploadFile = File(...)):
    try:
        upload_path = os.path.join(UPLOADS_DIR, file.filename)
        with open(upload_path, "wb") as buffer:
            while chunk := await file.read(1024 * 1024):
                buffer.write(chunk)
        return JSONResponse(content={"status": "success", "video_file": file.filename})
    except Exception as e:
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=False)
