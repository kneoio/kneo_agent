import asyncio
import json

import websockets

from cnst.play_list_item_type import PlaylistItemType


async def send_message(websocket, message):
    json_message = json.dumps(message)
    await websocket.send(json_message)
    response = await websocket.recv()
    return json.loads(response)


class MCPSongClient:
    def __init__(self, uri):
        self.uri = uri
        self.message_id = 1

    async def connect(self):
        try:
            async with websockets.connect(self.uri) as websocket:
                await self.initialize(websocket)
                print("\n=== Testing Brand Sound Fragments ===")
                await self.get_brand_sound_fragment(websocket, "lumisonic")
                await asyncio.sleep(1)

        except websockets.exceptions.ConnectionClosed:
            print("Connection closed")
        except ConnectionRefusedError:
            print("Connection refused - check if server is running")
        except Exception as e:
            print(f"Connection error: {type(e).__name__}: {e}")

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
        await send_message(websocket, message)

    async def get_brand_sound_fragment(self, websocket, brand):
        arguments = {
            "brand": brand,
            "fragment_type": PlaylistItemType.SONG.value
        }

        message = {
            "jsonrpc": "2.0",
            "id": self.message_id,
            "method": "tools/call",
            "params": {
                "name": "get_brand_sound_fragment",
                "arguments": arguments
            }
        }
        self.message_id += 1
        response = await send_message(websocket, message)
        print(f"Total results: {response}")
        return response


if __name__ == "__main__":
    uri = "ws://localhost:38708"
    client = MCPSongClient(uri)
    asyncio.run(client.connect())
