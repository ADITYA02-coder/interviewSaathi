"""The AI interviewer: conversation turns, per-answer evaluation and the final report."""
import json
import re
from collections import defaultdict
from . import llm, questionbank as qb

DURATION_QUESTIONS = {"short": 4, "standard": 7, "full": 12}
DIMENSIONS = ["accuracy", "relevance", "completeness", "clarity"]
WEIGHTS = {
    "technical": {"accuracy": .35, "relevance": .25, "completeness": .20, "clarity": .20},
    "soft": {"accuracy": .30, "relevance": .30, "completeness": .20, "clarity": .20},
}
LABELS = {
    "technical": {"accuracy": "Technical accuracy", "relevance": "Relevance", "completeness": "Completeness", "clarity": "Clarity and structure"},
    "soft": {"accuracy": "Specificity and examples", "relevance": "Relevance", "completeness": "Structure (e.g. STAR)", "clarity": "Clarity"},
}

LANG_RULES = {
    "en-IN": "Speak clear, natural Indian English.",
    "hi-IN": "Speak natural Hindi in Devanagari script, keeping technical terms (inheritance, API, database...) in English words.",
    "hinglish": "Speak Hinglish: Hindi and English mixed the way educated Indians talk, written ONLY in Roman script. Never use Devanagari.",
}


def lang_rule(code: str) -> str:
    return LANG_RULES.get(code) or f"Speak in the language with BCP-47 code {code}, written in its native script, keeping technical terms in English."


def persona_name(config: dict) -> str:
    return "Arjun" if config.get("interviewer") == "male" else "Ananya"


def total_questions(config: dict) -> int:
    return DURATION_QUESTIONS.get(config.get("duration", "standard"), 7)


def kind_of(config: dict) -> str:
    return "technical" if config.get("interview_type", "technical") in ("technical", "project", "mixed") else "soft"


def system_prompt(interview, user_name: str, final: bool = False) -> str:
    c = interview.config
    n = total_questions(c)
    ctx = ""
    if interview.resume_text.strip():
        ctx += f"\nCANDIDATE RESUME (use it to personalise questions; ask about listed projects and skills):\n{interview.resume_text[:5000]}\n"
    if interview.jd_text.strip():
        ctx += f"\nTARGET JOB DESCRIPTION (tailor questions to these requirements):\n{interview.jd_text[:4000]}\n"
    pool = qb.pool_texts(c)
    if pool and c.get("interview_type") != "project":
        ctx += "\nCURATED QUESTION POOL from the placement team (prefer these when they fit, adapt the wording, never read numbers or labels):\n- " + "\n- ".join(pool) + "\n"
    if c.get("focus_note"):
        ctx += f"\nASSIGNED FOCUS from the placement team: {c['focus_note']}\n"
    types = {
        "technical": "technical concepts for the role, from fundamentals upward",
        "hr": "HR questions: introduction, strengths and weaknesses, motivation, goals, teamwork",
        "behavioral": "behavioural questions; nudge the candidate to answer in STAR form (situation, task, action, result)",
        "project": "the candidate's own projects: architecture, technology choices, trade-offs, debugging, their personal contribution",
        "mixed": "a realistic mix: technical, project/resume, HR and behavioural questions in a logical order",
    }
    return f"""You are {persona_name(c)}, a warm, sharp, professional interviewer on a live video call with a candidate named {user_name}.
Role being interviewed for: {c.get('role', 'General')} | Level: {c.get('experience', 'fresher')} | Difficulty: {c.get('difficulty', 'intermediate')}
Interview focus: {types.get(c.get('interview_type', 'technical'))}.
The interview has {n} candidate answers in total. {lang_rule(c.get('language', 'en-IN'))}
{ctx}
Everything you write is converted to speech, so write for the ear:
- 1 to 3 short sentences, under 45 words. Sound like a real person, never like a script.
- Begin with a brief, varied human reaction to what they just said ("Right, that makes sense.", "Hmm, okay.", "Good, I like that you mentioned..."), never the same opener twice, then ask exactly ONE question.
- No markdown, lists, emojis, code or symbols. Say "big O of n", "C plus plus", "dot net".
- Never reveal scores or the full correct answer during the interview. If they are wrong or stuck, give a small hint or gently move on.
- Ask one question at a time, do not repeat topics or questions already asked, and move between topics logically. Follow up on weak or interesting answers once, then move on.
- Do not penalise accent, grammar or speech-recognition glitches; assume the transcript may contain recognition errors and infer the intended technical term.
- If the candidate asks you to repeat or clarify, do so briefly in different words. If they say they don't know or want to skip, be kind and move on.
{"- THIS IS THE FINAL TURN: react briefly to their last answer, thank them warmly by name, say the report is being prepared, and ask NO new question. Use kind \"closing\"." if final else ""}

Reply with ONLY a JSON object, no other text:
{{"reply": "<what you say aloud>", "topic": "<2-3 word label of the topic of the question you ask>", "kind": "main|followup|clarify|closing", "candidate_turn_type": "answer|clarification|skip"}}
candidate_turn_type describes the candidate's LAST message ("answer" if they attempted to answer, "clarification" if they asked you to repeat/explain the question, "skip" if they declined). For the opening turn use "answer"."""


