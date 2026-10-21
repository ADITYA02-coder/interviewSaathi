/* Hands-free voice capture with voice-activity detection.
   Captures raw PCM via an AudioWorklet, finds the end of the answer by silence, and encodes 16 kHz mono WAV
   (a format Gnani Prisma accepts). Speech is clipped to 55 s because Prisma's REST endpoint takes clips of up to 60 s. */

const WORKLET = `
class Tap extends AudioWorkletProcessor {
  constructor(){ super(); this.buf = new Float32Array(2048); this.n = 0; }
  process(inputs){
    const ch = inputs[0] && inputs[0][0];
    if (ch) for (let i = 0; i < ch.length; i++) { this.buf[this.n++] = ch[i]; if (this.n === 2048) { this.port.postMessage(this.buf.slice(0)); this.n = 0; } }
    return true;
  }
}
registerProcessor('tap', Tap);`;

export function encodeWav(chunks, srcRate, dstRate = 16000) {
  let len = 0; for (const c of chunks) len += c.length;
  const src = new Float32Array(len); let o = 0; for (const c of chunks) { src.set(c, o); o += c.length; }
  const ratio = srcRate / dstRate, outLen = Math.floor(src.length / ratio), pcm = new Int16Array(outLen);
  for (let i = 0; i < outLen; i++) {
    const a = i * ratio, i0 = Math.floor(a), i1 = Math.min(src.length - 1, i0 + 1), f = a - i0;
    const v = Math.max(-1, Math.min(1, src[i0] * (1 - f) + src[i1] * f));
    pcm[i] = v < 0 ? v * 0x8000 : v * 0x7fff;
  }
  const buf = new ArrayBuffer(44 + pcm.length * 2), dv = new DataView(buf);
  const w = (off, s) => { for (let i = 0; i < s.length; i++) dv.setUint8(off + i, s.charCodeAt(i)); };
  w(0, "RIFF"); dv.setUint32(4, 36 + pcm.length * 2, true); w(8, "WAVE"); w(12, "fmt "); dv.setUint32(16, 16, true); dv.setUint16(20, 1, true);
  dv.setUint16(22, 1, true); dv.setUint32(24, dstRate, true); dv.setUint32(28, dstRate * 2, true); dv.setUint16(32, 2, true); dv.setUint16(34, 16, true);
  w(36, "data"); dv.setUint32(40, pcm.length * 2, true); new Int16Array(buf, 44).set(pcm);
  return new Blob([buf], { type: "audio/wav" });
}

import { wsBase } from "./api.js";

const STREAM_RATES = [8000, 16000, 44100, 48000];

function toPcm16(f32) {
  const out = new Int16Array(f32.length);
  for (let i = 0; i < f32.length; i++) { const v = Math.max(-1, Math.min(1, f32[i])); out[i] = v < 0 ? v * 0x8000 : v * 0x7fff; }
  return out.buffer;
}

export class VoiceRecorder {
  constructor({ levelRef, onStatus, onPartial } = {}) {
    this.levelRef = levelRef || { current: 0 };
    this.onStatus = onStatus || (() => {});
    this.onPartial = onPartial || (() => {});
    this.listening = false; this.muted = false; this.patienceMs = 1800; this.maxMs = 55000; this.minSpeechMs = 500;
    this.floor = 0.01; this.job = null;
  }

  async open() {
    this.stream = await navigator.mediaDevices.getUserMedia({ audio: { echoCancellation: true, noiseSuppression: true, autoGainControl: true, channelCount: 1 } });
    this.ctx = new (window.AudioContext || window.webkitAudioContext)();
    await this.ctx.resume();
    const url = URL.createObjectURL(new Blob([WORKLET], { type: "application/javascript" }));
    await this.ctx.audioWorklet.addModule(url);
    URL.revokeObjectURL(url);
    this.src = this.ctx.createMediaStreamSource(this.stream);
    this.node = new AudioWorkletNode(this.ctx, "tap");
    const mute = this.ctx.createGain(); mute.gain.value = 0;
    this.src.connect(this.node).connect(mute).connect(this.ctx.destination);
    this.node.port.onmessage = (e) => this._chunk(e.data);
  }

