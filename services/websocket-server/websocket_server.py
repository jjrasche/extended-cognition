# websocket_server.py
import asyncio
import websockets
import json
import base64
import redis.asyncio as redis
from datetime import datetime
import logging
import os
from typing import Dict, Set
import uuid

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AudioStreamingServer:
    def __init__(self):
        self.redis_client = None
        self.active_sessions: Dict[str, dict] = {}
        self.audio_stream = "audio_stream"
        self.command_stream = "recording_command_stream"
        
    async def init_redis(self):
        """Initialize Redis connection"""
        redis_host = os.getenv('REDIS_URL', 'redis://localhost:6379').replace('redis://', '').split(':')[0]
        self.redis_client = redis.Redis(
            host=redis_host, 
            port=6379, 
            db=0,
            decode_responses=False  # We'll handle encoding ourselves
        )
        
    async def handle_client(self, websocket, path):
        """Handle WebSocket connection from Android client"""
        session_id = str(uuid.uuid4())
        client_info = {
            "websocket": websocket,
            "start_time": datetime.utcnow(),
            "status": "connected",
            "buffer": []  # Local buffer for disconnection handling
        }
        
        self.active_sessions[session_id] = client_info
        logger.info(f"New client connected: {session_id}")
        
        try:
            # Send session info to client
            await websocket.send(json.dumps({
                "type": "session_started",
                "session_id": session_id,
                "timestamp": datetime.utcnow().isoformat()
            }))
            
            # Listen for messages
            async for message in websocket:
                await self.process_message(session_id, message)
                
        except websockets.exceptions.ConnectionClosed:
            logger.info(f"Client disconnected: {session_id}")
        except Exception as e:
            logger.error(f"Error handling client {session_id}: {e}")
        finally:
            await self.cleanup_session(session_id)
    
    async def process_message(self, session_id: str, message: str):
        """Process incoming WebSocket message"""
        try:
            data = json.loads(message)
            message_type = data.get("type")
            
            if message_type == "audio_chunk":
                await self.handle_audio_chunk(session_id, data)
            elif message_type == "recording_status":
                await self.handle_recording_status(session_id, data)
            elif message_type == "ping":
                await self.handle_ping(session_id)
            else:
                logger.warning(f"Unknown message type: {message_type}")
                
        except json.JSONDecodeError:
            logger.error(f"Invalid JSON from session {session_id}")
        except Exception as e:
            logger.error(f"Error processing message: {e}")
    
    async def handle_audio_chunk(self, session_id: str, data: dict):
        """Handle incoming audio chunk"""
        audio_data = {
            "session_id": session_id,
            "chunk": data.get("audio"),  # base64 encoded
            "timestamp": data.get("timestamp", datetime.utcnow().isoformat()),
            "sequence": data.get("sequence", 0)
        }
        
        # Add to Redis stream for processing
        await self.redis_client.xadd(
            self.audio_stream,
            audio_data,
            maxlen=10000  # Keep last 10k chunks
        )
        
        # Also add to local buffer
        if session_id in self.active_sessions:
            self.active_sessions[session_id]["buffer"].append(audio_data)
            # Keep only last 100 chunks in memory
            if len(self.active_sessions[session_id]["buffer"]) > 100:
                self.active_sessions[session_id]["buffer"].pop(0)
    
    async def handle_recording_status(self, session_id: str, data: dict):
        """Handle recording start/stop commands"""
        status = data.get("status")  # "started" or "stopped"
        
        command_data = {
            "session_id": session_id,
            "command": f"recording_{status}",
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Publish to command stream
        await self.redis_client.xadd(self.command_stream, command_data)
        
        # Update session status
        if session_id in self.active_sessions:
            self.active_sessions[session_id]["status"] = status
            
        # Send acknowledgment
        ws = self.active_sessions[session_id]["websocket"]
        await ws.send(json.dumps({
            "type": "status_confirmed",
            "status": status,
            "timestamp": datetime.utcnow().isoformat()
        }))
    
    async def handle_ping(self, session_id: str):
        """Handle ping/keepalive"""
        if session_id in self.active_sessions:
            ws = self.active_sessions[session_id]["websocket"]
            await ws.send(json.dumps({
                "type": "pong",
                "timestamp": datetime.utcnow().isoformat()
            }))
    
    async def cleanup_session(self, session_id: str):
        """Clean up when client disconnects"""
        if session_id in self.active_sessions:
            # Save any buffered audio
            buffer = self.active_sessions[session_id]["buffer"]
            if buffer:
                logger.info(f"Saving {len(buffer)} buffered chunks for session {session_id}")
                # In production, you'd upload these to Google Drive
                
            # Notify other services that session ended
            await self.redis_client.xadd(
                self.command_stream,
                {
                    "session_id": session_id,
                    "command": "session_ended",
                    "timestamp": datetime.utcnow().isoformat()
                }
            )
            
            del self.active_sessions[session_id]
    
    async def send_to_client(self, session_id: str, message: dict):
        """Send message to specific client"""
        if session_id in self.active_sessions:
            ws = self.active_sessions[session_id]["websocket"]
            try:
                await ws.send(json.dumps(message))
            except Exception as e:
                logger.error(f"Error sending to client {session_id}: {e}")
    
    async def response_listener(self):
        """Listen for TTS responses to send back to clients"""
        while True:
            try:
                # Listen for audio responses
                messages = await self.redis_client.xread(
                    {"audio_response_stream": "$"},
                    block=100
                )
                
                for stream, msgs in messages:
                    for msg_id, fields in msgs:
                        session_id = fields.get(b"session_id", b"").decode()
                        audio_chunk = fields.get(b"chunk", b"").decode()
                        is_final = fields.get(b"is_final", b"false").decode() == "true"
                        
                        await self.send_to_client(session_id, {
                            "type": "audio_response",
                            "audio": audio_chunk,
                            "is_final": is_final,
                            "timestamp": datetime.utcnow().isoformat()
                        })
                        
            except Exception as e:
                logger.error(f"Error in response listener: {e}")
                await asyncio.sleep(1)
    
    async def conversation_complete_listener(self):
        """Listen for completed conversation documents"""
        while True:
            try:
                messages = await self.redis_client.xread(
                    {"conversation_complete_stream": "$"},
                    block=100
                )
                
                for stream, msgs in messages:
                    for msg_id, fields in msgs:
                        session_id = fields.get(b"session_id", b"").decode()
                        document_content = fields.get(b"content", b"").decode()
                        filename = fields.get(b"filename", b"").decode()
                        
                        await self.send_to_client(session_id, {
                            "type": "conversation_document",
                            "filename": filename,
                            "content": document_content,
                            "timestamp": datetime.utcnow().isoformat()
                        })
                        
            except Exception as e:
                logger.error(f"Error in document listener: {e}")
                await asyncio.sleep(1)
    
    async def start(self, host="0.0.0.0", port=8765):
        """Start the WebSocket server"""
        await self.init_redis()
        
        # Start response listeners
        asyncio.create_task(self.response_listener())
        asyncio.create_task(self.conversation_complete_listener())
        
        # Start WebSocket server
        logger.info(f"Starting WebSocket server on {host}:{port}")
        async with websockets.serve(self.handle_client, host, port):
            await asyncio.Future()  # Run forever

async def main():
    server = AudioStreamingServer()
    await server.start()

if __name__ == "__main__":
    asyncio.run(main())