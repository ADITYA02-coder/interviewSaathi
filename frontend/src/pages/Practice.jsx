import { useEffect, useState } from "react";
import CodeEditor from "../components/CodeEditor.jsx";
import CodeResult from "../components/CodeResult.jsx";
import ProblemView from "../components/ProblemView.jsx";
import { api } from "../lib/api.js";
import { go, useApp } from "../App.jsx";

const tone = (d) => (d === "easy" ? "green" : d === "medium" ? "gold" : "coral");

export function PracticeList() {
  const { meta, ensureUser } = useApp();
  const [list, setList] = useState(null); const [f, setF] = useState("all"); const [err, setErr] = useState("");
  useEffect(() => { ensureUser().then(() => api.problems()).then(setList).catch((e) => setErr(e.message)); }, []);
  const shown = (list || []).filter((p) => f === "all" || (f === "unsolved" ? !p.solved : p.difficulty === f));
  return (
    <div className="wrap" style={{ maxWidth: 820 }}>
      <h2 style={{ fontSize: 38, marginBottom: 6 }}>Coding practice</h2>
      <p className="sub" style={{ marginBottom: 18 }}>Solve problems in Python, JavaScript or Java. Your code runs in an isolated sandbox against sample and hidden tests. For the full experience with a spoken interviewer, start a <a href="#/setup">coding interview</a>.</p>
      {meta && !meta.coding_enabled && <p className="notice" style={{ marginBottom: 16 }}>The code runner isn't configured on this server yet, so you can read problems but not run code.</p>}
      <div className="seg" style={{ marginBottom: 16 }}>{[["all", "All"], ["easy", "Easy"], ["medium", "Medium"], ["hard", "Hard"], ["unsolved", "Unsolved"]].map(([k, l]) => <button key={k} className={f === k ? "on" : ""} onClick={() => setF(k)}>{l}</button>)}</div>
      {err && <p className="err">{err}</p>}
      <div className="plist">{shown.map((p) => (
        <a key={p.id} className="prow" href={`#/code/${p.id}`}><b>{p.title}</b><span className="pill">{p.topic}</span><span className={`pill ${tone(p.difficulty)}`}>{p.difficulty}</span>{p.solved && <span className="pill green">solved ✓</span>}</a>))}
        {list && !shown.length && <p className="sub">Nothing here yet.</p>}</div>
    </div>
  );
}

export function PracticeSolve({ id }) {
  const { meta, ensureUser } = useApp();
  const [p, setP] = useState(null); const [lang, setLang] = useState("python"); const [codes, setCodes] = useState({});
  const [res, setRes] = useState(null); const [busy, setBusy] = useState(""); const [err, setErr] = useState("");
  useEffect(() => { ensureUser().then(() => api.problem(id)).then((x) => { setP(x); if (x.last_submission) { setLang(x.last_submission.language); setCodes({ [x.last_submission.language]: x.last_submission.code }); } }).catch((e) => setErr(e.message)); }, [id]);
  if (err) return <div className="wrap"><p className="err">{err}</p></div>;
  if (!p) return null;
  const code = codes[lang] ?? p.starters[lang];
  const act = (kind) => async () => {
    setBusy(kind); setErr("");
    try { setRes(await (kind === "run" ? api.practiceRun : api.practiceSubmit)(id, { language: lang, code })); } catch (e) { setErr(e.message); } finally { setBusy(""); }
  };
  return (
    <div className="wrap">
      <a href="#/code" style={{ fontWeight: 600 }}>← All problems</a>
      <div className="solve" style={{ marginTop: 14 }}>
        <div className="card"><ProblemView problem={p} /></div>
        <div className="stack">
          <div className="bar-row" style={{ display: "flex", gap: 8, flexWrap: "wrap", alignItems: "center" }}>
            <select value={lang} onChange={(e) => { setLang(e.target.value); setRes(null); }} style={{ width: "auto" }} aria-label="Language">{Object.entries(meta?.code_languages || { python: "Python 3" }).map(([k, v]) => <option key={k} value={k}>{v}</option>)}</select>
            <button className="btn ghost sm" onClick={act("run")} disabled={!!busy}>{busy === "run" ? "Running…" : "Run samples"}</button>
            <button className="btn gold sm" onClick={act("submit")} disabled={!!busy}>{busy === "submit" ? "Judging…" : "Submit"}</button>
          </div>
          <CodeEditor value={code} onChange={(v) => setCodes({ ...codes, [lang]: v })} language={lang} onRun={act("run")} minRows={18} />
          {err && <p className="err" role="alert">{err}</p>}
          <CodeResult result={res} />
        </div>
      </div>
    </div>
  );
}
