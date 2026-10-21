import pytest
from fastapi.testclient import TestClient
from app import mailer
from app.config import settings
from app.main import app
from app.security import purpose_token

MAILS = []


@pytest.fixture(autouse=True)
def _admin_mode(monkeypatch):
    MAILS.clear()
    monkeypatch.setattr(mailer, "send", lambda to, subject, body: MAILS.append((to, subject)))
    monkeypatch.setattr(settings, "verification_mode", "admin")


def reg(email, name):
    c = TestClient(app)
    r = c.post("/api/auth/register", json={"email": email, "password": "password123", "name": name}); assert r.status_code == 200, r.text
    c.headers["Authorization"] = "Bearer " + r.json()["token"]
    return c, r.json()["user"]


_ADMIN = {}


def make_admin():
    """One admin for the whole module (what the CLI / first-admin path produces)."""
    if "c" not in _ADMIN:
        c, u = reg("boss2@college.edu", "Dean")
        TestClient(app).post("/api/auth/verify", json={"token": purpose_token(u["id"], "verify", 60)})
        from app.db import SessionLocal, User
        with SessionLocal() as db:
            db.get(User, u["id"]).role = "admin"; db.commit()
        _ADMIN["c"] = c
    return _ADMIN["c"]


def test_admin_mode_sends_no_email_and_students_wait_for_approval():
    assert TestClient(app).get("/api/meta").json()["verification"] == "admin"
    s, u = reg("rahul@c.edu", "Rahul")
    assert MAILS == [] and u["email_verified"] is False
    r = s.post("/api/auth/verify/send")
    assert r.status_code == 409 and "admin" in r.json()["detail"].lower()
    assert s.post("/api/interviews", json={"config": {"interview_type": "hr", "duration": "short"}}).status_code == 200    # unverified students can still practise


def test_admin_approves_one_by_one_and_in_bulk_and_sees_the_count():
    admin = make_admin()
    ids = [reg(f"bulk{i}@c.edu", f"Bulk {i}")[1]["id"] for i in range(3)]
    st = admin.get("/api/admin/stats").json()
    assert st["unverified"] >= 3
    pending = admin.get("/api/admin/users?unverified=true").json()
    assert {u["id"] for u in pending} >= set(ids) and all(not u["verified"] for u in pending)
    assert admin.put(f"/api/admin/users/{ids[0]}/verify").status_code == 200                                              # one by one
    assert ids[0] not in {u["id"] for u in admin.get("/api/admin/users?unverified=true").json()}
    n = admin.post("/api/admin/users/verify", json={"ids": ids[1:]}).json()["verified"]                                    # a chosen subset
    assert n == 2
    everyone = admin.post("/api/admin/users/verify", json={}).json()["verified"]                                           # all remaining
    assert everyone >= 0 and admin.get("/api/admin/stats").json()["unverified"] == 0
    assert admin.post("/api/admin/users/verify", json={}).json()["verified"] == 0


def test_bulk_verify_never_promotes_and_students_cannot_use_it():
    admin = make_admin()
    s, u = reg("sneaky@c.edu", "Sneaky")
    assert s.post("/api/admin/users/verify", json={}).status_code == 403
    admin.post("/api/admin/users/verify", json={})
    assert s.get("/api/auth/me").json()["role"] == "student" and s.get("/api/auth/me").json()["email_verified"] is True


def test_admin_mode_still_emails_the_admin_address_so_the_first_admin_can_bootstrap(monkeypatch):
    monkeypatch.setattr(settings, "admin_emails", {"founder@college.edu"})
    c, u = reg("founder@college.edu", "Founder")
    assert [m[0] for m in MAILS] == ["founder@college.edu"]
    MAILS.clear()
    reg("plain.student@college.edu", "Plain")
    assert MAILS == []                                                       # ordinary students get nothing
    assert TestClient(app).post("/api/auth/verify", json={"token": purpose_token(u["id"], "verify", 60)}).status_code == 200
    assert c.get("/api/auth/me").json()["role"] == "admin"
