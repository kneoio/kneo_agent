import json
from typing import Any, Dict, Optional

import httpx


class QueueAPIClient:
    def __init__(self, config: Dict[str, Any]):
        b = config.get("broadcaster", {})
        self.base_url = b.get("api_base_url")
        self.api_key = b.get("api_key")
        self.timeout = b.get("api_timeout")

    def _headers(self, extra: Optional[Dict[str, str]] = None) -> Dict[str, str]:
        h = {"Content-Type": "application/json"}
        if self.api_key:
            h["Authorization"] = f"Bearer {self.api_key}"
        if extra:
            h.update(extra)
        return h

    async def enqueue_add(self, brand: str, process_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        url = f"{self.base_url}/{brand}/queue/add"
        params = {"processId": process_id}
        timeout = httpx.Timeout(60.0, connect=10.0)
        async with httpx.AsyncClient(timeout=timeout) as c:
            r = await c.post(url, params=params, headers=self._headers(), json=payload)
            r.raise_for_status()
            try:
                return r.json()
            except json.JSONDecodeError:
                return {}

