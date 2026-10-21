#!/bin/bash
# Starts the code runner on :9000 (development only: NOT isolated), runs the given command, stops the runner.
cd "$(dirname "$0")/../../runner"
RUNNER_CONFIRM_ISOLATED=1 RUNNER_SECRET=devsecret123 python -m uvicorn app:app --port 9000 >/tmp/runner.log 2>&1 &
RP=$!
for i in $(seq 1 30); do curl -s localhost:9000/health >/dev/null && break; sleep 0.3; done
cd - >/dev/null; "$@"; RC=$?
kill $RP 2>/dev/null; wait $RP 2>/dev/null; exit $RC
