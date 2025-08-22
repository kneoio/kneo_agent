#!/usr/bin/env python3
import json
import asyncio
import websockets

BRAND_NAME = 'lumisonic'


class SoundFragmentChecker:
    def __init__(self):
        self.websocket = None
        self.request_id = 0
        self.all_songs = []

    async def connect(self, host: str, port: int):
        uri = f"ws://{host}:{port}"
        self.websocket = await websockets.connect(uri)
        await self.initialize()

    async def initialize(self):
        self.request_id += 1
        init_request = {
            "jsonrpc": "2.0",
            "id": self.request_id,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {}},
                "clientInfo": {
                    "name": "sound-fragment-client",
                    "version": "1.0.0"
                }
            }
        }
        await self.websocket.send(json.dumps(init_request))
        await self.websocket.recv()

    async def get_fragments(self, brand: str):
        self.request_id += 1
        request = {
            "jsonrpc": "2.0",
            "id": self.request_id,
            "method": "tools/call",
            "params": {
                "name": "get_brand_sound_fragments",
                "arguments": {"brand": brand, "page": 1, "size": 1}
            }
        }

        await self.websocket.send(json.dumps(request))
        response = await self.websocket.recv()
        result = json.loads(response)

        content = result.get('result', {}).get('content', [])
        if content:
            return json.loads(content[0].get('text', '{}'))
        return None

    async def run_test(self):
        # Test 1: Rapid calls (no delay)
        print("=== TEST 1: Rapid calls (no delay) ===")
        rapid_songs = []
        for i in range(1, 11):
            data = await self.get_fragments(BRAND_NAME)

            if data and 'fragments' in data:
                fragment = data['fragments'][0]
                song = fragment['soundfragment']
                title = song['title']
                artist = song['artist']

                song_id = f"{artist} - {title}"
                rapid_songs.append(song_id)

                print(f"Call {i:2d}: {title} by {artist}")

        print(f"Rapid test - Unique: {len(set(rapid_songs))}/{len(rapid_songs)}")

        # Test 2: With delays
        print("\n=== TEST 2: With delays ===")
        delayed_songs = []
        for i in range(1, 11):
            data = await self.get_fragments(BRAND_NAME)

            if data and 'fragments' in data:
                fragment = data['fragments'][0]
                song = fragment['soundfragment']
                title = song['title']
                artist = song['artist']

                song_id = f"{artist} - {title}"
                delayed_songs.append(song_id)

                print(f"Call {i:2d}: {title} by {artist}")
                await asyncio.sleep(0.1)  # Small delay

        print(f"Delayed test - Unique: {len(set(delayed_songs))}/{len(delayed_songs)}")

        # Combine for final analysis
        self.all_songs = rapid_songs + delayed_songs

        # Check uniqueness
        unique_songs = set(self.all_songs)
        print(f"\nOverall - Total songs: {len(self.all_songs)}")
        print(f"Overall - Unique songs: {len(unique_songs)}")

        if len(unique_songs) == len(self.all_songs):
            print("All songs are unique!")
        else:
            print("Some duplicates found:")
            for song in self.all_songs:
                count = self.all_songs.count(song)
                if count > 1:
                    print(f"  {song} appears {count} times")

    async def close(self):
        await self.websocket.close()


async def main():
    client = SoundFragmentChecker()
    await client.connect("localhost", 38708)
    await client.run_test()
    await client.close()


if __name__ == "__main__":
    asyncio.run(main())