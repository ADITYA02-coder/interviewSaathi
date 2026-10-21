"""Client for the separate code-runner service, plus the judge that compares output with the expected answers.
The main server never executes submitted code itself."""
import httpx
from .config import settings

_transport = None  # tests inject httpx.MockTransport
LANGUAGES = {"python": "Python 3", "javascript": "JavaScript (Node)", "java": "Java"}

STARTERS = {
    "python": 'import sys\n\n\ndef main():\n    data = sys.stdin.read().split("\\n")\n    # Read the input as described, solve the problem, print the answer.\n\n\nmain()\n',
    "javascript": 'const lines = require("fs").readFileSync(0, "utf8").split("\\n");\n// Read the input as described, solve the problem, print the answer.\n',
    "java": 'import java.util.*;\n\npublic class Main {\n    public static void main(String[] args) {\n        Scanner sc = new Scanner(System.in);\n        // Read the input as described, solve the problem, print the answer.\n    }\n}\n',
}


class RunnerUnavailable(Exception):
    pass


def enabled() -> bool:
    return bool(settings.runner_url and settings.runner_secret)


def norm(s: str) -> str:
    lines = [ln.rstrip() for ln in (s or "").replace("\r\n", "\n").split("\n")]
    while lines and not lines[-1]:
        lines.pop()
    return "\n".join(lines)


async def _judge(language: str, code: str, inputs: list[str], timeout_s: float) -> dict:
    if not enabled():
        raise RunnerUnavailable("The code runner is not configured on this server.")
    try:
        async with httpx.AsyncClient(timeout=90, transport=_transport) as c:
            r = await c.post(f"{settings.runner_url}/judge", headers={"X-Runner-Key": settings.runner_secret},
                             json={"language": language, "code": code, "tests": [{"input": i} for i in inputs], "timeout_s": timeout_s})
    except httpx.HTTPError as e:
        raise RunnerUnavailable(f"Could not reach the code runner ({e.__class__.__name__}).")
    if r.status_code == 422:
        raise RunnerUnavailable(r.json().get("detail", "Language not available on the runner."))
    if r.status_code != 200:
        raise RunnerUnavailable(f"Code runner error ({r.status_code}).")
    return r.json()


def _clip(s: str, n: int = 600) -> str:
    return s if len(s) <= n else s[:n] + "…"


async def run_problem(problem, language: str, code: str, visible_only: bool) -> dict:
    """Returns the PUBLIC result: hidden tests expose only pass/fail, never their input or expected output."""
    tests = [t for t in problem.tests if not (visible_only and t.get("hidden"))]
    resp = await _judge(language, code, [t["input"] for t in tests], 4.0)
    if not resp["compile"]["ok"]:
        return {"status": "compile_error", "passed": 0, "total": len(tests), "compile_error": _clip(resp["compile"]["output"], 2000), "tests": [], "max_time_ms": 0}
    out, passed, first_error = [], 0, None
    for i, (t, r) in enumerate(zip(tests, resp["runs"])):
        if r.get("timed_out"):
            st = "timeout"
        elif r["exit_code"] != 0:
            st = "runtime_error"
        else:
            st = "pass" if norm(r["stdout"]) == norm(t["expected"]) else "wrong_answer"
        passed += st == "pass"
        row = {"i": i + 1, "hidden": bool(t.get("hidden")), "status": st, "time_ms": r["time_ms"]}
        if not t.get("hidden"):
            row.update(input=_clip(t["input"].strip()), expected=_clip(t["expected"]), actual=_clip(r["stdout"].strip()))
        if st == "runtime_error" and first_error is None:
            first_error = _clip(r["stderr"][-1200:], 1200)
            row["error"] = first_error
        out.append(row)
    statuses = {r["status"] for r in out}
    status = "accepted" if passed == len(out) else "timeout" if "timeout" in statuses else "runtime_error" if "runtime_error" in statuses else "wrong_answer"
    return {"status": status, "passed": passed, "total": len(out), "tests": out, "max_time_ms": max((r["time_ms"] for r in out), default=0),
            "hidden_failed": sum(1 for r in out if r["hidden"] and r["status"] != "pass")}


def public_problem(p, include_starters: bool = True) -> dict:
    d = {"id": p.id, "title": p.title, "difficulty": p.difficulty, "topic": p.topic, "statement": p.statement, "input_format": p.input_format,
         "output_format": p.output_format, "examples": p.examples, "visible_tests": sum(1 for t in p.tests if not t.get("hidden")),
         "hidden_tests": sum(1 for t in p.tests if t.get("hidden"))}
    if include_starters:
        d["starters"] = STARTERS
    return d
