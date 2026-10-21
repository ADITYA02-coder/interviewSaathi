"""Admin tools. PRIVACY MODEL: admins see scores, trends and report summaries only for students who joined one of their cohorts with its
code (that is the student's consent). Answer transcripts and submitted code are visible only if that student also switched on
'share transcripts'. Admins cannot browse arbitrary users' interviews."""
import csv
import io
import secrets
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel, Field
from sqlalchemy import func, select
import asyncio
from .. import mailer, questionbank as qb, sandbox
from ..config import settings
from ..db import Cohort, Interview, Membership, Problem, Question, SessionLocal, Submission, Support, Template, Turn, User
from ..security import admin_user

router = APIRouter(prefix="/api/admin", tags=["admin"], dependencies=[Depends(admin_user)])
ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"


# ======================================================================== overview
@router.get("/stats")
def stats():
    with SessionLocal() as db:
        now = datetime.utcnow()
        users = db.scalars(select(User)).all()
        students = [u for u in users if u.role == "student" and not u.is_guest]
        its = db.scalars(select(Interview)).all()
        done = [i for i in its if i.status == "completed" and i.report and i.report.get("answered", 0) > 0]
        week = {i.user_id for i in its if i.started_at > now - timedelta(days=7)}
        days = Counter(i.started_at.date().isoformat() for i in its if i.started_at > now - timedelta(days=30))
        series = [{"date": (now - timedelta(days=d)).date().isoformat(), "count": days.get((now - timedelta(days=d)).date().isoformat(), 0)} for d in range(29, -1, -1)]
        sources = Counter(s for (s,) in db.query(Turn.source).filter(Turn.role == "candidate", Turn.source != "").all())
        subs = db.query(Submission).filter(Submission.kind == "submit").all()
        return {
            "students": len(students), "guests": sum(1 for u in users if u.is_guest), "interviews": len(its), "completed": len(done),
            "average_score": round(sum(i.report["overall"] for i in done) / len(done)) if done else None, "active_7d": len(week),
            "answers_by_voice": sources.get("voice", 0), "answers_by_text": sources.get("text", 0),
            "languages": Counter(i.config.get("language", "en-IN") for i in its), "types": Counter(i.config.get("interview_type", "technical") for i in its),
            "per_day": series, "code_submissions": len(subs), "code_accept_rate": round(100 * sum(1 for s in subs if s.status == "accepted") / len(subs)) if subs else None,
            "open_support": db.query(Support).filter(Support.status == "open").count(), "cohorts": db.query(Cohort).count(),
            "unverified": 0,
        }


# ======================================================================== cohorts
class CohortIn(BaseModel):
    name: str = Field(min_length=2, max_length=120)


@router.get("/cohorts")
def cohorts():
    with SessionLocal() as db:
        counts = dict(db.query(Membership.cohort_id, func.count(Membership.id)).group_by(Membership.cohort_id).all())
        return [{"id": c.id, "name": c.name, "code": c.code, "members": counts.get(c.id, 0), "created_at": c.created_at.isoformat()} for c in db.scalars(select(Cohort).order_by(Cohort.id.desc())).all()]


@router.post("/cohorts")
def new_cohort(body: CohortIn, admin: User = Depends(admin_user)):
    with SessionLocal() as db:
        for _ in range(20):
            code = "".join(secrets.choice(ALPHABET) for _ in range(6))
            if not db.scalar(select(Cohort).where(Cohort.code == code)):
                break
        c = Cohort(name=body.name.strip(), code=code, created_by=admin.id)
        db.add(c)
        db.commit()
        return {"id": c.id, "name": c.name, "code": c.code, "members": 0}


@router.delete("/cohorts/{cid}")
def del_cohort(cid: int):
    with SessionLocal() as db:
        c = db.get(Cohort, cid)
        if not c:
            raise HTTPException(404, "Not found")
        db.query(Membership).filter(Membership.cohort_id == cid).delete()
        db.query(Template).filter(Template.cohort_id == cid).delete()
        db.delete(c)
        db.commit()
    return {"deleted": True}


