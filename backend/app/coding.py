"""Coding round. For each problem the interviewer runs three phases:
   approach  -> candidate explains their plan by voice (scored)
   coding    -> candidate writes code in the editor, can run the sample tests and chat; submit runs ALL tests in the sandbox
   followup  -> interviewer reacts to the real test results and asks about time/space complexity and edge cases (scored)
Score per problem = 50% test results + 25% approach explanation + 25% complexity/edge-case discussion."""
import copy
import json
import random
import re
from collections import defaultdict
from . import interviewer, llm, questionbank as qb
from .db import Problem, SessionLocal, Submission, Turn

PROBLEMS_PER = {"short": 1, "standard": 2, "full": 3}
CODE_WEIGHTS = {"correctness": 0.50, "approach": 0.25, "complexity": 0.25}
CODING_LABELS = {"accuracy": "Code correctness", "relevance": "Approach", "completeness": "Complexity and edge cases", "clarity": "Explanation clarity"}

TEXT = {
    "en": {
        "intro_first": "Hello {name}, I'm {p}. Today is a coding round. {summary} The full problem is on your screen. Before you write any code, walk me through how you'd approach it.",
        "intro_next": "Alright, problem {i}. {summary} Same drill: tell me your approach first.",
        "restate": "Sure. {summary} The details are on your screen. How would you approach it?",
        "go_code": ["Sounds reasonable. Go ahead and code it. Run the sample tests whenever you like, and submit when you're happy.", "Okay, that works as a plan. Over to you: write it, try the samples, and submit when ready."],
        "nudge": "Okay. One thought: have you considered {hint}? Anyway, start coding and run the samples as you go.",
        "chat": ["Take your time. You can run the sample tests whenever you like.", "Sure, go on. I'm here if you want to talk it through."],
        "after_ok": "Nice, every test passed. Now, what's the time and space complexity of your solution, and which edge cases did you think about?",
        "after_partial": "Your solution passed {passed} of {total} tests. What's its time and space complexity, and which edge cases might be breaking it?",
        "after_fail": "Hmm, that didn't pass the tests. What's the time and space complexity of what you wrote, and what do you think went wrong?",
        "after_error": "It didn't compile or run properly. Walk me through what you intended, and what the complexity of that idea would be.",
        "restate_follow": "Of course. I asked: what's the time and space complexity of your solution, and which edge cases did you consider?",
        "good": ["Good, that's right.", "Nice, I like that explanation."], "meh": ["Okay, thanks for explaining.", "Alright, noted."],
        "skipped": "No problem, let's move on.",
        "closing": "Thank you {name}, that completes the coding round. I'm putting your report together now.",
    },
    "hing": {
        "intro_first": "Namaste {name}, main {p} hoon. Aaj coding round hai. {summary} Poora problem screen par hai. Code likhne se pehle batao, tum ise kaise solve karoge?",
        "intro_next": "Chalo, problem {i}. {summary} Pehle apna approach batao.",
        "restate": "Zaroor. {summary} Details screen par hain. Tum ise kaise approach karoge?",
        "go_code": ["Theek hai, approach sahi lag raha hai. Ab code likho, sample tests run karo, aur ready ho to submit karo.", "Okay, plan achha hai. Ab code likho aur samples par test karke submit karo."],
        "nudge": "Okay. Ek idea: kya tumne {hint} ke baare mein socha? Chalo, code likhna shuru karo.",
        "chat": ["Aaram se, tumhare paas time hai. Sample tests kabhi bhi run kar sakte ho.", "Haan bolo, main sun raha hoon."],
        "after_ok": "Badhiya, saare tests pass ho gaye. Ab batao, solution ki time aur space complexity kya hai, aur kaun se edge cases socha?",
        "after_partial": "{total} mein se {passed} tests pass hue. Time aur space complexity kya hai, aur kaun se edge cases fail ho sakte hain?",
        "after_fail": "Hmm, tests pass nahi hue. Jo likha usski time aur space complexity kya hai, aur tumhe kya galat lagta hai?",
        "after_error": "Code compile ya run nahi hua. Batao tumhara idea kya tha, aur uski complexity kya hogi?",
        "restate_follow": "Zaroor. Maine poocha tha: solution ki time aur space complexity kya hai, aur kaun se edge cases socha?",
        "good": ["Sahi hai, achha explain kiya.", "Badhiya, yeh correct hai."], "meh": ["Okay, samjhane ke liye thanks.", "Theek hai."],
        "skipped": "Koi baat nahi, aage badhte hain.",
        "closing": "Thank you {name}, coding round ho gaya. Main abhi tumhari report bana raha hoon.",
    },
    "hi": {
        "intro_first": "नमस्ते {name}, मैं {p} हूँ। आज कोडिंग राउंड है। {summary} पूरा प्रॉब्लम स्क्रीन पर है। कोड लिखने से पहले बताइए कि आप इसे कैसे हल करेंगे।",
        "intro_next": "चलिए, प्रॉब्लम {i}। {summary} पहले अपना अप्रोच बताइए।",
        "restate": "ज़रूर। {summary} विवरण स्क्रीन पर है। आप इसे कैसे हल करेंगे?",
        "go_code": ["ठीक है, अप्रोच सही लग रहा है। अब कोड लिखिए, सैंपल टेस्ट चलाइए और तैयार होने पर सबमिट कीजिए।"],
        "nudge": "ठीक है। एक सुझाव: क्या आपने {hint} के बारे में सोचा? चलिए, कोड लिखना शुरू कीजिए।",
        "chat": ["आराम से, आपके पास समय है। सैंपल टेस्ट कभी भी चला सकते हैं।"],
        "after_ok": "बढ़िया, सभी टेस्ट पास हो गए। अब बताइए, आपके सॉल्यूशन की टाइम और स्पेस कॉम्प्लेक्सिटी क्या है, और आपने कौन से एज केसेस सोचे?",
        "after_partial": "{total} में से {passed} टेस्ट पास हुए। टाइम और स्पेस कॉम्प्लेक्सिटी क्या है, और कौन से एज केस फेल हो सकते हैं?",
        "after_fail": "हम्म, टेस्ट पास नहीं हुए। आपने जो लिखा उसकी टाइम और स्पेस कॉम्प्लेक्सिटी क्या है, और आपको क्या गलत लगता है?",
        "after_error": "कोड कंपाइल या रन नहीं हुआ। बताइए आपका आइडिया क्या था और उसकी कॉम्प्लेक्सिटी क्या होगी?",
        "restate_follow": "ज़रूर। मैंने पूछा था: सॉल्यूशन की टाइम और स्पेस कॉम्प्लेक्सिटी क्या है, और कौन से एज केसेस सोचे?",
        "good": ["सही है, अच्छा समझाया।"], "meh": ["ठीक है, समझाने के लिए धन्यवाद।"],
        "skipped": "कोई बात नहीं, आगे बढ़ते हैं।",
        "closing": "धन्यवाद {name}, कोडिंग राउंड पूरा हुआ। मैं अभी आपकी रिपोर्ट बना रहा हूँ।",
    },
}


