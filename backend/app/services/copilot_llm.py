import json
import re
import os
import httpx
from typing import Dict, Any, List, Optional
from openai import AsyncOpenAI
from app.services.db import db
from app.services.copilot_tools import (
    tool_cut_video,
    tool_schedule_video,
    tool_add_captions,
    tool_generate_clips,
    tool_list_episodes,
    tool_configure_llm_provider,
    TOOL_REGISTRY
)

SUPPORTED_PROVIDERS = [
    {
        "id": "openai",
        "name": "OpenAI",
        "default_model": "gpt-4o-mini",
        "models": ["gpt-4o-mini", "gpt-4o", "gpt-3.5-turbo"],
        "base_url": "https://api.openai.com/v1"
    },
    {
        "id": "anthropic",
        "name": "Anthropic Claude",
        "default_model": "claude-3-5-sonnet",
        "models": ["claude-3-5-sonnet", "claude-3-haiku"],
        "base_url": None
    },
    {
        "id": "ollama",
        "name": "Ollama (Local)",
        "default_model": "llama3",
        "models": ["llama3", "mistral", "llama3.1", "qwen"],
        "base_url": "http://localhost:11434/v1"
    },
    {
        "id": "deepseek",
        "name": "DeepSeek",
        "default_model": "deepseek-chat",
        "models": ["deepseek-chat", "deepseek-coder"],
        "base_url": "https://api.deepseek.com/v1"
    },
    {
        "id": "gemini",
        "name": "Google Gemini",
        "default_model": "gemini-2.5-flash",
        "models": ["gemini-2.5-flash", "gemini-1.5-pro"],
        "base_url": "https://generativelanguage.googleapis.com/v1beta/openai/"
    }
]

SYSTEM_PROMPT = """You are PodBin Copilot, an AI utility assistant for podcasters.
You execute user instructions to manage podcasts, cut/trim media, generate clips, add captions, schedule distribution, and configure settings.

AVAILABLE TOOLS & INTENTS:
1. cut_video(episode_id, start_time, end_time, reason)
   e.g., "cut video from 01:20 to 02:45 on EP-1"
2. schedule_video(episode_id, platforms, scheduled_at, caption)
   e.g., "schedule episode EP-1 for TikTok and YouTube tomorrow at 5pm"
3. add_captions(episode_id, burn_in_captions, caption_style)
   e.g., "add animated captions to episode EP-1"
4. generate_clips(episode_id, count, platform)
   e.g., "generate 3 vertical clips for TikTok from EP-1"
5. list_episodes(status_filter)
   e.g., "list all episodes"
6. configure_llm_provider(provider, model_name, api_key)
   e.g., "switch provider to Ollama llama3"

TOOL EXECUTION FORMAT:
If the user prompt requires a tool action, include a JSON block in your response formatted as:
```json
{
  "tool": "<tool_name>",
  "arguments": { ... }
}
```
Always provide a concise, friendly natural language explanation alongside any tool invocation.
"""


def extract_tool_call_fallback(user_prompt: str, assistant_response: str) -> Optional[Dict[str, Any]]:
    """Parse JSON block or extract intent from prompt when model output doesn't supply native tool calls."""
    # 1. Try parsing JSON block in response
    json_match = re.search(r'```json\s*(\{.*?\})\s*```', assistant_response, re.DOTALL)
    if not json_match:
        json_match = re.search(r'(\{\s*"tool"\s*:\s*".*?\}\s*)', assistant_response, re.DOTALL)
        
    if json_match:
        try:
            parsed = json.loads(json_match.group(1))
            if "tool" in parsed and parsed["tool"] in TOOL_REGISTRY:
                return parsed
        except Exception:
            pass

    # 2. Rule-based regex fallback parser for direct utility commands
    prompt_lower = user_prompt.lower()
    
    # Check cut video intent: "cut video from 01:20 to 02:45"
    cut_match = re.search(r'cut\s+(?:video\s+)?(?:from\s+)?(\d{1,2}:\d{2})\s+to\s+(\d{1,2}:\d{2})', prompt_lower)
    if cut_match:
        ep_match = re.search(r'(ep-\d+|episodes?-\d+)', prompt_lower)
        ep_id = ep_match.group(1).upper() if ep_match else "EP-1"
        return {
            "tool": "cut_video",
            "arguments": {
                "episode_id": ep_id,
                "start_time": cut_match.group(1),
                "end_time": cut_match.group(2),
                "reason": "User requested cut"
            }
        }
        
    # Check schedule video intent
    if "schedule" in prompt_lower:
        ep_match = re.search(r'(ep-\d+|episodes?-\d+)', prompt_lower)
        ep_id = ep_match.group(1).upper() if ep_match else "EP-1"
        platforms = []
        for p in ["tiktok", "youtube", "instagram", "twitter", "spotify"]:
            if p in prompt_lower:
                platforms.append(p.capitalize())
        if not platforms:
            platforms = ["TikTok", "YouTube"]
            
        from datetime import datetime, timedelta
        sched_time = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%dT17:00:00Z")
        return {
            "tool": "schedule_video",
            "arguments": {
                "episode_id": ep_id,
                "platforms": platforms,
                "scheduled_at": sched_time
            }
        }
        
    # Check captions intent
    if "caption" in prompt_lower:
        ep_match = re.search(r'(ep-\d+|episodes?-\d+)', prompt_lower)
        ep_id = ep_match.group(1).upper() if ep_match else "EP-1"
        return {
            "tool": "add_captions",
            "arguments": {
                "episode_id": ep_id,
                "burn_in_captions": True,
                "caption_style": "animated"
            }
        }
        
    # Check generate clips intent
    if "clip" in prompt_lower or "repurpose" in prompt_lower:
        ep_match = re.search(r'(ep-\d+|episodes?-\d+)', prompt_lower)
        ep_id = ep_match.group(1).upper() if ep_match else "EP-1"
        return {
            "tool": "generate_clips",
            "arguments": {
                "episode_id": ep_id,
                "count": 3,
                "platform": "TikTok"
            }
        }
        
    # Check list episodes intent
    if "list" in prompt_lower and "episode" in prompt_lower:
        return {
            "tool": "list_episodes",
            "arguments": {}
        }
        
    return None


