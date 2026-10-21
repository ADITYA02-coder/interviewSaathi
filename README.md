# InterviewSaathi

Practise placement interviews by **talking to an AI interviewer on screen**. She speaks (Gnani **Timbre**), listens (Gnani **Prisma**), reacts, asks follow-ups, runs a **coding round** with a sandboxed judge, and afterwards shows scores, missing concepts and a study plan. Placement cells get **admin tools**: groups, assigned interviews, a leaderboard, question and problem management.

```
you speak ─► (audio streams live) ─► Gnani Prisma ─► interviewer brain ─► Gnani Timbre ─► animated face lip-syncs to the audio
                                                          └─► answers are scored in the background
coding round:  explain approach (voice) ─► code in browser ─► Run / Submit ─► [runner sandbox] ─► she asks about complexity (voice)
```

## Run it

```bash
cp .env.example .env                       # paste GNANI_API_KEY; optionally an LLM key; set ADMIN_EMAILS=you@college.edu

# backend
cd backend && python -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt
python -m scripts.check_gnani              # DO THIS FIRST once the key is set (see "Gnani checks")
uvicorn app.main:app --reload --port 8000

# frontend (second terminal)
cd frontend && npm install && npm run dev  # http://localhost:5173

# code runner (third terminal; only for coding rounds, development mode). WINDOWS / POWERSHELL: see runner/README.md
cd runner && pip install -r requirements.txt
RUNNER_CONFIRM_ISOLATED=1 RUNNER_SECRET=choose-a-long-secret uvicorn app:app --port 9000   # bash only; PowerShell uses $env:VAR = "..." instead
#   then in .env:  RUNNER_URL=http://127.0.0.1:9000   RUNNER_SECRET=choose-a-long-secret
```

**Production, one command** (HTTPS + backend + web app + locked-down runner): see *Deploy to production* below.

## Deploy to production

