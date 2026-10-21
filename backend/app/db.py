from datetime import datetime
from typing import Optional
from sqlalchemy import JSON, DateTime, Float, ForeignKey, Integer, String, Text, Boolean, create_engine, inspect, text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship, sessionmaker
from .config import settings

connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
engine = create_engine(settings.database_url, connect_args=connect_args, pool_pre_ping=True)  # pre-ping: hosted Postgres drops idle connections
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[Optional[str]] = mapped_column(String(255), unique=True, nullable=True)
    name: Mapped[str] = mapped_column(String(120), default="Candidate")
    password_hash: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    is_guest: Mapped[bool] = mapped_column(Boolean, default=False)
    education: Mapped[str] = mapped_column(String(255), default="")
    skills: Mapped[str] = mapped_column(Text, default="")
    target_role: Mapped[str] = mapped_column(String(120), default="")
    preferred_language: Mapped[str] = mapped_column(String(16), default="en-IN")
    target_companies: Mapped[str] = mapped_column(Text, default="")
    role: Mapped[str] = mapped_column(String(16), default="student")  # student | admin
    email_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    interviews = relationship("Interview", back_populates="user", cascade="all, delete-orphan")


class Interview(Base):
    __tablename__ = "interviews"
    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    config: Mapped[dict] = mapped_column(JSON, default=dict)
    resume_text: Mapped[str] = mapped_column(Text, default="")
    jd_text: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(16), default="active")  # active | completed
    state: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)  # coding rounds: problem sequence + phase
    engine: Mapped[str] = mapped_column(String(160), default="")
    report: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    overall_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    ended_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    user = relationship("User", back_populates="interviews")
    turns = relationship("Turn", back_populates="interview", cascade="all, delete-orphan", order_by="Turn.idx")


class Turn(Base):
    __tablename__ = "turns"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    interview_id: Mapped[str] = mapped_column(ForeignKey("interviews.id"))
    idx: Mapped[int] = mapped_column(Integer)
    role: Mapped[str] = mapped_column(String(16))  # interviewer | candidate
    text: Mapped[str] = mapped_column(Text)
    topic: Mapped[str] = mapped_column(String(120), default="")
    kind: Mapped[str] = mapped_column(String(24), default="")  # interviewer: main|followup|clarify|closing ; candidate: answer|clarification|skip
    source: Mapped[str] = mapped_column(String(8), default="")  # voice | text
    question_ref: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    evaluation: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    meta: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    interview = relationship("Interview", back_populates="turns")


class Cohort(Base):
    __tablename__ = "cohorts"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    code: Mapped[str] = mapped_column(String(12), unique=True)
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Membership(Base):
    """A student joining a cohort with its code is their explicit consent to share SCORES and report summaries with that cohort's admins.
    Full answer transcripts stay private unless the student also switches share_transcripts on."""
    __tablename__ = "memberships"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    cohort_id: Mapped[int] = mapped_column(ForeignKey("cohorts.id"))
    share_transcripts: Mapped[bool] = mapped_column(Boolean, default=False)
    joined_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Question(Base):
    __tablename__ = "questions"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    bank_key: Mapped[str] = mapped_column(String(16))  # java | python | mern | data | hr | behavioral
    topic: Mapped[str] = mapped_column(String(80), default="General")
    level: Mapped[int] = mapped_column(Integer, default=2)  # 1 beginner .. 3 advanced
    text: Mapped[str] = mapped_column(Text)
    concepts: Mapped[list] = mapped_column(JSON, default=list)  # [[label, [synonyms]]]
    followup: Mapped[str] = mapped_column(Text, default="")
    model_answer: Mapped[str] = mapped_column(Text, default="")
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    source: Mapped[str] = mapped_column(String(10), default="custom")  # builtin | custom


class Problem(Base):
    __tablename__ = "problems"
    id: Mapped[str] = mapped_column(String(48), primary_key=True)  # slug
    title: Mapped[str] = mapped_column(String(160))
    difficulty: Mapped[str] = mapped_column(String(12), default="easy")  # easy | medium | hard
    topic: Mapped[str] = mapped_column(String(80), default="Arrays")
    statement: Mapped[str] = mapped_column(Text)
    input_format: Mapped[str] = mapped_column(Text, default="")
    output_format: Mapped[str] = mapped_column(Text, default="")
    examples: Mapped[list] = mapped_column(JSON, default=list)  # [{input, output, note}]
    tests: Mapped[list] = mapped_column(JSON, default=list)  # [{input, expected, hidden}]
    expected_time: Mapped[str] = mapped_column(String(40), default="")
    expected_space: Mapped[str] = mapped_column(String(40), default="")
    approach_keywords: Mapped[list] = mapped_column(JSON, default=list)  # [[label,[synonyms]]]
    summary: Mapped[str] = mapped_column(Text, default="")  # one spoken sentence
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    source: Mapped[str] = mapped_column(String(10), default="custom")


class Submission(Base):
    __tablename__ = "submissions"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    interview_id: Mapped[Optional[str]] = mapped_column(ForeignKey("interviews.id"), nullable=True)
    problem_id: Mapped[str] = mapped_column(String(48))
    language: Mapped[str] = mapped_column(String(16))
    code: Mapped[str] = mapped_column(Text)
    kind: Mapped[str] = mapped_column(String(8), default="submit")  # run | submit
    passed: Mapped[int] = mapped_column(Integer, default=0)
    total: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(24), default="")  # accepted | wrong_answer | runtime_error | compile_error | timeout | error
    results: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Template(Base):
    """An interview an admin assigns to a cohort (or everyone). Students start it in one click from the setup page."""
    __tablename__ = "templates"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(160))
    cohort_id: Mapped[Optional[int]] = mapped_column(ForeignKey("cohorts.id"), nullable=True)
    config: Mapped[dict] = mapped_column(JSON, default=dict)
    focus_note: Mapped[str] = mapped_column(Text, default="")
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Support(Base):
    __tablename__ = "support"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    subject: Mapped[str] = mapped_column(String(200))
    message: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(12), default="open")  # open | resolved
    admin_note: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


def _ensure_columns():
    """Tiny forward-migration so an existing SQLite/Postgres database from the first version keeps working."""
    insp = inspect(engine)
    wanted = {"users": [("role", "VARCHAR(16) DEFAULT 'student'"), ("email_verified", "BOOLEAN DEFAULT FALSE")], "interviews": [("state", "JSON")]}
    with engine.begin() as c:
        for table, cols in wanted.items():
            have = {x["name"] for x in insp.get_columns(table)} if insp.has_table(table) else None
            if have is None:
                continue
            for name, ddl in cols:
                if name not in have:
                    c.execute(text(f"ALTER TABLE {table} ADD COLUMN {name} {ddl}"))


def init_db():
    _ensure_columns()
    Base.metadata.create_all(engine)
