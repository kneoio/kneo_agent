#!/usr/bin/env python3
from abc import ABC, abstractmethod

from typing import Dict, Any, Optional, List


class BaseTool(ABC):
    """Base class for all tools with brand awareness."""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.brand_manager = config.get("brand_manager")

    @property
    @abstractmethod
    def name(self) -> str:
        """Tool name used for registration and lookups."""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """Tool description for Claude's system prompt."""
        pass

    def get_brand(self, brand_identifier: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Get brand by slugName or ID, or current brand if None provided."""
        if not self.brand_manager:
            return None

        return self.brand_manager.get_brand(brand_identifier)