"""Promote an existing account to admin:   python -m scripts.make_admin someone@college.edu
(Or set ADMIN_EMAILS in .env and register/sign in with that address.)"""
import sys
from app.db import SessionLocal, User, init_db

init_db()
if len(sys.argv) != 2:
    raise SystemExit(__doc__)
with SessionLocal() as db:
    u = db.query(User).filter(User.email == sys.argv[1].lower()).first()
    if not u:
        raise SystemExit("No account with that email. Register first, then run this again.")
    u.role = "admin"
    db.commit()
    print(f"{u.email} is now an admin.")
