# Phase 1: Personal Second Brain
> Minimal voice capture → transcription → LLM conversation system
> Target: Working prototype in 1 week

## Overview
Build a personal voice assistant that captures thoughts, continuously transcribes them, listens for trigger phrases, and saves complete conversation documents to your Obsidian second brain.

## Core User Flow
1. **Say "start recording** → Start recording
2. **Say "stop recording"** → Stop recording
3. **Every 60 seconds** → Subtle audio beep confirms still recording
4. Audio streams to backend for continuous processing
5. **Say trigger phrase** → Backend processes with appropriate LLM prompt
6. LLM response played through earbuds automatically
7. After recording stops → Complete conversation document sent to phone

## Architecture
```
Android App (No UI)
    ├── Hardware button listener
    ├── Audio recorder (streaming)
    ├── Status indicator (audio beep)
    └── WebSocket to backend
           ↓
    Supabase Backend
        ├── Edge Function (streaming)
        │   ├── Continuous Groq STT
        │   ├── Keyword detection
        │   ├── Groq LLM (on triggers)
        │   └── TTS responses
        ├── Google Drive (audio files)
        └── Generate conversation doc
               ↓
        Phone Obsidian Vault
            └── conversation-2025-06-27-143215.md
```

## Key Design Decisions

### Recording Control
- "start recording" voice command
- "Stop recording" voice command
- No automatic timeout - records until explicitly stopped
- Subtle beep every 60 seconds confirms recording active
- Notification shows recording status and duration

### Trigger Phrases & Prompts
| Phrase | LLM System Prompt |
|--------|-------------------|
| "What do you think?" | "Analyze this thought and provide insights" |
| "Stop Recording" | "Ends Conversation" |
| "Interesting" | "Explore what makes this interesting and related implications" |
| "Summarize that" | "Create a concise summary of the key points" |
| "Save that thought" | "Mark this as important and create a formatted highlight" |

### Storage Strategy
- **Audio files** → Google Drive (permanent backup)
- **Live transcripts** → Streamed to Google Drive 
- **Final conversation doc** → Sent to phone's Obsidian vault
- Each conversation creates one markdown file (not daily notes)

### Connection Handling
**Why local buffer?** If backend connection drops, audio keeps recording locally until reconnection

**Retry logic for connection interruptions:**
1. Detect disconnect → Switch to local recording
2. Show notification: "Connection lost, recording locally"
3. Retry connection every: 1s, 2s, 4s, 8s, 16s, 32s, then every 60s
4. On reconnect → Upload buffered audio, merge transcripts
5. User sees seamless transcript in final document

### Error Logging
**Why not SQLite?** You're right - a rolling log file is simpler:
- `/Android/data/com.extendedcognition/files/error.log`
- Rotate daily, keep last 7 days
- Log: connection errors, recording failures, timestamps

## Implementation Plan

### 1. Android App Components

**Architecture**: Wake Word Service + Foreground Recording Service

**Core Services**

**WakeWordService (Foreground Service)**
- Always listening for "Hey Cognition" using Porcupine
- ~1% battery usage per hour when idle
- Triggers RecordingService on wake word detection
- Shows minimal persistent notification: "Extended Cognition - Listening"

**RecordingService (Foreground Service)**
- Maintains WebSocket connection to backend (`ws://[backend-ip]:8765`)
- Handles audio recording via MediaRecorder
- Streams audio chunks in real-time
- Manages local buffer for disconnection resilience
- Receives and saves conversation documents
- Shows detailed notification with recording duration

**Notification UI**
- **Listening State**: "Extended Cognition - Listening"
- **Recording State**: "Recording: 2:34" with quick actions:
  - Stop Recording button
  - Pause/Resume button
  - Connection status indicator (green/yellow/red dot)
- Tapping notification opens minimal settings/status activity

**WebSocketManager**
- Manages connection lifecycle with automatic reconnection
- Exponential backoff: 1s → 2s → 4s → 8s → 16s → 32s → 60s
- Sends audio chunks as base64-encoded JSON
- Handles all message types:
  - `session_started` - Store session ID
  - `status_confirmed` - Update notification
  - `audio_response` - Play TTS through earbuds
  - `conversation_document` - Save to Obsidian folder
- Switches to local buffering on disconnection

