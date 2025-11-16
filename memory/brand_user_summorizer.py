import json
from cnst.llm_types import LlmType
from llm.llm_request import invoke_intro

class BrandUserSummarizer:
    def __init__(self, db_pool, llm_client, llm_type=LlmType.GROQ):
        self.db = db_pool
        self.llm = llm_client
        self.llm_type = llm_type

    async def summarize(self, brand: str):
        async with self.db.acquire() as conn:
            rows = await conn.fetch(
                "SELECT history FROM mixpla__user_memory WHERE brand = $1",
                brand
            )

        texts = []
        for r in rows:
            h = r["history"]
            if isinstance(h, str):
                try:
                    h = json.loads(h)
                except Exception:
                    h = []
            if isinstance(h, list):
                for item in h:
                    if isinstance(item, dict) and "text" in item:
                        texts.append(item["text"])

        if not texts:
            return ""

        merged = "\n".join(texts)

        prompt = (
            "Summarize all listener messages into one short description: "
            "mood, requests, themes, sentiments. Output plain text."
        )

        result = await invoke_intro(self.llm, prompt, merged, self.llm_type)
        return result.actual_result
