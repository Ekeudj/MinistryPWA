"""
app/db.py

One shared database module used by everything else in the app.
Replaces the old RAM dicts (TIKTOK_TOKENS / YOUTUBE_TOKENS) with a real
Supabase Postgres table, so tokens survive Render restarts/redeploys.

Uses SQLModel (an ORM on top of SQLAlchemy) so we never write raw SQL.
A connection POOL is created once at import time and reused for every
request — we never open/close a single long-lived connection by hand.
"""

import os
from datetime import datetime
from typing import Optional
from sqlmodel import SQLModel, Field, create_engine, Session, select

# Paste your Supabase "Transaction pooler" connection string into .env as
# SUPABASE_DB_URL (with your real DB password swapped into the placeholder).
DATABASE_URL = os.getenv("SUPABASE_DB_URL")

# pool_pre_ping checks a connection is still alive before using it — avoids
# "connection closed" errors after the DB has been idle for a while.
engine = create_engine(DATABASE_URL, pool_pre_ping=True, echo=False)


# ===================================================
# TABLES
# ===================================================

class PlatformToken(SQLModel, table=True):
    __tablename__ = "platform_tokens"
    # platform = "tiktok" / "youtube" / "instagram" / "facebook"
    platform: str = Field(primary_key=True)
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None
    # Optional stable IDs some platforms need alongside the token
    # (e.g. Meta's Page ID / IG Business Account ID)
    extra_id: Optional[str] = None
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class Post(SQLModel, table=True):
    __tablename__ = "posts"
    id: Optional[int] = Field(default=None, primary_key=True)
    title: str
    media_type: str          # "audio" / "video" / "photo"
    platforms: str           # comma-separated, e.g. "tiktok,youtube"
    status: str               # "success" / "partial" / "failed"
    created_at: datetime = Field(default_factory=datetime.utcnow)


def init_db():
    """Call once at startup — creates tables if they don't exist yet."""
    SQLModel.metadata.create_all(engine)


# ===================================================
# TOKEN HELPERS  (replaces TIKTOK_TOKENS / YOUTUBE_TOKENS dicts)
# ===================================================

def get_token(platform: str) -> Optional[PlatformToken]:
    with Session(engine) as session:
        return session.get(PlatformToken, platform)


def save_token(platform: str, access_token: str, refresh_token: str = None, extra_id: str = None):
    with Session(engine) as session:
        existing = session.get(PlatformToken, platform)
        if existing:
            existing.access_token = access_token
            if refresh_token is not None:
                existing.refresh_token = refresh_token
            if extra_id is not None:
                existing.extra_id = extra_id
            existing.updated_at = datetime.utcnow()
            session.add(existing)
        else:
            session.add(PlatformToken(
                platform=platform,
                access_token=access_token,
                refresh_token=refresh_token,
                extra_id=extra_id,
            ))
        session.commit()


# ===================================================
# POST HISTORY HELPERS  (for "recent posts" on the dashboard)
# ===================================================

def save_post(title: str, media_type: str, platforms: list, status: str):
    with Session(engine) as session:
        session.add(Post(
            title=title,
            media_type=media_type,
            platforms=",".join(platforms),
            status=status,
        ))
        session.commit()


def list_recent_posts(limit: int = 20):
    with Session(engine) as session:
        statement = select(Post).order_by(Post.created_at.desc()).limit(limit)
        return session.exec(statement).all()
