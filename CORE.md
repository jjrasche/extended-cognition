# Extended Cognition Core Project Document

> **Single Source of Truth** - Last Updated: June 22, 2025

## 🎯 Project North Star

**What**: A persistent deeply contextual voice-first AI companion that knows you deeply - remembering your thoughts, understanding your intent, and acting on your behalf in the digital world.

**Why**: 

- **Conversational** - How we currently interface with technology slows our thinking - clicking, tapping, scrolling, reading, navigating. Extended Cognition's voice-first approach removes that friction - just speak naturally while walking, driving, or with eyes closed. Enable stream-of-consciousness productivity with no barriers between your thoughts and your companion.

- **Act at Machine Speed** - We are not built to operate in the digital world. All our tools, from keyboards to screens, are a compromise forcing even the fastest users to read, type, click, navigate, and most of all wait. Extended Cognition allows you to build the trust necessary for your your companion to take action in the digital world on your behalf. Whether, moving funds, sending messages, ordering online, scheduling deliveries - your companion executes your intent at machine speed. Build trust in your companion's ability to handle the digital world so you can focus on the real world.

- **Data sovereignty** - We can't build deep trust with systems controlled by others. Extended Cognition is fully self-hosted - your data, your models, your control. Only when you own the system can you share freely enough for AI to truly help YOU.

- **Turn ideas into assets** - Automation and AI is erroding our economic potential. With every discussion, your companion extracts the insights, patterns, and wisdom that make you irreplaceable and adds it to your `knowledge base`. This collection of unique perspectives and connections become your primary economic asset. Your companion helps you capture and leverage this value. Build personal intellectual property and secure your ability to contribute to the future.

- **Perfect recall** - We've forgoten more than we can imagine. Extended Cognition has access to your full `knowledge base`, connecting today's thoughts to conversations from years ago, surfacing patterns in your relationships and thinking, and helping you build higher on foundations you've already laid.

- **Adapts to you** - Consumer products generalize to large markets and are difficult to make your own. Extended Cognition connects seamless feedback to update models and parameters, reducing misunderstandings, reinforcing desired behaviors, and adapting to your communication style. You're not just using a tool - you're training a companion.

- **Understand how it thinks** - We don't know what knwoledge forms the basis of AI inference. Extended Cognition reveals what assumptions your companion holds. From which portions of your `knowledge base` it's pulling from to how it percieves your emotional state, you see it all. Every fact is traceable and correctable.

**Demo Target**: September 2025 - Grand Rapids Tech Week - Showcase Extended Cognition as a useful thinking companion in meeting people and furthering my intent to advocate for and connect with contributors to this project.

## 🏗️ Architecture
### Layer-Based Pipeline Design
```
                              ┌─────────┐
┌─────────────┐               │  Audio  │
│ API Gateway ├──────────────►│ Capture │
└─────▲───────┘               └────┬────┘
      │                            │   ┌───────────┐
      │                            ├───┤    STT    │
      │                          audio └─────┬─────┘                  ┌──────────────┐
      │                            │         ├────────────────────────┤Command Parser│
      │                            │        text                      └──────┬───────┘ 
     web                           │         │                            command      
     RTC                           │         │                               │
      │                            │         │                        ┌──────┴───────┐
      │                          ┌─┴─────────┴┐                       │   Command    │
      │                          │  Thought   │                       │   Executor   │
      │                          │  Parser    │                       └───────┬──────┘
      │                          └─────┬──────┘                               │
┌─────┴──────┐                         │                                 command verify
│ Device PWA │                      thought                              or execution
└─────┬──────┘                         │                                      │
      │                    ┌───────────┼──────────┬─────────────┐             │
      │              ┌─────┴─────┐     │    ┌─────┴─────┐  ┌────┴─────┐       │
      │              │  Context  │     │    │ Emotional │  │  Intent  │       │
      │              │ Assembler │     │    │ Analyzer  │  │ Analyzer │       │
      │              └─────┬─────┘     │    └─────┬─────┘  └────┬─────┘       │
      │                    │           │          │             │             │
      │                knowledge       │         user          user           │
      │                 chunks         │       emotion        intent          │
      │                    │           │          │             │             │
      │                    └───────────┼──────────┴─────────────┘             │
      │                                │                                      │
      │                         ┌──────┴──────┐                               │
      │                         │ LLM Service │                               │
      │                         └──────┬──────┘                               │
      │                                │                                      │
      │                               AI                                      │
      │                             thought                                   │
      │                                │                                      │
      │                          ┌─────┴──────┐                               │
      │                          │ Interrupt  │                        ┌──────┴──────┐
      │                          │ Classifier ├───────yes──────────────┤ TTS Service │
      │                          └─────┬──────┘                        └──────┬──────┘
      │                                │                                     audio
      │                                no                                     │
      │                                │                                      │
      └─────────────cognition──────────┴──────────────────────────────────────┘
```
### Architectural Layers
| Layer                | Purpose                                        | Modules                                            |
| -------------------- | ---------------------------------------------- | -------------------------------------------------- |
| **Input Processing** | Capture and structure speech                   | Audio Capture, STT, Thought Parser                 |
| **Understanding**    | Extract meaning and context (thoughts only)    | User Intent, Context Assembler, Emotional Analyzer |
| **Agentic**          | Fast path for actions (bypasses understanding) | Command Parser, Command Executor                   |
| **Cognition**        | Form intelligent responses                     | LLM Service                                        |
| **Output**           | Determine response and deliver                 | Interrupt Classifier, TTS Service                  |


