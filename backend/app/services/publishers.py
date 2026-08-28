import abc
from typing import Dict, Any, Optional
import httpx
from datetime import datetime

class SocialPlatformProvider(abc.ABC):
    """Abstract Base Class for Social Media Platform Publishing Providers"""
    
    @abc.abstractmethod
    async def publish(self, content: str, media_urls: list, access_token: str, custom_copy: Optional[str] = None) -> Dict[str, Any]:
        """
        Publish content and media to the platform using valid OAuth access_token.
        Returns dict with keys: {'success': bool, 'post_url': str, 'error': str}
        """
        pass


class LinkedInPublisher(SocialPlatformProvider):
    async def publish(self, content: str, media_urls: list, access_token: str, custom_copy: Optional[str] = None) -> Dict[str, Any]:
        post_text = custom_copy or content
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
            "X-Restli-Protocol-Version": "2.0.0"
        }
        
        # Get user profile URN
        profile_urn = "urn:li:person:developer"
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                me_resp = await client.get("https://api.linkedin.com/v2/me", headers=headers)
                if me_resp.status_code == 200:
                    profile_urn = f"urn:li:person:{me_resp.json().get('id')}"
        except Exception:
            pass

        payload = {
            "author": profile_urn,
            "lifecycleState": "PUBLISHED",
            "specificContent": {
                "com.linkedin.ugc.ShareContent": {
                    "shareCommentary": {"text": post_text},
                    "shareMediaCategory": "NONE"
                }
            },
            "visibility": {"com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"}
        }

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                res = await client.post("https://api.linkedin.com/v2/ugcPosts", headers=headers, json=payload)
                if res.status_code in [200, 201]:
                    post_id = res.json().get("id", "")
                    return {
                        "success": True,
                        "post_url": f"https://www.linkedin.com/feed/update/{post_id}",
                        "error": None
                    }
                else:
                    return {
                        "success": False,
                        "post_url": None,
                        "error": f"LinkedIn API HTTP {res.status_code}: {res.text}"
                    }
        except Exception as e:
            return {"success": False, "post_url": None, "error": str(e)}


class TwitterPublisher(SocialPlatformProvider):
    async def publish(self, content: str, media_urls: list, access_token: str, custom_copy: Optional[str] = None) -> Dict[str, Any]:
        post_text = custom_copy or content
        if len(post_text) > 280:
            post_text = post_text[:277] + "..."

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
        payload = {"text": post_text}

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                res = await client.post("https://api.twitter.com/2/tweets", headers=headers, json=payload)
                if res.status_code in [200, 201]:
                    tweet_id = res.json().get("data", {}).get("id", "")
                    return {
                        "success": True,
                        "post_url": f"https://twitter.com/i/status/{tweet_id}",
                        "error": None
                    }
                else:
                    return {
                        "success": False,
                        "post_url": None,
                        "error": f"Twitter API HTTP {res.status_code}: {res.text}"
                    }
        except Exception as e:
            return {"success": False, "post_url": None, "error": str(e)}


class YouTubePublisher(SocialPlatformProvider):
    async def publish(self, content: str, media_urls: list, access_token: str, custom_copy: Optional[str] = None) -> Dict[str, Any]:
        title = (custom_copy or content)[:95] or "Podule Episode Clip"
        description = custom_copy or content

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
        
        # Insert metadata stub for YouTube Video / Shorts Upload
        payload = {
            "snippet": {
                "title": title,
                "description": description,
                "tags": ["podcast", "podule", "ai"],
                "categoryId": "22"
            },
            "status": {
                "privacyStatus": "public"
            }
        }

        try:
            async with httpx.AsyncClient(timeout=20.0) as client:
                res = await client.post(
                    "https://www.googleapis.com/youtube/v3/videos?part=snippet,status",
                    headers=headers,
                    json=payload
                )
                if res.status_code in [200, 201]:
                    video_id = res.json().get("id", "")
                    return {
                        "success": True,
                        "post_url": f"https://www.youtube.com/watch?v={video_id}",
                        "error": None
                    }
                else:
                    return {
                        "success": False,
                        "post_url": None,
                        "error": f"YouTube API HTTP {res.status_code}: {res.text}"
                    }
        except Exception as e:
            return {"success": False, "post_url": None, "error": str(e)}


# Platform Provider Registry Factory
PROVIDERS: Dict[str, SocialPlatformProvider] = {
    "linkedin": LinkedInPublisher(),
    "twitter": TwitterPublisher(),
    "youtube": YouTubePublisher()
}

def get_platform_publisher(platform: str) -> SocialPlatformProvider:
    return PROVIDERS.get(platform.lower(), TwitterPublisher())
