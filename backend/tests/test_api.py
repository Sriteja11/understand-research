import pytest
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.db.database import init_db

@pytest.fixture(scope="module", autouse=True)
def setup_test_environment():
    init_db()

def test_health_endpoint():
    client = TestClient(app)
    res = client.get("/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "healthy"

def test_sessions_lifecycle():
    client = TestClient(app)
    # Create session
    create_res = client.post("/sessions", json={"title": "Test Session"})
    assert create_res.status_code == 200
    sid = create_res.json()["id"]

    # List sessions
    list_res = client.get("/sessions")
    assert list_res.status_code == 200
    ids = [s["id"] for s in list_res.json()]
    assert sid in ids

    # Get session details
    detail_res = client.get(f"/sessions/{sid}")
    assert detail_res.status_code == 200
    assert detail_res.json()["id"] == sid

    # Delete session
    del_res = client.delete(f"/sessions/{sid}")
    assert del_res.status_code == 200

def test_documents_list():
    client = TestClient(app)
    res = client.get("/documents")
    assert res.status_code == 200
    assert isinstance(res.json(), list)

def test_chat_empty_query_rejected():
    client = TestClient(app)
    res = client.post("/chat/sync", json={"message": "   "})
    assert res.status_code == 400

def test_spa_browser_routes():
    client = TestClient(app)
    # Direct browser navigation to /documents with Accept: text/html
    res = client.get("/documents", headers={"accept": "text/html,application/xhtml+xml"})
    assert res.status_code == 200
    assert "<!doctype html>" in res.text.lower() or "<html" in res.text.lower()

    # Direct browser navigation to /evaluation with Accept: text/html
    res_eval = client.get("/evaluation", headers={"accept": "text/html,application/xhtml+xml"})
    assert res_eval.status_code == 200
    assert "<!doctype html>" in res_eval.text.lower() or "<html" in res_eval.text.lower()

    # Browser navigation to /chat/sess_123
    res_chat = client.get("/chat/sess_123")
    assert res_chat.status_code == 200
    assert "<!doctype html>" in res_chat.text.lower() or "<html" in res_chat.text.lower()

    # API call to /documents with Accept: application/json returns JSON list
    res_api = client.get("/documents", headers={"accept": "application/json"})
    assert res_api.status_code == 200
    assert isinstance(res_api.json(), list)

