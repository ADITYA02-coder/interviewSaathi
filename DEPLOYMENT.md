# Deploying InterviewSaathi (step by step)

**The setup:** one Linux server running three containers: **Caddy** (free automatic HTTPS), the **app** (API + web UI), and the **code runner** (locked-down sandbox with no internet). Only Caddy is reachable from outside.

> Why HTTPS is mandatory: browsers only allow the microphone on `https://` pages (or `localhost`). Without it, voice interviews silently do nothing.

## Before you start: what you need

| Item | Notes |
|---|---|
| A server | Ubuntu 22.04 or 24.04, **2 vCPU / 4 GB RAM / 25 GB disk** minimum. Pick a region near India (e.g. Mumbai) for lower voice latency. Any provider works: AWS (Lightsail/EC2), DigitalOcean, Azure, GCP, Hetzner, Oracle Cloud. |
| A domain name | e.g. `interview.yourcollege.edu`. **No domain?** Use `<server-ip-with-dashes>.sslip.io` (for IP `203.0.113.10` use `203-0-113-10.sslip.io`). Good for demos. |
| Gnani key | Both scopes on (Text to Speech and Speech to Text). |
| An LLM key | Groq/Anthropic/OpenAI-compatible. See the README. |
| Optional | SMTP login for real password-reset emails. |

## Step 1. Create the server and open the firewall

1. Create the Ubuntu server and note its **public IP**.
2. In the provider's firewall / security group allow inbound **TCP 22** (SSH), **TCP 80** and **TCP 443**, and **UDP 443** (optional, faster HTTPS). Nothing else. Never open 8000 or 9000.

## Step 2. Point your domain at it

Add a DNS **A record**: `interview.yourcollege.edu` → your server IP. Check it (from your laptop):

```bash
dig +short interview.yourcollege.edu      # must print your server IP; can take a few minutes
```

If this is wrong, HTTPS certificate issuing will fail in Step 6.

## Step 3. Prepare the server

```bash
ssh root@YOUR_SERVER_IP                       # or ubuntu@... depending on the provider
apt-get update && apt-get -y upgrade
curl -fsSL https://get.docker.com | sh        # installs Docker + Compose
ufw allow 22 && ufw allow 80 && ufw allow 443 && ufw allow 443/udp && ufw --force enable
docker compose version                        # should print a version
```

Only 2 GB of RAM? Add swap first so the build doesn't run out of memory:
`fallocate -l 2G /swapfile && chmod 600 /swapfile && mkswap /swapfile && swapon /swapfile`

## Step 4. Put the project on the server

From your laptop (where `interviewsaathi.zip` is):

```bash
scp interviewsaathi.zip root@YOUR_SERVER_IP:/opt/
ssh root@YOUR_SERVER_IP
apt-get install -y unzip && cd /opt && unzip interviewsaathi.zip && cd interviewsaathi
```

(Using git instead? `git clone <your repo> /opt/interviewsaathi`. Make sure `.env` is **not** committed.)

## Step 5. Configure `.env`

```bash
cp .env.example .env
echo "JWT_SECRET=$(openssl rand -hex 32)"; echo "RUNNER_SECRET=$(openssl rand -hex 16)"    # copy these two lines
nano .env
```

Set at least:

```ini
DOMAIN=interview.yourcollege.edu
JWT_SECRET=<the 64-character value you just generated>
RUNNER_SECRET=<the 32-character value you just generated>
ADMIN_EMAILS=you@yourcollege.edu

GNANI_API_KEY=<your Gnani key>

LLM_PROVIDER=openai
OPENAI_API_KEY=<your Groq or other key>
OPENAI_BASE_URL=https://api.groq.com/openai/v1
OPENAI_MODEL=openai/gpt-oss-120b
```

Then lock the file down: `chmod 600 .env`. Leave `RUNNER_URL=` empty here; compose fills it in. The backend **refuses to start** with a weak `JWT_SECRET`.

## Step 6. Launch