# ======================================================================== leaderboard and students
def _member_ids(db, cohort_id: int | None) -> dict[int, list[int]]:
    q = db.query(Membership.user_id, Membership.cohort_id)
    if cohort_id:
        q = q.filter(Membership.cohort_id == cohort_id)
    out = defaultdict(list)
    for uid, cid in q.all():
        out[uid].append(cid)
    return out


def _board(cohort_id: int | None, interview_type: str | None):
    with SessionLocal() as db:
        members = _member_ids(db, cohort_id)
        if not members:
            return []
        users = {u.id: u for u in db.scalars(select(User).where(User.id.in_(members.keys()))).all()}
        cohort_names = {c.id: c.name for c in db.scalars(select(Cohort)).all()}
        its = db.scalars(select(Interview).where(Interview.user_id.in_(members.keys()), Interview.status == "completed").order_by(Interview.started_at)).all()
        solved = defaultdict(set)
        for uid, pid in db.query(Submission.user_id, Submission.problem_id).filter(Submission.status == "accepted", Submission.kind == "submit").all():
            solved[uid].add(pid)
        by_user = defaultdict(list)
        for i in its:
            if i.report and i.report.get("answered", 0) > 0 and (not interview_type or i.config.get("interview_type") == interview_type):
                by_user[i.user_id].append(i)
        rows, now = [], datetime.utcnow()
        for uid, u in users.items():
            ss = by_user.get(uid, [])
            scores = [s.report["overall"] for s in ss]
            topics = defaultdict(list)
            for s in ss:
                for t in s.report.get("topics", []):
                    topics[t["topic"]].append(t["score"])
            weak = sorted(((sum(v) / len(v), k) for k, v in topics.items()))[:1]
            last = max((s.started_at for s in ss), default=None)
            avg = round(sum(scores) / len(scores)) if scores else None
            rows.append({"id": uid, "name": u.name, "email": u.email, "cohorts": [cohort_names.get(c) for c in members[uid]], "interviews": len(ss), "average": avg,
                         "latest": scores[-1] if scores else None, "best": max(scores) if scores else None, "improvement": (scores[-1] - scores[0]) if len(scores) >= 2 else None,
                         "problems_solved": len(solved.get(uid, ())), "weakest_topic": weak[0][1] if weak and weak[0][0] < 70 else None,
                         "last_active": last.isoformat() if last else None,
                         "needs_attention": bool(scores and avg < 50) or (last is not None and last < now - timedelta(days=14)) or (not ss)})
        return rows


@router.get("/leaderboard")
def leaderboard(cohort_id: int | None = None, interview_type: str | None = None, sort: str = "average"):
    rows = _board(cohort_id, interview_type)
    key = sort if sort in ("average", "latest", "best", "improvement", "interviews", "problems_solved") else "average"
    rows.sort(key=lambda r: (r[key] is None, -(r[key] or 0), r["name"].lower()))
    rank = 0
    for r in rows:
        if r["average"] is not None:
            rank += 1
            r["rank"] = rank
        else:
            r["rank"] = None
    return rows


@router.get("/leaderboard.csv")
def leaderboard_csv(cohort_id: int | None = None, interview_type: str | None = None):
    rows = leaderboard(cohort_id, interview_type, "average")
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["rank", "name", "email", "groups", "interviews", "average", "latest", "best", "improvement", "problems_solved", "weakest_topic", "last_active"])
    for r in rows:
        w.writerow([r["rank"], r["name"], r["email"], "; ".join(filter(None, r["cohorts"])), r["interviews"], r["average"], r["latest"], r["best"], r["improvement"], r["problems_solved"], r["weakest_topic"], r["last_active"]])
    return Response(buf.getvalue(), media_type="text/csv", headers={"Content-Disposition": "attachment; filename=leaderboard.csv"})


def _consent(db, uid: int) -> tuple[bool, bool]:
    ms = db.query(Membership).filter(Membership.user_id == uid).all()
    return bool(ms), any(m.share_transcripts for m in ms)


