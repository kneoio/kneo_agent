import json

class UserMemoryManager:
    def __init__(self, db_pool):
        self.db = db_pool

    async def load(self, user_id: int):
        async with self.db.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT user_id, telegram_name, brand, history FROM mixpla__user_memory WHERE user_id = $1",
                user_id
            )
            if not row:
                return None
            d = dict(row)
            h = d.get("history")
            if isinstance(h, str):
                try:
                    d["history"] = json.loads(h)
                except Exception:
                    d["history"] = []
            return d

    async def save(self, user_id: int, telegram_name: str, brand: str, history):
        async with self.db.acquire() as conn:
            updated = await conn.fetchval(
                """
                UPDATE mixpla__user_memory
                SET last_mod_date = NOW(),
                    telegram_name = $2,
                    brand = $3,
                    history = $4
                WHERE user_id = $1
                RETURNING 1
                """,
                user_id, telegram_name, brand, json.dumps(history)
            )
            if not updated:
                await conn.execute(
                    """
                    INSERT INTO mixpla__user_memory (last_mod_date, user_id, telegram_name, brand, history)
                    VALUES (NOW(), $1, $2, $3, $4)
                    """,
                    user_id, telegram_name, brand, json.dumps(history)
                )

    async def add(self, user_id: int, telegram_name: str, brand: str, text: str):
        data = await self.load(user_id)
        history = data["history"] if data else []
        history.append({"role": "user", "text": text})
        if len(history) > 50:
            history = history[-50:]
        await self.save(user_id, telegram_name, brand, history)

    async def summarize(self, user_id: int, llm_client, llm_type):
        data = await self.load(user_id)
        if not data or not data["history"]:
            return ""

        text = "\n".join([h["text"] for h in data["history"]])

        prompt = (
            "Summarize the listener's recent messages into a short description of mood, intent, "
            "preferences and ongoing topics. Output plain text."
        )

        from llm.llm_request import invoke_intro
        from llm.llm_response import LlmResponse
        raw_response = await invoke_intro(llm_client, prompt, text, "")
        summary = LlmResponse.parse_plain_response(raw_response, llm_type)
        return summary.actual_result

    async def get_all(self):
        async with self.db.acquire() as conn:
            rows = await conn.fetch(
                "SELECT user_id, telegram_name, brand, history FROM mixpla__user_memory"
            )
        result = []
        for row in rows:
            d = dict(row)
            h = d.get("history")
            if isinstance(h, str):
                try:
                    d["history"] = json.loads(h)
                except Exception:
                    d["history"] = []
            result.append(d)
        return result

    async def clear(self, user_id: int):
        async with self.db.acquire() as conn:
            await conn.execute("DELETE FROM mixpla__user_memory WHERE user_id = $1", user_id)

    async def clear_all(self):
        async with self.db.acquire() as conn:
            await conn.execute("DELETE FROM mixpla__user_memory")
    
    async def get_all_active_chats(self):
        async with self.db.acquire() as conn:
            rows = await conn.fetch(
                "SELECT user_id, last_mod_date FROM mixpla__user_memory WHERE history IS NOT NULL"
            )
        return [(row["user_id"], row["last_mod_date"]) for row in rows]
