import re
import pytest
from fastapi.testclient import TestClient
from app import mailer, questionbank as qb
from app.main import app

MAILS = []


@pytest.fixture(autouse=True)
def _mail(monkeypatch):
    monkeypatch.setattr(mailer, "send", lambda to, subject, body: MAILS.append((to, subject, body)))


def reg(email, name, pw="password123"):
    c = TestClient(app)
    r = c.post("/api/auth/register", json={"email": email, "password": pw, "name": name}); assert r.status_code == 200, r.text
    c.headers["Authorization"] = "Bearer " + r.json()["token"]
    return c, r.json()["user"]


def finish_interview(c, itype="hr", answer="I am a final year student. I built a project with Java and React and I want to learn. My goal is to grow as a developer."):
    iv = c.post("/api/interviews", json={"config": {"role": "HR / General", "interview_type": itype, "duration": "short"}}).json()
    for _ in range(8):
        a = c.post(f"/api/interviews/{iv['id']}/answer", json={"text": answer, "source": "voice"}).json()
        if a["done"]:
            break
    return iv["id"], c.post(f"/api/interviews/{iv['id']}/finish").json()["report"]


@pytest.fixture(scope="module")
def world():
    from app.security import purpose_token
    admin, au = reg("boss@college.edu", "Dr Boss")
    assert au["role"] == "student"                         # listed in ADMIN_EMAILS but NOT verified yet: no admin rights
    assert admin.get("/api/admin/stats").status_code == 403
    assert TestClient(app).post("/api/auth/verify", json={"token": purpose_token(au["id"], "verify", 60)}).status_code == 200
    assert admin.get("/api/auth/me").json()["role"] == "admin"   # verifying the address is what grants it
    asha, a_u = reg("asha@c.edu", "Asha"); ravi, r_u = reg("ravi@c.edu", "Ravi"); lone, l_u = reg("lone@c.edu", "Lone")
    cohort = admin.post("/api/admin/cohorts", json={"name": "CSE 2026"}).json()
    return dict(admin=admin, asha=asha, ravi=ravi, lone=lone, asha_id=a_u["id"], ravi_id=r_u["id"], lone_id=l_u["id"], cohort=cohort)


def test_admin_only(world):
    assert world["asha"].get("/api/admin/stats").status_code == 403
    assert TestClient(app).get("/api/admin/stats").status_code == 401


def test_join_and_consent_gates(world):
    guest = TestClient(app); guest.headers["Authorization"] = "Bearer " + guest.post("/api/auth/guest").json()["token"]
    assert guest.post("/api/cohorts/join", json={"code": world["cohort"]["code"]}).status_code == 409   # guests can't be tracked
    assert world["asha"].post("/api/cohorts/join", json={"code": "ZZZZZZ"}).status_code == 404
    for who in ("asha", "ravi"):
        assert world[who].post("/api/cohorts/join", json={"code": world["cohort"]["code"].lower()}).status_code == 200
    assert world["asha"].get("/api/auth/me").json()["cohorts"][0]["name"] == "CSE 2026"
    # Lone never joined: admin must not be able to open her record
    assert world["admin"].get(f"/api/admin/students/{world['lone_id']}").status_code == 404


def test_leaderboard_ranks_by_real_results(world):
    finish_interview(world["asha"], answer="I am a final year engineering student with skills in Java and React. I built a project and my goal is to learn and grow. For example I developed a web app.")
    finish_interview(world["ravi"], answer="ok")
    finish_interview(world["lone"])
    lb = world["admin"].get(f"/api/admin/leaderboard?cohort_id={world['cohort']['id']}").json()
    names = [r["name"] for r in lb]
    assert names == ["Asha", "Ravi"], names           # Lone is not in the cohort, so she is invisible
    assert lb[0]["rank"] == 1 and lb[0]["average"] > lb[1]["average"] and lb[1]["needs_attention"] is True
    csvtxt = world["admin"].get(f"/api/admin/leaderboard.csv?cohort_id={world['cohort']['id']}").text
    assert csvtxt.splitlines()[1].startswith("1,Asha,asha@c.edu")


def test_transcripts_need_the_students_consent(world):
    uid = world["asha_id"]
    d = world["admin"].get(f"/api/admin/students/{uid}").json()
    assert d["transcripts_shared"] is False and d["sessions"] and d["email"] == "asha@c.edu"
    one = world["admin"].get(f"/api/admin/students/{uid}/interviews/{d['sessions'][0]['id']}").json()
    assert "turns" not in one and one["report"]["overall"] > 0                    # scores yes, words no
    cid = world["cohort"]["id"]
    world["asha"].put(f"/api/cohorts/{cid}/sharing", json={"share_transcripts": True})
    one = world["admin"].get(f"/api/admin/students/{uid}/interviews/{d['sessions'][0]['id']}").json()
    assert one["transcripts_shared"] and any(t["role"] == "candidate" for t in one["turns"])
    world["asha"].put(f"/api/cohorts/{cid}/sharing", json={"share_transcripts": False})
    assert "turns" not in world["admin"].get(f"/api/admin/students/{uid}/interviews/{d['sessions'][0]['id']}").json()
    world["ravi"].delete(f"/api/cohorts/{cid}/leave")
    assert world["admin"].get(f"/api/admin/students/{world['ravi_id']}").status_code == 404   # leaving withdraws access


