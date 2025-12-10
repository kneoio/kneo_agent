import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)


class FineTuneLogger:
    _instance: Optional['FineTuneLogger'] = None
    _output_dir: Path = Path("finetune_data")

    def __init__(self, output_dir: Optional[str] = None):
        if output_dir:
            self._output_dir = Path(output_dir)
        self._output_dir.mkdir(parents=True, exist_ok=True)

    @classmethod
    def get_instance(cls, output_dir: Optional[str] = None) -> 'FineTuneLogger':
        if cls._instance is None:
            cls._instance = cls(output_dir)
        return cls._instance

    def _get_file_path(self, llm_type: str, function_name: str) -> Path:
        date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        filename = f"{llm_type.lower()}_{function_name}_{date_str}.jsonl"
        return self._output_dir / filename

    def log_interaction(
        self,
        function_name: str,
        llm_type: str,
        messages: list,
        response_content: str,
        tools: Optional[list] = None,
        tool_calls: Optional[list] = None,
        tool_results: Optional[list] = None,
        reasoning: Optional[str] = None,
        thinking: Optional[str] = None,
        metadata: Optional[dict] = None
    ) -> None:
        try:
            record = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "function": function_name,
                "llm_type": llm_type,
                "messages": self._sanitize_messages(messages),
                "response": response_content,
            }

            if tools:
                record["tools"] = self._sanitize_tools(tools)
            if tool_calls:
                record["tool_calls"] = self._sanitize_tool_calls(tool_calls)
            if tool_results:
                record["tool_results"] = tool_results
            if reasoning:
                record["reasoning"] = reasoning
            if thinking:
                record["thinking"] = thinking
            if metadata:
                record["metadata"] = metadata

            file_path = self._get_file_path(llm_type, function_name)
            with open(file_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(record, ensure_ascii=False) + "\n")

            logger.debug(f"FineTuneLogger: logged interaction to {file_path}")
        except Exception as e:
            logger.error(f"FineTuneLogger: failed to log interaction: {e}")

    def _sanitize_messages(self, messages: list) -> list:
        sanitized = []
        for msg in messages or []:
            if isinstance(msg, dict):
                clean = {
                    "role": msg.get("role"),
                    "content": msg.get("content")
                }
                if msg.get("tool_calls"):
                    clean["tool_calls"] = self._sanitize_tool_calls(msg["tool_calls"])
                if msg.get("tool_call_id"):
                    clean["tool_call_id"] = msg["tool_call_id"]
                if msg.get("name"):
                    clean["name"] = msg["name"]
                sanitized.append(clean)
            else:
                sanitized.append({"raw": str(msg)})
        return sanitized

    def _sanitize_tools(self, tools: list) -> list:
        sanitized = []
        for tool in tools or []:
            if isinstance(tool, dict):
                sanitized.append(tool)
            else:
                sanitized.append({"raw": str(tool)})
        return sanitized

    def _sanitize_tool_calls(self, tool_calls: list) -> list:
        sanitized = []
        for tc in tool_calls or []:
            if isinstance(tc, dict):
                if "function" in tc:
                    fn = tc.get("function") or {}
                    sanitized.append({
                        "id": tc.get("id"),
                        "name": fn.get("name"),
                        "arguments": fn.get("arguments")
                    })
                else:
                    sanitized.append({
                        "id": tc.get("id") or tc.get("tool_call_id"),
                        "name": tc.get("name"),
                        "arguments": tc.get("arguments") or tc.get("args")
                    })
            else:
                try:
                    sanitized.append({
                        "id": tc.id,
                        "name": tc.function.name,
                        "arguments": tc.function.arguments
                    })
                except Exception:
                    sanitized.append({"raw": str(tc)})
        return sanitized


def get_finetune_logger(output_dir: Optional[str] = None) -> FineTuneLogger:
    return FineTuneLogger.get_instance(output_dir)