```bash
docker compose up -d --build        # first build takes 3 to 8 minutes
docker compose ps                   # all three should be "running"; backend "healthy"
docker compose logs -f caddy        # look for "certificate obtained successfully", then Ctrl+C
```

## Step 7. Verify (do every line)

1. Open `https://interview.yourcollege.edu`. The padlock shows and the landing page loads.
2. Open `https://interview.yourcollege.edu/api/meta` and confirm:
   - `"gnani_configured": true`
   - `"llm_live": true`
   - `"coding_enabled": true`
   - `"stream_stt": true`
3. Register with the email in `ADMIN_EMAILS`, then **verify it**: click the link in the email, or (no SMTP yet) find it with `docker compose logs backend | grep -A3 "DEV EMAIL"`, or run `docker compose exec backend python -m scripts.verify_email you@yourcollege.edu`. The **Admin** link appears after verification.
4. **Practise** → start an interview → click *Join*, allow the microphone, and answer by voice. You should hear the Timbre voice and see your words appear live as you speak.
5. Start a **Coding round**, run the samples, and submit.
6. From a **second device or browser**, register as a student, join a group (create one in Admin first), finish an interview, and confirm it appears in the Leaderboard.

## Step 8. Optional: demo data for a presentation

```bash
docker compose exec backend python -m scripts.seed_demo --yes      # 12 demo students, 46 interviews, 2 groups
docker compose exec backend python -m scripts.seed_demo --remove   # deletes ALL demo data
```

Demo logins: `admin@demo.interviewsaathi.app` / `DemoAdmin123!`, students `priya.sharma@demo.interviewsaathi.app` (and others) / `demo12345`, group codes `DEMO01` and `DEMO02`.
**Remove demo data before real students arrive**, or it will appear in your leaderboard.

## Step 9. Real emails (password reset, verification)

Full walkthrough with a test button and error table: **SMTP_SETUP.md**.

No mail service yet? Set `EMAIL_VERIFICATION=admin` in `.env`: no verification email is sent and you approve students in **Admin > Users** instead. Password-reset emails still need SMTP.


Without SMTP, emails are only printed in the logs (`docker compose logs backend`). To send real ones, add to `.env`:

```ini
SMTP_HOST=smtp-relay.brevo.com      # or smtp.gmail.com with an App Password
SMTP_PORT=587
SMTP_USER=<login>
SMTP_PASSWORD=<password>
SMTP_FROM=InterviewSaathi <no-reply@yourcollege.edu>
```

Apply with `docker compose up -d`, then test "Forgot password" with your own address.

## Step 10. Launch checklist

- [ ] HTTPS works and the microphone is allowed on the real domain
- [ ] `JWT_SECRET` and `RUNNER_SECRET` are long random values, `.env` is `chmod 600`
- [ ] Demo data removed
- [ ] Only ports 22, 80, 443 are open (`ufw status`)
- [ ] You tested one full voice interview and one coding round **on the real domain**
- [ ] A backup has been taken and restored once (see below)
- [ ] You know your LLM and Gnani **rate limits** for a live class (see "Capacity")

---

## Day-2 operations

| Task | Command |
|---|---|
| Logs | `docker compose logs -f backend` (also `runner`, `caddy`) |
| Restart | `docker compose restart backend` |
| Update to a new version | upload the new files over `/opt/interviewsaathi` (keep `.env`), then `docker compose up -d --build` |
| Stop everything | `docker compose down` (data is kept in volumes) |
| Change a key | edit `.env`, then `docker compose up -d` |
| Add an admin later | `docker compose exec backend python -m scripts.make_admin someone@college.edu` |
| Clear old cached voice audio | `docker compose exec backend find /data/tts_cache -mtime +14 -delete` |

**Backup** (the database, including all interviews, lives in the `appdata` volume; run daily with cron):

```bash
docker run --rm -v interviewsaathi_appdata:/data -v /opt/backups:/backup alpine \
  tar czf /backup/appdata-$(date +%F).tgz -C /data .
```

