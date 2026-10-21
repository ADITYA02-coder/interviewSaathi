import asyncio
import uuid
from datetime import datetime
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy import select
from .. import coding, gnani, interviewer, llm, resume as resume_mod, sandbox
from ..config import settings
from ..db import Interview, SessionLocal, Turn, User
from ..security import current_user

router = APIRouter(prefix="/api", tags=["interviews"])
ROLES = ["Java Developer", "MERN Stack Developer", "Python Developer", "Data Analyst", "HR / General"]


class ConfigIn(BaseModel):
    role: str = Field(default="Java Developer", max_length=120)
    interview_type: str = "technical"
    difficulty: str = "intermediate"
    experience: str = "fresher"
    language: str = "en-IN"
    duration: str = "standard"
    interviewer: str = "female"
    voice_speed: float = 1.0
    code_language: str = "python"
    focus_note: str = Field(default="", max_length=600)
    problem_ids: list[str] = Field(default_factory=list, max_length=6)


class CreateIn(BaseModel):
    config: ConfigIn
    resume_text: str = Field(default="", max_length=8000)
    jd_text: str = Field(default="", max_length=6000)


class AnswerIn(BaseModel):
    text: str = Field(min_length=1, max_length=4000)
    source: str = Field(default="voice", pattern="^(voice|text)$")
    duration_ms: int | None = None


def _get_owned(db, interview_id: str, user: User) -> Interview:
    it = db.get(Interview, interview_id)
    if not it or it.user_id != user.id:
        raise HTTPException(404, "Interview not found")
    return it


def _voice_info(config: dict) -> dict:
    lang = config.get("language", "en-IN")
    voice, tts_lang = gnani.pick_voice(lang, config.get("interviewer", "female"))
    return {"voice": voice, "tts_language": tts_lang, "stt_language": lang, "label": gnani.LANGUAGES.get(lang, gnani.LANGUAGES["en-IN"])["label"], "speed": config.get("voice_speed", 1.0)}


def _turn_out(t: Turn) -> dict:
    return {"idx": t.idx, "role": t.role, "text": t.text, "topic": t.topic, "kind": t.kind, "source": t.source,
            "question": t.question_ref, "evaluation": t.evaluation, "created_at": t.created_at.isoformat()}


def _summary(it: Interview) -> dict:
    answered = sum(1 for t in it.turns if t.role == "candidate" and t.kind == "answer")
    return {"id": it.id, "config": it.config, "status": it.status, "overall_score": it.overall_score, "answered": answered,
            "started_at": it.started_at.isoformat(), "ended_at": it.ended_at.isoformat() if it.ended_at else None, "engine": it.engine}


@router.get("/meta")
def meta():
    return {
        "gnani_configured": gnani.configured(), "llm": llm.engine_name(), "llm_live": llm.provider() != "none",
        "languages": [{"code": k, "label": v["label"], "male": bool(v["voices"].get("male")), "beta": k not in ("en-IN", "hi-IN", "hinglish")} for k, v in gnani.LANGUAGES.items()],
        "roles": ROLES, "tts_model": gnani.settings.gnani_tts_model, "coding_enabled": sandbox.enabled(), "code_languages": sandbox.LANGUAGES,
        "stream_stt": gnani.settings.gnani_streaming and gnani.configured(), "verification": settings.verification_mode,
    }


@router.post("/resume/parse")
async def parse_resume(file: UploadFile = File(...), _=Depends(current_user)):
    try:
        text = resume_mod.extract_text(file.filename or "", await file.read())
    except ValueError as e:
        raise HTTPException(422, str(e))
    except Exception:
        raise HTTPException(422, "Could not read this file.")
    return {"text": text, "chars": len(text)}


@router.post("/interviews")
async def create_interview(body: CreateIn, user: User = Depends(current_user)):
    cfg = body.config.model_dump()
    if cfg["interview_type"] not in ("technical", "hr", "behavioral", "project", "mixed", "coding"):
        raise HTTPException(422, "Unknown interview type")
    if cfg["language"] not in gnani.LANGUAGES:
        raise HTTPException(422, "Unsupported language")
    if cfg["interviewer"] == "male" and not gnani.LANGUAGES[cfg["language"]]["voices"].get("male"):
        cfg["interviewer"] = "female"
    cfg["voice_speed"] = max(0.85, min(1.15, cfg["voice_speed"]))
    is_coding = cfg["interview_type"] == "coding"
    if is_coding:
        if cfg["code_language"] not in sandbox.LANGUAGES:
            raise HTTPException(422, "Unsupported programming language")
        if not sandbox.enabled():
            raise HTTPException(503, "Coding rounds need the code-runner service, which isn't configured on this server yet.")
    name = user.name if not user.is_guest else "there"
    with SessionLocal() as db:
        it = Interview(id=uuid.uuid4().hex[:16], user_id=user.id, config=cfg, resume_text=body.resume_text, jd_text=body.jd_text, engine=llm.engine_name())
        db.add(it)
        db.flush()
        try:
            first = await (coding.opening(db, it, name) if is_coding else interviewer.opening(it, name))
        except ValueError as e:
            raise HTTPException(503, str(e))
        db.add(Turn(interview_id=it.id, idx=0, role="interviewer", text=first["reply"], topic=first["topic"], kind="main", meta=first.get("meta")))
        db.commit()
        out = {"id": it.id, "config": cfg, "persona": interviewer.persona_name(cfg), "voice": _voice_info(cfg),
               "total_questions": len(it.state["problems"]) if is_coding else interviewer.total_questions(cfg), "engine": it.engine,
               "opening": {"text": first["reply"], "topic": first["topic"]}}
        if is_coding:
            out["coding"] = coding.view(db, it)
        return out


