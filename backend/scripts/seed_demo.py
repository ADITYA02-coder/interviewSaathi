"""Demo data for showing the admin dashboard, leaderboard and reports without waiting for real students.

    python -m scripts.seed_demo --yes        add demo data
    python -m scripts.seed_demo --remove     delete ALL demo data (safe: only touches @demo.interviewsaathi.app accounts)
    python -m scripts.seed_demo --reset      remove, then add again

HONESTY NOTES: every demo account uses the email domain @demo.interviewsaathi.app, the sessions are generated (scored by the offline
keyword scorer and labelled engine="demo-seed"), and submitted "code" is a placeholder. Never leave demo data in a production
database that real students use: it would show up in your leaderboard. Remove it before launch.
"""
import argparse
import asyncio
import random
import sys
from datetime import datetime, timedelta

from app import coding, interviewer, llm, problems_seed, questionbank as qb
from app.db import Cohort, Interview, Membership, Problem, SessionLocal, Submission, Support, Template, Turn, User, init_db
from app.security import hash_password

DOMAIN = "demo.interviewsaathi.app"
ADMIN_EMAIL, ADMIN_PASSWORD, STUDENT_PASSWORD = f"admin@{DOMAIN}", "DemoAdmin123!", "demo12345"
ROLE_TYPES = {"Java Developer": "java", "MERN Stack Developer": "mern", "Python Developer": "python", "Data Analyst": "data", "HR / General": "hr"}

# name, skill 0-1, growth per session, sessions, days since last session, cohort index, shares answers, role, coding skill (None = no coding)
STUDENTS = [
    ("Priya Sharma", .86, .03, 5, 1, 0, True, "Java Developer", .95),
    ("Arjun Mehta", .78, .04, 5, 2, 0, False, "MERN Stack Developer", .8),
    ("Ananya Iyer", .72, .06, 4, 3, 0, False, "Python Developer", .7),
    ("Rohan Das", .66, .02, 3, 5, 0, True, "Data Analyst", None),
    ("Sneha Reddy", .62, .07, 5, 2, 1, False, "Java Developer", .6),
    ("Vikram Singh", .58, -.02, 4, 6, 1, False, "Python Developer", .45),
    ("Kavya Nair", .55, .05, 3, 4, 1, False, "HR / General", None),
    ("Imran Khan", .5, .03, 3, 9, 0, False, "MERN Stack Developer", .5),
    ("Divya Patel", .45, .04, 2, 12, 1, False, "Data Analyst", None),
    ("Manish Kumar", .38, .01, 3, 21, 0, False, "Java Developer", .3),
    ("Pooja Verma", .33, .02, 2, 25, 1, False, "HR / General", None),
    ("Suresh Rao", .0, 0, 0, 0, 1, False, "Python Developer", None),   # joined, never finished an interview: shows up as "needs attention"
]
FILLER = ["So basically,", "I think,", "As far as I know,", "Okay, so", "Let me explain."]


def _clamp(x, lo=0.05, hi=0.97):
    return max(lo, min(hi, x))


def _answer(concepts, quality, rnd) -> str:
    k = max(0, min(len(concepts), round(len(concepts) * quality + rnd.uniform(-.6, .6))))
    chosen = rnd.sample(list(concepts), k)
    if not chosen:
        return "I am not completely sure about this. I think it depends on the situation and the use case, but I would need to look it up."
    bits = [f"{rnd.choice(['it uses', 'we have', 'there is', 'it involves', 'one point is'])} {rnd.choice(list(syns))}" for _, syns in chosen]
    return f"{rnd.choice(FILLER)} " + ". ".join(bits) + ". That is how I understand it from my projects and practice."


def _ts(days_ago: float, rnd) -> datetime:
    return datetime.utcnow() - timedelta(days=days_ago, hours=rnd.randint(0, 6), minutes=rnd.randint(0, 59))


