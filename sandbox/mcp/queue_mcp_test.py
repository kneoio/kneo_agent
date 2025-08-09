import asyncio
import json
import uuid

import websockets


class MCPQueueClient:
    def __init__(self, uri):
        self.uri = uri
        self.message_id = 1

    async def connect(self):
        try:
            async with websockets.connect(self.uri) as websocket:
                print(f"Connected to {self.uri}")
                await self.initialize(websocket)
                await asyncio.sleep(1)
                await self.get_queue(websocket)
                await asyncio.sleep(1)
                await self.add_to_queue(websocket)
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
                    "name": "MCP-Queue-Client",
                    "version": "1.0.0"
                },
                "capabilities": {}
            }
        }
        self.message_id += 1
        await self.send_message(websocket, message)

    async def get_queue(self, websocket, brand="labirints"):
        message = {
            "jsonrpc": "2.0",
            "id": self.message_id,
            "method": "tools/call",
            "params": {
                "name": "get_queue",
                "arguments": {
                    "brand": brand
                }
            }
        }
        self.message_id += 1
        response = await self.send_message(websocket, message)

        if "result" in response and "content" in response["result"]:
            content_text = response["result"]["content"][0]["text"]
            data = json.loads(content_text)

            print(f"\nBrand: {brand}")
            print("\nQueue Data:")
            print("=" * 80)

            if "queue" in data:
                queue_items = data["queue"]
                print(f"Queue Count: {data.get('count', len(queue_items))}")
                print("-" * 40)

                if not queue_items:
                    print("  Queue is empty")
                else:
                    for i, item in enumerate(queue_items, 1):
                        print(f"  Item {i}:")
                        if isinstance(item, dict):
                            for key, value in item.items():
                                print(f"    {key}: {value}")
                        else:
                            print(f"    {item}")
                        print()

        return response

    async def add_to_queue(self, websocket, brand_name="labirints", sound_fragment_uuid=None, file_path=None, priority=None):
        if sound_fragment_uuid is None:
            sound_fragment_uuid = '44b0f5d7-137c-459f-b043-5e6cff763b4a'
        if file_path is None:
            file_path = "C://Users//justa//Music//mixpla_filler.mp3"

        message = {
            "jsonrpc": "2.0",
            "id": self.message_id,
            "method": "tools/call",
            "params": {
                "name": "add_to_queue",
                "arguments": {
                    "brandName": brand_name,
                    "soundFragmentUUID": sound_fragment_uuid,
                    "filePath": file_path,
                    "priority": priority
                }
            }
        }
        self.message_id += 1
        response = await self.send_message(websocket, message)

        if "result" in response and "content" in response["result"]:
            content_text = response["result"]["content"][0]["text"]
            data = json.loads(content_text)

            print(f"\nAdd to Queue Result:")
            print("=" * 80)
            print(data)

        return response


uri = "ws://localhost:38708"
client = MCPQueueClient(uri)
asyncio.run(client.connect())