@router.post("/interviews/{interview_id}/answer")
async def answer(interview_id: str, body: AnswerIn, user: User = Depends(current_user)):
    with SessionLocal() as db:
        it = _get_owned(db, interview_id, user)
        if it.status != "active":
            raise HTTPException(409, "This interview has already ended.")
        turns = list(it.turns)
        answers_done = sum(1 for t in turns if t.role == "candidate" and t.kind in ("answer", "skip"))
        prev_q = next((t for t in reversed(turns) if t.role == "interviewer"), None)
        cand = Turn(interview_id=it.id, idx=len(turns), role="candidate", text=body.text.strip(), kind="answer", source=body.source,
                    question_ref=prev_q.text if prev_q else None, topic=prev_q.topic if prev_q else "", meta={"duration_ms": body.duration_ms})
        db.add(cand)
        db.flush()
        turns.append(cand)
        name = user.name if not user.is_guest else "there"
        if it.config.get("interview_type") == "coding":
            r = await coding.handle_answer(db, it, cand, name, answers_done)
            if r["candidate_turn_type"] == "clarification":
                cand.kind = "clarification"
        else:
            r = await interviewer.next_turn(it, turns, name, answers_done)
            cand.kind = r["candidate_turn_type"]
        db.add(Turn(interview_id=it.id, idx=len(turns), role="interviewer", text=r["reply"], topic=r["topic"], kind=r["kind"], meta=r.get("meta")))
        db.commit()
        bank_ref = (prev_q.meta or {}).get("bank_q") if prev_q else None
        if cand.kind == "answer":
            asyncio.create_task(_evaluate_in_background(it.id, cand.id, bank_ref))
        out = {"reply": r["reply"], "topic": r["topic"], "kind": r["kind"], "done": r["done"], "turn_index": len(turns),
               "answered": answers_done + (1 if cand.kind in ("answer", "skip") else 0)}
        if it.config.get("interview_type") == "coding":
            out["coding"] = coding.view(db, it)
            out["answered"] = min(it.state["i"] + (0 if r["done"] else 0), len(it.state["problems"])) if not r["done"] else len(it.state["problems"])
        return out


async def _evaluate_turn(interview_id: str, turn_id: int, bank_ref):
    with SessionLocal() as db:
        it, t = db.get(Interview, interview_id), db.get(Turn, turn_id)
        if not it or not t or t.evaluation:
            return
        if it.config.get("interview_type") == "coding":
            t.evaluation = await coding.evaluate_turn(it, t)
        else:
            t.evaluation = await interviewer.evaluate_answer(it, t.question_ref or "", t.text, t.topic, bank_ref)
        db.commit()


async def _evaluate_in_background(interview_id: str, turn_id: int, bank_ref):
    try:
        await _evaluate_turn(interview_id, turn_id, bank_ref)
    except Exception:  # a background failure must never disturb the live call; finish() retries
        pass


async def _ensure_evaluations(interview_id: str):
    pending = []
    for _ in range(40):  # wait up to ~20 s for background evaluations
        with SessionLocal() as db:
            pending = [t.id for t in db.scalars(select(Turn).where(Turn.interview_id == interview_id, Turn.kind == "answer", Turn.evaluation.is_(None)))]
        if not pending:
            return
        await asyncio.sleep(0.5)
    for tid in pending:
        with SessionLocal() as db:
            t = db.get(Turn, tid)
            prev = db.scalar(select(Turn).where(Turn.interview_id == interview_id, Turn.idx == t.idx - 1))
            bank = (prev.meta or {}).get("bank_q") if prev else None
        await _evaluate_turn(interview_id, tid, bank)


@router.post("/interviews/{interview_id}/finish")
async def finish(interview_id: str, user: User = Depends(current_user)):
    with SessionLocal() as db:
        it = _get_owned(db, interview_id, user)
        if it.report:
            return {"report": it.report, **_summary(it)}
    await _ensure_evaluations(interview_id)
    with SessionLocal() as db:
        it = _get_owned(db, interview_id, user)
        if it.report:
            return {"report": it.report, **_summary(it)}
        report = await interviewer.build_report(it, user.name)
        it.report, it.overall_score, it.status, it.ended_at = report, report["overall"], "completed", datetime.utcnow()
        db.commit()
        return {"report": report, **_summary(it)}


@router.get("/interviews")
def list_interviews(user: User = Depends(current_user)):
    with SessionLocal() as db:
        rows = db.scalars(select(Interview).where(Interview.user_id == user.id).order_by(Interview.started_at.desc()).limit(100)).all()
        return [_summary(r) for r in rows]


@router.get("/interviews/{interview_id}")
def get_interview(interview_id: str, user: User = Depends(current_user)):
    with SessionLocal() as db:
        it = _get_owned(db, interview_id, user)
        coding_view = coding.view(db, it) if it.config.get("interview_type") == "coding" and it.status == "active" else None
        return {**_summary(it), "persona": interviewer.persona_name(it.config), "voice": _voice_info(it.config), "report": it.report, "coding": coding_view,
                "total_questions": len(it.state["problems"]) if it.state else interviewer.total_questions(it.config), "turns": [_turn_out(t) for t in it.turns]}


@router.delete("/interviews/{interview_id}")
def delete_interview(interview_id: str, user: User = Depends(current_user)):
    with SessionLocal() as db:
        db.delete(_get_owned(db, interview_id, user))
        db.commit()
    return {"deleted": True}
