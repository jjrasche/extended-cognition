# audio_capture_service.py
class AudioCaptureService:
    async def handle_websocket_stream(self, websocket):
        # Real-time chunk processing

    async def handle_file_upload(self, request):  
        # File chunking and processing

    async def process_audio_chunk(self, chunk, session_id):
        # Shared validation/formatting logic

    async def send_to_stt(self, formatted_chunk):
        # Unified STT interface