@router.get("/students/{uid}")
def student(uid: int):
    with SessionLocal() as db:
        member, transcripts = _consent(db, uid)
        u = db.get(User, uid)
        if not u or not member:
            raise HTTPException(404, "Student not found, or they haven't joined one of your groups.")
        its = db.scalars(select(Interview).where(Interview.user_id == uid, Interview.status == "completed").order_by(Interview.started_at)).all()
        done = [i for i in its if i.report and i.report.get("answered", 0) > 0]
        topics, dims = defaultdict(list), defaultdict(list)
        for i in done:
            for t in i.report.get("topics", []):
                topics[t["topic"]].append(t["score"])
            for k, v in i.report.get("dimensions", {}).items():
                dims[k].append(v)
        rows = sorted(({"topic": k, "score": round(sum(v) / len(v)), "count": len(v)} for k, v in topics.items()), key=lambda x: x["score"])
        subs = db.query(Submission).filter(Submission.user_id == uid, Submission.kind == "submit").all()
        return {
            "id": u.id, "name": u.name, "email": u.email, "education": u.education, "skills": u.skills, "target_role": u.target_role, "target_companies": u.target_companies,
            "transcripts_shared": transcripts, "joined": u.created_at.isoformat(),
            "sessions": [{"id": i.id, "date": i.started_at.isoformat(), "type": i.config.get("interview_type"), "role": i.config.get("role"), "language": i.config.get("language"),
                          "overall": i.report["overall"], "answered": i.report["answered"], "dimensions": i.report.get("dimensions")} for i in done],
            "weakest": [t for t in rows if t["score"] < 70][:5], "strongest": [t for t in reversed(rows) if t["score"] >= 70][:5],
            "dimension_average": {k: round(sum(v) / len(v)) for k, v in dims.items()},
            "code": {"submissions": len(subs), "accepted": sum(1 for s in subs if s.status == "accepted"), "problems_solved": len({s.problem_id for s in subs if s.status == "accepted"})},
        }


@router.get("/students/{uid}/interviews/{iid}")
def student_interview(uid: int, iid: str):
    with SessionLocal() as db:
        member, transcripts = _consent(db, uid)
        it = db.get(Interview, iid)
        if not member or not it or it.user_id != uid:
            raise HTTPException(404, "Not found")
        report = dict(it.report or {})
        if not transcripts and report.get("problems"):  # submitted code is the student's work: only with transcript consent
            report["problems"] = [{k: v for k, v in p.items() if k != "code"} for p in report["problems"]]
        out = {"id": it.id, "config": it.config, "report": report, "transcripts_shared": transcripts}
        if transcripts:
            out["turns"] = [{"role": t.role, "text": t.text, "evaluation": t.evaluation} for t in it.turns]
        return out


# ======================================================================== question bank
class QuestionIn(BaseModel):
    bank_key: str
    topic: str = Field(max_length=80, default="General")
    level: int = Field(ge=1, le=3, default=2)
    text: str = Field(min_length=8, max_length=1500)
    concepts: list[list] = Field(default_factory=list, max_length=12)  # [[label, [synonyms]]]
    followup: str = Field(default="", max_length=1500)
    model_answer: str = Field(default="", max_length=3000)
    active: bool = True


def _clean_concepts(cs):
    out = []
    for c in cs:
        if len(c) != 2 or not isinstance(c[0], str) or not isinstance(c[1], list):
            raise HTTPException(422, "Each concept must be [label, [synonym, ...]]")
        out.append([c[0][:120], [str(x)[:60] for x in c[1]][:12]])
    return out


def _q_out(q: Question) -> dict:
    return {"id": q.id, "bank_key": q.bank_key, "topic": q.topic, "level": q.level, "text": q.text, "concepts": q.concepts, "followup": q.followup, "model_answer": q.model_answer, "active": q.active, "source": q.source}


@router.get("/questions")
def questions(bank_key: str | None = None, q: str | None = None):
    with SessionLocal() as db:
        stmt = select(Question).order_by(Question.bank_key, Question.level, Question.id)
        if bank_key:
            stmt = stmt.where(Question.bank_key == bank_key)
        rows = [r for r in db.scalars(stmt).all() if not q or q.lower() in r.text.lower() or q.lower() in r.topic.lower()]
        return {"keys": qb.BANK_KEYS, "questions": [_q_out(r) for r in rows]}


