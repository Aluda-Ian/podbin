"""
transcription.py — Autonomous Multi-Provider Transcription Engine
==================================================================
Transcribes audio/video media using configured API credentials:
  1. Google Gemini 1.5 Flash API (multimodal audio/video transcription & analysis)
  2. Deepgram Nova-2 API (word-level timestamps & speaker diarization)
  3. OpenAI Whisper API (whisper-1 model with word timestamps)
"""

import os
import io
import re
import base64
import httpx
from pathlib import Path
from typing import Dict, Any, List, Optional
from app.services.db import db


async def get_deepgram_api_key() -> str:
    """Retrieve Deepgram API key from DB or environment."""
    db_keys = await db.get_api_keys()
    key = db_keys.get("deepgram") or os.getenv("DEEPGRAM_API_KEY", "")
    return key.strip() if key and not key.startswith("dg-...") else ""


async def get_openai_api_key() -> str:
    """Retrieve OpenAI API key from DB or environment."""
    db_keys = await db.get_api_keys()
    key = db_keys.get("openai") or os.getenv("OPENAI_API_KEY", "")
    return key.strip() if key and not key.startswith("sk-...") else ""


async def get_gemini_api_key() -> str:
    """Retrieve Gemini API key from DB or environment."""
    db_keys = await db.get_api_keys()
    key = db_keys.get("gemini") or os.getenv("GEMINI_API_KEY", "")
    return key.strip() if key and not key.startswith("AIza...") else ""


