#!/usr/bin/env python3
import logging
from typing import Dict, Any, List, Optional


class BaseTool:
    """Base class for all tools."""

    def __init__(self, config: Dict[str, Any]):
        self.logger = logging.getLogger(self.__class__.__module__)
        self.config = config
        self.brand_manager = config.get("brand_manager")
        self._initialize()

    def _initialize(self):
        """Initialize the tool. Override in subclasses."""
        pass

    @property
    def name(self) -> str:
        """Get the name of the tool."""
        return self._get_name()

    def _get_name(self) -> str:
        """Get the name of the tool. Override in subclasses."""
        raise NotImplementedError("Tool must implement _get_name method")

    def get_description(self) -> str:
        """Get a description of the tool."""
        return self._get_description()

    def _get_description(self) -> str:
        """Get a description of the tool. Override in subclasses."""
        raise NotImplementedError("Tool must implement _get_description method")

    def get_category(self) -> str:
        """Get the category of the tool."""
        return self._get_category()

    def _get_category(self) -> str:
        """Get the category of the tool. Override in subclasses."""
        raise NotImplementedError("Tool must implement _get_category method")

    def get_current_brand_id(self) -> Optional[str]:
        """Get the current brand ID from the brand manager."""
        if self.brand_manager:
            return self.brand_manager.get_current_brand_id()
        return None

    def get_brand_context(self, brand_id: Optional[str] = None):
        """Get the context for a specific brand or the current brand."""
        if self.brand_manager:
            return self.brand_manager.get_brand(brand_id)
        return None