import sys
import os
from pathlib import Path

backend_dir = Path(__file__).resolve().parents[1] / "backend"
if backend_dir.exists() and str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

try:
    from app.main import app
except Exception as err:
    import traceback
    error_tb = traceback.format_exc()
    print(f"Error initializing FastAPI app: {error_tb}")
    from fastapi import FastAPI
    app = FastAPI(title="Podule Backend Fallback API")

    @app.get("/{full_path:path}")
    async def fallback_error(full_path: str):
        return {
            "status": "error",
            "message": "Failed to initialize main FastAPI application on serverless runtime",
            "detail": str(err),
            "traceback": error_tb
        }

