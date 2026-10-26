import { useEffect, useRef, useState } from "react";
import Avatar from "../components/Avatar.jsx";
import { api } from "../lib/api.js";
import { VoiceRecorder } from "../lib/recorder.js";
import { Speaker } from "../lib/speaker.js";
import { go, useApp } from "../App.jsx";

const TYPES = [["technical", "Technical"], ["hr", "HR"], ["behavioral", "Behavioural"], ["project", "Project-based"], ["mixed", "Mixed"], ["coding", "Coding round"]];
const LEVELS = [["beginner", "Beginner"], ["intermediate", "Intermediate"], ["advanced", "Advanced"]];
const EXP = [["student", "Student"], ["fresher", "Fresher"], ["experienced", "Experienced"]];
const DUR = [["short", "Short · 4 questions"], ["standard", "Standard · 7"], ["full", "Full mock · 12"]];
const DUR_CODE = [["short", "Short · 1 problem"], ["standard", "Standard · 2 problems"], ["full", "Full · 3 problems"]];
const SAMPLE = { "en-IN": "Hello! I'm your interviewer. Can you hear me clearly?", "hi-IN": "नमस्ते! मैं आपकी इंटरव्यूअर हूँ। क्या आप मुझे साफ़ सुन पा रहे हैं?", hinglish: "Namaste! Main aapki interviewer hoon. Kya aap mujhe clearly sun pa rahe hain?" };

function Seg({ value, onChange, options, disabledFn }) {
  return <div className="seg" role="group">{options.map(([v, l]) => <button type="button" key={v} className={value === v ? "on" : ""} aria-pressed={value === v} disabled={disabledFn?.(v)} onClick={() => onChange(v)}>{l}</button>)}</div>;
}