def T(config) -> dict:
    lang = config.get("language", "en-IN")
    return TEXT["hing" if lang == "hinglish" else "hi" if lang == "hi-IN" else "en"]


def _pick(lst, seed):
    return lst[seed % len(lst)]


# ---------------------------------------------------------------- setup
def pick_problems(db, config: dict, seed: str) -> list[str]:
    ids = [i for i in (config.get("problem_ids") or []) if db.get(Problem, i)]
    if ids:
        return ids
    n = PROBLEMS_PER.get(config.get("duration", "standard"), 2)
    rows = db.query(Problem).filter(Problem.active.is_(True)).all()
    rnd = random.Random(seed)
    order = {"beginner": ["easy", "medium"], "intermediate": ["easy", "medium"], "advanced": ["medium", "hard", "easy"]}[config.get("difficulty", "intermediate")]
    easy = [r for r in rows if r.difficulty == "easy"]; med = [r for r in rows if r.difficulty == "medium"]; hard = [r for r in rows if r.difficulty == "hard"]
    rnd.shuffle(easy); rnd.shuffle(med); rnd.shuffle(hard)
    pools = {"easy": easy, "medium": med, "hard": hard}
    if config.get("difficulty") == "beginner":
        seq = easy + med
    elif config.get("difficulty") == "advanced":
        seq = med + hard + easy
    else:
        seq = [x for pair in zip(easy, med) for x in pair] + easy[len(med):] + med[len(easy):]
    return [r.id for r in seq[:n]] or [r.id for r in rows[:n]]


