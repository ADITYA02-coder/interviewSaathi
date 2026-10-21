import { useEffect, useState } from "react";
import { api } from "../lib/api.js";
import { go } from "../App.jsx";

const col = (n) => (n >= 75 ? "var(--green)" : n >= 55 ? "var(--gold-d)" : "var(--coral)");

export function Ring({ value, size = 160, label = "overall" }) {
  const r = size / 2 - 12, c = 2 * Math.PI * r;
  return (
    <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} role="img" aria-label={`${value} out of 100`}>
      <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke="#e4ecea" strokeWidth="12" />
      <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke={col(value)} strokeWidth="12" strokeLinecap="round" strokeDasharray={`${(c * value) / 100} ${c}`} transform={`rotate(-90 ${size / 2} ${size / 2})`} />
      <text x="50%" y="50%" textAnchor="middle" dominantBaseline="central" fontFamily="var(--display)" fontWeight="800" fontSize={size / 3.2} fill="var(--ink)">{value}</text>
      <text x="50%" y={size * 0.72} textAnchor="middle" fontSize="12" fontWeight="700" fill="var(--muted)" letterSpacing=".08em">{label.toUpperCase()}</text>
    </svg>
  );
}

export default function Report({ id }) {
  const [data, setData] = useState(null); const [err, setErr] = useState("");
  useEffect(() => {
    (async () => {
      try {
        let r = await api.interview(id);
        if (!r.report) { await api.finish(id); r = await api.interview(id); }
        setData(r);
      } catch (e) { setErr(e.message); }
    })();
  }, [id]);
  if (err) return <div className="wrap"><p className="err">{err}</p></div>;
  if (!data) return <div className="wrap"><p className="sub">Preparing your report…</p></div>;
  const rep = data.report, c = data.config;
  const qa = data.turns.filter((t) => t.role === "candidate" && t.kind === "answer" && t.evaluation);
  const skipped = data.turns.filter((t) => t.role === "candidate" && t.kind === "skip").length;

  const practiseWeak = () => {
    const weak = rep.topics.filter((t) => t.score < 70).map((t) => t.topic);
    sessionStorage.setItem("is_prefill", JSON.stringify({ role: c.role, interview_type: c.interview_type, jd_text: weak.length ? `Focus most of the questions on these topics I was weak at: ${weak.join(", ")}.` : "" }));
    go("setup");
  };
  const retake = () => { sessionStorage.setItem("is_prefill", JSON.stringify({ role: c.role, interview_type: c.interview_type })); go("setup"); };

  return (
    <div className="wrap stack">
      <div className="card rep-head">
        <Ring value={rep.overall} />
        <div>
          <span className="pill">{c.role} · {c.interview_type} · {c.difficulty}</span>
          <h2 style={{ fontSize: 36, margin: "10px 0 6px" }}>{rep.headline}</h2>
          <p className="sub">{rep.answered} answer{rep.answered === 1 ? "" : "s"} scored{skipped ? ` · ${skipped} skipped` : ""} · {new Date(data.started_at + "Z").toLocaleString()}</p>
          <div style={{ display: "flex", gap: 10, marginTop: 16, flexWrap: "wrap" }}>
            <button className="btn gold" onClick={practiseWeak}>{rep.topics.some((t) => t.score < 70) ? "Practise my weak topics" : "Practise again"}</button>
            <button className="btn ghost" onClick={retake}>Same setup, new interview</button>
            <a className="btn ghost" href="#/dashboard">My progress</a>
          </div>
        </div>
      </div>
      <p className="notice">{rep.disclaimer} Scored by: {rep.engine}.{rep.engine === "offline-rule-based" ? " This is a keyword-based estimate; connect an AI model for deeper evaluation." : ""}</p>

      {rep.answered > 0 && <div className="grid2">
        <div className="card"><h3>How you did, by skill</h3>
          {Object.entries(rep.dimensions).map(([k, v]) => <div className="bar" key={k}><span>{rep.dimension_labels[k]}</span><div><i style={{ width: v + "%", background: col(v) }} /></div><b>{v}</b></div>)}</div>
        <div className="card"><h3>By topic</h3>
          {rep.topics.length ? rep.topics.map((t) => <div className="bar" key={t.topic}><span>{t.topic}</span><div><i style={{ width: t.score + "%", background: col(t.score) }} /></div><b>{t.score}</b></div>) : <p className="sub">No topics yet.</p>}</div>
      </div>}

      <div className="grid2">
        <div className="card"><h3>What went well</h3>{rep.strengths?.length ? <ul className="clean">{rep.strengths.map((s, i) => <li key={i}>{s}</li>)}</ul> : <p className="sub">Keep practising and strengths will show up here.</p>}</div>
        <div className="card"><h3>What to improve</h3>{rep.improvements?.length ? <ul className="clean">{rep.improvements.map((s, i) => <li key={i}>{s}</li>)}</ul> : <p className="sub">Nothing major stood out.</p>}</div>
      </div>

      {rep.study_plan?.length > 0 && <div className="card"><h3 style={{ marginBottom: 12 }}>Your study plan</h3>
        <div className="plan">{rep.study_plan.map((p, i) => <div key={i}><b>{p.topic}</b> <span className={`pill ${p.urgency === "high" ? "coral" : "gold"}`}>{p.urgency} priority</span>
          <p className="sub" style={{ margin: "4px 0" }}>{p.why}</p><ul className="clean">{(p.actions || []).map((a, j) => <li key={j}>{a}</li>)}</ul></div>)}</div></div>}

      {rep.kind === "coding" && rep.problems?.length > 0 && <div><h3 style={{ fontSize: 24, margin: "8px 0 14px" }}>Problem by problem</h3>
        {rep.problems.map((p) => p.skipped ? <p key={p.id} className="sub" style={{ marginBottom: 10 }}>{p.title}: skipped</p> : (
          <details className="qa" key={p.id} open>
            <summary><span className="sc" style={{ background: col(p.overall) }}>{p.overall}</span><span style={{ flex: 1 }}>{p.title}<br /><span className="sub" style={{ fontWeight: 500 }}>{p.topic} · {p.difficulty} · {p.submitted ? `${p.passed}/${p.total} tests passed` : "not submitted"}</span></span><span className={`pill ${p.status === "accepted" ? "green" : "coral"}`}>{p.status.replace("_", " ")}</span></summary>
            <div className="body">
              <div className="bar"><span>Tests passed</span><div><i style={{ width: p.correctness + "%", background: col(p.correctness) }} /></div><b>{p.correctness}</b></div>
              {p.hidden_failed > 0 && <p className="notice">{p.hidden_failed} hidden test{p.hidden_failed > 1 ? "s" : ""} failed. Hidden tests usually probe edge cases such as empty or minimum-size input, duplicates, negatives and very large input.</p>}
              <p className="sub">Expected complexity: time {p.expected_time}, space {p.expected_space}. You ran the samples {p.runs} time{p.runs === 1 ? "" : "s"}.</p>
              {[["Your approach (spoken)", p.approach], ["Complexity and edge cases (spoken)", p.complexity]].map(([label, ev]) => ev && (
                <div key={label}><span className="label">{label} · {ev.overall}/100</span><p>{ev.explanation}</p>
                  {ev.missing_concepts?.length > 0 && <div className="tags">{ev.missing_concepts.map((x, j) => <span key={j} className="pill miss">{x}</span>)}</div>}
                  {ev.model_answer && <div className="model" style={{ marginTop: 8 }}><span className="label">One possible strong answer</span><p>{ev.model_answer}</p></div>}</div>))}
              {p.code && <div><span className="label">Your submitted code ({p.language})</span><pre className="code-in-report">{p.code}</pre></div>}
            </div>
          </details>))}</div>}
      {qa.length > 0 && rep.kind !== "coding" && <div><h3 style={{ fontSize: 24, margin: "8px 0 14px" }}>Question by question</h3>
        {qa.map((t, i) => { const e = t.evaluation; return (
          <details className="qa" key={i} open={i === 0}>
            <summary><span className="sc" style={{ background: col(e.overall) }}>{e.overall}</span><span style={{ flex: 1 }}>{t.question}<br /><span className="sub" style={{ fontWeight: 500 }}>{e.topic}</span></span></summary>
            <div className="body">
              <div><span className="label">Your answer{t.source === "voice" ? " (transcribed from your voice)" : ""}</span><div className="ans">{t.text}</div></div>
              <p>{e.explanation}</p>
              <div>{Object.entries(e.scores).map(([k, v]) => <div className="bar" key={k}><span>{rep.dimension_labels[k]}</span><div><i style={{ width: v + "%", background: col(v) }} /></div><b>{v}</b></div>)}</div>
              {e.correct_concepts?.length > 0 && <div><span className="label">Covered</span><div className="tags">{e.correct_concepts.map((x, j) => <span key={j} className="pill ok">✓ {x}</span>)}</div></div>}
              {e.missing_concepts?.length > 0 && <div><span className="label">Missing</span><div className="tags">{e.missing_concepts.map((x, j) => <span key={j} className="pill miss">{x}</span>)}</div></div>}
              {e.inaccuracies?.length > 0 && <div><span className="label">Inaccuracies</span><ul className="clean">{e.inaccuracies.map((x, j) => <li key={j}>{x}</li>)}</ul></div>}
              {e.improvements?.length > 0 && <div><span className="label">How to improve</span><ul className="clean">{e.improvements.map((x, j) => <li key={j}>{x}</li>)}</ul></div>}
              {e.model_answer && <div className="model"><span className="label">One possible strong answer</span><p>{e.model_answer}</p><p className="sub" style={{ marginTop: 6 }}>It isn't the only correct answer. Use it to compare structure and coverage, then say it in your own words.</p></div>}
            </div>
          </details>); })}</div>}
    </div>
  );
}
