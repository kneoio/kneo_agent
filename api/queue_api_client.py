import asyncio
import json
import time
from typing import Any, AsyncIterator, Dict, Optional

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
        timeout = httpx.Timeout(30.0, connect=10.0)
        async with httpx.AsyncClient(timeout=timeout) as c:
            r = await c.post(url, params=params, headers=self._headers(), json=payload)
            r.raise_for_status()
            try:
                return r.json()
            except json.JSONDecodeError:
                return {}

    async def stream_progress(self, brand: str, process_id: str) -> AsyncIterator[Dict[str, Any]]:
        url = f"{self.base_url}/{brand}/queue/progress/{process_id}/stream"
        headers = self._headers({"Accept": "text/event-stream"})
        async with httpx.AsyncClient(timeout=None) as c:
            async with c.stream("GET", url, headers=headers) as r:
                async for line in r.aiter_lines():
                    if not line:
                        continue
                    if line.startswith("data:"):
                        data = line[5:].strip()
                        try:
                            obj = json.loads(data)
                            yield obj
                        except Exception:
                            yield {"data": data}

    async def wait_until_done(self, brand: str, process_id: str, timeout_s: Optional[int] = 600) -> Optional[
        Dict[str, Any]]:
        start = time.time()
        last: Optional[Dict[str, Any]] = None
        async for ev in self.stream_progress(brand, process_id):
            last = ev
            status = ev.get("status")
            if status in ("DONE", "ERROR"):
                break
            if timeout_s is not None and (time.time() - start) > timeout_s:
                break
            await asyncio.sleep(0)
        return last
    
    async def check_process_status(self, brand: str, process_id: str, timeout_s: int = 5) -> Optional[str]:
        try:
            start = time.time()
            async for ev in self.stream_progress(brand, process_id):
                status = ev.get("status")
                if status:
                    return status
                if (time.time() - start) > timeout_s:
                    break
            return None
        except Exception:
            return None
