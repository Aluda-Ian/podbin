from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, HTMLResponse
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional
import os
import mimetypes

from app.core.config import settings
from app.api.v1.episodes import router as episodes_router
from app.api.v1.agents import router as agents_router
from app.api.v1.approvals import router as approvals_router
from app.api.v1.settings import router as settings_router
from app.api.v1.auth import router as auth_router
from app.api.v1.admin import router as admin_router
from app.api.v1.distribution import router as distribution_router
from app.api.v1.integrations import router as integrations_router
from app.api.v1.notifications import router as notifications_router
from app.api.v1.copilot import router as copilot_router
from app.api.v1.video_uploads import router as video_uploads_router
from app.services.db import db

DEFAULT_INDEX_HTML = """<!DOCTYPE html><html lang="en"><head><meta charSet="utf-8"/><meta name="viewport" content="width=device-width, initial-scale=1"/><link rel="stylesheet" href="/assets/styles-BiabKEYy.css" data-precedence="default"/><link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Open+Sans:ital,wght@0,300..800;1,300..800&amp;family=JetBrains+Mono:wght@400;500&amp;display=swap" data-precedence="default"/><title>podule — Autonomous Podcast Operations</title><meta name="description" content="podule is the agentic AI operating system for podcasters. Autonomous research, production, and distribution — with human-in-the-loop control."/><meta name="author" content="podule"/><meta property="og:title" content="podule — Autonomous Podcast Operations"/><meta property="og:description" content="Stop managing your podcast. Start scaling it. podule orchestrates research, production, and distribution autonomously."/><meta property="og:type" content="website"/><meta name="twitter:card" content="summary"/><link rel="modulepreload" href="/assets/index-B1NRAZfl.js"/><link rel="modulepreload" href="/assets/jsx-runtime-bzQ4Vb5N.js"/><link rel="modulepreload" href="/assets/react-dom-DUKFG4MT.js"/><link rel="modulepreload" href="/assets/link-CVkLs2P8.js"/><link rel="modulepreload" href="/assets/createLucideIcon-DeQrcgrh.js"/><link rel="modulepreload" href="/assets/routes-CUzeY4A9.js"/><link rel="modulepreload" href="/assets/chevron-right-BYJJVHf4.js"/><link rel="modulepreload" href="/assets/cpu-CHN-xGLC.js"/><link rel="modulepreload" href="/assets/volume-2-Ds1m7MT4.js"/><link rel="preconnect" href="https://fonts.googleapis.com"/><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin="anonymous"/><script>(function(){const stored=localStorage.getItem('podule-theme');const theme=stored||'light';if(theme==='dark'){document.documentElement.classList.add('dark');}else{document.documentElement.classList.remove('dark');}})();</script></head><body><!-- chunked_upload_injector MUST load before app bundle --><script src="/assets/chunked_upload_injector.js"></script><div class="flex h-screen w-screen items-center justify-center bg-background"><div class="h-8 w-8 animate-spin rounded-full border-4 border-accent border-t-transparent"></div></div><section aria-label="Notifications alt+T" tabindex="-1" aria-live="polite" aria-relevant="additions text" aria-atomic="false"></section><script type="module" async="" src="/assets/index-B1NRAZfl.js"></script><script src="/assets/copilot_widget.js"></script><script src="/assets/gemini_config_injector.js"></script><script src="/assets/distribution_dashboard_injector.js"></script><script src="/assets/google_auth_injector.js"></script></body></html>"""

BACKEND_DIR = Path(__file__).resolve().parents[1]

def find_file_in_candidates(relative_path: str) -> Optional[Path]:
    rel = relative_path.lstrip("/")
    candidates = []
    
    cwd = Path.cwd()
    candidates.append(cwd / "public" / rel)
    candidates.append(cwd / "backend" / "public" / rel)

    p1 = Path(__file__)
    for parent in p1.parents:
        candidates.append(parent / "public" / rel)
        candidates.append(parent / "backend" / "public" / rel)

    try:
        p2 = Path(__file__).resolve()
        for parent in p2.parents:
            candidates.append(parent / "public" / rel)
            candidates.append(parent / "backend" / "public" / rel)
    except Exception:
        pass

    candidates.extend([
        Path("/var/task/public") / rel,
        Path("/var/task/backend/public") / rel,
        Path("/var/task/api/public") / rel,
    ])

    for c in candidates:
        try:
            if c.exists() and c.is_file():
                return c
        except Exception:
            pass
    return None

def find_public_dir() -> Path:
    found_index = find_file_in_candidates("index.html")
    if found_index:
        return found_index.parent
    return Path.cwd() / "public"

@asynccontextmanager
async def lifespan(app: FastAPI):
    if db.is_configured:
        try:
            import asyncio
            await asyncio.wait_for(db.init_db(), timeout=10.0)
        except Exception as e:
            print(f"Warning: Database initialization failed on startup: {e}")
    else:
        print("Database is not configured; starting without database initialization.")
    yield

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Backend API for Podule Podcast Automation platform",
    version="1.0.0",
    lifespan=lifespan
)

# ── Upload body-size guard ────────────────────────────────────────────────────
# Rejects upload requests whose Content-Length exceeds 512 MB before the body
# is streamed.  This is enforced at the HTTP middleware layer so Uvicorn/h11
# never has to buffer the payload at all.
_MAX_UPLOAD_BYTES = 512 * 1024 * 1024  # 512 MB
_UPLOAD_PATHS = ("/api/v1/episodes/upload-direct", "/api/v1/episodes/", "/api/v1/episodes")

