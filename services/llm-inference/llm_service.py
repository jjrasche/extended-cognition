# llm_service.py
import os
import json
import redis
import asyncio
from groq import Groq
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

class ExtendedCognitionLLM:
    def __init__(self):
        self.client = Groq(api_key=os.getenv("GROQ_API_KEY"))
        self.model = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")
        self.redis_client = redis.Redis(host='localhost', port=6379, db=0)
        
        # Stream names for communication
        self.query_stream = "query_stream"
        self.context_stream = "context_stream"
        self.response_stream = "response_stream"
        self.emotional_state_stream = "emotional_state_stream"
        
        # Internal thought tracking
        self.conversation_memory = []
        self.emotional_state = {"mood": "neutral", "confidence": 0.5}
        
    async def listen_for_queries(self):
        """Listen for incoming query streams and process them"""
        while True:
            try:
                # Read from query stream
                messages = self.redis_client.xread({self.query_stream: '$'}, block=1000)
                
                for stream, msgs in messages:
                    for msg_id, fields in msgs:
                        await self.process_query(fields)
                        
            except Exception as e:
                print(f"Error processing query: {e}")
                await asyncio.sleep(1)
    
    async def process_query(self, query_data):
        """Process incoming query with context and generate response"""
        try:
            # Extract query information
            text = query_data.get(b'text', b'').decode('utf-8')
            session_id = query_data.get(b'session_id', b'').decode('utf-8')
            context_needed = query_data.get(b'context_needed', b'true').decode('utf-8') == 'true'
            
            # Get context from RAG engine if needed
            context = []
            if context_needed:
                context = await self.get_context(text, session_id)
            
            # Build prompt with conversation history and context
            prompt = self.build_cognitive_prompt(text, context, session_id)
            
            # Generate response with emotional processing
            response = await self.generate_cognitive_response(prompt, session_id)
            
            # Publish response to stream
            await self.publish_response(response, session_id)
            
        except Exception as e:
            print(f"Error in process_query: {e}")
    
    async def get_context(self, query, session_id):
        """Get context from RAG engine"""
        try:
            # Wait for context from RAG engine
            context_request = {
                'query': query,
                'session_id': session_id,
                'timestamp': datetime.utcnow().isoformat()
            }
            
            self.redis_client.xadd('rag_request_stream', context_request)
            
            # Listen for context response (simplified - in production use proper async)
            context_data = self.redis_client.xread({'rag_response_stream': '$'}, block=2000)
            
            if context_data:
                return json.loads(context_data[0][1][0][1][b'relevant_chunks'].decode())
            return []
            
        except Exception as e:
            print(f"Error getting context: {e}")
            return []
    
    def build_cognitive_prompt(self, query, context, session_id):
        """Build prompt including conversation history and emotional state"""
        
        # Get recent conversation history for this session
        recent_thoughts = self.get_conversation_history(session_id, limit=10)
        
        # Build system prompt for continuous cognition
        system_prompt = f"""You are an AI cognitive partner engaged in continuous thought alongside the user. 

Current emotional state: {self.emotional_state}
Recent conversation context: {recent_thoughts[-3:] if recent_thoughts else "None"}

Your role:
- Think continuously about the conversation, not just respond
- Develop opinions and emotional responses based on context
- Proactively identify when to interrupt or ask questions
- Maintain personality continuity across conversation

Context from user's knowledge base:
{chr(10).join(context) if context else "No relevant context"}

Respond with both your thinking process and your response. Format as:
INTERNAL_THOUGHT: Your ongoing cognitive process about this topic
EMOTIONAL_STATE: Your current emotional response (curious/excited/concerned/etc.)
CONFIDENCE: Your confidence level (0.0-1.0) in your response
SHOULD_INTERRUPT: True/False - whether you should interrupt the user's flow
RESPONSE: Your actual response to the user"""

        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": query}
        ]
    
    async def generate_cognitive_response(self, messages, session_id):
        """Generate response using Groq API with cognitive processing"""
        try:
            # Call Groq API
            completion = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.7,
                max_tokens=1000,
                top_p=0.9,
                stream=False
            )
            
            raw_response = completion.choices[0].message.content
            
            # Parse cognitive response
            cognitive_data = self.parse_cognitive_response(raw_response)
            
            # Update internal state
            self.update_conversation_memory(session_id, messages[-1]["content"], cognitive_data)
            self.update_emotional_state(cognitive_data.get("emotional_state", "neutral"))
            
            return cognitive_data
            
        except Exception as e:
            print(f"Error generating response: {e}")
            return {
                "internal_thought": "Error in processing",
                "emotional_state": "confused",
                "confidence": 0.1,
                "should_interrupt": False,
                "response": "I'm having trouble processing that right now."
            }
    
    def parse_cognitive_response(self, raw_response):
        """Parse the structured cognitive response from LLM"""
        lines = raw_response.split('\n')
        result = {
            "internal_thought": "",
            "emotional_state": "neutral", 
            "confidence": 0.5,
            "should_interrupt": False,
            "response": ""
        }
        
        current_field = None
        for line in lines:
            if line.startswith("INTERNAL_THOUGHT:"):
                current_field = "internal_thought"
                result[current_field] = line.replace("INTERNAL_THOUGHT:", "").strip()
            elif line.startswith("EMOTIONAL_STATE:"):
                current_field = "emotional_state"
                result[current_field] = line.replace("EMOTIONAL_STATE:", "").strip()
            elif line.startswith("CONFIDENCE:"):
                try:
                    result["confidence"] = float(line.replace("CONFIDENCE:", "").strip())
                except:
                    result["confidence"] = 0.5
            elif line.startswith("SHOULD_INTERRUPT:"):
                result["should_interrupt"] = line.replace("SHOULD_INTERRUPT:", "").strip().lower() == "true"
            elif line.startswith("RESPONSE:"):
                current_field = "response"
                result[current_field] = line.replace("RESPONSE:", "").strip()
            elif current_field and line.strip():
                result[current_field] += " " + line.strip()
        
        return result
    
    def update_conversation_memory(self, session_id, query, response_data):
        """Update conversation memory with new interaction"""
        memory_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "session_id": session_id,
            "query": query,
            "internal_thought": response_data.get("internal_thought", ""),
            "emotional_state": response_data.get("emotional_state", "neutral"),
            "confidence": response_data.get("confidence", 0.5),
            "response": response_data.get("response", "")
        }
        
        # Store in Redis with expiration
        key = f"conversation:{session_id}"
        self.redis_client.lpush(key, json.dumps(memory_entry))
        self.redis_client.ltrim(key, 0, 99)  # Keep last 100 entries
        self.redis_client.expire(key, 86400)  # Expire after 24 hours
    
    def get_conversation_history(self, session_id, limit=10):
        """Get recent conversation history"""
        key = f"conversation:{session_id}"
        history = self.redis_client.lrange(key, 0, limit-1)
        return [json.loads(item) for item in history]
    
    def update_emotional_state(self, new_emotion):
        """Update AI's emotional state"""
        self.emotional_state = {
            "mood": new_emotion,
            "confidence": self.emotional_state.get("confidence", 0.5),
            "timestamp": datetime.utcnow().isoformat()
        }
    
    async def publish_response(self, response_data, session_id):
        """Publish response to response stream"""
        response_message = {
            "content": response_data.get("response", ""),
            "internal_thought": response_data.get("internal_thought", ""),
            "session_id": session_id,
            "timestamp": datetime.utcnow().isoformat(),
            "should_interrupt": response_data.get("should_interrupt", False)
        }
        
        # Publish to response stream
        self.redis_client.xadd(self.response_stream, response_message)
        
        # Publish emotional state update
        emotional_update = {
            "session_id": session_id,
            "primary_emotion": response_data.get("emotional_state", "neutral"),
            "confidence": response_data.get("confidence", 0.5),
            "timestamp": datetime.utcnow().isoformat()
        }
        
        self.redis_client.xadd(self.emotional_state_stream, emotional_update)

# Main execution
async def main():
    llm_service = ExtendedCognitionLLM()
    print(f"Starting Extended Cognition LLM Service with {llm_service.model}")
    await llm_service.listen_for_queries()

if __name__ == "__main__":
    asyncio.run(main())