#!/usr/bin/env python3
import asyncio
import json
import websockets

BRAND_NAME = 'lumisonic'


async def main():
    uri = "ws://localhost:38708"

    try:
        async with websockets.connect(uri) as websocket:
            print("Connected to MCP server.")

            request = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/call",
                "params": {
                    "name": "get_brand_sound_fragment",
                    "arguments": {
                        "brand": BRAND_NAME,
                        "fragment_type": "SONG"
                    }
                }
            }

            await websocket.send(json.dumps(request))

            response = await websocket.recv()
            result = json.loads(response)

            if 'error' in result:
                print(f"Error from server: {result['error']['message']}")
                return

            content = result.get('result', {}).get('content', [])
            for item in content:
                if item.get('type') == 'toolResult':
                    final_data = item.get('result')
                    print("\n--- Tool Call Successful ---")
                    print("Received Sound Fragment:")
                    print(json.dumps(final_data, indent=2))
                    return

            print("Tool call returned an unexpected format.")

    except Exception as e:
        print(f"An error occurred: {e}")


if __name__ == "__main__":
    asyncio.run(main())