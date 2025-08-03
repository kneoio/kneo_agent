import logging
import json
import asyncio
import websockets
from typing import Dict, List, Any, Optional
from langchain.tools import BaseTool
from pydantic import BaseModel, Field


class BroadcasterMCPClient:
    def __init__(self, config):
        self.ws_url = config.get("broadcaster", {}).get("mcp_ws_url", "ws://localhost:38708")
        self.logger = logging.getLogger(__name__)
        self.connection = None
        self.message_id = 1

    async def connect(self):
        try:
            self.logger.info(f"Connecting to MCP server at {self.ws_url}")
            self.connection = await websockets.connect(self.ws_url)
            self.logger.info("Connected to MCP server")

            # Initialize the connection
            await self.initialize()
        except Exception as e:
            self.logger.error(f"Failed to connect to MCP server: {e}")
            self.connection = None
            raise

    async def disconnect(self):
        if self.connection:
            await self.connection.close()

    async def send_message(self, message):
        if not self.connection:
            raise Exception("WebSocket connection is not established")

        json_message = json.dumps(message)
        self.logger.debug(f"Sending MCP message: {json_message}")
        await self.connection.send(json_message)

        response = await self.connection.recv()
        #self.logger.debug(f"Received MCP response: {response}")
        return json.loads(response)

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
        response = await self.send_message(message)

        if "error" in response:
            raise Exception(f"MCP tool error: {response['error']}")

        # Extract the actual content from MCP response
        result = response.get("result", {})
        content = result.get("content", [])
        if content and len(content) > 0:
            text_content = content[0].get("text", "")
            return json.loads(text_content)

        return {}


class BrandSoundFragmentSearchInput(BaseModel):
    brand: str = Field(description="Brand name to filter sound fragments by")
    page: int = Field(default=1, description="Page number for pagination (1-based)")
    size: int = Field(default=10, description="Number of items per page")


class SoundFragmentSearchInput(BaseModel):
    query: str = Field(description="Search term to find matching sound fragments")
    page: int = Field(default=1, description="Page number for pagination (1-based)")
    size: int = Field(default=10, description="Number of items per page")


class BrandSoundFragmentSearchTool(BaseTool):
    name: str = "get_brand_soundfragments"
    description: str = """Get sound fragments available for a specific brand. 
    Returns a list of songs with their metadata including:
    - id: UUID of the sound fragment 
    - title: Song title
    - artist: Artist name
    - genre: Music genre
    - album: Album name
    - status: Song status
    Use this to find songs for a specific radio brand/station."""

    args_schema: type = BrandSoundFragmentSearchInput

    def __init__(self, mcp_client: BroadcasterMCPClient):
        super().__init__()
        self.mcp_client = mcp_client

    def _run(self, brand: str, page: int = 1, size: int = 10) -> str:
        return asyncio.run(self._arun(brand, page, size))

    async def _arun(self, brand: str, page: int = 1, size: int = 10) -> str:
        try:
            arguments = {"brand": brand, "page": page, "size": size}
            result = await self.mcp_client.call_tool("get_brand_soundfragments", arguments)

            fragments = result.get("fragments", [])
            total_count = result.get("totalCount", 0)
            max_page = result.get("maxPage", 1)

            # Format the response for the AI
            formatted_result = {
                "total_songs": total_count,
                "current_page": page,
                "max_pages": max_page,
                "songs": []
            }

            for fragment in fragments:
                song_info = fragment.get("soundfragment", {})
                formatted_result["songs"].append({
                    "id": fragment.get("id"),
                    "title": song_info.get("title"),
                    "artist": song_info.get("artist"),
                    "genre": song_info.get("genre"),
                    "album": song_info.get("album"),
                    "status": song_info.get("status"),
                    "type": song_info.get("type"),
                    "played_count": fragment.get("playedByBrandCount", 0)
                })

            return json.dumps(formatted_result, indent=2)

        except Exception as e:
            return f"Error searching brand sound fragments: {str(e)}"


class SoundFragmentSearchTool(BaseTool):
    name: str = "search_soundfragments"
    description: str = """Search sound fragments by query term across all songs.
    Returns a list of songs matching the search query with their metadata.
    Use this to find specific songs by title, artist, genre, or other attributes."""

    args_schema: type = SoundFragmentSearchInput

    def __init__(self, mcp_client: BroadcasterMCPClient):
        super().__init__()
        self.mcp_client = mcp_client

    def _run(self, query: str, page: int = 1, size: int = 10) -> str:
        return asyncio.run(self._arun(query, page, size))

    async def _arun(self, query: str, page: int = 1, size: int = 10) -> str:
        try:
            arguments = {"query": query, "page": page, "size": size}
            result = await self.mcp_client.call_tool("search_soundfragments", arguments)

            fragments = result.get("fragments", [])
            total_count = result.get("totalCount", 0)
            max_page = result.get("maxPage", 1)

            # Format the response for the AI
            formatted_result = {
                "total_results": total_count,
                "current_page": page,
                "max_pages": max_page,
                "query": query,
                "songs": []
            }

            for fragment in fragments:
                formatted_result["songs"].append({
                    "id": fragment.get("id"),
                    "title": fragment.get("title"),
                    "artist": fragment.get("artist"),
                    "genre": fragment.get("genre"),
                    "album": fragment.get("album"),
                    "status": fragment.get("status"),
                    "type": fragment.get("type")
                })

            return json.dumps(formatted_result, indent=2)

        except Exception as e:
            return f"Error searching sound fragments: {str(e)}"


class MCPToolsManager:
    """Manager class to handle MCP tools for AI integration"""

    def __init__(self, config):
        self.config = config
        self.mcp_client = None
        self.tools = []
        self.logger = logging.getLogger(__name__)

    async def initialize(self):
        """Initialize MCP connection and create tools"""
        self.mcp_client = BroadcasterMCPClient(self.config)
        await self.mcp_client.connect()

        # Create LangChain tools
        self.tools = [
            BrandSoundFragmentSearchTool(self.mcp_client),
            SoundFragmentSearchTool(self.mcp_client)
        ]

        self.logger.info(f"Initialized {len(self.tools)} MCP tools")
        return self.tools

    async def cleanup(self):
        """Clean up MCP connection"""
        if self.mcp_client:
            await self.mcp_client.disconnect()

    def get_tools(self):
        """Get the list of LangChain tools"""
        return self.tools
