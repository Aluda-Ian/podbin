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


async def get_openai_api_key() -> str:
    import os
    settings_data = await db.get_settings()
    operational_tier = settings_data.get("operational_tier", "FREE")
    provider_config = settings_data.get("provider_config", {})
    provider_tier = provider_config.get("tier", ProviderTier.PLATFORM_FREE)

    if operational_tier != "BYO" and provider_tier != ProviderTier.BYO_KEY:
        return os.getenv("OPENAI_API_KEY", "") or settings.OPENAI_API_KEY or ""

    storage_target = settings_data.get("api_storage_target") or "database"
    if storage_target == "database":
        db_keys = await db.get_api_keys()
        openai_key = db_keys.get("openai")
        if openai_key:
            return openai_key
    return settings.OPENAI_API_KEY or os.getenv("OPENAI_API_KEY", "")


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
        api_key = await get_openai_api_key()
        client = AsyncOpenAI(api_key=api_key)
        model = "gpt-4o"
    else:
        api_key = await get_openai_api_key()
        client = AsyncOpenAI(api_key=api_key)
        model = "gpt-4o-mini"

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


def _resolve_base_url(provider: str | None) -> str | None:
    mapping = {
        "openai": "https://api.openai.com/v1",
        "anthropic": None,
        "google": None,
        "azure": None,
        "ollama": "http://localhost:11434/v1",
    }
    return mapping.get(provider.lower()) if provider else None


async def run_local_whisper_transcription(media_path_or_url: str) -> dict:
    import os
    import httpx
    import tempfile
    import asyncio
    try:
        from faster_whisper import WhisperModel
    except ImportError:
        raise RuntimeError("faster-whisper is not installed in this environment. Please use Deepgram or OpenAI API transcription.")

    local_path = media_path_or_url
    temp_file = None

    if media_path_or_url.startswith("http://") or media_path_or_url.startswith("https://"):
        try:
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
            async with httpx.AsyncClient() as client:
                resp = await client.get(media_path_or_url, follow_redirects=True, timeout=120.0)
                resp.raise_for_status()
                temp_file.write(resp.content)
                temp_file.flush()
                local_path = temp_file.name
        except Exception as e:
            print(f"Failed to download remote file for local transcription: {e}")
            if temp_file:
                try:
                    os.unlink(temp_file.name)
                except:
                    pass
            raise e

    def _run():
        model = WhisperModel("base", device="cpu", compute_type="int8")
        segments, info = model.transcribe(local_path, word_timestamps=True)

        words = []
        transcript_parts = []
        word_idx = 1

        for segment in segments:
            transcript_parts.append(segment.text)
            if segment.words:
                for w in segment.words:
                    words.append({
                        "word": w.word.strip(),
                        "start": round(w.start, 2),
                        "end": round(w.end, 2),
                        "id": f"w{word_idx}"
                    })
                    word_idx += 1
            else:
                words.append({
                    "word": segment.text.strip(),
                    "start": round(segment.start, 2),
                    "end": round(segment.end, 2),
                    "id": f"w{word_idx}"
                })
                word_idx += 1

        return {
            "transcript": "".join(transcript_parts),
            "words": words
        }

    try:
        loop = asyncio.get_running_loop()
        res = await loop.run_in_executor(None, _run)
        return res
    finally:
        if temp_file:
            try:
                os.unlink(temp_file.name)
            except:
                pass
