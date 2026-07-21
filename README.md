<div align="center">

<br/>

```
██╗  ██╗███████╗██████╗  ██████╗ ██╗      ██████╗ ██████╗ ██╗   ██╗
██║  ██║██╔════╝██╔══██╗██╔════╝ ██║     ██╔═══██╗██╔══██╗╚██╗ ██╔╝
███████║█████╗  ██████╔╝██║  ███╗██║     ██║   ██║██████╔╝ ╚████╔╝ 
██╔══██║██╔══╝  ██╔══██╗██║   ██║██║     ██║   ██║██╔══██╗  ╚██╔╝  
██║  ██║███████╗██║  ██║╚██████╔╝███████╗╚██████╔╝██║  ██║   ██║   
╚═╝  ╚═╝╚══════╝╚═╝  ╚═╝ ╚═════╝ ╚══════╝ ╚═════╝ ╚═╝  ╚═╝   ╚═╝  
```

### **HerGlory Media Cross-Posting Platform**
*One upload. Four platforms. Zero friction.*

<br/>

![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=flat-square&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.111-009688?style=flat-square&logo=fastapi&logoColor=white)
![Supabase](https://img.shields.io/badge/Supabase-PostgreSQL-3ECF8E?style=flat-square&logo=supabase&logoColor=white)
![Render](https://img.shields.io/badge/Deployed-Render.com-46E3B7?style=flat-square&logo=render&logoColor=white)
![PWA](https://img.shields.io/badge/PWA-Installable-5A0FC8?style=flat-square&logo=pwa&logoColor=white)

<br/>

</div>

---

## What This Is

A **production-grade Progressive Web App** built for Her Glory Ministries International a ministry based in Uganda that needed to publish sermon content (video, audio, images) across TikTok, YouTube, Facebook, and Instagram simultaneously, from a single interface, without touching four separate apps every time.

The client opens the PWA on her phone, uploads a file, writes a caption, and taps **Post Now**. The backend handles everything else — format conversion, token management, parallel API dispatch, and error isolation per platform.

Built and shipped solo. I was 19 and had never deployed production software before starting this.

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        CLIENT LAYER                             │
│                                                                 │
│   ┌─────────────────────────────────────────────────────────┐   │
│   │           HerGlory PWA  (Vanilla JS + HTML/CSS)         │   │
│   │     Installable via Chrome/Safari · No app store        │   │
│   └───────────────────────────┬─────────────────────────────┘   │
└───────────────────────────────┼─────────────────────────────────┘
                                │  HTTP  (multipart/form-data)
┌───────────────────────────────▼─────────────────────────────────┐
│                        BACKEND LAYER                            │
│                    FastAPI  ·  Python 3.11                      │
│                                                                 │
│  ┌──────────────┐    ┌──────────────────┐    ┌──────────────┐   │
│  │ Upload Router│    │  resolve_video   │    │  Supabase DB │   │
│  │              │    │  _path()         │◄───│  Token Store │   │
│  │ /upload-video│    │                  │    │  (SQLModel)  │   │
│  │ /upload-audio│    │  Finds correct   │    └──────────────┘   │
│  └──────┬───────┘    │  file incl.      │                       │
│         │            │  _render.mp4     │                       │
│    ┌────▼────┐        │  fallback        │                       │
│    │ FFmpeg  │        └────────┬─────────┘                       │
│    │+MoviePy │                 │                                 │
│    │         │     Promise.allSettled()                          │
│    │ Audio → │     All platforms fire simultaneously             │
│    │  MP4    │                 │                                 │
│    └────┬────┘        ┌────────▼─────────────────────────┐      │
│         │             │       Publisher Dispatcher        │      │
│         └────────────►│                                   │      │
│                       └──┬──────┬──────┬──────────┬───────┘      │
└──────────────────────────┼──────┼──────┼──────────┼──────────────┘
                           │      │      │          │
          ┌────────────────▼─┐  ┌─▼──┐ ┌─▼────┐ ┌──▼──────────┐
          │    TikTok        │  │ YT │ │  FB  │ │  Instagram  │
          │  OAuth v2        │  │    │ │      │ │             │
          │  Video upload    │  │ BG │ │ Page │ │ Public URL  │
          │  /v2/post/video  │  │task│ │token │ │ container   │
          └──────────────────┘  └────┘ └──────┘ └─────────────┘
```

### Key Architectural Decisions

| Decision | Rationale |
|---|---|
| `Promise.allSettled()` for dispatch | Instagram's container polling takes ~60s. Sequential publishing would make all other platforms wait. Parallel execution means total post time = slowest platform, not sum of all. |
| `/uploads` static mount | Instagram's Graph API requires a public URL for video/image ingestion. Rather than S3 or a CDN, the uploads directory is served as a static route — free, zero config, and every uploaded file is instantly publicly reachable. |
| `resolve_video_path()` shared helper | The frontend passes the original filename. If the file was audio, the actual file on disk is `originalname_render.mp4`. One shared resolver handles this across all four publishers so the logic lives in exactly one place. |
| SQLModel over raw SQL | Type-safe ORM with Pydantic integration. Token rows are Python objects, not dict lookups. Schema migrations happen at startup via `SQLModel.metadata.create_all()`. |
| Chunked file streaming | Render free tier is 512 MB RAM. Reading a 150 MB sermon video into memory with `await file.read()` crashes the instance. Streaming in 1 MB chunks keeps memory flat regardless of file size. |
| DB-backed password management | App credentials stored in `app_config` table, not env vars. Allows the client to change her own password from the login screen without triggering a Render redeploy. |

---

## Tech Stack

| Layer | Technology | Why |
|---|---|---|
| **Backend** | FastAPI (Python 3.11) | Async-native, fast, excellent OpenAPI docs out of the box |
| **Database** | Supabase (PostgreSQL) | Managed Postgres with a generous free tier; zero DBA overhead |
| **ORM** | SQLModel | SQLAlchemy + Pydantic in one; tables defined as Python classes |
| **Video processing** | FFmpeg + MoviePy | Audio-to-video conversion with custom ministry background |
| **Frontend** | Vanilla JS + HTML/CSS | No framework overhead; installable as PWA via Web App Manifest |
| **Hosting** | Render.com | Git-push deploys, free tier, Oregon (US) region |
| **Auth — TikTok** | TikTok OAuth v2 | PKCE flow; tokens stored in DB |
| **Auth — YouTube** | Google OAuth 2.0 | Offline access; refresh token persisted to DB |
| **Auth — Meta** | Graph API Page Token | Long-lived (~60d) Page Access Token via manual exchange flow |

---

## Platform Integration Map

```
TIKTOK
  └── GET  /api/auth/tiktok          → redirect to TikTok OAuth
  └── GET  /api/callback/tiktok      → exchange code → save token
  └── GET  /api/auth/status/tiktok   → check DB for active token
  └── POST /api/test-publish/tiktok  → TikTokPublisher.publish_video()

YOUTUBE
  └── GET  /api/auth/youtube         → redirect to Google OAuth
  └── GET  /api/callback/youtube     → exchange code → save token
  └── GET  /api/auth/status/youtube  → check DB for active token
  └── POST /api/test-publish/youtube → YouTubePublisher (background task)

META (Facebook + Instagram — shared Page Access Token)
  └── GET  /api/auth/meta            → store LONG_LIVED_TOKEN from env
  └── POST /api/setup/meta           → exchange short-lived → long-lived → save
  └── GET  /api/auth/status/meta     → check DB for active token
  └── POST /api/test-publish/facebook   → FacebookPublisher.publish_video/photo()
  └── POST /api/test-publish/instagram  → InstagramPublisher.publish_video/photo()

UPLOAD
  └── POST /api/upload-video         → stream to disk → return filename
  └── POST /api/upload-audio         → stream to disk → FFmpeg render → return MP4 name
```

---

## Upload Flow (Detailed)

```
User taps "Post Now"
        │
        ▼
 Frontend detects media type
 (video / photo / audio)
        │
        ├── audio ──► POST /api/upload-audio
        │                   │
        │              Stream 1 MB chunks to /uploads/
        │                   │
        │              asyncio.to_thread(generate_sermon_video())
        │                   │
        │              FFmpeg renders audio + background → _render.mp4
        │                   │
        │              return { video_file: "sermon_render.mp4" }
        │
        └── video/photo ──► POST /api/upload-video
                                │
                           Stream 1 MB chunks to /uploads/
                                │
                           return { video_file: "original.mp4" }

        │
        ▼
 Frontend calls all selected platform endpoints simultaneously
 (Promise.allSettled — failure on one never blocks the others)
        │
        ├── POST /api/test-publish/tiktok
        ├── POST /api/test-publish/youtube
        ├── POST /api/test-publish/facebook
        └── POST /api/test-publish/instagram
                    │
              Each endpoint:
              1. Fetch token from Supabase
              2. Call resolve_video_path(filename)
                 → checks /uploads/filename
                 → falls back to /uploads/filename_render.mp4
              3. Call Publisher.publish_video() or publish_photo()
              4. db.save_post() — log result to posts table
              5. Return {status, publish_id}
```

---

## Database Schema

```sql
-- Platform OAuth tokens (one row per platform)
CREATE TABLE platform_tokens (
    platform      TEXT PRIMARY KEY,   -- "tiktok" | "youtube" | "meta"
    access_token  TEXT,
    refresh_token TEXT,
    extra_id      TEXT,               -- Meta Page ID / IG Business ID
    updated_at    TIMESTAMP
);

-- Post history
CREATE TABLE posts (
    id          SERIAL PRIMARY KEY,
    title       TEXT NOT NULL,
    media_type  TEXT NOT NULL,        -- "video" | "audio" | "photo"
    platforms   TEXT NOT NULL,        -- comma-separated: "tiktok,youtube"
    status      TEXT NOT NULL,        -- "success" | "partial" | "failed"
    created_at  TIMESTAMP
);

-- App config (runtime-mutable settings)
CREATE TABLE app_config (
    key   TEXT PRIMARY KEY,           -- e.g. "app_password"
    value TEXT NOT NULL
);
```

*Tables are created automatically at startup via `SQLModel.metadata.create_all(engine)`. No migration files needed.*

---

## Publisher Architecture

Each platform is an isolated class inheriting from `BasePublisher`:

```python
class BasePublisher(ABC):
    @abstractmethod
    def authenticate(self) -> bool: ...

    @abstractmethod
    def publish_video(self, video_path, title, description, **kwargs) -> dict: ...
```

```
app/publishers/
├── base.py           ← Abstract interface
├── tiktok.py         ← TikTokPublisher
├── youtube.py        ← YouTubePublisher
└── meta.py           ← InstagramPublisher + FacebookPublisher
                         exchange_for_long_lived_token()
```

Every publisher returns a consistent `{"status": "success"|"failed", ...}` dict. The dispatcher never needs to know how a platform works — just whether it succeeded.

---

## Instagram-Specific Handling

Instagram is the most demanding platform in this stack. Three non-obvious things the code handles:

**1. No direct file upload.** Instagram's Graph API requires a publicly accessible URL, not a multipart file. The `/uploads` static mount solves this — every file gets a public URL at `https://[host]/uploads/[filename]` automatically.

**2. Async container model.** Publishing a Reel is a three-step process:
```
POST /{ig_id}/media  →  container created (id returned)
     │
     ▼
GET  /{container_id}?fields=status_code  ← poll every 3s
     │                                      until FINISHED or ERROR
     ▼ (FINISHED)
POST /{ig_id}/media_publish  →  Reel goes live
```

**3. Aspect ratio enforcement.** Instagram rejects images outside the 4:5 → 1.91:1 ratio range. The backend auto-corrects with Pillow before upload:

```python
with Image.open(image_path) as img:
    w, h = img.size
    if (w / h) < 0.8 or (w / h) > 1.91:
        size = min(w, h)
        img = img.crop(((w-size)//2, (h-size)//2,
                        (w+size)//2, (h+size)//2))
    img.save(corrected_path)
```

## Local Development

```bash
# Clone
git clone https://github.com/Ekeudj/MinistryPWA
cd MinistryPWA

# Environment
cp .env.example .env #I've left this out intentionally
# → fill in your credentials

# Dependencies
pip install -r requirements.txt

# Run
uvicorn main:app --reload --port 8000

# Visit
open http://localhost:8000
```

**Requirements:** Python 3.11+, FFmpeg installed and on `$PATH`

---

## Deployment

This project deploys to **Render.com** from a GitHub push.

```
main branch push
      │
      ▼
Render detects Procfile / render.yaml
      │
      ▼
pip install -r requirements.txt
      │
      ▼
uvicorn main:app --host 0.0.0.0 --port $PORT
      │
      ▼
SQLModel.metadata.create_all()  ← runs at startup, creates tables if missing
      │
      ▼
Live at https://herglory-backend.onrender.com/
```

> **Free tier note:** Render spins the server down after 15 minutes of inactivity. First request after idle takes ~30–60s to wake. Upgrade to a paid instance to eliminate cold starts.

---

## Lessons From Building This

A few things I would tell myself at the start:

- **OAuth errors are almost always environment errors**, not code errors. The redirect URI, the token type (User vs Page), the scope — check these first before reading the code.
- **Free tier constraints are real architectural constraints.** 512 MB RAM meant I had to stream uploads in chunks. That decision is in the code permanently, not just "until we upgrade."
- **Put everything in the database.** My first version stored tokens in RAM dicts. Every server restart wiped all platform connections. Moving to Supabase was obvious in hindsight and took an afternoon.
- **Parallel over sequential.** Sequential publishing (one platform, then the next) meant Instagram's 60-second container polling blocked everything. `Promise.allSettled()` cut real-world post time by ~70%.
- **Non-technical communication is a skill.** The hardest parts of this project were not the code — they were explaining Meta's token model to a pastor over TeamViewer.

---

## Project Structure

```
herglory-cms/
├── main.py                    ← FastAPI app, all endpoints
├── app/
│   ├── db.py                  ← SQLModel ORM, all DB helpers
│   ├── config.py              ← Settings / env
│   ├── video_engine.py        ← FFmpeg/MoviePy audio→video renderer
│   └── publishers/
│       ├── base.py            ← BasePublisher ABC
│       ├── tiktok.py          ← TikTok v2 API
│       ├── youtube.py         ← YouTube Data API v3
│       └── meta.py            ← Instagram + Facebook Graph API
├── frontend/
│   ├── index.html             ← PWA shell
│   ├── app.js                 ← All client logic
│   ├── style.css              ← Styles
│   ├── manifest.json          ← PWA manifest (installable)
│   └── sw.js                  ← Service worker
├── uploads/                   ← Runtime file storage (gitignored)
├── requirements.txt
├── .env.example
└── README.md
```

---

## About

Built by *David* a 19-year-old self-taught developer from Kampala, Uganda.
Every project teaches me something the last one didn't.

**GitHub:** (https://github.com/Ekeudj)

---

<div align="center">

*Built in Uganda · Deployed in Oregon*

</div>
