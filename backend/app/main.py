from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from . import problems_seed, questionbank
from .config import settings
from .db import SessionLocal, init_db
from .routes import admin, auth, code, community, dashboard, interview, voice


def check_secrets():
    weak = len(settings.jwt_secret) < 32 or settings.jwt_secret in ("dev-secret-change-me", "change-me-to-a-long-random-string")
    if weak and settings.require_strong_secrets:
        raise RuntimeError("JWT_SECRET is missing or too weak. Generate one with: openssl rand -hex 32")
    if weak:
        print("WARNING: JWT_SECRET is weak. Fine for development, never for production.", flush=True)


def bootstrap():
    """Create tables, then seed the built-in interview questions and coding problems (admins can edit them afterwards)."""
    init_db()
    with SessionLocal() as db:
        questionbank.seed_builtin(db)
        problems_seed.seed(db)


app = FastAPI(title="InterviewSaathi API", version="2.0")
app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origins, allow_origin_regex=settings.cors_origin_regex or None, allow_methods=["*"], allow_headers=["*"])
check_secrets()
bootstrap()
for r in (auth.router, interview.router, code.router, community.router, admin.router, voice.router, dashboard.router):
    app.include_router(r)

dist = settings.frontend_dist
if dist.exists():
    app.mount("/assets", StaticFiles(directory=dist / "assets"), name="assets")

    @app.get("/{path:path}", include_in_schema=False)
    def spa(path: str):
        f = dist / path
        return FileResponse(f if path and f.is_file() else dist / "index.html")