def _history_messages(turns, limit=28) -> list[dict]:
    msgs = [{"role": "user", "content": "[The call has just connected. Start the interview.]"}]
    for t in turns[-limit:]:
        if t.role == "interviewer":
            msgs.append({"role": "assistant", "content": json.dumps({"reply": t.text, "topic": t.topic, "kind": t.kind or "main", "candidate_turn_type": "answer"}, ensure_ascii=False)})
        else:
            msgs.append({"role": "user", "content": t.text})
    return msgs


def _clean_reply(r: dict, fallback_topic: str = "General") -> dict:
    reply = re.sub(r"[*_`#]+", "", str(r.get("reply", ""))).strip()
    if not reply:
        raise llm.LLMUnavailable("empty reply")
    kind = r.get("kind") if r.get("kind") in ("main", "followup", "clarify", "closing") else "main"
    ctt = r.get("candidate_turn_type") if r.get("candidate_turn_type") in ("answer", "clarification", "skip") else "answer"
    return {"reply": reply, "topic": str(r.get("topic") or fallback_topic)[:60], "kind": kind, "candidate_turn_type": ctt}


# ---------------------------------------------------------------- offline engine
OPENERS = ["Okay, thanks for that.", "Right, I see.", "Alright, good.", "Got it.", "Okay, let's move on.", "Thank you, that's helpful."]
GOOD = ["Good, that covers the main idea.", "Nice, that's a solid explanation.", "Right, you've hit the key points."]
MID = ["Okay, you've touched on some of the important points.", "Fair enough, that's a decent start."]
LOW = ["No worries, that's a tricky one.", "That's okay, let's try something different."]
HINTS = {"en-IN": "I'm {p}. We'll do a {t} interview for the {r} role, one question at a time, so just speak naturally. Let's begin.",
         "hi-IN": "मैं {p} हूँ। हम {r} रोल के लिए एक इंटरव्यू करेंगे, एक बार में एक सवाल। आराम से बोलिए। शुरू करते हैं।",
         "hinglish": "Main {p} hoon. Hum {r} role ke liye interview karenge, ek time par ek question. Aaram se boliye. Chaliye shuru karte hain."}


def _offline_pick(interview, turns) -> tuple[dict, dict]:
    """Returns (question dict, meta). Chooses a follow-up once if the last answer was partial."""
    qs = qb.question_list(interview.config, interview.id)
    asked = {t.text for t in turns if t.role == "interviewer"}
    for q in qs:
        if q["q"] not in asked:
            return q, {"bank_q": q["q"]}
    return qs[len(turns) % len(qs)], {"bank_q": qs[0]["q"]}


async def opening(interview, user_name: str) -> dict:
    c = interview.config
    try:
        r = _clean_reply(await llm.complete_json(system_prompt(interview, user_name), _history_messages([]), max_tokens=400))
        return {**r, "meta": None}
    except llm.LLMUnavailable:
        q, meta = _offline_pick(interview, [])
        lang = c.get("language", "en-IN")
        itype = c.get("interview_type", "technical").replace("_", " ")
        hello = {"hi-IN": f"नमस्ते {user_name}! ", "hinglish": f"Namaste {user_name}! "}.get(lang, f"Hello {user_name}, welcome! ")
        intro = HINTS.get(lang, HINTS["en-IN"]).format(p=persona_name(c), t=itype, r=c.get("role", "general"))
        return {"reply": f"{hello}{intro} {q['q']}", "topic": q["topic"], "kind": "main", "candidate_turn_type": "answer", "meta": meta}


async def next_turn(interview, turns, user_name: str, answers_done: int) -> dict:
    """turns already include the candidate's newest message. answers_done counts answers/skips INCLUDING this one if it is one."""
    c = interview.config
    n = total_questions(c)
    last = turns[-1].text
    final_guess = answers_done + (0 if qb.detect_turn_type(last) == "clarification" else 1) >= n
    try:
        r = _clean_reply(await llm.complete_json(system_prompt(interview, user_name, final=final_guess), _history_messages(turns), max_tokens=400))
        counted = r["candidate_turn_type"] in ("answer", "skip")
        done = (answers_done + (1 if counted else 0)) >= n
        if done and r["kind"] != "closing":
            # the model asked a new question although we reached the limit: regenerate as a closing
            r = _clean_reply(await llm.complete_json(system_prompt(interview, user_name, final=True), _history_messages(turns), max_tokens=300))
        r["done"] = done
        r["meta"] = None
        return r
    except llm.LLMUnavailable:
        return _offline_next(interview, turns, user_name, answers_done, n)


