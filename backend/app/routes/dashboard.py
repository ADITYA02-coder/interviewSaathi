from collections import defaultdict
from fastapi import APIRouter, Depends
from sqlalchemy import select
from ..db import Interview, SessionLocal, User
from ..security import current_user

router = APIRouter(prefix="/api", tags=["dashboard"])


@router.get("/dashboard")
def dashboard(user: User = Depends(current_user)):
    """Everything here is computed from saved interview results. Nothing is invented."""
    with SessionLocal() as db:
        its = db.scalars(select(Interview).where(Interview.user_id == user.id, Interview.status == "completed").order_by(Interview.started_at)).all()
        done = [i for i in its if i.report and i.report.get("answered", 0) > 0]
        by_type, topics, sessions = defaultdict(list), defaultdict(list), []
        for i in done:
            r = i.report
            by_type[i.config.get("interview_type", "technical")].append(r["overall"])
            for t in r.get("topics", []):
                topics[t["topic"]].append(t["score"])
            sessions.append({"id": i.id, "date": i.started_at.isoformat(), "overall": r["overall"], "role": i.config.get("role"),
                             "type": i.config.get("interview_type"), "dimensions": r["dimensions"]})
        rows = sorted(({"topic": k, "score": round(sum(v) / len(v)), "count": len(v)} for k, v in topics.items()), key=lambda x: x["score"])
        weak = [t for t in rows if t["score"] < 70][:5]
        return {
            "total_completed": len(done),
            "average_overall": round(sum(s["overall"] for s in sessions) / len(sessions)) if sessions else None,
            "by_type": [{"type": k, "average": round(sum(v) / len(v)), "count": len(v)} for k, v in by_type.items()],
            "sessions": sessions, "weakest_topics": weak,
            "strongest_topics": [t for t in reversed(rows) if t["score"] >= 70][:5],
            "first_vs_latest": {"first": sessions[0], "latest": sessions[-1]} if len(sessions) >= 2 else None,
            "recommended_practice": [t["topic"] for t in weak[:3]],
        }
