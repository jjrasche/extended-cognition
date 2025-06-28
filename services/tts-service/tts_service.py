# tts_service.py
import asyncio
import redis.asyncio as redis
import json
import base64
from datetime import datetime
from groq import AsyncGroq
import os
import logging
import io
from pydub import AudioSegment

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TTSService:
    def __init__(self):
        self.groq_client = AsyncGroq(api_key=os.getenv("GROQ_API_KEY"))
        self.redis_client = None
        
        # Stream names
        self.tts_request_stream = "tts_request_stream"
        self.audio_response_stream = "audio_response_stream"
        
        # Audio settings
        self.chunk_size = 4096  # Size of audio chunks to stream
        
    async def init_redis(self):
        """Initialize Redis connection"""
        redis_host = os.getenv('REDIS_URL', 'redis://localhost:6379').replace('redis://', '').split(':')[0]
        self.redis_client = redis.Redis(
        host=redis_host,
            port=6379,
            db=0,
            decode_responses=False
        )
    
    async def process_tts_requests(self):
        """Process TTS generation requests"""
        while True:
            try:
                messages = await self.redis_client.xread(
                    {self.tts_request_stream: "$"},
                    block=1000
                )
                
                for stream, msgs in messages:
                    for msg_id, fields in msgs:
                        await self.generate_tts(fields)
                        
            except Exception as e:
                logger.error(f"Error processing TTS requests: {e}")
                await asyncio.sleep(1)
    
    async def generate_tts(self, request_data: dict):
        """Generate TTS audio using Groq API"""
        session_id = request_data.get(b"session_id", b"").decode()
        text = request_data.get(b"text", b"").decode()
        voice = request_data.get(b"voice", b"nova").decode()
        
        logger.info(f"Generating TTS for session {session_id}: {text[:50]}...")
        
        try:
            # Generate audio using Groq TTS
            # Note: As of the implementation date, Groq might not have TTS yet
            # This is a placeholder for when it's available, or you can use another service
            
            # For Phase 1, we'll simulate with a simple approach
            # In production, you'd use actual TTS API
            audio_data = await self.generate_audio_placeholder(text, voice)
            
            # Stream audio chunks back to client
            await self.stream_audio_response(session_id, audio_data)
            
        except Exception as e:
            logger.error(f"Error generating TTS: {e}")
    
    async def generate_audio_placeholder(self, text: str, voice: str) -> bytes:
        """Placeholder for actual TTS generation"""
        # In production, this would call Groq TTS or another service like:
        # - OpenAI TTS
        # - ElevenLabs
        # - Azure Speech Services
        # - Local TTS like Coqui TTS
        
        # For now, return empty audio to complete the pipeline
        # You can integrate with your preferred TTS service here
        
        # Example with OpenAI TTS (if you want to use it):
        """
        from openai import AsyncOpenAI
        openai_client = AsyncOpenAI()
        
        response = await openai_client.audio.speech.create(
            model="tts-1",
            voice=voice,
            input=text
        )
        
        audio_data = response.content
        """
        
        # Return empty audio for now
        return b""
    
    async def stream_audio_response(self, session_id: str, audio_data: bytes):
        """Stream audio response in chunks"""
        if not audio_data:
            # Send empty response to indicate completion
            await self.redis_client.xadd(
                self.audio_response_stream,
                {
                    "session_id": session_id,
                    "chunk": "",
                    "is_final": "true",
                    "timestamp": datetime.utcnow().isoformat()
                }
            )
            return
        
        # Convert audio to base64 chunks
        audio_base64 = base64.b64encode(audio_data).decode()
        
        # Split into chunks for streaming
        chunks = [
            audio_base64[i:i + self.chunk_size] 
            for i in range(0, len(audio_base64), self.chunk_size)
        ]
        
        # Stream each chunk
        for i, chunk in enumerate(chunks):
            is_final = (i == len(chunks) - 1)
            
            await self.redis_client.xadd(
                self.audio_response_stream,
                {
                    "session_id": session_id,
                    "chunk": chunk,
                    "is_final": str(is_final).lower(),
                    "timestamp": datetime.utcnow().isoformat()
                }
            )
            
            # Small delay between chunks to simulate streaming
            await asyncio.sleep(0.01)
        
        logger.info(f"Streamed {len(chunks)} audio chunks for session {session_id}")
    
    async def start(self):
        """Start the TTS service"""
        await self.init_redis()
        
        logger.info("Starting TTS service...")
        await self.process_tts_requests()

async def main():
    service = TTSService()
    await service.start()

if __name__ == "__main__":
    asyncio.run(main())