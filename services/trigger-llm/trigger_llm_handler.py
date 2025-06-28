# trigger_llm_handler.py
import asyncio
import redis.asyncio as redis
import json
from datetime import datetime
from groq import AsyncGroq
import os
import logging
from typing import Dict

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TriggerLLMHandler:
    def __init__(self):
        self.groq_client = AsyncGroq(api_key=os.getenv("GROQ_API_KEY"))
        self.redis_client = None
        self.model = os.getenv("GROQ_MODEL", "llama-3.1-70b-versatile")
        
        # Stream names
        self.trigger_stream = "trigger_stream"
        self.llm_interaction_stream = "llm_interaction_stream"
        self.tts_request_stream = "tts_request_stream"
        
        # System prompts for each trigger
        self.system_prompts = {
            "what do you think": """You are a thoughtful AI companion helping someone process their thoughts. 
Analyze what they've said and provide meaningful insights. Be concise but insightful. 
Focus on connections, implications, or perspectives they might not have considered.""",
            
            "interesting": """You are exploring what makes something interesting with your conversation partner.
Dig deeper into why this caught their attention and explore related implications or connections.
Be curious and help them discover what's compelling about this thought.""",
            
            "summarize that": """You are creating a concise summary of the key points discussed.
Extract the main ideas and present them in a clear, bulleted format.
Focus on actionable insights and important takeaways.""",
            
            "save that thought": """You are highlighting an important insight from the conversation.
Reframe the key thought in a clear, memorable way that captures its essence.
Make it suitable for future reference in their second brain."""
        }
    
    async def init_redis(self):
        """Initialize Redis connection"""
        redis_host = os.getenv('REDIS_URL', 'redis://localhost:6379').replace('redis://', '').split(':')[0]
        self.redis_client = redis.Redis(
        host=redis_host,
            port=6379,
            db=0,
            decode_responses=False
        )
    
    async def process_triggers(self):
        """Process trigger events from the audio processor"""
        while True:
            try:
                messages = await self.redis_client.xread(
                    {self.trigger_stream: "$"},
                    block=1000
                )
                
                for stream, msgs in messages:
                    for msg_id, fields in msgs:
                        await self.handle_trigger(fields)
                        
            except Exception as e:
                logger.error(f"Error processing triggers: {e}")
                await asyncio.sleep(1)
    
    async def handle_trigger(self, trigger_data: dict):
        """Process a single trigger and generate LLM response"""
        session_id = trigger_data.get(b"session_id", b"").decode()
        trigger = trigger_data.get(b"trigger", b"").decode()
        context = trigger_data.get(b"context", b"").decode()
        timestamp = trigger_data.get(b"timestamp", b"").decode()
        
        logger.info(f"Processing trigger '{trigger}' for session {session_id}")
        
        # Get the appropriate system prompt
        system_prompt = self.system_prompts.get(trigger, "You are a helpful AI assistant.")
        
        try:
            # Generate LLM response
            response = await self.generate_response(system_prompt, context)
            
            # Save interaction to stream
            interaction_data = {
                "session_id": session_id,
                "trigger": trigger,
                "user_text": context,
                "ai_response": response,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            await self.redis_client.xadd(
                self.llm_interaction_stream,
                interaction_data
            )
            
            # Request TTS for the response
            await self.request_tts(session_id, response)
            
        except Exception as e:
            logger.error(f"Error generating LLM response: {e}")
    
    async def generate_response(self, system_prompt: str, context: str) -> str:
        """Generate response using Groq LLM"""
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": context}
        ]
        
        completion = await self.groq_client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=0.7,
            max_tokens=500,
            top_p=0.9
        )
        
        return completion.choices[0].message.content.strip()
    
    async def request_tts(self, session_id: str, text: str):
        """Request TTS generation for the response"""
        tts_request = {
            "session_id": session_id,
            "text": text,
            "voice": "nova",  # Groq TTS voice option
            "timestamp": datetime.utcnow().isoformat()
        }
        
        await self.redis_client.xadd(self.tts_request_stream, tts_request)
        logger.info(f"TTS requested for session {session_id}")
    
    async def start(self):
        """Start the trigger handler"""
        await self.init_redis()
        
        logger.info("Starting trigger-based LLM handler...")
        await self.process_triggers()

async def main():
    handler = TriggerLLMHandler()
    await handler.start()

if __name__ == "__main__":
    asyncio.run(main())