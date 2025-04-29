import logging
from typing import Dict, Any, List, Optional
from api.broadcaster_client import BroadcasterAPIClient

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

    def get_brand(self, brand_identifier=None):
        if isinstance(brand_identifier, str):
            from simple_brand import SimpleBrand
            return SimpleBrand(brand_identifier)
        return None

#    def get_brand(self, brand_id: str) -> Optional[Brand]:
#        """Get details for a specific brand as a Brand object."""
#        response = self.api_client.get(f"brands/{brand_id}")
#        if not response or "brand" not in response:
#            self.logger.error(f"Failed to retrieve brand {brand_id}")
#            return None

#       brand_data = response.get("brand")
#       # Get profile data
#        profile_data = self.get_brand_profile(brand_id)
#        if profile_data:
#            brand_data["profile"] = profile_data

 #       return Brand.from_dict(brand_data)

    def get_brand_profile(self, brand_id: str) -> Optional[Dict[str, Any]]:
        """Get current profile for a brand."""
        response = self.api_client.get(f"brands/{brand_id}/profile")
        if response and "profile" in response:
            return response.get("profile")
        return None

    def update_brand_profile(self, brand_id: str, profile_id: str) -> bool:
        """Update a brand's profile."""
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
        """Get all available profiles."""
        response = self.api_client.get("profiles")
        profiles = []

        if response and "profiles" in response:
            for profile_data in response.get("profiles", []):
                profiles.append(Profile.from_dict(profile_data))

        return profiles