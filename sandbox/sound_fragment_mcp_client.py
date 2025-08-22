#!/usr/bin/env python3
import json
import logging
import time
from typing import Optional

import websockets

# Enhanced logging configuration (Windows-compatible)
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - [%(funcName)s:%(lineno)d] - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('mcp_client.log', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)

BRAND_NAME = 'lumisonic'


class SoundFragmentMCPClient:
    def __init__(self):
        logger.info("=" * 50)
        logger.info("Initializing SoundFragmentMCPClient")
        self.websocket: Optional[websockets.WebSocketServerProtocol] = None
        self.request_id = 0
        self.connection_start_time = None
        logger.debug(f"Client initialized with request_id: {self.request_id}")

    async def connect(self, host: str, port: int):
        logger.info("=" * 50)
        logger.info("STARTING CONNECTION PROCESS")

        try:
            uri = f"ws://{host}:{port}"
            logger.info(f"Constructed WebSocket URI: {uri}")

            self.connection_start_time = time.time()
            self.websocket = await websockets.connect(uri)
            connection_time = time.time() - self.connection_start_time

            logger.info(f"[SUCCESS] WebSocket connection established successfully!")
            logger.debug(f"WebSocket state: {self.websocket.state}")

            logger.info("Starting MCP initialization...")
            await self.initialize()

            logger.info("[SUCCESS] CONNECTION PROCESS COMPLETED SUCCESSFULLY")
            return True

        except ConnectionRefusedError as e:
            logger.error(f"[ERROR] Connection refused - server may not be running: {e}")
            return False
        except websockets.exceptions.InvalidURI as e:
            logger.error(f"[ERROR] Invalid WebSocket URI: {e}")
            return False
        except Exception as e:
            logger.error(f"[ERROR] Unexpected error during connection: {type(e).__name__}: {e}")
            logger.exception("Full traceback:")
            return False

    async def initialize(self):
        logger.info("-" * 30)
        logger.info("INITIALIZING MCP PROTOCOL")

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

        logger.debug(json.dumps(init_request, indent=2))

        logger.info("Sending initialization request to server...")
        send_start = time.time()
        await self.websocket.send(json.dumps(init_request))
        send_time = time.time() - send_start
        recv_start = time.time()
        response = await self.websocket.recv()
        recv_time = time.time() - recv_start
        logger.debug(f"Response received in {recv_time:.3f} seconds")

        logger.debug(f"Raw response: {response}")

        try:
            init_response = json.loads(response)
            logger.debug("Parsed response:")
            logger.debug(json.dumps(init_response, indent=2))

            if 'error' in init_response:
                logger.error(f"[ERROR] Initialization error: {init_response['error']}")
                return False

            server_info = init_response.get('result', {}).get('serverInfo', {})
            server_name = server_info.get('name', 'Unknown')
            server_version = server_info.get('version', 'Unknown')

            logger.info(f"[SUCCESS] MCP session initialized successfully!")
            logger.debug(f"Full server info: {server_info}")

        except json.JSONDecodeError as e:
            logger.error(f"[ERROR] Failed to parse initialization response: {e}")
            logger.error(f"Raw response was: {response}")
            return False

    async def list_tools(self):
        logger.info("-" * 30)
        logger.info("LISTING AVAILABLE TOOLS")

        self.request_id += 1
        logger.debug(f"Generated request ID: {self.request_id}")

        request = {
            "jsonrpc": "2.0",
            "id": self.request_id,
            "method": "tools/list",
            "params": {}
        }

        logger.debug(json.dumps(request, indent=2))
        await self.websocket.send(json.dumps(request))
        response = await self.websocket.recv()
        logger.debug(f"Raw response: {response}")

        try:
            result = json.loads(response)
            logger.debug(json.dumps(result, indent=2))

            if 'error' in result:
                logger.error(f"[ERROR] Tools list error: {result['error']}")
                return []

            tools = result.get('result', {}).get('tools', [])
            logger.info(f"[SUCCESS] Found {len(tools)} available tools:")

            for i, tool in enumerate(tools, 1):
                tool_name = tool.get('name', 'Unknown')
                tool_desc = tool.get('description', 'No description')
                logger.info(f"  {i}. {tool_name}: {tool_desc}")
                logger.debug(f"     Full tool info: {tool}")

            return tools

        except json.JSONDecodeError as e:
            logger.error(f"[ERROR] Failed to parse tools list response: {e}")
            return []

    async def call_tool(self, tool_name: str, arguments: dict):
        logger.info("-" * 30)
        logger.info(f"CALLING TOOL: {tool_name}")
        logger.info(f"Arguments: {arguments}")

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

        logger.debug("Prepared tool call request:")
        logger.debug(json.dumps(request, indent=2))

        logger.info(f"Sending tool call request for '{tool_name}'...")
        call_start = time.time()
        await self.websocket.send(json.dumps(request))
        response = await self.websocket.recv()
        call_time = time.time() - call_start
        logger.debug(f"Raw response: {response}")

        try:
            result = json.loads(response)
            logger.debug("Parsed response:")
            logger.debug(json.dumps(result, indent=2))

            if 'error' in result:
                error_info = result['error']
                logger.error(f"[ERROR] Tool call error for '{tool_name}':")
                logger.error(f"   Code: {error_info.get('code', 'Unknown')}")
                logger.error(f"   Message: {error_info.get('message', 'Unknown error')}")
                logger.debug(f"   Full error: {error_info}")
                return {}

            content = result.get('result', {}).get('content', [])
            if not content:
                logger.warning(f"[WARNING] Tool '{tool_name}' returned empty content")
                return {}

            response_text = content[0].get('text', '{}')
            logger.info(f"[SUCCESS] Tool '{tool_name}' executed successfully")
            logger.debug(f"Response preview: {response_text[:200]}{'...' if len(response_text) > 200 else ''}")

            return response_text

        except json.JSONDecodeError as e:
            logger.error(f"[ERROR] Failed to parse tool call response: {e}")
            logger.error(f"Raw response was: {response}")
            return {}
        except Exception as e:
            logger.error(f"[ERROR] Unexpected error processing tool response: {e}")
            logger.exception("Full traceback:")
            return {}

    async def get_brand_sound_fragments(self, brand: str, page: int = 1, size: int = 1):
        logger.info("=" * 50)
        logger.info(f"GETTING SOUND FRAGMENTS FOR BRAND: {brand}")
        logger.info(f"Page: {page}, Size: {size}")

        response_text = await self.call_tool(
            "get_brand_sound_fragments",
            {"brand": brand, "page": page, "size": size}
        )

        if not response_text:
            logger.warning("[ERROR] No response from get_brand_sound_fragments tool")
            return {}

        try:
            fragments_data = json.loads(response_text)
            if isinstance(fragments_data, dict):
                total_fragments = fragments_data.get('totalCount', 0)
                current_page = fragments_data.get('page', page)
                fragments = fragments_data.get('fragments', [])

                logger.info(f"Total fragments available: {total_fragments}")
                logger.info(f"Current page: {current_page}")
                logger.info(f"Fragments in this page: {len(fragments)}")

                for i, fragment in enumerate(fragments, 1):
                    soundfragment = fragment.get('soundfragment', {})
                    fragment_title = soundfragment.get('title', 'Unknown')
                    fragment_artist = soundfragment.get('artist', 'Unknown')
                    played_count = fragment.get('playedByBrandCount', 0)

                    logger.info(f"  {i}. \"{fragment_title}\" by {fragment_artist} (Played: {played_count} times)")
            else:
                logger.debug(f"Raw fragments data: {fragments_data}")

            return fragments_data

        except json.JSONDecodeError as e:
            logger.error(f"[ERROR] Failed to parse sound fragments response: {e}")
            logger.error(f"Raw response was: {response_text}")
            return {}

    async def close(self):
        logger.info("-" * 30)

        if self.websocket:
            logger.debug("Closing WebSocket connection...")
            await self.websocket.close()

            if self.connection_start_time:
                total_time = time.time() - self.connection_start_time
                logger.info(f"Connection was active for {total_time:.3f} seconds")

            logger.info("[SUCCESS] Connection closed successfully")
        else:
            logger.warning("No active connection to close")


# Example usage with detailed logging
async def main():
    logger.info("[START] STARTING SOUND FRAGMENT MCP CLIENT")

    client = SoundFragmentMCPClient()

    # Connect to server
    if await client.connect("localhost", 38708):
        tools = await client.list_tools()
        fragments = await client.get_brand_sound_fragments(BRAND_NAME, page=1, size=1)
        await client.close()
    else:
        logger.error("[FAILED] Failed to establish connection")


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())