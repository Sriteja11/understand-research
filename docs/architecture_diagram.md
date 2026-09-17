# Architecture diagram

![System Architecture](architecture.png)

This document outlines the system architecture of the Evidence-Grounded AI Research Assistant.
You can copy the Mermaid code block below and paste it directly into [Excalidraw](https://excalidraw.com) via **More Tools -> Mermaid to Excalidraw** or render it in any Markdown viewer.

## System architecture

```mermaid
flowchart TD
    subgraph UI["Frontend Client (React + Vite + Tailwind CSS)"]
        ChatUI["Chat View (/chat/:sessionId)\nMarkdown Renderer, SSE Reader, Citations"]
        DocsUI["Documents View (/documents)\nPDF/TXT/MD Upload, Ingestion Progress"]
        EvalUI["Evaluation View (/evaluation)\n20-Case Benchmark, Metric Cards"]
    end

    subgraph API["FastAPI Application Server"]
        SPA["SPA Navigation Middleware\nHTML Fallback & Static Assets"]
        ChatRouter["Chat Router\nPOST /chat (SSE) & POST /chat/sync"]
        DocRouter["Documents Router\nUpload, List, Delete, SSE Status"]
        SessRouter["Sessions Router\nCRUD Session State & History"]
        EvalRouter["Evaluation Router\nGET /evaluation & POST /evaluation/run"]
        SecFilter["Security Layer\nInjection Scanner & Input Sanitizer"]
    end

    subgraph Storage["Persistent Storage"]
        SQLite[("SQLite DB (app.db)\nSessions, Messages, Evaluation Logs")]
        VectorStore[("ChromaDB Vector Store\n384-dim Embeddings & Metadata")]
        DocStore[("File Storage\nSeed Documents & User Uploads")]
    end

    subgraph Ingestion["Document Ingestion Pipeline"]
        Parsers["Document Parsers\nPyMuPDF, TextParser, MarkdownParser"]
        Cleaner["Text Cleaner\nHeader/Footer Stripping, Hyphen Joining"]
        Detector["Section Detector\nAbstract, Methods, Results, Conclusion"]
        Chunker["Chunking Engine\n650 Words, 80-Word Overlap"]
    end

    subgraph Retrieval["Hybrid Retrieval & Ranking"]
        Embedder["Embedding Model\nsentence-transformers/all-MiniLM-L6-v2"]
        DenseSearch["Dense Vector Search\nCosine Distance Retrieval"]
        BM25["BM25 Lexical Search\nExact Keyword Matching"]
        RRF["Reciprocal Rank Fusion\nHybrid Score Aggregator"]
    end

    subgraph Generation["Evidence Grounded Generation"]
        PromptBuilder["Prompt Construction\nSystem Rules, Evidence Fencing"]
        LLMFactory{"LLM Provider Factory"}
        OpenRouter["OpenRouter API\nFree Fallbacks: Qwen, Llama 3.3, Gemma"]
        Gemini["Google Gemini API\ngemini-2.5-flash with Exponential Backoff"]
        Ollama["Local Ollama\nDeepSeek / Llama Local Inference"]
        CitationExtractor["Citation Extractor\nFormat: [DocID, p.X] Verification"]
    end

    subgraph EvalEngine["Evaluation Suite"]
        Benchmark["20-Question Benchmark Dataset\nSingle-Doc, Multi-Doc, Adversarial, Unanswerable"]
        MetricCalc["Metric Calculator\nHit Rate, Groundedness, Citation Acc, Refusal Acc"]
    end

    %% User Interactions
    ChatUI -->|Send Message| ChatRouter
    DocsUI -->|Upload Document| DocRouter
    EvalUI -->|Trigger Benchmark| EvalRouter

    %% API Routing & Security
    ChatRouter --> SecFilter
    SecFilter --> Retrieval
    ChatRouter --> SessRouter
    SessRouter <--> SQLite

    %% Ingestion Flow
    DocRouter --> Ingestion
    Ingestion --> Parsers --> Cleaner --> Detector --> Chunker
    Chunker --> Embedder
    Embedder --> VectorStore
    DocRouter --> DocStore

    %% Retrieval Flow
    Retrieval --> Embedder
    Embedder --> DenseSearch
    DenseSearch <--> VectorStore
    Retrieval --> BM25
    DenseSearch --> RRF
    BM25 --> RRF
    RRF -->|Top K Evidence Chunks| PromptBuilder

    %% Generation Flow
    PromptBuilder --> LLMFactory
    LLMFactory --> OpenRouter
    LLMFactory --> Gemini
    LLMFactory --> Ollama
    OpenRouter --> CitationExtractor
    Gemini --> CitationExtractor
    Ollama --> CitationExtractor
    CitationExtractor -->|Streamed SSE Chunks| ChatRouter
    ChatRouter -->|Assistant Response + Citations| SQLite

    %% Evaluation Flow
    EvalRouter --> EvalEngine
    Benchmark --> EvalEngine
    EvalEngine --> ChatRouter
    EvalEngine --> MetricCalc
    MetricCalc --> SQLite
```

## Data flow summary

1. **Ingestion**: Uploaded documents are parsed via PyMuPDF or plain text readers, cleaned, tagged with section headings, chunked into 650-word windows with 80-word overlap, embedded with `all-MiniLM-L6-v2`, and indexed into ChromaDB.
2. **Retrieval**: User queries pass through security screening. A hybrid search combines dense cosine similarity from ChromaDB with BM25 lexical search using Reciprocal Rank Fusion to retrieve the top evidence chunks.
3. **Generation**: Top evidence chunks are fenced in `<retrieved_evidence>` tags with a strict system prompt. The selected LLM (OpenRouter, Gemini, or Ollama) generates answers that separate evidence from inference and reference explicit citations (`[doc_id, p.X]`). Unsupported questions trigger an explicit refusal.
4. **Delivery & Storage**: Responses stream to the React UI via Server-Sent Events (SSE). The user message and assistant answer are saved to SQLite. If the session has a default title, the first user message updates the session title.
