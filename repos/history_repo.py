from typing import Any, List, Tuple

class HistoryRepository:
    def __init__(self, user_memory_manager):
        self.user_memory = user_memory_manager

    async def build_messages(self, chat_id: int, system_prompt: str) -> Tuple[List[dict], list, Any]:
        data_state = await self.user_memory.load(chat_id)
        history = data_state["history"] if data_state else []
        messages = [{"role": "system", "content": system_prompt}]
        for h in history[-19:]:
            role = h.get("role")
            if role == "user":
                content = h.get("text", "")
                if content:
                    messages.append({"role": "user", "content": content})
            elif role == "assistant":
                content = h.get("text", "")
                tool_calls = h.get("tool_calls")
                if content or tool_calls:
                    messages.append({"role": "assistant", "content": content or "", "tool_calls": tool_calls})
            elif role == "tool":
                messages.append({
                    "role": "tool",
                    "name": h.get("name"),
                    "content": h.get("content", ""),
                    "tool_call_id": h.get("tool_call_id")
                })
        return messages, history, data_state

    async def update_from_result(self, chat_id: int, name: str, brand: str, existing_history: list, result, fallback_user_text: str | None = None) -> list:
        reply = result.actual_result if hasattr(result, "actual_result") else ""
        if getattr(result, "full_messages", None):
            new_history = []
            for msg in result.full_messages:
                role = msg.get("role")
                if role == "system":
                    continue
                if role == "user":
                    new_history.append({"role": "user", "text": msg.get("content", "")})
                elif role == "assistant":
                    new_history.append({"role": "assistant", "text": msg.get("content", ""), "tool_calls": msg.get("tool_calls")})
                elif role == "tool":
                    new_history.append({"role": "tool", "name": msg.get("name"), "content": msg.get("content"), "tool_call_id": msg.get("tool_call_id")})
            if existing_history:
                existing_history.extend(new_history)
                history = existing_history[-50:]
            else:
                history = new_history
        else:
            if existing_history:
                existing_history.extend([{"role": "user", "text": fallback_user_text or ""}, {"role": "assistant", "text": reply}])
                history = existing_history[-50:]
            else:
                history = [{"role": "user", "text": fallback_user_text or ""}, {"role": "assistant", "text": reply}]
        await self.user_memory.save(chat_id, name, brand, history)
        return history

    async def clear(self, chat_id: int):
        await self.user_memory.clear(chat_id)
