import os
from moviepy.editor import AudioFileClip, ImageClip

def generate_sermon_video(audio_path: str, output_filename: str) -> str:
    """
    Renders standard ministry content from an audio track and a static logo image background.
    """
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    DEFAULT_BG = os.path.join(BASE_DIR, "frontend", "assets", "logo.webp")
    
    # BUG FIX 3: Change output directory to match 'uploads' so main_2.py path validation functions find it instantly
    OUTPUT_DIR = os.path.join(BASE_DIR, "uploads")
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    output_path = os.path.join(OUTPUT_DIR, output_filename)
    
    try:
        audio_clip = AudioFileClip(audio_path)
        duration = audio_clip.duration
        
        video_clip = ImageClip(DEFAULT_BG).set_duration(duration)
        video_clip = video_clip.set_audio(audio_clip)
        
        video_clip.write_videofile(
            output_path,
            fps=24,
            codec="libx264",
            audio_codec="aac",
            temp_audiofile=os.path.join(OUTPUT_DIR, "temp-audio.m4a"),
            remove_temp=True
        )
        
        audio_clip.close()
        video_clip.close()
        return output_path
        
    except Exception as e:
        print(f"[Engine Rendering Exception]: {str(e)}")
        raise e