import asyncio
import websockets
import json

from cnst.play_list_item_type import PlaylistItemType
from cnst.source_type import SourceType


class MCPSongClient:
    def __init__(self, uri):
        self.uri = uri
        self.message_id = 1

    async def connect(self):
        try:
            async with websockets.connect(self.uri) as websocket:
                await self.initialize(websocket)
                await asyncio.sleep(1)

                print("=== Testing Search with Filters ===")

                await self.search_sound_fragments(websocket, "EBM")
                await asyncio.sleep(1)
                await self.search_sound_fragments(websocket, "jazz", genres="jazz,blues")
                await asyncio.sleep(1)
                await self.search_sound_fragments(websocket, "rock", genres="rock,pop",
                                                  sources=SourceType.USERS_UPLOAD.value,
                                                  types=PlaylistItemType.SONG.value)
                await asyncio.sleep(1)

                print("\n=== Testing Brand Sound Fragments ===")
                await self.get_brand_sound_fragments(websocket, "aizoo",
                                                     genres="rock,electronic",
                                                     types=[PlaylistItemType.SONG.value])
                await asyncio.sleep(1)

                print("\n=== Testing Get All Sound Fragments ===")
                await self.get_all_sound_fragments(websocket, genres="jazz", sources=SourceType.USERS_UPLOAD.value)

        except websockets.exceptions.ConnectionClosed:
            print("Connection closed")
        except ConnectionRefusedError:
            print("Connection refused - check if server is running")
        except Exception as e:
            print(f"Connection error: {type(e).__name__}: {e}")

    async def send_message(self, websocket, message):
        json_message = json.dumps(message)
        await websocket.send(json_message)
        response = await websocket.recv()
        return json.loads(response)

    async def initialize(self, websocket):
        message = {
            "jsonrpc": "2.0",
            "id": self.message_id,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "clientInfo": {
                    "name": "MCP-Song-Client",
                    "version": "1.0.0"
                },
                "capabilities": {}
            }
        }
        self.message_id += 1
        await self.send_message(websocket, message)

    async def search_sound_fragments(self, websocket, query, page=1, size=10, genres=None, sources=None, types=None):
        arguments = {
            "query": query,
            "page": page,
            "size": size
        }

        if genres:
            arguments["genres"] = genres
        if sources:
            arguments["sources"] = sources
        if types:
            arguments["types"] = types

        message = {
            "jsonrpc": "2.0",
            "id": self.message_id,
            "method": "tools/call",
            "params": {
                "name": "search_soundfragments",
                "arguments": arguments
            }
        }
        self.message_id += 1
        response = await self.send_message(websocket, message)

        if "result" in response and "content" in response["result"]:
            content_text = response["result"]["content"][0]["text"]
            data = json.loads(content_text)

            filter_info = []
            if genres:
                filter_info.append(f"genres: {genres}")
            if sources:
                filter_info.append(f"sources: {sources}")
            if types:
                filter_info.append(f"types: {types}")

            filter_str = f" (filters: {', '.join(filter_info)})" if filter_info else ""

            print(f"\nSearch query: '{query}'{filter_str}")
            print(f"Total results: {data['totalCount']}")
            print(f"Page: {data['page']} of {data['maxPage']}")
            print("\nSearch Results:")
            print("-" * 80)

            for fragment in data["fragments"]:
                print(f"ID: {fragment['id']}")
                print(f"Title: {fragment['title']}")
                print(f"Artist: {fragment['artist']}")
                print(f"Genre: {fragment['genre']}")
                print(f"Album: {fragment['album']}")
                print(f"Type: {fragment['type']}")
                print(f"Source: {fragment['source']}")
                print("-" * 40)

        return response

    async def get_brand_sound_fragments(self, websocket, brand, page=1, size=10, genres=None, sources=None, types=None):
        arguments = {
            "brand": brand,
            "page": page,
            "size": size
        }

        if genres:
            arguments["genres"] = genres
        if sources:
            arguments["sources"] = sources
        if types:
            arguments["types"] = types

        message = {
            "jsonrpc": "2.0",
            "id": self.message_id,
            "method": "tools/call",
            "params": {
                "name": "get_brand_sound_fragments",
                "arguments": arguments
            }
        }
        self.message_id += 1
        response = await self.send_message(websocket, message)

        if "result" in response and "content" in response["result"]:
            content_text = response["result"]["content"][0]["text"]
            data = json.loads(content_text)

            filter_info = []
            if genres:
                filter_info.append(f"genres: {genres}")
            if sources:
                filter_info.append(f"sources: {sources}")
            if types:
                filter_info.append(f"types: {types}")

            filter_str = f" (filters: {', '.join(filter_info)})" if filter_info else ""

            print(f"\nBrand: '{brand}'{filter_str}")
            print(f"Total results: {data['totalCount']}")
            print(f"Page: {data['page']} of {data['maxPage']}")
            print("\nBrand Sound Fragments:")
            print("-" * 80)

            for fragment in data["fragments"]:

                print(f"ID: {fragment['id']}")
                print(f"Title: {fragment['title']}")
                print(f"Artist: {fragment['artist']}")
                print(f"Genre: {fragment['genre']}")
                print(f"Type: {fragment['type']}")
                print(f"Source: {fragment['source']}")
                print("-" * 40)

        return response

    async def get_all_sound_fragments(self, websocket, page=1, size=10, genres=None, sources=None, types=None):
        arguments = {
            "page": page,
            "size": size
        }
        if genres:
            arguments["genres"] = genres
        if sources:
            arguments["sources"] = sources
        if types:
            arguments["types"] = types

        message = {
            "jsonrpc": "2.0",
            "id": self.message_id,
            "method": "tools/call",
            "params": {
                "name": "get_all_sound_fragments",
                "arguments": arguments
            }
        }
        self.message_id += 1
        response = await self.send_message(websocket, message)

        if "result" in response and "content" in response["result"]:
            content_text = response["result"]["content"][0]["text"]
            data = json.loads(content_text)

            filter_info = []
            if genres:
                filter_info.append(f"genres: {genres}")
            if sources:
                filter_info.append(f"sources: {sources}")
            if types:
                filter_info.append(f"types: {types}")

            filter_str = f" (filters: {', '.join(filter_info)})" if filter_info else ""

            print(f"\nAll Sound Fragments{filter_str}")
            print(f"Total results: {data['totalCount']}")
            print(f"Page: {data['page']} of {data['maxPage']}")
            print("\nSound Fragments:")
            print("-" * 80)

            for fragment in data["fragments"]:
                print(f"ID: {fragment['id']}")
                print(f"Title: {fragment['title']}")
                print(f"Artist: {fragment['artist']}")
                print(f"Genre: {fragment['genre']}")
                print(f"Type: {fragment['type']}")
                print(f"Source: {fragment['source']}")
                print("-" * 40)

        return response


if __name__ == "__main__":
    uri = "ws://localhost:38708"
    client = MCPSongClient(uri)
    asyncio.run(client.connect())