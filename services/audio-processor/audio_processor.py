# audio_processor.py
import asyncio
import aioredis as redis
import json
import base64
import os
from datetime import datetime
from groq import AsyncGroq
from typing import Dict, List, Optional
import logging
from collections import defaultdict

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AudioProcessor:
    def __init__(self):
        self.groq_client = AsyncGroq(api_key=os.getenv("GROQ_API_KEY"))
        self.redis_client = None
        
        # Stream names
        self.audio_stream = "audio_stream"
        self.transcript_stream = "transcript_stream"
        self.trigger_stream = "trigger_stream"
        
        # Session management
        self.sessions: Dict[str, dict] = defaultdict(lambda: {
            "audio_buffer": [],
            "transcript_buffer": "",
            "last_activity": datetime.utcnow(),
            "is_recording": True
        })
        
        # Trigger phrases and their associated prompts
        self.trigger_phrases = {
            "what do you think": "Analyze this thought and provide insights",
            "stop recording": None,  # Special case - ends recording
            "interesting": "Explore what makes this interesting and related implications",
            "summarize that": "Create a concise summary of the key points",
            "save that thought": "Mark this as important and create a formatted highlight"
        }
        
    async def init_redis(self):
        """Initialize Redis connection"""
        self.redis_client = await redis.Redis(
            host='localhost',
            port=6379,
            db=0,
            decode_responses=False
        )
    
    async def process_audio_stream(self):
        """Main processing loop for audio chunks"""
        while True:
            try:
                # Read from audio stream
                messages = await self.redis_client.xread(
                    {self.audio_stream: "$"},
                    block=100
                )
                
                for stream, msgs in messages:
                    for msg_id, fields in msgs:
                        await self.process_audio_chunk(fields)
                        
            except Exception as e:
                logger.error(f"Error in audio processing: {e}")
                await asyncio.sleep(1)
    
    async def process_audio_chunk(self, chunk_data: dict):
        """Process individual audio chunk"""
        session_id = chunk_data.get(b"session_id", b"").decode()
        audio_base64 = chunk_data.get(b"chunk", b"").decode()
        timestamp = chunk_data.get(b"timestamp", b"").decode()
        
        # Add to session buffer
        session = self.sessions[session_id]
        session["audio_buffer"].append({
            "audio": audio_base64,
            "timestamp": timestamp
        })
        session["last_activity"] = datetime.utcnow()
        
        # Process buffer if we have enough audio (e.g., 2 seconds worth)
        # For Phase 1, we'll use a simple chunk-based approach
        if len(session["audio_buffer"]) >= 20:  # Assuming ~100ms chunks
            await self.transcribe_buffer(session_id)
    
    async def transcribe_buffer(self, session_id: str):
        """Transcribe accumulated audio buffer using Groq"""
        session = self.sessions[session_id]
        
        if not session["audio_buffer"]:
            return
        
        try:
            # Combine audio chunks (in production, you'd properly concatenate audio)
            # For now, we'll process the last chunk as a simplification
            last_chunk = session["audio_buffer"][-1]
            audio_data = base64.b64decode(last_chunk["audio"])
            
            # Create temporary file for Groq API (it requires file upload)
            temp_filename = f"/tmp/audio_{session_id}_{datetime.utcnow().timestamp()}.wav"
            with open(temp_filename, "wb") as f:
                f.write(audio_data)
            
            # Transcribe using Groq
            with open(temp_filename, "rb") as audio_file:
                transcription = await self.groq_client.audio.transcriptions.create(
                    file=("audio.wav", audio_file.read()),
                    model="whisper-large-v3",
                    response_format="json",
                    language="en"
                )
            
            # Clean up temp file
            os.unlink(temp_filename)
            
            # Process transcription
            text = transcription.text.strip()
            if text:
                await self.process_transcription(session_id, text)
            
            # Clear processed buffer
            session["audio_buffer"] = []
            
        except Exception as e:
            logger.error(f"Transcription error for session {session_id}: {e}")
    
    async def process_transcription(self, session_id: str, text: str):
        """Process transcribed text for triggers and save to stream"""
        session = self.sessions[session_id]
        
        # Add to transcript buffer
        session["transcript_buffer"] += " " + text
        
        # Publish to transcript stream
        await self.redis_client.xadd(
            self.transcript_stream,
            {
                "session_id": session_id,
                "text": text,
                "timestamp": datetime.utcnow().isoformat()
            }
        )
        
        # Check for trigger phrases
        text_lower = text.lower()
        for trigger, prompt in self.trigger_phrases.items():
            if trigger in text_lower:
                await self.handle_trigger(session_id, trigger, prompt, text)
                break
    
    async def handle_trigger(self, session_id: str, trigger: str, prompt: Optional[str], full_text: str):
        """Handle detected trigger phrase"""
        logger.info(f"Trigger detected in session {session_id}: {trigger}")
        
        if trigger == "stop recording":
            # Special case - end recording
            await self.end_recording(session_id)
        else:
            # Send to LLM for processing
            trigger_data = {
                "session_id": session_id,
                "trigger": trigger,
                "prompt": prompt,
                "context": self.sessions[session_id]["transcript_buffer"][-1000:],  # Last 1000 chars
                "timestamp": datetime.utcnow().isoformat()
            }
            
            await self.redis_client.xadd(self.trigger_stream, trigger_data)
    
    async def end_recording(self, session_id: str):
        """Handle end of recording"""
        session = self.sessions[session_id]
        session["is_recording"] = False
        
        # Notify other services
        await self.redis_client.xadd(
            "recording_command_stream",
            {
                "session_id": session_id,
                "command": "recording_stopped",
                "timestamp": datetime.utcnow().isoformat()
            }
        )
        
        # Trigger conversation document generation
        await self.redis_client.xadd(
            "generate_document_stream",
            {
                "session_id": session_id,
                "transcript": session["transcript_buffer"],
                "timestamp": datetime.utcnow().isoformat()
            }
        )
    
    async def cleanup_inactive_sessions(self):
        """Clean up inactive sessions periodically"""
        while True:
            try:
                current_time = datetime.utcnow()
                inactive_sessions = []
                
                for session_id, session in self.sessions.items():
                    # Clean up sessions inactive for more than 1 hour
                    if (current_time - session["last_activity"]).seconds > 3600:
                        inactive_sessions.append(session_id)
                
                for session_id in inactive_sessions:
                    logger.info(f"Cleaning up inactive session: {session_id}")
                    del self.sessions[session_id]
                
                await asyncio.sleep(300)  # Check every 5 minutes
                
            except Exception as e:
                logger.error(f"Error in session cleanup: {e}")
                await asyncio.sleep(60)
    
    async def start(self):
        """Start the audio processor"""
        await self.init_redis()
        
        # Start background tasks
        asyncio.create_task(self.cleanup_inactive_sessions())
        
        # Start main processing loop
        logger.info("Starting audio processor...")
        await self.process_audio_stream()

async def main():
    processor = AudioProcessor()
    await processor.start()

if __name__ == "__main__":
    asyncio.run(main())