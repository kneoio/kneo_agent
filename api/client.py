#!/usr/bin/env python3
import logging
import os

import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class APIClient:
    def __init__(self, base_url=None, api_key=None, timeout=None):
        self.base_url = base_url or os.getenv("API_BASE_URL")
        self.api_key = api_key or os.getenv("API_KEY")
        self.timeout = timeout or int(os.getenv("API_TIMEOUT", "10"))
        self.logger = logging.getLogger(__name__)

    def _get_headers(self):
        headers = {'Content-Type': 'application/json'}
        if self.api_key:
            headers['Authorization'] = f'Bearer {self.api_key}'
        return headers

    def get(self, endpoint, params=None):
        url = f"{self.base_url}/{endpoint}"
        try:
            response = requests.get(
                url,
                headers=self._get_headers(),
                params=params,
                timeout=self.timeout
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
                timeout=self.timeout
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
                timeout=self.timeout
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            self.logger.error(f"API PUT request failed: {e}")
            return None

    def delete(self, endpoint, params=None):
        url = f"{self.base_url}/{endpoint}"
        try:
            response = requests.delete(
                url,
                headers=self._get_headers(),
                params=params,
                timeout=self.timeout
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            self.logger.error(f"API DELETE request failed: {e}")
            return None