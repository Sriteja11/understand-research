# Cactus Compute Whistle Audio Input Integration

This specification describes the integration of **Cactus Compute Whistle** (`cactus-needle`) into **Understand Research** for real-time, on-device audio and speech input.

## Features
- **16.9 MB CPU Speech Recognition**: Runs locally with zero external network or GPU dependency.
- **Microphone Voice Queries**: Click-to-record voice questions directly in the chat interface.
- **Sub-50ms Transcription**: Near-instantaneous response times powered by Whistle's C++ inference engine.
- **AI Domain Keyword Biasing**: Research vocabulary (Transformer, Attention, RAG, ReAct, ChromaDB, etc.) is automatically biased using Aho-Corasick matching during beam search.
- **Audio File Upload**: Upload `.wav` voice memos or discussion clips.

For the full architectural specification, refer to the project documentation.
