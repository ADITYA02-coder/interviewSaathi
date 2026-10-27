import { useEffect, useRef, useState } from "react";
import Avatar from "../components/Avatar.jsx";

const LINES = [
  "Explain the difference between an interface and an abstract class in Java.",
  "Good. Can a class implement multiple interfaces? How is that different from extending classes?",
  "Tell me about a project you're proud of. What was your own contribution?",
];

export default function Landing() {
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
            <span className="hero-kicker"><i /> BUILT FOR THE MOMENT THAT MATTERS</span>
            <h1 style={{ marginTop: 18 }}>Turn preparation<br /><em>into presence.</em></h1>
            <p className="lead">A calmer, smarter way to prepare for the interview you actually want. Practise by actually talking with an AI interviewer that listens, follows up, and gives you a clear path to improve.</p>
            <div className="cta">
              <a className="btn gold lg" href="#/setup">Start a practice session <span aria-hidden="true">→</span></a>
              <a className="btn ghost lg" href="#/dashboard">See your progress</a>
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

      <section className="proof-strip"><div className="wrap">
        <div className="proof-intro"><span className="eyebrow">YOUR ADVANTAGE</span><h2>More than practice.</h2><p className="sub">A focused space to sound like yourself when the stakes are high.</p></div>
        <div className="proof-grid">
          <div className="proof-item"><span className="proof-icon">◒</span><b>Listen naturally</b><p className="sub">Speak in the language and rhythm that feels most comfortable to you.</p></div>
          <div className="proof-item"><span className="proof-icon">↗</span><b>Go beyond scripts</b><p className="sub">Get thoughtful follow-ups that help you build real communication confidence.</p></div>
          <div className="proof-item"><span className="proof-icon">✦</span><b>Improve with clarity</b><p className="sub">Walk away with practical feedback, not vague advice or empty scores.</p></div>
        </div>
      </div></section>

      <section className="section"><div className="wrap">
        <span className="eyebrow">A BETTER WAY TO REHEARSE</span><h2>Practice the conversation, not just the answer.</h2>
        <p className="sub" style={{ maxWidth: 640, fontSize: 18 }}>Build the confidence to think clearly, communicate naturally, and handle the follow-up that changes the room.</p>
        <div className="pipe">
          <div><span className="n">01 · YOU SPEAK</span><b>Your answer</b><p className="sub">Your microphone captures it. The app detects when you finish, so no buttons to press.</p></div>
          <div><span className="n">02 · HEAR</span><b>Understands you</b><p className="sub">Speech recognition built for Indian languages and accents turns your voice into a clear transcript.</p><span className="pill green tag">speech recognition</span></div>
          <div><span className="n">03 · THINK</span><b>The interviewer</b><p className="sub">Reads your answer, reacts like a person, asks a relevant follow-up, and scores quietly in the background.</p></div>
          <div><span className="n">04 · REPLY</span><b>Feels conversational</b><p className="sub">The next question is spoken back in a natural voice while the face on screen lip-syncs to it.</p><span className="pill green tag">natural voice replies</span></div>
        </div>
      </div></section>

      <section className="section" style={{ paddingTop: 0 }}><div className="wrap">
        <span className="eyebrow">DESIGNED AROUND YOUR GROWTH</span><h2>Every session leaves you sharper.</h2>
        <div className="feat">
          <div><h3>Scored on substance</h3><p className="sub">Technical accuracy, relevance, completeness and clarity. Length and fancy English never raise your score, and accents or Hinglish are never penalised.</p></div>
          <div><h3>Missing concepts, named</h3><p className="sub">See what you got right, what you missed, and one possible strong answer for every question.</p></div>
          <div><h3>Your resume, your interview</h3><p className="sub">Upload a resume or paste a job description and get questions about your own projects and the role.</p></div>
          <div><h3>A real coding round</h3><p className="sub">Explain your approach out loud, code in the browser in Python, JavaScript or Java, run it against hidden tests in a sandbox, then defend your complexity.</p></div>
          <div><h3>Progress from real data</h3><p className="sub">Your dashboard is built only from interviews you actually completed. Nothing is made up.</p></div>
          <div><h3>Practice on your terms</h3><p className="sub">Build a routine that fits your goals, whether you're preparing for your first interview, changing careers or sharpening your skills. No school or organization required.</p></div>
        </div>
      </div></section>
    </>
  );
}
