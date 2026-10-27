# Deploying on Render and Vercel

**Read this first (what each platform can do):**

| Part of the app | Vercel | Render |
|---|---|---|
| Web UI (static React build) | Yes, ideal | Yes (served by the backend) |
| Backend API | **No.** Vercel functions can't run a WebSocket server, and this backend needs one for live transcription, plus background scoring tasks and a database | **Yes** (Docker web service, WebSockets supported) |
| Database | Not applicable | Postgres. **SQLite does not work on Render's free tier**: the disk is wiped on every restart |
| Code runner (coding round) | **No** | Only as a paid *private service*, with weaker isolation than `docker-compose.yml`. See section 4 |

**So there are two valid setups:**

- **Path A, Render only (recommended, simplest):** one Render service serves the UI and the API. Use this unless you specifically want Vercel's CDN.
- **Path B, Vercel + Render:** UI on Vercel, API on Render. Slightly more setup (CORS, one environment variable).

Free-tier facts I checked (Oct 2026): Render free web services **sleep after 15 minutes without traffic** and take about a minute to wake; their filesystem is not persistent; **free Postgres expires after 30 days**; free tier is 512 MB RAM. Fine for a demo; for real students use a paid web service and database.

---

## 0. Put the project on GitHub (both paths)

1. Create an empty **private** repo on GitHub.
2. On your laptop, in the project folder (PowerShell):

```powershell
git init
git add .
git status          # CHECK: .env must NOT be listed. Only .env.example should appear.
git commit -m "InterviewSaathi"
git branch -M main
git remote add origin https://github.com/YOUR-USER/interviewsaathi.git
git push -u origin main
```

`.gitignore` already excludes `.env`. If `.env` ever appears in `git status`, stop and fix that before pushing, because it holds your keys.

---

## Path A: Render only

### A1. Create the services

1. Sign in at render.com with GitHub.
2. **New + > Blueprint**, pick your repo. Render reads `render.yaml` and proposes a **Postgres database** and a **web service**.
3. It asks for the secret values:

| Variable | What to enter |
|---|---|
| `GNANI_API_KEY` | Your Gnani key (both scopes enabled) |
| `OPENAI_API_KEY` | Your Groq key (or other LLM key; edit `OPENAI_BASE_URL`/`OPENAI_MODEL` in `render.yaml` if not Groq) |
| `ADMIN_EMAILS` | The email you will register with, e.g. `you@gmail.com` |
| `ADMIN_PASSWORD` | The password required for that configured admin email. Keep it only in Render Environment variables. |
| `APP_URL` | `https://interviewsaathi.onrender.com`. If Render gives your service a different name/URL, fix this afterwards in the Environment tab |

`JWT_SECRET` is generated for you and `DATABASE_URL` is wired to the database automatically.

4. Click **Apply**. The first build takes roughly 5 to 10 minutes (it builds the UI and the API).

### A2. Check it

Open `https://YOUR-SERVICE.onrender.com/api/meta`. You want `"gnani_configured": true` and `"llm_live": true`. (`coding_enabled` will be false until you do section 4.) Register with your admin email, then **verify it**: without SMTP the verification link is printed in the Render **Logs** tab (search for `DEV EMAIL`); open it in your browser. The Admin link appears after that. Then run a voice interview.

### A3. Optional demo data

Render's free tier has no shell, so seed from **your laptop** against the Render database:

1. Render dashboard > your database > copy the **External Database URL**.
2. In PowerShell, from the `backend` folder (venv active, `pip install -r requirements.txt` done):

```powershell
$env:DATABASE_URL = "PASTE-THE-EXTERNAL-URL-HERE"
python -m scripts.seed_demo --yes        # later: python -m scripts.seed_demo --remove
```

Remove demo data before real students use the system.

---

## Path B: Vercel (UI) + Render (API)

### B1. Deploy the API on Render
Do **A1 and A2** exactly as above. Note your API URL, e.g. `https://interviewsaathi.onrender.com`.

### B2. Deploy the UI on Vercel
1. vercel.com > **Add New > Project** > import the same GitHub repo.
2. **Root Directory: `frontend`** (important). Framework preset: Vite (auto-detected); build command `npm run build`; output `dist`.
3. **Environment Variables** (Production, and Preview if you use previews):
   - `VITE_API_URL` = `https://interviewsaathi.onrender.com` (your Render API URL, no trailing slash)
4. **Deploy.** Note the URL, e.g. `https://interviewsaathi.vercel.app`.

> **Never put secret keys in Vercel variables.** Anything starting with `VITE_` is shipped to every visitor's browser. Only the public API address goes here. Gnani and LLM keys stay on Render.