async def opening(db, it, user_name: str) -> dict:
    ids = pick_problems(db, it.config, it.id)
    if not ids:
        raise ValueError("No coding problems are available.")
    it.state = {"problems": ids, "i": 0, "phase": "approach", "results": {}}
    p = db.get(Problem, ids[0])
    t = T(it.config)
    return {"reply": t["intro_first"].format(name=user_name, p=interviewer.persona_name(it.config), summary=p.summary), "topic": p.topic, "kind": "main",
            "candidate_turn_type": "answer", "meta": {"problem_id": p.id, "phase": "approach"}}


def current(db, it):
    st = it.state or {}
    if not st or st.get("i", 0) >= len(st.get("problems", [])):
        return None
    return db.get(Problem, st["problems"][st["i"]])


def view(db, it) -> dict:
    from .sandbox import public_problem
    st = it.state or {}
    p = current(db, it)
    res = st.get("results", {}).get(p.id, {}) if p else {}
    return {"phase": st.get("phase"), "index": st.get("i", 0), "total": len(st.get("problems", [])), "problem": public_problem(p) if p else None,
            "language": it.config.get("code_language", "python"), "submitted": bool(res.get("submitted")), "last_result": res.get("last_public")}


# ---------------------------------------------------------------- offline evaluation (used when no LLM is configured)
COMPLEXITY_SYNS = {
    "1": ["constant", "o(1)"], "n": ["o(n)", "linear", "order n", "order of n", "big o of n"], "log n": ["log n", "logn", "logarithmic"],
    "n + m": ["n+m", "n plus m", "m+n", "sum of the lengths", "linear"], "n log k": ["nlogk", "n log k", "n log of k"], "k": ["o(k)", "size k", "k elements", "heap size", "size of the heap"],
    "amount x coins": ["amount*coins", "amount times", "n*m", "m*n", "amount into", "amount x"], "rows x cols": ["rows*cols", "m*n", "n*m", "r*c", "number of cells", "size of the grid", "grid size", "rows times"],
}


def _norm(s: str) -> str:
    return re.sub(r"\s+", "", s.lower().replace("×", "x"))


def complexity_hit(expected: str, text: str) -> bool:
    expr = re.sub(r"^o\(|\)$", "", expected.strip().lower()).strip()
    cands = {_norm(expected), _norm(expr), *[_norm(x) for x in COMPLEXITY_SYNS.get(expr, [])]}
    flat = _norm(text)
    return any(c and c in flat for c in cands)


EDGE_RE = re.compile(r"edge|corner|empty|duplicate|negative|single|one element|only one|zero|overflow|all same|null|boundary|large input|smallest|largest|no solution|not found", re.I)


def offline_eval(problem, phase: str, text: str) -> dict:
    labels = [l for l, _ in problem.approach_keywords]
    model = f"{problem.summary} A strong approach: {', '.join(labels)}. Expected time {problem.expected_time}, space {problem.expected_space}."
    q = {"concepts": [(l, s) for l, s in problem.approach_keywords], "model": model, "topic": problem.topic}
    if phase == "approach":
        ev = qb.evaluate(q, text)
        ev["explanation"] = f"You covered {len(ev['correct_concepts'])} of {len(labels)} key ideas for this problem."
        return ev
    words = len(text.split())
    tok, sok, eok = complexity_hit(problem.expected_time, text), bool(re.search(r"space|memory|extra", text, re.I) and complexity_hit(problem.expected_space, text)), bool(EDGE_RE.search(text))
    scores = {"accuracy": 15 + 45 * tok + 25 * sok + 10 * eok if words >= 5 else 8, "relevance": 85 if (tok or sok or eok) else 30,
              "completeness": round(40 * eok + 35 * tok + 25 * sok) if words >= 5 else 5, "clarity": qb.evaluate(None, text)["scores"]["clarity"]}
    missing = ([] if tok else [f"time complexity ({problem.expected_time})"]) + ([] if sok else [f"space complexity ({problem.expected_space})"]) + ([] if eok else ["edge cases"])
    return {"scores": {k: min(100, v) for k, v in scores.items()}, "correct_concepts": ([f"time {problem.expected_time}"] if tok else []) + ([f"space {problem.expected_space}"] if sok else []) + (["edge cases"] if eok else []),
            "missing_concepts": missing, "inaccuracies": [], "explanation": "Keyword-based check against the expected complexity and edge-case discussion.",
            "improvements": [f"State the complexity precisely, for example time {problem.expected_time} and space {problem.expected_space}."] if missing else ["Good coverage."], "model_answer": f"Time {problem.expected_time}, space {problem.expected_space}. Mention edge cases such as empty or minimum-size input, duplicates and very large input.", "topic": problem.topic}


