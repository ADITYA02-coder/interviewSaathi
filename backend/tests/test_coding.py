"""Needs the real runner on :9000 (see tests/run_with_runner.sh). Skipped automatically if it is not reachable."""
import os, tempfile, socket
import pytest
from fastapi.testclient import TestClient
from app.main import app
from tests.solutions import PY, JS_TWO_SUM, JAVA_TWO_SUM


def runner_up():
    try:
        socket.create_connection(("127.0.0.1", 9000), timeout=0.5).close(); return True
    except OSError:
        return False


pytestmark = pytest.mark.skipif(not runner_up(), reason="code runner not running on :9000")


@pytest.fixture(autouse=True)
def _reset_limiter():
    from app import security
    security._hits.clear()


@pytest.fixture(scope="module")
def c():
    with TestClient(app) as cl:
        cl.headers["Authorization"] = "Bearer " + cl.post("/api/auth/guest").json()["token"]
        yield cl


def test_every_builtin_problem_accepts_a_correct_solution(c):
    probs = c.get("/api/problems").json()
    assert len(probs) >= 12
    from app import security
    for p in probs:
        security._hits.clear()
        r = c.post(f"/api/problems/{p['id']}/submit", json={"language": "python", "code": PY[p["id"]]}).json()
        assert r["status"] == "accepted", (p["id"], r)
        assert r["passed"] == r["total"] >= 9


def test_multi_language_and_failure_modes(c):
    assert c.post("/api/problems/two-sum/submit", json={"language": "javascript", "code": JS_TWO_SUM}).json()["status"] == "accepted"
    assert c.post("/api/problems/two-sum/submit", json={"language": "java", "code": JAVA_TWO_SUM}).json()["status"] == "accepted"
    wrong = c.post("/api/problems/two-sum/submit", json={"language": "python", "code": "print('0 1')"}).json()
    assert wrong["status"] == "wrong_answer" and 0 < wrong["passed"] < wrong["total"]
    hidden = [t for t in wrong["tests"] if t["hidden"]]
    assert hidden and all("expected" not in t and "input" not in t and "actual" not in t for t in hidden), "hidden tests must not leak"
    assert c.post("/api/problems/two-sum/submit", json={"language": "python", "code": "while True: pass"}).json()["status"] == "timeout"
    assert c.post("/api/problems/two-sum/submit", json={"language": "python", "code": "def ("}).json()["status"] == "runtime_error"
    assert c.post("/api/problems/two-sum/submit", json={"language": "java", "code": "class Main { oops }"}).json()["status"] == "compile_error"
    assert c.post("/api/problems/two-sum/run", json={"language": "python", "code": PY["two-sum"]}).json()["total"] == 2  # run = visible tests only


def test_full_coding_interview_flow(c):
    r = c.post("/api/interviews", json={"config": {"role": "Java Developer", "interview_type": "coding", "difficulty": "beginner", "duration": "standard", "code_language": "python", "problem_ids": ["two-sum", "valid-parentheses"]}})
    assert r.status_code == 200, r.text
    iv = r.json(); iid = iv["id"]
    assert iv["coding"]["phase"] == "approach" and iv["coding"]["total"] == 2 and "approach" in iv["opening"]["text"].lower()
    p1 = iv["coding"]["problem"]["id"]
    a = c.post(f"/api/interviews/{iid}/answer", json={"text": "I would use a hash map to store seen values and check the complement for each number in one pass.", "source": "voice"}).json()
    assert a["coding"]["phase"] == "coding" and "samples" in a["reply"].lower()
    chat = c.post(f"/api/interviews/{iid}/answer", json={"text": "Can the numbers be negative?"}).json()
    assert chat["kind"] == "clarify" and chat["coding"]["phase"] == "coding"
    run = c.post(f"/api/interviews/{iid}/code/run", json={"language": "python", "code": PY[p1]}).json()
    assert run["status"] == "accepted" and run["total"] == 2
    sub = c.post(f"/api/interviews/{iid}/code/submit", json={"language": "python", "code": PY[p1]}).json()
    assert sub["result"]["status"] == "accepted" and "complexity" in sub["reply"].lower() and sub["coding"]["phase"] == "followup"
    assert c.post(f"/api/interviews/{iid}/code/submit", json={"language": "python", "code": PY[p1]}).status_code == 409
    f = c.post(f"/api/interviews/{iid}/answer", json={"text": "Time complexity is O(n) and space is O(n) for the hash map. Edge cases: empty input and negative numbers."}).json()
    assert f["coding"]["phase"] == "approach" and f["coding"]["index"] == 1 and not f["done"]
    sk = c.post(f"/api/interviews/{iid}/code/skip").json()
    assert sk["done"] and sk["kind"] == "closing"
    rep = c.post(f"/api/interviews/{iid}/finish").json()["report"]
    assert rep["kind"] == "coding" and rep["answered"] == 1 and rep["skipped"] == 1
    prob = rep["problems"][0]
    assert prob["status"] == "accepted" and prob["correctness"] == 100 and prob["complexity"]["overall"] >= 60 and prob["overall"] >= 80
    assert rep["overall"] == prob["overall"]
    assert c.get("/api/dashboard").json()["total_completed"] == 1


def test_coding_needs_runner_when_missing(c):
    from app.config import settings
    url = settings.runner_url; settings.runner_url = ""
    try:
        assert c.post("/api/interviews", json={"config": {"interview_type": "coding"}}).status_code == 503
        assert c.get("/api/meta").json()["coding_enabled"] is False
    finally:
        settings.runner_url = url
