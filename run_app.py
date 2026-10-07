import os
import sys
import shutil
import subprocess
from pathlib import Path

def bootstrap():
    root = Path(__file__).resolve().parent
    env_file = root / ".env"
    env_example = root / ".env.example"

    # 1. Initialize .env from .env.example if missing
    if not env_file.exists() and env_example.exists():
        print("Notice: .env not found. Initializing .env from .env.example...")
        shutil.copy(env_example, env_file)

    # 2. Re-exec with local .venv python if present and not currently active
    venv_py_win = root / ".venv" / "Scripts" / "python.exe"
    venv_py_unix = root / ".venv" / "bin" / "python"
    venv_py = venv_py_win if os.name == "nt" else venv_py_unix

    if venv_py.exists() and Path(sys.executable).resolve() != venv_py.resolve():
        args = [str(venv_py), str(Path(__file__).resolve())] + sys.argv[1:]
        sys.exit(subprocess.call(args))

    # 3. Check for core dependencies and auto-install if missing
    required = ["uvicorn", "fastapi", "chromadb", "sentence_transformers", "pymupdf", "pydantic_settings", "needle"]
    missing = []
    for pkg in required:
        try:
            __import__(pkg)
        except ImportError:
            missing.append(pkg)

    if missing:
        print(f"Installing missing dependencies ({', '.join(missing)}) from requirements.txt...")
        uv_bin = shutil.which("uv")
        req_file = root / "requirements.txt"
        if uv_bin:
            cmd = [uv_bin, "pip", "install", "-r", str(req_file)]
        else:
            cmd = [sys.executable, "-m", "pip", "install", "-r", str(req_file)]
        subprocess.check_call(cmd)
        print("Dependencies installed successfully.\n")

if __name__ == "__main__":
    bootstrap()

    # Import app dependencies after bootstrap verification
    import uvicorn
    from backend.app.db.database import init_db
    from backend.app.services.indexing_service import get_indexing_service

    print("=" * 65)
    print("  EVIDENCE GROUNDED AI RESEARCH ASSISTANT")
    print("=" * 65)
    print("Initializing SQLite state and verifying seed papers...")
    init_db()
    idx_service = get_indexing_service()
    idx_service.index_seed_documents()

    print("\nStarting application on http://localhost:8000")
    print("Open http://localhost:8000 in your browser to use the assistant.")
    print("API documentation available at http://localhost:8000/docs")
    print("=" * 65 + "\n")

    uvicorn.run(
        "backend.app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
        log_level="info"
    )
