# test_audio_backend.py
import asyncio
import websockets
import json
import base64
import wave
import time
from datetime import datetime

async def test_with_wav_file(wav_path, websocket_url="ws://localhost:8765"):
    """Test the backend by streaming a WAV file through WebSocket"""
    
    print(f"🎵 Loading WAV file: {wav_path}")
    
    # Read WAV file
    with wave.open(wav_path, 'rb') as wav_file:
        params = wav_file.getparams()
        frames = wav_file.readframes(params.nframes)
        
        print(f"📊 WAV Info:")
        print(f"   Sample rate: {params.framerate} Hz")
        print(f"   Channels: {params.nchannels}")
        print(f"   Duration: {params.nframes / params.framerate:.2f} seconds")
        print(f"   Total frames: {params.nframes}")
    
    # Calculate chunk size (~100ms of audio)
    chunk_duration_ms = 100
    bytes_per_sample = params.sampwidth
    chunk_size = int(params.framerate * params.nchannels * bytes_per_sample * chunk_duration_ms / 1000)
    
    print(f"\n🔌 Connecting to WebSocket at {websocket_url}...")
    
    async with websockets.connect(websocket_url) as websocket:
        # Wait for session info
        response = await websocket.recv()
        session_info = json.loads(response)
        print(f"✅ Connected! Session ID: {session_info['session_id']}")
        
        # Send recording started
        await websocket.send(json.dumps({
            "type": "recording_status",
            "status": "started"
        }))
        print("📼 Recording started")
        
        # Wait for acknowledgment
        ack = await websocket.recv()
        print(f"✅ Server acknowledged: {json.loads(ack)['status']}")
        
        # Stream audio in chunks
        print(f"\n📤 Streaming audio in {chunk_duration_ms}ms chunks...")
        
        total_chunks = len(frames) // chunk_size
        for i in range(0, len(frames), chunk_size):
            chunk = frames[i:i + chunk_size]
            
            # Convert chunk to base64
            chunk_base64 = base64.b64encode(chunk).decode('utf-8')
            
            # Send audio chunk
            await websocket.send(json.dumps({
                "type": "audio_chunk",
                "audio": chunk_base64,
                "sequence": i // chunk_size,
                "timestamp": datetime.utcnow().isoformat()
            }))
            
            # Progress indicator
            current_chunk = i // chunk_size
            if current_chunk % 10 == 0:
                progress = (current_chunk / total_chunks) * 100
                print(f"   Progress: {progress:.1f}% ({current_chunk}/{total_chunks} chunks)")
            
            # Simulate real-time streaming
            await asyncio.sleep(chunk_duration_ms / 1000)
        
        print("\n✅ Audio streaming complete")
        
        # Keep connection open to receive responses
        print("\n👂 Listening for transcripts and responses...")
        print("   (Will wait 10 seconds for processing)")
        
        # Listen for responses with timeout
        start_time = time.time()
        while time.time() - start_time < 10:
            try:
                message = await asyncio.wait_for(websocket.recv(), timeout=0.5)
                data = json.loads(message)
                
                if data.get("type") == "audio_response":
                    print(f"\n🔊 TTS Response received!")
                    print(f"   Is final: {data.get('is_final')}")
                elif data.get("type") == "conversation_document":
                    print(f"\n📄 Conversation document received!")
                    print(f"   Filename: {data.get('filename')}")
                    print(f"   Content preview: {data.get('content', '')[:200]}...")
                else:
                    print(f"\n📨 Message: {data}")
                    
            except asyncio.TimeoutError:
                continue
        
        # Send stop recording
        print("\n🛑 Sending stop recording...")
        await websocket.send(json.dumps({
            "type": "recording_status",
            "status": "stopped"
        }))
        
        # Wait a bit more for final responses
        await asyncio.sleep(2)
        
        print("\n✅ Test complete!")

async def monitor_redis_streams():
    """Monitor Redis streams to see what's happening"""
    import redis
    
    r = redis.Redis(host='localhost', port=6379, decode_responses=True)
    
    print("\n📊 Monitoring Redis streams...")
    print("   (Run this in a separate terminal while testing)")
    
    streams = [
        'audio_stream',
        'transcript_stream', 
        'trigger_stream',
        'llm_interaction_stream',
        'tts_request_stream',
        'conversation_complete_stream'
    ]
    
    last_ids = {stream: '$' for stream in streams}
    
    while True:
        try:
            # Read from all streams
            result = r.xread(last_ids, block=1000)
            
            for stream_name, messages in result:
                for msg_id, data in messages:
                    print(f"\n📨 [{stream_name}] {msg_id}")
                    for key, value in data.items():
                        if key in ['audio', 'chunk']:  # Skip binary data
                            print(f"   {key}: [binary data]")
                        else:
                            print(f"   {key}: {value[:100] if len(value) > 100 else value}")
                    
                    last_ids[stream_name] = msg_id
                    
        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"Error: {e}")
            await asyncio.sleep(1)

def main():
    import sys
    
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python test_audio_backend.py <wav_file>")
        print("  python test_audio_backend.py monitor")
        print("\nExample:")
        print("  python test_audio_backend.py recording.wav")
        print("  python test_audio_backend.py monitor  # Run in separate terminal")
        sys.exit(1)
    
    if sys.argv[1] == "monitor":
        asyncio.run(monitor_redis_streams())
    else:
        wav_file = sys.argv[1]
        
        # Check if file exists
        import os
        if not os.path.exists(wav_file):
            print(f"❌ Error: File '{wav_file}' not found")
            sys.exit(1)
        
        asyncio.run(test_with_wav_file(wav_file))

if __name__ == "__main__":
    main()