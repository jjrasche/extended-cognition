import asyncio
import websockets
import json
import base64

async def test_connection():
    uri = "ws://localhost:8765"
    
    try:
        async with websockets.connect(uri) as websocket:
            # Wait for session info
            response = await websocket.recv()
            session_info = json.loads(response)
            print(f"✅ Connected! Session: {session_info['session_id']}")
            
            # Send recording start
            await websocket.send(json.dumps({
                "type": "recording_status",
                "status": "started"
            }))
            print("✅ Sent recording start")
            
            # Send a test audio chunk
            await websocket.send(json.dumps({
                "type": "audio_chunk",
                "audio": base64.b64encode(b"test").decode(),
                "sequence": 1
            }))
            print("✅ Sent test audio chunk")
            
            # Send stop recording
            await websocket.send(json.dumps({
                "type": "recording_status", 
                "status": "stopped"
            }))
            print("✅ Sent recording stop")
            
            print("✅ Test completed successfully!")
    except Exception as e:
        print(f"❌ Test failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_connection())
