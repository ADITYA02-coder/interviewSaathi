import { JSDOM } from "jsdom";
const dom = new JSDOM("<!doctype html><div id=root></div>", { url: "http://localhost/#/", pretendToBeVisual: true });
const w = dom.window;
for (const k of ["window","document","location","localStorage","sessionStorage","navigator","HTMLElement","Node","requestAnimationFrame","cancelAnimationFrame","FormData","Blob"]) {
  try { Object.defineProperty(globalThis, k, { value: w[k] ?? globalThis[k], configurable: true, writable: true }); } catch {}
}
globalThis.addEventListener = w.addEventListener.bind(w); globalThis.removeEventListener = w.removeEventListener.bind(w);
globalThis.IS_REACT_ACT_ENVIRONMENT = true; w.scrollTo = () => {}; globalThis.confirm = () => true; w.confirm = () => true;

// ---- fake audio stack
let workletNode;
class FakeCtx { constructor(){ this.sampleRate = 48000; this.destination = {}; this.audioWorklet = { addModule: async () => {} }; }
  resume = async () => {}; close = () => {};
  createAnalyser(){ return { fftSize: 1024, connect(){}, getFloatTimeDomainData(b){ b.fill(0.05); } }; }
  createGain(){ return { gain: {}, connect(n){ return n; } }; }
  createMediaStreamSource(){ return { connect: (n) => n, disconnect(){} }; }
  createBufferSource(){ const s = { connect(){}, start(){ setTimeout(() => s.onended && s.onended(), 120); }, stop(){ s.onended && s.onended(); }, playbackRate: {} }; return s; }
  async decodeAudioData(){ return { duration: 1 }; } }
globalThis.AudioContext = w.AudioContext = FakeCtx;
globalThis.AudioWorkletNode = w.AudioWorkletNode = class { constructor(){ this.port = {}; workletNode = this; } connect(n){ return n; } disconnect(){} };
const track = { stop(){} };
Object.defineProperty(w.navigator, "mediaDevices", { value: { getUserMedia: async () => ({ getTracks: () => [track] }) }, configurable: true });
globalThis.URL.createObjectURL = () => "blob:x"; globalThis.URL.revokeObjectURL = () => {};
Object.defineProperty(globalThis, "navigator", { value: w.navigator, configurable: true });

// ---- fake WebSocket for streaming STT (first answer streams a transcript, second returns nothing -> must fall back to REST upload)
class FakeWS { constructor(url){ this.url = url; this.bytes = 0; this.readyState = 0; FakeWS.all.push(this); setTimeout(() => { this.readyState = 1; this.onopen && this.onopen(); }, 10); }
  send(d){ if (typeof d === "string") { if (JSON.parse(d).type === "end") { const text = FakeWS.texts.shift() ?? ""; setTimeout(() => this.onmessage && this.onmessage({ data: JSON.stringify({ type: "final", text }) }), 20); } } else this.bytes += d.byteLength; }
  close(){ this.readyState = 3; } }
FakeWS.all = []; FakeWS.texts = ["An interface is a contract that classes implement.", ""];
globalThis.WebSocket = w.WebSocket = FakeWS;

