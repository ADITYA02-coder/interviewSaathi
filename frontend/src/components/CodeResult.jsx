const LABEL = { accepted: "Accepted", wrong_answer: "Wrong answer", runtime_error: "Runtime error", compile_error: "Compile error", timeout: "Time limit exceeded", error: "Error" };
const TONE = { accepted: "green", compile_error: "coral", runtime_error: "coral", timeout: "coral", wrong_answer: "coral" };

export default function CodeResult({ result, dark = false }) {
  if (!result) return null;
  const pct = result.total ? Math.round((100 * result.passed) / result.total) : 0;
  return (
    <div className={`cres ${dark ? "dark" : ""}`} role="region" aria-label="Test results">
      <div className="cres-head">
        <span className={`pill ${TONE[result.status] || ""}`}>{LABEL[result.status] || result.status}</span>
        <b>{result.passed} / {result.total} tests passed</b>
        {result.max_time_ms > 0 && <span className="sub">slowest {result.max_time_ms} ms</span>}
      </div>
      <div className="meter" aria-hidden="true"><i style={{ width: pct + "%", background: result.status === "accepted" ? "var(--green)" : "linear-gradient(90deg,var(--teal),var(--gold))" }} /></div>
      {result.compile_error && <pre className="err-pre">{result.compile_error}</pre>}
      <div className="tlist">
        {result.tests.map((t) => (
          <details key={t.i} className={`t ${t.status === "pass" ? "ok" : "bad"}`} open={t.status !== "pass" && !t.hidden}>
            <summary>
              <span className="dot" /> {t.hidden ? `Hidden test ${t.i}` : `Sample test ${t.i}`}
              <span className="sub">{t.status === "pass" ? "passed" : t.status.replace("_", " ")} · {t.time_ms} ms</span>
            </summary>
            {t.hidden ? <p className="sub">The input and expected output of hidden tests stay secret, like in a real interview. Think about edge cases: empty or minimum-size input, duplicates, negatives, very large input.</p> : (
              <div className="tcase">
                <div><span className="label">Input</span><pre>{t.input}</pre></div>
                <div><span className="label">Expected</span><pre>{t.expected}</pre></div>
                <div><span className="label">Your output</span><pre>{t.actual || "(nothing printed)"}</pre></div>
              </div>)}
            {t.error && <pre className="err-pre">{t.error}</pre>}
          </details>))}
      </div>
    </div>
  );
}
