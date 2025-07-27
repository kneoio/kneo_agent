import json
import logging

import websockets


class BroadcasterMCPClient:
    def __init__(self, config):
        self.ws_url = config.get("mcp").get("ws_url")
        self.logger = logging.getLogger(__name__)
        self.connection = None

    async def connect(self):
        try:
            self.logger.info(f"Connecting to MCP server at {self.ws_url}")
            self.connection = await websockets.connect(self.ws_url)
            self.logger.info("Connected to MCP server")
        except Exception as e:
            self.logger.error(f"Failed to connect to MCP server: {e}")
            self.connection = None

    async def disconnect(self):
        if self.connection:
            await self.connection.close()
            self.logger.info("Disconnected from MCP server")

    async def send_message(self, message):
        if self.connection:
            json_message = json.dumps(message)
            self.logger.info(f"Sending: {json_message}")
            await self.connection.send(json_message)
        else:
            self.logger.error("WebSocket connection is not established")

    async def receive_message(self):
        if self.connection:
            try:
                response = await self.connection.recv()
                self.logger.info(f"Received: {response}")
                return json.loads(response)
            except json.JSONDecodeError as e:
                self.logger.error(f"Failed to decode the response: {e}")
                return None
        else:
            self.logger.error("WebSocket connection is not established")
            return None

    async def initialize(self):
        message = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "clientInfo": {
                    "name": "KneoBroadcaster-MCP-Client",
                    "version": "1.0.0"
                },
                "capabilities": {}
            }
        }
        await self.send_message(message)
        return await self.receive_message()

    async def list_tools(self):
        message = {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/list",
            "params": {}
        }
        await self.send_message(message)
        return await self.receive_message()

    async def call_tool(self, tool_name, arguments):
        message = {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": arguments
            }
        }
        await self.send_message(message)
        return await self.receive_message()