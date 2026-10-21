const KEY = "is_token";
// Same-origin by default (backend serves the UI, or the dev proxy). Set VITE_API_URL at build time when the UI is hosted elsewhere (e.g. Vercel).
export const API_BASE = (import.meta.env?.VITE_API_URL || "").replace(/\/+$/, "");
export const wsBase = () => (API_BASE ? API_BASE.replace(/^http/, "ws") : `${location.protocol === "https:" ? "wss" : "ws"}://${location.host}`);
export const session = {
  get token() { return localStorage.getItem(KEY) || ""; },
  set token(v) { v ? localStorage.setItem(KEY, v) : localStorage.removeItem(KEY); },
};

export class ApiError extends Error {
  constructor(message, status, code) { super(message); this.status = status; this.code = code; }
}

async function request(path, { method = "GET", body, form } = {}) {
  const headers = {};
  if (session.token) headers.Authorization = `Bearer ${session.token}`;
  let payload;
  if (form) payload = form;
  else if (body !== undefined) { headers["Content-Type"] = "application/json"; payload = JSON.stringify(body); }
  let res;
  try { res = await fetch(`${API_BASE}/api${path}`, { method, headers, body: payload }); }
  catch { throw new ApiError("Can't reach the server. Is the backend running?", 0, "network"); }
  if (!res.ok) {
    let d = {}; try { d = await res.json(); } catch {}
    const msg = typeof d.detail === "string" ? d.detail : Array.isArray(d.detail) ? d.detail.map((x) => x.msg).join(", ") : `Request failed (${res.status})`;
    throw new ApiError(msg, res.status, d.code);
  }
  return res;
}
const json = async (p, o) => (await request(p, o)).json();

export const api = {
  meta: () => json("/meta"),
  guest: () => json("/auth/guest", { method: "POST" }),
  register: (b) => json("/auth/register", { method: "POST", body: b }),
  login: (b) => json("/auth/login", { method: "POST", body: b }),
  me: () => json("/auth/me"),
  updateMe: (b) => json("/auth/me", { method: "PUT", body: b }),
  parseResume: (file) => { const f = new FormData(); f.append("file", file); return json("/resume/parse", { method: "POST", form: f }); },
  createInterview: (b) => json("/interviews", { method: "POST", body: b }),
  answer: (id, b) => json(`/interviews/${id}/answer`, { method: "POST", body: b }),
  finish: (id) => json(`/interviews/${id}/finish`, { method: "POST" }),
  interview: (id) => json(`/interviews/${id}`),
  interviews: () => json("/interviews"),
  remove: (id) => json(`/interviews/${id}`, { method: "DELETE" }),
  dashboard: () => json("/dashboard"),
  codeRun: (id, b) => json(`/interviews/${id}/code/run`, { method: "POST", body: b }),
  codeSubmit: (id, b) => json(`/interviews/${id}/code/submit`, { method: "POST", body: b }),
  codeSkip: (id) => json(`/interviews/${id}/code/skip`, { method: "POST" }),
  problems: () => json("/problems"),
  problem: (id) => json(`/problems/${id}`),
  practiceRun: (id, b) => json(`/problems/${id}/run`, { method: "POST", body: b }),
  practiceSubmit: (id, b) => json(`/problems/${id}/submit`, { method: "POST", body: b }),
  forgot: (email) => json("/auth/forgot", { method: "POST", body: { email } }),
  reset: (b) => json("/auth/reset", { method: "POST", body: b }),
  verify: (token) => json("/auth/verify", { method: "POST", body: { token } }),
  resendVerify: () => json("/auth/verify/send", { method: "POST" }),
  joinCohort: (code) => json("/cohorts/join", { method: "POST", body: { code } }),
  leaveCohort: (id) => json(`/cohorts/${id}/leave`, { method: "DELETE" }),
  shareCohort: (id, v) => json(`/cohorts/${id}/sharing`, { method: "PUT", body: { share_transcripts: v } }),
  templates: () => json("/templates"),
  support: (b) => json("/support", { method: "POST", body: b }),
  mySupport: () => json("/support"),
  // generic admin helpers
  get: (p) => json(p), post: (p, body) => json(p, { method: "POST", body }), put: (p, body) => json(p, { method: "PUT", body }), del: (p) => json(p, { method: "DELETE" }),
  stt: (blob, language) => { const f = new FormData(); f.append("audio", blob, "answer.wav"); f.append("language", language); return json("/voice/stt", { method: "POST", form: f }); },
  tts: async (text, voice, language, speed) => (await request("/voice/tts", { method: "POST", body: { text, voice, language, speed } })).arrayBuffer(),
};
