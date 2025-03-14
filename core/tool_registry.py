#!/usr/bin/env python3
# core/tool_registry.py - Tool registry for managing available tools

import logging
from typing import Dict, List, Optional, Any
from tools.base_tool import BaseTool


class ToolRegistry:
    """Registry for all available tools in the AI DJ Agent system."""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.tools: Dict[str, BaseTool] = {}

    def register_tool(self, tool: BaseTool) -> bool:
        """
        Register a tool with the registry.

        Args:
            tool: The tool instance to register

        Returns:
            bool: True if registration successful, False otherwise
        """
        if not tool.name:
            self.logger.error("Cannot register tool without a name")
            return False

        if tool.name in self.tools:
            self.logger.warning(f"Tool with name '{tool.name}' already registered. Overwriting.")

        self.tools[tool.name] = tool
        self.logger.debug(f"Registered tool: {tool.name}")
        return True

    def get_tool(self, tool_name: str) -> Optional[BaseTool]:
        """
        Get a tool by name.

        Args:
            tool_name: The name of the tool to retrieve

        Returns:
            The tool instance or None if not found
        """
        tool = self.tools.get(tool_name)
        if not tool:
            self.logger.warning(f"Tool '{tool_name}' not found in registry")
        return tool

    def get_all_tools(self) -> List[BaseTool]:
        """
        Get all registered tools.

        Returns:
            List of all registered tool instances
        """
        return list(self.tools.values())

    def get_tools_by_category(self, category: str) -> List[BaseTool]:
        """
        Get all tools belonging to a specific category.

        Args:
            category: The category to filter by

        Returns:
            List of tool instances in the specified category
        """
        return [tool for tool in self.tools.values() if tool.category == category]

    def get_tool_descriptions(self) -> str:
        """
        Get descriptions of all registered tools.

        Returns:
            A formatted string containing descriptions of all tools
        """
        if not self.tools:
            return "No tools registered."

        descriptions = []
        for name, tool in self.tools.items():
            descriptions.append(f"- {name}: {tool.description}")

        return "\n".join(descriptions)

    def unregister_tool(self, tool_name: str) -> bool:
        """
        Unregister a tool from the registry.

        Args:
            tool_name: The name of the tool to unregister

        Returns:
            bool: True if unregistration successful, False otherwise
        """
        if tool_name not in self.tools:
            self.logger.warning(f"Cannot unregister tool '{tool_name}': not found")
            return False

        del self.tools[tool_name]
        self.logger.debug(f"Unregistered tool: {tool_name}")
        return True