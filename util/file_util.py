import json
from pathlib import Path
from typing import Any


def load_external_prompts(agent_config):
    try:
        decision_prompt_path = Path("prompts/decision_prompt.json")
        if decision_prompt_path.exists():
            with open(decision_prompt_path, 'r', encoding='utf-8') as f:
                decision_data = json.load(f)
                agent_config["decision_prompt"] = decision_data.get_by_type("prompt", agent_config.get_by_type("decision_prompt", ""))
            debug_log(f"Loaded decision_prompt from {decision_prompt_path}")
        else:
            debug_log(f"Decision prompt file not found: {decision_prompt_path}")

        song_prompt_path = Path("prompts/song_prompt.json")
        if song_prompt_path.exists():
            with open(song_prompt_path, 'r', encoding='utf-8') as f:
                song_data = json.load(f)
                agent_config["prompt"] = song_data.get_by_type("prompt", agent_config.get_by_type("prompt", ""))
            debug_log(f"Loaded song_prompt from {song_prompt_path}")
        else:
            debug_log(f"Song prompt file not found: {song_prompt_path}")

    except Exception as e:
        debug_log(message=f"Failed to load external prompts, using defaults")


def debug_log(message: str, data: Any = None):
    if data is not None:
        print(f"[DEBUG] {message}: {data}")
    else:
        print(f"[DEBUG] {message}")
