import json
from typing import Dict, Any
from openai import AsyncOpenAI
from app.core.config import settings
from app.services.db import db, decrypt_key
from app.models.user import ProviderTier, ProviderConfig


async def get_provider_config() -> ProviderConfig:
    settings_data = await db.get_settings()
    pc = settings_data.get("provider_config", {})
    tier = pc.get("tier", ProviderTier.PLATFORM_FREE)
    custom_api_key = pc.get("custom_api_key")
    if tier == ProviderTier.BYO_KEY and custom_api_key:
        custom_api_key = decrypt_key(custom_api_key)
    return ProviderConfig(
        tier=tier,
        custom_api_key=custom_api_key,
        custom_provider=pc.get("custom_provider"),
    )


async def generate_metadata(transcript: str) -> Dict[str, Any]:
    provider = await get_provider_config()

    system_prompt = (
        "You are a podcast metadata specialist. Given a transcript, generate:\n"
        "1. A list of 3-5 episode title suggestions (concise, engaging)\n"
        "2. Detailed show notes (2-3 paragraphs summarizing key topics)\n"
        "Return JSON with keys 'titles' (list of strings) and 'notes' (string)."
    )

    if provider.tier == ProviderTier.BYO_KEY and provider.custom_api_key:
        client = AsyncOpenAI(
            api_key=provider.custom_api_key,
            base_url=_resolve_base_url(provider.custom_provider),
        )
        model = "gpt-4o"
    elif provider.tier == ProviderTier.PLATFORM_PAID:
        client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        model = "gpt-4o"
    else:
        client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        model = "gpt-4o-mini"

    try:
        resp = await client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Transcript:\n\n{transcript}"},
            ],
            response_format={"type": "json_object"},
            temperature=0.7,
            max_tokens=1500,
        )
        raw = resp.choices[0].message.content or "{}"
        return json.loads(raw)
    except Exception:
        return _mock_metadata(transcript)


def _resolve_base_url(provider: str | None) -> str | None:
    mapping = {
        "openai": "https://api.openai.com/v1",
        "anthropic": None,
        "google": None,
        "azure": None,
        "ollama": "http://localhost:11434/v1",
    }
    return mapping.get(provider.lower()) if provider else None


def _mock_metadata(transcript: str) -> Dict[str, Any]:
    lines = [l for l in transcript.split("\n") if l.strip()]
    return {
        "titles": [
            f"Deep Dive: {lines[0][:50]}" if lines else "Untitled Episode",
            f"In Conversation About {transcript[:40]}...",
            f"Exploring {transcript[30:70]}...",
            "Full Episode Recap",
        ],
        "notes": (
            f"In this episode, we explore key themes from the conversation. "
            f"The discussion covers {transcript[:100]}...\n\n"
            f"Topics include actionable insights for creators looking to streamline "
            f"their podcast production workflow and distribute content efficiently."
        ),
    }
