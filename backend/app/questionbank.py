"""Offline question bank + keyword evaluator (used when no LLM is configured or the LLM call fails)."""
import random
import re

# Each question: q, topic, level, concepts [(label, [synonyms...])], followup, model
def Q(q, topic, level, concepts, followup, model):
    return {"q": q, "topic": topic, "level": level, "concepts": concepts, "followup": followup, "model": model}

BANK = {
    "java": [
        Q("Explain the difference between an interface and an abstract class in Java.", "OOP", 1,
          [("interface is a contract", ["contract", "implement", "abstract methods"]), ("abstract class can hold state", ["state", "fields", "instance variable", "constructor"]),
           ("multiple interfaces allowed", ["multiple", "more than one"]), ("single inheritance for classes", ["extends", "single inheritance"])],
          "Can a Java class implement multiple interfaces? How is that different from extending classes?",
          "An interface defines a contract that classes implement, and a class can implement many interfaces. An abstract class can hold state and shared implementation, but a class can extend only one."),
        Q("What is the difference between ArrayList and LinkedList, and when would you pick each?", "Collections", 1,
          [("ArrayList uses a dynamic array", ["array", "dynamic array", "resizable"]), ("LinkedList uses nodes", ["node", "doubly", "linked"]),
           ("random access cost", ["random access", "index", "o(1)", "constant"]), ("insertion and deletion cost", ["insert", "delete", "remove", "o(n)"])],
          "What happens to an ArrayList when it runs out of capacity?",
          "ArrayList is backed by a resizable array, so index access is constant time but middle insertions shift elements. LinkedList uses doubly linked nodes, so insertion at a known node is cheap but access by index is linear."),
        Q("How does HashMap work internally in Java?", "Collections", 2,
          [("hashing of the key", ["hash", "hashcode"]), ("buckets", ["bucket", "array of"]), ("equals for collisions", ["equals", "collision"]),
           ("linked list or tree in a bucket", ["linked list", "tree", "treeify", "red-black"]), ("resizing and load factor", ["load factor", "resize", "rehash"])],
          "What is the contract between equals and hashCode?",
          "HashMap hashes the key to pick a bucket in an array. Collisions are stored as a list, converted to a tree when long, and equals decides the exact match. When the load factor is exceeded the table resizes and rehashes."),
        Q("What is the difference between checked and unchecked exceptions?", "Exception handling", 1,
          [("checked are verified at compile time", ["compile", "must handle", "declare", "throws"]), ("unchecked extend RuntimeException", ["runtimeexception", "runtime"]),
           ("examples", ["ioexception", "nullpointer", "sqlexception", "arithmetic"]), ("try catch finally", ["try", "catch", "finally"])],
          "When would you create your own custom exception?",
          "Checked exceptions such as IOException must be caught or declared, so the compiler enforces handling. Unchecked exceptions extend RuntimeException and usually signal programming errors."),
        Q("Explain method overloading and method overriding.", "OOP", 1,
          [("overloading same name different parameters", ["same name", "different parameter", "signature"]), ("overloading is compile time", ["compile time", "static"]),
           ("overriding in subclass", ["subclass", "child", "parent", "superclass"]), ("overriding is runtime polymorphism", ["runtime", "dynamic", "polymorphism"])],
          "Can we override a static method? Why or why not?",
          "Overloading uses the same method name with different parameters and is resolved at compile time. Overriding redefines a parent method in a subclass and enables runtime polymorphism."),
        Q("What is the difference between String, StringBuilder and StringBuffer?", "Strings", 1,
          [("String is immutable", ["immutable"]), ("StringBuilder is mutable", ["mutable"]), ("StringBuffer is thread safe", ["thread", "synchronized"]),
           ("string pool", ["pool", "intern"])],
          "Why is String immutable in Java?",
          "String is immutable and pooled, StringBuilder is mutable and fast but not thread safe, and StringBuffer is mutable and synchronized."),
        Q("Explain how multithreading works in Java and how you can create a thread.", "Concurrency", 2,
          [("Thread class or Runnable", ["runnable", "extends thread", "thread class"]), ("start vs run", ["start", "run method"]),
           ("synchronization", ["synchronized", "lock", "race condition"]), ("executor service", ["executor", "thread pool"])],
          "What is a race condition and how do you prevent it?",
          "You create threads by extending Thread or implementing Runnable and calling start. Shared state needs synchronization, locks or atomics, and thread pools through ExecutorService are preferred in production."),
        Q("What are the main features of Java 8 that you have used?", "Modern Java", 2,
          [("lambda expressions", ["lambda"]), ("streams", ["stream"]), ("functional interfaces", ["functional interface", "predicate", "function"]), ("Optional", ["optional"])],
          "What is the difference between map and flatMap in streams?",
          "Java 8 added lambdas, the Streams API, functional interfaces, Optional and default methods, which make collection processing declarative."),
    ],
    "python": [
        Q("What is the difference between a list and a tuple in Python?", "Data structures", 1,
          [("list is mutable", ["mutable", "change", "modify"]), ("tuple is immutable", ["immutable"]), ("tuple is hashable", ["hash", "dictionary key"]), ("use cases", ["fixed", "record", "performance"])],
          "Can you use a list as a dictionary key? Why not?",
          "Lists are mutable and tuples are immutable, so tuples can be dictionary keys and are used for fixed records."),
        Q("Explain how decorators work in Python.", "Functions", 2,
          [("function that wraps another", ["wrap", "takes a function", "higher order"]), ("returns a new function", ["returns", "inner function", "closure"]),
           ("@ syntax", ["@", "syntax sugar"]), ("use cases", ["logging", "timing", "auth", "cache"])],
          "How would you write a decorator that measures execution time?",
          "A decorator is a function that takes a function and returns a wrapped one, usually via a closure. The @ syntax is sugar for reassigning the function."),
        Q("What is the Global Interpreter Lock and how does it affect multithreading?", "Concurrency", 3,
          [("GIL allows one thread at a time", ["one thread", "single thread", "mutex", "lock"]), ("CPU bound limited", ["cpu bound", "cpu-bound"]),
           ("IO bound fine", ["io bound", "i/o", "network"]), ("multiprocessing", ["multiprocessing", "processes"])],
          "When would you choose multiprocessing over threading?",
          "The GIL lets only one thread execute Python bytecode at a time, so CPU-bound work needs multiprocessing, while I/O-bound work still benefits from threads or asyncio."),
        Q("What are generators and why would you use them?", "Functions", 2,
          [("yield keyword", ["yield"]), ("lazy evaluation", ["lazy", "one at a time", "on demand"]), ("memory efficiency", ["memory"]), ("iterator protocol", ["iterator", "next"])],
          "What is the difference between a generator and a list comprehension?",
          "Generators use yield to produce values lazily, which saves memory for large or infinite sequences."),
        Q("How does Python manage memory?", "Internals", 3,
          [("reference counting", ["reference count"]), ("garbage collector for cycles", ["garbage", "cycle", "gc"]), ("private heap", ["heap"]), ("mutable default args or object identity", ["id", "identity"])],
          "What problem can circular references cause?",
          "CPython uses reference counting plus a cyclic garbage collector on a private heap."),
        Q("Explain the difference between deep copy and shallow copy.", "Data structures", 2,
          [("shallow copies references", ["reference", "same objects"]), ("deep copies recursively", ["recursive", "independent", "new objects"]), ("copy module", ["copy.copy", "deepcopy", "copy module"]), ("nested objects", ["nested"])],
          "What would happen if you shallow-copy a list of lists and modify an inner list?",
          "A shallow copy duplicates the container but shares inner objects, while deepcopy recursively duplicates everything."),
        Q("What is the difference between is and == in Python?", "Basics", 1,
          [("== compares values", ["value", "equality"]), ("is compares identity", ["identity", "same object", "memory"]), ("small integer or string caching", ["cache", "interning", "interned"]), ("None check with is", ["none"])],
          "Why do we write `x is None` instead of `x == None`?",
          "== compares values, is compares object identity, and None checks should use is."),
    ],
    "mern": [
        Q("Explain the request flow in a MERN application when a user logs in.", "Full stack", 1,
          [("React sends request", ["react", "axios", "fetch"]), ("Express route and controller", ["express", "route", "controller"]), ("MongoDB lookup", ["mongodb", "mongoose", "database", "find"]),
           ("password hashing", ["bcrypt", "hash"]), ("JWT or session", ["jwt", "token", "session", "cookie"])],
          "Where would you store the token on the client and what are the security trade-offs?",
          "React posts credentials to an Express route, which finds the user in MongoDB, compares the bcrypt hash, issues a JWT or session, and React stores it and uses it on later requests."),
        Q("What is the virtual DOM and how does React use it?", "React", 1,
          [("in-memory representation", ["in-memory", "copy", "representation", "lightweight"]), ("diffing", ["diff", "compare", "reconciliation"]), ("batch updates real DOM", ["batch", "minimal", "update the real dom", "efficient"])],
          "How do keys help React when rendering lists?",
          "React keeps a virtual DOM, diffs it against the previous one, and applies only the minimal changes to the real DOM."),
        Q("What is the difference between useState and useRef?", "React", 2,
          [("state triggers re-render", ["re-render", "rerender"]), ("ref does not trigger re-render", ["does not", "doesn't", "without"]), ("ref persists across renders", ["persist", "mutable", "current"]), ("DOM access", ["dom", "element"])],
          "When does useEffect run and how do you clean up an effect?",
          "useState holds state that triggers a re-render when it changes, while useRef holds a mutable value that persists across renders without re-rendering, and is often used for DOM nodes."),
        Q("What is middleware in Express and how would you use it?", "Node and Express", 1,
          [("function with req res next", ["req", "res", "next"]), ("runs in order", ["order", "chain", "pipeline"]), ("auth or logging or error handling", ["auth", "logging", "error", "cors", "body"]), ("app.use", ["app.use", "use("])],
          "How is error-handling middleware different?",
          "Middleware are functions with access to req, res and next, executed in order for concerns like authentication, logging, parsing and error handling."),
        Q("Why would you choose MongoDB, and when would you not?", "Database", 2,
          [("document model flexible schema", ["document", "schema", "json", "flexible"]), ("horizontal scaling", ["scale", "sharding", "horizontal"]), ("no joins and transactions trade-offs", ["join", "transaction", "relational", "acid"]), ("indexes", ["index"])],
          "How would you model orders and products in MongoDB?",
          "MongoDB suits flexible, document-shaped data and horizontal scale, but relational data with heavy joins and strict transactions may fit SQL better."),
        Q("What is the event loop in Node.js?", "Node and Express", 3,
          [("single thread", ["single thread", "single-threaded"]), ("non-blocking I/O", ["non-blocking", "asynchronous", "async"]), ("callback queue", ["queue", "callback"]), ("libuv", ["libuv", "thread pool"])],
          "What happens if you run a heavy CPU loop inside a request handler?",
          "Node runs JavaScript on a single thread and uses the event loop with libuv to dispatch non-blocking I/O callbacks."),
    ],
    "data": [
        Q("What is the difference between INNER JOIN and LEFT JOIN?", "SQL", 1,
          [("inner returns matching rows only", ["matching", "both tables", "only"]), ("left keeps all rows from left table", ["all rows", "left table", "every row"]), ("nulls for no match", ["null"]), ("example", ["example", "customers", "orders"])],
          "How would you find customers who have never placed an order?",
          "INNER JOIN returns only matching rows, while LEFT JOIN keeps every left row and fills NULL where there is no match. Filtering on NULL finds unmatched rows."),
        Q("How do you handle missing values in a dataset?", "Data cleaning", 1,
          [("understand why missing", ["why", "reason", "pattern", "mcar"]), ("drop rows or columns", ["drop", "remove", "delete"]), ("impute mean median mode", ["impute", "mean", "median", "mode", "fill"]), ("flag missingness", ["flag", "indicator"])],
          "When is median better than mean for imputation?",
          "First investigate why values are missing, then drop, impute with mean, median or model-based values, or add an indicator, depending on the amount and the bias introduced."),
        Q("Explain the difference between GROUP BY and a window function.", "SQL", 2,
          [("group by collapses rows", ["collapse", "aggregate", "one row per group"]), ("window keeps rows", ["keeps", "each row", "retain"]), ("over partition by", ["over", "partition"]), ("rank or running total", ["rank", "row_number", "running", "lag"])],
          "Write the idea of a query for the top 3 salaries per department.",
          "GROUP BY collapses rows into one per group, while window functions compute across a partition but keep every row, enabling rankings and running totals."),
        Q("What is a p-value and how would you explain it to a non-technical manager?", "Statistics", 2,
          [("probability of data under null", ["null hypothesis", "null"]), ("small means unlikely by chance", ["chance", "unlikely", "significant"]), ("threshold 0.05", ["0.05", "5%", "alpha"]), ("not probability hypothesis is true", ["not the probability", "doesn't mean", "does not mean"])],
          "What is the difference between statistical and practical significance?",
          "A p-value is the probability of seeing results at least this extreme if the null hypothesis were true; a small value suggests the result is unlikely to be pure chance."),
        Q("How would you design a dashboard to track sales performance?", "Visualization", 2,
          [("define KPIs", ["kpi", "metric", "revenue", "conversion"]), ("know the audience", ["audience", "stakeholder", "manager"]), ("right chart types", ["line", "bar", "trend", "chart"]), ("filters and drill down", ["filter", "drill", "interactive"])],
          "How do you make sure the numbers on the dashboard are trusted?",
          "Start from the audience and KPIs, choose simple charts such as trends and comparisons, add filters and drill-downs, and validate the data pipeline."),
        Q("What is the difference between correlation and causation?", "Statistics", 1,
          [("correlation is association", ["relationship", "associated", "move together"]), ("causation means one causes the other", ["cause", "causes"]), ("confounding variable", ["confound", "third variable", "lurking"]), ("experiments or A/B test", ["a/b", "experiment", "randomized"])],
          "Can you give a real example of a misleading correlation?",
          "Correlation shows two variables move together; causation means one drives the other, which requires ruling out confounders, ideally with a randomized experiment."),
    ],
    "hr": [
        Q("Tell me about yourself.", "Introduction", 1,
          [("education or background", ["college", "degree", "studying", "engineering", "background"]), ("skills", ["skill", "python", "java", "react", "project"]), ("goal", ["goal", "looking for", "want to", "interested"]), ("a specific achievement", ["built", "developed", "won", "completed", "internship"])],
          "Which of those experiences are you most proud of, and why?",
          "A strong answer is a short story: who you are, what you studied and built, one concrete achievement, and why this role is the next step."),
        Q("What are your biggest strengths and one weakness you are working on?", "Self-awareness", 1,
          [("a relevant strength", ["strength", "good at"]), ("evidence or example", ["example", "for instance", "when i", "project"]), ("a real weakness", ["weakness", "struggle", "used to"]), ("steps to improve", ["improve", "working on", "learning", "practice"])],
          "Can you give an example of how you worked on that weakness?",
          "Pick a strength relevant to the role with evidence, then a genuine, non-critical weakness and the concrete steps you are taking."),
        Q("Why do you want to work for our company?", "Motivation", 1,
          [("knows the company", ["company", "product", "mission", "values"]), ("matches own goals", ["goal", "learn", "grow", "career"]), ("what they can contribute", ["contribute", "skills", "bring", "value"])],
          "What do you know about our recent work?",
          "Show you researched the company, connect its work to your goals, and explain what you can contribute."),
        Q("Where do you see yourself in five years?", "Career goals", 1,
          [("realistic growth", ["grow", "senior", "lead", "expert"]), ("link to role", ["role", "company", "this job"]), ("learning plan", ["learn", "skills", "certification"])],
          "What would you do if the role changed in a direction you did not expect?",
          "Describe realistic growth in skills and responsibility that connects to the role."),
        Q("How do you handle pressure or tight deadlines?", "Work style", 2,
          [("prioritise", ["prioritize", "prioritise", "plan", "break down"]), ("communication", ["communicate", "inform", "ask for help"]), ("example", ["example", "once", "project", "exam"]), ("stay calm", ["calm", "focus"])],
          "Tell me about a time you missed a deadline. What happened?",
          "Explain your method for prioritising and communicating, supported by a real example."),
        Q("Are you comfortable relocating or working in shifts if needed?", "Logistics", 1,
          [("clear answer", ["yes", "comfortable", "open", "flexible"]), ("any conditions stated honestly", ["depends", "condition", "family", "notice"])],
          "Is there anything that would make this difficult for you?",
          "Answer honestly and clearly, mentioning any real constraints politely."),
    ],
    "behavioral": [
        Q("Tell me about a time you worked in a team and disagreed with a teammate.", "Teamwork", 2,
          [("situation", ["situation", "project", "team"]), ("your action", ["i talked", "i suggested", "i decided", "i listened", "i"]), ("resolution", ["resolved", "agreed", "compromise", "decided together"]), ("result and learning", ["result", "learned", "outcome", "delivered"])],
          "What would you do differently if the same thing happened again?",
          "Use STAR: describe the situation and task, your specific actions to understand and resolve the disagreement, and the result and what you learned."),
        Q("Describe a situation where you failed. What did you learn?", "Failure", 2,
          [("honest failure", ["failed", "mistake", "didn't", "went wrong"]), ("took responsibility", ["my fault", "i should", "responsib", "i realised", "i realized"]), ("what changed", ["learned", "since then", "now i", "changed"])],
          "How has that experience changed how you work today?",
          "Own the mistake, explain what you learned and show a specific behaviour change."),
        Q("Tell me about a time you had to learn something new quickly.", "Adaptability", 1,
          [("context", ["project", "internship", "college", "needed to"]), ("how they learned", ["documentation", "tutorial", "course", "asked", "practice"]), ("outcome", ["delivered", "completed", "result", "worked"])],
          "How do you decide what to learn first when everything is new?",
          "Describe the situation, your learning method and the concrete outcome."),
        Q("Give an example of when you took initiative without being asked.", "Ownership", 2,
          [("noticed a problem", ["noticed", "problem", "gap", "issue"]), ("took action", ["started", "built", "organized", "organised", "created"]), ("impact", ["impact", "result", "saved", "improved"])],
          "How did others react to what you did?",
          "State the problem you noticed, the initiative you took and the measurable impact."),
        Q("Describe a time you had to meet a very tight deadline.", "Time management", 2,
          [("situation", ["deadline", "submission", "hackathon", "exam"]), ("prioritisation", ["prioritize", "prioritise", "plan", "scope"]), ("result", ["completed", "submitted", "delivered", "result"])],
          "What did you cut or compromise on, and was it the right call?",
          "Explain the deadline, how you prioritised and scoped, and the result."),
    ],
}