- **Render and/or Vercel:** **[DEPLOY_VERCEL_RENDER.md](DEPLOY_VERCEL_RENDER.md)** (free-tier realities, Postgres, CORS, what can and can't run there).
- **Windows runner problems:** **[runner/README.md](runner/README.md)** has exact PowerShell commands and a troubleshooting table.
- **A real server with Docker and HTTPS (best isolation):**

Full step-by-step guide (server, domain, HTTPS, backups, troubleshooting): **[DEPLOYMENT.md](DEPLOYMENT.md)**. Short version: `cp .env.example .env`, set `DOMAIN`, `JWT_SECRET`, `RUNNER_SECRET` and your keys, then `docker compose up -d --build`.

## Demo data

`python -m scripts.seed_demo --yes` adds 12 clearly-labelled demo students (46 interviews, groups `DEMO01`/`DEMO02`, templates, support requests) so the admin dashboard has something to show; `--remove` deletes all of it. Demo accounts use `@demo.interviewsaathi.app`, their reports are generated and labelled `demo-seed`, and the app never emails them. Remove it before real students use the system.

## Admin

Register with an address listed in `ADMIN_EMAILS`, then **verify that email** (see *Email verification* below). Admin rights are granted only to a verified address, so nobody can claim your admin email by registering first. The **Admin** link then appears in the top bar. (Alternative: `python -m scripts.make_admin you@college.edu`.)

| Tab | What it does |
|---|---|
| Overview | students, completed interviews, average score, active users, voice vs typed answers, languages, code accept rate, 30-day activity |
| Leaderboard | who is doing best: rank, average, latest, best, improvement trend, problems solved, weakest topic, "needs attention" flag. Filter by group and type, sort by 6 measures, export CSV. Click a student for their trend, topics and interviews |
| Groups & templates | create a group (gets a join code), assign an interview (role, type, difficulty, language, specific coding problems, a focus note) to a group or everyone. Students start it in one click from Setup |
| Questions | add, edit, disable the interview questions and the concepts the offline scorer looks for. The AI interviewer is also offered them as a preferred pool |
| Coding problems | add problems with sample and hidden tests; **validate** your reference solution against all tests in the sandbox |
| Support | students' requests, with replies they can see |
| Users | promote or demote admins |

**Privacy model (deliberate).** A student appears to admins only after joining one of their groups with its code; that is their consent to share **scores, trends and report summaries**. Their **answers and submitted code stay private** unless they also switch on "let admins read my answers" in their profile. Leaving a group removes access immediately. Admins cannot browse arbitrary users.

## Coding round

For each problem: she explains the task and asks for your **approach** (voice, scored) → you **code** in the browser (Python, JavaScript, Java; run the samples any time; she answers clarifying questions without giving away the solution) → **Submit** runs all tests including hidden ones → she reacts to your real results and asks about **time/space complexity and edge cases** (voice, scored). Problem score = 50% tests + 25% approach + 25% complexity. Hidden tests never reveal their input or expected output. 12 built-in problems (arrays, strings, stacks, DP, graphs, heaps...). Practise without an interviewer under **Code**.

**The sandbox** (`runner/`) is a separate service. The main server never executes user code. The runner: only starts inside its container (or with an explicit `RUNNER_CONFIRM_ISOLATED=1`), requires a shared secret, runs code as the unprivileged `nobody` user in a throw-away directory with CPU-time, file-size, process-count and wall-clock limits, scrubs the environment, reaps every leftover process, and in `docker-compose.yml` has **no internet**, a read-only filesystem, no capabilities except switching to `nobody`, and CPU/memory/PID caps. Do not expose it publicly.

## Streaming speech-to-text

While you talk, the browser streams 16-bit PCM to `/api/voice/stream`; the backend re-frames it into the exact 1024-byte frames Gnani's realtime socket expects and relays finished segments back as live captions. By the time you stop speaking the transcript is usually ready, which removes the upload-and-transcribe wait. If streaming fails for any reason (or the browser's sample rate isn't supported) it silently falls back to the one-shot upload. Hinglish has no realtime code, so streaming uses Hindi recognition for it.

## Gnani checks (do these once your key arrives)

`python -m scripts.check_gnani` synthesises a sentence per language with Timbre, feeds it back into Prisma, and prints latency and transcripts. Only promise languages that pass. Also confirm: Hinglish (experimental code, auto-falls back to `hi-IN`), the voice genders for non-English languages (inferred from names, fix `LANGUAGES` in `gnani.py` if wrong), and `GNANI_STT_FORMAT` (`transcribe` vs `verbatim`) on technical answers.

## The interviewer's brain

Gnani is the voice. Follow-ups and scoring need a reasoning model: set `ANTHROPIC_API_KEY`, or any OpenAI-compatible key (free options: Groq, Cerebras, Gemini; see the earlier chat). With none, an offline question bank with keyword scoring runs (English only) and reports say "offline-rule-based". Scores are weighted in code, not by the model; the prompt forbids rewarding length or fluent English and penalising accent, Hinglish or transcription errors.

## Email verification

**Two modes** (`EMAIL_VERIFICATION` in `.env`): `email` (default) sends a link; `admin` sends **no email at all** and an admin approves students instead (**Admin > Users**: *Mark verified* per student, *Unverified only* filter, *Verify all N shown*, and a red count badge on the Users tab). Use `admin` when you have no SMTP. In `admin` mode ordinary students get no email, but the address in `ADMIN_EMAILS` still gets its link (printed in the server log / Render Logs when there's no SMTP) so your first admin can verify without any command line. "Forgot password" emails won't work without SMTP.

In `email` mode every new account gets a verification email with a link (valid 48 hours, opens `APP_URL/#/verify/...`). Verification doesn't block students from practising; it is required for admin rights.

| Situation | How to verify |
|---|---|
| SMTP configured | Click the link in the email. Students can resend it from **Profile** (max 3 per hour) |
| No SMTP (development, Render free) | The email is **printed in the server terminal / Render logs**: copy the link into the browser |
| You'd rather not hunt for the link | `python -m scripts.verify_email you@college.edu` (also applies `ADMIN_EMAILS`) |
| A student can't receive mail | Admin > Users > **Mark verified** |

Set `APP_URL` to the address people actually open (`http://localhost:8000` if you only run the backend, `http://localhost:5173` with the Vite dev server), otherwise the link points to the wrong place.

## Email

**Step-by-step SMTP setup (Brevo, Gmail, Render's blocked ports, testing): [SMTP_SETUP.md](SMTP_SETUP.md).** Admin > **Email** shows the status and has a *Send test email* button that explains failures.

Verification and password-reset emails use `SMTP_*`. Without SMTP they are **printed in the server console only**: links are never returned by the API, so a missing mail config can't be used to take over accounts.

## Tests

```bash
cd backend && backend/tests/run_with_runner.sh pytest     # 24 tests; the coding ones use the real sandbox
cd frontend && npm test                                   # drives the real UI through a voice interview, a coding interview, practice and admin pages
```
`tests/solutions.py` holds independent solutions that prove all 12 built-in problems' tests are correct, in the real sandbox.

## Known limits

- Never exercised against live Gnani (no key during development): requests follow Gnani's official client and are checked against mock servers, including the realtime WebSocket framing.
- Never viewed in a real browser by the developer: the UI is tested through jsdom with fake audio devices. Check the avatar animation, microphone and autoplay on your machine first.
- `docker compose` files are provided but were not built in the development environment (no Docker there). The runner's hardening was tested directly (privilege drop, resource limits, process cleanup, hostile code).
- Rate limiting is in-memory (single worker). SQLite is fine for a college cohort; for more, point `DATABASE_URL` at Postgres and add Alembic migrations.
- Not built: SSO, C++ in the coding round, analytics export beyond CSV.