**AudioStreamManager**
- Configures MediaRecorder for optimal settings:
  - Format: Opus (preferred) or AAC
  - Sample rate: 16kHz (for speech)
  - Mono channel
  - Bitrate: 32kbps
- Chunks audio into ~100ms segments
- Maintains 5MB circular buffer for offline recording
- Porcupine integration for "stop recording" detection

**File Reception**
- Listen for backend "conversation complete" message
- Receive markdown content via WebSocket
- Write to: `/storage/emulated/0/Documents/Obsidian/VaultName/conversations/`
- Filename: `conversation-YYYY-MM-DD-HHMMSS.md`

**Error Handling & Feedback**
- **Vibration Patterns**:
  - Wake word recognized: Short pulse (100ms)
  - Recording started: Double pulse (100ms × 2)
  - Connection lost: Three short pulses (50ms × 3)
  - Recording failed: Long buzz (500ms)
  - Reconnected: Two medium pulses (200ms × 2)
- **Visual Feedback**:
  - Notification color changes (green/yellow/red)
  - Status text updates in real-time
- **Audio Feedback**:
  - Subtle tone on wake word detection
  - Different tone for stop command

**Connection Flow**
1. App starts → WakeWordService begins listening
2. User says "Hey Cognition" → Vibration + tone feedback
3. RecordingService starts → Connects to WebSocket
4. Continuous audio streaming begins
5. Backend processes audio and triggers
6. TTS responses play automatically
7. User says "Stop recording" → Recording ends
8. Conversation document saved to Obsidian

**Error Handling**
- **Connection lost**: Switch to local recording, queue chunks
- **Reconnection**: Upload buffered audio, merge transcripts
- **Recording fails**: Vibrate alert (long buzz), log error
- **Server errors**: Exponential backoff retry (1s → 60s max)

**Permissions Required**
- `RECORD_AUDIO` - For microphone access
- `FOREGROUND_SERVICE` - For background services
- `INTERNET` - For WebSocket connection
- `WRITE_EXTERNAL_STORAGE` - For saving documents
- `VIBRATE` - For haptic feedback
- `WAKE_LOCK` - To keep wake word detection active

**User Experience**
- Zero-touch operation: Everything voice controlled
- Always ready: Wake word detection runs continuously
- Clear feedback: Vibration + notification shows status
- Resilient: Automatic reconnection and local buffering
- Minimal battery impact: ~1% idle, ~5% when recording
- Natural interaction: Just speak to start/stop

### 2. Backend Processing

**Streaming Pipeline**
1. Receive audio chunks via WebSocket
2. Stream to Groq STT for real-time transcription
3. Upload complete audio to Google Drive
4. Monitor transcript for trigger phrases
5. On trigger → Generate LLM response → TTS → Send audio back
6. On "stop recording" → Generate final document

**Conversation Document Generator**
After recording stops, create markdown with:
- Metadata (duration, word count, date/time)
- Full transcript with timestamps
- Google Drive audio link
- All LLM interactions inline
- Any "save that thought" highlights

### 3. Conversation Document Format

```markdown
# Conversation - 2025-06-27 14:32:15

**Duration:** 12:34  
**Audio:** [Google Drive Link](https://drive.google.com/...)

## Transcript

[00:00] I've been thinking about the architecture for extended cognition...

[00:45] What do you think?

### AI Response
That's a fascinating approach. The key insight about streaming...

[02:15] Good point about latency.

### AI Response  
Yes, latency is crucial because...

[03:22] Save that thought about using Redis streams.

### 💡 Saved Thought
"Using Redis streams for inter-service communication allows for natural backpressure and replay capabilities"

[05:30] Actually, interesting - what if we used WebSockets instead?

### AI Response
WebSockets would provide different tradeoffs...

[08:45] Summarize that.

### Summary
Key points discussed:
- Redis streams provide backpressure and replay
- WebSockets offer lower latency but less durability
- Hybrid approach might work best

[12:34] Stop recording.
```

## Success Metrics
- [ ] Voice command "stop recording" works reliably
- [ ] Connection interruptions don't lose any audio
- [ ] Trigger phrases detected within 2 seconds
- [ ] LLM responses play automatically without interaction
- [ ] Complete conversation document in Obsidian within 10s of stopping
- [ ] Google Drive backup link works immediately
- [ ] 60-second beep is audible but not disruptive