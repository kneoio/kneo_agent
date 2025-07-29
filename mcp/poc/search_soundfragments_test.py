import asyncio
import websockets
import json


class MCPSongClient:
    def __init__(self, uri):
        self.uri = uri
        self.message_id = 1

    async def connect(self):
        async with websockets.connect(self.uri) as websocket:
            await self.initialize(websocket)
            await asyncio.sleep(1)
            await self.search_soundfragments(websocket, "EBM")

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

    async def search_soundfragments(self, websocket, query, page=1, size=10):
        message = {
            "jsonrpc": "2.0",
            "id": self.message_id,
            "method": "tools/call",
            "params": {
                "name": "search_soundfragments",
                "arguments": {
                    "query": query,
                    "page": page,
                    "size": size
                }
            }
        }
        self.message_id += 1
        response = await self.send_message(websocket, message)

        # Parse and display the search results nicely
        if "result" in response and "content" in response["result"]:
            content_text = response["result"]["content"][0]["text"]
            data = json.loads(content_text)

            print(f"\nSearch query: '{query}'")
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
                print("-" * 40)

        return response


# Usage
uri = "ws://localhost:38708"
client = MCPSongClient(uri)
asyncio.run(client.connect())