@router.post("/questions")
def add_question(body: QuestionIn):
    if body.bank_key not in qb.BANK_KEYS:
        raise HTTPException(422, "Unknown question bank")
    with SessionLocal() as db:
        r = Question(bank_key=body.bank_key, topic=body.topic, level=body.level, text=body.text.strip(), concepts=_clean_concepts(body.concepts), followup=body.followup, model_answer=body.model_answer, active=body.active, source="custom")
        db.add(r)
        db.commit()
        qb.invalidate()
        return _q_out(r)


@router.put("/questions/{qid}")
def edit_question(qid: int, body: QuestionIn):
    with SessionLocal() as db:
        r = db.get(Question, qid)
        if not r:
            raise HTTPException(404, "Not found")
        r.bank_key, r.topic, r.level, r.text, r.followup, r.model_answer, r.active = body.bank_key, body.topic, body.level, body.text.strip(), body.followup, body.model_answer, body.active
        r.concepts = _clean_concepts(body.concepts)
        db.commit()
        qb.invalidate()
        return _q_out(r)


@router.delete("/questions/{qid}")
def del_question(qid: int):
    with SessionLocal() as db:
        r = db.get(Question, qid)
        if not r:
            raise HTTPException(404, "Not found")
        if r.source == "builtin":  # built-ins are disabled, not deleted, so old reports keep their reference
            r.active = False
        else:
            db.delete(r)
        db.commit()
        qb.invalidate()
    return {"ok": True}


# ======================================================================== coding problems
class TestIn(BaseModel):
    input: str = Field(max_length=100_000)
    expected: str = Field(max_length=20_000)
    hidden: bool = True


class ProblemIn(BaseModel):
    id: str = Field(pattern=r"^[a-z0-9][a-z0-9-]{1,46}$")
    title: str = Field(min_length=3, max_length=160)
    difficulty: str = Field(pattern="^(easy|medium|hard)$")
    topic: str = Field(max_length=80, default="General")
    statement: str = Field(min_length=10, max_length=6000)
    input_format: str = Field(default="", max_length=1500)
    output_format: str = Field(default="", max_length=1500)
    summary: str = Field(default="", max_length=400)
    expected_time: str = Field(default="", max_length=40)
    expected_space: str = Field(default="", max_length=40)
    approach_keywords: list[list] = Field(default_factory=list, max_length=10)
    tests: list[TestIn] = Field(min_length=2, max_length=40)
    active: bool = True


def _p_out(p: Problem, full=True) -> dict:
    d = {"id": p.id, "title": p.title, "difficulty": p.difficulty, "topic": p.topic, "active": p.active, "source": p.source, "tests": len(p.tests)}
    if full:
        d.update(statement=p.statement, input_format=p.input_format, output_format=p.output_format, summary=p.summary, expected_time=p.expected_time, expected_space=p.expected_space,
                 approach_keywords=p.approach_keywords, tests=p.tests)
    return d


@router.get("/problems")
def problems():
    with SessionLocal() as db:
        return [_p_out(p, False) for p in db.scalars(select(Problem).order_by(Problem.difficulty, Problem.title)).all()]


@router.get("/problems/{pid}")
def problem(pid: str):
    with SessionLocal() as db:
        p = db.get(Problem, pid)
        if not p:
            raise HTTPException(404, "Not found")
        return _p_out(p)


def _apply(p: Problem, b: ProblemIn):
    tests = [t.model_dump() for t in b.tests]
    for t in tests:
        t["input"] = t["input"].replace("\r\n", "\n")
        if not t["input"].endswith("\n"):
            t["input"] += "\n"
    p.title, p.difficulty, p.topic, p.statement, p.input_format, p.output_format, p.summary = b.title, b.difficulty, b.topic, b.statement, b.input_format, b.output_format, b.summary or b.title
    p.expected_time, p.expected_space, p.active, p.tests = b.expected_time, b.expected_space, b.active, tests
    p.approach_keywords = _clean_concepts(b.approach_keywords)
    p.examples = [{"input": t["input"].strip(), "output": t["expected"]} for t in tests if not t["hidden"]][:3] or [{"input": tests[0]["input"].strip(), "output": tests[0]["expected"]}]