def _eval(q, text, kind):
    ev = qb.evaluate(q, text)
    ev["engine"] = "demo-seed"
    ev["overall"] = interviewer.overall_from(ev["scores"], kind)
    return ev


def _regular_session(db, user, role, itype, quality, started, rnd, n_q):
    cfg = {"role": role, "interview_type": itype, "difficulty": "intermediate", "experience": "fresher", "language": rnd.choice(["en-IN"] * 4 + ["hinglish"]),
           "duration": "standard", "interviewer": rnd.choice(["female", "male"]), "voice_speed": 1.0}
    it = Interview(id=f"demo{rnd.getrandbits(52):013x}", user_id=user.id, config=cfg, status="completed", engine="demo-seed", started_at=started, ended_at=started + timedelta(minutes=rnd.randint(12, 24)))
    db.add(it)
    db.flush()
    kind = interviewer.kind_of(cfg)
    qs = qb.question_list(cfg, it.id)[:n_q]
    idx, t = 0, started
    for q in qs:
        t += timedelta(seconds=40)
        db.add(Turn(interview_id=it.id, idx=idx, role="interviewer", text=q["q"], topic=q["topic"], kind="main", meta={"bank_q": q["q"]}, created_at=t)); idx += 1
        text = _answer(q["concepts"], quality, rnd)
        t += timedelta(seconds=rnd.randint(25, 80))
        db.add(Turn(interview_id=it.id, idx=idx, role="candidate", text=text, topic=q["topic"], kind="answer", source="voice" if rnd.random() < .85 else "text", question_ref=q["q"],
                    evaluation=_eval(q, text, kind), meta={"duration_ms": rnd.randint(15000, 60000)}, created_at=t)); idx += 1
    db.add(Turn(interview_id=it.id, idx=idx, role="interviewer", text=f"Thank you {user.name.split()[0]}, that brings us to the end of the interview.", topic="Wrap up", kind="closing", created_at=t))
    db.commit()
    return it.id


def _coding_session(db, user, role, quality, started, rnd):
    probs = [p for p in db.query(Problem).filter(Problem.difficulty == "easy", Problem.active.is_(True)).all()]
    rnd.shuffle(probs)
    probs = probs[:2]
    cfg = {"role": role, "interview_type": "coding", "difficulty": "beginner", "experience": "fresher", "language": "en-IN", "duration": "standard", "interviewer": "female", "voice_speed": 1.0, "code_language": "python"}
    it = Interview(id=f"demo{rnd.getrandbits(52):013x}", user_id=user.id, config=cfg, status="completed", engine="demo-seed", started_at=started, ended_at=started + timedelta(minutes=30),
                   state={"problems": [p.id for p in probs], "i": len(probs), "phase": "done", "results": {}})
    db.add(it)
    db.flush()
    idx, t = 0, started
    for p in probs:
        approach = _answer(p.approach_keywords, quality, rnd)
        good = rnd.random() < quality + .1
        complexity = (f"The time complexity is {p.expected_time} and the space is {p.expected_space}. Edge cases are empty input and duplicates." if good else "I think it is fast enough, not sure about the exact complexity.")
        for phase, text in (("approach", approach), ("followup", complexity)):
            t += timedelta(seconds=60)
            ev = coding.offline_eval(p, phase, text); ev["engine"] = "demo-seed"; ev["topic"] = p.topic; ev["overall"] = interviewer.overall_from(ev["scores"], "technical")
            db.add(Turn(interview_id=it.id, idx=idx, role="interviewer", text=p.summary if phase == "approach" else "What is the time and space complexity?", topic=p.topic, kind="main", meta={"problem_id": p.id, "phase": phase}, created_at=t)); idx += 1
            db.add(Turn(interview_id=it.id, idx=idx, role="candidate", text=text, topic=p.topic, kind="answer", source="voice", evaluation=ev, meta={"problem_id": p.id, "phase": phase}, created_at=t)); idx += 1
        total = len(p.tests)
        passed = total if rnd.random() < quality else max(0, int(total * rnd.uniform(.3, .85)))
        tests = [{"i": i + 1, "hidden": bool(tt.get("hidden")), "status": "pass" if i < passed else "wrong_answer", "time_ms": rnd.randint(8, 90)} for i, tt in enumerate(p.tests)]
        for _ in range(rnd.randint(1, 3)):
            db.add(Submission(user_id=user.id, interview_id=it.id, problem_id=p.id, language="python", code="# Demo data: no real code was written for this seeded run\n", kind="run", passed=min(2, passed), total=2, status="accepted" if passed >= 2 else "wrong_answer", created_at=t))
        db.add(Submission(user_id=user.id, interview_id=it.id, problem_id=p.id, language="python", code="# Demo data: no real code was written for this seeded submission\n", kind="submit", passed=passed, total=total,
                          status="accepted" if passed == total else "wrong_answer", results=tests, created_at=t))
    db.commit()
    return it.id


