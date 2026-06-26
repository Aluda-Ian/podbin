import os
from pathlib import Path
from dotenv import load_dotenv

# Load env file from backend root .env or project root .env
backend_root = Path(__file__).resolve().parents[2]
env_path = backend_root / ".env"
load_dotenv(dotenv_path=env_path)

class Settings:
    PROJECT_NAME: str = os.getenv("PROJECT_NAME", "PodBin Backend API")
    
    # Parse allowed origins from comma separated string
    ALLOWED_ORIGINS: list[str] = [
        origin.strip()
        for origin in os.getenv("ALLOWED_ORIGINS", "http://localhost:5173,http://localhost:5174").split(",")
        if origin.strip()
    ]
    
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    DEEPGRAM_API_KEY: str = os.getenv("DEEPGRAM_API_KEY", "")

settings = Settings()
