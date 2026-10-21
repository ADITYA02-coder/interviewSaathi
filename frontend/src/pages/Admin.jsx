import { useEffect, useState } from "react";
import { api, session, API_BASE } from "../lib/api.js";
import { Trend } from "./Dashboard.jsx";
import { Ring } from "./Report.jsx";
import { useApp } from "../App.jsx";

const col = (n) => (n == null ? "var(--muted)" : n >= 75 ? "var(--green)" : n >= 55 ? "var(--gold-d)" : "var(--coral)");
const TABS = [["", "Overview"], ["leaderboard", "Leaderboard"], ["groups", "Groups & templates"], ["questions", "Questions"], ["problems", "Coding problems"], ["support", "Support"], ["users", "Users"], ["email", "Email"]];
const dt = (s) => (s ? new Date(s.endsWith("Z") ? s : s + "Z").toLocaleDateString() : "–");
const useLoad = (fn, deps = []) => { const [d, setD] = useState(null); const [e, setE] = useState(""); const reload = () => fn().then(setD).catch((x) => setE(x.message)); useEffect(() => { reload(); }, deps); return [d, e, reload]; };

export default function Admin({ path = [] }) {
  const [tab, arg] = path;
  const [st] = useLoad(() => api.get("/admin/stats"), [tab]);
  const pending = 0;
  return (
    <div className="wrap stack">
      <div><h2 style={{ fontSize: 38 }}>Admin</h2>
        <p className="sub">Scores and trends are visible only for students who joined one of your groups. Answers and submitted code are visible only if the student also allows it.</p></div>
      <div className="tabs" role="tablist" style={{ overflowX: "auto" }}>{TABS.map(([k, l]) => <button key={k} className={(tab || "") === k || (k === "leaderboard" && tab === "student") ? "on" : ""} style={{ whiteSpace: "nowrap", padding: "10px 14px" }} onClick={() => (location.hash = "#/admin/" + k)}>{l}{k === "users" && pending > 0 && <span className="pill coral" style={{ marginLeft: 6 }} title="Students waiting to be verified">{pending}</span>}</button>)}</div>
      {!tab && <Overview />}
      {tab === "leaderboard" && <Leaderboard />}
      {tab === "student" && <Student id={arg} />}
      {tab === "groups" && <Groups />}
      {tab === "questions" && <Questions />}
      {tab === "problems" && <Problems />}
      {tab === "support" && <SupportInbox />}
      {tab === "users" && <Users />}
      {tab === "email" && <EmailSetup />}
    </div>
  );
}

function Err({ e }) { return e ? <p className="err" role="alert">{e}</p> : null; }

// ------------------------------------------------------------------ overview
function Overview() {
  const [s, e] = useLoad(() => api.get("/admin/stats"));
  if (e) return <Err e={e} />;
  if (!s) return null;
  const max = Math.max(1, ...s.per_day.map((d) => d.count));
  const cards = [[s.students, "students"], [s.completed, "interviews completed"], [s.average_score ?? "–", "average score"], [s.active_7d, "active in 7 days"], [s.code_accept_rate == null ? "–" : s.code_accept_rate + "%", `code accept rate (${s.code_submissions})`], [s.open_support, "open support requests"]];
  return (
    <>
      <div className="grid3">{cards.map(([v, l]) => <div className="card stat" key={l}><b>{v}</b><span>{l}</span></div>)}</div>
      <div className="card"><h3 style={{ marginBottom: 10 }}>Interviews started, last 30 days</h3>
        <svg viewBox="0 0 600 120" style={{ width: "100%" }} role="img" aria-label="Interviews per day">
          {s.per_day.map((d, i) => <rect key={d.date} x={i * 20 + 2} y={110 - (d.count / max) * 100} width="16" height={(d.count / max) * 100 || 1} rx="3" fill="var(--teal)"><title>{d.date}: {d.count}</title></rect>)}</svg></div>
      <div className="grid2">
        <div className="card"><h3>How students answer</h3><p className="sub">By voice: <b>{s.answers_by_voice}</b> · by typing: <b>{s.answers_by_text}</b></p>
          <h3 style={{ marginTop: 14 }}>Interview types</h3><div className="tags">{Object.entries(s.types).map(([k, v]) => <span className="pill" key={k}>{k}: {v}</span>)}</div></div>
        <div className="card"><h3>Languages</h3><div className="tags">{Object.entries(s.languages).map(([k, v]) => <span className="pill" key={k}>{k}: {v}</span>)}</div>
          <p className="sub" style={{ marginTop: 14 }}>{s.guests} guests · {s.cohorts} groups · {s.interviews} interviews started</p></div>
      </div>
    </>
  );
}

// ------------------------------------------------------------------ leaderboard
async function downloadCsv(qs) {
  const r = await fetch(`${API_BASE}/api/admin/leaderboard.csv?` + qs, { headers: { Authorization: "Bearer " + session.token } });
  const url = URL.createObjectURL(await r.blob()); const a = document.createElement("a"); a.href = url; a.download = "leaderboard.csv"; a.click(); URL.revokeObjectURL(url);
}

