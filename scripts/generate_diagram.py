from PIL import Image, ImageDraw, ImageFont
from pathlib import Path

def generate_diagram():
    width = 1600
    height = 1050
    img = Image.new("RGB", (width, height), color=(248, 250, 252))
    draw = ImageDraw.Draw(img)

    # Helper functions
    def draw_box(x, y, w, h, fill, outline, title, subtitle="", radius=10):
        draw.rounded_rectangle([x, y, x + w, y + h], radius=radius, fill=fill, outline=outline, width=2)
        draw.text((x + 15, y + 15), title, fill=(15, 23, 42))
        if subtitle:
            draw.text((x + 15, y + 40), subtitle, fill=(100, 116, 139))

    def draw_arrow(x1, y1, x2, y2, label=""):
        draw.line([x1, y1, x2, y2], fill=(71, 85, 105), width=2)
        # Arrowhead
        arrow_len = 8
        if x2 > x1:
            draw.polygon([(x2, y2), (x2 - arrow_len, y2 - 4), (x2 - arrow_len, y2 + 4)], fill=(71, 85, 105))
        elif y2 > y1:
            draw.polygon([(x2, y2), (x2 - 4, y2 - arrow_len), (x2 + 4, y2 - arrow_len)], fill=(71, 85, 105))
        elif x2 < x1:
            draw.polygon([(x2, y2), (x2 + arrow_len, y2 - 4), (x2 + arrow_len, y2 + 4)], fill=(71, 85, 105))
        elif y2 < y1:
            draw.polygon([(x2, y2), (x2 - 4, y2 + arrow_len), (x2 + 4, y2 + arrow_len)], fill=(71, 85, 105))
        if label:
            mx = (x1 + x2) // 2 + 5
            my = (y1 + y2) // 2 - 12
            draw.text((mx, my), label, fill=(100, 116, 139))

    # Header
    draw.text((50, 30), "EVIDENCE-GROUNDED RAG RESEARCH ASSISTANT — SYSTEM ARCHITECTURE", fill=(30, 41, 59))
    draw.text((50, 55), "End-to-End Ingestion, Retrieval, Reranking, Security Boundaries, and Evaluation Pipeline", fill=(100, 116, 139))

    # 1. Frontend Layer
    draw_box(50, 100, 420, 160, (238, 242, 255), (165, 180, 252), "React 18 + Vite Frontend (SPA)", "ChatPage, DocumentsPage, EvaluationPage\nNative EventSource SSE Client, Citation & Evidence Drawers")
    
    # HTTP + SSE Bridge
    draw_arrow(260, 260, 260, 340, "HTTP POST & Server-Sent Events (SSE)")
    draw_arrow(280, 340, 280, 260, "Live Tokens, Progress & Metrics")

    # 2. FastAPI Gateway
    draw_box(50, 340, 420, 150, (241, 245, 249), (203, 213, 225), "FastAPI Application Gateway", "Routers: /chat, /documents, /sessions, /evaluation\nCORS, Lifespan Pre-Indexing, Static File Serving")

    # Connect to Services
    draw_arrow(470, 380, 560, 380, "Upload Flow")
    draw_arrow(470, 430, 560, 580, "Chat Flow")
    draw_arrow(470, 470, 560, 780, "Eval Flow")

    # 3. Ingestion Pipeline
    draw_box(560, 100, 480, 290, (254, 243, 199), (252, 211, 77), "Ingestion & Indexing Service", "1. Parsers: PyMuPDF (PDF), Text, Markdown\n2. Cleaner: Unicode normalization & control character strip\n3. Section Detector: Academic numbering & Markdown tags\n4. Section-Aware Chunker (500-1000 tokens, overlap)\n5. Error Paths: 400 Empty File, Corrupt PDF -> FAILED")

    # Connect Ingestion to Data Sources and ChromaDB
    draw_arrow(780, 390, 780, 460, "Embed & Upsert")
    
    # 4. Storage Layer
    draw_box(560, 460, 220, 110, (240, 253, 244), (134, 239, 172), "ChromaDB (Local)", "Collection: research_documents\nHNSW Cosine Vectors, Source Metadata")
    draw_box(820, 460, 220, 110, (240, 253, 244), (134, 239, 172), "SQLite (app.db)", "sessions, messages, documents\nindexing_jobs, evaluation_results")

    # Connect Ingestion to Data
    draw_arrow(1150, 180, 1040, 180, "Read Seed & Uploads")
    draw_box(1150, 120, 380, 150, (248, 250, 252), (203, 213, 225), "Storage Directories", "data/seed_documents/ (5 bundled papers, 247 pages)\ndata/uploads/ (user uploaded files)\ndata/chroma/ (persistent vector indexes)")

    # 5. Retrieval & Reranker Service
    draw_box(560, 600, 480, 180, (243, 232, 255), (216, 180, 254), "Retrieval & Reranker Service", "1. Embed Query (all-MiniLM-L6-v2)\n2. Initial Top-K Vector Search in ChromaDB\n3. Hybrid Lexical-Semantic Reranker (ms-marco-MiniLM-L-6-v2)\n4. Threshold Filter (Relevance >= 0.20)\n5. Insufficient Evidence Detection")

    draw_arrow(650, 570, 650, 600, "Vector Search")
    draw_arrow(800, 780, 800, 830, "Top-N Evidence")

    # 6. Security and LLM Provider Layer
    draw_box(560, 830, 480, 160, (255, 241, 242), (254, 205, 211), "Security Boundaries & Untrusted Context Fencing", "1. Query Length Validation (max 2000 chars)\n2. Prompt Injection Scanner (detects override commands)\n3. XML Fence Wrapping: <retrieved_evidence> untrusted blocks\n4. Strict System Prompt Enforcement")

    draw_arrow(1040, 910, 1150, 910, "Secure Context")

    # 7. LLM Providers
    draw_box(1150, 830, 380, 160, (236, 253, 245), (110, 231, 183), "LLM Provider Abstraction", "GeminiProvider (google-genai SDK, streaming)\nOllamaProvider (local qwen3.5:4b, HTTP API)\nStrict Refusal: 'Insufficient evidence'\nEvidence vs Inference Separation")

    draw_arrow(1340, 830, 1340, 580, "Grounded Answer + Citations")

    # 8. Evaluation Layer
    draw_box(1150, 460, 380, 220, (254, 242, 242), (252, 165, 165), "Evaluation Service & Dataset", "dataset.json (20 test cases):\n- 10 answerable, 5 unanswerable\n- 3 contradictory, 2 prompt injection\nMetrics: Hit Rate, Citation Accuracy,\nGroundedness, Refusal Accuracy, Latency\nExports to eval_latest.json and .csv")

    draw_arrow(1340, 460, 1340, 300, "")

    # Save output
    docs_dir = Path("docs")
    docs_dir.mkdir(parents=True, exist_ok=True)
    out_path = docs_dir / "architecture.png"
    img.save(out_path)
    print(f"Architecture diagram saved to {out_path}")

if __name__ == "__main__":
    generate_diagram()