ROLE_MAP = [("java", "java"), ("python", "python"), ("mern", "mern"), ("react", "mern"), ("node", "mern"), ("full", "mern"), ("data", "data"), ("analyst", "data"), ("sql", "data")]
BANK_KEYS = ["java", "python", "mern", "data", "hr", "behavioral"]
_cache = {"at": 0.0, "active": None, "by_text": None}


def seed_builtin(db):
    """First run: copy the built-in questions into the database so admins can edit, disable or extend them."""
    from .db import Question
    if db.query(Question).filter(Question.source == "builtin").count():
        return
    for key, qs in BANK.items():
        for q in qs:
            db.add(Question(bank_key=key, topic=q["topic"], level=q["level"], text=q["q"], concepts=[[l, list(s)] for l, s in q["concepts"]],
                            followup=q["followup"], model_answer=q["model"], active=True, source="builtin"))
    db.commit()


def invalidate():
    _cache["at"] = 0.0


def _row(r) -> dict:
    return {"id": r.id, "q": r.text, "topic": r.topic, "level": r.level, "concepts": [(c[0], c[1]) for c in (r.concepts or [])], "followup": r.followup, "model": r.model_answer, "key": r.bank_key}


def _load():
    import time
    if _cache["active"] is not None and time.time() - _cache["at"] < 30:
        return
    try:
        from .db import Question, SessionLocal
        with SessionLocal() as db:
            rows = db.query(Question).all()
        if not rows:
            raise RuntimeError("empty")
        active = {k: [] for k in BANK_KEYS}
        by_text = {}
        for r in rows:
            d = _row(r)
            by_text[r.text] = d
            if r.followup:
                by_text.setdefault(r.followup, d)
            if r.active and r.bank_key in active:
                active[r.bank_key].append(d)
        _cache.update(active=active, by_text=by_text, at=time.time())
    except Exception:  # database not ready (e.g. unit use): fall back to the built-in bank
        active = {k: [{"id": None, "q": q["q"], "topic": q["topic"], "level": q["level"], "concepts": q["concepts"], "followup": q["followup"], "model": q["model"], "key": k} for q in qs] for k, qs in BANK.items()}
        by_text = {}
        for qs in active.values():
            for q in qs:
                by_text[q["q"]] = q; by_text.setdefault(q["followup"], q)
        _cache.update(active=active, by_text=by_text, at=time.time())


