# Running the code runner (Windows PowerShell, macOS, Linux)

The runner executes student code for the **Coding round**. The backend calls it over HTTP. It needs the **same secret** on both sides.

> **Windows:** older versions used Unix-only features and crashed on startup in PowerShell. This version has a **portable mode** that starts automatically on Windows. Portable mode is **not a sandbox** (see the warning at the bottom): it is for developing on your own laptop only.

## A. Windows PowerShell (VS Code terminal), development mode

Open a **new terminal** in VS Code (Terminal > New Terminal) and keep it running. Use a separate terminal for the backend.

```powershell
cd runner
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

$env:RUNNER_CONFIRM_ISOLATED = "1"
$env:RUNNER_SECRET = "my-long-dev-secret-123"
python -m uvicorn app:app --port 9000
```

You should see `RUNNER PORTABLE MODE: ...` and `Uvicorn running on http://127.0.0.1:9000`.

If activation says *running scripts is disabled*, run `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` and activate again.

Check it from a second terminal:

```powershell
Invoke-RestMethod http://127.0.0.1:9000/health
# expected: ok True, portable True, languages python/javascript/java
```

Then put these two lines in the project's `.env` (same secret!) and **restart the backend**:

```
RUNNER_URL=http://127.0.0.1:9000
RUNNER_SECRET=my-long-dev-secret-123
```

Verify: `http://localhost:8000/api/meta` shows `"coding_enabled": true`.

### Languages
- **Python** always works (it uses the Python running the service).
- **JavaScript** needs Node: `node --version`.
- **Java** needs a **JDK**, not just a JRE: `javac -version`. If missing, that language shows as unavailable.

## B. Docker Desktop (closer to production, recommended if installed)

```powershell
docker build -t interviewsaathi-runner ./runner
docker run --rm -p 9000:9000 -e RUNNER_SECRET=my-long-dev-secret-123 --read-only --tmpfs /tmp:size=128m,mode=1777 --cap-drop ALL --cap-add SETUID --cap-add SETGID --pids-limit 512 -m 1g interviewsaathi-runner
```

Use the same `.env` lines as above. This runs the **hardened** mode (unprivileged user, resource limits) inside a Linux container.

## C. WSL2 (Ubuntu on Windows) or macOS / Linux

```bash
cd runner
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
RUNNER_CONFIRM_ISOLATED=1 RUNNER_SECRET=my-long-dev-secret-123 uvicorn app:app --port 9000
```

(That one-line `VAR=value command` syntax is **bash only**. It does not work in PowerShell, which is the usual reason it "doesn't work" from a VS Code terminal.)

## Troubleshooting

| Symptom | Fix |
|---|---|
| `RUNNER_SECRET=... : The term is not recognized` | You pasted the bash line into PowerShell. Use the `$env:` lines in section A |
| `uvicorn is not recognized` | Use `python -m uvicorn ...` and make sure the venv is activated (prompt shows `(.venv)`) |
| `Refusing to start: this service executes untrusted code` | Set `$env:RUNNER_CONFIRM_ISOLATED = "1"` in the **same** terminal before starting |
| `Set RUNNER_SECRET (8+ characters)` | Set `$env:RUNNER_SECRET` to 8 or more characters |
| `ModuleNotFoundError: No module named 'resource'` | You have an old copy of `runner/app.py`. Use the version in this project |
| Backend says *Could not reach the code runner* | Use `127.0.0.1`, **not** `localhost` (Windows may resolve it to IPv6). Check the runner terminal is still running; allow Python through Windows Firewall on *private* networks if prompted |
| Backend says *code runner error (401)* | The secret differs between `.env` and the runner terminal. Make them identical, restart both |
| Coding round greyed out in Setup | Restart the backend after editing `.env`; check `/api/meta` shows `coding_enabled: true` |
| `Address already in use` on 9000 | `netstat -ano \| findstr :9000`, stop that process or use `--port 9001` and change `RUNNER_URL` |
| Java submissions are slow the first time | JVM start-up. Normal; later runs are faster |
| JavaScript / Java says *not available on this runner* | Install Node.js / a JDK and open a **new** terminal so PATH updates |

## Safety

- **Portable mode runs submitted code with your own user's permissions and no memory/CPU/process limits.** A student's code could read your files. Use it only for your own testing, never on a shared machine or a server, and never expose port 9000 beyond your laptop.
- Real deployments must use the hardened mode: the Docker container (`docker-compose.yml`) or a Linux host. It runs code as an unprivileged user with resource limits, no internet and a read-only filesystem.
- I developed and tested portable mode's code path on Linux (including all coding tests). The Windows-specific parts (process-tree kill via `taskkill`) could not be run on Windows in my environment, so if something misbehaves there, send me the runner terminal output.
