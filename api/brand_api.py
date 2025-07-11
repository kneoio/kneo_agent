import logging
from typing import Dict, Any, List, Optional
from api.broadcaster_client import BroadcasterAPIClient
from models.brand import Profile


class BrandAPI:
    def __init__(self, config: Dict[str, Any] = None):
        self.logger = logging.getLogger(__name__)
        self.api_client = BroadcasterAPIClient()

    def get_all_brands(self) -> Dict[str, Any]:
        response = self.api_client.get("radiostations")
        if not response or "payload" not in response:
            self.logger.error("Failed to retrieve brands or invalid response format")
            return {"payload": {"viewData": {"entries": []}}}
        return response

    def get_brand_profile(self, brand_id: str) -> Optional[Dict[str, Any]]:
        response = self.api_client.get(f"brands/{brand_id}/profile")
        if response and "profile" in response:
            return response.get("profile")
        return None

    def update_brand_profile(self, brand_id: str, profile_id: str) -> bool:
        response = self.api_client.post(
            f"brands/{brand_id}/profile",
            data={"profileId": profile_id}
        )
        success = response and response.get("success", False)
        if success:
            self.logger.info(f"Updated brand {brand_id} profile to {profile_id}")
        else:
            self.logger.error(f"Failed to update brand {brand_id} profile")
        return success

    def get_available_profiles(self) -> List[Profile]:
        response = self.api_client.get("profiles")
        profiles = []

        if response and "profiles" in response:
            for profile_data in response.get("profiles", []):
                profiles.append(Profile.from_dict(profile_data))

        return profiles