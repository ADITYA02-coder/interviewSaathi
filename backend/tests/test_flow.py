import json, os, tempfile, wave, io, struct
import httpx, pytest
from fastapi.testclient import TestClient
from app import gnani, llm
from app.config import settings
from app.main import app

SEEN = {"stt": [], "tts": []}


def gnani_handler(request: httpx.Request) -> httpx.Response:
    assert request.headers["X-API-Key-ID"] == "test-key"
    if request.url.path == "/stt/v3":
        body = request.content
        assert b'name="audio_file"' in body and b'name="language_code"' in body and b'name="format"' in body
        lang = body.split(b'name="language_code"')[1].split(b"\r\n")[2].decode()
        SEEN["stt"].append(lang)
        if lang == "en-hi-IN-latn":  # simulate experimental code being rejected -> backend must fall back
            return httpx.Response(422, text="unsupported")
        return httpx.Response(200, json={"success": True, "transcript": "An interface is a contract that a class implements, and a class can implement multiple interfaces, while an abstract class can hold state."})
    if request.url.path == "/api/v1/tts/inference":
        j = json.loads(request.content)
        SEEN["tts"].append(j)
        return httpx.Response(200, content=b"ID3" + b"\x00" * 2000, headers={"content-type": "audio/mpeg"})
    return httpx.Response(404)


def wav_bytes(seconds=1.0):
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(16000)
        w.writeframes(struct.pack("<h", 1000) * int(16000 * seconds))
    return buf.getvalue()


@pytest.fixture(scope="module")
def client():
    gnani._transport = httpx.MockTransport(gnani_handler)
    with TestClient(app) as c:
        tok = c.post("/api/auth/guest").json()["token"]
        c.headers["Authorization"] = f"Bearer {tok}"
        yield c


def run_interview(client, cfg, n_answers):
    r = client.post("/api/interviews", json={"config": cfg})
    assert r.status_code == 200, r.text
    iv = r.json()
    assert iv["opening"]["text"]
    done, last = False, None
    for i in range(n_answers + 3):
        a = client.post(f"/api/interviews/{iv['id']}/answer", json={"text": "An interface is a contract implemented by classes; a class can implement multiple interfaces while abstract classes hold state and use extends.", "source": "voice"})
        assert a.status_code == 200, a.text
        last = a.json()
        if last["done"]:
            break
    assert last["done"] and last["kind"] == "closing"
    fin = client.post(f"/api/interviews/{iv['id']}/finish")
    assert fin.status_code == 200, fin.text
    return iv, fin.json()


def test_meta_and_voice_contract(client):
    m = client.get("/api/meta").json()
    assert m["gnani_configured"] and any(l["code"] == "hinglish" for l in m["languages"])
    r = client.post("/api/voice/tts", json={"text": "Hello there", "voice": "Kaveri", "language": "en-IN"})
    assert r.status_code == 200 and r.headers["content-type"] == "audio/mpeg"
    j = SEEN["tts"][-1]
    assert j["model"] == "timbre-v2.5" and j["voice"] == "Kaveri" and j["language"] == "en-IN" and j["audio_config"]["container"] == "mp3"
    n = len(SEEN["tts"]); client.post("/api/voice/tts", json={"text": "Hello there", "voice": "Kaveri", "language": "en-IN"})
    assert len(SEEN["tts"]) == n, "second identical TTS call must be served from cache"
    assert client.post("/api/voice/tts", json={"text": "x", "voice": "Evil", "language": "en-IN"}).status_code == 422
    s = client.post("/api/voice/stt", files={"audio": ("a.wav", wav_bytes(), "audio/wav")}, data={"language": "en-IN"})
    assert s.status_code == 200 and "interface" in s.json()["transcript"]
    h = client.post("/api/voice/stt", files={"audio": ("a.wav", wav_bytes(), "audio/wav")}, data={"language": "hinglish"})
    assert h.status_code == 200 and h.json()["language_code"] == "hi-IN" and SEEN["stt"][-2:] == ["en-hi-IN-latn", "hi-IN"]


def test_offline_full_interview_and_dashboard(client):
    assert llm.provider() == "none"
    iv, fin = run_interview(client, {"role": "Java Developer", "interview_type": "technical", "difficulty": "beginner", "duration": "short"}, 4)
    rep = fin["report"]
    assert rep["answered"] >= 3 and 0 < rep["overall"] <= 100 and rep["engine"] == "offline-rule-based"
    d = client.get("/api/dashboard").json()
    assert d["total_completed"] == 1 and d["sessions"][0]["id"] == iv["id"]
    full = client.get(f"/api/interviews/{iv['id']}").json()
    assert any(t["evaluation"] for t in full["turns"] if t["role"] == "candidate")


def test_other_user_cannot_read(client):
    iv = client.post("/api/interviews", json={"config": {"role": "HR / General", "interview_type": "hr"}}).json()
    other = TestClient(app)
    tok = other.post("/api/auth/guest").json()["token"]
    assert other.get(f"/api/interviews/{iv['id']}", headers={"Authorization": f"Bearer {tok}"}).status_code == 404


def test_clarification_does_not_count(client):
    iv = client.post("/api/interviews", json={"config": {"role": "Python Developer", "duration": "short"}}).json()
    r = client.post(f"/api/interviews/{iv['id']}/answer", json={"text": "Sorry, can you repeat the question?"}).json()
    assert r["kind"] == "clarify" and r["answered"] == 0 and not r["done"]


def test_register_upgrades_guest(client):
    r = client.post("/api/auth/register", json={"email": "a@b.com", "password": "password123", "name": "Asha"})
    assert r.status_code == 200 and r.json()["user"]["is_guest"] is False
    client.headers["Authorization"] = f"Bearer {r.json()['token']}"
    assert client.get("/api/dashboard").json()["total_completed"] == 1  # history survived the upgrade
    assert client.post("/api/auth/login", json={"email": "a@b.com", "password": "nope-nope"}).status_code == 401


def test_llm_path_with_mocked_anthropic(client):
    settings.anthropic_api_key = "k"
    calls = []

    def handler(req: httpx.Request):
        body = json.loads(req.content)
        calls.append(body["system"][:40])
        sysm = body["system"]
        if "evaluator" in sysm:
            out = {"scores": {"accuracy": 90, "relevance": 80, "completeness": 70, "clarity": 60}, "correct_concepts": ["contract"], "missing_concepts": ["default methods"],
                   "inaccuracies": [], "explanation": "ok", "improvements": ["a", "b"], "model_answer": "m", "topic": "OOP"}
        elif "supportive interview coach" in sysm:
            out = {"headline": "Nice work.", "strengths": ["OOP"], "improvements": ["Concurrency"], "study_plan": []}
        else:
            final = "FINAL TURN" in sysm
            out = {"reply": "Thanks, we are done." if final else "Good. What is polymorphism?", "topic": "OOP", "kind": "closing" if final else "main", "candidate_turn_type": "answer"}
        return httpx.Response(200, json={"content": [{"type": "text", "text": "```json\n" + json.dumps(out) + "\n```"}]})

    llm._transport = httpx.MockTransport(handler)
    try:
        iv, fin = run_interview(client, {"role": "Java Developer", "duration": "short"}, 4)
    finally:
        settings.anthropic_api_key = ""; llm._transport = None
    rep = fin["report"]
    assert rep["headline"] == "Nice work." and rep["engine"].startswith("anthropic:")
    # overall = .35*90 + .25*80 + .2*70 + .2*60 = 77.5 -> 78 (weights applied in code, not by the model)
    assert rep["overall"] in (77, 78)
