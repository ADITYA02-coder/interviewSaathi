import { useEffect, useState } from "react";
import { api, api as API } from "../lib/api.js";
import { go, useApp } from "../App.jsx";

export default function Profile() {
  const { user, setUser, meta } = useApp();
  const [f, setF] = useState(null); const [saved, setSaved] = useState(false); const [err, setErr] = useState("");
  useEffect(() => { if (!user) go("login"); else setF({ name: user.name, education: user.education, skills: user.skills, target_role: user.target_role, preferred_language: user.preferred_language, target_companies: user.target_companies }); }, [user]);
  if (!f) return null;
  const set = (k) => (e) => { setSaved(false); setF({ ...f, [k]: e.target.value }); };
  const save = async (e) => { e.preventDefault(); setErr(""); try { setUser(await api.updateMe(f)); setSaved(true); } catch (x) { setErr(x.message); } };
  return (
    <div className="wrap stack" style={{ maxWidth: 680 }}>
      <h2 style={{ fontSize: 34 }}>Your profile</h2>
      <form className="card" onSubmit={save}>
        <div className="field"><label htmlFor="a">Name</label><input id="a" type="text" value={f.name} onChange={set("name")} /></div>
        <div className="field"><label htmlFor="b">Education</label><input id="b" type="text" value={f.education} onChange={set("education")} placeholder="B.Tech CSE, 2026, NIT Jamshedpur" /></div>
        <div className="field"><label htmlFor="c">Skills</label><textarea id="c" value={f.skills} onChange={set("skills")} placeholder="Java, Spring Boot, MySQL, React…" /></div>
        <div className="grid2">
          <div className="field"><label htmlFor="d">Target role</label><input id="d" type="text" value={f.target_role} onChange={set("target_role")} placeholder="MERN Stack Developer" /></div>
          <div className="field"><label htmlFor="g">Preferred interview language</label>
            <select id="g" value={f.preferred_language} onChange={set("preferred_language")}>{(meta?.languages || []).map((l) => <option key={l.code} value={l.code}>{l.label}</option>)}</select></div>
        </div>
        <div className="field"><label htmlFor="h">Target companies</label><input id="h" type="text" value={f.target_companies} onChange={set("target_companies")} placeholder="TCS, Infosys, Tata Steel…" /></div>
        {err && <p className="err" role="alert">{err}</p>}
        <button className="btn gold">Save profile</button> {saved && <span className="pill green" style={{ marginLeft: 10 }}>Saved</span>}
      </form>
      <Groups />
      <Support />
    </div>
  );
}

function Groups() {
  const { user, setUser } = useApp();
  const [code, setCode] = useState(""); const [msg, setMsg] = useState(""); const [err, setErr] = useState("");
  const refresh = async () => setUser(await API.me());
  const join = async (e) => { e.preventDefault(); setErr(""); setMsg(""); try { const r = await API.joinCohort(code); setMsg(`Joined ${r.name}.`); setCode(""); refresh(); } catch (x) { setErr(x.message); } };
  return (
    <div className="card">
      <h3>Practice group <span className="pill" style={{ marginLeft: 6, verticalAlign: "middle" }}>Optional</span></h3>
      <p className="sub" style={{ margin: "4px 0 12px" }}>Join a group if you have an invite code from a coach, community or organization. <b>Members' admins can see your interview scores, trends and report summaries.</b> They <u>cannot</u> read your answers or submitted code unless you turn that on below. You can leave any time.</p>
      {(user?.cohorts || []).map((c) => (
        <div key={c.id} style={{ border: "1px solid var(--line)", borderRadius: 12, padding: "10px 14px", marginBottom: 10 }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 8 }}><b>{c.name}</b><button className="btn ghost sm" onClick={async () => { await API.leaveCohort(c.id); refresh(); }}>Leave</button></div>
          <label style={{ display: "flex", gap: 8, alignItems: "center", marginTop: 8, fontSize: 14 }}><input type="checkbox" checked={c.share_transcripts} onChange={async (e) => { await API.shareCohort(c.id, e.target.checked); refresh(); }} /> Also let admins read my answers and submitted code</label>
        </div>))}
      <form onSubmit={join} style={{ display: "flex", gap: 8 }}><input type="text" placeholder="Group code, e.g. K7P2QX" value={code} onChange={(e) => setCode(e.target.value.toUpperCase())} maxLength={12} aria-label="Group code" /><button className="btn" disabled={code.length < 4}>Join</button></form>
      {user?.is_guest && <p className="sub" style={{ marginTop: 8 }}>Create an account first to join a group.</p>}
      {msg && <p className="pill green" style={{ marginTop: 8 }}>{msg}</p>}{err && <p className="err" style={{ marginTop: 8 }}>{err}</p>}
    </div>
  );
}

function Support() {
  const [f, setF] = useState({ subject: "", message: "" }); const [mine, setMine] = useState([]); const [sent, setSent] = useState(false); const [err, setErr] = useState("");
  const load = () => API.mySupport().then(setMine).catch(() => {});
  useEffect(() => { load(); }, []);
  const send = async (e) => { e.preventDefault(); setErr(""); try { await API.support(f); setSent(true); setF({ subject: "", message: "" }); load(); } catch (x) { setErr(x.message); } };
  return (
    <div className="card">
      <h3>Contact support</h3>
      <form onSubmit={send} style={{ marginTop: 10 }}>
        <div className="field"><label htmlFor="ss">Subject</label><input id="ss" type="text" required minLength={3} value={f.subject} onChange={(e) => setF({ ...f, subject: e.target.value })} /></div>
        <div className="field"><label htmlFor="sm">What's going on?</label><textarea id="sm" required minLength={5} value={f.message} onChange={(e) => setF({ ...f, message: e.target.value })} /></div>
        {err && <p className="err" role="alert" style={{ marginBottom: 10 }}>{err}</p>}
        <button className="btn">Send</button> {sent && <span className="pill green">Sent. We'll get back to you.</span>}
      </form>
      {mine.length > 0 && <div style={{ marginTop: 16 }}>{mine.map((m) => <p key={m.id} className="sub" style={{ marginTop: 6 }}><span className={`pill ${m.status === "resolved" ? "green" : "gold"}`}>{m.status}</span> <b>{m.subject}</b>{m.admin_note && <> · reply: {m.admin_note}</>}</p>)}</div>}
    </div>
  );
}
