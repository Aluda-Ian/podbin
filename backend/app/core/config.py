import os
from pathlib import Path
from dotenv import load_dotenv

# Load env file from backend root .env or project root .env
backend_root = Path(__file__).resolve().parents[2]
env_path = backend_root / ".env"
load_dotenv(dotenv_path=env_path)

class Settings:
    PROJECT_NAME: str = os.getenv("PROJECT_NAME", "Podule Backend API")
    PUBLIC_URL: str = os.getenv("PUBLIC_URL", "https://podule.vendatechnologies.com").rstrip("/")
    FRONTEND_URL: str = os.getenv("FRONTEND_URL", PUBLIC_URL).rstrip("/")
    
    # Parse allowed origins from comma separated string
    ALLOWED_ORIGINS: list[str] = [
        origin.strip()
        for origin in os.getenv(
            "ALLOWED_ORIGINS",
            f"{FRONTEND_URL},http://localhost:5173,http://localhost:5174",
        ).split(",")
        if origin.strip()
    ]
    
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    DEEPGRAM_API_KEY: str = os.getenv("DEEPGRAM_API_KEY", "")
    IS_SANDBOX_MODE: bool = os.getenv("IS_SANDBOX_MODE", "False").lower() == "true"

settings = Settings()