// ---- fake backend
const calls = []; let answers = 0;
const J = (o, s = 200) => new Response(JSON.stringify(o), { status: s, headers: { "content-type": "application/json" } });
globalThis.fetch = async (url, opt = {}) => {
  const path = String(url).replace("/api", ""); calls.push(`${opt.method || "GET"} ${path}`);
  if (path === "/meta") return J({ gnani_configured: true, stream_stt: true, coding_enabled: true, code_languages: { python: "Python 3", javascript: "JavaScript (Node)", java: "Java" }, llm: "offline", llm_live: false, roles: ["Java Developer"], languages: [{ code: "en-IN", label: "English", male: true, beta: false }, { code: "hinglish", label: "Hinglish", male: true, beta: false }] });
  if (path === "/voice/tts") return new Response(new ArrayBuffer(100));
  if (path === "/voice/stt") return J({ transcript: "An interface is a contract.", language_code: "en-IN" });
  if (path === "/templates") return J([]);
  if (path === "/problems") return J([{ id: "two-sum", title: "Two Sum", difficulty: "easy", topic: "Arrays and Hashing", solved: false }]);
  if (path === "/problems/two-sum") return J({ ...{ id: "two-sum", title: "Two Sum", difficulty: "easy", topic: "Arrays and Hashing", statement: "Find two indices.", input_format: "n, array, target", output_format: "two indices", examples: [{ input: "4\\n2 7 11 15\\n9", output: "0 1" }], starters: { python: "# starter\\n", javascript: "// js\\n", java: "// java\\n" }, visible_tests: 2, hidden_tests: 8 }, last_submission: null });
  if (path === "/admin/stats") return J({ students: 12, guests: 3, interviews: 40, completed: 31, average_score: 68, active_7d: 9, answers_by_voice: 120, answers_by_text: 14, languages: { "en-IN": 30 }, types: { technical: 20 }, per_day: Array.from({ length: 30 }, (_, i) => ({ date: "2026-01-" + (i + 1), count: i % 4 })), code_submissions: 7, code_accept_rate: 57, open_support: 2, cohorts: 2, unverified: 2 });
  if (path === "/admin/email") return J({ configured: true, host: "smtp-relay.brevo.com", port: 2525, security: "starttls", from: "InterviewSaathi <no-reply@c.edu>", user: "a1b***", verification_mode: "email", app_url: "https://app.example.com" });
  if (path === "/admin/email/test") { globalThis.__mailTests = (globalThis.__mailTests || 0) + 1; return J(globalThis.__mailTests === 1 ? { ok: false, error: "The mail server refused the login. Check SMTP_USER and SMTP_PASSWORD." } : { ok: true }); }
  if (path.startsWith("/admin/users/verify")) return J({ verified: 2 });
  if (path.endsWith("/verify")) return J({ ok: true });
  if (path.startsWith("/admin/users")) return J([{ id: 8, name: "Rahul Jain", email: "rahul@c.edu", role: "student", verified: false, interviews: 0, joined: "2026-01-03T00:00:00" }, { id: 9, name: "Meera Pillai", email: "meera@c.edu", role: "student", verified: false, interviews: 1, joined: "2026-01-02T00:00:00" }, { id: 1, name: "Dean", email: "dean@c.edu", role: "admin", verified: true, interviews: 0, joined: "2026-01-01T00:00:00" }]);
  if (path === "/admin/cohorts") return J([{ id: 1, name: "CSE 2026", code: "K7P2QX", members: 12 }]);
  if (path.startsWith("/admin/leaderboard")) return J([{ id: 5, name: "Priya Sharma", email: "p@c.edu", cohorts: ["CSE 2026"], interviews: 4, average: 81, latest: 85, best: 90, improvement: 12, problems_solved: 5, weakest_topic: "SQL", last_active: "2026-01-02T00:00:00", needs_attention: false, rank: 1 }]);
  if (path.endsWith("/code/run")) return J({ status: "wrong_answer", passed: 1, total: 2, max_time_ms: 40, tests: [{ i: 1, hidden: false, status: "pass", time_ms: 20, input: "x", expected: "0 1", actual: "0 1" }, { i: 2, hidden: false, status: "wrong_answer", time_ms: 40, input: "y", expected: "1 2", actual: "0 0" }] });
  if (path.endsWith("/code/submit")) return J({ result: { status: "accepted", passed: 10, total: 10, max_time_ms: 30, tests: [{ i: 1, hidden: false, status: "pass", time_ms: 10, input: "a", expected: "b", actual: "b" }] }, reply: "Nice, every test passed. What is the time complexity?", coding: { phase: "followup", index: 0, total: 1, problem: { id: "two-sum", title: "Two Sum", difficulty: "easy", topic: "Arrays and Hashing", statement: "Find two indices.", input_format: "n, array, target", output_format: "two indices", examples: [{ input: "4\\n2 7 11 15\\n9", output: "0 1" }], starters: { python: "# starter\\n", javascript: "// js\\n", java: "// java\\n" }, visible_tests: 2, hidden_tests: 8 }, language: "python", submitted: true } });
  if (path === "/interviews/cod/answer") { answers++; const first = answers === 3; return J(first ? { reply: "Sounds reasonable. Go ahead and code it.", topic: "Arrays", kind: "main", done: false, turn_index: 2, answered: 1, coding: { phase: "coding", index: 0, total: 1, problem: { id: "two-sum", title: "Two Sum", difficulty: "easy", topic: "Arrays and Hashing", statement: "Find two indices.", input_format: "n, array, target", output_format: "two indices", examples: [{ input: "4\\n2 7 11 15\\n9", output: "0 1" }], starters: { python: "# starter\\n", javascript: "// js\\n", java: "// java\\n" }, visible_tests: 2, hidden_tests: 8 }, language: "python", submitted: false } } : { reply: "Thank you, that completes the coding round.", topic: "Wrap up", kind: "closing", done: true, turn_index: 6, answered: 1, coding: { phase: "done", index: 1, total: 1, problem: null } }); }
  if (path.endsWith("/answer")) { answers++; return J({ reply: answers >= 2 ? "Thank you, that is the end." : "Good. Next question here.", topic: "OOP", kind: answers >= 2 ? "closing" : "main", done: answers >= 2, turn_index: answers * 2, answered: answers }); }
  if (path.endsWith("/finish")) return J({ report: {} });
  if (path.startsWith("/interviews/")) return J({ id: "abc", config: { role: "Java Developer", interview_type: "technical", difficulty: "beginner" }, status: "completed", started_at: new Date().toISOString().replace("Z", ""), turns: [
      { role: "interviewer", text: "Explain interfaces.", kind: "main" },
      { role: "candidate", text: "An interface is a contract.", kind: "answer", source: "voice", question: "Explain interfaces.", evaluation: { scores: { accuracy: 80, relevance: 70, completeness: 60, clarity: 75 }, overall: 72, topic: "OOP", correct_concepts: ["contract"], missing_concepts: ["default methods"], inaccuracies: [], explanation: "Solid.", improvements: ["Add an example."], model_answer: "An interface defines..." } }],
    report: { overall: 72, headline: "A solid base.", dimensions: { accuracy: 80, relevance: 70, completeness: 60, clarity: 75 }, dimension_labels: { accuracy: "Technical accuracy", relevance: "Relevance", completeness: "Completeness", clarity: "Clarity" }, topics: [{ topic: "OOP", score: 72, count: 1 }], answered: 1, strengths: ["OOP"], improvements: [], study_plan: [], engine: "test", disclaimer: "Estimates." } });
  if (path === "/dashboard") return J({ total_completed: 2, average_overall: 70, by_type: [], sessions: [{ id: "a", date: "2026-01-01", overall: 60, dimensions: { accuracy: 50, relevance: 60, completeness: 60, clarity: 70 } }, { id: "b", date: "2026-01-02", overall: 80, dimensions: { accuracy: 80, relevance: 80, completeness: 70, clarity: 80 } }], weakest_topics: [{ topic: "SQL", score: 40, count: 1 }], strongest_topics: [{ topic: "OOP", score: 85, count: 2 }], first_vs_latest: { first: { overall: 60, dimensions: { accuracy: 50, relevance: 60, completeness: 60, clarity: 70 } }, latest: { overall: 80, dimensions: { accuracy: 80, relevance: 80, completeness: 70, clarity: 80 } } }, recommended_practice: ["SQL"] });
  if (path === "/interviews") return J([]);
  if (path === "/auth/me") return J({ id: 1, name: "Asha", email: "asha@c.edu", is_guest: false, role: "admin", cohorts: [], email_verified: true, preferred_language: "en-IN" });
  return J({ detail: "nope " + path }, 404);
};
localStorage.setItem("is_token", "tok");

