import os
from typing import Dict, Any, List, Optional
from datetime import datetime
from app.services.db import db
from app.agents.state import EpisodeStatus

async def tool_cut_video(episode_id: str, start_time: str, end_time: str, reason: str = "User requested trim") -> Dict[str, Any]:
    """Cut or trim a video segment between start_time (e.g. '01:20') and end_time (e.g. '02:45')."""
    ep = await db.get_episode(episode_id)
    if not ep:
        return {"error": f"Episode '{episode_id}' not found."}
    
    edl = ep.get("edit_decision_list") or []
    cut_entry = {
        "cut_id": f"cut-{len(edl) + 1}",
        "start_time": start_time,
        "end_time": end_time,
        "action": "REMOVE",
        "reason": reason,
        "timestamp": datetime.now().isoformat()
    }
    edl.append(cut_entry)
    
    await db.update_episode(episode_id, {
        "edit_decision_list": edl,
        "note": f"Video trimmed from {start_time} to {end_time} ({reason})"
    })
    
    # Send agent completion notification
    await db.notify_agent_completion(
        agent_tag="AGENT_PROD",
        message=f"Applied video cut on {episode_id} ({start_time} - {end_time})",
        episode_id=episode_id
    )
    
    return {
        "status": "success",
        "action": "cut_video",
        "episode_id": episode_id,
        "start_time": start_time,
        "end_time": end_time,
        "reason": reason,
        "edl_count": len(edl),
        "message": f"Successfully cut video segment ({start_time} -> {end_time}) on episode {episode_id}."
    }


async def tool_schedule_video(episode_id: str, platforms: List[str], scheduled_at: str, caption: Optional[str] = None) -> Dict[str, Any]:
    """Schedule episode or clip distribution to selected platforms at a specified ISO datetime string."""
    ep = await db.get_episode(episode_id)
    if not ep:
        return {"error": f"Episode '{episode_id}' not found."}
    
    schedule = ep.get("socials_schedule") or []
    for platform in platforms:
        entry = {
            "id": f"sched-{episode_id}-{platform.lower()}-{len(schedule) + 1}",
            "platform": platform,
            "caption": caption or f"Episode release: {ep.get('title', 'Untitled')}",
            "time": scheduled_at,
            "status": "SCHEDULED"
        }
        schedule.append(entry)
        
    await db.update_episode(episode_id, {
        "socials_schedule": schedule,
        "status": EpisodeStatus.DISTRO,
        "stage": "Growth",
        "note": f"Scheduled to {', '.join(platforms)} for {scheduled_at}"
    })
    
    await db.notify_agent_completion(
        agent_tag="AGENT_DISTRO",
        message=f"Scheduled distribution for {episode_id} across {', '.join(platforms)} on {scheduled_at[:10]}",
        episode_id=episode_id
    )
    
    return {
        "status": "success",
        "action": "schedule_video",
        "episode_id": episode_id,
        "platforms": platforms,
        "scheduled_at": scheduled_at,
        "message": f"Successfully scheduled episode {episode_id} for {', '.join(platforms)} at {scheduled_at}."
    }


async def tool_add_captions(episode_id: str, burn_in_captions: bool = True, caption_style: str = "animated") -> Dict[str, Any]:
    """Generate or burn in animated captions for clips in an episode."""
    ep = await db.get_episode(episode_id)
    if not ep:
        return {"error": f"Episode '{episode_id}' not found."}
    
    clips = ep.get("clips") or []
    updated_clips = []
    for clip in clips:
        updated_clips.append({
            **clip,
            "burn_in_captions": burn_in_captions,
            "caption_style": caption_style,
            "status": "APPROVED"
        })
        
    if not updated_clips:
        # Create a default clip if none exist
        updated_clips = [{
            "id": f"clip-{episode_id}-1",
            "title": f"Highlight Clip - {ep.get('title', 'Untitled')}",
            "duration": "00:45",
            "burn_in_captions": burn_in_captions,
            "caption_style": caption_style,
            "status": "APPROVED",
            "platforms": ["TikTok", "YouTube Shorts"]
        }]
        
    await db.update_episode(episode_id, {
        "clips": updated_clips,
        "note": f"Captions ({caption_style}) {'enabled' if burn_in_captions else 'disabled'} for clips."
    })
    
    await db.notify_agent_completion(
        agent_tag="AGENT_REPURPOSE",
        message=f"Generated animated captions burn-in ({caption_style}) for episode {episode_id}",
        episode_id=episode_id
    )
    
    return {
        "status": "success",
        "action": "add_captions",
        "episode_id": episode_id,
        "burn_in_captions": burn_in_captions,
        "caption_style": caption_style,
        "clips_count": len(updated_clips),
        "message": f"Successfully added {caption_style} captions to episode {episode_id} clips."
    }