def seed(db, quiet=False):
    llm.provider = lambda: "none"            # reports are built by the deterministic offline summariser, never by a live model
    if db.query(User).filter(User.email.like(f"%@{DOMAIN}")).count():
        raise SystemExit("Demo data already exists. Use --reset to recreate it or --remove to delete it.")
    rnd = random.Random(2026)
    admin = User(email=ADMIN_EMAIL, name="Demo Admin", role="admin", email_verified=True, password_hash=hash_password(ADMIN_PASSWORD))
    db.add(admin)
    db.flush()
    cohorts = []
    for name, code in (("CSE 2026 (Demo)", "DEMO01"), ("IT 2026 (Demo)", "DEMO02")):
        existing = db.query(Cohort).filter(Cohort.code == code).first()
        c = existing or Cohort(name=name, code=code, created_by=admin.id)
        if not existing:
            db.add(c)
        cohorts.append(c)
    db.flush()
    sessions = 0
    for name, skill, growth, n, last_days, ci, share, role, code_skill in STUDENTS:
        first, last = name.lower().split()
        u = User(email=f"{first}.{last}@{DOMAIN}", name=name, email_verified=True, password_hash=hash_password(STUDENT_PASSWORD), education="B.Tech, 2026",
                 skills=ROLE_TYPES[role].upper() + ", Git, SQL", target_role=role, target_companies="TCS, Infosys, Tata Steel", created_at=_ts(60, rnd))
        db.add(u)
        db.flush()
        db.add(Membership(user_id=u.id, cohort_id=cohorts[ci].id, share_transcripts=share))
        types = ["technical", "hr", "technical", "behavioral", "mixed"]
        for i in range(n):
            days_ago = last_days + (n - 1 - i) * rnd.randint(5, 9)
            quality = _clamp(skill + growth * (i - (n - 1) / 2) + rnd.uniform(-.06, .06))
            itype = "technical" if role != "HR / General" else rnd.choice(["hr", "behavioral"])
            itype = types[i % len(types)] if role != "HR / General" else itype
            iid = _regular_session(db, u, role, itype, quality, _ts(days_ago, rnd), rnd, rnd.randint(4, 6))
            it = db.get(Interview, iid)
            report = asyncio.run(interviewer.build_report(it, u.name))
            it.report, it.overall_score = report, report["overall"]
            sessions += 1
        if code_skill is not None and n:
            iid = _coding_session(db, u, role, code_skill, _ts(max(1, last_days - 1), rnd), rnd)
            it = db.get(Interview, iid)
            report = asyncio.run(coding.build_report(it, u.name))
            it.report, it.overall_score = report, report["overall"]
            sessions += 1
            for p in db.query(Problem).filter(Problem.difficulty == "easy").limit(int(code_skill * 6)).all():   # a few extra practice-mode solves
                db.add(Submission(user_id=u.id, interview_id=None, problem_id=p.id, language="python", code="# Demo data\n", kind="submit", passed=10, total=10, status="accepted", created_at=_ts(rnd.randint(1, 30), rnd)))
        db.commit()
    db.add(Template(name="Mock placement drive: Week 1", cohort_id=cohorts[0].id, config={"role": "Java Developer", "interview_type": "technical", "difficulty": "intermediate", "duration": "standard"}, focus_note="Concentrate on OOP and collections", created_by=admin.id))
    db.add(Template(name="Coding warm-up", cohort_id=None, config={"role": "Java Developer", "interview_type": "coding", "difficulty": "beginner", "duration": "standard", "problem_ids": ["two-sum", "valid-parentheses"]}, focus_note="", created_by=admin.id))
    sneha = db.query(User).filter(User.email == f"sneha.reddy@{DOMAIN}").first(); vik = db.query(User).filter(User.email == f"vikram.singh@{DOMAIN}").first()
    db.add(Support(user_id=sneha.id, subject="Microphone not detected", message="The interview page says my microphone is blocked on Safari.", status="open"))
    db.add(Support(user_id=vik.id, subject="Question about my report", message="Why did my HR answer score lower than my technical one?", status="resolved", admin_note="HR answers are scored on specificity and examples. Add a concrete story next time."))
    db.commit()
    if not quiet:
        print(f"Created {len(STUDENTS)} demo students in 2 groups, {sessions} interviews, 2 assigned templates, 2 support requests.")
        print(f"  Admin login   : {ADMIN_EMAIL} / {ADMIN_PASSWORD}")
        print(f"  Student login : priya.sharma@{DOMAIN} / {STUDENT_PASSWORD}   (any student, same password)")
        print("  Group codes   : DEMO01, DEMO02")
        print("Remove everything later with:  python -m scripts.seed_demo --remove")


