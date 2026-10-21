"""Gnani voice layer: Prisma (speech-to-text) and Timbre (text-to-speech).

Contract taken from Gnani's official client (gnani-vachana):
  STT  POST {base}/stt/v3                 multipart: audio_file, language_code, format   (<= 60 s clips)
  TTS  POST {base}/api/v1/tts/inference   JSON: text, model, voice, language, speed, audio_config
  Auth header on every call: X-API-Key-ID
"""
import hashlib
import uuid
import httpx
from .config import settings

STT_LANGUAGES = {
    "en-IN": "English (India)", "hi-IN": "Hindi", "gu-IN": "Gujarati", "ta-IN": "Tamil", "kn-IN": "Kannada",
    "te-IN": "Telugu", "mr-IN": "Marathi", "bn-IN": "Bengali", "ml-IN": "Malayalam", "pa-IN": "Punjabi",
}
HINGLISH_STT = "en-hi-IN-latn"  # documented as experimental (Latin-script Hinglish)

# UI language key -> (STT code, TTS language, voices by gender)
LANGUAGES = {
    "en-IN": {"label": "English", "stt": "en-IN", "tts": "en-IN", "voices": {"female": "Kaveri", "male": "Pranav"}},
    "hi-IN": {"label": "Hindi", "stt": "hi-IN", "tts": "hi-IN", "voices": {"female": "Nalini", "male": "Deepak"}},
    "hinglish": {"label": "Hinglish", "stt": HINGLISH_STT, "tts": "auto", "voices": {"female": "Poorvi", "male": "Deepak"}, "stt_fallback": "hi-IN"},
    "ta-IN": {"label": "Tamil", "stt": "ta-IN", "tts": "ta-IN", "voices": {"female": "Asmita", "male": None}},
    "te-IN": {"label": "Telugu", "stt": "te-IN", "tts": "te-IN", "voices": {"female": "Suhana", "male": None}},
    "kn-IN": {"label": "Kannada", "stt": "kn-IN", "tts": "kn-IN", "voices": {"female": "Saanvi", "male": "Kavin"}},
    "ml-IN": {"label": "Malayalam", "stt": "ml-IN", "tts": "ml-IN", "voices": {"female": "Reshma", "male": "Riyaan"}},
    "mr-IN": {"label": "Marathi", "stt": "mr-IN", "tts": "mr-IN", "voices": {"female": "Zahira", "male": "Ishaan"}},
    "bn-IN": {"label": "Bengali", "stt": "bn-IN", "tts": "bn-IN", "voices": {"female": "Kirra", "male": "Dhruva"}},
    "gu-IN": {"label": "Gujarati", "stt": "gu-IN", "tts": "gu-IN", "voices": {"female": "Falak", "male": None}},
    "pa-IN": {"label": "Punjabi", "stt": "pa-IN", "tts": "pa-IN", "voices": {"female": "Mehuli", "male": "Zayan"}},
}


STREAM_LANGUAGES = {"bn-IN", "en-IN", "gu-IN", "hi-IN", "kn-IN", "ml-IN", "mr-IN", "pa-IN", "ta-IN", "te-IN"}
STREAM_RATES = (8000, 16000, 44100, 48000)
STREAM_FRAME_BYTES = 1024  # 512 samples x 16-bit: the frame size Gnani's realtime endpoint expects


def stream_language(language: str) -> str:
    """Realtime STT has no Hinglish code: Hinglish falls back to Hindi recognition."""
    cfg = LANGUAGES.get(language, LANGUAGES["en-IN"])
    for code in (cfg["stt"], cfg.get("stt_fallback"), "en-IN"):
        if code in STREAM_LANGUAGES:
            return code


def stream_url() -> str:
    base = settings.gnani_base_url
    return ("wss://" + base[8:] if base.startswith("https://") else "ws://" + base[7:] if base.startswith("http://") else base) + "/stt/v3/stream"


