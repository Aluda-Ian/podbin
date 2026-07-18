import os
from typing import Optional
from app.services.db import db
from app.models.user import ProviderTier

async def get_deepgram_api_key() -> str:
    """
    Retrieve the Deepgram API key.
    Checks the user's operational_tier or provider_config.tier. If the tier is NOT 'BYO_KEY',
    the system pulls the required key directly from the server's environment variables
    rather than querying the database for user-specific keys.
    """
    settings_data = await db.get_settings()
    operational_tier = settings_data.get("operational_tier", "FREE")
    provider_config = settings_data.get("provider_config", {})
    provider_tier = provider_config.get("tier", ProviderTier.PLATFORM_FREE)

    # Master Key Fallback check: if the tier is NOT BYO_KEY, pull directly from environment variables
    if operational_tier != "BYO" and provider_tier != ProviderTier.BYO_KEY:
        return os.getenv("DEEPGRAM_API_KEY", "")

    # Otherwise, check the target storage (database vs env)
    storage_target = settings_data.get("api_storage_target") or "database"
    if storage_target == "database":
        db_keys = await db.get_api_keys()
        return db_keys.get("deepgram", "")
    return os.getenv("DEEPGRAM_API_KEY", "")