def remove(db, quiet=False):
    users = db.query(User).filter(User.email.like(f"%@{DOMAIN}")).all()
    ids = [u.id for u in users]
    if not ids:
        if not quiet:
            print("No demo data found.")
        return
    iids = [i for (i,) in db.query(Interview.id).filter(Interview.user_id.in_(ids)).all()]
    cohort_ids = [c for (c,) in db.query(Cohort.id).filter(Cohort.created_by.in_(ids)).all()]
    if iids:
        db.query(Turn).filter(Turn.interview_id.in_(iids)).delete(synchronize_session=False)
        db.query(Submission).filter(Submission.interview_id.in_(iids)).delete(synchronize_session=False)
    db.query(Submission).filter(Submission.user_id.in_(ids)).delete(synchronize_session=False)
    db.query(Interview).filter(Interview.user_id.in_(ids)).delete(synchronize_session=False)
    db.query(Membership).filter((Membership.user_id.in_(ids)) | (Membership.cohort_id.in_(cohort_ids or [-1]))).delete(synchronize_session=False)
    db.query(Support).filter(Support.user_id.in_(ids)).delete(synchronize_session=False)
    db.query(Template).filter(Template.created_by.in_(ids)).delete(synchronize_session=False)
    db.query(Cohort).filter(Cohort.id.in_(cohort_ids or [-1])).delete(synchronize_session=False)
    db.query(User).filter(User.id.in_(ids)).delete(synchronize_session=False)
    db.commit()
    if not quiet:
        print(f"Removed {len(ids)} demo accounts and everything attached to them.")


def main():
    ap = argparse.ArgumentParser(description="Seed or remove demo data.")
    ap.add_argument("--yes", action="store_true", help="don't ask for confirmation")
    ap.add_argument("--remove", action="store_true", help="delete all demo data")
    ap.add_argument("--reset", action="store_true", help="remove then re-create")
    a = ap.parse_args()
    init_db()
    from app import questionbank
    with SessionLocal() as db:
        questionbank.seed_builtin(db)
        problems_seed.seed(db)
        if not a.yes and not input("This writes DEMO accounts into the current database. Is that OK? [y/N] ").lower().startswith("y"):
            sys.exit("Cancelled.")
        if a.remove or a.reset:
            remove(db)
        if not a.remove:
            seed(db)


if __name__ == "__main__":
    main()
