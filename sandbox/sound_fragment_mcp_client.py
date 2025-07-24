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
            f"MCP session initialized: {init_response.get('result', {}).get('serverInfo', {}).get('name', 'Unknown')}")

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

        tools = result.get('result', {}).get('tools', [])
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

        return result.get('result', {}).get('content', [{}])[0].get('text', '{}')

    async def get_brand_soundfragments(self, brand: str, page: int = 1, size: int = 10):
        """Get sound fragments for a brand"""
        response_text = await self.call_tool(
            "get_brand_soundfragments",
            {"brand": brand, "page": page, "size": size}
        )

        if response_text:
            return json.loads(response_text)
        return {}

    async def search_soundfragments(self, query: str, page: int = 1, size: int = 10):
        """Search sound fragments"""
        response_text = await self.call_tool(
            "search_soundfragments",
            {"query": query, "page": page, "size": size}
        )

        if response_text:
            return json.loads(response_text)
        return {}


async def main():
    # Connect to your MCP WebSocket server
    server_host = "localhost"
    server_port = 38708

    client = SoundFragmentMCPClient()

    logger.info("Connecting to MCP WebSocket server...")
    if not await client.connect(server_host, server_port):
        logger.error("Failed to connect")
        return

    # List available tools
    logger.info("Listing available tools...")
    tools = await client.list_tools()

    # Test brand sound fragments
    logger.info(f"Getting sound fragments for brand: {BRAND_NAME}")
    brand_response = await client.get_brand_soundfragments(brand=BRAND_NAME, size=5)

    if brand_response and 'fragments' in brand_response:
        logger.info(f"Found {brand_response['totalCount']} total fragments for {BRAND_NAME}")

        # Debug: Print first fragment structure
        if brand_response['fragments']:
            logger.info(f"Sample fragment structure: {json.dumps(brand_response['fragments'][0], indent=2)}")

        for i, fragment in enumerate(brand_response['fragments'][:3], 1):
            # Try different ways to access the data based on your DTO structure
            sound_fragment = fragment.get('soundFragmentDTO', fragment.get('soundfragment', {}))

            title = sound_fragment.get('title', fragment.get('title', 'Unknown'))
            artist = sound_fragment.get('artist', fragment.get('artist', 'Unknown'))
            genre = sound_fragment.get('genre', fragment.get('genre', 'Unknown'))

            logger.info(f"{i}. {title} by {artist} ({genre})")

    # Test search
    logger.info(f"Searching for: {SEARCH_QUERY}")
    search_response = await client.search_soundfragments(query=SEARCH_QUERY, size=5)

    if search_response and 'fragments' in search_response:
        logger.info(f"Found {search_response['totalCount']} total search results")
        for i, fragment in enumerate(search_response['fragments'][:3], 1):
            title = fragment.get('title', 'Unknown')
            artist = fragment.get('artist', 'Unknown')
            logger.info(f"{i}. {title} by {artist}")

    logger.info("Done!")


if __name__ == "__main__":
    asyncio.run(main())