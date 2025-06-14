import logging
from typing import Dict, Any, List, Optional
from api.broadcaster_client import BroadcasterAPIClient

class EnvironmentProfileAPI:
    def __init__(self, config: Dict[str, Any] = None):
        self.logger = logging.getLogger(__name__)
        self.api_client = BroadcasterAPIClient()

    def get_profiles(self) -> List[Dict[str, Any]]:
        endpoint = "profiles"
        response = self.api_client.get(endpoint)
        if response and "payload" in response:
            return response["payload"].get("viewData", {}).get("entries", [])
        return []

    def get_station_profile(self, station_id: str) -> Optional[Dict[str, Any]]:
        endpoint = f"radiostations/{station_id}"
        response = self.api_client.get(endpoint)
        if response and "payload" in response:
            return response["payload"].get("profile")
        return None

    def get_profile(self, profile_id: str) -> Optional[Dict[str, Any]]:
        endpoint = f"radiostations/{profile_id}"
        response = self.api_client.get(endpoint)
        if response and "payload" in response:
            return response["payload"]
        return None

    def create_profile(self, profile_data: Dict[str, Any]) -> bool:
        endpoint = "profiles"
        response = self.api_client.post(endpoint, profile_data)
        if response and response.get("success"):
            self.logger.info(f"Created new environment profile: {profile_data.get('name')}")
            return True
        return False

    def update_profile(self, profile_id: str, profile_data: Dict[str, Any]) -> bool:
        endpoint = f"profiles/{profile_id}"
        response = self.api_client.put(endpoint, profile_data)
        if response and response.get("success"):
            self.logger.info(f"Updated environment profile: {profile_data.get('name')}")
            return True
        return False

    def delete_profile(self, profile_id: str) -> bool:
        """Delete a profile"""
        endpoint = f"profiles/{profile_id}"
        response = self.api_client.delete(endpoint)
        if response and response.get("success"):
            self.logger.info(f"Deleted environment profile with ID: {profile_id}")
            return True
        return False

    def assign_profile_to_station(self, station_id: str, profile_id: str) -> bool:
        endpoint = f"radiostations/{station_id}/profile"
        data = {"profileId": profile_id}
        response = self.api_client.put(endpoint, data)
        if response and response.get("success"):
            self.logger.info(f"Assigned profile {profile_id} to station {station_id}")
            return True
        return False