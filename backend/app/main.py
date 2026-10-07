import os
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from backend.app.config import settings
from backend.app.db.database import init_db
from backend.app.services.indexing_service import get_indexing_service
from backend.app.api.chat import router as chat_router
from backend.app.api.documents import router as documents_router
from backend.app.api.sessions import router as sessions_router
from backend.app.api.evaluation import router as evaluation_router
from backend.app.api.audio import router as audio_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Initialize SQLite database
    init_db()

    # Pre-index seed documents if missing from ChromaDB
    try:
        idx_service = get_indexing_service()
        indexed = idx_service.index_seed_documents()
        if indexed > 0:
            print(f"Indexed {indexed} seed documents.")
        else:
            print("Seed documents already indexed.")
    except Exception as e:
        print(f"Seed indexing notice: {e}")

    yield
    # Shutdown cleanups if needed

app = FastAPI(
    title="Evidence-Grounded AI Research Assistant API",
    description="Local RAG application for answering technical questions from AI research papers.",
    version="1.0.0",
    lifespan=lifespan
)

# Enable CORS for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routers
app.include_router(chat_router)
app.include_router(documents_router)
app.include_router(sessions_router)
app.include_router(evaluation_router)
app.include_router(audio_router)

@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "provider": settings.llm_provider,
        "embedding_model": settings.embedding_model,
        "audio_model": "Whistle (16.9 MB)"
    }

# Serve built frontend if available
frontend_dist = Path("frontend/dist").resolve()

@app.middleware("http")
async def spa_navigation_middleware(request, call_next):
    accept = request.headers.get("accept", "")
    if request.method == "GET" and "text/html" in accept:
        path = request.url.path
        if not path.startswith(("/docs", "/redoc", "/openapi.json", "/health")):
            index_file = frontend_dist / "index.html"
            if index_file.exists():
                target = frontend_dist / path.lstrip("/")
                if not (target.exists() and target.is_file()):
                    return FileResponse(str(index_file))
    return await call_next(request)

if frontend_dist.exists() and (frontend_dist / "assets").exists():
    app.mount("/assets", StaticFiles(directory=str(frontend_dist / "assets")), name="assets")

@app.get("/{full_path:path}")
async def serve_spa(full_path: str):
    target = frontend_dist / full_path
    if target.exists() and target.is_file():
        return FileResponse(str(target))
    index_file = frontend_dist / "index.html"
    if index_file.exists():
        return FileResponse(str(index_file))
    return {"message": "Evidence-Grounded AI Research Assistant API. Frontend not yet built."}

