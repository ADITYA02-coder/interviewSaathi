import { useEffect, useRef, useState } from "react";
import Avatar from "../components/Avatar.jsx";
import CodeEditor from "../components/CodeEditor.jsx";
import CodeResult from "../components/CodeResult.jsx";
import ProblemView from "../components/ProblemView.jsx";
import { api, session } from "../lib/api.js";
import { VoiceRecorder } from "../lib/recorder.js";
import { Speaker } from "../lib/speaker.js";
import { go, useApp } from "../App.jsx";

const P = {
  mic: "M12 2a3 3 0 0 0-3 3v7a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3Z M19 10v2a7 7 0 0 1-14 0v-2 M12 19v3",
  micoff: "M12 2a3 3 0 0 0-3 3v7a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3Z M19 10v2a7 7 0 0 1-14 0v-2 M12 19v3 M2 2l20 20",
  cam: "M23 7l-7 5 7 5V7z M1 5h15a2 2 0 0 1 2 2v10a2 2 0 0 1-2 2H1z",
  camoff: "M23 7l-7 5 7 5V7z M1 5h15a2 2 0 0 1 2 2v10a2 2 0 0 1-2 2H1z M2 2l20 20",
  cc: "M3 5h18v14H3z M7 12h3 M14 12h3 M7 15h6",
  list: "M8 6h13 M8 12h13 M8 18h13 M3 6h.01 M3 12h.01 M3 18h.01",
  replay: "M3 12a9 9 0 1 0 3-6.7L3 8 M3 3v5h5",
  skip: "M5 4l10 8-10 8z M19 5v14",
  kb: "M2 6h20v12H2z M6 10h.01 M10 10h.01 M14 10h.01 M18 10h.01 M7 14h10",
  check: "M20 6L9 17l-5-5",
  x: "M18 6L6 18 M6 6l12 12",
  gear: "M12 15a3 3 0 1 0 0-6 3 3 0 0 0 0 6z M19.4 15a1.7 1.7 0 0 0 .3 1.8l.1.1a2 2 0 1 1-2.8 2.8l-.1-.1a1.7 1.7 0 0 0-1.8-.3 1.7 1.7 0 0 0-1 1.5V21a2 2 0 1 1-4 0v-.1a1.7 1.7 0 0 0-1.1-1.5 1.7 1.7 0 0 0-1.8.3l-.1.1a2 2 0 1 1-2.8-2.8l.1-.1a1.7 1.7 0 0 0 .3-1.8 1.7 1.7 0 0 0-1.5-1H3a2 2 0 1 1 0-4h.1a1.7 1.7 0 0 0 1.5-1.1 1.7 1.7 0 0 0-.3-1.8l-.1-.1a2 2 0 1 1 2.8-2.8l.1.1a1.7 1.7 0 0 0 1.8.3H9a1.7 1.7 0 0 0 1-1.5V3a2 2 0 1 1 4 0v.1a1.7 1.7 0 0 0 1 1.5 1.7 1.7 0 0 0 1.8-.3l.1-.1a2 2 0 1 1 2.8 2.8l-.1.1a1.7 1.7 0 0 0-.3 1.8V9a1.7 1.7 0 0 0 1.5 1H21a2 2 0 1 1 0 4h-.1a1.7 1.7 0 0 0-1.5 1z",
};
const Ic = ({ d }) => <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d={d} /></svg>;
const Btn = ({ icon, label, on, cls = "", ...p }) => <button className={`cbtn ${on ? "on" : ""} ${cls}`} aria-pressed={on} {...p}><span className="ic"><Ic d={P[icon]} /></span>{label}</button>;
const fmt = (s) => `${String(Math.floor(s / 60)).padStart(2, "0")}:${String(s % 60).padStart(2, "0")}`;

