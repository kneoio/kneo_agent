#!/usr/bin/env python3
import asyncio
import json
import websockets

BRAND_NAME = 'lumisonic'
SONG_IDS = {'song1': 'bce344e4-f170-4fbd-b7bf-589e025fa20c', 'song2': 'c62a21b5-1a56-439e-a798-23c07fd06128'}
FILE_PATHS = {"audio1": "C:/Users/justa/Music/Intro_Lumar.wav"}

async def main():
    uri = "ws://localhost:38708"

    try:
        async with websockets.connect(uri) as websocket:
            print("Connected to MCP server.")

            request_for_intro_song_handler = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/call",
                "params": {
                    "name": "add_to_queue",
                    "arguments": {
                        "brand": BRAND_NAME,
                        "songIds": SONG_IDS,
                        "filePaths": FILE_PATHS,
                        "mergingMethod": "INTRO_SONG",
                        "priority": 10
                    }
                }
            }

            request_for_song_intro_song_handler = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/call",
                "params": {
                    "name": "add_to_queue",
                    "arguments": {
                        "brand": BRAND_NAME,
                        "songIds": SONG_IDS,
                        "filePaths": FILE_PATHS,
                        "mergingMethod": "SONG_INTRO_SONG",
                        "priority": 10
                    }
                }
            }

            #await websocket.send(json.dumps(request_for_intro_song_handler))
            await websocket.send(json.dumps(request_for_song_intro_song_handler))

            response = await websocket.recv()
            result = json.loads(response)

            if 'error' in result:
                print(f"Error from server: {result['error']['message']}")
                return

            content = result.get('result', {}).get('content', [])
            for item in content:
                if item.get('type') == 'text':
                    print("\n--- Tool Call Result ---")
                    print(f"Success: {item.get('text')}")
                    return

            print(f"Full response: {json.dumps(result, indent=2)}")

    except Exception as e:
        print(f"An error occurred: {e}")


if __name__ == "__main__":
    asyncio.run(main())