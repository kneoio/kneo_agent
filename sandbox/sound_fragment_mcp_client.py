#!/usr/bin/env python3
import asyncio
import json
import logging
import websockets
from typing import Dict, Optional, Any

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

BRAND_NAME = 'aizoo'
SEARCH_QUERY = 'massive'


class SoundFragmentMCPClient:
    def __init__(self):
        self.websocket: Optional[websockets.WebSocketServerProtocol] = None
        self.request_id = 0

    async def connect(self, host: str, port: int):
        try:
            uri = f"ws://{host}:{port}"
            logger.info(f"Connecting to MCP WebSocket server at {uri}")
            self.websocket = await websockets.connect(uri)

            # Initialize MCP session
            await self.initialize()
            return True

        except Exception as e:
            logger.error(f"Failed to connect to MCP server: {e}")
            return False

    async def initialize(self):
        """Initialize MCP session"""
        self.request_id += 1
        init_request = {
            "jsonrpc": "2.0",
            "id": self.request_id,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {
                    "tools": {}
                },
                "clientInfo": {
                    "name": "sound-fragment-client",
                    "version": "1.0.0"
                }
            }
        }

        await self.websocket.send(json.dumps(init_request))
        response = await self.websocket.recv()
        init_response = json.loads(response)
        logger.info(
            f"MCP session initialized: {init_response.get_by_type('result', {}).get_by_type('serverInfo', {}).get_by_type('name', 'Unknown')}")

    async def list_tools(self):
        """List available tools"""
        self.request_id += 1
        request = {
            "jsonrpc": "2.0",
            "id": self.request_id,
            "method": "tools/list",
            "params": {}
        }

        await self.websocket.send(json.dumps(request))
        response = await self.websocket.recv()
        result = json.loads(response)

        tools = result.get_by_type('result', {}).get_by_type('tools', [])
        logger.info(f"Available tools: {[tool['name'] for tool in tools]}")
        return tools

    async def call_tool(self, tool_name: str, arguments: dict):
        """Call an MCP tool"""
        self.request_id += 1
        request = {
            "jsonrpc": "2.0",
            "id": self.request_id,
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": arguments
            }
        }

        await self.websocket.send(json.dumps(request))
        response = await self.websocket.recv()
        result = json.loads(response)

        if 'error' in result:
            logger.error(f"Tool call error: {result['error']}")
            return {}

        return result.get_by_type('result', {}).get_by_type('content', [{}])[0].get_by_type('text', '{}')

    async def get_brand_sound_fragments(self, brand: str, page: int = 1, size: int = 10):
        """Get sound fragments for a brand"""
        response_text = await self.call_tool(
            "get_brand_soundfragments",
            {"brand": brand, "page": page, "size": size}
        )

        if response_text:
            return json.loads(response_text)
        return {}

    async def search_sound_fragments(self, query: str, page: int = 1, size: int = 10):
        """Search sound fragments"""
        response_text = await self.call_tool(
            "search_soundfragments",
            {"query": query, "page": page, "size": size}
        )

        if response_text:
            return json.loads(response_text)
        return {}