function Leaderboard() {
  const [cohorts] = useLoad(() => api.get("/admin/cohorts"));
  const [f, setF] = useState({ cohort_id: "", interview_type: "", sort: "average" });
  const qs = new URLSearchParams(Object.entries(f).filter(([, v]) => v)).toString();
  const [rows, e] = useLoad(() => api.get("/admin/leaderboard?" + qs), [qs]);
  const set = (k) => (ev) => setF({ ...f, [k]: ev.target.value });
  return (
    <div className="card">
      <div style={{ display: "flex", gap: 10, flexWrap: "wrap", marginBottom: 14, alignItems: "center" }}>
        <select value={f.cohort_id} onChange={set("cohort_id")} style={{ width: "auto" }} aria-label="Group"><option value="">All groups</option>{(cohorts || []).map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}</select>
        <select value={f.interview_type} onChange={set("interview_type")} style={{ width: "auto" }} aria-label="Type"><option value="">All types</option>{["technical", "hr", "behavioral", "project", "mixed", "coding"].map((t) => <option key={t}>{t}</option>)}</select>
        <select value={f.sort} onChange={set("sort")} style={{ width: "auto" }} aria-label="Sort by">{[["average", "Average score"], ["latest", "Latest score"], ["best", "Best score"], ["improvement", "Most improved"], ["interviews", "Most practice"], ["problems_solved", "Problems solved"]].map(([k, l]) => <option key={k} value={k}>Sort: {l}</option>)}</select>
        <button className="btn ghost sm" style={{ marginLeft: "auto" }} onClick={() => downloadCsv(qs)}>Export CSV</button>
      </div>
      <Err e={e} />
      {rows && !rows.length && <p className="sub">No students yet. Create a group, share its code, and students appear here after they join and complete an interview.</p>}
      {rows && rows.length > 0 && <div style={{ overflowX: "auto" }}><table className="hist"><thead><tr><th>#</th><th>Student</th><th>Group</th><th>Interviews</th><th>Avg</th><th>Latest</th><th>Trend</th><th>Solved</th><th>Weakest topic</th><th>Last active</th></tr></thead><tbody>
        {rows.map((r) => (
          <tr key={r.id} style={{ cursor: "pointer" }} onClick={() => (location.hash = "#/admin/student/" + r.id)}>
            <td><b>{r.rank ?? "–"}</b></td>
            <td><b>{r.name}</b> {r.needs_attention && <span className="pill coral" title="Average under 50, or inactive for 14+ days, or no completed interview">needs attention</span>}<br /><span className="sub">{r.email}</span></td>
            <td>{(r.cohorts || []).join(", ")}</td><td>{r.interviews}</td>
            <td><b style={{ color: col(r.average) }}>{r.average ?? "–"}</b></td><td>{r.latest ?? "–"}</td>
            <td style={{ color: r.improvement == null ? "var(--muted)" : r.improvement >= 0 ? "var(--green)" : "var(--coral)", fontWeight: 700 }}>{r.improvement == null ? "–" : (r.improvement >= 0 ? "+" : "") + r.improvement}</td>
            <td>{r.problems_solved}</td><td>{r.weakest_topic || "–"}</td><td>{dt(r.last_active)}</td></tr>))}</tbody></table></div>}
    </div>
  );
}

