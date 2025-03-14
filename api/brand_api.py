#!/usr/bin/env python3
import logging
from typing import Dict, Any, List, Optional
from api.client import APIClient


class BrandAPI:
    def __init__(self, config: Dict[str, Any] = None):
        self.logger = logging.getLogger(__name__)
        self.api_client = APIClient()  # Will use environment variables automatically

    def get_all_brands(self) -> List[Dict[str, Any]]:
        """Get all available brands/radiostations."""
        response = self.api_client.get("brands")
        if response:
            return response.get("brands", [])
        return []

    def get_brand(self, brand_id: str) -> Optional[Dict[str, Any]]:
        """Get details for a specific brand."""
        response = self.api_client.get(f"brands/{brand_id}")
        if response:
            return response.get("brand")
        return None

    def get_brand_profile(self, brand_id: str) -> Optional[Dict[str, Any]]:
        """Get current profile for a brand."""
        response = self.api_client.get(f"brands/{brand_id}/profile")
        if response:
            return response.get("profile")
        return None