async def evaluate_turn(it, turn) -> dict:
    meta = turn.meta or {}
    with SessionLocal() as db:
        problem = db.get(Problem, meta.get("problem_id"))
    kind = "technical"
    if problem is None:
        return await interviewer.evaluate_answer(it, turn.question_ref or "", turn.text, turn.topic, None)
    ev = None
    if llm.provider() != "none":
        try:
            notes = (f"REFERENCE NOTES. Problem: {problem.title} ({problem.summary}). Expected time {problem.expected_time}, space {problem.expected_space}. "
                     f"Key ideas: {', '.join(l for l, _ in problem.approach_keywords)}. The candidate is explaining their {meta.get('phase')} out loud in a coding interview.")
            r = await llm.complete_json(interviewer.EVAL_SYSTEM.format(acc_label="Correctness of the reasoning"),
                                        [{"role": "user", "content": f"Language: {it.config.get('language')}\nQUESTION: {turn.question_ref}\nCANDIDATE ANSWER (transcript): {turn.text}\n{notes}"}], max_tokens=900, temperature=0.2)
            scores = {d: int(max(0, min(100, float(r["scores"][d])))) for d in interviewer.DIMENSIONS}
            ev = {"scores": scores, "correct_concepts": [str(x) for x in r.get("correct_concepts", [])][:8], "missing_concepts": [str(x) for x in r.get("missing_concepts", [])][:8],
                  "inaccuracies": [str(x) for x in r.get("inaccuracies", [])][:6], "explanation": str(r.get("explanation", "")), "improvements": [str(x) for x in r.get("improvements", [])][:4],
                  "model_answer": str(r.get("model_answer", "")), "topic": problem.topic, "engine": llm.engine_name()}
        except (llm.LLMUnavailable, KeyError, TypeError, ValueError):
            ev = None
    if ev is None:
        ev = offline_eval(problem, meta.get("phase", "approach"), turn.text)
        ev["engine"] = "offline-rule-based"
    ev["topic"] = problem.topic
    ev["overall"] = interviewer.overall_from(ev["scores"], kind)
    return ev


# ---------------------------------------------------------------- turn handling
def _advance(db, st: dict, it, name: str, react: str) -> dict:
    st["i"] += 1
    t = T(it.config)
    if st["i"] >= len(st["problems"]):
        st["phase"] = "done"
        return {"reply": f"{react} {t['closing'].format(name=name)}".strip(), "topic": "Wrap up", "kind": "closing", "done": True, "meta": None}
    st["phase"] = "approach"
    p = db.get(Problem, st["problems"][st["i"]])
    return {"reply": f"{react} {t['intro_next'].format(i=st['i'] + 1, summary=p.summary)}".strip(), "topic": p.topic, "kind": "main", "done": False, "meta": {"problem_id": p.id, "phase": "approach"}}