function Student({ id }) {
  const [d, e] = useLoad(() => api.get("/admin/students/" + id), [id]);
  const [open, setOpen] = useState(null); const [detail, setDetail] = useState(null);
  if (e) return <><Err e={e} /><a href="#/admin/leaderboard">← Back</a></>;
  if (!d) return null;
  const view = async (iid) => { setOpen(iid); setDetail(null); setDetail(await api.get(`/admin/students/${id}/interviews/${iid}`)); };
  const trend = d.sessions.map((s) => ({ id: s.id, overall: s.overall }));
  return (
    <div className="stack">
      <a href="#/admin/leaderboard" style={{ fontWeight: 600 }}>← Leaderboard</a>
      <div className="card"><div style={{ display: "flex", gap: 24, flexWrap: "wrap", alignItems: "center" }}>
        {trend.length > 0 && <Ring value={Math.round(trend.reduce((a, b) => a + b.overall, 0) / trend.length)} size={120} label="average" />}
        <div style={{ flex: 1, minWidth: 220 }}><h3 style={{ fontSize: 26 }}>{d.name}</h3><p className="sub">{d.email}{d.education && ` · ${d.education}`}{d.target_role && ` · targeting ${d.target_role}`}</p>
          {d.skills && <p style={{ marginTop: 6, fontSize: 14 }}><b>Skills:</b> {d.skills}</p>}
          <p style={{ marginTop: 8 }}><span className={`pill ${d.transcripts_shared ? "green" : ""}`}>{d.transcripts_shared ? "Student shares answers and code" : "Scores only: answers and code are private"}</span> <span className="pill">{d.code.problems_solved} coding problems solved ({d.code.accepted}/{d.code.submissions} accepted)</span></p></div></div></div>
      {trend.length > 0 && <div className="card"><h3 style={{ marginBottom: 8 }}>Scores over time</h3><Trend sessions={trend} /></div>}
      <div className="grid2">
        <div className="card"><h3 style={{ marginBottom: 10 }}>Weakest topics</h3>{d.weakest.length ? d.weakest.map((t) => <div className="bar" key={t.topic}><span>{t.topic}</span><div><i style={{ width: t.score + "%", background: col(t.score) }} /></div><b>{t.score}</b></div>) : <p className="sub">None below 70.</p>}</div>
        <div className="card"><h3 style={{ marginBottom: 10 }}>Strongest topics</h3>{d.strongest.length ? d.strongest.map((t) => <div className="bar" key={t.topic}><span>{t.topic}</span><div><i style={{ width: t.score + "%", background: col(t.score) }} /></div><b>{t.score}</b></div>) : <p className="sub">None above 70 yet.</p>}</div>
      </div>
      <div className="card"><h3 style={{ marginBottom: 10 }}>Interviews</h3>
        {d.sessions.map((s) => (
          <div key={s.id} style={{ borderTop: "1px solid var(--line)", padding: "10px 0" }}>
            <div style={{ display: "flex", gap: 12, alignItems: "center", flexWrap: "wrap" }}><b style={{ color: col(s.overall), fontSize: 20 }}>{s.overall}</b><span>{s.role} · {s.type}</span><span className="sub">{dt(s.date)}</span><button className="btn ghost sm" style={{ marginLeft: "auto" }} onClick={() => (open === s.id ? setOpen(null) : view(s.id))}>{open === s.id ? "Hide" : "Details"}</button></div>
            {open === s.id && detail && (
              <div style={{ marginTop: 10, display: "grid", gap: 8 }}>
                <p><b>{detail.report.headline}</b></p>
                {Object.entries(detail.report.dimensions || {}).map(([k, v]) => <div className="bar" key={k}><span>{detail.report.dimension_labels?.[k] || k}</span><div><i style={{ width: v + "%", background: col(v) }} /></div><b>{v}</b></div>)}
                {(detail.report.problems || []).map((p) => <p key={p.id} className="sub">{p.title}: {p.skipped ? "skipped" : `${p.passed}/${p.total} tests · ${p.status}`}</p>)}
                {detail.turns ? detail.turns.map((t, i) => <p key={i} style={{ fontSize: 14 }}><b>{t.role === "candidate" ? "Student" : "Interviewer"}:</b> {t.text}{t.evaluation && <span className="pill" style={{ marginLeft: 8 }}>{t.evaluation.overall}</span>}</p>) : <p className="sub">Answers are private (the student hasn't enabled sharing).</p>}
              </div>)}
          </div>))}</div>
    </div>
  );
}

// ------------------------------------------------------------------ groups + templates
function Groups() {
  const [cohorts, e, reload] = useLoad(() => api.get("/admin/cohorts"));
  const [tpls, , reloadT] = useLoad(() => api.get("/admin/templates"));
  const [probs] = useLoad(() => api.get("/admin/problems"));
  const [name, setName] = useState("");
  const [t, setT] = useState({ name: "", cohort_id: "", role: "Java Developer", interview_type: "technical", difficulty: "intermediate", language: "en-IN", duration: "standard", code_language: "python", focus_note: "", problem_ids: [] });
  const [err, setErr] = useState("");
  const add = async (e) => { e.preventDefault(); setErr(""); try { await api.post("/admin/cohorts", { name }); setName(""); reload(); } catch (x) { setErr(x.message); } };
  const addT = async (e) => {
    e.preventDefault(); setErr("");
    const { name: n, cohort_id, focus_note, ...config } = t;
    if (config.interview_type !== "coding") { delete config.problem_ids; delete config.code_language; }
    try { await api.post("/admin/templates", { name: n, cohort_id: cohort_id ? +cohort_id : null, focus_note, config }); setT({ ...t, name: "", focus_note: "" }); reloadT(); } catch (x) { setErr(x.message); }
  };
  const S = (k) => (ev) => setT({ ...t, [k]: ev.target.value });
  return (
    <div className="stack">
      <Err e={e || err} />
      <div className="card"><h3>Groups</h3><p className="sub" style={{ margin: "4px 0 12px" }}>Create a group per batch or college. Students enter its code in their profile; that is their consent to share scores with you.</p>
        <form onSubmit={add} style={{ display: "flex", gap: 8, marginBottom: 14 }}><input type="text" placeholder="e.g. CSE 2026, NIT Jamshedpur" value={name} onChange={(e) => setName(e.target.value)} aria-label="Group name" /><button className="btn" disabled={name.trim().length < 2}>Create</button></form>
        {(cohorts || []).map((c) => (<div key={c.id} style={{ display: "flex", gap: 14, alignItems: "center", padding: "10px 0", borderTop: "1px solid var(--line)" }}><b style={{ flex: 1 }}>{c.name}</b><span className="pill gold" style={{ fontSize: 16, letterSpacing: ".12em" }}>{c.code}</span><span className="sub">{c.members} members</span>
          <button className="btn ghost sm" onClick={async () => { if (confirm("Delete this group? Students keep their own data, but you lose access to it.")) { await api.del("/admin/cohorts/" + c.id); reload(); reloadT(); } }}>Delete</button></div>))}</div>
      <div className="card"><h3>Assign an interview</h3><p className="sub" style={{ margin: "4px 0 12px" }}>Students see assigned interviews at the top of their setup page and can start with one click.</p>
        <form onSubmit={addT} className="grid2">
          <div className="field"><label>Name</label><input type="text" required minLength={3} value={t.name} onChange={S("name")} placeholder="Mock placement drive: Week 3" /></div>
          <div className="field"><label>For group</label><select value={t.cohort_id} onChange={S("cohort_id")}><option value="">Everyone</option>{(cohorts || []).map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}</select></div>
          <div className="field"><label>Role</label><input type="text" value={t.role} onChange={S("role")} /></div>
          <div className="field"><label>Type</label><select value={t.interview_type} onChange={S("interview_type")}>{["technical", "hr", "behavioral", "project", "mixed", "coding"].map((x) => <option key={x}>{x}</option>)}</select></div>
          <div className="field"><label>Difficulty</label><select value={t.difficulty} onChange={S("difficulty")}>{["beginner", "intermediate", "advanced"].map((x) => <option key={x}>{x}</option>)}</select></div>
          <div className="field"><label>Length</label><select value={t.duration} onChange={S("duration")}>{["short", "standard", "full"].map((x) => <option key={x}>{x}</option>)}</select></div>
          {t.interview_type === "coding" && <div className="field" style={{ gridColumn: "1/-1" }}><label>Specific problems (optional, otherwise chosen by difficulty)</label>
            <div className="seg">{(probs || []).filter((p) => p.active).map((p) => <button type="button" key={p.id} className={t.problem_ids.includes(p.id) ? "on" : ""} onClick={() => setT({ ...t, problem_ids: t.problem_ids.includes(p.id) ? t.problem_ids.filter((x) => x !== p.id) : [...t.problem_ids, p.id] })}>{p.title}</button>)}</div></div>}
          <div className="field" style={{ gridColumn: "1/-1" }}><label>Focus note for the interviewer (optional)</label><input type="text" value={t.focus_note} onChange={S("focus_note")} placeholder="Concentrate on OOP and collections" /></div>
          <div><button className="btn gold">Assign</button></div>
        </form>
        {(tpls || []).map((x) => <div key={x.id} style={{ display: "flex", gap: 12, alignItems: "center", padding: "10px 0", borderTop: "1px solid var(--line)" }}><div style={{ flex: 1 }}><b>{x.name}</b><br /><span className="sub">{x.group} · {x.config.interview_type} · {x.config.role}{x.focus_note && ` · ${x.focus_note}`}</span></div><button className="btn ghost sm" onClick={async () => { await api.del("/admin/templates/" + x.id); reloadT(); }}>Remove</button></div>)}</div>
    </div>
  );
}

// ------------------------------------------------------------------ question bank
const conceptsToText = (cs) => (cs || []).map(([l, s]) => `${l}: ${s.join(", ")}`).join("\n");
const textToConcepts = (t) => t.split("\n").map((l) => l.trim()).filter(Boolean).map((l) => { const [label, ...rest] = l.split(":"); return [label.trim(), rest.join(":").split(",").map((x) => x.trim()).filter(Boolean)]; });

function Questions() {
  const [bank, setBank] = useState("hr"); const [q, setQ] = useState("");
  const [data, e, reload] = useLoad(() => api.get(`/admin/questions?bank_key=${bank}&q=${encodeURIComponent(q)}`), [bank, q]);
  const blank = { id: null, bank_key: bank, topic: "", level: 2, text: "", concepts: "", followup: "", model_answer: "", active: true };
  const [form, setForm] = useState(null); const [err, setErr] = useState("");
  const save = async (ev) => {
    ev.preventDefault(); setErr("");
    const body = { bank_key: form.bank_key, topic: form.topic || "General", level: +form.level, text: form.text, concepts: textToConcepts(form.concepts), followup: form.followup, model_answer: form.model_answer, active: form.active };
    try { await (form.id ? api.put("/admin/questions/" + form.id, body) : api.post("/admin/questions", body)); setForm(null); reload(); } catch (x) { setErr(x.message); }
  };
  const S = (k) => (ev) => setForm({ ...form, [k]: ev.target.type === "checkbox" ? ev.target.checked : ev.target.value });
  return (
    <div className="card">
      <p className="sub" style={{ marginBottom: 12 }}>These questions drive the offline interviewer and are offered to the AI interviewer as a preferred pool. Concepts (one per line, <code>label: synonym, synonym</code>) are what the offline scorer looks for in answers.</p>
      <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginBottom: 14 }}>
        <div className="seg">{(data?.keys || ["hr"]).map((k) => <button key={k} className={bank === k ? "on" : ""} onClick={() => setBank(k)}>{k}</button>)}</div>
        <input type="text" placeholder="Search…" value={q} onChange={(e) => setQ(e.target.value)} style={{ maxWidth: 220 }} aria-label="Search questions" />
        <button className="btn gold sm" style={{ marginLeft: "auto" }} onClick={() => setForm({ ...blank, bank_key: bank })}>Add question</button></div>
      <Err e={e || err} />
      {form && <form onSubmit={save} className="card" style={{ marginBottom: 14, background: "#f8fbfa" }}>
        <div className="grid3"><div className="field"><label>Bank</label><select value={form.bank_key} onChange={S("bank_key")}>{(data?.keys || []).map((k) => <option key={k}>{k}</option>)}</select></div>
          <div className="field"><label>Topic</label><input type="text" value={form.topic} onChange={S("topic")} /></div>
          <div className="field"><label>Level</label><select value={form.level} onChange={S("level")}><option value={1}>1 beginner</option><option value={2}>2 intermediate</option><option value={3}>3 advanced</option></select></div></div>
        <div className="field"><label>Question (spoken aloud)</label><textarea required minLength={8} value={form.text} onChange={S("text")} /></div>
        <div className="field"><label>Key concepts</label><textarea value={form.concepts} onChange={S("concepts")} placeholder={"uses a hash map: hash, dictionary, map\\nhandles collisions: collision, chaining"} /></div>
        <div className="field"><label>Follow-up question</label><input type="text" value={form.followup} onChange={S("followup")} /></div>
        <div className="field"><label>Model answer (shown as "one possible strong answer")</label><textarea value={form.model_answer} onChange={S("model_answer")} /></div>
        <label style={{ display: "flex", gap: 8, marginBottom: 12 }}><input type="checkbox" checked={form.active} onChange={S("active")} /> Active</label>
        <div style={{ display: "flex", gap: 8 }}><button className="btn gold">Save</button><button type="button" className="btn ghost" onClick={() => setForm(null)}>Cancel</button></div></form>}
      {(data?.questions || []).map((x) => (
        <div key={x.id} style={{ borderTop: "1px solid var(--line)", padding: "12px 0", display: "flex", gap: 12, alignItems: "flex-start", opacity: x.active ? 1 : 0.5 }}>
          <div style={{ flex: 1 }}><b>{x.text}</b><br /><span className="pill">{x.topic}</span> <span className="pill">level {x.level}</span> {x.source === "builtin" && <span className="pill">built-in</span>} {!x.active && <span className="pill coral">disabled</span>}</div>
          <button className="btn ghost sm" onClick={() => setForm({ ...x, concepts: conceptsToText(x.concepts), model_answer: x.model_answer || "" })}>Edit</button>
          <button className="btn ghost sm" onClick={async () => { if (x.source === "builtin" ? true : confirm("Delete this question?")) { if (x.source === "builtin" && x.active === false) { await api.put("/admin/questions/" + x.id, { bank_key: x.bank_key, topic: x.topic, level: x.level, text: x.text, concepts: x.concepts, followup: x.followup, model_answer: x.model_answer, active: true }); } else await api.del("/admin/questions/" + x.id); reload(); } }}>{x.source === "builtin" ? (x.active ? "Disable" : "Enable") : "Delete"}</button></div>))}
    </div>
  );
}

