import { useEffect, useRef } from "react";

/* A lip-synced, blinking, nodding illustrated interviewer.
   The mouth is driven in real time by the amplitude of the audio that is actually playing (see lib/speaker.js),
   so it moves with Gnani Timbre's voice. All per-frame motion is written straight to SVG attributes (no React re-renders). */

const PERSONAS = {
  female: { skin: "#C98F6B", shade: "#B27653", hair: "#1B1210", hair2: "#2C1C17", jacket: "#1E3A5F", jacket2: "#27496F", inner: "#F3ECE1", lip: "#A24E50", brow: "#1B1210", bg1: "#2B5A6B", bg2: "#0E2F3C" },
  male: { skin: "#BC825D", shade: "#A56C49", hair: "#15100E", hair2: "#241A16", jacket: "#2E3340", jacket2: "#3A4050", inner: "#E9EEF3", lip: "#8F4A45", brow: "#15100E", bg1: "#3A5A5C", bg2: "#12302F" },
};

export function mouthShape(open, wide, smile) {
  const cx = 200, cy = 304;
  const w = 24 + wide * 7;
  const lift = 2 + smile * 5;
  const cyC = cy - lift;
  const lx = cx - w, rx = cx + w;
  const q = (m) => 2 * m - cyC; // control y so the curve's midpoint lands on y = m
  const upTop = cy - 5 - open * 1.2;
  const loBot = cy + 7 + open * 21;
  const inTop = cy - 1 - open * 1.5;
  const inBot = cy + open * 17;
  const outer = `M ${lx} ${cyC} Q ${cx - w * 0.55} ${q(upTop) - 1.5} ${cx} ${upTop} Q ${cx + w * 0.55} ${q(upTop) - 1.5} ${rx} ${cyC} Q ${cx} ${q(loBot)} ${lx} ${cyC} Z`;
  const inner = `M ${lx + 3} ${cyC} Q ${cx} ${q(inTop)} ${rx - 3} ${cyC} Q ${cx} ${q(Math.max(inBot, inTop + 0.2))} ${lx + 3} ${cyC} Z`;
  const line = `M ${lx} ${cyC} Q ${cx} ${q(cy + 0.5)} ${rx} ${cyC}`;
  return { outer, inner, line, open, cx, inTop, inBot, lx, rx };
}

const clamp = (v, a, b) => Math.max(a, Math.min(b, v));

