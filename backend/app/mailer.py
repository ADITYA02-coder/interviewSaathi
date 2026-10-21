"""Outgoing email over SMTP. With SMTP_HOST set it really sends; otherwise it only LOGS the message on the server console (development).
Links are never returned through the API, so a missing SMTP config can't be abused to take over accounts."""
import logging
import smtplib
import socket
import ssl
import threading
from email.message import EmailMessage
from .config import DEMO_EMAIL_DOMAIN, settings

log = logging.getLogger("interviewsaathi.mail")


class MailError(Exception):
    """A send failure with a plain-language explanation that is safe to show an admin (never contains the password)."""


def configured() -> bool:
    return bool(settings.smtp_host)


def security() -> str:
    """starttls (port 587/2525), ssl (port 465) or none (local debug servers only)."""
    s = (settings.smtp_security or "").lower()
    if s in ("starttls", "ssl", "none"):
        return s
    return "ssl" if settings.smtp_port == 465 else "starttls"


def explain(e: Exception) -> str:
    host, port = settings.smtp_host, settings.smtp_port
    if isinstance(e, smtplib.SMTPAuthenticationError):
        return "The mail server refused the login. Check SMTP_USER and SMTP_PASSWORD. For Gmail use an App Password (not your normal password); for Brevo use the SMTP key (not the API key)."
    if isinstance(e, (smtplib.SMTPSenderRefused,)):
        return f"The mail server rejected the sender address ({settings.smtp_from}). Verify that address in your provider's dashboard and use exactly it in SMTP_FROM."
    if isinstance(e, smtplib.SMTPRecipientsRefused):
        return "The mail server rejected the recipient address."
    if isinstance(e, (socket.timeout, TimeoutError)):
        return (f"Timed out connecting to {host}:{port}. The port is probably blocked. Render's free tier blocks SMTP ports 25, 465 and 587: use a provider that offers port 2525 "
                "(Brevo does) or a paid instance. Some networks and cloud hosts block outbound SMTP too.")
    if isinstance(e, socket.gaierror):
        return f"The host name '{host}' could not be found. Check SMTP_HOST for typos."
    if isinstance(e, ConnectionRefusedError):
        return f"Nothing is listening on {host}:{port}. Check SMTP_HOST and SMTP_PORT."
    if isinstance(e, ssl.SSLError) or isinstance(e, smtplib.SMTPNotSupportedError):
        return f"Secure connection problem with {host}:{port}. Try SMTP_PORT=587 (STARTTLS) or SMTP_PORT=465 with SMTP_SECURITY=ssl."
    if isinstance(e, smtplib.SMTPServerDisconnected):
        return f"{host}:{port} closed the connection. The port/security setting may not match (587 and 2525 use STARTTLS, 465 uses SSL)."
    if isinstance(e, OSError):
        return f"Could not connect to {host}:{port} ({e.__class__.__name__}). The port may be blocked on this host."
    return f"{e.__class__.__name__}: {e}"[:300]


def _smtp_send(msg: EmailMessage):
    mode, ctx = security(), ssl.create_default_context()
    if mode == "ssl":
        server = smtplib.SMTP_SSL(settings.smtp_host, settings.smtp_port, timeout=15, context=ctx)
    else:
        server = smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=15)
    with server as s:
        s.ehlo()
        if mode == "starttls":
            s.starttls(context=ctx)
            s.ehlo()
        if settings.smtp_user:
            s.login(settings.smtp_user, settings.smtp_password)
        s.send_message(msg)


def _build(to: str, subject: str, body: str) -> EmailMessage:
    msg = EmailMessage()
    msg["From"], msg["To"], msg["Subject"] = settings.smtp_from, to, subject
    msg.set_content(body)
    return msg


def send_blocking(to: str, subject: str, body: str):
    """Send now and raise MailError with a readable reason. Used by the admin 'Send test email' button and scripts/test_email.py."""
    if not configured():
        raise MailError("SMTP isn't configured. Set SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD and SMTP_FROM.")
    try:
        _smtp_send(_build(to, subject, body))
    except Exception as e:
        raise MailError(explain(e)) from e


def _send_bg(msg: EmailMessage):
    try:
        _smtp_send(msg)
        log.info("Email sent to %s", msg["To"])
    except Exception as e:  # never break a request because mail failed
        log.error("Could not send email to %s: %s", msg["To"], explain(e))


_threads: list = []


def wait_idle(timeout: float = 10.0):
    """Block until every queued email has been handed to the SMTP server (used by tests and clean shutdown)."""
    for t in list(_threads):
        t.join(timeout)
    _threads[:] = [t for t in _threads if t.is_alive()]


def send(to: str, subject: str, body: str):
    if to.lower().endswith("@" + DEMO_EMAIL_DOMAIN):  # seeded demo accounts are not real mailboxes
        log.info("Skipped email to demo account %s", to)
        return
    if not configured():
        log.warning("EMAIL NOT SENT (no SMTP configured). To: %s | Subject: %s\n%s", to, subject, body)
        print(f"\n--- DEV EMAIL to {to} ---\n{subject}\n{body}\n--- end ---\n", flush=True)
        return
    t = threading.Thread(target=_send_bg, args=(_build(to, subject, body),), daemon=True)
    _threads[:] = [x for x in _threads if x.is_alive()] + [t]
    t.start()