// ------------------------------------------------------------------ coding problems
const NEW_PROBLEM = { id: "", title: "", difficulty: "easy", topic: "", statement: "", input_format: "", output_format: "", summary: "", expected_time: "", expected_space: "", approach_keywords: "", tests: [{ input: "", expected: "", hidden: false }, { input: "", expected: "", hidden: true }], active: true };

function Problems() {
  const [list, e, reload] = useLoad(() => api.get("/admin/problems"));
  const [form, setForm] = useState(null); const [err, setErr] = useState(""); const [isNew, setIsNew] = useState(false);
  const [ref, setRef] = useState({ language: "python", code: "" }); const [vres, setVres] = useState(null); const [busy, setBusy] = useState(false);
  const edit = async (id) => { const p = await api.get("/admin/problems/" + id); setForm({ ...p, approach_keywords: conceptsToText(p.approach_keywords) }); setIsNew(false); setVres(null); };
  const S = (k) => (ev) => setForm({ ...form, [k]: ev.target.type === "checkbox" ? ev.target.checked : ev.target.value });
  const setTest = (i, k, v) => setForm({ ...form, tests: form.tests.map((t, j) => (j === i ? { ...t, [k]: v } : t)) });
  const save = async (ev) => {
    ev.preventDefault(); setErr("");
    const body = { ...form, approach_keywords: textToConcepts(form.approach_keywords), tests: form.tests.map((t) => ({ input: t.input, expected: t.expected, hidden: !!t.hidden })) };
    delete body.source;
    try { await (isNew ? api.post("/admin/problems", body) : api.put("/admin/problems/" + form.id, body)); setForm(null); reload(); } catch (x) { setErr(x.message); }
  };
  const validate = async () => { setBusy(true); setVres(null); try { setVres(await api.post(`/admin/problems/${form.id}/validate`, ref)); } catch (x) { setErr(x.message); } finally { setBusy(false); } };
  return (
    <div className="card">
      <div style={{ display: "flex", marginBottom: 12, alignItems: "center" }}><p className="sub" style={{ flex: 1 }}>Problems read from standard input and print to standard output. Hidden tests never reveal their input or expected output to students.</p><button className="btn gold sm" onClick={() => { setForm(NEW_PROBLEM); setIsNew(true); setVres(null); }}>Add problem</button></div>
      <Err e={e || err} />
      {form && <form onSubmit={save} className="card" style={{ marginBottom: 14, background: "#f8fbfa" }}>
        <div className="grid3"><div className="field"><label>Id (a-z, 0-9, -)</label><input type="text" required disabled={!isNew} pattern="[a-z0-9][a-z0-9\-]{1,46}" value={form.id} onChange={S("id")} /></div>
          <div className="field"><label>Title</label><input type="text" required value={form.title} onChange={S("title")} /></div>
          <div className="field"><label>Difficulty</label><select value={form.difficulty} onChange={S("difficulty")}><option>easy</option><option>medium</option><option>hard</option></select></div>
          <div className="field"><label>Topic</label><input type="text" value={form.topic} onChange={S("topic")} /></div>
          <div className="field"><label>Expected time</label><input type="text" value={form.expected_time} onChange={S("expected_time")} placeholder="O(n)" /></div>
          <div className="field"><label>Expected space</label><input type="text" value={form.expected_space} onChange={S("expected_space")} placeholder="O(1)" /></div></div>
        <div className="field"><label>One-sentence summary (spoken by the interviewer)</label><input type="text" value={form.summary} onChange={S("summary")} /></div>
        <div className="field"><label>Statement</label><textarea required minLength={10} value={form.statement} onChange={S("statement")} /></div>
        <div className="grid2"><div className="field"><label>Input format</label><textarea value={form.input_format} onChange={S("input_format")} /></div><div className="field"><label>Output format</label><textarea value={form.output_format} onChange={S("output_format")} /></div></div>
        <div className="field"><label>Approach ideas (one per line, <code>label: synonym, synonym</code>)</label><textarea value={form.approach_keywords} onChange={S("approach_keywords")} placeholder="a hash map of seen values: hash, dictionary, map" /></div>
        <span className="label">Tests</span>
        {form.tests.map((t, i) => <div key={i} className="grid2" style={{ margin: "8px 0", alignItems: "start" }}>
          <textarea value={t.input} onChange={(ev) => setTest(i, "input", ev.target.value)} placeholder="stdin" aria-label={`Test ${i + 1} input`} style={{ minHeight: 64, fontFamily: "monospace" }} />
          <div style={{ display: "flex", gap: 8 }}><textarea value={t.expected} onChange={(ev) => setTest(i, "expected", ev.target.value)} placeholder="expected stdout" aria-label={`Test ${i + 1} expected`} style={{ minHeight: 64, fontFamily: "monospace" }} />
            <div style={{ display: "grid", gap: 6, fontSize: 13 }}><label><input type="checkbox" checked={t.hidden} onChange={(ev) => setTest(i, "hidden", ev.target.checked)} /> hidden</label><button type="button" className="btn ghost sm" onClick={() => setForm({ ...form, tests: form.tests.filter((_, j) => j !== i) })} disabled={form.tests.length <= 2}>✕</button></div></div></div>)}
        <button type="button" className="btn ghost sm" onClick={() => setForm({ ...form, tests: [...form.tests, { input: "", expected: "", hidden: true }] })}>Add test</button>
        <label style={{ display: "flex", gap: 8, margin: "12px 0" }}><input type="checkbox" checked={form.active} onChange={S("active")} /> Active (visible to students)</label>
        <div style={{ display: "flex", gap: 8 }}><button className="btn gold">Save</button><button type="button" className="btn ghost" onClick={() => setForm(null)}>Cancel</button></div>
        {!isNew && <div style={{ marginTop: 16, borderTop: "1px solid var(--line)", paddingTop: 12 }}><span className="label">Validate with your reference solution</span>
          <div style={{ display: "flex", gap: 8, margin: "8px 0" }}><select value={ref.language} onChange={(ev) => setRef({ ...ref, language: ev.target.value })} style={{ width: "auto" }}><option value="python">python</option><option value="javascript">javascript</option><option value="java">java</option></select>
            <button type="button" className="btn ghost sm" disabled={busy || !ref.code.trim()} onClick={validate}>{busy ? "Running…" : "Run against all tests"}</button></div>
          <textarea value={ref.code} onChange={(ev) => setRef({ ...ref, code: ev.target.value })} placeholder="Paste a correct solution to prove the expected outputs are right…" style={{ fontFamily: "monospace", minHeight: 100 }} />
          {vres && <p style={{ marginTop: 8 }}><span className={`pill ${vres.status === "accepted" ? "green" : "coral"}`}>{vres.status}</span> {vres.passed}/{vres.total} passed{vres.tests.filter((t) => t.status !== "pass").map((t) => <span key={t.i} className="sub"> · test {t.i}: {t.status}</span>)}</p>}</div>}
      </form>}
      {(list || []).map((p) => <div key={p.id} style={{ display: "flex", gap: 10, alignItems: "center", padding: "10px 0", borderTop: "1px solid var(--line)", opacity: p.active ? 1 : 0.5 }}>
        <b style={{ flex: 1 }}>{p.title}</b><span className="pill">{p.topic}</span><span className="pill">{p.difficulty}</span><span className="sub">{p.tests} tests</span>{p.source === "builtin" && <span className="pill">built-in</span>}
        <button className="btn ghost sm" onClick={() => edit(p.id)}>Edit</button>
        <button className="btn ghost sm" onClick={async () => { if (p.active ? confirm("Remove this problem for students? (Built-in problems and problems with submissions are hidden, not deleted.)") : true) { if (p.active) await api.del("/admin/problems/" + p.id); else { const full = await api.get("/admin/problems/" + p.id); await api.put("/admin/problems/" + p.id, { ...full, active: true }); } reload(); } }}>{p.active ? "Remove" : "Restore"}</button></div>)}
    </div>
  );
}

