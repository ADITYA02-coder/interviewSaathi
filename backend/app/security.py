import time
import bcrypt
import jwt
from fastapi import Depends, Header, HTTPException
from .config import settings
from .db import SessionLocal, User


def hash_password(pw: str) -> str:
    return bcrypt.hashpw(pw.encode()[:72], bcrypt.gensalt()).decode()


def verify_password(pw: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(pw.encode()[:72], hashed.encode())
    except ValueError:
        return False


def make_token(user_id: int) -> str:
    return jwt.encode({"sub": str(user_id), "exp": int(time.time()) + 14 * 86400}, settings.jwt_secret, algorithm="HS256")


def purpose_token(user_id: int, purpose: str, minutes: int, fingerprint: str = "") -> str:
    return jwt.encode({"sub": str(user_id), "purpose": purpose, "fp": fingerprint, "exp": int(time.time()) + minutes * 60}, settings.jwt_secret, algorithm="HS256")


def read_purpose_token(token: str, purpose: str) -> dict:
    try:
        data = jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])
    except jwt.PyJWTError:
        raise HTTPException(400, "This link is invalid or has expired.")
    if data.get("purpose") != purpose:
        raise HTTPException(400, "This link is invalid or has expired.")
    return data


def current_user(authorization: str = Header(default="")) -> User:
    if not authorization.lower().startswith("bearer "):
        raise HTTPException(401, "Not signed in")
    try:
        data = jwt.decode(authorization[7:], settings.jwt_secret, algorithms=["HS256"])
        if data.get("purpose"):
            raise jwt.PyJWTError()
    except jwt.PyJWTError:
        raise HTTPException(401, "Session expired. Please sign in again.")
    with SessionLocal() as db:
        user = db.get(User, int(data["sub"]))
    if not user:
        raise HTTPException(401, "Account not found")
    return user


_hits: dict = {}


def rate_limit(user_id: int, key: str, limit: int, window: float):
    """Tiny in-memory limiter (per process). Use Redis or a gateway if you run several workers."""
    import collections
    from fastapi import HTTPException
    now = time.time()
    q = _hits.setdefault((user_id, key), collections.deque())
    while q and now - q[0] > window:
        q.popleft()
    if len(q) >= limit:
        raise HTTPException(429, f"Slow down a little: you can do this {limit} times every {int(window)} seconds.")
    q.append(now)


def admin_user(user=Depends(current_user)):
    if user.role != "admin":
        raise HTTPException(403, "Admins only")
    return user
