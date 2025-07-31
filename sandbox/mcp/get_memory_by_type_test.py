import asyncio
import json

import websockets


class MCPMemoryClient:
    def __init__(self, uri):
        self.uri = uri
        self.message_id = 1

    async def connect(self):
        try:
            async with websockets.connect(self.uri) as websocket:
                print(f"Connected to {self.uri}")
                await self.initialize(websocket)
                await asyncio.sleep(1)
                await self.get_memory_by_type(websocket)
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
            "method": "tools/list",
            "params": {
                "protocolVersion": "2024-11-05",
                "clientInfo": {
                    "name": "MCP-Memory-Client",
                    "version": "1.0.0"
                },
                "capabilities": {}
            }
        }
        self.message_id += 1
        await self.send_message(websocket, message)

    async def get_memory_by_type(self, websocket, brand="aizoo", types=None):
        if types is None:
            types = []
        message = {
            "jsonrpc": "2.0",
            "id": self.message_id,
            "method": "tools/call",
            "params": {
                "name": "get_memory_by_type",
                "arguments": {
                    "brand": brand,
                    "types": types
                }
            }
        }
        self.message_id += 1
        response = await self.send_message(websocket, message)

        if "result" in response and "content" in response["result"]:
            content_text = response["result"]["content"][0]["text"]
            data = json.loads(content_text)

            print(f"\nBrand: {brand}")
            print(f"Memory Types Retrieved: {', '.join(types)}")
            print("\nMemory Data:")
            print("=" * 80)

            for memory_type, memory_data in data.items():
                print(f"\n{memory_type.upper()}:")
                print("-" * 40)

                if isinstance(memory_data, list):
                    if len(memory_data) == 0:
                        print("  No data available")
                    else:
                        for i, item in enumerate(memory_data, 1):
                            if isinstance(item, dict):
                                if "id" in item and "content" in item:
                                    print(f"  Entry {i} (ID: {item['id']}):")
                                    content = item["content"]
                                    if isinstance(content, dict):
                                        for key, value in content.items():
                                            print(f"    {key}: {value}")
                                    else:
                                        print(f"    Content: {content}")
                                else:
                                    print(f"  Entry {i}:")
                                    for key, value in item.items():
                                        print(f"    {key}: {value}")
                            else:
                                print(f"  Entry {i}: {item}")
                            print()
                else:
                    print(f"  {memory_data}")

        return response


uri = "ws://localhost:38708"
client = MCPMemoryClient(uri)
asyncio.run(client.connect())