### Device-Side Modules:
| Module                     | Purpose                  | Output                      | Latency |
| -------------------------- | ------------------------ | --------------------------- | ------- |
| Audio Capture              | Continuous mic recording | Audio stream                | ~10ms   |
| Physical Context Collector | Sensor aggregation       | Activity + environment data | ~30ms   |
| Stream Manager             | WebSocket handling       | Bidirectional streams       | ~5ms    |

### Server-Side Module Details
| Module               | Purpose                                 | Output                  | Latency | Trainability                 |
| -------------------- | --------------------------------------- | ----------------------- | ------- | ---------------------------- |
| STT                  | Convert speech to text                  | Transcript + confidence | ~80ms   | High (vocabulary, accent)    |
| Thought Parser       | Identify thought boundaries             | Thoughts                | ~20ms   | High (pause patterns)        |
| User Intent          | Interpret what user wants               | Goal + topic analysis   | ~50ms   | Very High (context patterns) |
| Context Assembler    | Find relevant knowledge                 | RAG documents           | ~100ms  | High (relevance scoring)     |
| Emotional Analyzer   | Detect user state                       | Emotion + energy        | ~50ms   | High (baseline calibration)  |
| Command Parser       | Identify action requests                | Command list            | ~30ms   | Very High (custom commands)  |
| LLM Service          | Generate AI thoughts                    | AI thought + type       | ~400ms  | Medium (model selection)     |
| Interrupt Classifier | Decide whether to speak                 | yes/no decision         | ~20ms   | Very High (thresholds)       |
| Command Verifier     | Check permissions                       | Verification need       | ~10ms   | High (trust rules)           |
| TTS Service          | Generate speech (only on interrupt=yes) | Audio response          | ~200ms  | Medium (voice, emotion)      |
| Command Executor     | Run approved commands                   | Action results          | Varies  | Low (plugin-based)           |

**Command Path**: ~110ms to start execution (Audio → STT → Parser)  
**Thought Path**: ~650ms to interrupt decision (Audio → STT → Parser → Understanding → LLM → Classifier)  
**With TTS**: +200ms for audio response


### Key Design Decisions
1. **Server-side everything** - Processing power, speed, battery life constraints of mobile
2. **Thought as atomic unit** - Each user thought gets one complete AI cognition
3. **Two optimized paths** - Commands (~110ms) bypass thought processing, thoughts (~650ms) get full understanding

## 📊 Cognition Contract

Data structure representing a complete AI cognition in response to a user thought:
```json
{
  "thought_id": "uuid",
  "timestamp": 1719000000000,
  "session_id": "uuid-v4",
  
  // Raw inputs
  "audio_segment": "base64_chunk",
  "transcript": "what if we made the AI interruptible",
  
  // Understanding layer (all complete before LLM runs)
  "user_intent": {
    "interpreted_goal": "exploring system design for natural AI interruption",
    "confidence": 0.85,
    "topic_shift": false,
    "relates_to": ["thought_123", "thought_456"]  // Previous related thoughts
  },
  
  "rag_context": [{
    "doc_id": "interruption_patterns",
    "relevance": 0.92,
    "excerpt": "Natural conversation requires..."
  }],
  
  "user_emotion": {
    "primary": "curious",
    "energy": "high",
    "certainty": 0.7
  },
  
  "commands": [
    {
      "type": "create_note", 
      "confidence": 0.78, 
      "params": {...},
      "needs_verification": false
    }
  ],
  
  // Cognition layer (LLM response with full context)
  "ai_thought": {
    "content": "This connects to their earlier idea about flow",
    "confidence": 0.87,
    "type": "connection|question|insight|agreement|clarification|counterpoint"
  },
  
  // Decision layer
  "should_interrupt": false,
  
  // Output layer (only if interrupting)
  "audio_response": "base64_tts_audio"
}
```

## 🚧 Current Status & Immediate Priorities

### Working
- ✅ Repository structure established
- ✅ React PWA shell with package.json
- ✅ Cognition contracts defined
- ✅ Architecture documented

### Immediate Blocker (FOCUS HERE)
- 🔴 **WebRTC audio capture in React → WebSocket to Node.js API Gateway**
  - Need: Implement MediaStream API in React
  - Need: WebSocket connection to API Gateway
  - Need: Base64 audio chunk streaming
  
### Next Steps (After Blocker)
1. API Gateway WebSocket handler for audio streams
2. Audio archival to database
3. STT service integration (Whisper)
4. Basic round-trip: speak → transcribe → echo back text

## 🛠️ Technology Stack

