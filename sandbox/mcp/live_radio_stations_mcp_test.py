#!/usr/bin/env python3
import asyncio
import json
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

import websockets
from models.live_container import LiveContainer


async def main():
    uri = "ws://localhost:38708"
    #uri = "ws://mixpla.io:38708"

    try:
        async with websockets.connect(uri) as websocket:
            print("Connected to MCP server.")

            request = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/call",
                "params": {
                    "name": "get_live_radio_stations",
                    "arguments": {}
                }
            }

            print(f"\n--- Sending Request ---")
            print(json.dumps(request, indent=2))
            
            await websocket.send(json.dumps(request))

            response = await websocket.recv()
            print(f"\n--- Raw Response ---")
            print(response)
            
            result = json.loads(response)
            print(f"\n--- Parsed Response ---")
            print(json.dumps(result, indent=2))

            if 'error' in result:
                print(f"\n--- Error Details ---")
                print(f"Error message: {result['error'].get('message', 'No message')}")
                print(f"Error code: {result['error'].get('code', 'No code')}")
                print(f"Full error: {json.dumps(result['error'], indent=2)}")
                return

            content = result.get('result', {}).get('content', [])
            print(f"\n--- Content ---")
            print(f"Content type: {type(content)}")
            print(f"Content length: {len(content) if isinstance(content, list) else 'N/A'}")
            
            for item in content:
                if item.get('type') == 'toolResult':
                    final_data = item.get('result')
                    print("\n--- Tool Call Successful ---")
                    print("Received Live Radio Stations:")
                    print(json.dumps(final_data, indent=2))
                    
                    # Parse into LiveContainer model
                    print("\n--- Parsing into LiveContainer ---")
                    live_container = LiveContainer.from_dict(final_data)
                    print(f"Number of stations: {len(live_container)}")
                    
                    for idx, station in enumerate(live_container.radioStations):
                        print(f"\nStation {idx + 1}:")
                        print(f"  Name: {station.name}")
                        print(f"  Status: {station.radioStationStatus}")
                        print(f"  DJ: {station.djName}")
                        print(f"  Preferred Voice: {station.tts.preferredVoice}")
                        print(f"  LLM Type: {station.prompt.llmType}")
                        print(f"  Search Engine: {station.prompt.searchEngineType}")
                    
                    # Test helper methods
                    print(f"\n--- Testing Helper Methods ---")
                    print(f"All station names: {live_container.get_all_station_names()}")
                    warming_up = live_container.get_stations_by_status("WARMING_UP")
                    print(f"Stations with WARMING_UP status: {len(warming_up)}")
                    
                    return

            print("Tool call returned an unexpected format.")

    except Exception as e:
        print(f"\n--- Exception ---")
        print(f"Exception type: {type(e).__name__}")
        print(f"Exception message: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
