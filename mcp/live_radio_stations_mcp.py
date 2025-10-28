#!/usr/bin/env python3
import logging
from typing import Optional

from models.live_container import LiveContainer


class LiveRadioStationsMCP:

    def __init__(self, mcp_client):
        self.mcp_client = mcp_client
        self.logger = logging.getLogger(__name__)
    
    async def get_live_radio_stations(self) -> Optional[LiveContainer]:
        try:
            result = await self.mcp_client.call_tool(
                tool_name="get_live_radio_stations",
                arguments={}
            )
            
            if not result:
                self.logger.warning("No data returned from get_live_radio_stations MCP tool")
                return None
            
            live_container = LiveContainer.from_dict(result)
            self.logger.info(f"Retrieved {len(live_container)} radio stations from MCP")
            
            return live_container
            
        except Exception as e:
            self.logger.error(f"Error calling get_live_radio_stations MCP tool: {e}")
            return None
