import asyncio
import websockets
import json
import socket


def test_tcp_connection():
    """Test basic TCP connection"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        result = sock.connect_ex(('localhost', 38708))
        sock.close()
        if result == 0:
            print("✓ TCP connection successful")
            return True
        else:
            print(f"✗ TCP connection failed: {result}")
            return False
    except Exception as e:
        print(f"✗ TCP connection error: {e}")
        return False


def test_basic_connection():
    """Test WebSocket connection with debugging"""
    if not test_tcp_connection():
        return

    uri = "ws://localhost:38708"

    async def run_test():
        try:
            print(f"Attempting WebSocket connection to {uri}...")

            # Try with explicit timeout and logging
            websocket = await websockets.connect(
                uri,
                close_timeout=10,
                ping_timeout=20,
                ping_interval=None
            )

            print("✓ WebSocket connection successful")

            test_message = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "clientInfo": {
                        "name": "Test-Client",
                        "version": "1.0.0"
                    },
                    "capabilities": {}
                }
            }

            await websocket.send(json.dumps(test_message))
            print("✓ Message sent")

            # Wait for response with timeout
            response = await asyncio.wait_for(websocket.recv(), timeout=10)
            print(f"✓ Response received: {response}")

            await websocket.close()
            print("✓ Connection closed cleanly")

        except websockets.exceptions.InvalidHandshake as e:
            print(f"✗ WebSocket handshake failed: {e}")
            print(f"   Status: {e.status_code if hasattr(e, 'status_code') else 'unknown'}")
            print(f"   Headers: {e.response_headers if hasattr(e, 'response_headers') else 'unknown'}")
        except asyncio.TimeoutError:
            print("✗ Timeout during WebSocket operation")
        except Exception as e:
            print(f"✗ WebSocket error: {type(e).__name__}: {e}")

    try:
        asyncio.run(run_test())
    except Exception as e:
        print(f"✗ Async error: {e}")


if __name__ == "__main__":
    test_basic_connection()