def _offline_next(interview, turns, user_name, answers_done, n) -> dict:
    c = interview.config
    last = turns[-1]
    ctt = qb.detect_turn_type(last.text)
    prev_q = next((t for t in reversed(turns[:-1]) if t.role == "interviewer"), None)
    if ctt == "clarification" and prev_q:
        return {"reply": f"Sure. Let me put it another way. {prev_q.text}", "topic": prev_q.topic, "kind": "clarify", "candidate_turn_type": ctt, "done": False, "meta": prev_q.meta}
    counted = answers_done + 1
    if counted >= n:
        return {"reply": f"Thank you {user_name}, that brings us to the end of the interview. I'm preparing your feedback report now.", "topic": "Wrap up", "kind": "closing", "candidate_turn_type": ctt, "done": True, "meta": None}
    bank_q = qb.find_question((prev_q.meta or {}).get("bank_q", "")) if prev_q else None
    ev = qb.evaluate(bank_q, last.text) if ctt == "answer" else None
    cov = (len(ev["correct_concepts"]) / max(1, len(bank_q["concepts"]))) if (ev and bank_q) else 0
    used_followup = bool(prev_q and (prev_q.meta or {}).get("followup"))
    if ctt == "answer" and bank_q and 0.25 <= cov <= 0.75 and not used_followup and prev_q.kind == "main":
        return {"reply": f"{MID[answers_done % len(MID)]} {bank_q['followup']}", "topic": bank_q["topic"], "kind": "followup", "candidate_turn_type": ctt, "done": False, "meta": {"bank_q": bank_q["q"], "followup": True}}
    q, meta = _offline_pick(interview, turns)
    react = (GOOD if cov > 0.75 else MID if cov >= 0.25 else LOW)[answers_done % 2] if ctt == "answer" and bank_q else OPENERS[answers_done % len(OPENERS)]
    if ctt == "skip":
        react = "No problem, let's move on."
    return {"reply": f"{react} {q['q']}", "topic": q["topic"], "kind": "main", "candidate_turn_type": ctt, "done": False, "meta": meta}


# ---------------------------------------------------------------- evaluation
def overall_from(scores: dict, kind: str) -> int:
    w = WEIGHTS[kind]
    return round(sum(max(0, min(100, float(scores.get(d, 0)))) * w[d] for d in DIMENSIONS))


EVAL_SYSTEM = """You are a rigorous but fair interview evaluator. Score ONE spoken answer given in a mock interview.
Dimensions, each 0-100: accuracy ({acc_label}), relevance (does it answer the actual question), completeness (covers the important points), clarity (organised, understandable).
Anchors: 90+ expert and complete; 70-89 solid with minor gaps; 50-69 partially correct or incomplete; 30-49 major gaps or errors; under 30 wrong, off-topic or empty.
Rules:
- Technical correctness and relevance matter far more than length or polish. Never reward an answer for being long or for sophisticated English.
- Do NOT penalise accent, grammar, Hinglish, or speech-recognition mistakes (the text is an automatic transcript). Judge the ideas.
- Be specific and concrete; never invent facts. If the answer is a skip or empty, give low scores.
Return ONLY JSON:
{{"scores": {{"accuracy": n, "relevance": n, "completeness": n, "clarity": n}}, "correct_concepts": ["..."], "missing_concepts": ["..."], "inaccuracies": ["..."], "explanation": "1-2 sentences on why this score", "improvements": ["2-3 specific, actionable tips"], "model_answer": "one possible strong answer in 2-5 sentences, in the interview language", "topic": "2-3 word topic"}}"""


