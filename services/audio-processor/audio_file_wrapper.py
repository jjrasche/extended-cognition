# audio_file_wrapper.py
import redis
import base64
import uuid
from datetime import datetime
import time
from pydub import AudioSegment
import sys
import os

def process_audio_file(audio_file_path, session_id=None):
    """
    Process any audio file and send it through the Redis pipeline
    
    Args:
        audio_file_path: Path to audio file (m4a, mp3, wav, ogg, flac, etc.)
        session_id: Optional session ID (generates one if not provided)
    """
    
    # Connect to Redis
    r = redis.Redis(host='localhost', port=6379, db=0)
    
    # Generate session ID if not provided
    if not session_id:
        session_id = str(uuid.uuid4())
    
    print(f"🎵 Processing: {audio_file_path}")
    print(f"📋 Session ID: {session_id}")
    
    try:
        # Load audio file (pydub auto-detects format)
        print("📂 Loading audio file...")
        audio = AudioSegment.from_file(audio_file_path)
        
        # Get original info
        duration_seconds = len(audio) / 1000.0
        print(f"⏱️  Duration: {duration_seconds:.2f} seconds")
        print(f"📊 Original format: {audio.frame_rate}Hz, {audio.channels} channel(s)")
        
        # Convert to required format: 16kHz, mono, 16-bit
        print("🔄 Converting to 16kHz mono...")
        audio = audio.set_frame_rate(16000).set_channels(1).set_sample_width(2)
        
        # Get raw PCM data
        raw_audio = audio.raw_data
        
        # Calculate chunk parameters
        chunk_duration_ms = 100  # 100ms chunks
        sample_rate = 16000
        bytes_per_sample = 2
        channels = 1
        chunk_size = int(sample_rate * channels * bytes_per_sample * chunk_duration_ms / 1000)
        
        total_chunks = len(raw_audio) // chunk_size
        print(f"📦 Splitting into {total_chunks} chunks of {chunk_duration_ms}ms each")
        
        # Send start recording event (simulating what the app would do)
        r.xadd('recording_command_stream', {
            'session_id': session_id,
            'command': 'recording_started',
            'timestamp': datetime.utcnow().isoformat()
        })
        
        # Send chunks to Redis
        print("\n📤 Sending chunks to Redis...")
        start_time = time.time()
        
        for i in range(0, len(raw_audio), chunk_size):
            chunk = raw_audio[i:i + chunk_size]
            
            # Pad last chunk if needed
            if len(chunk) < chunk_size:
                chunk = chunk + b'\x00' * (chunk_size - len(chunk))
            
            # Create message
            message = {
                'session_id': session_id,
                'chunk': base64.b64encode(chunk).decode('utf-8'),
                'timestamp': datetime.utcnow().isoformat(),
                'sequence': str(i // chunk_size)
            }
            
            # Send to Redis stream
            r.xadd('audio_stream', message)
            
            # Progress indicator
            if (i // chunk_size) % 50 == 0:  # Every 5 seconds
                progress = ((i // chunk_size) / total_chunks) * 100
                elapsed = (i // chunk_size) * chunk_duration_ms / 1000
                print(f"   Progress: {progress:.1f}% ({elapsed:.1f}s / {duration_seconds:.1f}s)")
            
            # Optional: Add small delay to simulate real-time streaming
            # time.sleep(0.01)  # Uncomment for more realistic streaming
        
        print(f"\n✅ All chunks sent in {time.time() - start_time:.2f} seconds")
        
        # Monitor transcript stream
        print("\n📝 Monitoring transcripts...")
        print("=" * 50)
        
        transcripts = []
        last_id = '0'
        start_monitor = time.time()
        timeout = duration_seconds + 30  # Wait for duration + 30 seconds
        
        while time.time() - start_monitor < timeout:
            try:
                # Read from transcript stream
                messages = r.xread({'transcript_stream': last_id}, block=1000, count=100)
                
                if not messages:
                    continue
                
                for stream_name, stream_messages in messages:
                    for msg_id, data in stream_messages:
                        # Check if it's our session
                        msg_session_id = data.get(b'session_id', b'').decode()
                        if msg_session_id == session_id:
                            text = data.get(b'text', b'').decode()
                            timestamp = data.get(b'timestamp', b'').decode()
                            
                            transcripts.append({
                                'text': text,
                                'timestamp': timestamp
                            })
                            
                            # Print transcript as it arrives
                            print(f"[{len(transcripts)}] {text}")
                        
                        last_id = msg_id
                
                # Check if we've received transcripts recently
                if transcripts and time.time() - start_monitor > 5:
                    # If no new transcripts for 5 seconds, we're probably done
                    last_transcript_time = datetime.fromisoformat(transcripts[-1]['timestamp'])
                    if (datetime.utcnow() - last_transcript_time).seconds > 5:
                        print("\n⏸️  No new transcripts for 5 seconds, assuming complete")
                        break
                        
            except KeyboardInterrupt:
                print("\n\n⚠️  Interrupted by user")
                break
            except Exception as e:
                print(f"❌ Error monitoring transcripts: {e}")
                time.sleep(1)
        
        # Send stop recording event
        r.xadd('recording_command_stream', {
            'session_id': session_id,
            'command': 'recording_stopped',
            'timestamp': datetime.utcnow().isoformat()
        })
        
        # Combine all transcripts
        print("\n" + "=" * 50)
        print("📄 COMPLETE TRANSCRIPT:")
        print("=" * 50)
        
        full_transcript = ' '.join([t['text'] for t in transcripts])
        print(full_transcript)
        
        # Save to file
        output_file = f"{os.path.splitext(audio_file_path)[0]}_transcript.txt"
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(f"Audio File: {audio_file_path}\n")
            f.write(f"Session ID: {session_id}\n")
            f.write(f"Duration: {duration_seconds:.2f} seconds\n")
            f.write(f"Transcript segments: {len(transcripts)}\n")
            f.write("=" * 50 + "\n\n")
            f.write(full_transcript)
        
        print(f"\n💾 Transcript saved to: {output_file}")
        
        # Stats
        print(f"\n📊 Statistics:")
        print(f"   Total chunks sent: {total_chunks}")
        print(f"   Transcript segments: {len(transcripts)}")
        print(f"   Processing time: {time.time() - start_time:.2f} seconds")
        
    except FileNotFoundError:
        print(f"❌ Error: File '{audio_file_path}' not found")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error processing audio: {e}")
        print("\nMake sure:")
        print("1. Redis is running (docker-compose up redis)")
        print("2. Audio processor is running (docker-compose up audio-processor)")
        print("3. You have pydub installed (pip install pydub)")
        print("4. You have ffmpeg installed")
        sys.exit(1)

def main():
    if len(sys.argv) < 2:
        print("Audio File Wrapper for Extended Cognition")
        print("=" * 40)
        print("\nUsage: python audio_file_wrapper.py <audio_file> [session_id]")
        print("\nSupported formats: WAV, M4A, MP3, OGG, FLAC, AAC, WMA, AIFF")
        print("\nExamples:")
        print('  python audio_file_wrapper.py "New Recording.m4a"')
        print('  python audio_file_wrapper.py recording.wav')
        print('  python audio_file_wrapper.py audio.mp3 custom-session-123')
        sys.exit(1)
    
    audio_file = sys.argv[1]
    session_id = sys.argv[2] if len(sys.argv) > 2 else None
    
    # Check dependencies
    try:
        import pydub
        import redis
    except ImportError as e:
        print(f"❌ Missing dependency: {e}")
        print("\nInstall with:")
        print("  pip install pydub redis")
        sys.exit(1)
    
    process_audio_file(audio_file, session_id)

if __name__ == "__main__":
    main()