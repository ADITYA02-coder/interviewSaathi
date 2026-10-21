import asyncio, json, threading
import pytest, websockets
from fastapi.testclient import TestClient
from app.config import settings
from app.main import app

SEEN = {"headers": None, "frames": []}


def start_fake_gnani():
    """A stand-in for wss://api.vachana.ai/stt/v3/stream that follows the documented event flow."""
    ready = threading.Event(); box = {}

    async def handler(conn):
        SEEN["headers"] = dict(conn.request.headers)
        await conn.send(json.dumps({"type": "connected", "message": "ok", "config": {"sample_rate": 48000, "chunk_size": 512}}))
        loud = silent = 0; spoke = False
        async for frame in conn:
            SEEN["frames"].append(len(frame))
            if any(frame):
                loud += 1; silent = 0
                if not spoke:
                    spoke = True; await conn.send(json.dumps({"type": "speech_start"}))
            elif spoke:
                silent += 1
                if silent == 5:
                    await conn.send(json.dumps({"type": "speech_end"})); await conn.send(json.dumps({"type": "processing"}))
                    await asyncio.sleep(0.15)
                    await conn.send(json.dumps({"type": "transcript", "text": "an interface is a contract", "segment_id": "s1", "segment_index": "0", "latency": 150, "audio_duration_ms": 900}))

    async def main():
        server = await websockets.serve(handler, "127.0.0.1", 0)
        box["port"] = server.sockets[0].getsockname()[1]; box["stop"] = asyncio.Event(); ready.set()
        await box["stop"].wait(); server.close()

    loop = asyncio.new_event_loop(); box["loop"] = loop
    threading.Thread(target=lambda: loop.run_until_complete(main()), daemon=True).start()
    ready.wait(5)
    return box


def test_stream_proxy_end_to_end():
    box = start_fake_gnani()
    old = settings.gnani_base_url; settings.gnani_base_url = f"http://127.0.0.1:{box['port']}"
    try:
        with TestClient(app) as c:
            tok = c.post("/api/auth/guest").json()["token"]
            with c.websocket_connect(f"/api/voice/stream?token={tok}&language=hinglish&rate=48000") as ws:
                loud = bytes([1, 2]) * 700          # 1400 bytes: deliberately NOT a multiple of 1024, the proxy must re-frame it
                for _ in range(6):
                    ws.send_bytes(loud)
                for _ in range(12):
                    ws.send_bytes(bytes(1024))
                got = ws.receive_json()
                assert got["type"] == "transcript" and got["text"] == "an interface is a contract"   # partial result arrives while still streaming
                ws.send_text(json.dumps({"type": "end"}))
                fin = ws.receive_json()
                assert fin == {**fin, "type": "final", "text": "an interface is a contract"}
        h = SEEN["headers"]
        assert h["x-api-key-id"] == "test-key" and h["lang_code"] == "hi-IN" and h["x-sample-rate"] == "48000" and h["x-format"] == "transcribe"   # hinglish -> hindi on the realtime socket
        assert set(SEEN["frames"]) == {1024}, SEEN["frames"][:5]                                  # every frame is exactly 1024 bytes
    finally:
        settings.gnani_base_url = old; box["loop"].call_soon_threadsafe(box["stop"].set)


def test_stream_rejects_bad_token_and_rate():
    with TestClient(app) as c:
        with pytest.raises(Exception):
            with c.websocket_connect("/api/voice/stream?token=nope"):
                pass
        tok = c.post("/api/auth/guest").json()["token"]
        with pytest.raises(Exception):
            with c.websocket_connect(f"/api/voice/stream?token={tok}&rate=22050"):
                pass