async def evaluate_answer(interview, question: str, answer: str, topic_hint: str, bank_ref: str | None) -> dict:
    kind = kind_of(interview.config)
    try:
        sys = EVAL_SYSTEM.format(acc_label=LABELS[kind]["accuracy"])
        prompt = (f"Role: {interview.config.get('role')} | Level: {interview.config.get('experience')} | Difficulty: {interview.config.get('difficulty')} | "
                  f"Interview type: {interview.config.get('interview_type')} | Language: {interview.config.get('language')}\n"
                  f"QUESTION: {question}\nCANDIDATE ANSWER (transcript): {answer}")
        r = await llm.complete_json(sys, [{"role": "user", "content": prompt}], max_tokens=900, temperature=0.2)
        scores = {d: int(max(0, min(100, float(r["scores"][d])))) for d in DIMENSIONS}
        ev = {
            "scores": scores,
            "correct_concepts": [str(x) for x in r.get("correct_concepts", [])][:8],
            "missing_concepts": [str(x) for x in r.get("missing_concepts", [])][:8],
            "inaccuracies": [str(x) for x in r.get("inaccuracies", [])][:6],
            "explanation": str(r.get("explanation", "")),
            "improvements": [str(x) for x in r.get("improvements", [])][:4],
            "model_answer": str(r.get("model_answer", "")),
            "topic": str(r.get("topic") or topic_hint or "General")[:60],
            "engine": llm.engine_name(),
        }
    except (llm.LLMUnavailable, KeyError, TypeError, ValueError):
        ev = qb.evaluate(qb.find_question(bank_ref or "") or qb.find_question(question), answer)
        ev["topic"] = ev.get("topic") if ev.get("topic") != "General" else (topic_hint or "General")
        ev["engine"] = "offline-rule-based"
    ev["overall"] = overall_from(ev["scores"], kind)
    return ev


# ---------------------------------------------------------------- report
def _study_plan(weak: list[tuple[str, float]]) -> list[dict]:
    plan = []
    for i, (topic, score) in enumerate(weak[:4]):
        plan.append({
            "topic": topic, "urgency": "high" if score < 50 else "medium",
            "why": f"Your average on {topic} was {round(score)}/100.",
            "actions": [f"Review the core concepts of {topic}.", f"Practise three {topic} questions out loud.", f"Retry the {topic} questions you found hard in a new mock interview."],
        })
    return plan


async def build_report(interview, user_name: str) -> dict:
    if interview.config.get("interview_type") == "coding":
        from . import coding
        return await coding.build_report(interview, user_name)
    kind = kind_of(interview.config)
    cands = [t for t in interview.turns if t.role == "candidate" and t.kind == "answer" and t.evaluation]
    skipped = [t for t in interview.turns if t.role == "candidate" and t.kind == "skip"]
    dims = {d: round(sum(t.evaluation["scores"][d] for t in cands) / len(cands)) if cands else 0 for d in DIMENSIONS}
    overall = round(sum(t.evaluation["overall"] for t in cands) / len(cands)) if cands else 0
    by_topic = defaultdict(list)
    for t in cands:
        by_topic[t.evaluation.get("topic", "General")].append(t.evaluation["overall"])
    topics = sorted(({"topic": k, "score": round(sum(v) / len(v)), "count": len(v)} for k, v in by_topic.items()), key=lambda x: x["score"])
    weak = [(x["topic"], x["score"]) for x in topics if x["score"] < 70]
    strong = [x for x in reversed(topics) if x["score"] >= 70]
    report = {
        "overall": overall, "dimensions": dims, "dimension_labels": LABELS[kind], "topics": topics,
        "answered": len(cands), "skipped": len(skipped),
        "headline": "", "strengths": [f"Strong on {x['topic']} ({x['score']}/100)." for x in strong[:3]],
        "improvements": [f"Work on {t} (average {round(s)}/100)." for t, s in weak[:3]],
        "study_plan": _study_plan(weak),
        "engine": interview.engine,
        "disclaimer": "Scores are estimates from an AI system, not an objective measure of your ability.",
    }
    report["headline"] = ("Strong performance." if overall >= 75 else "A solid base with clear room to grow." if overall >= 55 else "Good start. Focused practice will lift this quickly.") if cands else "No answers were scored."
    if cands and llm.provider() != "none":
        try:
            summary_in = [{"q": t.question_ref, "overall": t.evaluation["overall"], "topic": t.evaluation.get("topic"),
                           "missing": t.evaluation.get("missing_concepts"), "correct": t.evaluation.get("correct_concepts")} for t in cands]
            r = await llm.complete_json(
                "You are a supportive interview coach. From the per-answer results write a short summary for the candidate. Be specific, honest and encouraging. "
                'Return ONLY JSON: {"headline": "one sentence", "strengths": ["up to 3"], "improvements": ["up to 3"], '
                '"study_plan": [{"topic": "...", "urgency": "high|medium|low", "why": "...", "actions": ["2-3 concrete steps"]}]}',
                [{"role": "user", "content": f"Candidate: {user_name}. Role: {interview.config.get('role')}. Overall: {overall}.\nResults: {json.dumps(summary_in, ensure_ascii=False)}"}],
                max_tokens=900, temperature=0.4)
            for k in ("headline", "strengths", "improvements", "study_plan"):
                if r.get(k):
                    report[k] = r[k]
        except llm.LLMUnavailable:
            pass
    return report