**Restore** (stop the app first): `docker compose down`, then
`docker run --rm -v interviewsaathi_appdata:/data -v /opt/backups:/backup alpine sh -c "rm -rf /data/* && tar xzf /backup/appdata-YYYY-MM-DD.tgz -C /data"`, then `docker compose up -d`.
(The volume name is `<folder>_appdata`; check with `docker volume ls`.) Copy backups **off the server** too.

**Monitoring:** add `https://your-domain/api/meta` to a free uptime monitor (UptimeRobot, Better Stack).

## Capacity: read before a live class

I have not load-tested this. What I can say:

- **Your bottleneck will be API limits, not the server.** Free LLM tiers are shared per organisation and are measured in requests per minute (Groq's free tier is around 30 per minute, and one interview answer costs about two calls). **40 students answering at once will hit it.** For a live session use a paid LLM key, or stagger students.
- Ask Gnani about your key's **concurrency and rate limits** for streaming and TTS before a big event.
- Each active voice interview holds one WebSocket while the student speaks. The runner handles 4 judge jobs at once by default (`RUNNER_MAX_PARALLEL`); Java is the slowest. A busy coding class may queue.
- Rate limiting and the TTS cache are per process, so keep the single backend worker. SQLite is fine for one college; for thousands of users move to Postgres (set `DATABASE_URL`) and add migrations.

## Troubleshooting

| Symptom | Likely cause and fix |
|---|---|
| Browser says the connection is not secure / no padlock | The certificate wasn't issued. `docker compose logs caddy`. Usually DNS isn't pointing at the server yet, or ports 80/443 are blocked in the provider firewall |
| `backend` keeps restarting | `docker compose logs backend`. Often a weak/missing `JWT_SECRET` or a typo in `.env` |
| `docker compose up` says set RUNNER_SECRET | It must be in `.env` (min 8 chars, use 32) |
| Microphone does nothing | Not on HTTPS, mic blocked in the browser, or use Chrome/Edge. Check the padlock |
| Interviews are typing-only | `gnani_configured` is false: key missing/wrong, or the scopes weren't both enabled |
| Reports say "offline-rule-based" | No LLM key, or the model name was rejected. Check `docker compose logs backend` |
| Coding round greyed out | `coding_enabled` false: the runner isn't healthy (`docker compose logs runner`) or the secrets differ |
| Code always "timeout" on Java | First JVM start is slow on small servers. Use 4 GB RAM; raise `timeout_s` in `sandbox.py` if needed |
| Build killed / out of memory | Add swap (Step 3) or use a 4 GB server |
| Real emails never arrive | SMTP not configured or blocked; check backend logs. Many clouds block port 25, so use 587 |

## Security notes

- Only Caddy is public. The app and runner have no published ports, and the runner sits on an internal Docker network with **no internet** and a read-only filesystem.
- The runner executes student code as an unprivileged user with CPU, memory, file, process and time limits. Still, treat it as untrusted: **never** put secrets on that host path, never expose port 9000, and keep the host patched (`apt-get upgrade`, rebuild images regularly).
- Student answers and code are private unless the student opts in to share them with their group's admins. Keep `.env` and backups private; backups contain everything.
- Keys: if a key ever leaks, revoke it in the provider's console, create a new one, update `.env`, run `docker compose up -d`.

## Deploying somewhere else?

- **Render / Railway / Fly.io and similar:** fine for the web app, but they can't give the runner the same isolation (no internal-only network, no capability dropping), so run the runner on a small VPS instead, or switch coding rounds off by leaving `RUNNER_URL` empty.
- **Trying it on your laptop with the production stack:** `docker compose up --build` with `DOMAIN=localhost` serves `https://localhost` (accept the self-signed certificate warning).
- **Not tested here:** I couldn't run Docker in my build environment, so the container build and the Caddy certificate step were not exercised. If any step fails, send me the exact error from `docker compose logs`.
