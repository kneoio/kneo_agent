#!/usr/bin/env python3
import logging
from typing import Dict, Any, Optional


class BrandContext:

    def __init__(self, brand_id: str, brand_config: Dict[str, Any]):
        self.logger = logging.getLogger(__name__)
        self.brand_id = brand_id
        self.config = brand_config
        self.current_profile = brand_config.get("default_profile", "generic")
        self.state = {
            "current_song": None,
            "audience_info": {},
            "upcoming_events": [],
            "last_action": None,
            "feedback": []
        }

    def get_current_profile(self) -> str:
        return self.current_profile

    def set_current_profile(self, profile_name: str):
        self.current_profile = profile_name
        self.logger.info(f"Brand {self.brand_id}: Set current profile to {profile_name}")

    def update_state(self, key: str, value: Any):
        self.state[key] = value

    def get_state(self) -> Dict[str, Any]:
        return self.state.copy()

    def get_state_value(self, key: str) -> Any:
        return self.state.get(key)


class BrandContextManager:

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.brands: Dict[str, BrandContext] = {}
        self.current_brand_id: Optional[str] = None

    def add_brand(self, brand_id: str, brand_config: Dict[str, Any]) -> BrandContext:
        if brand_id in self.brands:
            self.logger.warning(f"Brand {brand_id} already exists, overwriting")

        brand_context = BrandContext(brand_id, brand_config)
        self.brands[brand_id] = brand_context

        # Set as current if it's the first one
        if self.current_brand_id is None:
            self.current_brand_id = brand_id

        self.logger.info(f"Added brand context: {brand_id}")
        return brand_context

    def get_brand(self, brand_id: Optional[str] = None) -> Optional[BrandContext]:
        """Get a specific brand context or the current one if not specified."""
        target_id = brand_id or self.current_brand_id
        if not target_id:
            self.logger.error("No brand specified and no current brand set")
            return None

        if target_id not in self.brands:
            self.logger.error(f"Brand {target_id} not found")
            return None

        return self.brands[target_id]

    def set_current_brand(self, brand_id: str) -> bool:
        """Set the current active brand."""
        if brand_id not in self.brands:
            self.logger.error(f"Cannot set current brand: {brand_id} not found")
            return False

        self.current_brand_id = brand_id
        self.logger.info(f"Set current brand to: {brand_id}")
        return True

    def get_current_brand_id(self) -> Optional[str]:
        """Get the ID of the current brand."""
        return self.current_brand_id

    def get_all_brand_ids(self) -> list:
        """Get IDs of all registered brands."""
        return list(self.brands.keys())