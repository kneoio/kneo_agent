#!/usr/bin/env python3
import logging
from typing import Dict, Any, List, Optional
from api.client import APIClient


class EnvironmentProfileAPI:
    def __init__(self, config: Dict[str, Any]):
        self.logger = logging.getLogger(__name__)
        self.api_client = APIClient(
            base_url=config.get("api_base_url", "http://localhost:8000"),
            api_key=config.get("api_key"),
            timeout=config.get("timeout", 10)
        )

    def get_profiles(self, brand_id: str = None) -> Dict[str, Dict[str, Any]]:
        endpoint = f"brands/{brand_id}/profiles" if brand_id else "brands/current/profiles"
        response = self.api_client.get(endpoint)
        if response:
            return response.get("profiles", {})
        return {}

    def get_profile(self, profile_name: str, brand_id: str = None) -> Optional[Dict[str, Any]]:
        endpoint = f"brands/{brand_id}/profiles/{profile_name}" if brand_id else f"brands/current/profiles/{profile_name}"
        response = self.api_client.get(endpoint)
        if response:
            return response.get("profile")
        return None

    def create_profile(self, profile_name: str, profile_data: Dict[str, Any], brand_id: str = None) -> bool:
        endpoint = f"brands/{brand_id}/profiles" if brand_id else "brands/current/profiles"
        data = {"name": profile_name, "profile": profile_data}
        response = self.api_client.post(endpoint, data)
        if response and response.get("success"):
            self.logger.info(f"Created new environment profile: {profile_name}")
            return True
        return False

    def update_profile(self, profile_name: str, profile_data: Dict[str, Any], brand_id: str = None) -> bool:
        endpoint = f"brands/{brand_id}/profiles/{profile_name}" if brand_id else f"brands/current/profiles/{profile_name}"
        data = {"profile": profile_data}
        response = self.api_client.put(endpoint, data)
        if response and response.get("success"):
            self.logger.info(f"Updated environment profile: {profile_name}")
            return True
        return False

    def delete_profile(self, profile_name: str, brand_id: str = None) -> bool:
        endpoint = f"brands/{brand_id}/profiles/{profile_name}" if brand_id else f"brands/current/profiles/{profile_name}"
        response = self.api_client.delete(endpoint)
        if response and response.get("success"):
            self.logger.info(f"Deleted environment profile: {profile_name}")
            return True
        return False