// ------------------------------------------------------------------ support + users
function SupportInbox() {
  const [rows, e, reload] = useLoad(() => api.get("/admin/support"));
  const [notes, setNotes] = useState({});
  return (
    <div className="card"><Err e={e} />
      {rows && !rows.length && <p className="sub">No requests.</p>}
      {(rows || []).map((s) => (
        <div key={s.id} style={{ borderTop: "1px solid var(--line)", padding: "12px 0" }}>
          <div style={{ display: "flex", gap: 10, alignItems: "center", flexWrap: "wrap" }}><span className={`pill ${s.status === "open" ? "gold" : "green"}`}>{s.status}</span><b>{s.subject}</b><span className="sub">{s.from} · {s.email} · {dt(s.created_at)}</span></div>
          <p style={{ margin: "6px 0 8px" }}>{s.message}</p>
          <div style={{ display: "flex", gap: 8 }}><input type="text" placeholder="Reply note (the student sees this)" value={notes[s.id] ?? s.admin_note} onChange={(ev) => setNotes({ ...notes, [s.id]: ev.target.value })} aria-label="Reply note" />
            <button className="btn sm" onClick={async () => { await api.put("/admin/support/" + s.id, { status: s.status === "open" ? "resolved" : "open", admin_note: notes[s.id] ?? s.admin_note }); reload(); }}>{s.status === "open" ? "Resolve" : "Reopen"}</button></div></div>))}
    </div>
  );
}

