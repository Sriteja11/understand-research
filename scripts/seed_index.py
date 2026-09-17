import sys
import os
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.app.db.database import init_db
from backend.app.services.indexing_service import get_indexing_service
from backend.app.retrieval.vector_store import get_vector_store

def main():
    print("Initializing SQLite database...")
    init_db()

    print("Checking seed documents...")
    idx_service = get_indexing_service()
    count = idx_service.index_seed_documents()
    print(f"Newly indexed documents: {count}")

    store = get_vector_store()
    print(f"Total vector chunks in ChromaDB: {store.count()}")
    print("Seed indexing finished.")

if __name__ == "__main__":
    main()

