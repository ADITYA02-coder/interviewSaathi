# Setting up email (SMTP) so verification links reach real inboxes

**What this enables:** when someone registers, the app emails them a link. They click it and are verified. The same setup makes "Forgot password" emails work. The admin address in `ADMIN_EMAILS` becomes admin by clicking its link.

**What you need:** an SMTP account from an email provider, and 5 settings: `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, `SMTP_FROM`. Plus two switches: `EMAIL_VERIFICATION=email` and `APP_URL` set to the address people really open.

## 0. Pick a provider (read this first)

| Provider | Cost | Works on Render **free** tier? | Notes |
|---|---|---|---|
| **Brevo** (recommended) | Free: 300 emails/day | **Yes**, use port **2525** | Needs a verified sender address; best if you have a college domain |
| **Gmail** | Free (personal account) | **No** | Quick for tests from your laptop, a VPS or a paid Render instance. Needs 2-Step Verification + an App Password |

**Why Render matters:** since 26 Sept 2025 Render's **free** web services block outgoing SMTP on ports **25, 465 and 587**. A normal Gmail setup silently times out there. Port 2525 is not on that list and Brevo accepts it. On a paid Render instance, a VPS or your laptop, any port works.

| Port | Use |
|---|---|
| 587 | Default (STARTTLS) |
| 2525 | Alternative (STARTTLS) when 587 is blocked, e.g. Render free |
| 465 | SSL; the app switches to SSL mode automatically on this port |
| 25 | Don't use (blocked almost everywhere) |

## A. Brevo (recommended)

1. Create a free account at **brevo.com** (no credit card).
2. **Verify your sender address.** *Settings > Senders, Domains & IPs > Senders > Add a sender.* Use an address you can receive mail on, e.g. `placements@yourcollege.edu` (Brevo emails you to confirm it). Sending from a `@gmail.com` address through Brevo works for demos but often lands in spam; a college-domain address is far better (and add Brevo's DKIM record for your domain when you can).
3. **Create an SMTP key.** *Settings > SMTP & API > SMTP tab.* Note the **Login** shown there (it may look like `a1b2c3001@smtp-brevo.com`; if none is shown, use your Brevo account email), then **Generate a new SMTP key** and copy it immediately (it is shown once). It is **not** the API key.
4. Put these in your settings (see section C for where):

```
EMAIL_VERIFICATION=email
APP_URL=https://your-real-address
SMTP_HOST=smtp-relay.brevo.com
SMTP_PORT=2525
SMTP_USER=<the Login from step 3>
SMTP_PASSWORD=<your SMTP key>
SMTP_FROM=InterviewSaathi <placements@yourcollege.edu>
```

`SMTP_FROM` must use the **exact address you verified** in step 2. If your laptop or server allows it, `SMTP_PORT=587` also works; use 2525 on Render free.

New Brevo accounts can be reviewed before they are allowed to send. If sending is refused, check the messages in the Brevo dashboard.

## B. Gmail (laptop, VPS or paid Render only)

1. Google Account > **Security** > turn on **2-Step Verification**.
2. Open **myaccount.google.com/apppasswords**, create an app password (name it "InterviewSaathi"). Copy the 16-character code (without spaces).
3. Settings:

```
EMAIL_VERIFICATION=email
APP_URL=https://your-real-address
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=you@gmail.com
SMTP_PASSWORD=<the 16-character app password>
SMTP_FROM=InterviewSaathi <you@gmail.com>
```

Gmail always sends as your own address, and limits how many emails you can send per day. School or work (Google Workspace) accounts may have App Passwords disabled by their administrator.

## C. Where to put the settings

| Where you run it | Put the settings in | Then |
|---|---|---|
| Your laptop | the project's `.env` | restart the backend |
| A server with Docker | `.env` next to `docker-compose.yml` | `docker compose up -d` |
| Render | your web service > **Environment** (use *Add from .env*) | save; Render redeploys |
| Vercel | **nothing**: the website never sends mail, only the API does | |

`APP_URL` must be the address in the browser (your Vercel address if the UI is there). Otherwise links in the emails point to the wrong place.

## D. Test it (do not skip)

1. Sign in as admin > **Admin > Email**. It shows whether SMTP is configured. Type your own address and click **Send test email**.
   - Success: a green "Sent" message. Check the inbox **and the spam folder**.
   - Failure: it shows the exact reason in plain language (table below).
2. Command-line alternative: `python -m scripts.test_email you@gmail.com` (Docker: `docker compose exec backend python -m scripts.test_email you@gmail.com`).
3. The real flow: register a new account with a second email address. The mail arrives; click the link; the page says "Email verified". In **Admin > Users** the student now shows a tick.

## Troubleshooting

| Message / symptom | Cause and fix |
|---|---|
| "refused the login" | Wrong `SMTP_USER` / `SMTP_PASSWORD`. Gmail: use the App Password, not your normal password. Brevo: use the SMTP key, not the API key |
| "Timed out connecting..." | The port is blocked. On Render free use Brevo with `SMTP_PORT=2525`, or a paid instance. Some networks block SMTP too |
| "Nothing is listening on host:port" | Wrong `SMTP_HOST` or `SMTP_PORT` |
| "host name could not be found" | Typo in `SMTP_HOST` |
| "rejected the sender address" | `SMTP_FROM` isn't a verified sender at your provider. Verify it and use exactly that address |
| "Secure connection problem" | Port and security mismatch: 587 / 2525 use STARTTLS, 465 uses SSL (`SMTP_SECURITY=ssl`) |
| Test succeeds but nothing arrives | Check spam. Use a verified sender on your own domain with DKIM. Check your provider's daily limit (Brevo free: 300/day) |
| Students never get a link | `EMAIL_VERIFICATION` is still `admin` (no emails by design): change it to `email` |
| Link opens the wrong site / localhost | `APP_URL` is wrong: set it to the real address |
| Link says "invalid or has expired" | Links last 48 hours (password resets 1 hour) and work once. Students can resend from **Profile** (3 per hour) |

Emails are sent in the background. A failure never breaks registration; it is written to the server log (`docker compose logs backend`, Render Logs).

## What I tested, and what I could not

- **Tested for real:** the whole path against a local mail server that speaks genuine SMTP with a login: test email headers and content, wrong password, dead port, a registration email whose link verifies the student, the admin address becoming admin through its link, and a password-reset email whose link works.
- **Not tested:** live Brevo or Gmail (I have no accounts), and Render's port rules beyond what Render documents. Use the **Send test email** button: it tells you immediately whether your provider works.