function Users() {
  const [search, setSearch] = useState(""); const [only, setOnly] = useState(false);
  const [rows, e, reload] = useLoad(() => api.get(`/admin/users?search=${encodeURIComponent(search)}${only ? "&unverified=true" : ""}`), [search, only]);
  const unverified = (rows || []).filter((u) => !u.verified && u.role === "student");
  const verifyAll = async () => {
    if (!confirm(`Mark ${unverified.length} student${unverified.length === 1 ? "" : "s"} as verified?`)) return;
    await api.post("/admin/users/verify", { ids: unverified.map((u) => u.id) }); reload();
  };
  return (
    <div className="card">
      <div style={{ display: "flex", gap: 10, flexWrap: "wrap", alignItems: "center", marginBottom: 12 }}>
        <input type="text" placeholder="Search name or email" value={search} onChange={(ev) => setSearch(ev.target.value)} style={{ maxWidth: 320 }} aria-label="Search users" />
        <label style={{ display: "flex", gap: 6, alignItems: "center", fontWeight: 600 }}><input type="checkbox" checked={only} onChange={(ev) => setOnly(ev.target.checked)} /> Unverified only</label>
        {unverified.length > 0 && <button className="btn gold sm" style={{ marginLeft: "auto" }} onClick={verifyAll}>Verify all {unverified.length} shown</button>}
      </div>
      <Err e={e} />
      <div style={{ overflowX: "auto" }}><table className="hist"><thead><tr><th>Name</th><th>Email</th><th>Role</th><th>Verified</th><th>Interviews</th><th>Joined</th><th /></tr></thead><tbody>
        {(rows || []).map((u) => <tr key={u.id}><td><b>{u.name}</b></td><td>{u.email}</td><td><span className={`pill ${u.role === "admin" ? "gold" : ""}`}>{u.role}</span></td><td>{u.verified ? "✓" : <button className="btn ghost sm" title="Mark this student as verified" onClick={async () => { await api.put(`/admin/users/${u.id}/verify`, {}); reload(); }}>Mark verified</button>}</td><td>{u.interviews}</td><td>{dt(u.joined)}</td>
          <td><button className="btn ghost sm" onClick={async () => { try { await api.put(`/admin/users/${u.id}/role`, { role: u.role === "admin" ? "student" : "admin" }); reload(); } catch (x) { alert(x.message); } }}>{u.role === "admin" ? "Make student" : "Make admin"}</button></td></tr>)}</tbody></table></div>
      {rows && !rows.length && <p className="sub" style={{ marginTop: 10 }}>{only ? "Everyone is verified. 🎉" : "No users found."}</p>}
    </div>
  );
}

