"""InterviewSaathi code runner: a SEPARATE service that executes untrusted code.

NEVER run this on a machine you care about. It is meant to live inside its own locked-down container (see Dockerfile and
docker-compose.yml: no internet, no secrets, read-only filesystem, CPU/memory/PID limits). Inside the container the submitted code runs as
the unprivileged user `nobody`, in a throw-away directory, with CPU-time / file-size / process-count limits and a hard wall-clock timeout.
The main FastAPI server never executes user code itself; it only calls POST /judge here.
"""
import asyncio
import ctypes
import hmac
import os
import shutil
import signal
import subprocess
import sys
import tempfile
import time
from pathlib import Path

try:
    import resource  # Unix only
except ImportError:
    resource = None
from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel, Field

# PORTABLE mode = Windows, or RUNNER_PORTABLE=1. It runs code with only a timeout: NO user switch, NO memory/CPU/process limits, NO network
# isolation. It exists so you can develop coding rounds on a Windows laptop. Never use it on a server.
PORTABLE = os.name != "posix" or os.environ.get("RUNNER_PORTABLE") == "1" or resource is None
if os.environ.get("RUNNER_CONFIRM_ISOLATED") != "1":
    sys.exit("Refusing to start: this service executes untrusted code. Run it inside the provided container, or set "
             "RUNNER_CONFIRM_ISOLATED=1 to confirm you understand the machine is NOT protected (development only).")
SECRET = os.environ.pop("RUNNER_SECRET", "")
if len(SECRET) < 8:
    sys.exit("Set RUNNER_SECRET (8+ characters); the backend sends it in X-Runner-Key.")

if PORTABLE:
    print("RUNNER PORTABLE MODE: student code runs with your own user rights and no resource limits. Development only.", flush=True)
if not PORTABLE:
    try:  # become the "subreaper" so orphaned grandchildren of user code are reparented to us (and can be reaped), not left as zombies
        ctypes.CDLL("libc.so.6", use_errno=True).prctl(36, 1, 0, 0, 0)  # PR_SET_CHILD_SUBREAPER
    except Exception:
        pass
MAX_OUT = 64 * 1024
NOBODY = 65534
SEM = asyncio.Semaphore(int(os.environ.get("RUNNER_MAX_PARALLEL", "4")))
HAS_JAVAC = shutil.which("javac") is not None
PY = sys.executable if PORTABLE else "python3"   # on Windows there is usually no "python3"; use the interpreter running this service
LANGS = {
    "python": {"file": "main.py", "available": PORTABLE or bool(shutil.which("python3")), "as_limit": 768 * 1024 * 1024},
    "javascript": {"file": "main.js", "available": bool(shutil.which("node")), "as_limit": None},
    "java": {"file": "Main.java", "available": bool(shutil.which("java")), "as_limit": None},
}
app = FastAPI(title="InterviewSaathi runner", docs_url=None, redoc_url=None, openapi_url=None)


class Test(BaseModel):
    input: str = Field(max_length=200_000, default="")


class Judge(BaseModel):
    language: str
    code: str = Field(max_length=100_000)
    tests: list[Test] = Field(max_length=40)
    timeout_s: float = Field(default=4.0, ge=0.5, le=10.0)


def _uid() -> int:
    return os.getuid() if hasattr(os, "getuid") else -1


def _kill_tree(p):
    if os.name == "nt":
        subprocess.run(["taskkill", "/F", "/T", "/PID", str(p.pid)], capture_output=True)
    else:
        try:
            os.killpg(p.pid, signal.SIGKILL)
        except (ProcessLookupError, PermissionError):
            pass


def _demote(limits_cpu: int, as_limit):
    def fn():
        os.setsid()
        resource.setrlimit(resource.RLIMIT_CPU, (limits_cpu, limits_cpu + 1))
        resource.setrlimit(resource.RLIMIT_FSIZE, (2 * 1024 * 1024, 2 * 1024 * 1024))
        resource.setrlimit(resource.RLIMIT_NOFILE, (96, 96))
        resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
        resource.setrlimit(resource.RLIMIT_NPROC, (512, 512))
        if as_limit:
            resource.setrlimit(resource.RLIMIT_AS, (as_limit, as_limit))
        if _uid() == 0:  # drop root before touching user code
            os.setgroups([])
            os.setgid(NOBODY)
            os.setuid(NOBODY)
    return fn


def _read(path: Path) -> tuple[str, bool]:
    data = path.read_bytes()
    return data[:MAX_OUT].decode("utf8", "replace"), len(data) > MAX_OUT


