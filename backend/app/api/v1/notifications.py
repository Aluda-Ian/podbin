from fastapi import APIRouter, HTTPException, Header
from typing import Optional, List, Dict, Any
from app.services.db import db
from app.core.security import verify_token

router = APIRouter()

@router.get("/")
async def get_notifications(authorization: Optional[str] = Header(None)):
    user_id = await verify_token(authorization)
    notifs = await db.get_notifications(user_id)
    unread = await db.get_unread_count(user_id)
    return {"notifications": notifs, "unread_count": unread}

@router.get("/unread-count")
async def get_unread_count(authorization: Optional[str] = Header(None)):
    user_id = await verify_token(authorization)
    count = await db.get_unread_count(user_id)
    return {"unread_count": count}

@router.post("/{notif_id}/read")
async def mark_read(notif_id: str, authorization: Optional[str] = Header(None)):
    user_id = await verify_token(authorization)
    n = await db.mark_notification_read(notif_id)
    if not n:
        raise HTTPException(status_code=404, detail="Notification not found")
    return {"status": "ok"}

@router.post("/read-all")
async def mark_all_read(authorization: Optional[str] = Header(None)):
    user_id = await verify_token(authorization)
    count = await db.mark_all_notifications_read(user_id)
    return {"status": "ok", "marked": count}

from pydantic import BaseModel

class PushNotificationPayload(BaseModel):
    user_id: Optional[str] = None
    type: str = "info"
    title: str
    message: str
    action_url: Optional[str] = None
    episode_id: Optional[str] = None

@router.post("/push")
async def push_notification(payload: PushNotificationPayload, authorization: Optional[str] = Header(None)):
    user_id = await verify_token(authorization)
    target_user_id = payload.user_id or user_id
    
    n = await db.create_notification({
        "user_id": target_user_id,
        "type": payload.type,
        "title": payload.title,
        "message": payload.message,
        "action_url": payload.action_url,
        "episode_id": payload.episode_id,
        "read": False
    })
    
    return {"status": "success", "notification": n}