const React = (await import("react")).default;
const { createRoot } = await import("react-dom/client");
const { act } = await import("react");
const App = (await import("../_ssr_app/App.js")).default;
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const root = createRoot(document.getElementById("root"));
const text = () => document.body.textContent;
const errors = []; const ce = console.error; console.error = (...a) => { errors.push(a.join(" ").slice(0, 200)); };
const nav = async (h) => { await act(async () => { location.hash = h; await sleep(80); }); };
const ok = (c, m) => { console.log((c ? "PASS " : "FAIL ") + m); if (!c) process.exitCode = 1; };

await act(async () => { root.render(React.createElement(App)); await sleep(100); });
ok(/actually talking/.test(text()), "landing renders");
await nav("#/setup"); ok(/Set up your interview/.test(text()) && !!document.querySelector(".btn.gold.lg"), "setup renders");
await nav("#/dashboard"); ok(/Score over time/.test(text()) && /60 → 80/.test(text()) || /50 → 80/.test(text()), "dashboard renders with real data");
await nav("#/report/abc"); await act(async () => { await sleep(150); }); ok(/A solid base/.test(text()) && /One possible strong answer/.test(text()), "report renders");

// ---- full room conversation
sessionStorage.setItem("is_room_xyz", JSON.stringify({ id: "xyz", config: { role: "Java Developer", interview_type: "technical", language: "en-IN", interviewer: "female" }, persona: "Ananya", voice: { voice: "Kaveri", tts_language: "en-IN", stt_language: "en-IN", speed: 1 }, total_questions: 2, opening: { text: "Hello. Explain interfaces. Take your time." } }));
await nav("#/room/xyz"); await act(async () => { await sleep(100); });
ok(/Ananya is ready/.test(text()), "room gate shown");
const join = [...document.querySelectorAll("button")].find((b) => /Join interview/.test(b.textContent));
await act(async () => { join.click(); await sleep(60); });
ok(/Ananya is speaking/.test(text()), "interviewer speaks after join");
await act(async () => { await sleep(700); });
ok(/Your turn/.test(text()), "switches to listening after speech ends");
const loud = () => new Float32Array(2048).fill(0.2), quiet = () => new Float32Array(2048).fill(0.001);
const waitFor = async (cond, ms = 6000) => { const t0 = Date.now(); while (Date.now() - t0 < ms) { if (cond()) return true; await act(async () => { await sleep(50); }); } return false; };
async function speakAnswer() {
  for (let i = 0; i < 20; i++) await act(async () => { workletNode.port.onmessage({ data: loud() }); await sleep(45); });
  ok(/Listening…/.test(text()), "VAD detects speech");
  const n = calls.filter((c) => c === "POST /voice/stt").length;
  for (let i = 0; i < 120 && calls.filter((c) => c === "POST /voice/stt").length === n; i++) await act(async () => { workletNode.port.onmessage({ data: quiet() }); await sleep(30); });
}
await speakAnswer();
ok(await waitFor(() => calls.some((c) => c.endsWith("/xyz/answer"))), "transcript submitted to interviewer");
ok(FakeWS.all.length >= 1 && FakeWS.all[0].bytes > 0 && /voice\/stream\?token=tok&language=en-IN&rate=48000/.test(FakeWS.all[0].url), "audio was streamed live over the WebSocket (" + FakeWS.all[0].bytes + " bytes)");
ok(!calls.includes("POST /voice/stt"), "streamed transcript used directly: no REST upload needed");
ok(await waitFor(() => /Your turn/.test(text())), "second question: listening again");
await speakAnswer();
ok(await waitFor(() => calls.includes("POST /voice/stt")), "empty stream result falls back to the REST upload");
ok(await waitFor(() => calls.some((c) => c.endsWith("/finish"))), "interview finishes after final answer");
ok(await waitFor(() => location.hash.startsWith("#/report/xyz")), "navigates to the report");