async def run_copilot_chat(
    prompt: str,
    provider: str = "openai",
    model: Optional[str] = None,
    api_key: Optional[str] = None,
    context: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Execute Copilot chat prompt using selected LLM provider and utility tools."""
    
    # 1. Resolve Provider Settings
    p_id = provider.lower().strip()
    provider_info = next((p for p in SUPPORTED_PROVIDERS if p["id"] == p_id), SUPPORTED_PROVIDERS[0])
    target_model = model or provider_info["default_model"]
    base_url = provider_info["base_url"]
    
    if not api_key:
        db_keys = await db.get_api_keys()
        if p_id in ("openai", "open_ai"):
            api_key = db_keys.get("openai") or os.getenv("OPENAI_API_KEY", "")
        elif p_id in ("anthropic", "claude"):
            api_key = db_keys.get("anthropic") or os.getenv("ANTHROPIC_API_KEY", "")
        elif p_id in ("gemini", "google"):
            api_key = db_keys.get("gemini") or os.getenv("GEMINI_API_KEY", "")
        elif p_id == "deepseek":
            api_key = db_keys.get("deepseek") or os.getenv("DEEPSEEK_API_KEY", "")
        else:
            api_key = db_keys.get(p_id) or os.getenv("OPENAI_API_KEY", "")
    
    env_api_key = api_key
    
    # Build System + User Messages
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"Context: {json.dumps(context or {})}\n\nInstruction: {prompt}"}
    ]
    
    assistant_text = ""
    tool_result = None
    
    try:
        if p_id == "ollama":
            # Direct HTTP call to local Ollama server
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    "http://localhost:11434/api/generate",
                    json={"model": target_model, "prompt": f"{SYSTEM_PROMPT}\n\nUser: {prompt}\n\nAssistant:", "stream": False},
                    timeout=30.0
                )
                if resp.status_code == 200:
                    assistant_text = resp.json().get("response", "")
                else:
                    assistant_text = f"Ollama local service returned status {resp.status_code}. Processing instruction locally..."
        else:
            client = AsyncOpenAI(
                api_key=env_api_key or "sk-dummy-key-for-sandbox",
                base_url=base_url
            )
            res = await client.chat.completions.create(
                model=target_model,
                messages=messages,
                temperature=0.7,
                max_tokens=800
            )
            assistant_text = res.choices[0].message.content or ""
    except Exception as e:
        assistant_text = f"Received instruction: '{prompt}'. Executing utility request..."

    # Extract tool execution
    tool_call = extract_tool_call_fallback(prompt, assistant_text)
    
    if tool_call and tool_call.get("tool") in TOOL_REGISTRY:
        tool_fn = TOOL_REGISTRY[tool_call["tool"]]
        args = tool_call.get("arguments", {})
        try:
            tool_result = await tool_fn(**args)
        except Exception as te:
            tool_result = {"error": f"Tool execution failed: {str(te)}"}
            
    if not assistant_text or "dummy" in assistant_text.lower():
        if tool_result and "message" in tool_result:
            assistant_text = tool_result["message"]
        else:
            assistant_text = f"I've processed your instruction: '{prompt}'."

    return {
        "status": "success",
        "provider": provider,
        "model": target_model,
        "response": assistant_text,
        "tool_call": tool_call,
        "tool_result": tool_result
    }
