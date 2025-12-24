import logging
import json
import httpx


class BroadcasterAPIClient:
    def __init__(self, config):
        self.base_url = config.get("broadcaster").get("api_base_url")
        self.api_key = config.get("broadcaster").get("api_key")
        self.api_timeout = config.get("broadcaster").get("api_timeout")
        self.logger = logging.getLogger(__name__)

    def _get_headers(self):
        headers = {'Content-Type': 'application/json'}
        if self.api_key:
            headers['Authorization'] = f'Bearer {self.api_key}'
        return headers

    async def get(self, endpoint, params=None):
        url = f"{self.base_url}/{endpoint}"
        try:
            timeout = httpx.Timeout(self.api_timeout if self.api_timeout else 30.0)
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.get(
                    url,
                    headers=self._get_headers(),
                    params=params
                )
                response.raise_for_status()
                json_data = response.json()
                self.logger.debug(f"API GET response from {url}: {json_data}")
                return json_data
        except json.JSONDecodeError as e:
            self.logger.error(f"API GET request to {url} returned invalid JSON: {e}")
            return None
        except httpx.HTTPError as e:
            self.logger.error(f"API GET request to {url} failed: {e}")
            return None

    async def post(self, endpoint, data):
        url = f"{self.base_url}/{endpoint}"
        try:
            timeout = httpx.Timeout(self.api_timeout if self.api_timeout else 30.0)
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.post(
                    url,
                    headers=self._get_headers(),
                    json=data
                )
                response.raise_for_status()
                return response.json()
        except httpx.HTTPError as e:
            self.logger.error(f"API POST request to {url} failed: {e}")
            return None

    async def put(self, endpoint, data):
        url = f"{self.base_url}/{endpoint}"
        try:
            timeout = httpx.Timeout(self.api_timeout if self.api_timeout else 30.0)
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.put(
                    url,
                    headers=self._get_headers(),
                    json=data
                )
                response.raise_for_status()
                return response.json()
        except httpx.HTTPError as e:
            self.logger.error(f"API PUT request to {url} failed: {e}")
            return None

    async def patch(self, endpoint, data):
        url = f"{self.base_url}/{endpoint}"
        try:
            timeout = httpx.Timeout(self.api_timeout if self.api_timeout else 30.0)
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.patch(
                    url,
                    headers=self._get_headers(),
                    json=data
                )
                response.raise_for_status()
                try:
                    return response.json()
                except json.JSONDecodeError:
                    self.logger.info(
                        f"API PATCH request to {url} successful (Status: {response.status_code}), but no JSON content.")
                    return {}
        except httpx.HTTPError as e:
            self.logger.error(f"API PATCH request to {url} failed: {e}")
            return None

    async def delete(self, endpoint, params=None):
        url = f"{self.base_url}/{endpoint}"
        try:
            timeout = httpx.Timeout(self.api_timeout if self.api_timeout else 30.0)
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.delete(
                    url,
                    headers=self._get_headers(),
                    params=params
                )
                response.raise_for_status()
                return response.json()
        except httpx.HTTPError as e:
            self.logger.error(f"API DELETE request to {url} failed: {e}")
            return None

    async def close(self):
        if hasattr(self, '_client'):
            await self._client.aclose()
