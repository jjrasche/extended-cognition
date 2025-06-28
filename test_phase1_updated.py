import asyncio
import websockets
import json
import base64
import socket

async def test_connection():
    # Try different URIs
    uris = [
        "ws://localhost:8765",
        "ws://127.0.0.1:8765",
        "ws://host.docker.internal:8765",  # Sometimes needed on Windows
        "ws://0.0.0.0:8765"
    ]
    
    for uri in uris:
        print(f"\n🔌 Trying to connect to: {uri}")
        try:
            async with websockets.connect(uri, timeout=5) as websocket:
                # Wait for session info
                response = await websocket.recv()
                session_info = json.loads(response)
                print(f"✅ Connected to {uri}!")
                print(f"✅ Session: {session_info['session_id']}")
                
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
                return True
                
        except asyncio.TimeoutError:
            print(f"❌ Timeout connecting to {uri}")
        except ConnectionRefusedError:
            print(f"❌ Connection refused for {uri}")
        except Exception as e:
            print(f"❌ Error with {uri}: {type(e).__name__}: {e}")
    
    return False

def check_port():
    """Check if port 8765 is open"""
    print("\n🔍 Checking if port 8765 is open...")
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(2)
    
    for host in ['localhost', '127.0.0.1']:
        result = sock.connect_ex((host, 8765))
        if result == 0:
            print(f"✅ Port 8765 is open on {host}")
            sock.close()
            return True
        else:
            print(f"❌ Port 8765 is closed on {host} (error code: {result})")
    
    sock.close()
    return False

if __name__ == "__main__":
    print("🚀 Extended Cognition Phase 1 Connection Test")
    print("=" * 50)
    
    # First check if port is open
    port_open = check_port()
    
    if not port_open:
        print("\n⚠️  Port 8765 doesn't appear to be open.")
        print("Try running: docker-compose ps")
        print("And check if websocket-server is running with port 8765 mapped")
    
    # Try WebSocket connection regardless
    print("\n🌐 Testing WebSocket connections...")
    success = asyncio.run(test_connection())
    
    if not success:
        print("\n💡 Troubleshooting tips:")
        print("1. Check Docker Desktop is running")
        print("2. Run: docker logs extended-cognition-websocket-server-1")
        print("3. Try: docker-compose restart websocket-server")
        print("4. On Windows, sometimes you need to use the Docker machine IP")
        print("5. Check Windows Defender Firewall settings")