def test_question_bank_management_changes_the_interview(world):
    a = world["admin"]
    r = a.post("/api/admin/questions", json={"bank_key": "hr", "topic": "Placement", "level": 1, "text": "Why should our college placement cell recommend you to recruiters?", "concepts": [["gives reasons", ["because", "reason"]]]})
    assert r.status_code == 200, r.text
    qid = r.json()["id"]
    assert a.post("/api/admin/questions", json={"bank_key": "nope", "text": "A question that is long enough."}).status_code == 422
    assert any("placement cell" in q for q in qb.pool_texts({"interview_type": "hr"}, 50))
    for q in a.get("/api/admin/questions?bank_key=hr").json()["questions"]:
        if q["source"] == "builtin":
            a.delete(f"/api/admin/questions/{q['id']}")   # disables the built-ins
    assert qb.pool_texts({"interview_type": "hr"}, 50) == ["Why should our college placement cell recommend you to recruiters?"]
    iv = world["asha"].post("/api/interviews", json={"config": {"interview_type": "hr", "duration": "short"}}).json()
    assert "placement cell" in iv["opening"]["text"]
    a.delete(f"/api/admin/questions/{qid}")
    assert a.get("/api/admin/questions?bank_key=hr").json()["questions"] and True


def test_templates_support_and_stats(world):
    a, cid = world["admin"], world["cohort"]["id"]
    assert a.post("/api/admin/templates", json={"name": "Mock placement drive", "cohort_id": cid, "config": {"role": "Java Developer", "interview_type": "technical", "evil": 1}, "focus_note": "Focus on OOP"}).status_code == 200
    mine = world["asha"].get("/api/templates").json()
    assert mine and mine[0]["config"] == {"role": "Java Developer", "interview_type": "technical"} and mine[0]["focus_note"] == "Focus on OOP"
    assert world["lone"].get("/api/templates").json() == []                         # not in the cohort
    assert world["asha"].post("/api/support", json={"subject": "Mic problem", "message": "My microphone is not detected in Safari."}).status_code == 200
    s = a.get("/api/admin/support").json(); assert s[0]["subject"] == "Mic problem" and s[0]["status"] == "open"
    a.put(f"/api/admin/support/{s[0]['id']}", json={"status": "resolved", "admin_note": "Use Chrome"})
    assert world["asha"].get("/api/support").json()[0]["admin_note"] == "Use Chrome"
    st = a.get("/api/admin/stats").json()
    assert st["students"] >= 3 and st["completed"] >= 3 and st["answers_by_voice"] > 0 and st["open_support"] == 0 and len(st["per_day"]) == 30


def test_roles_and_cohort_delete(world):
    a = world["admin"]
    assert a.put(f"/api/admin/users/{world['ravi_id']}/role", json={"role": "admin"}).status_code == 200
    assert a.get("/api/admin/users?search=ravi").json()[0]["role"] == "admin"
    assert a.put("/api/admin/users/1/role", json={"role": "student"}).status_code in (200, 409)
    assert a.delete(f"/api/admin/cohorts/{world['cohort']['id']}").status_code == 200
    assert world["asha"].get("/api/templates").json() == []


def test_password_reset_and_email_verification():
    MAILS.clear()
    c, u = reg("reset@c.edu", "Reset Me", "oldpassword1")
    assert u["email_verified"] is False and any("Verify" in m[1] for m in MAILS)
    vtok = re.search(r"#/verify/(\S+)", [m for m in MAILS if "Verify" in m[1]][-1][2]).group(1)
    assert TestClient(app).post("/api/auth/verify", json={"token": vtok}).status_code == 200
    assert c.get("/api/auth/me").json()["email_verified"] is True
    anon = TestClient(app)
    assert anon.post("/api/auth/forgot", json={"email": "ghost@nowhere.com"}).json() == {"sent": True}        # same answer, no account enumeration
    MAILS.clear()
    assert anon.post("/api/auth/forgot", json={"email": "reset@c.edu"}).json() == {"sent": True}
    rtok = re.search(r"#/reset/(\S+)", MAILS[-1][2]).group(1)
    assert anon.post("/api/auth/reset", json={"token": vtok, "password": "newpassword1"}).status_code == 400   # wrong kind of token
    assert anon.post("/api/auth/reset", json={"token": rtok, "password": "newpassword1"}).status_code == 200
    assert anon.post("/api/auth/reset", json={"token": rtok, "password": "another-pass1"}).status_code == 400  # single use
    assert anon.post("/api/auth/login", json={"email": "reset@c.edu", "password": "oldpassword1"}).status_code == 401
    assert anon.post("/api/auth/login", json={"email": "reset@c.edu", "password": "newpassword1"}).status_code == 200
    # a reset/verify token must never work as a login session
    assert TestClient(app).get("/api/auth/me", headers={"Authorization": f"Bearer {rtok}"}).status_code == 401


def test_admin_can_mark_a_students_email_verified_but_not_promote(world):
    ravi_id = world["ravi_id"]
    row = next(u for u in world["admin"].get("/api/admin/users?search=ravi").json() if u["id"] == ravi_id)
    if not row["verified"]:
        assert world["admin"].put(f"/api/admin/users/{ravi_id}/verify").status_code == 200
    row = next(u for u in world["admin"].get("/api/admin/users?search=ravi").json() if u["id"] == ravi_id)
    assert row["verified"] is True
    assert world["asha"].put(f"/api/admin/users/{ravi_id}/verify").status_code == 403           # students can't verify anyone
