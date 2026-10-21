import asyncio
import json
import time
import jwt
from fastapi import APIRouter, Depends, File, Form, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel, Field
from .. import gnani
from ..config import settings
from ..db import SessionLocal, User
from ..security import current_user

router = APIRouter(prefix="/api/voice", tags=["voice"])
ALLOWED_VOICES = {v for cfg in gnani.LANGUAGES.values() for v in cfg["voices"].values() if v}
ALLOWED_TTS_LANGS = {cfg["tts"] for cfg in gnani.LANGUAGES.values()}


class TTSIn(BaseModel):
    text: str = Field(min_length=1, max_length=700)
    voice: str
    language: str = "en-IN"
    speed: float = 1.0


def _err(e: gnani.GnaniError):
    return JSONResponse({"detail": str(e), "code": e.code}, status_code=e.status)


@router.post("/stt")
async def stt(audio: UploadFile = File(...), language: str = Form("en-IN"), _=Depends(current_user)):
    data = await audio.read()
    if len(data) > 10 * 1024 * 1024:
        return JSONResponse({"detail": "Recording is too large.", "code": "too_large"}, status_code=413)
    if len(data) < 800:
        return JSONResponse({"detail": "Recording was empty.", "code": "empty_audio"}, status_code=422)
    t0 = time.perf_counter()
    try:
        out = await gnani.transcribe(data, audio.filename or "answer.wav", audio.content_type or "audio/wav", language)
    except gnani.GnaniError as e:
        return _err(e)
    out["latency_ms"] = round((time.perf_counter() - t0) * 1000)
    return out


@router.post("/tts")
async def tts(body: TTSIn, _=Depends(current_user)):
    if body.voice not in ALLOWED_VOICES or body.language not in ALLOWED_TTS_LANGS:
        return JSONResponse({"detail": "Unknown voice or language.", "code": "bad_voice"}, status_code=422)
    try:
        audio = await gnani.synthesize(body.text, body.voice, body.language, body.speed)
    except gnani.GnaniError as e:
        return _err(e)
    return Response(content=audio, media_type="audio/mpeg", headers={"Cache-Control": "private, max-age=86400"})


@router.websocket("/stream")
async def stream(ws: WebSocket, token: str = "", language: str = "en-IN", rate: int = 48000):
    """Live speech-to-text. The browser sends raw 16-bit mono PCM frames; we forward them to Gnani Prisma's realtime socket (server-side VAD)
    and push each finished segment back as {"type":"transcript"}. When the browser sends {"type":"end"} we wait for the last segment and
    answer {"type":"final","text":...}. The Gnani key never leaves the server."""
    try:
        data = jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])
        with SessionLocal() as db:
            ok = db.get(User, int(data["sub"])) is not None and not data.get("purpose")
    except Exception:
        ok = False
    if not ok:
        await ws.close(code=4401)
        return
    if not (gnani.configured() and settings.gnani_streaming) or rate not in gnani.STREAM_RATES:
        await ws.close(code=4503)
        return
    await ws.accept()
    try:
        up = await gnani.stream_connect(language, rate)
    except Exception:
        await ws.send_json({"type": "unavailable"})
        await ws.close()
        return

    st = {"texts": [], "in_speech": False, "awaiting": False, "t0": time.perf_counter()}

    async def down():  # Gnani -> browser
        try:
            async for raw in up:
                try:
                    ev = json.loads(raw)
                except (TypeError, ValueError):
                    continue
                t = ev.get("type")
                if t in ("speech_start", "vad_start"):
                    st["in_speech"], st["awaiting"] = True, False
                elif t in ("speech_end", "vad_end", "processing"):
                    st["in_speech"], st["awaiting"] = False, True
                elif t == "transcript":
                    st["in_speech"], st["awaiting"] = False, False
                    text = (ev.get("text") or "").strip()
                    if text:
                        st["texts"].append(text)
                        await ws.send_json({"type": "transcript", "text": text, "latency": ev.get("latency")})
                elif t == "error":
                    await ws.send_json({"type": "error", "message": ev.get("message", "")})
        except Exception:
            pass

    async def finish(buf: bytearray):
        if buf:
            buf.extend(b"\x00" * (gnani.STREAM_FRAME_BYTES - len(buf)))
            await up.send(bytes(buf))
            buf.clear()
        waited = 0.0
        while waited < 3.0 and not (not st["in_speech"] and not st["awaiting"] and (st["texts"] or waited >= 0.9)):
            await asyncio.sleep(0.1)
            waited += 0.1
        await ws.send_json({"type": "final", "text": " ".join(st["texts"]), "latency_ms": round((time.perf_counter() - st["t0"]) * 1000)})

    reader = asyncio.create_task(down())
    buf = bytearray()
    try:
        while True:
            msg = await ws.receive()
            if msg["type"] == "websocket.disconnect":
                break
            if msg.get("bytes"):
                buf.extend(msg["bytes"])
                while len(buf) >= gnani.STREAM_FRAME_BYTES:
                    await up.send(bytes(buf[: gnani.STREAM_FRAME_BYTES]))
                    del buf[: gnani.STREAM_FRAME_BYTES]
            elif msg.get("text"):
                try:
                    if json.loads(msg["text"]).get("type") == "end":
                        await finish(buf)
                        break
                except ValueError:
                    pass
    except WebSocketDisconnect:
        pass
    except Exception:
        pass
    finally:
        reader.cancel()
        try:
            await up.close()
        except Exception:
            pass
        try:
            await ws.close()
        except Exception:
            pass
