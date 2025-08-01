import logging
import json
import requests


class BroadcasterAPIClient:
    def __init__(self, config):
        self.base_url = config.get_by_type("broadcaster").get_by_type("api_base_url")
        self.api_key = config.get_by_type("broadcaster").get_by_type("api_key")
        self.api_timeout = config.get_by_type("broadcaster").get_by_type("api_timeout")
        self.logger = logging.getLogger(__name__)

    def _get_headers(self):
        headers = {'Content-Type': 'application/json'}
        if self.api_key:
            headers['Authorization'] = f'Bearer {self.api_key}'
        return headers

    def get(self, endpoint, params=None):
        url = f"{self.base_url}/{endpoint}"
        self.logger.info(f"Making GET request to: {url} with params {params}")
        try:
            response = requests.get(
                url,
                headers=self._get_headers(),
                params=params,
                timeout=self.api_timeout
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            self.logger.error(f"API GET request failed: {e}")
            return None

    def post(self, endpoint, data):
        url = f"{self.base_url}/{endpoint}"
        try:
            response = requests.post(
                url,
                headers=self._get_headers(),
                json=data,
                timeout=self.api_timeout
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            self.logger.error(f"API POST request failed: {e}")
            return None

    def put(self, endpoint, data):
        url = f"{self.base_url}/{endpoint}"
        try:
            response = requests.put(
                url,
                headers=self._get_headers(),
                json=data,
                timeout=self.api_timeout
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            self.logger.error(f"API PUT request failed: {e}")
            return None

    def patch(self, endpoint, data):
        url = f"{self.base_url}/{endpoint}"
        try:
            response = requests.patch(
                url,
                headers=self._get_headers(),
                json=data,
                timeout=self.api_timeout
            )
            response.raise_for_status()
            try:
                return response.json()
            except json.JSONDecodeError:
                self.logger.info(
                    f"API PATCH request to {url} successful (Status: {response.status_code}), but no JSON content.")
                return {}
        except requests.exceptions.RequestException as e:
            self.logger.error(f"API PATCH request failed: {e}")
            return None

    def delete(self, endpoint, params=None):
        url = f"{self.base_url}/{endpoint}"
        try:
            response = requests.delete(
                url,
                headers=self._get_headers(),
                params=params,
                timeout=self.api_timeout
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            self.logger.error(f"API DELETE request failed: {e}")
            return None
