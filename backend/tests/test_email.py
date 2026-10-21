"""Real SMTP conversations against a local fake mail server (aiosmtpd): auth, message content, and the links inside."""
import email as emaillib
import email.policy
import re
import socket
import time

import pytest
from fastapi.testclient import TestClient

pytest.importorskip("aiosmtpd")
from aiosmtpd.controller import Controller
from aiosmtpd.smtp import AuthResult, LoginPassword

from app import mailer
from app.config import settings
from app.main import app
from app.security import purpose_token


class Sink:
    def __init__(self):
        self.messages = []

    async def handle_DATA(self, server, session, envelope):
        self.messages.append(emaillib.message_from_bytes(envelope.content, policy=emaillib.policy.default))
        return "250 OK"


def _auth(server, session, envelope, mechanism, data):
    ok = isinstance(data, LoginPassword) and data.login == b"mailuser" and data.password == b"s3cret-key"
    return AuthResult(success=ok, handled=ok)


def free_port():
    s = socket.socket(); s.bind(("127.0.0.1", 0)); p = s.getsockname()[1]; s.close(); return p


@pytest.fixture()
def smtp(monkeypatch):
    sink, port = Sink(), free_port()
    ctl = Controller(sink, hostname="127.0.0.1", port=port, authenticator=_auth, auth_required=True, auth_require_tls=False)
    ctl.start()
    for k, v in dict(smtp_host="127.0.0.1", smtp_port=port, smtp_security="none", smtp_user="mailuser", smtp_password="s3cret-key", smtp_from="InterviewSaathi <no-reply@college.edu>").items():
        monkeypatch.setattr(settings, k, v)
    yield sink
    mailer.wait_idle()          # finish any in-flight email BEFORE the settings are restored and the next test starts
    ctl.stop()


def wait_for(sink, n=1, secs=6):
    t0 = time.time()
    while len(sink.messages) < n and time.time() - t0 < secs:
        time.sleep(0.05)
    return sink.messages


def reg(c, mail, name="Someone"):
    r = c.post("/api/auth/register", json={"email": mail, "password": "password123", "name": name}); assert r.status_code == 200, r.text
    c.headers["Authorization"] = "Bearer " + r.json()["token"]
    return r.json()["user"]


_n = [0]


def make_admin(monkeypatch):
    _n[0] += 1
    mail = f"mailadmin{_n[0]}@college.edu"
    monkeypatch.setattr(settings, "admin_emails", {mail})
    c = TestClient(app)
    u = reg(c, mail, "Mail Admin")
    wait_for_noop()
    assert TestClient(app).post("/api/auth/verify", json={"token": purpose_token(u["id"], "verify", 60)}).status_code == 200
    assert c.get("/api/auth/me").json()["role"] == "admin"
    return c


def wait_for_noop():
    mailer.wait_idle()


def test_security_defaults_and_plain_language_errors(monkeypatch):
    monkeypatch.setattr(settings, "smtp_security", ""); monkeypatch.setattr(settings, "smtp_port", 465)
    assert mailer.security() == "ssl"
    monkeypatch.setattr(settings, "smtp_port", 587); assert mailer.security() == "starttls"
    monkeypatch.setattr(settings, "smtp_port", 2525); assert mailer.security() == "starttls"
    msg = mailer.explain(TimeoutError())
    assert "2525" in msg and "Render" in msg and "blocked" in msg


def test_admin_test_email_arrives_with_correct_headers_and_never_leaks_the_password(smtp, monkeypatch):
    admin = make_admin(monkeypatch)
    st = admin.get("/api/admin/email").json()
    assert st["configured"] and st["security"] == "none" and st["user"] == "mai***" and "s3cret" not in str(st)
    r = admin.post("/api/admin/email/test", json={"to": "principal@college.edu"}).json()
    assert r == {"ok": True}
    m = wait_for(smtp)[-1]
    assert m["To"] == "principal@college.edu" and m["From"] == "InterviewSaathi <no-reply@college.edu>" and "test email" in m["Subject"]
    assert settings.app_url in m.get_content()


def test_helpful_errors_for_bad_password_and_dead_port(smtp, monkeypatch):
    admin = make_admin(monkeypatch)
    monkeypatch.setattr(settings, "smtp_password", "wrong")
    bad = admin.post("/api/admin/email/test", json={"to": "a@b.co"}).json()
    assert bad["ok"] is False and "refused the login" in bad["error"] and "wrong" not in bad["error"]
    monkeypatch.setattr(settings, "smtp_password", "s3cret-key"); monkeypatch.setattr(settings, "smtp_port", free_port())
    dead = admin.post("/api/admin/email/test", json={"to": "a@b.co"}).json()
    assert dead["ok"] is False and "Nothing is listening" in dead["error"]


def test_students_cannot_use_the_email_tools(smtp):
    c = TestClient(app); reg(c, "just.a.student@college.edu")
    assert c.post("/api/admin/email/test", json={"to": "a@b.co"}).status_code == 403 and c.get("/api/admin/email").status_code == 403


def test_registration_email_contains_a_working_verification_link(smtp):
    c = TestClient(app)
    u = reg(c, "newstudent@college.edu", "New Student")
    assert u["email_verified"] is False
    m = wait_for(smtp)[-1]
    assert m["To"] == "newstudent@college.edu" and "Verify" in m["Subject"]
    link = re.search(r"(https?://\S+/#/verify/(\S+))", m.get_content())
    assert link and link.group(1).startswith(settings.app_url)
    assert TestClient(app).post("/api/auth/verify", json={"token": link.group(2)}).status_code == 200      # what the page does when the student clicks
    assert c.get("/api/auth/me").json()["email_verified"] is True


def test_admin_address_gets_a_link_that_makes_them_admin(smtp, monkeypatch):
    monkeypatch.setattr(settings, "admin_emails", {"principal@college.edu"})
    c = TestClient(app); reg(c, "principal@college.edu", "Principal")
    token = re.search(r"#/verify/(\S+)", wait_for(smtp)[-1].get_content()).group(1)
    assert c.get("/api/auth/me").json()["role"] == "student"
    TestClient(app).post("/api/auth/verify", json={"token": token})
    assert c.get("/api/auth/me").json()["role"] == "admin"


def test_password_reset_email_link_works(smtp):
    c = TestClient(app); reg(c, "forgetful@college.edu"); wait_for(smtp)
    n = len(smtp.messages)
    assert TestClient(app).post("/api/auth/forgot", json={"email": "forgetful@college.edu"}).status_code == 200
    m = wait_for(smtp, n + 1)[-1]
    assert "Reset" in m["Subject"]
    tok = re.search(r"#/reset/(\S+)", m.get_content()).group(1)
    assert TestClient(app).post("/api/auth/reset", json={"token": tok, "password": "brandnewpass1"}).status_code == 200
    assert TestClient(app).post("/api/auth/login", json={"email": "forgetful@college.edu", "password": "brandnewpass1"}).status_code == 200
