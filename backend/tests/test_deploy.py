from fastapi.testclient import TestClient
from app.config import _db_url
from app.main import app


def test_cors_allows_only_configured_origins():
    c = TestClient(app)
    pre = lambda origin: c.options("/api/auth/guest", headers={"Origin": origin, "Access-Control-Request-Method": "POST", "Access-Control-Request-Headers": "authorization,content-type"})
    ok = pre("https://interviewsaathi.vercel.app")
    assert ok.status_code == 200 and ok.headers["access-control-allow-origin"] == "https://interviewsaathi.vercel.app" and "authorization" in ok.headers["access-control-allow-headers"].lower()
    assert "access-control-allow-origin" not in pre("https://evil.example.com").headers      # an unknown site cannot call the API from a browser


def test_database_url_is_normalised_for_hosted_postgres():
    assert _db_url("postgres://u:p@host/db") == "postgresql+psycopg://u:p@host/db"
    assert _db_url("postgresql://u:p@host/db?sslmode=require") == "postgresql+psycopg://u:p@host/db?sslmode=require"
    assert _db_url("sqlite:///x.db") == "sqlite:///x.db"


def test_answer_source_is_validated():
    c = TestClient(app); c.headers["Authorization"] = "Bearer " + c.post("/api/auth/guest").json()["token"]
    iid = c.post("/api/interviews", json={"config": {"interview_type": "hr", "duration": "short"}}).json()["id"]
    assert c.post(f"/api/interviews/{iid}/answer", json={"text": "hello there", "source": "x" * 40}).status_code == 422