export default function Avatar({ persona = "female", state = "idle", levelRef, userLevelRef, className = "" }) {
  const P = PERSONAS[persona] || PERSONAS.female;
  const els = useRef({});
  const stateRef = useRef(state);
  stateRef.current = state;
  const set = (k) => (el) => { els.current[k] = el; };
  const m0 = mouthShape(0, 0, 0.5);

  useEffect(() => {
    let raf, last = performance.now();
    const s = { open: 0, wide: 0, blink: 0, nextBlink: 1.5, blinkT: -1, gx: 0, gy: 0, tgx: 0, tgy: 0, nextGaze: 1, nod: -1, nextNod: 3, phase: Math.random() * 10, smile: 0.5, brow: 0, headRot: 0, headY: 0, tilt: 0 };
    const t0 = last;
    const tick = (now) => {
      const dt = Math.min(0.05, (now - last) / 1000); last = now;
      const t = (now - t0) / 1000;
      const st = stateRef.current;
      const lvl = levelRef?.current || 0;
      const ulvl = userLevelRef?.current || 0;

      // ---- blinking
      s.nextBlink -= dt;
      if (s.nextBlink <= 0 && s.blinkT < 0) { s.blinkT = 0; s.nextBlink = 2 + Math.random() * 4; }
      if (s.blinkT >= 0) { s.blinkT += dt; const p = s.blinkT / 0.16; s.blink = p < 1 ? Math.sin(p * Math.PI) : 0; if (p >= 1) s.blinkT = -1; }

      // ---- gaze (eye contact with micro-saccades; looks up when thinking)
      s.nextGaze -= dt;
      if (s.nextGaze <= 0) { s.nextGaze = 0.8 + Math.random() * 2.2; s.tgx = (Math.random() - 0.5) * 3; s.tgy = (Math.random() - 0.5) * 2; }
      let gx = s.tgx, gy = s.tgy;
      if (st === "thinking") { gx = 4.5; gy = -4; }
      s.gx += (gx - s.gx) * Math.min(1, dt * 9); s.gy += (gy - s.gy) * Math.min(1, dt * 9);

      // ---- mouth
      let tOpen = 0, tWide = 0, tSmile = 0.55;
      if (st === "speaking") {
        tOpen = clamp(lvl * 2.6, 0, 1);
        tWide = Math.sin(t * 9 + s.phase) * 0.7 + Math.sin(t * 5.3) * 0.3 - (tOpen > 0.55 ? 0.2 : 0);
        tSmile = 0.35 + (1 - tOpen) * 0.2;
      } else if (st === "listening") { tSmile = 0.75; }
      else if (st === "thinking") { tSmile = 0.1; tWide = -0.5; }
      s.open += (tOpen - s.open) * Math.min(1, dt * (tOpen > s.open ? 28 : 14));
      s.wide += (tWide - s.wide) * Math.min(1, dt * 12);
      s.smile += (tSmile - s.smile) * Math.min(1, dt * 4);

      // ---- head, nods, brows
      s.nextNod -= dt;
      if (s.nextNod <= 0 && s.nod < 0 && (st === "listening" || (st === "speaking" && Math.random() < 0.4))) { s.nod = 0; s.nextNod = 2.5 + Math.random() * 3.5; }
      else if (s.nextNod <= 0) s.nextNod = 1 + Math.random() * 2;
      let nodY = 0, nodR = 0;
      if (s.nod >= 0) { s.nod += dt; const p = s.nod / 0.7; nodY = p < 1 ? Math.sin(p * Math.PI) * 4.5 : 0; nodR = p < 1 ? Math.sin(p * Math.PI) * 1.2 : 0; if (p >= 1) s.nod = -1; }
      const tTilt = st === "thinking" ? 3.2 : st === "listening" ? 1.6 + (ulvl > 0.04 ? 1 : 0) : 0;
      s.tilt += (tTilt - s.tilt) * Math.min(1, dt * 3);
      const sway = Math.sin(t * 0.7 + s.phase) * 0.9 + Math.sin(t * 1.9) * 0.3;
      const speakBob = st === "speaking" ? s.open * 1.4 : 0;
      const rot = sway + s.tilt + nodR + (st === "speaking" ? Math.sin(t * 3.1) * 0.8 * s.open : 0);
      const ty = Math.sin(t * 1.15) * 1.2 + nodY + speakBob;
      const tBrow = st === "thinking" ? -6 : st === "listening" ? -2.5 : st === "speaking" ? -s.open * 3 : 0;
      s.brow += (tBrow - s.brow) * Math.min(1, dt * 6);

      // ---- write to the DOM
      const e = els.current;
      e.head?.setAttribute("transform", `translate(0 ${ty.toFixed(2)}) rotate(${rot.toFixed(2)} 200 345)`);
      e.body?.setAttribute("transform", `translate(0 ${(Math.sin(t * 1.15) * 1.6).toFixed(2)})`);
      const lid = (1 - s.blink) * 0 + s.blink * 20;
      e.lidL?.setAttribute("height", lid.toFixed(2)); e.lidR?.setAttribute("height", lid.toFixed(2));
      e.irisL?.setAttribute("transform", `translate(${s.gx.toFixed(2)} ${s.gy.toFixed(2)})`);
      e.irisR?.setAttribute("transform", `translate(${s.gx.toFixed(2)} ${s.gy.toFixed(2)})`);
      e.browL?.setAttribute("transform", `translate(0 ${(s.brow + (st === "thinking" ? 0 : 0)).toFixed(2)})`);
      e.browR?.setAttribute("transform", `translate(0 ${(s.brow * (st === "thinking" ? 1.6 : 1)).toFixed(2)})`);
      const m = mouthShape(s.open, s.wide, s.smile);
      e.lips?.setAttribute("d", m.outer);
      e.cav?.setAttribute("d", m.inner); e.cavClip?.setAttribute("d", m.inner);
      e.line?.setAttribute("d", m.line);
      const vis = s.open > 0.06 ? 1 : 0;
      e.cav?.setAttribute("opacity", vis); e.teeth?.setAttribute("opacity", vis); e.tongue?.setAttribute("opacity", s.open > 0.3 ? 1 : 0);
      e.line?.setAttribute("opacity", s.open > 0.06 ? 0 : 1);
      e.teeth?.setAttribute("height", Math.min(9, 2 + s.open * 9).toFixed(2));
      e.tongue?.setAttribute("cy", (m.inBot - 2).toFixed(1));
      raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [levelRef, userLevelRef]);

  const female = persona !== "male";
  const uid = useRef("av" + Math.random().toString(36).slice(2, 7)).current;
  return (
    <svg className={className} viewBox="0 0 400 500" role="img" aria-label={`${female ? "Ananya" : "Arjun"}, your AI interviewer`} preserveAspectRatio="xMidYMax slice">
      <defs>
        <radialGradient id={`${uid}bg`} cx="50%" cy="38%" r="75%"><stop offset="0" stopColor={P.bg1} /><stop offset="1" stopColor={P.bg2} /></radialGradient>
        <linearGradient id={`${uid}skin`} x1="0" y1="0" x2="0" y2="1"><stop offset="0" stopColor={P.skin} /><stop offset="1" stopColor={P.shade} /></linearGradient>
        <radialGradient id={`${uid}face`} cx="50%" cy="42%" r="60%"><stop offset="0.6" stopColor="#fff" stopOpacity="0" /><stop offset="1" stopColor="#3b1d10" stopOpacity="0.22" /></radialGradient>
        <clipPath id={`${uid}eL`}><ellipse cx="164" cy="226" rx="17" ry="9.6" /></clipPath>
        <clipPath id={`${uid}eR`}><ellipse cx="236" cy="226" rx="17" ry="9.6" /></clipPath>
        <clipPath id={`${uid}mouth`}><path ref={set("cavClip")} d={m0.inner} /></clipPath>
        <filter id={`${uid}blur`}><feGaussianBlur stdDeviation="9" /></filter>
      </defs>

      {/* office backdrop */}
      <rect width="400" height="500" fill={`url(#${uid}bg)`} />
      <g filter={`url(#${uid}blur)`} opacity="0.85">
        <rect x="262" y="40" width="110" height="150" rx="8" fill="#BFE3EA" opacity="0.55" />
        <rect x="20" y="70" width="70" height="170" rx="6" fill="#F5B301" opacity="0.18" />
        <rect x="34" y="96" width="42" height="14" fill="#fff" opacity="0.2" /><rect x="34" y="130" width="42" height="14" fill="#fff" opacity="0.2" />
        <circle cx="330" cy="260" r="26" fill="#6FC8A2" opacity="0.35" />
      </g>

      <g ref={set("body")}>
        {/* shoulders & jacket */}
        <path d="M-10 500 C 0 420 70 392 140 376 L 260 376 C 330 392 400 420 410 500 Z" fill={P.jacket} />
        <path d="M140 376 L 200 462 L 150 500 L 60 500 C 70 440 100 396 140 376 Z" fill={P.jacket2} opacity="0.9" />
        <path d="M260 376 L 200 462 L 250 500 L 340 500 C 330 440 300 396 260 376 Z" fill={P.jacket2} opacity="0.9" />
        <path d="M166 372 L 200 466 L 234 372 Z" fill={P.inner} />
        {/* neck */}
        <path d="M170 318 L 230 318 L 236 384 Q 200 420 164 384 Z" fill={`url(#${uid}skin)`} />
        <path d="M168 340 Q 200 372 232 340 L 234 352 Q 200 386 166 352 Z" fill="#3b1d10" opacity="0.1" />
        <path d="M166 376 Q 200 408 234 376 L 234 384 Q 200 420 166 384 Z" fill={P.inner} />
      </g>

      <g ref={set("head")}>
        {female && <path d="M108 232 C 92 120 150 78 200 78 C 252 78 308 120 292 232 C 300 300 306 352 296 410 C 270 420 246 392 238 350 L 162 350 C 154 392 130 420 104 410 C 94 352 100 300 108 232 Z" fill={P.hair} />}
        {/* ears */}
        <ellipse cx="121" cy="236" rx="9" ry="16" fill={P.shade} /><ellipse cx="279" cy="236" rx="9" ry="16" fill={P.shade} />
        {female && <><circle cx="121" cy="256" r="3.4" fill="#F5B301" /><circle cx="279" cy="256" r="3.4" fill="#F5B301" /></>}
        {/* face */}
        <path d="M122 214 C 122 140 154 108 200 108 C 246 108 278 140 278 214 C 278 282 246 340 200 342 C 154 340 122 282 122 214 Z" fill={`url(#${uid}skin)`} />
        <path d="M122 214 C 122 140 154 108 200 108 C 246 108 278 140 278 214 C 278 282 246 340 200 342 C 154 340 122 282 122 214 Z" fill={`url(#${uid}face)`} />
        {/* cheeks */}
        <ellipse cx="148" cy="272" rx="20" ry="12" fill="#E07A5F" opacity="0.16" /><ellipse cx="252" cy="272" rx="20" ry="12" fill="#E07A5F" opacity="0.16" />
        {/* nose */}
        <path d="M196 232 Q 192 262 186 270 Q 200 280 214 270 Q 208 262 204 232" fill={P.shade} opacity="0.32" />
        <path d="M187 272 Q 200 282 213 272" fill="none" stroke="#5a2f1e" strokeWidth="1.6" strokeLinecap="round" opacity="0.55" />
        <ellipse cx="200" cy="262" rx="5" ry="6" fill="#fff" opacity="0.1" />

        {/* eyes */}
        {[["L", 164, "eL"], ["R", 236, "eR"]].map(([k, x, c]) => (
          <g key={k}>
            <ellipse cx={x} cy="226" rx="17" ry="9.6" fill="#F7F2EA" />
            <g clipPath={`url(#${uid}${c})`}>
              <g ref={set("iris" + k)}>
                <circle cx={x} cy="226" r="8" fill="#4A2B1A" /><circle cx={x} cy="226" r="3.9" fill="#120A06" /><circle cx={x + 3} cy="223" r="1.7" fill="#fff" opacity="0.9" />
              </g>
              <rect ref={set("lid" + k)} x={x - 18} y="214.5" width="36" height="0" fill={P.skin} />
            </g>
            <path d={`M${x - 18} 227 Q ${x} 212 ${x + 18} 227`} fill="none" stroke="#150b07" strokeWidth="3" strokeLinecap="round" />
            <path d={`M${x - 15} 231 Q ${x} 237 ${x + 15} 231`} fill="none" stroke={P.shade} strokeWidth="1.3" opacity="0.6" />
          </g>
        ))}
        {/* brows */}
        <g ref={set("browL")}><path d="M141 204 Q 163 190 188 202" fill="none" stroke={P.brow} strokeWidth={female ? 4.6 : 6.4} strokeLinecap="round" /></g>
        <g ref={set("browR")}><path d="M212 202 Q 237 190 259 204" fill="none" stroke={P.brow} strokeWidth={female ? 4.6 : 6.4} strokeLinecap="round" /></g>

        {/* mouth */}
        <path ref={set("lips")} d={m0.outer} fill={P.lip} />
        <path ref={set("cav")} d={m0.inner} fill="#3A1218" opacity="0" />
        <g clipPath={`url(#${uid}mouth)`}>
          <rect ref={set("teeth")} x="170" y="302" width="60" height="2" rx="2" fill="#F6F1E9" opacity="0" />
          <ellipse ref={set("tongue")} cx="200" cy="312" rx="13" ry="6" fill="#B9545E" opacity="0" />
        </g>
        <path ref={set("line")} d={m0.line} fill="none" stroke="#5B2227" strokeWidth="1.8" strokeLinecap="round" />
        <path d="M184 322 Q 200 328 216 322" fill="none" stroke={P.shade} strokeWidth="3" opacity="0.35" strokeLinecap="round" />
        {!female && <path d="M158 318 Q 200 346 242 318 Q 236 338 200 342 Q 164 338 158 318 Z" fill="#1d130f" opacity="0.16" />}

        {/* hair front */}
        {female ? (
          <path d="M112 232 C 100 118 156 86 204 88 C 262 90 300 130 288 232 C 284 178 262 146 226 134 C 190 150 150 166 122 214 Z" fill={P.hair} />
        ) : (
          <>
            <path d="M118 206 C 108 112 160 84 204 86 C 258 88 296 122 282 206 C 280 168 262 138 214 130 C 172 134 140 156 126 192 Z" fill={P.hair} />
            <path d="M150 112 C 180 98 226 98 256 116" fill="none" stroke={P.hair2} strokeWidth="5" opacity="0.6" strokeLinecap="round" />
          </>
        )}
        {female && <path d="M126 150 C 150 112 200 102 242 118" fill="none" stroke={P.hair2} strokeWidth="5" opacity="0.5" strokeLinecap="round" />}
      </g>
    </svg>
  );
}