def stream_headers(language: str, rate: int) -> dict:
    h = {"x-api-key-id": settings.gnani_api_key, "lang_code": stream_language(language), "x-sample-rate": str(rate), "x-api-request-id": uuid.uuid4().hex}
    if settings.gnani_stt_format and settings.gnani_stt_format != "verbatim":
        h["x-format"] = settings.gnani_stt_format
    return h


async def stream_connect(language: str, rate: int):
    import websockets
    headers = stream_headers(language, rate)
    try:
        from websockets.asyncio.client import connect  # websockets >= 13
        return await connect(stream_url(), additional_headers=headers, open_timeout=8, ping_interval=20, max_size=2 ** 20)
    except ImportError:
        return await websockets.connect(stream_url(), extra_headers=headers, open_timeout=8, ping_interval=20)


class GnaniError(Exception):
    def __init__(self, message: str, status: int = 502, code: str = "gnani_error"):
        super().__init__(message)
        self.status, self.code = status, code


def configured() -> bool:
    return bool(settings.gnani_api_key)


def _headers() -> dict:
    return {"X-API-Key-ID": settings.gnani_api_key, "X-API-Request-ID": uuid.uuid4().hex}


# Tests swap this to inject httpx.MockTransport.
_transport = None


def _client(timeout: float = 45.0) -> httpx.AsyncClient:
    return httpx.AsyncClient(base_url=settings.gnani_base_url, timeout=timeout, transport=_transport)


def pick_voice(language: str, gender: str) -> tuple[str, str]:
    cfg = LANGUAGES.get(language, LANGUAGES["en-IN"])
    voice = cfg["voices"].get(gender) or cfg["voices"].get("female")
    return voice, cfg["tts"]


async def transcribe(audio: bytes, filename: str, content_type: str, language: str) -> dict:
    if not configured():
        raise GnaniError("GNANI_API_KEY is not set on the server.", 503, "gnani_not_configured")
    cfg = LANGUAGES.get(language, LANGUAGES["en-IN"])
    codes = [cfg["stt"]] + ([cfg["stt_fallback"]] if cfg.get("stt_fallback") else [])
    last = ""
    async with _client(60) as c:
        for code in codes:
            r = await c.post(
                "/stt/v3", headers=_headers(),
                files={"audio_file": (filename, audio, content_type)},
                data={"language_code": code, "format": settings.gnani_stt_format},
            )
            if r.status_code == 200:
                body = r.json()
                text = (body.get("transcript") or "").strip()
                return {"transcript": text, "language_code": code, "request_id": body.get("request_id")}
            last = f"{r.status_code}: {r.text[:200]}"
            if r.status_code in (401, 403):
                raise GnaniError("Gnani rejected the API key.", 502, "gnani_auth")
    raise GnaniError(f"Gnani speech-to-text failed ({last})")


async def synthesize(text: str, voice: str, language: str, speed: float = 1.0) -> bytes:
    if not configured():
        raise GnaniError("GNANI_API_KEY is not set on the server.", 503, "gnani_not_configured")
    speed = max(0.85, min(1.15, speed))
    key = hashlib.sha256(f"{settings.gnani_tts_model}|{voice}|{language}|{speed}|{text}".encode()).hexdigest()
    path = settings.tts_cache_dir / f"{key}.mp3"
    if path.exists():
        return path.read_bytes()
    body = {
        "text": text, "model": settings.gnani_tts_model, "voice": voice,
        "audio_config": {"sample_rate": 24000, "encoding": "linear_pcm", "num_channels": 1,
                         "sample_width": 2, "container": "mp3", "bitrate": "96k"},
    }
    if settings.gnani_tts_model == "timbre-v2.5":
        body["language"] = language
        body["speed"] = speed
    async with _client() as c:
        r = await c.post("/api/v1/tts/inference", headers=_headers(), json=body)
    if r.status_code in (401, 403):
        raise GnaniError("Gnani rejected the API key.", 502, "gnani_auth")
    if r.status_code != 200 or not r.content:
        raise GnaniError(f"Gnani text-to-speech failed ({r.status_code}: {r.text[:200]})")
    settings.tts_cache_dir.mkdir(parents=True, exist_ok=True)
    path.write_bytes(r.content)
    return r.content
