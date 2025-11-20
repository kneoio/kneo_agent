import datetime
from cnst.llm_types import LlmType
from llm.llm_request import invoke_intro
from llm.llm_response import LlmResponse


class BrandSummarizer:
    def __init__(self, llm_client, db_pool, memory_manager, llm_type=LlmType.GROQ):
        self.llm = llm_client
        self.db = db_pool
        self.memory_manager = memory_manager
        self.llm_type = llm_type

    async def summarize(self, brand: str):
        raw_items = self.memory_manager.get(brand)
        raw_text = "\n".join(raw_items)

        prompt = (
            "Summarize the following on-air DJ history into a compact JSON with keys: "
            "mood, topics, active_listeners, highlights. Keep it short.\n\n"
            f"{raw_text}"
        )

        raw_response = await invoke_intro(self.llm, prompt, "", "")
        summary = LlmResponse.parse_plain_response(raw_response, self.llm_type)
        summary_json = summary.actual_result

        async with self.db.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO mixpla__brand_memory (last_mod_date, brand, day, summary)
                VALUES (NOW(), $1, $2, $3)
                ON CONFLICT (brand, day)
                DO UPDATE SET
                    last_mod_date = NOW(),
                    summary = EXCLUDED.summary;
                """,
                brand,
                datetime.date.today(),
                summary_json
            )

        return summary_json