// ---- practice + admin pages
await nav("#/code"); ok(await waitFor(() => /Two Sum/.test(text())), "practice list renders");
await nav("#/code/two-sum"); ok(await waitFor(() => /Run samples/.test(text()) && /Find two indices/.test(text())), "practice solve page renders with editor");
await nav("#/admin"); ok(await waitFor(() => /interviews completed/.test(text()) && /57%/.test(text())), "admin overview renders stats");
await nav("#/admin/leaderboard"); ok(await waitFor(() => /Priya Sharma/.test(text()) && /needs attention|\+12/.test(text())), "admin leaderboard renders students");
await nav("#/admin/groups"); ok(await waitFor(() => /K7P2QX/.test(text())), "admin groups shows the join code");

// ---- admin approves students (no-email verification)
calls.length = 0;
await nav("#/admin/users"); ok(await waitFor(() => /Rahul Jain/.test(text()) && /Verify all 2 shown/.test(text())), "Users tab lists unverified students with a bulk button");
ok(!!document.querySelector('[title="Students waiting to be verified"]'), "Users tab shows a pending-count badge");
await act(async () => { [...document.querySelectorAll("button")].find((b) => /^Mark verified$/.test(b.textContent.trim())).click(); await sleep(60); });
ok(await waitFor(() => calls.includes("PUT /admin/users/8/verify")), "Mark verified calls the API for that student");
await act(async () => { [...document.querySelectorAll("button")].find((b) => /Verify all 2 shown/.test(b.textContent)).click(); await sleep(60); });
ok(await waitFor(() => calls.includes("POST /admin/users/verify")), "Verify all approves the shown students in one call");

