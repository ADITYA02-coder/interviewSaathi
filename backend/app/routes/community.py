import secrets
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import or_, select
from ..db import Cohort, Membership, SessionLocal, Support, Template, User
from ..security import current_user, rate_limit

router = APIRouter(prefix="/api", tags=["community"])


class JoinIn(BaseModel):
    code: str = Field(min_length=4, max_length=12)


class ShareIn(BaseModel):
    share_transcripts: bool


class SupportIn(BaseModel):
    subject: str = Field(min_length=3, max_length=200)
    message: str = Field(min_length=5, max_length=4000)


@router.post("/cohorts/join")
def join(body: JoinIn, user: User = Depends(current_user)):
    if user.is_guest:
        raise HTTPException(409, "Create a free account first, so your results can be linked to you.")
    rate_limit(user.id, "join", 8, 600)
    with SessionLocal() as db:
        c = db.scalar(select(Cohort).where(Cohort.code == body.code.strip().upper()))
        if not c:
            raise HTTPException(404, "That code doesn't match any group.")
        if not db.scalar(select(Membership).where(Membership.user_id == user.id, Membership.cohort_id == c.id)):
            db.add(Membership(user_id=user.id, cohort_id=c.id))
            db.commit()
        return {"id": c.id, "name": c.name}


@router.delete("/cohorts/{cohort_id}/leave")
def leave(cohort_id: int, user: User = Depends(current_user)):
    with SessionLocal() as db:
        m = db.scalar(select(Membership).where(Membership.user_id == user.id, Membership.cohort_id == cohort_id))
        if m:
            db.delete(m)
            db.commit()
    return {"left": True}


@router.put("/cohorts/{cohort_id}/sharing")
def sharing(cohort_id: int, body: ShareIn, user: User = Depends(current_user)):
    with SessionLocal() as db:
        m = db.scalar(select(Membership).where(Membership.user_id == user.id, Membership.cohort_id == cohort_id))
        if not m:
            raise HTTPException(404, "You're not in that group.")
        m.share_transcripts = body.share_transcripts
        db.commit()
    return {"share_transcripts": body.share_transcripts}


@router.get("/templates")
def my_templates(user: User = Depends(current_user)):
    """Interviews your placement team assigned to your group(s) (or to everyone)."""
    with SessionLocal() as db:
        mine = [cid for (cid,) in db.query(Membership.cohort_id).filter(Membership.user_id == user.id).all()]
        rows = db.scalars(select(Template).where(or_(Template.cohort_id.is_(None), Template.cohort_id.in_(mine or [-1]))).order_by(Template.id.desc())).all()
        names = {c.id: c.name for c in db.scalars(select(Cohort)).all()}
        return [{"id": t.id, "name": t.name, "config": t.config, "focus_note": t.focus_note, "group": names.get(t.cohort_id)} for t in rows]


@router.post("/support")
def new_support(body: SupportIn, user: User = Depends(current_user)):
    rate_limit(user.id, "support", 5, 3600)
    with SessionLocal() as db:
        db.add(Support(user_id=user.id, subject=body.subject.strip(), message=body.message.strip()))
        db.commit()
    return {"sent": True}


@router.get("/support")
def my_support(user: User = Depends(current_user)):
    with SessionLocal() as db:
        rows = db.scalars(select(Support).where(Support.user_id == user.id).order_by(Support.id.desc()).limit(20)).all()
        return [{"id": s.id, "subject": s.subject, "status": s.status, "admin_note": s.admin_note, "created_at": s.created_at.isoformat()} for s in rows]
