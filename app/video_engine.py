import os
from moviepy.editor import AudioFileClip, ImageClip

def generate_sermon_video(audio_path: str, output_filename: str) -> str:
    """
    Takes a raw audio path, pairs it with a default ministry background image,
    and renders a high-quality vertical video (.mp4) optimized for shorts/shorts.
    """
    # 1. Define our directories
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    DEFAULT_BG = os.path.join(BASE_DIR, "frontend", "assets", "logo.webp") # Fallback background
    OUTPUT_DIR = os.path.join(BASE_DIR, "output")
    
    output_path = os.path.join(OUTPUT_DIR, output_filename)
    
    print(f"[Engine] Loading audio file: {audio_path}")
    
    try:
        # 2. Load the audio file
        audio_clip = AudioFileClip(audio_path)
        duration = audio_clip.duration
        print(f"[Engine] Audio duration loaded: {duration} seconds")
        
        # 3. Create the background image clip and match its duration to the audio
        print(f"[Engine] Generating video canvas using background: {DEFAULT_BG}")
        video_clip = ImageClip(DEFAULT_BG).set_duration(duration)
        
        # 4. Bind the audio to our video canvas
        video_clip = video_clip.set_audio(audio_clip)
        
        # 5. Render the final MP4 file
        print(f"[Engine] Starting heavy rendering pipeline...")
        video_clip.write_videofile(
            output_path,
            fps=24,                  # Standard video frame rate
            codec="libx264",         # Universally accepted video format
            audio_codec="aac",       # High-quality audio encoding
            temp_audiofile="temp-audio.m4a",
            remove_temp=True
        )
        
        # 6. Close clips to free up system RAM memory
        audio_clip.close()
        video_clip.close()
        
        print(f"[Engine] Success! Video saved cleanly to: {output_path}")
        return output_path
        
    except Exception as e:
        print(f"[Engine] Critical error during rendering: {str(e)}")
        raise e