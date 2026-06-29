import xml.etree.ElementTree as ET
from app.core.config import settings

def publish_to_youtube(episode_title: str, video_path: str, privacy_status: str = "public") -> dict:
    selected_status = privacy_status
    if settings.IS_SANDBOX_MODE:
        selected_status = "private"
        
    # Mocking YouTube API Uploading
    print(f"[YouTube Upload] Sandbox: {settings.IS_SANDBOX_MODE}. Uploading {episode_title} with status: {selected_status}")
    return {
        "status": "success",
        "platform": "YouTube",
        "privacy_status": selected_status,
        "video_id": "mock-yt-12345",
        "sandbox_enforced": settings.IS_SANDBOX_MODE
    }

def generate_spotify_rss(episodes: list) -> str:
    rss = ET.Element("rss", version="2.0")
    channel = ET.SubElement(rss, "channel")
    
    title = ET.SubElement(channel, "title")
    title.text = "The Lovable Frontier Podcast"
    
    link = ET.SubElement(channel, "link")
    link.text = "https://podbin.com"
    
    description = ET.SubElement(channel, "description")
    description.text = "AI autonomous podcasting"
    
    # Check sandbox guard
    if settings.IS_SANDBOX_MODE:
        sandbox_tag = ET.SubElement(channel, "sandbox")
        sandbox_tag.set("enabled", "true")
        
    for ep in episodes:
        item = ET.SubElement(channel, "item")
        ep_title = ET.SubElement(item, "title")
        ep_title.text = ep.get("title", "Untitled Episode")
        
        ep_desc = ET.SubElement(item, "description")
        ep_desc.text = ep.get("note", "")
        
        enclosure = ET.SubElement(item, "enclosure")
        enclosure.set("url", ep.get("raw_audio_url") or "")
        enclosure.set("type", "audio/mpeg")
        
    # Return pretty formatted XML string
    xml_str = ET.tostring(rss, encoding="utf-8")
    return xml_str.decode("utf-8")