// ------------------------------------------------------------------ email setup + test
const PRESETS = `# Brevo (free 300/day; works on Render's free tier thanks to port 2525)
SMTP_HOST=smtp-relay.brevo.com
SMTP_PORT=2525
SMTP_USER=<the Login shown in Brevo > SMTP & API>
SMTP_PASSWORD=<your Brevo SMTP key>
SMTP_FROM=InterviewSaathi <your-verified-sender@yourcollege.edu>

# Gmail (App Password; NOT usable on Render free, which blocks 587/465)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=you@gmail.com
SMTP_PASSWORD=<16-character app password>
SMTP_FROM=InterviewSaathi <you@gmail.com>`;

function EmailSetup() {
  const { user } = useApp();
  const [st, e] = useLoad(() => api.get("/admin/email"));
  const [to, setTo] = useState(user?.email || ""); const [res, setRes] = useState(null); const [busy, setBusy] = useState(false);
  if (e) return <Err e={e} />;
  if (!st) return null;
  const send = async (ev) => { ev.preventDefault(); setBusy(true); setRes(null); try { setRes(await api.post("/admin/email/test", { to })); } catch (x) { setRes({ ok: false, error: x.message }); } finally { setBusy(false); } };
  const localLink = /localhost|127\.0\.0\.1/.test(st.app_url) && !/localhost|127\.0\.0\.1/.test(location.hostname);
  return (
    <div className="stack">
      <div className="card">
        <h3>Email (SMTP) status</h3>
        {st.configured ? (
          <p style={{ margin: "8px 0" }}><span className="pill green">configured</span> sending through <b>{st.host}:{st.port}</b> ({st.security}) as <b>{st.from}</b> · login <code>{st.user || "none"}</code></p>
        ) : <p className="notice" style={{ margin: "8px 0" }}>SMTP isn't configured, so verification and password-reset emails are only <b>printed in the server log</b> and nobody receives them. Add the SMTP variables below, then restart the server.</p>}
        <p className="sub">Verification mode: <b>{st.verification_mode}</b>{st.verification_mode === "admin" && " (students get no email; set EMAIL_VERIFICATION=email to send links)"}. Links in emails start with <code>{st.app_url}</code>.</p>
        {localLink && <p className="err" style={{ marginTop: 10 }}>APP_URL is still {st.app_url}, so links in emails would point to localhost. Set APP_URL to the address people really use.</p>}
      </div>
      <div className="card">
        <h3>Send a test email</h3>
        <p className="sub" style={{ margin: "4px 0 12px" }}>Sends right now and shows the exact problem if it fails. Check the spam folder too.</p>
        <form onSubmit={send} style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
          <input type="email" required placeholder="you@gmail.com" value={to} onChange={(ev) => setTo(ev.target.value)} aria-label="Send test email to" style={{ maxWidth: 340 }} />
          <button className="btn gold" disabled={busy || !st.configured}>{busy ? "Sending…" : "Send test email"}</button>
        </form>
        {res && (res.ok ? <p className="pill green" style={{ marginTop: 12 }}>Sent. Check the inbox of {to} (and spam).</p> : <p className="err" role="alert" style={{ marginTop: 12 }}>{res.error}</p>)}
      </div>
      <div className="card"><h3>Settings to add on the server</h3><p className="sub" style={{ margin: "4px 0 8px" }}>Put these in <code>.env</code> (or Render's Environment tab), restart, then test above. Full steps: SMTP_SETUP.md.</p><pre style={{ maxHeight: 340 }}>{PRESETS}</pre></div>
    </div>
  );
}
