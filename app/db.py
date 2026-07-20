"""
app/db.py
"""

import os
from datetime import datetime
from typing import Optional
from sqlmodel import SQLModel, Field, create_engine, Session, select

DATABASE_URL = os.getenv("SUPABASE_DB_URL")
engine = create_engine(DATABASE_URL, pool_pre_ping=True, echo=False)


# ===================================================
# TABLES
# ===================================================

class PlatformToken(SQLModel, table=True):
    __tablename__ = "platform_tokens"
    platform: str = Field(primary_key=True)
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None
    extra_id: Optional[str] = None
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class Post(SQLModel, table=True):
    __tablename__ = "posts"
    id: Optional[int] = Field(default=None, primary_key=True)
    title: str
    media_type: str
    platforms: str
    status: str
    created_at: datetime = Field(default_factory=datetime.utcnow)


class AppConfig(SQLModel, table=True):
    """
    General key/value config stored in the DB so settings like the app
    password can be changed at runtime without a Render redeploy.
    key="app_password" stores the current login password.
    """
    __tablename__ = "app_config"
    key: str = Field(primary_key=True)
    value: str


def init_db():
    """Call once at startup — creates tables if they don't exist yet."""
    SQLModel.metadata.create_all(engine)


# ===================================================
# TOKEN HELPERS
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
# POST HISTORY HELPERS
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


# ===================================================
# APP CONFIG HELPERS  (password management)
# ===================================================

def get_app_password() -> Optional[str]:
    """
    Returns the password stored in the DB, or None if it has never been
    changed (in which case the caller should fall back to the APP_PASSWORD
    env var as the initial password).
    """
    with Session(engine) as session:
        row = session.get(AppConfig, "app_password")
        return row.value if row else None


def save_app_password(new_password: str):
    """Upsert the app password into the DB."""
    with Session(engine) as session:
        existing = session.get(AppConfig, "app_password")
        if existing:
            existing.value = new_password
            session.add(existing)
        else:
            session.add(AppConfig(key="app_password", value=new_password))
        session.commit()
