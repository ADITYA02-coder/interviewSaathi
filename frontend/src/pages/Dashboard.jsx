import { useEffect, useState } from "react";
import { api } from "../lib/api.js";
import { go, useApp } from "../App.jsx";
import { Ring } from "./Report.jsx";

const col = (n) => (n >= 75 ? "var(--green)" : n >= 55 ? "var(--gold-d)" : "var(--coral)");
const LABEL = { accuracy: "Accuracy / specificity", relevance: "Relevance", completeness: "Completeness", clarity: "Clarity" };

export function Trend({ sessions }) {
  const W = 640, H = 200, pad = 28, n = sessions.length;
  const x = (i) => pad + (n === 1 ? (W - 2 * pad) / 2 : (i * (W - 2 * pad)) / (n - 1)), y = (v) => H - pad - ((H - 2 * pad) * v) / 100;
  const pts = sessions.map((s, i) => `${x(i)},${y(s.overall)}`).join(" ");
  return (
    <svg viewBox={`0 0 ${W} ${H}`} style={{ width: "100%", height: "auto" }} role="img" aria-label="Overall score for each interview over time">
      {[0, 50, 100].map((g) => <g key={g}><line x1={pad} x2={W - pad} y1={y(g)} y2={y(g)} stroke="#e4ecea" /><text x="2" y={y(g) + 4} fontSize="11" fill="#5a707a">{g}</text></g>)}
      {n > 1 && <polyline points={pts} fill="none" stroke="var(--teal)" strokeWidth="3" strokeLinejoin="round" />}
      {sessions.map((s, i) => <g key={s.id}><circle cx={x(i)} cy={y(s.overall)} r="6" fill={col(s.overall)} stroke="#fff" strokeWidth="2" /><text x={x(i)} y={y(s.overall) - 12} textAnchor="middle" fontSize="12" fontWeight="700" fill="var(--ink)">{s.overall}</text></g>)}
    </svg>
  );
}

export default function Dashboard() {
  const { user } = useApp();
  const [d, setD] = useState(null); const [list, setList] = useState([]); const [err, setErr] = useState("");
  const load = () => Promise.all([api.dashboard(), api.interviews()]).then(([a, b]) => { setD(a); setList(b); }).catch((e) => setErr(e.message));
  useEffect(() => { if (!user) { setD({ total_completed: 0 }); return; } load(); }, [user]);
  if (err) return <div className="wrap"><p className="err">{err}</p></div>;
  if (!d) return null;
  if (!d.total_completed && !list.length) return (
    <div className="wrap"><div className="card empty"><h2 style={{ fontSize: 32 }}>Your progress will appear here</h2><p className="sub" style={{ maxWidth: 460 }}>Finish a mock interview and this page fills with your real scores, strongest and weakest topics, and what to practise next. Nothing is shown until it's earned.</p><a className="btn gold lg" href="#/setup">Start your first interview</a></div></div>);

  const remove = async (id) => { if (confirm("Delete this interview and its transcript?")) { await api.remove(id); load(); } };
  const fv = d.first_vs_latest;
  const practise = (topic) => { sessionStorage.setItem("is_prefill", JSON.stringify({ jd_text: `Focus most of the questions on: ${topic}.` })); go("setup"); };
  return (
    <div className="wrap stack">
      <h2 style={{ fontSize: 38 }}>Your progress</h2>
      {user?.is_guest && <p className="notice">You're using a guest account. <a href="#/login">Create a free account</a> to keep this history on any device.</p>}
      <div className="grid3">
        <div className="card stat"><b>{d.total_completed}</b><span>interviews completed</span></div>
        <div className="card stat"><b>{d.average_overall ?? "–"}</b><span>average score</span></div>
        <div className="card stat"><b>{d.sessions.length ? d.sessions[d.sessions.length - 1].overall : "–"}</b><span>latest score</span></div>
      </div>
      {d.sessions.length > 0 && <div className="card"><h3 style={{ marginBottom: 8 }}>Score over time</h3><Trend sessions={d.sessions} /></div>}
      <div className="grid2">
        <div className="card"><h3 style={{ marginBottom: 10 }}>Weakest topics</h3>
          {d.weakest_topics.length ? d.weakest_topics.map((t) => <div className="bar" key={t.topic}><span>{t.topic}</span><div><i style={{ width: t.score + "%", background: col(t.score) }} /></div><b>{t.score}</b></div>) : <p className="sub">No weak topics yet. Nice.</p>}
          {d.recommended_practice.length > 0 && <div style={{ marginTop: 14 }}><span className="label">Practise next</span><div className="tags">{d.recommended_practice.map((t) => <button key={t} className="pill gold" style={{ border: 0, cursor: "pointer" }} onClick={() => practise(t)}>{t} →</button>)}</div></div>}</div>
        <div className="card"><h3 style={{ marginBottom: 10 }}>Strongest topics</h3>
          {d.strongest_topics.length ? d.strongest_topics.map((t) => <div className="bar" key={t.topic}><span>{t.topic}</span><div><i style={{ width: t.score + "%", background: col(t.score) }} /></div><b>{t.score}</b></div>) : <p className="sub">Topics scoring 70+ will show up here.</p>}</div>
      </div>
      {fv && <div className="card"><h3 style={{ marginBottom: 10 }}>First attempt vs latest</h3>
        <div className="grid2" style={{ alignItems: "center" }}>
          <div style={{ display: "flex", gap: 24, justifyContent: "center" }}><Ring value={fv.first.overall} size={120} label="first" /><Ring value={fv.latest.overall} size={120} label="latest" /></div>
          <div>{Object.keys(LABEL).map((k) => { const diff = fv.latest.dimensions[k] - fv.first.dimensions[k]; return <div className="bar" key={k} style={{ gridTemplateColumns: "170px 1fr" }}><span>{LABEL[k]}</span><b style={{ color: diff >= 0 ? "var(--green)" : "var(--coral)" }}>{fv.first.dimensions[k]} → {fv.latest.dimensions[k]} ({diff >= 0 ? "+" : ""}{diff})</b></div>; })}</div></div></div>}
      <div className="card"><h3 style={{ marginBottom: 10 }}>Interview history</h3>
        <div style={{ overflowX: "auto" }}><table className="hist"><thead><tr><th>Date</th><th>Role</th><th>Type</th><th>Score</th><th /></tr></thead><tbody>
          {list.map((i) => <tr key={i.id}><td>{new Date(i.started_at + "Z").toLocaleDateString()}</td><td>{i.config.role}</td><td>{i.config.interview_type}</td>
            <td>{i.status === "completed" ? <b style={{ color: col(i.overall_score) }}>{Math.round(i.overall_score)}</b> : <span className="pill">unfinished</span>}</td>
            <td style={{ textAlign: "right", whiteSpace: "nowrap" }}>{i.status === "completed" && <a className="btn ghost sm" href={`#/report/${i.id}`}>Report</a>} <button className="btn ghost sm" onClick={() => remove(i.id)}>Delete</button></td></tr>)}
        </tbody></table></div></div>
    </div>
  );
}
