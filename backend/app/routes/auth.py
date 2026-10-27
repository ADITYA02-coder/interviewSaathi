import jwt as pyjwt
import hmac
from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import select
from ..config import settings
from .. import mailer
from ..db import Cohort, Membership, SessionLocal, User
from ..security import current_user, hash_password, make_token, purpose_token, rate_limit, read_purpose_token, verify_password

router = APIRouter(prefix="/api/auth", tags=["auth"])


def _cohorts(uid: int) -> list:
    with SessionLocal() as db:
        rows = db.query(Membership, Cohort).join(Cohort, Cohort.id == Membership.cohort_id).filter(Membership.user_id == uid).all()
        return [{"id": c.id, "name": c.name, "share_transcripts": m.share_transcripts} for m, c in rows]


def _promote_if_admin(db, u: User):
    """Grant admin access to accounts whose address is configured in ADMIN_EMAILS."""
    if u.email and u.email.lower() in settings.admin_emails and u.role != "admin":
        u.role = "admin"


def _admin_password_matches(email: str, password: str) -> bool:
    return not settings.admin_password or (
        email.lower() in settings.admin_emails
        and hmac.compare_digest(password, settings.admin_password)
    )


def user_out(u: User) -> dict:
    return {"role": u.role, "email_verified": u.email_verified, "cohorts": _cohorts(u.id), "id": u.id, "name": u.name, "email": u.email, "is_guest": u.is_guest, "education": u.education, "skills": u.skills,
            "target_role": u.target_role, "preferred_language": u.preferred_language, "target_companies": u.target_companies}


class RegisterIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    name: str = Field(min_length=1, max_length=120)


class LoginIn(BaseModel):
    email: EmailStr
    password: str


class ProfileIn(BaseModel):
    name: str | None = Field(default=None, max_length=120)
    education: str | None = Field(default=None, max_length=255)
    skills: str | None = Field(default=None, max_length=2000)
    target_role: str | None = Field(default=None, max_length=120)
    preferred_language: str | None = Field(default=None, max_length=16)
    target_companies: str | None = Field(default=None, max_length=2000)


def _guest_id(authorization: str) -> int | None:
    if not authorization.lower().startswith("bearer "):
        return None
    try:
        uid = int(pyjwt.decode(authorization[7:], settings.jwt_secret, algorithms=["HS256"])["sub"])
    except Exception:
        return None
    with SessionLocal() as db:
        u = db.get(User, uid)
        return u.id if u and u.is_guest else None


@router.post("/register")
def register(body: RegisterIn, authorization: str = Header(default="")):
    email = body.email.lower()
    if email in settings.admin_emails and not _admin_password_matches(email, body.password):
        raise HTTPException(403, "Use the configured administrator password for this email.")
    with SessionLocal() as db:
        if db.scalar(select(User).where(User.email == email)):
            raise HTTPException(409, "An account with this email already exists. Try signing in.")
        gid = _guest_id(authorization)
        user = db.get(User, gid) if gid else None  # upgrading a guest keeps their interview history
        if user:
            user.email, user.name, user.password_hash, user.is_guest = email, body.name.strip(), hash_password(body.password), False
        else:
            user = User(email=email, name=body.name.strip(), password_hash=hash_password(body.password))
            db.add(user)
        user.email_verified = True
        _promote_if_admin(db, user)
        db.commit()
        return {"token": make_token(user.id), "user": user_out(user)}


@router.post("/login")
def login(body: LoginIn):
    admin_login = body.email.lower() in settings.admin_emails and settings.admin_password and _admin_password_matches(body.email, body.password)
    if body.email.lower() in settings.admin_emails and not _admin_password_matches(body.email, body.password):
        raise HTTPException(401, "Email or password is incorrect.")
    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.email == body.email.lower()))
        if not user or not user.password_hash or (not admin_login and not verify_password(body.password, user.password_hash)):
            raise HTTPException(401, "Email or password is incorrect.")
        if admin_login and not verify_password(body.password, user.password_hash):
            user.password_hash = hash_password(body.password)
        _promote_if_admin(db, user)
        db.commit()
        return {"token": make_token(user.id), "user": user_out(user)}


@router.post("/guest")
def guest():
    with SessionLocal() as db:
        user = User(name="Guest", is_guest=True)
        db.add(user)
        db.commit()
        return {"token": make_token(user.id), "user": user_out(user)}


@router.get("/me")
def me(user: User = Depends(current_user)):
    return user_out(user)


@router.put("/me")
def update_me(body: ProfileIn, user: User = Depends(current_user)):
    with SessionLocal() as db:
        u = db.get(User, user.id)
        for k, v in body.model_dump(exclude_none=True).items():
            setattr(u, k, v.strip())
        db.commit()
        return user_out(u)


# ---------------------------------------------------------------- email verification and password reset
class EmailIn(BaseModel):
    email: EmailStr


class ResetIn(BaseModel):
    token: str
    password: str = Field(min_length=8, max_length=128)


class TokenIn(BaseModel):
    token: str


def _send_verification(user: User):
    if not user.email or user.email_verified:
        return
    if settings.verification_mode == "admin" and user.email.lower() not in settings.admin_emails:
        return  # students are approved by an admin; only the ADMIN_EMAILS address gets a link, so the very first admin can bootstrap
    link = f"{settings.app_url}/#/verify/{purpose_token(user.id, 'verify', 60 * 48)}"
    mailer.send(user.email, "Verify your InterviewSaathi email", f"Hi {user.name},\n\nConfirm your email address by opening this link (valid for 48 hours):\n{link}\n")


@router.post("/verify/send")
def resend_verification(user: User = Depends(current_user)):
    if settings.verification_mode == "admin":
        raise HTTPException(409, "Your placement admin verifies accounts, so no email is sent. Ask them to mark you as verified.")
    rate_limit(user.id, "verify", 3, 3600)
    if user.is_guest or not user.email:
        raise HTTPException(409, "Create an account first.")
    _send_verification(user)
    return {"sent": True}


@router.post("/verify")
def verify_email(body: TokenIn):
    data = read_purpose_token(body.token, "verify")
    with SessionLocal() as db:
        u = db.get(User, int(data["sub"]))
        if not u:
            raise HTTPException(400, "This link is invalid or has expired.")
        u.email_verified = True
        _promote_if_admin(db, u)
        db.commit()
    return {"verified": True}


@router.post("/forgot")
def forgot_password(body: EmailIn):
    """Always answers the same way so it can't be used to discover which emails have accounts."""
    with SessionLocal() as db:
        u = db.scalar(select(User).where(User.email == body.email.lower()))
        if u and u.password_hash:
            rate_limit(u.id, "forgot", 3, 3600)
            link = f"{settings.app_url}/#/reset/{purpose_token(u.id, 'reset', 60, u.password_hash[-12:])}"
            mailer.send(u.email, "Reset your InterviewSaathi password", f"Hi {u.name},\n\nSomeone asked to reset your password. If it was you, open this link within an hour:\n{link}\n\nIf it wasn't you, ignore this email.\n")
    return {"sent": True}


@router.post("/reset")
def reset_password(body: ResetIn):
    data = read_purpose_token(body.token, "reset")
    with SessionLocal() as db:
        u = db.get(User, int(data["sub"]))
        if not u or not u.password_hash or u.password_hash[-12:] != data.get("fp"):  # a used link stops working because the hash changed
            raise HTTPException(400, "This link is invalid or has expired.")
        u.password_hash = hash_password(body.password)
        db.commit()
        return {"token": make_token(u.id), "user": user_out(u)}
