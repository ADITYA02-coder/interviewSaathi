from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from .. import coding, sandbox
from ..db import Interview, Problem, SessionLocal, Submission, Turn, User
from ..security import current_user, rate_limit

router = APIRouter(prefix="/api", tags=["code"])


class CodeIn(BaseModel):
    language: str = "python"
    code: str = Field(min_length=1, max_length=50_000)


def _check(language: str):
    if language not in sandbox.LANGUAGES:
        raise HTTPException(422, "Unsupported programming language")
    if not sandbox.enabled():
        raise HTTPException(503, "The code runner isn't configured on this server.")


async def _judge(problem, body: CodeIn, visible_only: bool):
    try:
        return await sandbox.run_problem(problem, body.language, body.code, visible_only)
    except sandbox.RunnerUnavailable as e:
        raise HTTPException(503, str(e))


# ---------------------------------------------------------------- practice mode (no interview needed)
@router.get("/problems")
def list_problems(user: User = Depends(current_user)):
    with SessionLocal() as db:
        rows = db.scalars(select(Problem).where(Problem.active.is_(True))).all()
        solved = {pid for (pid,) in db.query(Submission.problem_id).filter(Submission.user_id == user.id, Submission.kind == "submit", Submission.status == "accepted").all()}
        order = {"easy": 0, "medium": 1, "hard": 2}
        return [{"id": p.id, "title": p.title, "difficulty": p.difficulty, "topic": p.topic, "solved": p.id in solved} for p in sorted(rows, key=lambda p: (order.get(p.difficulty, 9), p.title))]


@router.get("/problems/{pid}")
def get_problem(pid: str, user: User = Depends(current_user)):
    with SessionLocal() as db:
        p = db.get(Problem, pid)
        if not p or not p.active:
            raise HTTPException(404, "Problem not found")
        last = db.scalars(select(Submission).where(Submission.user_id == user.id, Submission.problem_id == pid, Submission.interview_id.is_(None), Submission.kind == "submit").order_by(Submission.id.desc()).limit(1)).first()
        return {**sandbox.public_problem(p), "last_submission": {"language": last.language, "code": last.code, "status": last.status, "passed": last.passed, "total": last.total} if last else None}


@router.post("/problems/{pid}/run")
async def practice_run(pid: str, body: CodeIn, user: User = Depends(current_user)):
    _check(body.language); rate_limit(user.id, "judge", 12, 30)
    with SessionLocal() as db:
        p = db.get(Problem, pid)
        if not p:
            raise HTTPException(404, "Problem not found")
    return await _judge(p, body, True)


@router.post("/problems/{pid}/submit")
async def practice_submit(pid: str, body: CodeIn, user: User = Depends(current_user)):
    _check(body.language); rate_limit(user.id, "judge", 12, 30)
    with SessionLocal() as db:
        p = db.get(Problem, pid)
        if not p:
            raise HTTPException(404, "Problem not found")
    res = await _judge(p, body, False)
    with SessionLocal() as db:
        coding.record_submission(db, None, p, body.language, body.code, res, "submit", user.id)
        db.commit()
    return res


# ---------------------------------------------------------------- inside a coding interview
def _active_coding(db, interview_id: str, user: User) -> Interview:
    it = db.get(Interview, interview_id)
    if not it or it.user_id != user.id:
        raise HTTPException(404, "Interview not found")
    if it.config.get("interview_type") != "coding" or it.status != "active":
        raise HTTPException(409, "This isn't an active coding interview.")
    return it


@router.post("/interviews/{interview_id}/code/run")
async def interview_run(interview_id: str, body: CodeIn, user: User = Depends(current_user)):
    _check(body.language); rate_limit(user.id, "judge", 12, 30)
    with SessionLocal() as db:
        it = _active_coding(db, interview_id, user)
        p = coding.current(db, it)
        if not p or it.state["phase"] == "followup":
            raise HTTPException(409, "You've already submitted this problem.")
    res = await _judge(p, body, True)
    with SessionLocal() as db:
        coding.record_submission(db, db.get(Interview, interview_id), p, body.language, body.code, res, "run", user.id)
        db.commit()
    return res


@router.post("/interviews/{interview_id}/code/submit")
async def interview_submit(interview_id: str, body: CodeIn, user: User = Depends(current_user)):
    _check(body.language); rate_limit(user.id, "judge", 12, 30)
    with SessionLocal() as db:
        it = _active_coding(db, interview_id, user)
        p = coding.current(db, it)
        if not p or it.state["phase"] not in ("approach", "coding"):
            raise HTTPException(409, "This problem has already been submitted.")
    res = await _judge(p, body, False)
    with SessionLocal() as db:
        it = _active_coding(db, interview_id, user)
        import copy
        st = copy.deepcopy(it.state)
        coding.record_submission(db, it, p, body.language, body.code, res, "submit", user.id)
        st["results"][p.id] = {**st["results"].get(p.id, {}), "submitted": True, "status": res["status"], "passed": res["passed"], "total": res["total"], "last_public": res}
        st["phase"] = "followup"
        it.state = st
        reply = coding.after_submit_reply(it, res, len(it.turns))
        db.add(Turn(interview_id=it.id, idx=len(it.turns), role="interviewer", text=reply, topic=p.topic, kind="followup", meta={"problem_id": p.id, "phase": "followup"}))
        db.commit()
        return {"result": res, "reply": reply, "coding": coding.view(db, it)}


@router.post("/interviews/{interview_id}/code/skip")
async def interview_skip(interview_id: str, user: User = Depends(current_user)):
    import copy
    with SessionLocal() as db:
        it = _active_coding(db, interview_id, user)
        p = coding.current(db, it)
        if not p:
            raise HTTPException(409, "Nothing to skip.")
        st = copy.deepcopy(it.state)
        st["results"].setdefault(p.id, {})["skipped"] = not st["results"].get(p.id, {}).get("submitted")
        r = coding._advance(db, st, it, user.name if not user.is_guest else "there", coding.T(it.config)["skipped"])
        it.state = st
        db.add(Turn(interview_id=it.id, idx=len(it.turns), role="interviewer", text=r["reply"], topic=r["topic"], kind=r["kind"], meta=r.get("meta")))
        db.commit()
        return {"reply": r["reply"], "kind": r["kind"], "done": r["done"], "coding": coding.view(db, it)}
