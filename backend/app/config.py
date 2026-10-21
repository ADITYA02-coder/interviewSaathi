import os
from pathlib import Path
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / ".env")


def _env(name: str, default: str = "") -> str:
    return os.environ.get(name, default).strip()


DEMO_EMAIL_DOMAIN = "demo.interviewsaathi.app"   # accounts created by scripts/seed_demo.py; the mailer never emails them


def _db_url(url: str) -> str:
    """Hosts hand out postgres:// or postgresql:// URLs. Pin the psycopg (v3) driver so it works whatever SQLAlchemy's default is."""
    for prefix in ("postgres://", "postgresql://"):
        if url.startswith(prefix):
            return "postgresql+psycopg://" + url[len(prefix):]
    return url


class Settings:
    gnani_api_key = _env("GNANI_API_KEY")
    gnani_base_url = _env("GNANI_BASE_URL", "https://api.vachana.ai").rstrip("/")
    gnani_tts_model = _env("GNANI_TTS_MODEL", "timbre-v2.5")
    gnani_stt_format = _env("GNANI_STT_FORMAT", "transcribe")

    llm_provider = _env("LLM_PROVIDER", "auto").lower()
    anthropic_api_key = _env("ANTHROPIC_API_KEY")
    anthropic_model = _env("ANTHROPIC_MODEL", "claude-sonnet-5-5")
    openai_api_key = _env("OPENAI_API_KEY")
    openai_base_url = _env("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/")
    openai_model = _env("OPENAI_MODEL", "gpt-4o-mini")

    gnani_streaming = _env("GNANI_STREAMING", "true").lower() in ("1", "true", "yes")

    runner_url = _env("RUNNER_URL").rstrip("/")
    runner_secret = _env("RUNNER_SECRET")
    admin_emails = {e.strip().lower() for e in _env("ADMIN_EMAILS").split(",") if e.strip()}
    # "email": verification link by email.  "admin": no email is sent; an admin approves students in Admin > Users (good when you have no SMTP).
    verification_mode = "admin" if _env("EMAIL_VERIFICATION", "email").lower() == "admin" else "email"
    app_url = _env("APP_URL", "http://localhost:5173").rstrip("/")
    smtp_host = _env("SMTP_HOST")
    smtp_port = int(_env("SMTP_PORT", "587") or 587)
    smtp_security = _env("SMTP_SECURITY", "").lower()   # starttls | ssl | none (default: ssl on port 465, otherwise starttls)
    smtp_user = _env("SMTP_USER")
    smtp_password = _env("SMTP_PASSWORD")
    smtp_from = _env("SMTP_FROM", "InterviewSaathi <no-reply@localhost>")

    require_strong_secrets = _env("REQUIRE_STRONG_SECRETS", "0") in ("1", "true", "yes")
    jwt_secret = _env("JWT_SECRET", "dev-secret-change-me")
    database_url = _db_url(_env("DATABASE_URL", f"sqlite:///{ROOT / 'interviewsaathi.db'}"))
    cors_origin_regex = _env("CORS_ORIGIN_REGEX")   # optional, e.g. https://.*\.vercel\.app to allow Vercel preview deployments
    cors_origins = [o.strip() for o in _env("CORS_ORIGINS", "http://localhost:5173").split(",") if o.strip()]
    tts_cache_dir = Path(_env("TTS_CACHE_DIR", str(ROOT / ".tts_cache")))
    frontend_dist = ROOT / "frontend" / "dist"


settings = Settings()
