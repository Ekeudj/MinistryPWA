from app.config import settings
from fastapi import FastAPI, UploadFile, File   
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from app.video_engine import generate_sermon_video
import os

#We intiliaze the server.

app = FastAPI(
    title="HerGlory Content Engine API",
    version="1.0.0",
    description="Scaalabe automation backend for cross-posting ministry content."
)

# 2. Tell FastAPI to look inside your custom frontend/ folder for style.css, app.js, icons, etc.
# 'StaticFiles' automatically handles streaming these files safely to user browsers.
# app.mount is how you tell fastapi to take a
#complete folder on your pc and expose it to the internt, PS it takes 3 arguments
#1.the url route,the actual location and the placeholder to track these files
app.mount("/static", StaticFiles(directory="frontend"), name="frontend_assets")

# 3. Create the Main Root URL Route
# When a user opens http://127.0.0.1:8000, this function hands them your 'index.html'
@app.get("/")
async def serve_frontend():
    """
        Serves the core Single Page Application UI from the frontend folder.
    """
    try:
        return FileResponse("frontend/index.html")
    except Exception as e:
        return {
            "status": "error",
            "message": f"Could not find frontend files: {str(e)}"
        }

@app.get("/sw.js")
async def serve_service_worker():
    """
    Serves the Service Worker from the root domain so it has the full 
    scope authority required by browsers to manage PWA caching.
    """
    try:
        return FileResponse("frontend/sw.js", media_type="application/javascript")
    except Exception as e:
        return {"status": "error", "message": f"Could not find sw.js: {str(e)}"}
    
#Route for the favocin image where the browser should find it
@app.get("/favicon.ico")
async def serve_favicon():
    """
    Serves the favicon icon to the browser tab to clear the 404 error log.
    """
    try:
        # We can reuse your existing logo image asset here
        return FileResponse("frontend/assets/logo.webp")
    except Exception:
        # If the file isn't found, return an empty response so the terminal stays clean
        from fastapi.responses import Response
        return Response(status_code=204)

@app.post("/api/upload-audio")
async def upload_sermon_audio(file: UploadFile = File(...)):
    """
    Receives an audio file from the phone/frontend browser, 
    saves it to disk, and passes it to the MoviePy engine.
    """
    try:
        print(f"[API] Received upload request for file: {file.filename}")
        
        # 1. Define where to save the incoming raw audio file
        BASE_DIR = os.path.dirname(os.path.abspath(__file__))
        upload_path = os.path.join(BASE_DIR, "uploads", file.filename)
        
        # 2. Stream the incoming bytes from the client network into our uploads folder
        with open(upload_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)
            
        print(f"[API] Successfully saved raw audio to disk: {upload_path}")
        
        # 3. Create a clean name for our rendered video file output
        filename_without_ext = os.path.splitext(file.filename)[0]
        output_video_name = f"{filename_without_ext}_render.mp4"
        
        # 4. Fire up the MoviePy generator engine
        rendered_video_path = generate_sermon_video(
            audio_path=upload_path, 
            output_filename=output_video_name
        )
        
        # 5. Return the clean metadata back to the client UI app
        return {
            "status": "success",
            "message": "Audio successfully converted to video clip!",
            "video_file": output_video_name,
            "full_path": rendered_video_path
        }
        
    except Exception as e:
        print(f"[API] Error handling media upload: {str(e)}")
        return {"status": "error", "message": f"Server processing failed: {str(e)}"}


# Heath check for when in deployment to keep cloud tracking systems updated
@app.get("/api/health")
async def health_check():
    """
    Returns the status of the engine room and loaded services.
    """
    return {
        "status": "online",
        #show what part of the backend have booted up sucessfully
        "loaded_modules": ["Config Engine", "Static Frontend Assets Router"],
        #JSON web token security is not yet implemented, but this is a placeholder for future security status
        "security": "JWT Protected (Pending)"
    }

# Boot engine directly if python file is executed via terminal
# This simply means each and evry python file is secetly has a varibale called __name__
# When you run a python file directly, the __name__ variable is set to "__main__" so this prevents you from accidenatllly starting the browrser from likr importing this into a diffrent file
if __name__ == "__name__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)