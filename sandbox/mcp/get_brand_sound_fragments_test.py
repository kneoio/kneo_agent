import asyncio
import websockets
import json

from cnst.play_list_item_type import PlaylistItemType


class MCPSongClient:
    def __init__(self, uri):
        self.uri = uri
        self.message_id = 1

    async def connect(self):
        try:
            async with websockets.connect(self.uri) as websocket:
                print(f"Connected to {self.uri}")
                await self.initialize(websocket)
                await asyncio.sleep(1)
                #await self.get_brand_sound_fragments(websocket, brand="aizoo", genres="rock,electronic",types="SONG")
                await self.get_brand_sound_fragments(websocket, brand="aizoo", genres="",types=PlaylistItemType.ADVERTISEMENT)
        except Exception as e:
            print(f"Connection failed: {e}")

    async def send_message(self, websocket, message):
        json_message = json.dumps(message)
        print(f"Sending: {json_message}")
        await websocket.send(json_message)
        response = await websocket.recv()
        print(f"Received: {response}")
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

    async def get_brand_sound_fragments(self, websocket, brand="aizoo", page=1, size=10, genres=None, sources=None, types=None):
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

        # Parse and display the song list nicely
        if "result" in response and "content" in response["result"]:
            content_text = response["result"]["content"][0]["text"]
            data = json.loads(content_text)

            print(f"\nBrand: {brand}")
            print(f"Total songs: {data['totalCount']}")
            print(f"Page: {data['page']} of {data['maxPage']}")
            print("\nSongs:")
            print("-" * 80)

            for fragment in data["fragments"]:
                song = fragment["soundfragment"]
                print(f"ID: {song['id']}")
                print(f"Title: {song['title']}")
                print(f"Artist: {song['artist']}")
                print(f"Genre: {song['genre']}")
                print(f"Album: {song['album']}")
                print(f"Played: {fragment['playedByBrandCount']} times")
                print("-" * 40)

        return response


uri = "ws://localhost:38708"
client = MCPSongClient(uri)
asyncio.run(client.connect())