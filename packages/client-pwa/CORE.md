# client-pwa CORE

> **Single Source of Truth** - Last Updated: 2025-06-25
> Layer: client | Language: react

## ?? Module Purpose

**What**: Progressive Web App for voice-first AI interaction with Extended Cognition

**Why**: Provides seamless voice interface for continuous thought streaming and AI collaboration

## ??? Architecture

```mermaid
graph LR
    A[Microphone] --> B[WebRTC Audio Capture]
    B --> C[WebSocket Client]
    C --> D[API Gateway]
    D --> E[Response Stream]
    E --> F[Audio Playback]
    E --> G[Visual Feedback]
```n
## ?? Module Structure
```nclient-pwa/
+-- CORE.md              # This file
+-- README.md            # Public documentation
+-- package.json         # Node dependencies
+-- src/
¦   +-- App.tsx         # Main app component
¦   +-- index.tsx       # Entry point
¦   +-- components/
¦   ¦   +-- AudioCapture.tsx    # WebRTC audio handling
¦   ¦   +-- ThoughtStream.tsx   # Visual thought display
¦   ¦   +-- ConnectionStatus.tsx # WebSocket status
¦   +-- hooks/
¦   ¦   +-- useWebSocket.ts     # WebSocket connection
¦   ¦   +-- useAudioStream.ts   # Audio streaming
¦   ¦   +-- useThoughts.ts      # Thought management
¦   +-- services/
¦       +-- webrtc.ts           # WebRTC utilities
¦       +-- api.ts              # API client
+-- public/
¦   +-- index.html
¦   +-- manifest.json    # PWA manifest
+-- Dockerfile
```n
## ?? Current Status

- [ ] React app initialized
- [ ] WebRTC audio capture
- [ ] WebSocket connection
- [ ] Audio streaming
- [ ] PWA configuration

## ?? Key Features

### Audio Capture
- Continuous microphone recording
- Audio chunking and encoding
- Voice activity detection

### Real-time Communication
- WebSocket for bidirectional streaming
- Low-latency audio transmission
- Connection resilience

### User Interface
- Minimal, voice-first design
- Visual feedback for audio levels
- Thought stream display
- Connection status indicator

## ?? PWA Requirements

- Service worker for offline capability
- HTTPS required for microphone access
- Mobile-responsive design
- Install prompt for add-to-home-screen

## ?? API Integration

**WebSocket Endpoint**: ws://localhost:3000/audio-stream`n
**Message Format**:
```json
{
  "type": "audio_chunk",
  "data": "base64_encoded_audio",
  "timestamp": 1234567890,
  "session_id": "uuid"
}
```n
## ?? Implementation Priority

1. **Basic React setup**
2. **WebRTC microphone access**
3. **WebSocket connection to API Gateway**
4. **Audio chunking and streaming**
5. **Visual feedback components**
6. **PWA configuration**