export default function Setup() {
  const { user, meta, ensureUser } = useApp();
  const pre = useRef(JSON.parse(sessionStorage.getItem("is_prefill") || "null")).current;
  const [c, setC] = useState({ role: pre?.role || user?.target_role || "Java Developer", interview_type: pre?.interview_type || "technical", difficulty: "intermediate", experience: "fresher", language: user?.preferred_language || "en-IN", duration: "standard", interviewer: "female", voice_speed: 1, code_language: "python", focus_note: "", problem_ids: [] });
  const [tpls, setTpls] = useState([]); const [applied, setApplied] = useState("");
  const [custom, setCustom] = useState(false);
  const [jd, setJd] = useState(pre?.jd_text || ""); const [resume, setResume] = useState(""); const [resumeName, setResumeName] = useState("");
  const [busy, setBusy] = useState(false); const [err, setErr] = useState("");
  const [mic, setMic] = useState("idle"); const [heard, setHeard] = useState(""); const [micMsg, setMicMsg] = useState("");
  const level = useRef(0), meterEl = useRef(null), rec = useRef(null), spk = useRef(null);
  const set = (k) => (v) => setC((o) => ({ ...o, [k]: v }));
  const langs = meta?.languages || [{ code: "en-IN", label: "English", male: true }];
  const lang = langs.find((l) => l.code === c.language) || langs[0];

  useEffect(() => { if (user && !user.is_guest) api.templates().then(setTpls).catch(() => {}); }, [user]);
  useEffect(() => { sessionStorage.removeItem("is_prefill"); let raf; const loop = () => { if (meterEl.current) meterEl.current.style.width = Math.round(level.current * 100) + "%"; raf = requestAnimationFrame(loop); }; raf = requestAnimationFrame(loop); return () => { cancelAnimationFrame(raf); rec.current?.close(); spk.current?.stop(); }; }, []);
  useEffect(() => { if (c.interviewer === "male" && lang && !lang.male) set("interviewer")("female"); }, [c.language]);

  const testMic = async () => {
    setMicMsg(""); setMic("testing");
    try {
      rec.current?.close(); rec.current = new VoiceRecorder({ levelRef: level });
      await rec.current.open(); rec.current.listening = true; setMic("ok");
      setMicMsg("Say something. The bar should move.");
    } catch { setMic("denied"); setMicMsg("Microphone blocked. You can still practise by typing, or allow the mic in your browser's address bar."); }
  };
  const testVoice = async () => {
    spk.current ||= new Speaker({ current: 0 });
    await spk.current.unlock(); setHeard("playing");
    const voiceMap = { female: { "en-IN": "Kaveri", "hi-IN": "Nalini", hinglish: "Poorvi" }, male: { "en-IN": "Pranav", "hi-IN": "Deepak", hinglish: "Deepak" } };
    const tl = c.language === "hinglish" ? "auto" : c.language;
    const voice = voiceMap[c.interviewer]?.[c.language] || "Kaveri";
    let fb = false;
    await spk.current.speak(SAMPLE[c.language] || SAMPLE["en-IN"], { voice, tts_language: tl, language: c.language, speed: c.voice_speed, onFallback: () => (fb = true) });
    setHeard(fb ? "fallback" : "done");
  };

  const onResume = async (e) => {
    const file = e.target.files?.[0]; if (!file) return; setErr("");
    try { await ensureUser(); const r = await api.parseResume(file); setResume(r.text); setResumeName(file.name); } catch (x) { setErr(x.message); }
  };

  const start = async () => {
    setBusy(true); setErr("");
    try {
      await ensureUser();
      rec.current?.close(); spk.current?.stop();
      const r = await api.createInterview({ config: c, resume_text: resume, jd_text: jd });
      sessionStorage.setItem("is_room_" + r.id, JSON.stringify(r));
      go("room/" + r.id);
    } catch (x) { setErr(x.message); setBusy(false); }
  };

  return (
    <div className="wrap">
      <h2 style={{ fontSize: 38, marginBottom: 6 }}>Set up your interview</h2>
      <p className="sub" style={{ marginBottom: 24 }}>Takes about 30 seconds. Your choices decide the questions and how answers are judged.</p>
      {tpls.length > 0 && <div className="card" style={{ marginBottom: 20 }}><h3>Assigned to you</h3><p className="sub" style={{ marginBottom: 10 }}>Your placement team set these up. Pick one to fill in the settings.</p>
        <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>{tpls.map((t) => <button key={t.id} type="button" className={`btn ${applied === t.id ? "gold" : "ghost"}`} onClick={() => { setApplied(t.id); setC((o) => ({ ...o, ...t.config, focus_note: t.focus_note || "", problem_ids: t.config.problem_ids || [] })); setCustom(false); }}>{t.name}{t.group ? ` · ${t.group}` : ""}</button>)}</div></div>}
      <div className="setup">
        <div className="stack">
          <div className="card">
            <div className="field"><span className="label">Job role</span>
              <select value={custom ? "__other" : c.role} onChange={(e) => { if (e.target.value === "__other") { setCustom(true); set("role")(""); } else { setCustom(false); set("role")(e.target.value); } }} aria-label="Job role">
                {(meta?.roles?.length ? meta.roles : ["Java Developer"]).map((r) => <option key={r}>{r}</option>)}<option value="__other">Other (type your own)</option></select>
              {custom && <input type="text" placeholder="e.g. DevOps Engineer" value={c.role} onChange={(e) => set("role")(e.target.value)} aria-label="Custom role" />}</div>
            <div className="field"><span className="label">Interview type</span><Seg value={c.interview_type} onChange={set("interview_type")} options={TYPES} disabledFn={(v) => v === "coding" && meta && !meta.coding_enabled} />
            {meta && !meta.coding_enabled && <p className="sub">Coding rounds need the code-runner service, which isn't running on this server.</p>}</div>
            <div className="field"><span className="label">Difficulty</span><Seg value={c.difficulty} onChange={set("difficulty")} options={LEVELS} /></div>
            <div className="field"><span className="label">Experience level</span><Seg value={c.experience} onChange={set("experience")} options={EXP} /></div>
            {c.interview_type === "coding" && <div className="field"><span className="label">Programming language</span><Seg value={c.code_language} onChange={set("code_language")} options={Object.entries(meta?.code_languages || { python: "Python 3" })} />
              <p className="sub">The interviewer asks for your approach, you code and test it in the browser, and she follows up on complexity and edge cases. Your code runs in an isolated sandbox.</p></div>}
            <div className="field"><span className="label">Length</span><Seg value={c.duration} onChange={set("duration")} options={c.interview_type === "coding" ? DUR_CODE : DUR} /></div>
            <div className="field" style={{ marginBottom: 0 }}><span className="label">Language</span>
              <Seg value={c.language} onChange={set("language")} options={langs.map((l) => [l.code, l.label + (l.beta ? " (beta)" : "")])} />
              {c.language === "hinglish" && <p className="sub">Hinglish speech recognition is experimental; if it misfires the app falls back to Hindi recognition.</p>}
              {lang?.beta && <p className="sub">Regional languages are in beta: the interviewer speaks {lang.label} and keeps technical terms in English.</p>}</div>
          </div>
          <div className="card">
            <h3>Make it about you <span className="pill">optional</span></h3>
            <p className="sub" style={{ marginBottom: 14 }}>Add a resume and/or a job description and the interviewer will ask about your real projects and the role's requirements.</p>
            <div className="field"><label htmlFor="rf">Resume (PDF, DOCX or TXT)</label><input id="rf" type="file" accept=".pdf,.docx,.txt" onChange={onResume} />{resumeName && <span className="pill green" style={{ justifySelf: "start" }}>Read {resumeName} ({resume.length.toLocaleString()} characters)</span>}</div>
            <div className="field" style={{ marginBottom: 0 }}><label htmlFor="jd">Job description</label><textarea id="jd" value={jd} onChange={(e) => setJd(e.target.value)} placeholder="Paste the job description here…" /></div>
            <p className="sub" style={{ marginTop: 10 }}>Your resume text is used only to run this interview and is stored with it. You can delete any interview from your dashboard.</p>
          </div>
        </div>

        <div className="stack" style={{ position: "sticky", top: 84 }}>
          <div className="card">
            <h3>Your interviewer</h3>
            <div className="persona-pick" style={{ margin: "12px 0" }}>
              {[["female", "Ananya"], ["male", "Arjun"]].map(([k, n]) => (
                <button type="button" key={k} className={c.interviewer === k ? "on" : ""} aria-pressed={c.interviewer === k} disabled={k === "male" && !lang?.male} onClick={() => set("interviewer")(k)}>
                  <div className="ph"><Avatar persona={k} state="listening" /></div><span>{n}</span></button>))}
            </div>
            <div className="field"><label htmlFor="sp">Speaking speed: {c.voice_speed.toFixed(2)}×</label><input id="sp" type="range" min="0.85" max="1.15" step="0.05" value={c.voice_speed} onChange={(e) => set("voice_speed")(parseFloat(e.target.value))} /></div>
            <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
              <button type="button" className="btn ghost sm" onClick={testVoice} disabled={heard === "playing"}>{heard === "playing" ? "Playing…" : "Hear the voice"}</button>
              <button type="button" className="btn ghost sm" onClick={testMic}>{mic === "ok" ? "Mic working ✓" : "Test my microphone"}</button>
            </div>
            {mic === "ok" && <div className="meter" style={{ marginTop: 12 }} aria-label="Microphone level"><i ref={meterEl} /></div>}
            {micMsg && <p className={mic === "denied" ? "err" : "sub"} style={{ marginTop: 10 }}>{micMsg}</p>}
            {heard === "fallback" && <p className="notice" style={{ marginTop: 10 }}>The enhanced voice is temporarily unavailable, so we played a browser voice instead.</p>}
            {meta && !meta.gnani_configured && <p className="notice" style={{ marginTop: 10 }}>Voice mode is temporarily unavailable. You can still have a complete interview by typing your answers.</p>}
          </div>
          <div className="card">
            {err && <p className="err" role="alert" style={{ marginBottom: 12 }}>{err}</p>}
            <button className="btn gold lg" style={{ width: "100%" }} onClick={start} disabled={busy || !c.role.trim()}>{busy ? "Preparing your interviewer…" : "Start interview"}</button>
            <p className="sub" style={{ marginTop: 10, textAlign: "center" }}>Questions: {meta?.llm_live ? "adaptive AI" : "curated practice bank"} · voice: {meta?.gnani_configured ? "natural voice" : "text mode"}</p>
          </div>
        </div>
      </div>
    </div>
  );
}
