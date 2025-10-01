#!/usr/bin/env python3
import asyncio
import json
import websockets

BRAND_NAME = 'lumisonic'
FILE_PATHS = {"audio1": "C:/Users/justa/Music/Dimu/ElevenLabs_2025-10-01T11_24_04_Dimu_ivc_sp100_s50_sb75_v3.mp3", "audio2": "C:/Users/justa/Music/Dimu/ElevenLabs_2025-10-01T11_24_04_Dimu_ivc_sp100_s50_sb75_v3.mp3"}
SONG_IDS = {'song1': '787c0b06-efff-491c-a624-50a1f1d45e13', 'song2': '3f03b5ee-e92b-45fe-99c8-8382532aa5cf'}

async def main():
    uri = "ws://localhost:38708"

    try:
        async with websockets.connect(uri) as websocket:
            print("Connected to MCP server.")

            request_for_mix = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/call",
                "params": {
                    "name": "add_to_queue",
                    "arguments": {
                        "brand": BRAND_NAME,
                        "songIds": SONG_IDS,
                        "filePaths": FILE_PATHS,
                        "mergingMethod": "INTRO_SONG_INTRO_SONG",
                        "priority": 10
                    }
                }
            }

            await websocket.send(json.dumps(request_for_mix))

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