// ---- admin email setup + test button
await nav("#/admin/email"); ok(await waitFor(() => /smtp-relay\.brevo\.com:2525/.test(text()) && /configured/.test(text())), "Email tab shows SMTP status");
const sendTest = async () => { await act(async () => { [...document.querySelectorAll("button")].find((b) => /Send test email/.test(b.textContent)).click(); await sleep(80); }); };
await sendTest(); ok(await waitFor(() => /refused the login/.test(text())), "failed test shows the plain-language reason");
await sendTest(); ok(await waitFor(() => /Sent\. Check the inbox/.test(text())), "successful test shows confirmation");

// ---- full coding interview in the room
FakeWS.texts = ["I would use a hash map to store the complement of each number.", "Time is O of n and space is O of n."]; answers = 2;
sessionStorage.setItem("is_room_cod", JSON.stringify({ id: "cod", config: { role: "Java Developer", interview_type: "coding", language: "en-IN", interviewer: "female", code_language: "python" }, persona: "Ananya", voice: { voice: "Kaveri", tts_language: "en-IN", stt_language: "en-IN", speed: 1 }, total_questions: 1, opening: { text: "Hello. Today is a coding round. Walk me through your approach." },
  coding: { phase: "approach", index: 0, total: 1, problem: JSON.parse(JSON.stringify({ id: "two-sum", title: "Two Sum", difficulty: "easy", topic: "Arrays and Hashing", statement: "Find two indices.", input_format: "n", output_format: "idx", examples: [], starters: { python: "# starter\\n", javascript: "", java: "" } })), language: "python", submitted: false } }));
calls.length = 0;
await nav("#/room/cod"); await act(async () => { await sleep(100); });
await act(async () => { [...document.querySelectorAll("button")].find((b) => /Join interview/.test(b.textContent)).click(); await sleep(60); });
ok(await waitFor(() => /Step 1/.test(text()) && /Two Sum/.test(text())), "coding room shows the problem and step 1");
ok(await waitFor(() => /Your turn/.test(text())), "interviewer waits for the spoken approach");
await speakAnswer();
ok(await waitFor(() => /Step 2/.test(text())), "after the approach she tells you to code (phase 2)");
ok(await waitFor(() => /Your turn to code/.test(text())), "she stops listening while you code");
ok(!!document.querySelector(".editor textarea"), "code editor is shown");
await act(async () => { [...document.querySelectorAll("button")].find((b) => /Run samples/.test(b.textContent)).click(); await sleep(80); });
ok(await waitFor(() => calls.some((c) => c.endsWith("/code/run")) && /1 \/ 2 tests passed/.test(text())), "Run samples shows results from the sandbox");
await act(async () => { [...document.querySelectorAll("button")].find((b) => /^Submit$/.test(b.textContent.trim())).click(); await sleep(80); });
ok(await waitFor(() => calls.some((c) => c.endsWith("/code/submit")) && /Step 3/.test(text())), "Submit moves to the complexity follow-up (phase 3)");
ok(await waitFor(() => /Your turn/.test(text()) && !/Your turn to code/.test(text())), "she asks about complexity and listens again");
await speakAnswer();
ok(await waitFor(() => calls.some((c) => c.endsWith("/finish"))), "coding interview finishes after the follow-up");
console.log("console errors:", errors.length ? errors : "none");
console.log("calls:", calls.join(" | "));
process.exit(process.exitCode || 0);
