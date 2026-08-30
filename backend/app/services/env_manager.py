"""
env_manager.py — Environment Variable & .env File Persistence Service
======================================================================
Ensures API keys, provider tokens, SMTP settings, and platform credentials
fed via the admin dashboard or settings are:
  1. Instantly injected into the active running Python process (os.environ)
  2. Persisted to all .env files (backend/.env and root .env) so restarts load them
"""

import os
from pathlib import Path
from typing import Dict, List


def get_env_file_paths() -> List[Path]:
    """
    Return all valid .env file paths in the workspace.
    Ensures both backend/.env and root .env are discovered and written to.
    """
    base_file = Path(__file__).resolve()
    # base_file: backend/app/services/env_manager.py
    # parents[2]: backend/
    # parents[3]: workspace root /
    candidates = [
        base_file.parents[2] / ".env",
        base_file.parents[3] / ".env" if len(base_file.parents) > 3 else None,
        Path.cwd() / ".env",
        Path.cwd() / "backend" / ".env",
    ]

    seen = set()
    paths = []
    for c in candidates:
        if c is not None:
            try:
                resolved = c.resolve()
                if resolved not in seen:
                    seen.add(resolved)
                    paths.append(resolved)
            except Exception:
                pass

    return paths


def read_env_file() -> Dict[str, str]:
    """Read key-value pairs from the primary .env file."""
    env_data: Dict[str, str] = {}
    for env_path in get_env_file_paths():
        if env_path.exists():
            try:
                with open(env_path, "r", encoding="utf-8") as f:
                    for line in f:
                        line_stripped = line.strip()
                        if line_stripped and not line_stripped.startswith("#") and "=" in line_stripped:
                            k, v = line_stripped.split("=", 1)
                            env_data[k.strip()] = v.strip().strip("\"'")
            except Exception as e:
                print(f"[EnvManager] Read notice for {env_path}: {e}")
    return env_data


def update_env_file(updates: Dict[str, str]):
    """
    Update both the live os.environ and the persistent .env files.
    """
    if not updates:
        return

    # 1. Update in-memory active environment variables for the running process
    for key, value in updates.items():
        if value is not None:
            val_str = str(value).strip()
            os.environ[key] = val_str

    # 2. Persist to all discovered .env paths
    env_paths = get_env_file_paths()
    if not env_paths:
        env_paths = [Path(__file__).resolve().parents[2] / ".env"]

    for env_path in env_paths:
        try:
            # Ensure parent directory exists
            env_path.parent.mkdir(parents=True, exist_ok=True)

            lines: List[str] = []
            if env_path.exists():
                with open(env_path, "r", encoding="utf-8") as f:
                    lines = f.readlines()

            # Map existing keys to line indices
            key_to_line_idx = {}
            for idx, line in enumerate(lines):
                line_stripped = line.strip()
                if line_stripped and not line_stripped.startswith("#") and "=" in line_stripped:
                    k, _ = line_stripped.split("=", 1)
                    key_to_line_idx[k.strip()] = idx

            for key, value in updates.items():
                if value is None:
                    continue
                val_str = str(value).strip()
                line_content = f"{key}={val_str}\n"

                if key in key_to_line_idx:
                    idx = key_to_line_idx[key]
                    lines[idx] = line_content
                else:
                    if lines and not lines[-1].endswith("\n"):
                        lines[-1] = lines[-1] + "\n"
                    lines.append(line_content)
                    key_to_line_idx[key] = len(lines) - 1

            with open(env_path, "w", encoding="utf-8") as f:
                f.writelines(lines)

            print(f"[EnvManager] Successfully synced {len(updates)} variables to {env_path.name}")
        except Exception as e:
            print(f"[EnvManager] Warning writing to {env_path}: {e}")