export default function Room({ id }) {
  const { meta } = useApp();
  const [iv, setIv] = useState(null);
  const [phase, setPhase] = useState("gate");
  const [turns, setTurns] = useState([]);
  const [caption, setCaption] = useState("");
  const [said, setSaid] = useState("");
  const [answered, setAnswered] = useState(0);
  const [toast, setToast] = useState("");
  const [procLabel, setProcLabel] = useState("Thinking");
  const [textMode, setTextMode] = useState(false);
  const [typing, setTyping] = useState(false); const [typed, setTyped] = useState("");
  const [muted, setMuted] = useState(false); const [heard, setHeard] = useState(false);
  const [ui, setUi] = useState({ captions: true, panel: false, camera: false, settings: false, review: false, patience: 1800 });
  const [review, setReview] = useState(null);
  const [fallbackVoice, setFallbackVoice] = useState(false);
  const [secs, setSecs] = useState(0);
  const [error, setError] = useState("");
  const [coding, setCoding] = useState(null); const codingRef = useRef(null); const touched = useRef(false);
  const [lang, setLang] = useState("python"); const [codes, setCodes] = useState({}); const [result, setResult] = useState(null); const [busyCode, setBusyCode] = useState("");
  const isCoding = iv?.config?.interview_type === "coding";

  const levelRef = useRef(0), userLevel = useRef(0), micBar = useRef(null), video = useRef(null), camStream = useRef(null);
  const speaker = useRef(null), rec = useRef(null), turn = useRef(0), done = useRef(false), finishP = useRef(null);
  const live = useRef({}); live.current = { iv, textMode, muted, ui, meta };
  const lastReply = useRef("");

  // ---------- load
  useEffect(() => {
    const cached = sessionStorage.getItem("is_room_" + id);
    const init = async () => {
      try {
        if (cached) { const c = JSON.parse(cached); setIv(c); setTurns([]); lastReply.current = c.opening.text; if (c.coding) { setCoding(c.coding); codingRef.current = c.coding; setLang(c.config.code_language || "python"); } return; }
        const r = await api.interview(id);
        if (r.status === "completed") return go("report/" + id);
        const last = [...r.turns].reverse().find((t) => t.role === "interviewer");
        setIv({ ...r, opening: { text: last.text, topic: last.topic } });
        setTurns(r.turns.map((t) => ({ role: t.role, text: t.text }))); setAnswered(r.answered); lastReply.current = last.text; if (r.coding) { setCoding(r.coding); codingRef.current = r.coding; setLang(r.config.code_language || "python"); touched.current = true; }
      } catch (e) { setError(e.message); }
    };
    init();
    return () => { turn.current++; speaker.current?.stop(); rec.current?.close(); camStream.current?.getTracks().forEach((t) => t.stop()); };
  }, [id]);

  useEffect(() => { const t = setInterval(() => setSecs((s) => s + 1), 1000); return () => clearInterval(t); }, []);
  useEffect(() => { let raf; const loop = () => { if (micBar.current) micBar.current.style.width = Math.round(Math.min(1, userLevel.current) * 100) + "%"; raf = requestAnimationFrame(loop); }; raf = requestAnimationFrame(loop); return () => cancelAnimationFrame(raf); }, []);
  useEffect(() => { if (!toast) return; const t = setTimeout(() => setToast(""), 4500); return () => clearTimeout(t); }, [toast]);
  useEffect(() => { if (rec.current) { rec.current.patienceMs = ui.patience; } }, [ui.patience]);
  useEffect(() => { if (rec.current) rec.current.muted = muted; }, [muted]);
  useEffect(() => {
    if (ui.camera) navigator.mediaDevices.getUserMedia({ video: { width: 480 } }).then((s) => { camStream.current = s; if (video.current) video.current.srcObject = s; }).catch(() => { setToast("Camera unavailable."); setUi((u) => ({ ...u, camera: false })); });
    else { camStream.current?.getTracks().forEach((t) => t.stop()); camStream.current = null; }
  }, [ui.camera]);

  const voiceOpts = () => { const v = live.current.iv.voice; return { voice: v.voice, tts_language: v.tts_language, language: v.stt_language, speed: v.speed, onFallback: () => setFallbackVoice(true) }; };

  const ckey = coding?.problem ? `${coding.problem.id}:${lang}` : "";
  const code = codes[ckey] ?? (ckey ? sessionStorage.getItem(`is_code_${id}_${ckey}`) : null) ?? coding?.problem?.starters?.[lang] ?? "";
  const setCode = (v) => { setCodes((o) => ({ ...o, [ckey]: v })); try { sessionStorage.setItem(`is_code_${id}_${ckey}`, v); } catch {} };

  // ---------- conversation engine
  async function deliver(text, isReplay = false) {
    const my = ++turn.current;
    lastReply.current = text; setCaption(text); setSaid(""); setPhase("speaking");
    if (!isReplay) setTurns((t) => [...t, { role: "interviewer", text }]);
    const ok = await speaker.current.speak(text, voiceOpts());
    if (my !== turn.current || !ok) return;
    if (done.current) return finishAndGo();
    if (codingRef.current?.phase === "coding") { setPhase("coding"); setTyping(live.current.textMode); return; }  // she waits while you code; press Talk to speak to her
    listen();
  }

  async function listen() {
    const my = ++turn.current;
    setTyping(false); setPhase("listening"); setHeard(false); setSaid("");
    if (live.current.textMode) { setTyping(true); return; }
    while (my === turn.current) {
      const res = await rec.current.listen({ stream: live.current.meta?.stream_stt ? { token: session.token, language: live.current.iv.config.language } : null });
      if (my !== turn.current || !res) return;
      setPhase("processing"); setProcLabel("Listening back to your answer");
      try {
        let text = (res.transcript || "").trim();   // already transcribed live while the candidate spoke (streaming)
        if (!text) text = ((await api.stt(res.blob, live.current.iv.config.language)).transcript || "").trim();   // otherwise one-shot upload
        if (my !== turn.current) return;
        if (!text) { setToast("I couldn't hear that clearly. Please say it again."); setPhase("listening"); setHeard(false); continue; }
        if (live.current.ui.review) { setReview({ text, ms: res.durationMs }); setPhase("review"); return; }
        return submit(text, "voice", res.durationMs);
      } catch (e) {
        if (e.code === "gnani_not_configured") { setTextMode(true); setToast("Voice recognition is temporarily unavailable. Please type your answer instead."); setTyping(true); setPhase("listening"); return; }
        setToast(`${e.message} You can try again or type.`); setPhase("listening"); setHeard(false);
      }
    }
  }

  async function submit(text, source, ms) {
    const my = ++turn.current;
    setReview(null); setTyped(""); setTyping(false); setSaid(text); setPhase("processing"); setProcLabel("Thinking");
    setTurns((t) => [...t, { role: "candidate", text }]);
    try {
      const r = await api.answer(id, { text, source, duration_ms: ms });
      if (my !== turn.current) return;
      setAnswered(r.answered); touched.current = true;
      if (r.coding) { if (r.coding.problem?.id !== codingRef.current?.problem?.id) setResult(null); setCoding(r.coding); codingRef.current = r.coding; }
      if (r.done) { done.current = true; finishP.current = api.finish(id); finishP.current.catch(() => {}); }
      await deliver(r.reply);
    } catch (e) {
      setToast(e.message); setTurns((t) => t.slice(0, -1)); listen();
    }
  }

  async function finishAndGo() {
    turn.current++; setPhase("ended");
    try { await (finishP.current || api.finish(id)); sessionStorage.removeItem("is_room_" + id); go("report/" + id); }
    catch (e) { setError(e.message); }
  }

  // ---------- actions
  const join = async () => {
    speaker.current = new Speaker(levelRef); await speaker.current.unlock();
    let voice = !!meta?.gnani_configured;
    if (voice) {
      try { rec.current = new VoiceRecorder({ levelRef: userLevel, onPartial: (t) => setSaid(t), onStatus: (s) => { if (s === "speech") setHeard(true); if (s === "long-silence") setToast("Take your time. You can also type your answer."); } }); rec.current.patienceMs = ui.patience; await rec.current.open(); }
      catch { voice = false; setToast("Microphone unavailable. You can type your answers."); }
    } else setToast("Voice mode is temporarily unavailable. You can type your answers for now.");
    setTextMode(!voice); live.current.textMode = !voice;
    deliver(iv.opening.text);
  };
  const doneTalking = () => rec.current?.stopNow();
  const interrupt = () => { speaker.current.stop(); turn.current++; if (done.current) finishAndGo(); else listen(); };
  const replay = () => { rec.current?.cancel(); deliver(lastReply.current, true); };
  const skip = () => { rec.current?.cancel(); submit("I'd like to skip this question, please.", "text"); };
  const typeInstead = () => { rec.current?.cancel(); turn.current++; setTyping(true); setPhase("listening"); };
  const backToVoice = () => { setTyping(false); if (!textMode) listen(); };
  const toggleMute = () => setMuted((m) => !m);
  const talk = () => { setTyping(false); listen(); };
  const runCode = async () => {
    setBusyCode("run"); touched.current = true;
    try { setResult(await api.codeRun(id, { language: lang, code })); } catch (e) { setToast(e.message); } finally { setBusyCode(""); }
  };
  const submitCode = async () => {
    if (!window.confirm("Submit your solution? It runs against all tests, including hidden ones, and you can't edit it afterwards.")) return;
    setBusyCode("submit"); touched.current = true; speaker.current?.stop(); rec.current?.cancel(); turn.current++;
    try {
      const r = await api.codeSubmit(id, { language: lang, code });
      setResult(r.result); setCoding(r.coding); codingRef.current = r.coding;
      await deliver(r.reply);
    } catch (e) { setToast(e.message); setPhase("coding"); } finally { setBusyCode(""); }
  };
  const skipProblem = async () => {
    if (!window.confirm("Skip this problem?")) return;
    speaker.current?.stop(); rec.current?.cancel(); turn.current++; setBusyCode("skip");
    try {
      const r = await api.codeSkip(id);
      setResult(null); setCoding(r.coding); codingRef.current = r.coding;
      if (r.done) { done.current = true; finishP.current = api.finish(id); finishP.current.catch(() => {}); }
      await deliver(r.reply);
    } catch (e) { setToast(e.message); } finally { setBusyCode(""); }
  };
  const end = async () => {
    if (!window.confirm(answered || touched.current ? "End the interview now and see your report?" : "End the interview? Nothing has been scored yet, so it won't be saved.")) return;
    turn.current++; speaker.current?.stop(); rec.current?.cancel();
    if (!answered && !touched.current) { try { await api.remove(id); } catch {} sessionStorage.removeItem("is_room_" + id); return go("setup"); }
    setPhase("ended"); finishP.current = api.finish(id); finishAndGo();
  };

  if (error) return <div className="room" style={{ placeItems: "center", display: "grid" }}><div className="box" style={{ textAlign: "center", display: "grid", gap: 14, justifyItems: "center" }}><p className="err">{error}</p><a className="btn gold" href="#/setup">Back to setup</a></div></div>;
  if (!iv) return <div className="room" style={{ display: "grid", placeItems: "center" }}>Connecting…</div>;

  const persona = iv.config.interviewer === "male" ? "male" : "female";
  const name = iv.persona;
  const avState = phase === "speaking" ? "speaking" : phase === "listening" || phase === "coding" ? "listening" : phase === "processing" ? "thinking" : "idle";
  const status = phase === "speaking" ? `${name} is speaking` : phase === "listening" ? (typing || textMode ? "Your turn · type your answer" : muted ? "Mic muted" : heard ? "Listening…" : "Your turn · speak when ready") : phase === "coding" ? "Your turn to code · run the samples, then submit" : phase === "processing" ? procLabel : phase === "review" ? "Check your answer" : phase === "ended" ? "Preparing your report" : "";
  const total = iv.total_questions;

  return (
    <div className="room" role="application" aria-label="Interview room">
      <div className="room-top">
        <a className="logo" href="#/" onClick={(e) => { e.preventDefault(); end(); }}><i />InterviewSaathi</a>
        <span className="chip">{iv.config.role} · {iv.config.interview_type}</span>
        <span className="spacer" />
        <span className="chip">{isCoding ? `Problem ${Math.min((coding?.index ?? 0) + 1, total)} of ${total}` : `Question ${Math.min(answered + 1, total)} of ${total}`}</span>
        <span className="chip" aria-label="Elapsed time">{fmt(secs)}</span>
        {fallbackVoice && <span className="chip warn">Demo voice</span>}
      </div>

      <div className={`stage ${isCoding ? "coding" : ""} ${ui.panel ? "withpanel" : ""}`}>
        <div className={`tile ${isCoding ? "small" : ""}`}>
          <div className="av"><Avatar persona={persona} state={avState} levelRef={levelRef} userLevelRef={userLevel} /></div>
          <div className={`ring ${phase === "speaking" ? "speaking" : phase === "listening" && heard ? "listening" : ""}`} />
          <div className="nameplate">{name} <span className="pill gold">AI interviewer</span></div>
          {status && <div className="status" role="status">{status}{phase === "processing" && <span className="dots"><i /><i /><i /></span>}</div>}
          {ui.captions && ((phase === "processing" || phase === "listening") && said ? <div className="caption"><b style={{ color: "#7fd4b0", fontSize: 12, display: "block" }}>{phase === "listening" ? "YOU (live)" : "YOU SAID"}</b>{said}</div> : caption && phase !== "gate" && <div className="caption" aria-live="polite">{caption}</div>)}
          <div className="selfview" style={{ display: ui.camera || !textMode ? "grid" : "none" }}>
            {ui.camera ? <video ref={video} autoPlay muted playsInline /> : <span>You</span>}
            <div className="micbar"><i ref={micBar} /></div>
          </div>
          {phase === "review" && review && (
            <div className="review"><b>Is this what you said?</b>
              <textarea value={review.text} onChange={(e) => setReview({ ...review, text: e.target.value })} aria-label="Edit your transcript" />
              <div style={{ display: "flex", gap: 8, justifyContent: "flex-end" }}>
                <button className="btn ghost sm" onClick={() => { setReview(null); listen(); }}>Record again</button>
                <button className="btn gold sm" onClick={() => submit(review.text.trim(), "voice", review.ms)} disabled={!review.text.trim()}>Send answer</button></div></div>)}
          {toast && <div className="toast" role="alert">{toast}</div>}
          {phase === "gate" && (
            <div className="gate"><div className="box">
              <div style={{ width: 150, height: 150, borderRadius: "50%", overflow: "hidden", boxShadow: "0 0 0 4px rgba(245,179,1,.6)" }}><Avatar persona={persona} state="listening" /></div>
              <h2>{name} is ready for you</h2>
              <p style={{ color: "#a9c6ce" }}>{meta?.gnani_configured ? "Allow your microphone, then just talk. She'll wait while you think and ask follow-ups." : "Voice mode is temporarily unavailable, so you'll type your answers."} Use headphones to avoid echo.</p>
              <button className="btn gold lg" onClick={join}>Join interview</button>
              <a href="#/setup" style={{ color: "#8fb3bc" }}>Change settings</a>
            </div></div>)}
        </div>
        {isCoding && coding?.problem && (
          <section className="codepanel" aria-label="Coding problem and editor">
            <div className={`phase-note ${coding.phase === "coding" ? "go" : ""}`}>
              {coding.phase === "approach" && `Step 1 · Tell ${name} how you'd approach this (speak or type). You can also start coding any time.`}
              {coding.phase === "coding" && `Step 2 · Write your solution, run the samples, then submit. Press Talk to speak with ${name} while you code.`}
              {coding.phase === "followup" && `Step 3 · Your solution is submitted. Answer ${name}'s question about complexity and edge cases.`}
            </div>
            <ProblemView problem={coding.problem} />
            <div className="bar-row">
              <select value={lang} onChange={(e) => { setLang(e.target.value); setResult(null); }} disabled={coding.phase === "followup"} aria-label="Programming language">
                {Object.entries(meta?.code_languages || { python: "Python 3" }).map(([k, v]) => <option key={k} value={k}>{v}</option>)}</select>
              <button className="btn ghost sm" onClick={runCode} disabled={!!busyCode || coding.phase === "followup" || phase === "gate"}>{busyCode === "run" ? "Running…" : "Run samples"}</button>
              <button className="btn gold sm" onClick={submitCode} disabled={!!busyCode || coding.phase === "followup" || phase === "gate"}>{busyCode === "submit" ? "Judging…" : "Submit"}</button>
              <span className="sub" style={{ marginLeft: "auto" }}>Ctrl/Cmd + Enter runs the samples</span>
            </div>
            <CodeEditor value={code} onChange={setCode} language={lang} readOnly={coding.phase === "followup"} onRun={runCode} />
            <CodeResult result={result} />
          </section>)}
        {ui.panel && (
          <aside className="panel" aria-label="Transcript"><h3>Transcript <button className="btn ghost sm" style={{ color: "#fff", boxShadow: "inset 0 0 0 2px rgba(255,255,255,.25)" }} onClick={() => setUi({ ...ui, panel: false })}>Close</button></h3>
            {turns.map((t, i) => <div key={i} className={`msg ${t.role === "candidate" ? "me" : ""}`}><b>{t.role === "candidate" ? "You" : name}</b>{t.text}</div>)}</aside>)}
      </div>

      {typing && (phase === "listening" || phase === "coding") && (
        <div className="typebox">
          <textarea value={typed} onChange={(e) => setTyped(e.target.value)} placeholder="Type your answer…" aria-label="Type your answer" autoFocus onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey && typed.trim()) { e.preventDefault(); submit(typed.trim(), "text"); } }} />
          <button className="btn gold" disabled={!typed.trim()} onClick={() => submit(typed.trim(), "text")}>Send</button>
          {!textMode && <button className="btn ghost" style={{ color: "#fff", boxShadow: "inset 0 0 0 2px rgba(255,255,255,.3)" }} onClick={backToVoice}>Use voice</button>}
        </div>)}

      {ui.settings && phase !== "gate" && (
        <div className="typebox" style={{ flexWrap: "wrap", justifyContent: "center", gap: 18, fontSize: 14 }}>
          <label>Pause patience: <select value={ui.patience} onChange={(e) => setUi({ ...ui, patience: +e.target.value })} style={{ width: "auto", padding: "6px 10px" }}><option value={1300}>Quick (1.3 s)</option><option value={1800}>Normal (1.8 s)</option><option value={2800}>Patient (2.8 s)</option></select></label>
          <label><input type="checkbox" checked={ui.review} onChange={(e) => setUi({ ...ui, review: e.target.checked })} /> Review transcript before sending</label>
        </div>)}

      <div className="controls">
        {!textMode && <Btn icon={muted ? "micoff" : "mic"} label={muted ? "Unmute" : "Mute"} on={muted} onClick={toggleMute} disabled={phase === "gate"} />}
        {phase === "coding" && !textMode && <Btn icon="mic" label={`Talk to ${name}`} cls="green" onClick={talk} />}
        {phase === "listening" && !typing && !textMode && heard && <Btn icon="check" label="I'm done" cls="green" onClick={doneTalking} />}
        {phase === "speaking" && <Btn icon="skip" label="I'm ready" onClick={interrupt} />}
        <Btn icon="replay" label="Repeat" onClick={replay} disabled={phase === "gate" || phase === "processing" || phase === "ended"} />
        <Btn icon="skip" label={isCoding ? "Skip problem" : "Skip question"} onClick={isCoding ? skipProblem : skip} disabled={isCoding ? !(phase === "listening" || phase === "coding") : phase !== "listening"} />
        {!textMode && <Btn icon="kb" label="Type" on={typing} onClick={typing ? backToVoice : typeInstead} disabled={phase === "gate" || phase === "ended"} />}
        <Btn icon="cam" label="Camera" on={ui.camera} onClick={() => setUi({ ...ui, camera: !ui.camera })} />
        <Btn icon="cc" label="Captions" on={ui.captions} onClick={() => setUi({ ...ui, captions: !ui.captions })} />
        <Btn icon="list" label="Transcript" on={ui.panel} onClick={() => setUi({ ...ui, panel: !ui.panel })} />
        <Btn icon="gear" label="Settings" on={ui.settings} onClick={() => setUi({ ...ui, settings: !ui.settings })} />
        <Btn icon="x" label="End" cls="red" onClick={end} disabled={phase === "gate"} />
      </div>
      {ui.camera && <p className="sr">Your camera preview stays on your device and is never recorded or uploaded.</p>}
    </div>
  );
}