def _run(cmd, cwd: Path, stdin_text: str, timeout: float, as_limit) -> dict:
    out_p, err_p = cwd / ".stdout", cwd / ".stderr"
    with open(out_p, "wb") as fo, open(err_p, "wb") as fe:
        t0 = time.perf_counter()
        if PORTABLE:
            env = {k: v for k, v in os.environ.items() if not k.startswith("RUNNER_")}
            env.update(HOME=str(cwd), PYTHONIOENCODING="utf-8")
            extra = {"creationflags": subprocess.CREATE_NEW_PROCESS_GROUP | getattr(subprocess, "CREATE_NO_WINDOW", 0)} if os.name == "nt" else {"start_new_session": True}
            p = subprocess.Popen(cmd, cwd=cwd, stdin=subprocess.PIPE, stdout=fo, stderr=fe, env=env, **extra)
        else:
            env = {"PATH": "/usr/local/bin:/usr/bin:/bin", "HOME": str(cwd), "LANG": "C.UTF-8", "PYTHONIOENCODING": "utf-8"}
            p = subprocess.Popen(cmd, cwd=cwd, stdin=subprocess.PIPE, stdout=fo, stderr=fe, env=env, preexec_fn=_demote(int(timeout) + 1, as_limit), close_fds=True)
        timed_out = False
        try:
            p.communicate(stdin_text.encode(), timeout=timeout)
        except subprocess.TimeoutExpired:
            timed_out = True
        except (BrokenPipeError, OSError):
            pass
        finally:
            _kill_tree(p)  # nothing the code spawned may outlive the test
            p.wait()
            for _ in range(0 if os.name != "posix" else 2000):  # reap every leftover process of this run's group (fork bombs would otherwise exhaust the process limit as zombies)
                try:
                    if os.waitpid(-p.pid, os.WNOHANG)[0] == 0:
                        break
                except ChildProcessError:
                    break
    ms = round((time.perf_counter() - t0) * 1000)
    so, t1 = _read(out_p); se, t2 = _read(err_p)
    return {"stdout": so, "stderr": se, "exit_code": p.returncode if not timed_out else None, "time_ms": ms, "timed_out": timed_out, "truncated": t1 or t2}


@app.get("/health")
def health():
    return {"ok": True, "portable": PORTABLE, "languages": {k: v["available"] for k, v in LANGS.items()}, "java_compiler": HAS_JAVAC, "uid": _uid()}


@app.post("/judge")
async def judge(req: Judge, x_runner_key: str = Header(default="")):
    if not hmac.compare_digest(x_runner_key, SECRET):
        raise HTTPException(401, "bad runner key")
    cfg = LANGS.get(req.language)
    if not cfg or not cfg["available"]:
        raise HTTPException(422, f"language '{req.language}' is not available on this runner")
    async with SEM:
        return await asyncio.to_thread(_judge_sync, req, cfg)


def _judge_sync(req: Judge, cfg: dict) -> dict:
    work = Path(tempfile.mkdtemp(prefix="run_", dir=os.environ.get("RUNNER_TMP") or None))
    try:
        (work / cfg["file"]).write_text(req.code, encoding="utf8")
        os.chmod(work, 0o755)
        if _uid() == 0:
            for f in work.iterdir():
                os.chown(f, NOBODY, NOBODY)
            os.chown(work, NOBODY, NOBODY)
        compile_info = {"ok": True, "output": ""}
        if req.language == "python":
            cmd = [PY, "-I", "-B", "main.py"]
        elif req.language == "javascript":
            cmd = ["node", "--max-old-space-size=128", "main.js"]
        else:
            jvm = ["-Xmx160m", "-Xss16m", "-XX:+UseSerialGC", "-XX:TieredStopAtLevel=1", "-Xshare:auto"]
            if HAS_JAVAC:
                r = _run(["javac", "-J-Xmx256m", "-d", "out", "Main.java"], work, "", 20, None)
                if r["exit_code"] != 0:
                    return {"compile": {"ok": False, "output": (r["stderr"] or r["stdout"])[:4000]}, "runs": []}
                cmd = ["java", *jvm, "-cp", "out", "Main"]
            else:
                cmd = ["java", *jvm, "Main.java"]
        runs, deadline, strikes = [], time.time() + 40, 0
        for t in req.tests:
            if time.time() > deadline or strikes >= 3:
                runs.append({"stdout": "", "stderr": "skipped", "exit_code": None, "time_ms": 0, "timed_out": True, "truncated": False, "skipped": True})
                continue
            r = _run(cmd, work, t.input, req.timeout_s + (1.5 if req.language == "java" else 0), cfg["as_limit"])
            if req.language == "java" and not HAS_JAVAC and "error: compilation failed" in r["stderr"]:  # source-launcher mode reports compile errors at run time
                return {"compile": {"ok": False, "output": r["stderr"][:4000]}, "runs": []}
            strikes = strikes + 1 if r["timed_out"] else 0
            runs.append(r)
        return {"compile": compile_info, "runs": runs}
    finally:
        shutil.rmtree(work, ignore_errors=True)
