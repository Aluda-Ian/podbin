import asyncio
import time
from datetime import datetime
from typing import Dict, Any, List

from app.models.social_post import SocialPost
from app.models.social_connection import SocialConnection
from app.api.v1.distribution import get_valid_social_token
from app.services.publishers import get_platform_publisher
from app.services.db import db

class SocialMediaScheduler:
    """
    Background Task Scheduler Engine:
    Polls SocialPost collection for posts where scheduled_time <= now() and status == 'SCHEDULED'.
    Executes publishing via platform adapters with retry exponential backoff for rate limits.
    """
    
    def __init__(self):
        self._running = False

    async def run_once(self) -> List[Dict[str, Any]]:
        """Run a single check and publishing cycle"""
        await db.ensure_db_initialized()
        if not db.is_db_ready:
            return []

        results = []
        try:
            now = datetime.utcnow()
            # Query posts ready for publishing
            posts = await SocialPost.find(
                SocialPost.status == "SCHEDULED",
                SocialPost.scheduled_time <= now
            ).to_list()

            for post in posts:
                res = await self.process_post(post)
                results.append(res)
        except Exception as e:
            print(f"[SCHEDULER ERROR] Error in publishing cycle: {e}")

        return results

    async def process_post(self, post: SocialPost) -> Dict[str, Any]:
        user_id = post.user_id
        published_urls = dict(post.published_urls or {})
        errors = []

        for platform in post.platforms:
            p_clean = platform.lower()
            # Fetch connected social account
            conn = await SocialConnection.find_one(
                SocialConnection.user_id == user_id,
                SocialConnection.platform == p_clean
            )
            
            if not conn or not conn.auto_posting_enabled:
                errors.append(f"{platform}: Account not connected or auto-posting disabled")
                continue

            # Retrieve active access token (auto-refreshed if expired)
            access_token = await get_valid_social_token(conn.id)
            if not access_token:
                errors.append(f"{platform}: Failed to obtain valid access token")
                continue

            publisher = get_platform_publisher(p_clean)
            custom_copy = (post.platform_captions or {}).get(p_clean, post.content)

            # Retry loop with exponential backoff for HTTP 429 rate limits
            max_retries = 3
            success = False
            result_data = None

            for attempt in range(max_retries):
                result_data = await publisher.publish(
                    content=post.content,
                    media_urls=post.media_urls,
                    access_token=access_token,
                    custom_copy=custom_copy
                )
                if result_data.get("success"):
                    success = True
                    published_urls[p_clean] = result_data.get("post_url", f"https://{p_clean}.com/published")
                    break
                else:
                    err_msg = result_data.get("error", "")
                    if "429" in err_msg or "rate limit" in err_msg.lower():
                        await asyncio.sleep(2 ** (attempt + 1))  # Exponential backoff: 2s, 4s, 8s
                    else:
                        break

            if not success:
                errors.append(f"{platform}: {result_data.get('error', 'Publish failed')}")

        # Update SocialPost document status
        post.published_urls = published_urls
        post.updated_at = datetime.utcnow()

        if len(published_urls) > 0:
            post.status = "PUBLISHED"
            if errors:
                post.error_log = "; ".join(errors)
        else:
            post.status = "FAILED"
            post.error_log = "; ".join(errors) if errors else "Failed to publish to all platforms"

        await post.save()
        return {
            "post_id": post.id,
            "status": post.status,
            "published_urls": published_urls,
            "errors": errors
        }

    async def start_background_loop(self):
        """Continuously check schedule queue every 60 seconds"""
        self._running = True
        print("[SCHEDULER] Background Social Media Publisher loop started.")
        while self._running:
            try:
                await self.run_once()
            except Exception as e:
                print(f"[SCHEDULER LOOP WARNING] {e}")
            await asyncio.sleep(60)

scheduler_engine = SocialMediaScheduler()
