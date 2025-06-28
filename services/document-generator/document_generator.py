# document_generator.py
import asyncio
import redis.asyncio as redis
import json
from datetime import datetime
from typing import Dict, List
import logging
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaInMemoryUpload
import os
import re

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ConversationDocumentGenerator:
    def __init__(self):
        self.redis_client = None
        self.drive_service = None
        
        # Stream names
        self.generate_stream = "generate_document_stream"
        self.transcript_stream = "transcript_stream"
        self.llm_interaction_stream = "llm_interaction_stream"
        self.conversation_complete_stream = "conversation_complete_stream"
        
        # Google Drive folder for audio backups
        self.audio_folder_id = os.getenv("GOOGLE_DRIVE_AUDIO_FOLDER_ID")
        
    async def init_redis(self):
        """Initialize Redis connection"""
        redis_host = os.getenv('REDIS_URL', 'redis://localhost:6379').replace('redis://', '').split(':')[0]
        self.redis_client = redis.Redis(
        host=redis_host,
            port=6379,
            db=0,
            decode_responses=False
        )
    
    def init_google_drive(self):
        """Initialize Google Drive API"""
        try:
            # Use service account credentials
            if os.path.exists('service-account-key.json'):
                creds = service_account.Credentials.from_service_account_file(
                    'service-account-key.json',
                    scopes=['https://www.googleapis.com/auth/drive.file']
                )
                self.drive_service = build('drive', 'v3', credentials=creds)
                logger.info("Google Drive API initialized successfully")
            else:
                logger.warning("No service-account-key.json found - Google Drive uploads disabled")
                logger.warning("Run setup_google_drive.sh to enable Google Drive integration")
                self.drive_service = None
        except Exception as e:
            logger.error(f"Failed to initialize Google Drive: {e}")
            self.drive_service = None
    
    async def process_generation_requests(self):
        """Process requests to generate conversation documents"""
        while True:
            try:
                messages = await self.redis_client.xread(
                    {self.generate_stream: "$"},
                    block=1000
                )
                
                for stream, msgs in messages:
                    for msg_id, fields in msgs:
                        await self.generate_document(fields)
                        
            except Exception as e:
                logger.error(f"Error processing generation request: {e}")
                await asyncio.sleep(1)
    
    async def generate_document(self, request_data: dict):
        """Generate a complete conversation document"""
        session_id = request_data.get(b"session_id", b"").decode()
        timestamp = request_data.get(b"timestamp", b"").decode()
        
        logger.info(f"Generating document for session {session_id}")
        
        try:
            # Gather all data for this session
            transcript_data = await self.get_session_transcripts(session_id)
            llm_interactions = await self.get_llm_interactions(session_id)
            audio_url = await self.get_audio_backup_url(session_id)
            
            # Build the markdown document
            document = self.build_markdown_document(
                session_id, 
                transcript_data, 
                llm_interactions,
                audio_url
            )
            
            # Generate filename
            start_time = transcript_data[0]["timestamp"] if transcript_data else datetime.utcnow()
            filename = f"conversation-{start_time.strftime('%Y-%m-%d-%H%M%S')}.md"
            
            # Send to client via WebSocket
            await self.redis_client.xadd(
                self.conversation_complete_stream,
                {
                    "session_id": session_id,
                    "filename": filename,
                    "content": document,
                    "timestamp": datetime.utcnow().isoformat()
                }
            )
            
            logger.info(f"Document generated for session {session_id}")
            
        except Exception as e:
            logger.error(f"Error generating document for session {session_id}: {e}")
    
    async def get_session_transcripts(self, session_id: str) -> List[Dict]:
        """Get all transcripts for a session"""
        transcripts = []
        
        # Read entire transcript stream and filter by session
        # In production, you'd use a more efficient approach
        messages = await self.redis_client.xrange(self.transcript_stream)
        
        for msg_id, fields in messages:
            if fields.get(b"session_id", b"").decode() == session_id:
                transcripts.append({
                    "text": fields.get(b"text", b"").decode(),
                    "timestamp": datetime.fromisoformat(
                        fields.get(b"timestamp", b"").decode()
                    )
                })
        
        return sorted(transcripts, key=lambda x: x["timestamp"])
    
    async def get_llm_interactions(self, session_id: str) -> List[Dict]:
        """Get all LLM interactions for a session"""
        interactions = []
        
        messages = await self.redis_client.xrange(self.llm_interaction_stream)
        
        for msg_id, fields in messages:
            if fields.get(b"session_id", b"").decode() == session_id:
                interactions.append({
                    "trigger": fields.get(b"trigger", b"").decode(),
                    "user_text": fields.get(b"user_text", b"").decode(),
                    "ai_response": fields.get(b"ai_response", b"").decode(),
                    "timestamp": datetime.fromisoformat(
                        fields.get(b"timestamp", b"").decode()
                    )
                })
        
        return sorted(interactions, key=lambda x: x["timestamp"])
    
    async def get_audio_backup_url(self, session_id: str) -> str:
        """Get Google Drive URL for audio backup"""
        if self.drive_service is None:
            return "[Google Drive not configured - audio backup unavailable]"
        
        # In Phase 1, return placeholder
        # TODO: Implement actual audio upload here
        return f"https://drive.google.com/file/d/placeholder_{session_id}"
    
    def build_markdown_document(
        self, 
        session_id: str, 
        transcripts: List[Dict], 
        llm_interactions: List[Dict],
        audio_url: str
    ) -> str:
        """Build the markdown document"""
        if not transcripts:
            return "# Empty Conversation\n\nNo transcripts found."
        
        # Calculate duration
        start_time = transcripts[0]["timestamp"]
        end_time = transcripts[-1]["timestamp"]
        duration = end_time - start_time
        duration_str = f"{duration.seconds // 60}:{duration.seconds % 60:02d}"
        
        # Calculate word count
        total_words = sum(len(t["text"].split()) for t in transcripts)
        
        # Build document
        doc = f"""# Conversation - {start_time.strftime('%Y-%m-%d %H:%M:%S')}

**Duration:** {duration_str}  
**Audio:** [Google Drive Link]({audio_url})

## Transcript

"""
        
        # Merge transcripts and interactions chronologically
        all_events = []
        
        # Add transcripts
        for t in transcripts:
            all_events.append({
                "type": "transcript",
                "timestamp": t["timestamp"],
                "content": t["text"]
            })
        
        # Add LLM interactions
        for i in llm_interactions:
            all_events.append({
                "type": "interaction",
                "timestamp": i["timestamp"],
                "trigger": i["trigger"],
                "user_text": i["user_text"],
                "ai_response": i["ai_response"]
            })
        
        # Sort by timestamp
        all_events.sort(key=lambda x: x["timestamp"])
        
        # Build the transcript section
        current_text = ""
        for event in all_events:
            if event["type"] == "transcript":
                # Calculate time offset
                offset = event["timestamp"] - start_time
                time_str = f"[{offset.seconds // 60:02d}:{offset.seconds % 60:02d}]"
                
                current_text += f"{time_str} {event['content']}\n\n"
                doc += current_text
                current_text = ""
                
            elif event["type"] == "interaction":
                # Add any pending text first
                if current_text:
                    doc += current_text + "\n"
                    current_text = ""
                
                # Format based on trigger type
                if event["trigger"] == "save that thought":
                    doc += f"### 💡 Saved Thought\n\"{event['ai_response']}\"\n\n"
                elif event["trigger"] == "summarize that":
                    doc += f"### Summary\n{event['ai_response']}\n\n"
                else:
                    doc += f"### AI Response\n{event['ai_response']}\n\n"
        
        # Add any remaining text
        if current_text:
            doc += current_text
        
        return doc
    
    async def start(self):
        """Start the document generator"""
        await self.init_redis()
        self.init_google_drive()
        
        logger.info("Starting conversation document generator...")
        await self.process_generation_requests()

async def main():
    generator = ConversationDocumentGenerator()
    await generator.start()

if __name__ == "__main__":
    asyncio.run(main())