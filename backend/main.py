import uvicorn
import os
from dotenv import load_dotenv

# Load variables before launching uvicorn
load_dotenv()

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    # Run the FastAPI app defined in backend/app/main.py
    uvicorn.run("app.main:app", host="0.0.0.0", port=port, reload=True)
