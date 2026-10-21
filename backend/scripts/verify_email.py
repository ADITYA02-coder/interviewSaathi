"""Mark an account's email as verified (and apply ADMIN_EMAILS promotion):   python -m scripts.verify_email you@college.edu
Use it when SMTP isn't configured and you don't want to copy the link from the server log."""
import sys
from app.config import settings
from app.db import SessionLocal, User, init_db

init_db()
if len(sys.argv) != 2:
    raise SystemExit(__doc__)
with SessionLocal() as db:
    u = db.query(User).filter(User.email == sys.argv[1].lower()).first()
    if not u:
        raise SystemExit("No account with that email. Register first.")
    u.email_verified = True
    if u.email.lower() in settings.admin_emails:
        u.role = "admin"
    db.commit()
    print(f"{u.email} is verified" + (" and is now an admin." if u.role == "admin" else "."))
