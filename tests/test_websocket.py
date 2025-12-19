#!/usr/bin/env python3
import asyncio
import websockets
import json


async def test_websocket():
    uri = "ws://localhost:8000/api/ws"
    print(f"Connecting to {uri}...")

    try:
        async with websockets.connect(uri) as websocket:
            print("Connected to WebSocket!")

            # Listen for messages
            while True:
                try:
                    message = await websocket.recv()
                    try:
                        data = json.loads(message)
                        print(f"Received: {data['type']} - {data.get('payload', {})}")
                    except json.JSONDecodeError as e:
                        print(f"Invalid JSON received: {message} - Error: {e}")
                except websockets.exceptions.ConnectionClosed:
                    print("WebSocket connection closed")
                    break

    except Exception as e:
        print(f"WebSocket connection failed: {e}")


if __name__ == "__main__":
    asyncio.run(test_websocket())
