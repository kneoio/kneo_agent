from typing import List, Dict, Any

from cnst.llm_types import LlmType
from llm.llm_request import invoke_chat
from rest.app_setup import llm_factory
from util.template_loader import render_template


async def run_mixplaclone_chat(brand: str, text: str, llm_choice: LlmType, history: List[Dict[str, str]] | None = None) -> str:
    system_prompt = render_template("chat/mixplaclone_system.hbs", {"brand": brand})
    messages: List[Dict[str, str]] = [{"role": "system", "content": system_prompt}]
    if history:
        for h in history[-19:]:
            role = "assistant" if h.get("role") == "assistant" else "user"
            content = h.get("text", "")
            if content:
                messages.append({"role": role, "content": content})
    messages.append({"role": "user", "content": text})
    client = llm_factory.get_llm_client(llm_choice, enable_sound_fragment_tool=True)
    result = await invoke_chat(llm_client=client, messages=messages)
    return result.actual_result
