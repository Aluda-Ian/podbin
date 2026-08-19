from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from contextlib import asynccontextmanager
from pathlib import Path
import os

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
from app.services.db import db

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize SQLAlchemy database schemas and seeds
    await db.init_db()
    yield

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Backend API for Podule Podcast Automation platform",
    version="1.0.0",
    lifespan=lifespan
)

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

# Mount static files folder dynamically for EDL edits
static_dir = Path("static")
static_dir.mkdir(exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")

# Mount logos directory
logos_dir = Path("public/logos")
logos_dir.mkdir(parents=True, exist_ok=True)
app.mount("/logos", StaticFiles(directory="public/logos"), name="logos")

# Serve compiled frontend assets
public_dir = Path("public")
public_dir.mkdir(exist_ok=True)
app.mount("/assets", StaticFiles(directory="public/assets"), name="assets")

# Basic health-check endpoint
@app.get("/health", status_code=200)
async def health_check():
    return {
        "status": "healthy",
        "service": settings.PROJECT_NAME
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

# SPA Catch-all route (must be at the very bottom)
@app.get("/{full_path:path}")
async def serve_spa(full_path: str):
    index_path = os.path.join("public", "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"error": "Frontend build not found"}
