import { useEffect, useRef, useState } from "react";
import Avatar from "../components/Avatar.jsx";
import { useApp } from "../App.jsx";

const LINES = [
  "Explain the difference between an interface and an abstract class in Java.",
  "Good. Can a class implement multiple interfaces? How is that different from extending classes?",
  "Tell me about a project you're proud of. What was your own contribution?",
];

export default function Landing() {
  const { meta } = useApp();
  const level = useRef(0);
  const [i, setI] = useState(0);
  const [st, setSt] = useState("speaking");

  // Decorative demo only: a synthetic loudness signal makes the preview talk. In the real interview the signal comes from the audio that is actually playing.
  useEffect(() => {
    let raf; const t0 = performance.now();
    const loop = () => { const t = (performance.now() - t0) / 1000; const talking = (t % 7) < 5.2; level.current = talking ? 0.22 + 0.2 * Math.abs(Math.sin(t * 8.3)) * (0.5 + 0.5 * Math.sin(t * 2.7)) : 0; setSt(talking ? "speaking" : "listening"); raf = requestAnimationFrame(loop); };
    raf = requestAnimationFrame(loop);
    const iv = setInterval(() => setI((x) => (x + 1) % LINES.length), 7000);
    return () => { cancelAnimationFrame(raf); clearInterval(iv); };
  }, []);

  return (
    <>
      <section className="hero">
        <div className="wrap">
          <div>
            <span className="hero-kicker"><i /> YOUR NEXT INTERVIEW STARTS HERE</span>
            <h1 style={{ marginTop: 18 }}>Show up ready.<br /><em>Speak with confidence.</em></h1>
            <p className="lead">Get realistic, voice powered interview practice whenever you need it. Meet your AI interviewer, work through thoughtful follow ups, and leave with feedback you can use. In English, Hindi or Hinglish.</p>
            <div className="cta">
              <a className="btn gold lg" href="#/setup">Start practising <span aria-hidden="true">→</span></a>
              <a className="btn ghost lg" href="#/dashboard">View my progress</a>
            </div>
            <div className="hero-trust"><span>✦ Free to get started</span><span>✦ No college required</span><span>✦ Speak or type</span></div>
          </div>
          <div className="callframe" aria-hidden="true">
            <div className="call-top"><span className="live"><i /> LIVE PRACTICE</span><span className="call-time">00:42</span></div>
            <Avatar persona="female" state={st} levelRef={level} />
            <div className="bubble"><b>Ananya · AI interviewer</b>{LINES[i]}<div className="waveform"><i /><i /><i /><i /><i /><i /><i /><i /><i /><i /><i /><i /><i /><i /><i /></div></div>
          </div>
        </div>
      </section>

      <section className="section"><div className="wrap">
        <span className="eyebrow">PRACTICE THAT FEELS REAL</span><h2>A conversation, not a question list.</h2>
        <p className="sub" style={{ maxWidth: 640, fontSize: 18 }}>Get comfortable thinking out loud, answering naturally, and handling the follow up.</p>
        <div className="pipe">
          <div><span className="n">01 · YOU SPEAK</span><b>Your answer</b><p className="sub">Your microphone captures it. The app detects when you finish, so no buttons to press.</p></div>
          <div><span className="n">02 · HEAR</span><b>Gnani Prisma</b><p className="sub">Speech-to-text built for Indian languages and accents turns your voice into a transcript.</p><span className="pill green tag">speech-to-text</span></div>
          <div><span className="n">03 · THINK</span><b>The interviewer</b><p className="sub">Reads your answer, reacts like a person, asks a relevant follow-up, and scores quietly in the background.</p></div>
          <div><span className="n">04 · REPLY</span><b>Gnani Timbre</b><p className="sub">The next question is spoken back in a natural Indian voice while the face on screen lip-syncs to it.</p><span className="pill green tag">text-to-speech</span></div>
        </div>
      </div></section>

      <section className="section" style={{ paddingTop: 0 }}><div className="wrap">
        <span className="eyebrow">MADE FOR YOUR NEXT STEP</span><h2>Feedback you can act on.</h2>
        <div className="feat">
          <div><h3>Scored on substance</h3><p className="sub">Technical accuracy, relevance, completeness and clarity. Length and fancy English never raise your score, and accents or Hinglish are never penalised.</p></div>
          <div><h3>Missing concepts, named</h3><p className="sub">See what you got right, what you missed, and one possible strong answer for every question.</p></div>
          <div><h3>Your resume, your interview</h3><p className="sub">Upload a resume or paste a job description and get questions about your own projects and the role.</p></div>
          <div><h3>A real coding round</h3><p className="sub">Explain your approach out loud, code in the browser in Python, JavaScript or Java, run it against hidden tests in a sandbox, then defend your complexity.</p></div>
          <div><h3>Progress from real data</h3><p className="sub">Your dashboard is built only from interviews you actually completed. Nothing is made up.</p></div>
          <div><h3>Practice on your terms</h3><p className="sub">Build a routine that fits your goals, whether you're preparing for your first interview, changing careers or sharpening your skills. No school or organization required.</p></div>
        </div>
        {meta && !meta.gnani_configured && <p className="notice" style={{ marginTop: 28 }}>Developer note: GNANI_API_KEY is not set on the server yet, so the app runs in text-and-browser-voice demo mode. Add the key to .env and restart to switch on Gnani voice.</p>}
      </div></section>
    </>
  );
}