def _bank_key(role: str, itype: str) -> str:
    if itype == "hr":
        return "hr"
    if itype == "behavioral":
        return "behavioral"
    r = role.lower()
    for needle, key in ROLE_MAP:
        if needle in r:
            return key
    return "hr"


def question_list(config: dict, seed: str) -> list[dict]:
    _load()
    bank = _cache["active"]
    itype = config.get("interview_type", "technical")
    rnd = random.Random(seed)
    if itype == "mixed":
        keys = [_bank_key(config.get("role", ""), "technical"), "hr", "behavioral"]
        pools = [rnd.sample(bank[k], len(bank[k])) for k in keys if bank.get(k)]
        out = []
        while any(pools):
            for p in pools:
                if p:
                    out.append(p.pop())
        return out or [q for qs in bank.values() for q in qs]
    pool = list(bank.get(_bank_key(config.get("role", ""), itype)) or [q for qs in bank.values() for q in qs])
    rnd.shuffle(pool)
    level = {"beginner": 1, "intermediate": 2, "advanced": 3}.get(config.get("difficulty", "intermediate"), 2)
    pool.sort(key=lambda q: abs(q["level"] - level))
    return pool


def pool_texts(config: dict, limit: int = 10) -> list[str]:
    """Curated questions (admin-managed) offered to the LLM interviewer as a preferred pool."""
    qs = question_list(config, "pool")
    return [q["q"] for q in qs[:limit]]