async def handle_answer(db, it, cand, user_name: str, answers_done: int) -> dict:
    st = copy.deepcopy(it.state)
    problem = current(db, it)
    phase, t, seed = st["phase"], T(it.config), len(it.turns)
    ctt = qb.detect_turn_type(cand.text)
    cand.meta = {**(cand.meta or {}), "problem_id": problem.id, "phase": phase}
    out = {"candidate_turn_type": ctt, "done": False, "kind": "main", "topic": problem.topic, "meta": {"problem_id": problem.id, "phase": phase}}
    if ctt == "skip":
        st["results"].setdefault(problem.id, {})["skipped"] = True
        r = _advance(db, st, it, user_name, t["skipped"])
        out.update(r)
    elif phase == "approach":
        if ctt == "clarification":
            out.update(reply=t["restate"].format(summary=problem.summary), kind="clarify")
        else:
            cand.kind = "answer"
            ev = offline_eval(problem, "approach", cand.text)
            missing = [l for l, _ in problem.approach_keywords if l in ev["missing_concepts"]]
            st["phase"] = "coding"
            if not ev["correct_concepts"] and missing and len(cand.text.split()) >= 4:
                out.update(reply=t["nudge"].format(hint=missing[0]), kind="main")
            else:
                out.update(reply=_pick(t["go_code"], seed), kind="main")
            out["meta"] = {"problem_id": problem.id, "phase": "coding"}
    elif phase == "coding":
        out.update(reply=await _chat_reply(it, problem, cand.text, t, seed), kind="clarify", candidate_turn_type="clarification")
        out["meta"] = {"problem_id": problem.id, "phase": "coding"}
    else:  # followup
        if ctt == "clarification":
            out.update(reply=t["restate_follow"], kind="clarify")
        else:
            cand.kind = "answer"
            ev = offline_eval(problem, "followup", cand.text)
            good = ev["scores"]["accuracy"] >= 60
            r = _advance(db, st, it, user_name, _pick(t["good"] if good else t["meh"], seed))
            out.update(r)
    it.state = st
    return out


async def _chat_reply(it, problem, text, t, seed) -> str:
    if llm.provider() != "none":
        try:
            r = await llm.complete_json(
                f"You are {interviewer.persona_name(it.config)}, a coding interviewer on a live call. The candidate is solving '{problem.title}' ({problem.summary}) and just said something while coding. "
                f"Answer in 1-2 short spoken sentences. You may clarify the problem statement, input format or constraints. NEVER give the algorithm, code or the answer; if asked for it, say you would like to see them try first and offer a tiny nudge. {interviewer.lang_rule(it.config.get('language', 'en-IN'))} "
                'Return ONLY JSON: {"reply": "..."}', [{"role": "user", "content": text}], max_tokens=200, temperature=0.5)
            if r.get("reply"):
                return re.sub(r"[*_`#]+", "", str(r["reply"])).strip()
        except llm.LLMUnavailable:
            pass
    return _pick(t["chat"], seed)


def after_submit_reply(it, result: dict, seed: int) -> str:
    t = T(it.config)
    if result["status"] == "accepted":
        return t["after_ok"]
    if result["status"] in ("compile_error",):
        return t["after_error"]
    if result["passed"] == 0:
        return t["after_fail"] if result["status"] == "wrong_answer" else t["after_error"]
    return t["after_partial"].format(passed=result["passed"], total=result["total"])


def record_submission(db, it, problem, language: str, code: str, result: dict, kind: str, user_id: int) -> Submission:
    sub = Submission(user_id=user_id, interview_id=it.id if it else None, problem_id=problem.id, language=language, code=code, kind=kind,
                     passed=result["passed"], total=result["total"], status=result["status"], results=result["tests"])
    db.add(sub)
    return sub


# ---------------------------------------------------------------- report
def _best_submit(db, interview_id: str, pid: str):
    subs = db.query(Submission).filter(Submission.interview_id == interview_id, Submission.problem_id == pid, Submission.kind == "submit").all()
    return max(subs, key=lambda s: (s.passed / max(1, s.total), s.id)) if subs else None


