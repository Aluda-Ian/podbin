import asyncio
from fastapi import HTTPException
import httpx
import xml.etree.ElementTree as ET
from typing import Optional, Dict, Any


def generate_spotify_rss(episodes: list) -> str:
    rss = ET.Element("rss", version="2.0")
    channel = ET.SubElement(rss, "channel")

    title = ET.SubElement(channel, "title")
    title.text = "The Lovable Frontier Podcast"

    link = ET.SubElement(channel, "link")
    link.text = "https://podule.com"

    description = ET.SubElement(channel, "description")
    description.text = "AI autonomous podcasting"

    for ep in episodes:
        item = ET.SubElement(channel, "item")
        ep_title = ET.SubElement(item, "title")
        ep_title.text = ep.get("title", "Untitled Episode")

        ep_desc = ET.SubElement(item, "description")
        ep_desc.text = ep.get("note", "")

        enclosure = ET.SubElement(item, "enclosure")
        enclosure.set("url", ep.get("raw_audio_url") or "")
        enclosure.set("type", "audio/mpeg")

    xml_str = ET.tostring(rss, encoding="utf-8")
    return xml_str.decode("utf-8")


async def publish_to_youtube(
    episode_title: str,
    video_path: str,
    privacy_status: str = "public",
    access_token: Optional[str] = None,
) -> dict:
    if not access_token:
        raise HTTPException(status_code=401, detail="YouTube not connected — no OAuth token available")

    async with httpx.AsyncClient() as client:
        # Step 1: Get the resumable upload URL
        metadata = {
            "snippet": {
                "title": episode_title,
                "description": f"Auto-published by Podule",
                "categoryId": "22",
            },
            "status": {
                "privacyStatus": privacy_status,
                "selfDeclaredMadeForKids": False,
            },
        }

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json; charset=utf-8",
            "X-Upload-Content-Type": "video/*",
        }

        res = await client.post(
            "https://www.googleapis.com/upload/youtube/v3/videos?uploadType=resumable&part=snippet,status",
            headers=headers,
            json=metadata,
        )

        if res.status_code != 200:
            raise HTTPException(
                status_code=502,
                detail=f"YouTube upload initiation failed: {res.status_code} {res.text[:200]}",
            )

        upload_url = res.headers.get("Location")
        if not upload_url:
            raise HTTPException(status_code=502, detail="YouTube did not return an upload URL")

        # Step 2: Upload the video binary
        def _read_file():
            with open(video_path, "rb") as f:
                return f.read()
        video_data = await asyncio.to_thread(_read_file)

        upload_headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "video/*",
            "Content-Length": str(len(video_data)),
        }

        upload_res = await client.put(
            upload_url,
            headers=upload_headers,
            content=video_data,
        )

        if upload_res.status_code not in (200, 201):
            raise HTTPException(
                status_code=502,
                detail=f"YouTube video upload failed: {upload_res.status_code} {upload_res.text[:200]}",
            )

        result = upload_res.json()
        return {
            "status": "success",
            "platform": "YouTube",
            "video_id": result.get("id"),
            "privacy": privacy_status,
        }


async def publish_to_tiktok(
    episode_title: str,
    video_path: str,
    privacy_status: str = "public",
    access_token: Optional[str] = None,
) -> dict:
    if not access_token:
        raise HTTPException(status_code=401, detail="TikTok not connected — no OAuth token available")

    async with httpx.AsyncClient() as client:
        # Step 1: Initialize upload
        init_res = await client.post(
            "https://open-api.tiktok.com/video/upload/init/",
            json={
                "access_token": access_token,
                "source_info": {
                    "source": "FILE",
                    "video_size": 0,
                },
            },
        )

        if init_res.status_code != 200:
            raise HTTPException(
                status_code=502,
                detail=f"TikTok upload init failed: {init_res.status_code} {init_res.text[:200]}",
            )

        init_data = init_res.json()
        upload_url = init_data.get("data", {}).get("upload_url")

        # Step 2: Upload video file
        def _read_file():
            with open(video_path, "rb") as f:
                return f.read()
        video_data = await asyncio.to_thread(_read_file)

        upload_headers = {
            "Content-Type": "video/mp4",
            "Content-Length": str(len(video_data)),
        }

        upload_res = await client.put(
            upload_url,
            headers=upload_headers,
            content=video_data,
        )

        if upload_res.status_code != 200:
            raise HTTPException(
                status_code=502,
                detail=f"TikTok video upload failed: {upload_res.status_code} {upload_res.text[:200]}",
            )

        # Step 3: Publish the video
        publish_res = await client.post(
            "https://open-api.tiktok.com/video/publish/",
            json={
                "access_token": access_token,
                "body": {
                    "title": episode_title,
                    "privacy_level": "0" if privacy_status == "public" else "1",
                },
            },
        )

        if publish_res.status_code != 200:
            raise HTTPException(
                status_code=502,
                detail=f"TikTok publish failed: {publish_res.status_code} {publish_res.text[:200]}",
            )

        return {
            "status": "success",
            "platform": "TikTok",
            "privacy": privacy_status,
        }