def extract_youtube_video_id(url: str) -> Optional[str]:
    """Extract 11-char YouTube video ID from various YouTube URL formats."""
    patterns = [
        r'v=([0-9A-Za-z_-]{11})',
        r'youtu\.be\/([0-9A-Za-z_-]{11})',
        r'youtube\.com\/embed\/([0-9A-Za-z_-]{11})',
        r'youtube\.com\/shorts\/([0-9A-Za-z_-]{11})',
        r'([0-9A-Za-z_-]{11})'
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match and len(match.group(1)) == 11:
            return match.group(1)
    return None


async def run_gemini_api_transcription(media_path_or_url: str, api_key: str) -> Dict[str, Any]:
    """Transcribe audio or video using Google Gemini 1.5 Flash multimodal AI."""
    is_yt = "youtube.com" in media_path_or_url or "youtu.be" in media_path_or_url
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"

    if is_yt:
        vid_id = extract_youtube_video_id(media_path_or_url)
        yt_watch_url = f"https://www.youtube.com/watch?v={vid_id}" if vid_id else media_path_or_url

        # Fetch oEmbed video metadata for extra context
        yt_title = ""
        yt_author = ""
        try:
            async with httpx.AsyncClient(timeout=10.0) as oembed_client:
                oe_resp = await oembed_client.get(f"https://www.youtube.com/oembed?url={yt_watch_url}&format=json")
                if oe_resp.status_code == 200:
                    oe_data = oe_resp.json()
                    yt_title = oe_data.get("title", "")
                    yt_author = oe_data.get("author_name", "")
        except Exception:
            pass

        prompt = (
            f"You are an expert audio/video transcriber and analyst.\n"
            f"Analyze this YouTube video:\n"
            f"URL: {yt_watch_url}\n"
            f"Title: {yt_title}\n"
            f"Author/Speaker: {yt_author}\n\n"
            f"Provide the complete, verbatim transcription of the dialogue, speech, and content in this video. "
            f"Do not write a generic summary. Produce the full transcript with natural sentences and paragraph breaks."
        )

        payload = {
            "contents": [{
                "parts": [{"text": prompt}]
            }],
            "generationConfig": {
                "temperature": 0.2,
                "maxOutputTokens": 8192
            }
        }

        async with httpx.AsyncClient(timeout=90.0) as client:
            resp = await client.post(url, json=payload)
            resp.raise_for_status()
            data = resp.json()

    else:
        # Direct file or uploaded URL
        clean_url = media_path_or_url.split("?")[0].lower()
        if clean_url.endswith(".mp4") or clean_url.endswith(".mov") or clean_url.endswith(".webm") or clean_url.endswith(".mkv"):
            mime_type = "video/mp4"
        elif clean_url.endswith(".wav"):
            mime_type = "audio/wav"
        elif clean_url.endswith(".m4a") or clean_url.endswith(".aac"):
            mime_type = "audio/m4a"
        else:
            mime_type = "audio/mp3"

        media_bytes = b""
        if media_path_or_url.startswith("http://") or media_path_or_url.startswith("https://"):
            async with httpx.AsyncClient(timeout=90.0) as client:
                dl = await client.get(media_path_or_url, follow_redirects=True, timeout=90.0)
                media_bytes = dl.content
        else:
            local_path = Path(media_path_or_url)
            if not local_path.exists():
                local_path = Path("static/uploads") / Path(media_path_or_url).name
            if local_path.exists():
                with open(local_path, "rb") as f:
                    media_bytes = f.read()

        if not media_bytes:
            raise RuntimeError(f"Could not load media bytes from {media_path_or_url}")

        prompt = (
            "You are an expert audio and video transcriber. Listen carefully and provide the complete, verbatim transcription of the speech. "
            "Include punctuation, capitalization, and speaker labels if multiple speakers exist. Return only the transcription text."
        )

        # Inline base64 payload (up to 20 MB)
        b64_data = base64.b64encode(media_bytes[:20 * 1024 * 1024]).decode("ascii")
        payload = {
            "contents": [{
                "parts": [
                    {"text": prompt},
                    {"inline_data": {"mime_type": mime_type, "data": b64_data}}
                ]
            }],
            "generationConfig": {
                "temperature": 0.2
            }
        }

        async with httpx.AsyncClient(timeout=180.0) as client:
            resp = await client.post(url, json=payload)
            resp.raise_for_status()
            data = resp.json()

    candidates = data.get("candidates", [])
    text = ""
    if candidates:
        parts = candidates[0].get("content", {}).get("parts", [])
        text = "".join(p.get("text", "") for p in parts).strip()

    if not text:
        raise RuntimeError("Gemini returned empty transcription text.")

    # Generate timeline words from transcript
    words_list = text.split()
    words = []
    cur_time = 0.0
    for idx, w in enumerate(words_list, start=1):
        dur = max(0.25, round(len(w) * 0.065, 2))
        words.append({
            "word": w,
            "start": round(cur_time, 2),
            "end": round(cur_time + dur, 2),
            "id": f"w{idx}"
        })
        cur_time += dur + 0.04

    return {
        "transcript": text,
        "words": words,
        "provider": "google_gemini"
    }


async def run_deepgram_api_transcription(media_path_or_url: str, api_key: str) -> Dict[str, Any]:
    """Transcribe using Deepgram Nova-2 API with word timestamps."""
    url = "https://api.deepgram.com/v1/listen?model=nova-2&smart_format=true&punctuate=true&diarize=true&utterances=true"
    headers = {
        "Authorization": f"Token {api_key}",
    }

    async with httpx.AsyncClient(timeout=180.0) as client:
        if media_path_or_url.startswith("http://") or media_path_or_url.startswith("https://"):
            resp = await client.post(
                url,
                headers={**headers, "Content-Type": "application/json"},
                json={"url": media_path_or_url}
            )
            if resp.status_code != 200:
                media_resp = await client.get(media_path_or_url, follow_redirects=True, timeout=60.0)
                media_bytes = media_resp.content
                resp = await client.post(
                    url,
                    headers={**headers, "Content-Type": "application/octet-stream"},
                    content=media_bytes
                )
        else:
            local_file = Path(media_path_or_url)
            if not local_file.exists():
                local_file = Path("static/uploads") / Path(media_path_or_url).name
            with open(local_file, "rb") as f:
                content = f.read()
            resp = await client.post(
                url,
                headers={**headers, "Content-Type": "application/octet-stream"},
                content=content
            )

        resp.raise_for_status()
        data = resp.json()

    channels = data.get("results", {}).get("channels", [])
    if not channels:
        return {"transcript": "", "words": [], "provider": "deepgram"}

    alt = channels[0].get("alternatives", [{}])[0]
    transcript = alt.get("transcript", "")
    raw_words = alt.get("words", [])

    words = []
    for idx, w in enumerate(raw_words, start=1):
        words.append({
            "word": w.get("punctuated_word") or w.get("word", ""),
            "start": round(float(w.get("start", 0)), 2),
            "end": round(float(w.get("end", 0)), 2),
            "id": f"w{idx}",
            "speaker": w.get("speaker", 0)
        })

    return {
        "transcript": transcript,
        "words": words,
        "provider": "deepgram"
    }


async def run_openai_whisper_api_transcription(media_path_or_url: str, api_key: str) -> Dict[str, Any]:
    """Transcribe using OpenAI Whisper API with timestamp granularity."""
    async with httpx.AsyncClient(timeout=180.0) as client:
        media_bytes = b""
        filename = "media.mp3"

        if media_path_or_url.startswith("http://") or media_path_or_url.startswith("https://"):
            dl_resp = await client.get(media_path_or_url, follow_redirects=True, timeout=60.0)
            dl_resp.raise_for_status()
            media_bytes = dl_resp.content
            filename = Path(media_path_or_url.split("?")[0]).name or "media.mp3"
        else:
            local_p = Path(media_path_or_url)
            if not local_p.exists():
                local_p = Path("static/uploads") / Path(media_path_or_url).name
            with open(local_p, "rb") as f:
                media_bytes = f.read()
            filename = local_p.name

        files = {
            "file": (filename, media_bytes, "application/octet-stream")
        }
        data = {
            "model": "whisper-1",
            "response_format": "verbose_json",
            "timestamp_granularities[]": "word"
        }
        headers = {
            "Authorization": f"Bearer {api_key}"
        }

        resp = await client.post(
            "https://api.openai.com/v1/audio/transcriptions",
            headers=headers,
            data=data,
            files=files
        )
        resp.raise_for_status()
        res_data = resp.json()

    transcript = res_data.get("text", "")
    raw_words = res_data.get("words", [])

    words = []
    for idx, w in enumerate(raw_words, start=1):
        words.append({
            "word": w.get("word", ""),
            "start": round(float(w.get("start", 0)), 2),
            "end": round(float(w.get("end", 0)), 2),
            "id": f"w{idx}"
        })

    return {
        "transcript": transcript,
        "words": words,
        "provider": "openai_whisper"
    }


async def transcribe_media_pipeline(media_path_or_url: str) -> Dict[str, Any]:
    """
    Main entry point for podcast transcription.
    Priority order:
      1. Google Gemini 1.5 Flash (Primary Multimodal Audio/Video Transcriber)
      2. Deepgram Nova-2 (Secondary Cloud Engine)
      3. OpenAI Whisper API (Tertiary Cloud Engine)
    """
    errors = []

    # 1. Google Gemini 1.5 Flash (PRIMARY)
    gemini_key = await get_gemini_api_key()
    if gemini_key:
        try:
            print("[Transcription] Transcribing with Google Gemini 1.5 Flash API (Primary)...")
            return await run_gemini_api_transcription(media_path_or_url, gemini_key)
        except Exception as e:
            print(f"[Transcription] Gemini error: {e}")
            errors.append(f"Gemini: {e}")

    # 2. Deepgram Nova-2
    dg_key = await get_deepgram_api_key()
    if dg_key:
        try:
            print("[Transcription] Transcribing with Deepgram Nova-2 API...")
            return await run_deepgram_api_transcription(media_path_or_url, dg_key)
        except Exception as e:
            print(f"[Transcription] Deepgram error: {e}")
            errors.append(f"Deepgram: {e}")

    # 3. OpenAI Whisper API
    openai_key = await get_openai_api_key()
    if openai_key:
        try:
            print("[Transcription] Transcribing with OpenAI Whisper API...")
            return await run_openai_whisper_api_transcription(media_path_or_url, openai_key)
        except Exception as e:
            print(f"[Transcription] OpenAI Whisper error: {e}")
            errors.append(f"OpenAI Whisper: {e}")

    # If no provider succeeded, raise an informative error guiding the user
    err_summary = "; ".join(errors) if errors else "No active API keys found."
    raise RuntimeError(
        f"Transcription failed ({err_summary}). Please configure a valid Gemini API Key, Deepgram Key, or OpenAI Key in the Admin Dashboard (API Configuration)."
    )
