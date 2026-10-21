/* Plays Gnani Timbre speech and exposes the live loudness so the avatar's mouth can follow the real audio.
   Long replies are split into sentences that are synthesised in parallel and played in order, so the interviewer starts talking
   after the FIRST sentence is ready instead of after the whole reply. If Timbre is unavailable the browser voice is used as a demo fallback. */
import { api } from "./api.js";

const LOCALE = { "en-IN": "en-IN", "hi-IN": "hi-IN", hinglish: "en-IN", "ta-IN": "ta-IN", "te-IN": "te-IN", "kn-IN": "kn-IN", "ml-IN": "ml-IN", "mr-IN": "mr-IN", "bn-IN": "bn-IN", "gu-IN": "gu-IN", "pa-IN": "pa-IN" };

export function splitSentences(text) {
  const parts = text.replace(/\s+/g, " ").match(/[^.!?।]+[.!?।]*\s*/g) || [text];
  const out = [];
  for (const p of parts) {
    if (out.length && out[out.length - 1].length < 28) out[out.length - 1] += p; else out.push(p);
  }
  return out.map((s) => s.trim()).filter(Boolean);
}

export class Speaker {
  constructor(levelRef) {
    this.levelRef = levelRef || { current: 0 };
    this.ctx = new (window.AudioContext || window.webkitAudioContext)();
    this.analyser = this.ctx.createAnalyser(); this.analyser.fftSize = 1024;
    this.analyser.connect(this.ctx.destination);
    this.gen = 0; this.source = null; this.fallback = false; this.meter = null;
    this.rate = 1;
  }
  unlock() { return this.ctx.resume(); }

  _meterStart() {
    const buf = new Float32Array(this.analyser.fftSize);
    const loop = () => {
      this.analyser.getFloatTimeDomainData(buf);
      let s = 0; for (let i = 0; i < buf.length; i++) s += buf[i] * buf[i];
      const rms = Math.sqrt(s / buf.length);
      this.levelRef.current = Math.min(1, rms * 5.5);
      this.meter = requestAnimationFrame(loop);
    };
    if (!this.meter) loop();
  }
  _meterStop() { cancelAnimationFrame(this.meter); this.meter = null; this.levelRef.current = 0; }

  stop() {
    this.gen++;
    try { this.source?.stop(); } catch {}
    window.speechSynthesis?.cancel();
    this._meterStop();
  }

  /** Speak `text`. Resolves true when finished, false if interrupted. */
  async speak(text, { voice, language, tts_language, speed = 1, onFallback } = {}) {
    const my = ++this.gen;
    this.stop(); this.gen = my;
    const chunks = splitSentences(text);
    const jobs = chunks.map((c) => api.tts(c, voice, tts_language, speed).then((ab) => this.ctx.decodeAudioData(ab)));
    jobs.forEach((j) => j.catch(() => {}));
    this._meterStart();
    try {
      for (let i = 0; i < jobs.length; i++) {
        const buffer = await jobs[i];
        if (my !== this.gen) return false;
        await new Promise((resolve) => {
          const src = this.ctx.createBufferSource();
          src.buffer = buffer; src.playbackRate.value = 1; src.connect(this.analyser);
          src.onended = resolve; this.source = src; src.start();
        });
        if (my !== this.gen) return false;
      }
      this._meterStop();
      return true;
    } catch (e) {
      if (my !== this.gen) return false;
      this._meterStop();
      this.fallback = true; onFallback?.(e);
      return this._browserSpeak(text, LOCALE[language] || "en-IN", my);
    }
  }

  _browserSpeak(text, lang, my) {
    return new Promise((resolve) => {
      if (!window.speechSynthesis) return resolve(true);
      const u = new SpeechSynthesisUtterance(text);
      u.lang = lang; u.rate = 1;
      const pick = speechSynthesis.getVoices().find((v) => v.lang.replace("_", "-").startsWith(lang));
      if (pick) u.voice = pick;
      let t0 = performance.now(), anim;
      const wiggle = () => { const t = (performance.now() - t0) / 1000; this.levelRef.current = 0.25 + 0.2 * Math.abs(Math.sin(t * 9)) * (0.6 + 0.4 * Math.sin(t * 3.1)); anim = requestAnimationFrame(wiggle); };
      u.onstart = wiggle;
      const end = () => { cancelAnimationFrame(anim); this.levelRef.current = 0; resolve(my === this.gen); };
      u.onend = end; u.onerror = end;
      speechSynthesis.speak(u);
    });
  }
}