@router.post("/problems")
def add_problem(body: ProblemIn):
    with SessionLocal() as db:
        if db.get(Problem, body.id):
            raise HTTPException(409, "A problem with this id already exists.")
        p = Problem(id=body.id, source="custom")
        _apply(p, body)
        db.add(p)
        db.commit()
        return _p_out(p)


@router.put("/problems/{pid}")
def edit_problem(pid: str, body: ProblemIn):
    if body.id != pid:
        raise HTTPException(422, "The id can't be changed.")
    with SessionLocal() as db:
        p = db.get(Problem, pid)
        if not p:
            raise HTTPException(404, "Not found")
        _apply(p, body)
        db.commit()
        return _p_out(p)


@router.delete("/problems/{pid}")
def del_problem(pid: str):
    with SessionLocal() as db:
        p = db.get(Problem, pid)
        if not p:
            raise HTTPException(404, "Not found")
        if p.source == "builtin" or db.query(Submission).filter(Submission.problem_id == pid).count():
            p.active = False  # keep history intact
        else:
            db.delete(p)
        db.commit()
    return {"ok": True}


class ValidateIn(BaseModel):
    language: str = "python"
    code: str = Field(min_length=1, max_length=50_000)


@router.post("/problems/{pid}/validate")
async def validate_problem(pid: str, body: ValidateIn):
    """Run YOUR reference solution against ALL of the problem's tests to prove the expected outputs are right."""
    with SessionLocal() as db:
        p = db.get(Problem, pid)
        if not p:
            raise HTTPException(404, "Not found")
    try:
        res = await sandbox.run_problem(p, body.language, body.code, False)
    except sandbox.RunnerUnavailable as e:
        raise HTTPException(503, str(e))
    for t in res["tests"]:  # admins may see everything: re-attach inputs for the failures
        if t["hidden"] and t["status"] != "pass":
            src = p.tests[t["i"] - 1]
            t.update(input=src["input"][:600], expected=src["expected"][:600])
    return res


# ======================================================================== templates, support, users
class TemplateIn(BaseModel):
    name: str = Field(min_length=3, max_length=160)
    cohort_id: int | None = None
    config: dict
    focus_note: str = Field(default="", max_length=600)


@router.get("/templates")
def templates():
    with SessionLocal() as db:
        names = {c.id: c.name for c in db.scalars(select(Cohort)).all()}
        return [{"id": t.id, "name": t.name, "cohort_id": t.cohort_id, "group": names.get(t.cohort_id, "Everyone"), "config": t.config, "focus_note": t.focus_note} for t in db.scalars(select(Template).order_by(Template.id.desc())).all()]


@router.post("/templates")
def add_template(body: TemplateIn, admin: User = Depends(admin_user)):
    allowed = {"role", "interview_type", "difficulty", "experience", "language", "duration", "interviewer", "code_language", "problem_ids"}
    cfg = {k: v for k, v in body.config.items() if k in allowed}
    with SessionLocal() as db:
        if body.cohort_id and not db.get(Cohort, body.cohort_id):
            raise HTTPException(422, "Unknown group")
        t = Template(name=body.name.strip(), cohort_id=body.cohort_id, config=cfg, focus_note=body.focus_note, created_by=admin.id)
        db.add(t)
        db.commit()
        return {"id": t.id}


@router.delete("/templates/{tid}")
def del_template(tid: int):
    with SessionLocal() as db:
        t = db.get(Template, tid)
        if t:
            db.delete(t)
            db.commit()
    return {"ok": True}


class SupportUpdate(BaseModel):
    status: str = Field(pattern="^(open|resolved)$")
    admin_note: str = Field(default="", max_length=2000)


