import uvicorn
import os
from dotenv import load_dotenv

# Load variables before launching uvicorn
load_dotenv()

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    # Run the FastAPI app defined in backend/app/main.py
    # - http=httptools    : C-based parser with no hard body-size limit (unlike h11's default)
    # - timeout_keep_alive: allow large uploads up to 10 minutes on slow connections
    # - limit_concurrency : prevent OOM when multiple large uploads happen simultaneously
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=port,
        reload=True,
        http="httptools",
        timeout_keep_alive=600,
        limit_concurrency=20,
    )