### Infrastructure
- PostgreSQL for persistent storage (maybe)
- S3-compatible storage for audio archive
- Docker + Docker Compose for development
- In-memory cognition_stream (Redis Streams optional for scaling)

## Technical Metrics
- Command response: ~110ms to execution
- Thought response: ~650ms to decision, ~850ms with TTS
- Audio transcription accuracy: >90% (initial) → >98% (trained)
- Concurrent users: 20+ on Mac Mini M4 Pro


## 🚀 Development Phases

### [Phase 1](./Phase1.md)
### Phase 2: Intelligence Layer (August - September 2025)
**Goal**: Add understanding, thinking, and speaking capabilities

- [ ] **User Intent module**
  - Small model for goal detection
  - Topic tracking across thoughts
  - Confidence scoring
- [ ] **RAG engine integration**
  - Vector database setup
  - Document ingestion pipeline
  - Context retrieval based on thoughts
- [ ] **LLM Service**
  - Local model deployment (VLLM)
  - Prompt engineering for thoughts
  - Response generation
- [ ] **TTS integration**
  - Voice synthesis setup
  - Emotion in voice (future)
  - Stream audio back to device
- [ ] **Command Parser**
  - Basic command recognition
  - Fuzzy matching for variations
  - Command execution framework

**Milestone**: Have a real conversation with context from your notes

### Phase 3: Cognitive Enhancement (October - November 2025)
**Goal**: Make the AI feel like a true thought partner

- [ ] **Emotional Analyzer**
  - Audio feature extraction
  - Text sentiment analysis
  - User state tracking
- [ ] **Interrupt Classifier**
  - Timing algorithms
  - Confidence thresholds
  - User preference learning
- [ ] **Persistent AI memory**
  - Cross-session thought storage
  - AI opinion formation
  - Metacognitive loops
- [ ] **Command marketplace**
  - Plugin architecture
  - Permission system
  - User verification flow
- [ ] **Training interfaces**
  - Perception correction UI
  - Module-specific training
  - Personalization dashboard

**Milestone**: AI that knows you, thinks with you, and helps proactively

## 📁 Repository Structure
```
extended-cognition/
├── CORE.md                    # THIS DOCUMENT - Single source of truth
├── README.md                  # Public-facing documentation
├── docs/
│   ├── architecture/         # Detailed architecture docs
│   ├── api/                  # API documentation
│   └── development/          # Developer guides
├── packages/
│   ├── client-pwa/          # React PWA
│   ├── api-gateway/         # Node.js gateway
│   ├── stt-service/         # Python STT
│   ├── command-parser/      # Go parser
│   ├── llm-service/         # Python LLM
│   ├── tts-service/         # Python TTS
│   ├── rag-engine/          # Rust RAG
│   └── action-executor/     # Go executor
├── shared/
│   ├── contracts/           # Stream contract definitions
│   └── types/               # Shared TypeScript types
├── infrastructure/
│   ├── docker/              # Docker configurations
│   └── k8s/                 # Kubernetes manifests
└── scripts/                 # Build and deployment scripts
```

## 🎭 Core Innovation: Making AI Cognition Transparent

**Traditional AI**: Black box that produces responses
**Extended Cognition**: Glass box where you see every step of AI cognition

The architecture separates **reactive commands** (fast path) from **cognitive thoughts** (understanding path):
- Commands execute in ~110ms without waiting for understanding
- Thoughts get full context before AI responds (~650ms)
- Both paths merge in the cognition_stream back to device

The cognition_stream makes AI cognition transparent by recording:
- What the AI understood from your words
- What context it retrieved and why
- What it thought about what you said
- Why it decided to speak or stay silent
- What commands it detected and confidence levels

This transparency enables true partnership - you can correct the AI's understanding at any layer, making it learn your patterns over time. The system records the AI's cognition of YOUR thoughts, making the AI's cognitive process visible and trainable.

## 🔒 Constraints & Requirements
- Budget: <$10K hardware
- Privacy: All processing local
- Latency: Real-time conversation
- Scale: 20+ concurrent users
- Open source: Community-driven

## 🤝 Contributing
- Each microservice can be developed independently
- Follow stream contracts exactly
- Write tests for stream producers/consumers
- Document API changes in CORE.md first

### First Command: Perception Correction
The most important initial command allows users to correct AI perception in real-time:

```json
{
  "command": "correct_perception",
  "params": {
    "thought_id": "uuid",
    "correction_type": "user_intent|emotion|command|context",
    "correct_value": "I was being sarcastic, not serious",
    "train_module": true
  }
}
```

This creates a feedback loop where users see AI perception and correct it, making the system learn their patterns.

## ❓ Open Questions
1. Thought Parser algorithm for identifying thought boundaries?
2. Best approach for persistent AI memory across sessions?
3. Interrupt confidence threshold tuning?
4. Training data format for personalization?
5. Should cognition_stream be buffered or immediate streaming to device?

---

**Remember**: This document is the single source of truth. All other documentation should reference this. When in doubt, check CORE.md first.