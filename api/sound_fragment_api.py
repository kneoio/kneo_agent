import logging
from typing import Optional, Dict, Any

import httpx


class BrandSoundFragmentsAPI:
    def __init__(self, config):
        broadcaster = config.get("broadcaster", {})
        self.api_base_url = broadcaster.get("api_base_url")
        self.api_key = broadcaster.get("api_key")
        self.api_timeout = broadcaster.get("api_timeout", 60)
        self.logger = logging.getLogger(__name__)

    async def search(self, brand: str, keyword: Optional[str] = None, limit: Optional[int] = None, offset: Optional[int] = None) -> Dict[str, Any]:
        if not self.api_base_url:
            raise ValueError("API base URL not configured")
        
        params = {}
        if keyword and keyword.strip():
            params["keyword"] = keyword.strip()
        if limit is not None:
            params["limit"] = limit
        if offset is not None:
            params["offset"] = offset
        
        url = f"{self.api_base_url}/ai/brand/{brand}/soundfragments"
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        
        try:
            async with httpx.AsyncClient(timeout=self.api_timeout) as client:
                response = await client.get(url, params=params, headers=headers)
                response.raise_for_status()
                return response.json()
        except httpx.HTTPStatusError as e:
            self.logger.error(f"HTTP error searching sound fragments: {e.response.status_code} - {e.response.text}")
            raise RuntimeError(f"API returned error {e.response.status_code} for brand {brand}")
        except Exception as e:
            self.logger.error(f"Error calling /api/ai/brand/{brand}/soundfragments: {e}")
            raise