async def build_report(it, user_name: str) -> dict:
    st = it.state or {"problems": [], "i": 0}
    with SessionLocal() as db:
        probs = []
        runs = defaultdict(int)
        for (pid,) in db.query(Submission.problem_id).filter(Submission.interview_id == it.id, Submission.kind == "run").all():
            runs[pid] += 1
        reached = st["problems"][: min(len(st["problems"]), st.get("i", 0) + (1 if st.get("phase") != "done" else 0))]
        for pid in reached:
            p = db.get(Problem, pid)
            sub = _best_submit(db, it.id, pid)
            turns = [t for t in it.turns if t.role == "candidate" and t.kind == "answer" and (t.meta or {}).get("problem_id") == pid and t.evaluation]
            appr = next((t.evaluation for t in turns if t.meta.get("phase") == "approach"), None)
            comp = next((t.evaluation for t in turns if t.meta.get("phase") == "followup"), None)
            if st.get("results", {}).get(pid, {}).get("skipped") and not sub and not appr:
                probs.append({"id": pid, "title": p.title, "topic": p.topic, "difficulty": p.difficulty, "skipped": True})
                continue
            if not sub and not appr and not comp and not runs.get(pid):
                continue
            correctness = round(100 * sub.passed / max(1, sub.total)) if sub else 0
            parts = {"correctness": correctness}
            if appr: parts["approach"] = appr["overall"]
            if comp: parts["complexity"] = comp["overall"]
            wsum = sum(CODE_WEIGHTS[k] for k in parts)
            overall = round(sum(parts[k] * CODE_WEIGHTS[k] for k in parts) / wsum)
            probs.append({"id": pid, "title": p.title, "topic": p.topic, "difficulty": p.difficulty, "skipped": False, "submitted": bool(sub), "status": sub.status if sub else "not_submitted",
                          "passed": sub.passed if sub else 0, "total": sub.total if sub else len(p.tests), "language": sub.language if sub else None, "code": sub.code if sub else None,
                          "runs": runs.get(pid, 0), "overall": overall, "correctness": correctness, "approach": appr, "complexity": comp,
                          "expected_time": p.expected_time, "expected_space": p.expected_space,
                          "hidden_failed": sum(1 for r in (sub.results or []) if r.get("hidden") and r["status"] != "pass") if sub else 0})
    done = [p for p in probs if not p.get("skipped")]
    avg = lambda xs: round(sum(xs) / len(xs)) if xs else 0
    dims = {"accuracy": avg([p["correctness"] for p in done]), "relevance": avg([p["approach"]["overall"] for p in done if p.get("approach")]),
            "completeness": avg([p["complexity"]["overall"] for p in done if p.get("complexity")]),
            "clarity": avg([e["scores"]["clarity"] for p in done for e in (p.get("approach"), p.get("complexity")) if e])}
    overall = avg([p["overall"] for p in done])
    topics = sorted(({"topic": p["topic"], "score": p["overall"], "count": 1} for p in done), key=lambda x: x["score"])
    weak = [(x["topic"], x["score"]) for x in topics if x["score"] < 70]
    strengths, improvements = [], []
    for p in done:
        if p["status"] == "accepted":
            strengths.append(f"Solved {p['title']} with every test passing.")
        elif p["submitted"]:
            improvements.append(f"{p['title']}: {p['passed']} of {p['total']} tests passed" + (f", including {p['hidden_failed']} hidden edge cases." if p["hidden_failed"] else "."))
        else:
            improvements.append(f"{p['title']}: no solution was submitted.")
        if p.get("complexity") and p["complexity"]["overall"] < 60:
            improvements.append(f"Practise stating complexity out loud for {p['title']} (expected time {p['expected_time']}, space {p['expected_space']}).")
        if p.get("approach") and p["approach"]["overall"] >= 75:
            strengths.append(f"Explained the approach for {p['title']} clearly before coding.")
    report = {"kind": "coding", "overall": overall, "dimensions": dims, "dimension_labels": CODING_LABELS, "topics": topics, "answered": len(done), "skipped": len(probs) - len(done),
              "problems": probs, "headline": ("Strong coding round." if overall >= 75 else "A decent attempt with clear things to fix." if overall >= 50 else "Keep practising: the fundamentals will come with repetition.") if done else "No solutions were attempted.",
              "strengths": strengths[:4], "improvements": improvements[:5], "study_plan": interviewer._study_plan(weak), "engine": it.engine,
              "disclaimer": "Test results are exact. Explanation scores are estimates from an AI system, not an objective measure of your ability."}
    return report
