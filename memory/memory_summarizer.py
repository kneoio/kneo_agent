import logging
from datetime import datetime, UTC, date
from typing import Dict, Any, List, Optional

from llm.llm_response import LlmResponse
from repos.brand_memory_repo import brand_memory_repo
from util.template_loader import render_template


class MemorySummarizer:
    def __init__(self, llm_client, llm_type):
        self.llm_client = llm_client
        self.llm_type = llm_type
        self.logger = logging.getLogger(__name__)

    async def summarize_brand_memory(self, brand: str, memory_entries: List[Dict[str, Any]]) -> Optional[
        Dict[str, Any]]:
        if not memory_entries:
            return None

        memory_texts = [entry["text"] for entry in memory_entries if isinstance(entry, dict) and "text" in entry]
        if not memory_texts:
            return None

        raw_mem = "\n".join(memory_texts)

        prompt = render_template("summarizer/memory_summary.hbs", {
            "brand": brand,
            "memoryText": raw_mem
        })

        try:
            messages = [
                {"role": "system", "content": "You are a memory summarization assistant."},
                {"role": "user", "content": prompt}
            ]
            raw_response = await self.llm_client.invoke(messages=messages)
            response = LlmResponse.parse_plain_response(raw_response, self.llm_type)

            summary_data = {
                "summary": response.actual_result,
                "entry_count": len(memory_entries),
                "summarized_at": datetime.now(UTC).isoformat(timespec="seconds"),
                "oldest_entry": min(entry["t"] for entry in memory_entries),
                "newest_entry": max(entry["t"] for entry in memory_entries)
            }

            return summary_data

        except Exception as e:
            self.logger.error(f"Error summarizing memory for brand {brand}: {e}")
            return None

    async def save_summary(self, brand: str, summary_data: Dict[str, Any]) -> bool:
        try:
            today = date.today()
            existing = await brand_memory_repo.get(brand, today)

            if existing:
                merged_summary = existing.summary.copy()
                merged_summary.update(summary_data)
                merged_summary["last_updated"] = datetime.now(UTC).isoformat(timespec="seconds")

                await brand_memory_repo.update(brand, today, merged_summary)
            else:
                await brand_memory_repo.insert(brand, today, summary_data)

            return True

        except Exception as e:
            self.logger.error(f"Error saving summary for brand {brand}: {e}")
            return False
