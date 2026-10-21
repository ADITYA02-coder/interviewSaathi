import os, tempfile
_tmp = tempfile.mkdtemp()
os.environ.update(DATABASE_URL=os.environ.get("TEST_DATABASE_URL") or f"sqlite:///{_tmp}/t.db", GNANI_API_KEY="test-key", TTS_CACHE_DIR=f"{_tmp}/tts", ANTHROPIC_API_KEY="", OPENAI_API_KEY="", LLM_PROVIDER="auto",
                  JWT_SECRET="x" * 32, ADMIN_EMAILS="boss@college.edu", RUNNER_URL="http://127.0.0.1:9000", RUNNER_SECRET="devsecret123", APP_URL="http://app.test", CORS_ORIGINS="http://localhost:5173,https://interviewsaathi.vercel.app")
