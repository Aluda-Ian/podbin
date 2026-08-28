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

SYSTEM_PROMPT = """You are PodBin Copilot, powered by Google Gemini AI.
You execute user instructions to manage podcasts, edit descriptions, update titles, cut/trim media, generate clips, add captions, schedule distribution, and configure settings.

AVAILABLE TOOLS & INTENTS:
1. edit_description(episode_id, new_description, instruction)
   e.g., "edit description to include key takeaways and guest links", "update show notes"
2. edit_title(episode_id, new_title, instruction)
   e.g., "edit the title to 'The Future of AI'", "make title more punchy"
3. cut_video(episode_id, start_time, end_time, reason)
   e.g., "cut video from 01:20 to 02:45 on EP-1"
4. schedule_video(episode_id, platforms, scheduled_at, caption)
   e.g., "schedule episode EP-1 for TikTok and YouTube tomorrow at 5pm"
5. add_captions(episode_id, burn_in_captions, caption_style)
   e.g., "add animated captions to episode EP-1"
6. generate_clips(episode_id, count, platform)
   e.g., "generate 3 vertical clips for TikTok from EP-1"
7. list_episodes(status_filter)
   e.g., "list all episodes"
8. configure_llm_provider(provider, model_name, api_key)
   e.g., "switch provider to Gemini gemini-1.5-flash"

TOOL EXECUTION FORMAT:
If the user prompt requires a tool action or content edit, include a JSON block in your response formatted as:
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
    
    # Check edit description intent: "edit description to ..."
    if any(w in prompt_lower for w in ["edit description", "update description", "change description", "rewrite description", "edit show notes", "update show notes"]):
        ep_match = re.search(r'(ep-\d+|episodes?-\d+)', prompt_lower)
        ep_id = ep_match.group(1).upper() if ep_match else None
        new_desc = user_prompt
        for kw in ["edit description to", "update description to", "change description to", "rewrite description to", "show notes to"]:
            if kw in prompt_lower:
                new_desc = user_prompt.split(kw, 1)[-1].strip()
                break
        return {
            "tool": "edit_description",
            "arguments": {
                "episode_id": ep_id,
                "new_description": new_desc,
                "instruction": user_prompt
            }
        }

    # Check edit title intent: "edit title to ..."
    if any(w in prompt_lower for w in ["edit title", "update title", "change title", "rename title", "make title"]):
        ep_match = re.search(r'(ep-\d+|episodes?-\d+)', prompt_lower)
        ep_id = ep_match.group(1).upper() if ep_match else None
        new_title = user_prompt
        for kw in ["edit title to", "update title to", "change title to", "rename title to", "title to"]:
            if kw in prompt_lower:
                new_title = user_prompt.split(kw, 1)[-1].strip().strip('"').strip("'")
                break
        return {
            "tool": "edit_title",
            "arguments": {
                "episode_id": ep_id,
                "new_title": new_title,
                "instruction": user_prompt
            }
        }

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
    provider: str = "gemini",
    model: Optional[str] = None,
    api_key: Optional[str] = None,
    context: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Execute Copilot chat prompt using Google Gemini or selected LLM provider and utility tools."""
    
    # Check if Gemini key is available in environment or database
    db_keys = await db.get_api_keys()
    gemini_key = db_keys.get("gemini") or os.getenv("GEMINI_API_KEY", "")

    # Default to gemini if gemini_key is available
    if gemini_key and (provider == "openai" or not provider):
        provider = "gemini"

    p_id = provider.lower().strip()
    provider_info = next((p for p in SUPPORTED_PROVIDERS if p["id"] == p_id), SUPPORTED_PROVIDERS[0])
    target_model = model or provider_info["default_model"]
    base_url = provider_info["base_url"]
    
    if not api_key:
        if p_id in ("openai", "open_ai"):
            api_key = db_keys.get("openai") or os.getenv("OPENAI_API_KEY", "")
        elif p_id in ("anthropic", "claude"):
            api_key = db_keys.get("anthropic") or os.getenv("ANTHROPIC_API_KEY", "")
        elif p_id in ("gemini", "google"):
            api_key = gemini_key
        elif p_id == "deepseek":
            api_key = db_keys.get("deepseek") or os.getenv("DEEPSEEK_API_KEY", "")
        else:
            api_key = db_keys.get(p_id) or os.getenv("OPENAI_API_KEY", "")
    
    env_api_key = api_key
    
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"Context: {json.dumps(context or {})}\n\nInstruction: {prompt}"}
    ]
    
    assistant_text = ""
    tool_result = None
    
    try:
        if p_id in ("gemini", "google") and env_api_key:
            # Execute Gemini 1.5 Flash REST API call
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={env_api_key}"
            user_msg = f"{SYSTEM_PROMPT}\n\nContext: {json.dumps(context or {})}\n\nInstruction: {prompt}"
            payload = {
                "contents": [{"parts": [{"text": user_msg}]}],
                "generationConfig": {"temperature": 0.7, "maxOutputTokens": 1000}
            }
            async with httpx.AsyncClient(timeout=25.0) as client:
                resp = await client.post(url, json=payload, headers={"Content-Type": "application/json"})
                if resp.status_code == 200:
                    g_data = resp.json()
                    try:
                        assistant_text = g_data["candidates"][0]["content"]["parts"][0]["text"]
                    except Exception:
                        assistant_text = f"Gemini processed instruction: '{prompt}'."
                else:
                    print(f"[GEMINI COPILOT ERROR] {resp.status_code}: {resp.text}")
                    assistant_text = f"Received instruction: '{prompt}'. Executing editing utility..."
        elif p_id == "ollama":
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    "http://localhost:11434/api/generate",
                    json={"model": target_model, "prompt": f"{SYSTEM_PROMPT}\n\nUser: {prompt}\n\nAssistant:", "stream": False},
                    timeout=30.0
                )
                if resp.status_code == 200:
                    assistant_text = resp.json().get("response", "")
                else:
                    assistant_text = f"Ollama service returned status {resp.status_code}. Processing instruction locally..."
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
        print(f"[COPILOT CHAT ERROR] {e}")
        assistant_text = f"Received instruction: '{prompt}'. Executing utility request..."

    # Extract and execute tool invocation
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
