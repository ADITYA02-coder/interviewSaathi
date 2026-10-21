"""Send one real email through your SMTP settings and print the exact problem if it fails:
    python -m scripts.test_email you@gmail.com"""
import sys
from app import mailer
from app.config import settings

if len(sys.argv) != 2:
    raise SystemExit(__doc__)
print(f"Sending via {settings.smtp_host}:{settings.smtp_port} ({mailer.security() if mailer.configured() else 'not configured'}) from {settings.smtp_from} ...")
try:
    mailer.send_blocking(sys.argv[1], "InterviewSaathi test email", f"If you can read this, SMTP works.\nVerification links will start with {settings.app_url}\n")
except mailer.MailError as e:
    raise SystemExit(f"FAILED: {e}")
print("Sent. Check the inbox (and the spam folder).")