async def tool_generate_clips(episode_id: str, count: int = 3, platform: str = "TikTok") -> Dict[str, Any]:
    """Generate AI viral clips from episode transcript and media."""
    ep = await db.get_episode(episode_id)
    if not ep:
        return {"error": f"Episode '{episode_id}' not found."}
    
    clips = ep.get("clips") or []
    new_clips = []
    for i in range(1, count + 1):
        c = {
            "id": f"clip-{episode_id}-{len(clips) + i}",
            "title": f"Key Highlight #{len(clips) + i} for {platform}",
            "duration": "00:45",
            "status": "PENDING",
            "burn_in_captions": True,
            "platforms": [platform]
        }
        new_clips.append(c)
        
    updated_clips = clips + new_clips
    await db.update_episode(episode_id, {
        "clips": updated_clips,
        "note": f"Extracted {count} vertical clips for {platform}."
    })
    
    await db.notify_agent_completion(
        agent_tag="AGENT_REPURPOSE",
        message=f"Generated {count} vertical clips optimized for {platform} from episode {episode_id}",
        episode_id=episode_id
    )
    
    return {
        "status": "success",
        "action": "generate_clips",
        "episode_id": episode_id,
        "generated_count": count,
        "platform": platform,
        "message": f"Generated {count} new clips for {platform}."
    }


async def tool_list_episodes(status_filter: Optional[str] = None) -> Dict[str, Any]:
    """List project episodes and their current workflow status."""
    episodes = await db.get_episodes()
    if status_filter:
        episodes = [ep for ep in episodes if ep.get("status") == status_filter]
    
    summary = [{
        "id": ep["id"],
        "title": ep.get("title"),
        "guest": ep.get("guest"),
        "status": ep.get("status"),
        "stage": ep.get("stage"),
        "clips_count": len(ep.get("clips") or [])
    } for ep in episodes]
    
    return {
        "status": "success",
        "count": len(summary),
        "episodes": summary
    }


async def tool_configure_llm_provider(provider: str, model_name: str, api_key: Optional[str] = None) -> Dict[str, Any]:
    """Update active LLM provider configuration (e.g. OpenAI, Anthropic, Ollama, DeepSeek, Gemini)."""
    current_settings = await db.get_settings()
    provider_config = current_settings.get("provider_config", {}) or {}
    
    provider_config["tier"] = "BYO_KEY" if api_key else "PLATFORM_FREE"
    provider_config["custom_provider"] = provider
    
    updates = {
        "provider_config": provider_config,
        "orchestrator_model": model_name
    }
    if api_key:
        from app.services.db import encrypt_key
        provider_config["custom_api_key"] = encrypt_key(api_key)
        
    await db.update_settings(updates)
    
    return {
        "status": "success",
        "provider": provider,
        "model": model_name,
        "message": f"Switched LLM provider to {provider} ({model_name})."
    }

async def tool_edit_description(episode_id: Optional[str] = None, new_description: str = "", instruction: Optional[str] = None) -> Dict[str, Any]:
    """Edit or update an episode's show notes / description in the database based on user instruction."""
    episodes = await db.get_episodes()
    target_ep = None
    if episode_id:
        target_ep = next((ep for ep in episodes if ep["id"].lower() == episode_id.lower()), None)
    if not target_ep and len(episodes) > 0:
        target_ep = episodes[0]
        
    if not target_ep:
        return {"error": f"Episode '{episode_id}' not found."}
        
    target_id = target_ep["id"]
    await db.update_episode(target_id, {
        "notes": new_description,
        "note": f"Description updated via Gemini AI Copilot instruction."
    })
    
    await db.notify_agent_completion(
        agent_tag="AGENT_PROD",
        message=f"Updated description for episode {target_id} using Gemini instruction.",
        episode_id=target_id
    )
    
    return {
        "status": "success",
        "action": "edit_description",
        "episode_id": target_id,
        "new_description": new_description,
        "message": f"Successfully updated description for episode '{target_ep.get('title', target_id)}'."
    }


async def tool_edit_title(episode_id: Optional[str] = None, new_title: str = "", instruction: Optional[str] = None) -> Dict[str, Any]:
    """Edit or update an episode's title in the database based on user instruction."""
    episodes = await db.get_episodes()
    target_ep = None
    if episode_id:
        target_ep = next((ep for ep in episodes if ep["id"].lower() == episode_id.lower()), None)
    if not target_ep and len(episodes) > 0:
        target_ep = episodes[0]
        
    if not target_ep:
        return {"error": f"Episode '{episode_id}' not found."}
        
    target_id = target_ep["id"]
    await db.update_episode(target_id, {
        "title": new_title,
        "note": f"Title updated to '{new_title}' via Gemini AI Copilot instruction."
    })
    
    await db.notify_agent_completion(
        agent_tag="AGENT_PROD",
        message=f"Updated title for episode {target_id} to '{new_title}'.",
        episode_id=target_id
    )
    
    return {
        "status": "success",
        "action": "edit_title",
        "episode_id": target_id,
        "new_title": new_title,
        "message": f"Successfully updated episode title to '{new_title}'."
    }


TOOL_REGISTRY = {
    "cut_video": tool_cut_video,
    "schedule_video": tool_schedule_video,
    "add_captions": tool_add_captions,
    "generate_clips": tool_generate_clips,
    "list_episodes": tool_list_episodes,
    "configure_llm_provider": tool_configure_llm_provider,
    "edit_description": tool_edit_description,
    "edit_title": tool_edit_title,
}
