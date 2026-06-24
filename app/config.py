import os
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    """
    Application settings. This auto looks into
    the.env file and extracts keys
    If a required key is missing, Python will immediately throw a clear error 
    when starting, stopping a broken deployment before it hits production.
    """

    # YT API configuration
    YOUTUBE_CLIENT_ID: str = 'placeholder_id'
    YOUTUBE_CLIENT_SECRET: str = 'placeholder_secret'

    #TikTok API configuration
    TIKTOK_CLIENT_KEY: str = 'placeholder_key'
    TIKTOK_CLIENT_SECRET: str = 'placeholder_secret'

    # Security token for Frontend to autheticate to Fastapi
    SECRET_KEY: str = ""

    # This configuration tells Pydantic exactly where to hunt for the keys
    model_config = SettingsConfigDict(
        env_file=".env",           # Look for a file named exactly '.env'
        env_file_encoding="utf-8", # Read it using standard text encoding
        extra="ignore"             # If there are extra variables in .env, don't crash
    )

# Create a single instance of the settings to be imported and used across the app
settings = Settings()