@app.middleware("http")
async def enforce_upload_size_limit(request, call_next):
    path = request.url.path
    if any(path.startswith(p) for p in _UPLOAD_PATHS):
        cl = request.headers.get("content-length")
        if cl and int(cl) > _MAX_UPLOAD_BYTES:
            from fastapi.responses import JSONResponse
            return JSONResponse(
                status_code=413,
                content={"detail": "File too large. Maximum allowed upload size is 512 MB."},
            )
    return await call_next(request)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def add_no_cache_header(request, call_next):
    response = await call_next(request)
    path = request.url.path.lower()
    if path.startswith("/assets") or path in ["/", "/dashboard", "/admin"]:
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
    return response

public_dir = find_public_dir()

# Mount static files folder dynamically for EDL edits safely
static_dir = Path("/tmp/static") if os.getenv("VERCEL") else (BACKEND_DIR / "static")
try:
    static_dir.mkdir(parents=True, exist_ok=True)
except Exception:
    pass
if static_dir.exists() and static_dir.is_dir():
    try:
        app.mount("/static", StaticFiles(directory=static_dir), name="static")
    except Exception as e:
        print(f"Notice: static mount warning: {e}")

# Mount logos directory safely
logos_dir = public_dir / "logos"
try:
    logos_dir.mkdir(parents=True, exist_ok=True)
except Exception:
    pass
if logos_dir.exists() and logos_dir.is_dir():
    try:
        app.mount("/logos", StaticFiles(directory=logos_dir), name="logos")
    except Exception as e:
        print(f"Notice: logos mount warning: {e}")

# Serve compiled frontend assets safely
assets_dir = public_dir / "assets"
if assets_dir.exists() and assets_dir.is_dir():
    try:
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")
    except Exception as e:
        print(f"Notice: assets mount warning: {e}")

# Diagnostic health-check & database status endpoint
@app.get("/health", status_code=200)
async def health_check():
    return {
        "status": "healthy",
        "service": settings.PROJECT_NAME,
        "database_configured": db.is_configured,
        "database_ready": db.is_db_ready,
    }

@app.get("/api/v1/db-status")
async def db_status():
    from urllib.parse import urlparse
    from app.services.db import get_mongodb_url, get_db_name
    from app.models.user import User
    
    url = get_mongodb_url()
    parsed = urlparse(url)
    await db.ensure_db_initialized()
    user_count = None
    if db.is_db_ready:
        try:
            user_count = await User.count()
        except Exception as e:
            user_count = f"Error: {e}"

    return {
        "is_configured": db.is_configured,
        "is_db_ready": db.is_db_ready,
        "init_step": getattr(db, "_init_step", None),
        "last_error": getattr(db, "_last_error", None),
        "mongodb_url_set": bool(url),
        "mongodb_host": parsed.hostname or "none",
        "db_name": get_db_name(),
        "user_count_in_mongo": user_count
    }

# Register routes with version prefix
app.include_router(episodes_router, prefix="/api/v1/episodes", tags=["episodes"])
app.include_router(agents_router, prefix="/api/v1/agents", tags=["agents"])
app.include_router(approvals_router, prefix="/api/v1/approvals", tags=["approvals"])
app.include_router(settings_router, prefix="/api/v1/settings", tags=["settings"])
app.include_router(auth_router, prefix="/api/v1/auth", tags=["auth"])
app.include_router(admin_router, prefix="/api/v1/admin", tags=["admin"])
app.include_router(distribution_router, prefix="/api/v1/distribution", tags=["distribution"])
app.include_router(integrations_router, prefix="/api/v1/integrations", tags=["integrations"])
app.include_router(notifications_router, prefix="/api/v1/notifications", tags=["Notifications"])
app.include_router(copilot_router, prefix="/api/v1/copilot", tags=["copilot"])
app.include_router(video_uploads_router, prefix="/api/v1/video-uploads", tags=["video-uploads"])

# SPA Catch-all route (must be at the very bottom)
@app.get("/{full_path:path}")
async def serve_spa(full_path: str):
    if full_path.startswith("api/"):
        raise HTTPException(status_code=404, detail="API endpoint not found")
    if full_path in ["docs", "redoc", "openapi.json", "docs/", "redoc/"]:
        raise HTTPException(status_code=404, detail="Documentation path handled by FastAPI")
        
    # Check if asking for a static asset file
    if full_path.startswith("assets/") or full_path.startswith("logos/") or full_path.startswith("static/") or "." in Path(full_path).name:
        asset_file = find_file_in_candidates(full_path)
        if asset_file:
            mime_type, _ = mimetypes.guess_type(str(asset_file))
            return FileResponse(str(asset_file), media_type=mime_type or "application/octet-stream")
        raise HTTPException(status_code=404, detail=f"Asset '{full_path}' not found")

    # Serve index.html from disk if available
    index_file = find_file_in_candidates("index.html")
    if index_file:
        return FileResponse(str(index_file), media_type="text/html")

    # Embedded HTML fallback
    return HTMLResponse(content=DEFAULT_INDEX_HTML, media_type="text/html")
