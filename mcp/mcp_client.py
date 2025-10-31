import asyncio
import json
import logging
from typing import Dict, Any

import websockets

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)


class MCPClient:
    def __init__(self, config, skip_initialization=False):
        self.ws_url = config.get("broadcaster", {}).get("mcp_ws_url", "ws://127.0.0.1:38708")
        self.logger = logging.getLogger(__name__)
        self.connection = None
        self.message_id = 1

        self.connect_timeout = config.get("broadcaster", {}).get("connect_timeout", 60)
        self.message_timeout = config.get("broadcaster", {}).get("message_timeout", 60)

        self.ping_interval = config.get("broadcaster", {}).get("ping_interval", None)
        self.ping_timeout = config.get("broadcaster", {}).get("ping_timeout", None)

        self.skip_initialization = skip_initialization

    async def connect(self):
        try:
            self.logger.info(f"Connecting to MCP server at {self.ws_url}")

            self.connection = await asyncio.wait_for(
                websockets.connect(
                    self.ws_url,
                    ping_interval=self.ping_interval,
                    ping_timeout=self.ping_timeout,
                    close_timeout=10,
                    open_timeout=30,
                    subprotocols=None
                ),
                timeout=self.connect_timeout
            )
            self.logger.info("Connected to MCP server successfully")

            if not self.skip_initialization:
                await self.initialize()

        except asyncio.TimeoutError:
            self.logger.error(f"Connection timeout after {self.connect_timeout}s")
            self.connection = None
            raise Exception(f"Connection timeout after {self.connect_timeout}s")
        except websockets.exceptions.ConnectionClosed as e:
            self.logger.error(f"WebSocket connection closed: {e}")
            self.connection = None
            raise Exception(f"WebSocket connection closed: {e}")
        except OSError as e:
            self.logger.error(f"Network error connecting to MCP server: {e}")
            self.connection = None
            raise Exception(f"Network error: {e}")
        except Exception as e:
            self.logger.error(f"Failed to connect to MCP server: {e}")
            self.connection = None
            raise

    async def disconnect(self):
        if self.connection:
            try:
                await self.connection.close()
                self.logger.info("Disconnected from MCP server")
            except Exception as e:
                self.logger.error(f"Error during disconnect: {e}")

    async def send_message(self, message):
        if not self.connection:
            raise Exception("WebSocket connection is not established")

        json_message = json.dumps(message)
        self.logger.debug(f"Sending MCP message: {json_message}")

        try:
            await asyncio.wait_for(
                self.connection.send(json_message),
                timeout=self.message_timeout
            )
            response = await asyncio.wait_for(
                self.connection.recv(),
                timeout=self.message_timeout
            )
            self.logger.debug(f"Received MCP response: {response}")
            return json.loads(response)
        except asyncio.TimeoutError:
            self.logger.error(f"Message timeout after {self.message_timeout}s")
            raise Exception(f"Message timeout after {self.message_timeout}s")
        except websockets.exceptions.ConnectionClosed as e:
            self.logger.warning(f"Server closed connection: {e}")
            self.connection = None
            raise Exception(f"Connection closed: {e}")

    async def initialize(self):
        message = {
            "jsonrpc": "2.0",
            "id": self.message_id,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "clientInfo": {
                    "name": "KneoBroadcaster-AI-Client",
                    "version": "1.0.0"
                },
                "capabilities": {}
            }
        }
        self.message_id += 1
        response = await self.send_message(message)
        return response

    async def list_tools(self):
        message = {
            "jsonrpc": "2.0",
            "id": self.message_id,
            "method": "tools/list",
            "params": {}
        }
        self.message_id += 1
        response = await self.send_message(message)
        return response

    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]):
        if not self.connection:
            self.logger.info("Connection lost, reconnecting...")
            await self.connect()
        
        message = {
            "jsonrpc": "2.0",
            "id": self.message_id,
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": arguments
            }
        }
        self.message_id += 1
        
        try:
            response = await self.send_message(message)
        except Exception as e:
            if "Connection closed" in str(e) or "not established" in str(e):
                self.logger.info("Connection lost during call, reconnecting and retrying...")
                await self.connect()
                response = await self.send_message(message)
            else:
                raise

        if "error" in response:
            raise Exception(f"MCP tool error: {response['error'].get('message', 'Unknown error')}")

        result = response.get("result", {})
        content = result.get("content", [])

        for item in content:
            if item.get("type") == "toolResult":
                return item.get("result", {})

        self.logger.warning(f"Tool '{tool_name}' returned an unexpected response format. Content: {content}")
        return {}