def find_question(text: str) -> dict | None:
    _load()
    return (_cache["by_text"] or {}).get(text)


def detect_turn_type(text: str) -> str:
    t = text.lower().strip()
    if re.search(r"\b(repeat|say that again|say it again|come again|didn'?t (hear|catch|understand)|can you rephrase|what do you mean)\b", t) and len(t.split()) < 18:
        return "clarification"
    if re.search(r"\b(skip|pass on|next question|move on)\b", t) and len(t.split()) < 12:
        return "skip"
    return "answer"


def _hit(answer: str, syns: list[str]) -> bool:
    a = answer.lower()
    return any(s.lower() in a for s in syns)


def evaluate(question: dict | None, answer: str) -> dict:
    words = len(answer.split())
    if not question:
        cov = min(1.0, words / 60)
        correct, missing = [], []
    else:
        hits = [(label, _hit(answer, syns)) for label, syns in question["concepts"]]
        correct = [l for l, h in hits if h]
        missing = [l for l, h in hits if not h]
        cov = len(correct) / max(1, len(hits))
    sentences = max(1, len(re.findall(r"[.!?।]", answer)) or 1)
    clarity = 35 + min(40, words * 1.2) + (10 if 8 <= words / sentences <= 28 else 0)
    if words < 8:
        clarity = min(clarity, 35)
    accuracy = round(20 + cov * 75) if words >= 6 else 10
    relevance = round(25 + cov * 65 + min(10, words / 6)) if words >= 6 else 10
    completeness = round(cov * 100) if words >= 6 else 5
    scores = {"accuracy": min(accuracy, 100), "relevance": min(relevance, 100), "completeness": min(completeness, 100), "clarity": round(min(clarity, 95))}
    return {
        "scores": scores,
        "correct_concepts": correct,
        "missing_concepts": missing,
        "inaccuracies": [],
        "explanation": (f"Your answer covered {len(correct)} of {len(correct) + len(missing)} key ideas." if question else "Scored on length and structure only."),
        "improvements": [f"Mention {m}." for m in missing[:3]] or ["Add a short concrete example to make the answer memorable."],
        "model_answer": (question or {}).get("model", ""),
        "topic": (question or {}).get("topic", "General"),
    }
