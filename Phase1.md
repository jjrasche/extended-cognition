# Phase 1: Personal Second Brain
> Minimal voice capture → transcription → LLM conversation system
> Target: Working prototype in 1 week

## Overview
Build a personal voice assistant that captures thoughts via hardware button toggle, continuously transcribes them, listens for trigger phrases, and saves complete conversation documents to your Obsidian second brain.

## Core User Flow
1. **Long press volume up** → Start recording
2. **Say "stop recording" OR long press volume up** → Stop recording
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
- Long press volume up starts recording
- "Stop recording" voice command OR long press stops it
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

**Background Service**
- Foreground service with persistent notification
- WebSocket client for streaming audio
- Local audio buffer (5MB rotating) for disconnections
- Voice command detection for "stop recording"
- Error logging to rotating file

**Audio Flow**
```
Microphone → MediaRecorder → WebSocket (if connected)
                          ↘ Local Buffer (if disconnected)
```

**File Reception**
- Listen for backend "conversation complete" message
- Receive markdown content via WebSocket
- Write to: `/storage/emulated/0/Documents/Obsidian/VaultName/conversations/`
- Filename: `conversation-YYYY-MM-DD-HHMMSS.md`

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