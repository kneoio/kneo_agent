import logging
from typing import Dict, Any
from mcp.mcp_client import MCPClient
from core.config import get_tool_config


class SoundFragmentMCP:
    def __init__(self, mcp_client: MCPClient = None, config=None):
        self.mcp_client = mcp_client
        self.config = config or {}
        self.logger = logging.getLogger(__name__)
        self.logger.info("SoundFragmentMCP initialized")

    async def get_brand_sound_fragment(self, brand: str, fragment_type: str = "SONG") -> Dict[str, Any]:
        try:
            self.logger.info(f"Getting sound fragment for brand: {brand}, type: {fragment_type}")
            
            if not self.mcp_client:
                self.logger.error("MCP client not available")
                return {
                    "success": False,
                    "brand": brand,
                    "fragment_type": fragment_type,
                    "error": "MCP client not available"
                }

            result = await self.mcp_client.call_tool(
                "get_brand_sound_fragment",
                {"brand": brand, "fragment_type": fragment_type}
            )
            
            self.logger.info(f"Successfully retrieved sound fragment for {brand}")
            return {
                "success": True,
                "brand": brand,
                "fragment_type": fragment_type,
                "data": result
            }

        except Exception as e:
            self.logger.error(f"Failed to get sound fragment for {brand}: {e}")
            return {
                "success": False,
                "brand": brand,
                "fragment_type": fragment_type,
                "error": str(e)
            }

    @staticmethod
    def get_tool_definition() -> Dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": "get_brand_sound_fragment",
                "description": "Get a sound fragment (song, jingle, etc.) from the broadcaster for a specific brand",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "brand": {
                            "type": "string",
                            "description": "The brand name to get sound fragment for"
                        },
                        "fragment_type": {
                            "type": "string",
                            "description": "Type of sound fragment (SONG, JINGLE, etc.)",
                            "default": "SONG"
                        }
                    },
                    "required": ["brand"]
                }
            }
        }

    def _get_tool_config(self):
        if not self.config:
            self.logger.warning("No config provided to SoundFragmentMCP")
            return {}

        tool_cfg = get_tool_config(self.config, "sound_fragment_mcp")
        if tool_cfg is None:
            if not hasattr(self, '_config_warning_logged'):
                self.logger.warning("sound_fragment_mcp configuration not found - using empty config")
                self._config_warning_logged = True
            return {}

        if not hasattr(self, '_config_loaded_logged'):
            self.logger.info("sound_fragment_mcp config loaded")
            self._config_loaded_logged = True

        return tool_cfg
