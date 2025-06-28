import asyncio
import websockets
import json

async def test_websocket():
    uri = "ws://127.0.0.1:8765"  # Use 127.0.0.1 instead of localhost
    
    print(f"🔌 Connecting to {uri}...")
    
    try:
        async with websockets.connect(uri) as websocket:
            print("✅ Connected!")
            
            # Wait for initial session message
            message = await websocket.recv()
            data = json.loads(message)
            print(f"✅ Received session info: {data}")
            
            # Send a simple ping
            await websocket.send(json.dumps({"type": "ping"}))
            print("✅ Sent ping")
            
            # Wait for pong
            response = await websocket.recv()
            print(f"✅ Received response: {response}")
            
            print("\n🎉 WebSocket connection successful!")
            return True
            
    except Exception as e:
        print(f"❌ Error: {type(e).__name__}: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Simple WebSocket Connection Test")
    print("=" * 40)
    
    success = asyncio.run(test_websocket())
    
    if not success:
        print("\n💡 Try these alternatives:")
        print("1. python -m pip install --upgrade websockets")
        print("2. Restart Docker Desktop")
        print("3. In PowerShell as Administrator:")
        print("   New-NetFirewallRule -DisplayName 'Docker WebSocket' -Direction Inbound -Protocol TCP -LocalPort 8765 -Action Allow")