### B3. Tell the API about the UI
In Render > your service > **Environment**, add/update:

| Variable | Value |
|---|---|
| `CORS_ORIGINS` | `https://interview-saathi-neon.vercel.app` (comma-separate several: custom domain too) |
| `APP_URL` | `https://interview-saathi-neon.vercel.app` (so reset/verification emails link to the UI) |

Save; Render redeploys. The value must match the browser address **exactly**: `https`, no trailing slash.

Vercel preview deployments get different URLs. To allow them, add `CORS_ORIGIN_REGEX` = `https://.*\.vercel\.app`. This lets any Vercel-hosted site call your API from a browser, so use it only while testing.

### B4. Check it
Open the Vercel URL. In the browser's developer tools (Network tab), requests should go to `onrender.com/api/...`, and the live-transcription socket to `wss://...onrender.com/api/voice/stream`. Changing `VITE_API_URL` requires a **redeploy** of the Vercel project, because it is baked in at build time.

---

## 4. The coding round on Render/Vercel

The runner executes untrusted student code. Options, best first:

| Option | Notes |
|---|---|
| **A small VPS running the full stack** | Follow `DEPLOYMENT.md`. Best isolation (no internet, read-only, capped). Then you don't need Render at all. |
| **Render private service** (paid, "Starter" or higher) | Uncomment the `pserv` block in `render.yaml`. Then on the web service set `RUNNER_URL=http://interviewsaathi-runner:9000` and the same `RUNNER_SECRET` on both. Student code **can reach the internet** from there and Render can't apply the container hardening in `docker-compose.yml`. I have not been able to test this on Render. |
| **Leave coding off** | Don't set `RUNNER_URL`. The coding option is greyed out; everything else works. |

Do not expose the runner publicly: it is a remote-code-execution endpoint protected only by a shared secret.

---

## 4b. No email on the free tier? Use admin approval

Render's free tier has no mail service. Add `EMAIL_VERIFICATION=admin` in the Environment tab. Students register, no email is sent, and you approve them in **Admin > Users** (*Mark verified*, or *Verify all*). The one exception is the address in `ADMIN_EMAILS`: it still gets a verification link, printed in the Render **Logs** tab (search for `DEV EMAIL`), so you can become admin without any command line. Password-reset emails still need SMTP. To send real emails from Render **free**, use Brevo on port 2525 (Render blocks 25/465/587 on free instances): see `SMTP_SETUP.md`.

## 5. Tell students and admins about free-tier behaviour

- **First load after idle takes about a minute** (Render waking). Open the site a few minutes before a class, or pay for a non-sleeping instance.
- **Database:** free Postgres is deleted after 30 days. Before that, either upgrade it or point `DATABASE_URL` at an external Postgres (Neon, Supabase; check their current free limits) and redeploy. Tables are created automatically on first start. Existing data does not move by itself: copy it with `pg_dump` / `psql`.
- **Rate limits:** a free LLM key will not survive a class answering at once. See `DEPLOYMENT.md` ("Capacity").

## 6. Troubleshooting

| Symptom | Cause / fix |
|---|---|
| Vercel page loads but "Can't reach the server" | `VITE_API_URL` missing or wrong, or you didn't redeploy after setting it; or the Render API is asleep (wait a minute, refresh) |
| Browser console: **CORS error** | `CORS_ORIGINS` doesn't exactly match the Vercel address (scheme, host, no trailing slash); redeploy Render after changing |
| Typing works, voice doesn't | Gnani key missing/wrong (`/api/meta`), or microphone blocked. Streaming failures fall back to upload automatically |
| Everything resets after a while | The database is not Postgres, or the free Postgres expired (30 days). Check `DATABASE_URL` |
| Render build fails | Open the build log. `dockerContext` must be the repo root (`.`) because the Dockerfile copies `frontend/` and `backend/` |
| Boot loop: "JWT_SECRET is missing or too weak" | Use the generated value, or at least 32 random characters |
| Admin link missing | The email you registered with isn't in `ADMIN_EMAILS` (exact match). Fix it, then sign out and in |
| Reset emails never arrive | No SMTP configured: emails are only printed in the Render logs. Add the `SMTP_*` variables |

## What I tested and what I could not

- **Tested for real:** the backend and all 24 backend tests on **PostgreSQL 16** and SQLite; a Render-style boot (`$PORT`, Postgres, seeded data, admin promotion); the CORS rules; a Vercel-style build with `VITE_API_URL`.
- **Not tested** (no Render/Vercel accounts or Docker here): the actual Render Blueprint deploy, the Vercel deploy, the Render private-service runner. `render.yaml` follows Render's documented format, but if Render rejects any field, send me the exact message and I'll fix it.
