from fastapi.testclient import TestClient
from app.db import Interview, SessionLocal, User, Turn
from app.main import app
from scripts import seed_demo


def login(c, email, pw):
    r = c.post("/api/auth/login", json={"email": email, "password": pw}); assert r.status_code == 200, r.text
    c.headers["Authorization"] = "Bearer " + r.json()["token"]
    return r.json()["user"]


def test_seed_populates_a_believable_dashboard_and_removes_cleanly():
    with SessionLocal() as db:
        before = (db.query(User).count(), db.query(Interview).count())
        seed_demo.seed(db, quiet=True)
    admin = TestClient(app)
    assert login(admin, seed_demo.ADMIN_EMAIL, seed_demo.ADMIN_PASSWORD)["role"] == "admin"

    board = admin.get("/api/admin/leaderboard").json()
    demo = [r for r in board if r["email"].endswith("@" + seed_demo.DOMAIN)]
    assert len(demo) == 12
    ranked = [r for r in demo if r["rank"]]
    assert ranked[0]["name"] == "Priya Sharma" and ranked[0]["average"] > 80                    # strongest student on top
    assert [r["average"] for r in ranked] == sorted([r["average"] for r in ranked], reverse=True)
    assert any(r["needs_attention"] for r in demo) and next(r for r in demo if r["name"] == "Suresh Rao")["rank"] is None
    assert any(r["improvement"] and r["improvement"] > 0 for r in demo) and any(r["problems_solved"] > 0 for r in demo)

    # consent still enforced on demo data: only Priya shares her answers
    uid = next(r["id"] for r in demo if r["name"] == "Priya Sharma")
    d = admin.get(f"/api/admin/students/{uid}").json()
    sid = next(s["id"] for s in d["sessions"] if s["type"] != "coding")
    assert "turns" in admin.get(f"/api/admin/students/{uid}/interviews/{sid}").json()
    arjun = next(r["id"] for r in demo if r["name"] == "Arjun Mehta")
    asid = admin.get(f"/api/admin/students/{arjun}").json()["sessions"][0]["id"]
    assert "turns" not in admin.get(f"/api/admin/students/{arjun}/interviews/{asid}").json()

    stats = admin.get("/api/admin/stats").json()
    assert stats["completed"] >= 40 and stats["code_submissions"] > 0 and stats["open_support"] >= 1

    # a demo student sees real-looking reports, dashboard and assigned templates
    s = TestClient(app)
    login(s, f"priya.sharma@{seed_demo.DOMAIN}", seed_demo.STUDENT_PASSWORD)
    dash = s.get("/api/dashboard").json()
    assert dash["total_completed"] >= 5 and dash["first_vs_latest"] and dash["average_overall"] > 75
    rep = s.get(f"/api/interviews/{sid}").json()
    assert rep["report"]["engine"] == "demo-seed" and rep["report"]["answered"] >= 4 and any(t["evaluation"] for t in rep["turns"] if t["role"] == "candidate")
    coding_iv = next(i for i in s.get("/api/interviews").json() if i["config"]["interview_type"] == "coding")
    crep = s.get(f"/api/interviews/{coding_iv['id']}").json()["report"]
    assert crep["kind"] == "coding" and crep["problems"] and 0 < crep["overall"] <= 100
    assert any(t["group"] for t in s.get("/api/templates").json()) and len(s.get("/api/templates").json()) == 2

    with SessionLocal() as db:
        seed_demo.remove(db, quiet=True)
        assert (db.query(User).count(), db.query(Interview).count()) == before                 # back to exactly where we started
        assert db.query(Turn).filter(Turn.interview_id.like("demo%")).count() == 0
    assert TestClient(app).post("/api/auth/login", json={"email": seed_demo.ADMIN_EMAIL, "password": seed_demo.ADMIN_PASSWORD}).status_code == 401