  _chunk(data) {
    let sum = 0; for (let i = 0; i < data.length; i++) sum += data[i] * data[i];
    const rms = Math.sqrt(sum / data.length);
    if (!this.listening || this.muted) { this.levelRef.current *= 0.8; return; }
    this.levelRef.current = Math.min(1, rms * 8);
    const j = this.job; if (!j) return;
    const now = performance.now(), thr = Math.max(0.014, this.floor * 3);
    const loud = rms > thr;
    j.chunks.push(data);
    if (!j.speaking) {
      this.floor = this.floor * 0.97 + rms * 0.03;
      if (j.chunks.length > 10) j.chunks.shift(); // keep ~0.4 s of pre-roll so the first word is never clipped
      j.hits = loud ? j.hits + 1 : 0;
      if (j.hits >= 3) { j.speaking = true; j.startedAt = now; j.lastLoud = now; this.onStatus("speech"); for (const c of j.chunks) this._send(j, c); }
      else if (now - j.t0 > j.waitMs && !j.warned) { j.warned = true; this.onStatus("long-silence"); }
    } else {
      this._send(j, data);
      if (loud) j.lastLoud = now;
      const spoke = j.lastLoud - j.startedAt;
      if (now - j.lastLoud > this.patienceMs) {
        if (spoke >= this.minSpeechMs) this._finish("silence");
        else { j.speaking = false; j.hits = 0; j.chunks = []; this.onStatus("listening"); } // a cough or click, not an answer: discard and keep listening
      } else if (now - j.startedAt > this.maxMs) this._finish("max");
    }
  }

  /** Live transcription: audio is streamed to the backend (which proxies Gnani Prisma's realtime socket) while the candidate speaks,
   *  so the transcript is usually ready the moment they stop. Any failure just means we fall back to the one-shot upload. */
  _openStream(j, { token, language }) {
    const rate = this.ctx.sampleRate;
    if (!STREAM_RATES.includes(rate) || typeof WebSocket === "undefined") return;
    try {
      const ws = new WebSocket(`${wsBase()}/api/voice/stream?token=${encodeURIComponent(token)}&language=${encodeURIComponent(language)}&rate=${rate}`);
      ws.binaryType = "arraybuffer";
      j.ws = ws; j.queue = []; j.partials = []; j.finalWaiters = [];
      ws.onopen = () => { j.open = true; for (const b of j.queue) ws.send(b === null ? JSON.stringify({ type: "end" }) : b); j.queue = []; };
      ws.onmessage = (e) => {
        let m; try { m = JSON.parse(e.data); } catch { return; }
        if (m.type === "transcript" && m.text) { j.partials.push(m.text); this.onPartial(j.partials.join(" ")); }
        if (m.type === "final") { j.finalText = m.text || ""; j.finalWaiters.forEach((f) => f(j.finalText)); j.finalWaiters = []; }
        if (m.type === "unavailable" || m.type === "error") j.streamFailed = true;
      };
      ws.onerror = ws.onclose = () => { j.closed = true; j.finalWaiters.forEach((f) => f(j.partials.join(" "))); j.finalWaiters = []; };
    } catch { j.ws = null; }
  }

  _send(j, f32) {
    if (!j.ws || j.closed) return;
    const buf = toPcm16(f32);
    if (j.open) { try { j.ws.send(buf); } catch {} } else j.queue.push(buf);
  }

  _finalize(j) {
    return new Promise((resolve) => {
      if (!j.ws || j.closed || j.streamFailed) return resolve(j.partials?.join(" ") || "");
      const timer = setTimeout(() => resolve(j.partials.join(" ")), 4500);
      j.finalWaiters.push((t) => { clearTimeout(timer); resolve(t); });
      try { if (j.open) j.ws.send(JSON.stringify({ type: "end" })); else j.queue.push(null); } catch { resolve(j.partials.join(" ")); }
    }).finally(() => { try { j.ws?.close(); } catch {} });
  }

  /** Resolves with { blob, durationMs, transcript? } when the speaker finishes, or null if cancelled / nothing was said. */
  listen({ waitMs = 25000, stream = null } = {}) {
    return new Promise((resolve) => {
      this.job = { chunks: [], speaking: false, hits: 0, t0: performance.now(), waitMs, resolve };
      if (stream) this._openStream(this.job, stream);
      this.listening = true; this.onStatus("listening");
    });
  }

  stopNow() { if (this.job?.speaking) this._finish("manual"); else this.cancel(); }
  cancel() { const j = this.job; this.job = null; this.listening = false; this.levelRef.current = 0; try { j?.ws?.close(); } catch {} j?.resolve(null); }

  _finish(reason) {
    const j = this.job; if (!j) return;
    this.job = null; this.listening = false; this.levelRef.current = 0;
    const durationMs = Math.round(performance.now() - j.startedAt);
    const res = { blob: encodeWav(j.chunks, this.ctx.sampleRate), durationMs, reason };
    if (j.ws) this._finalize(j).then((transcript) => j.resolve({ ...res, transcript: (transcript || "").trim() }));
    else j.resolve(res);
  }

  close() {
    this.cancel();
    try { this.node?.disconnect(); this.src?.disconnect(); this.stream?.getTracks().forEach((t) => t.stop()); this.ctx?.close(); } catch {}
  }
}