@router.get("/support")
def support(status: str | None = None):
    with SessionLocal() as db:
        stmt = select(Support).order_by(Support.status.desc(), Support.id.desc())
        if status:
            stmt = stmt.where(Support.status == status)
        users = {u.id: u for u in db.scalars(select(User)).all()}
        return [{"id": s.id, "subject": s.subject, "message": s.message, "status": s.status, "admin_note": s.admin_note, "created_at": s.created_at.isoformat(),
                 "from": users[s.user_id].name if s.user_id in users else "?", "email": users[s.user_id].email if s.user_id in users else None} for s in db.scalars(stmt).all()]


@router.put("/support/{sid}")
def update_support(sid: int, body: SupportUpdate):
    with SessionLocal() as db:
        s = db.get(Support, sid)
        if not s:
            raise HTTPException(404, "Not found")
        s.status, s.admin_note = body.status, body.admin_note
        db.commit()
    return {"ok": True}


class RoleIn(BaseModel):
    role: str = Field(pattern="^(student|admin)$")


@router.get("/users")
def users(search: str = "", unverified: bool = False):
    with SessionLocal() as db:
        counts = dict(db.query(Interview.user_id, func.count(Interview.id)).group_by(Interview.user_id).all())
        rows = [u for u in db.scalars(select(User).where(User.is_guest.is_(False)).order_by(User.id.desc()).limit(500)).all() if (not search or search.lower() in (u.name + (u.email or "")).lower()) and not unverified]
        return [{"id": u.id, "name": u.name, "email": u.email, "role": u.role, "verified": u.email_verified, "interviews": counts.get(u.id, 0), "joined": u.created_at.isoformat()} for u in rows]


class BulkVerify(BaseModel):
    ids: list[int] | None = None   # None = every unverified student


@router.post("/users/verify")
def verify_many(body: BulkVerify):
    """Approve many students at once. Never touches admins and never promotes anyone."""
    with SessionLocal() as db:
        q = db.query(User).filter(User.is_guest.is_(False), User.email.isnot(None), User.email_verified.is_(False), User.role == "student")
        if body.ids is not None:
            q = q.filter(User.id.in_(body.ids or [-1]))
        rows = q.all()
        for u in rows:
            u.email_verified = True
        db.commit()
        return {"verified": len(rows)}


@router.put("/users/{uid}/verify")
def mark_verified(uid: int):
    """For students who can't receive the email. Admins only; this does NOT promote anyone."""
    with SessionLocal() as db:
        u = db.get(User, uid)
        if not u or u.is_guest or not u.email:
            raise HTTPException(404, "Not found")
        u.email_verified = True
        db.commit()
    return {"ok": True}


@router.put("/users/{uid}/role")
def set_role(uid: int, body: RoleIn, admin: User = Depends(admin_user)):
    if uid == admin.id:
        raise HTTPException(409, "You can't change your own role.")
    with SessionLocal() as db:
        u = db.get(User, uid)
        if not u or u.is_guest:
            raise HTTPException(404, "Not found")
        u.role = body.role
        db.commit()
    return {"ok": True}


# ======================================================================== email setup check
class TestMailIn(BaseModel):
    to: str = Field(min_length=5, max_length=200, pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


@router.get("/email")
def email_status():
    u = settings.smtp_user
    return {"configured": mailer.configured(), "host": settings.smtp_host, "port": settings.smtp_port, "security": mailer.security() if mailer.configured() else None,
            "from": settings.smtp_from, "user": (u[:3] + "***") if u else "", "verification_mode": settings.verification_mode, "app_url": settings.app_url}


@router.post("/email/test")
async def email_test(body: TestMailIn, admin: User = Depends(admin_user)):
    """Sends a real email right now and reports the exact reason if it fails (the normal send path is silent by design)."""
    from ..security import rate_limit
    rate_limit(admin.id, "mailtest", 6, 60)
    try:
        await asyncio.to_thread(mailer.send_blocking, body.to, "InterviewSaathi test email",
                                f"This is a test email from InterviewSaathi.\n\nIf you can read this, verification and password-reset emails will reach people.\nLinks in those emails will start with {settings.app_url}\n")
    except mailer.MailError as e:
        return {"ok": False, "error": str(e)}
    return {"ok": True}
