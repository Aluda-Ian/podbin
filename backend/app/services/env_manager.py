import os
from pathlib import Path
from typing import Dict

def get_env_file_path() -> Path:
    # __file__ is backend/app/services/env_manager.py
    # parents[2] is backend/
    return Path(__file__).resolve().parents[2] / ".env"

def read_env_file() -> Dict[str, str]:
    env_path = get_env_file_path()
    env_data = {}
    if not env_path.exists():
        return env_data

    with open(env_path, "r", encoding="utf-8") as f:
        for line in f:
            line_stripped = line.strip()
            if line_stripped and not line_stripped.startswith("#") and "=" in line_stripped:
                k, v = line_stripped.split("=", 1)
                env_data[k.strip()] = v.strip()
    return env_data

def update_env_file(updates: Dict[str, str]):
    env_path = get_env_file_path()
    lines = []
    if env_path.exists():
        with open(env_path, "r", encoding="utf-8") as f:
            lines = f.readlines()

    # Map key to their line indices
    key_to_line_idx = {}
    for idx, line in enumerate(lines):
        line_stripped = line.strip()
        if line_stripped and not line_stripped.startswith("#") and "=" in line_stripped:
            k, _ = line_stripped.split("=", 1)
            key_to_line_idx[k.strip()] = idx

    for key, value in updates.items():
        # Update in-memory active environment variables for the running process
        os.environ[key] = value

        line_content = f"{key}={value}\n"
        if key in key_to_line_idx:
            idx = key_to_line_idx[key]
            lines[idx] = line_content
        else:
            # Append a newline if the file doesn't end with one
            if lines and not lines[-1].endswith("\n"):
                lines[-1] = lines[-1] + "\n"
            lines.append(line_content)

    with open(env_path, "w", encoding="utf-8") as f:
        f.writelines(lines)
