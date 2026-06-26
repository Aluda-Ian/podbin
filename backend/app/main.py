from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.api.v1.episodes import router as episodes_router

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Backend API for PodBin Podcast Automation platform",
    version="1.0.0"
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Basic health-check endpoint
@app.get("/health", status_code=200)
async def health_check():
    return {
        "status": "healthy",
        "service": settings.PROJECT_NAME
    }

# Register routes with version prefix
app.include_router(episodes_router, prefix="/api/v1/episodes", tags=["episodes"])
