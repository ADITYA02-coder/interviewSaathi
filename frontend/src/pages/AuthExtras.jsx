import { useEffect, useState } from "react";
import { api } from "../lib/api.js";
import { go, useApp } from "../App.jsx";

export function Forgot() {
  const [email, setEmail] = useState(""); const [sent, setSent] = useState(false); const [err, setErr] = useState("");
  const submit = async (e) => { e.preventDefault(); setErr(""); try { await api.forgot(email); setSent(true); } catch (x) { setErr(x.message); } };
  return (
    <div className="wrap"><div className="card auth">
      <h2 style={{ fontSize: 30, marginBottom: 8 }}>Forgot your password?</h2>
      {sent ? <p>If an account exists for <b>{email}</b>, a reset link is on its way. It works for one hour.</p> : (
        <form onSubmit={submit}><p className="sub" style={{ marginBottom: 14 }}>Enter your email and we'll send you a reset link.</p>
          <div className="field"><label htmlFor="fe">Email</label><input id="fe" type="email" required value={email} onChange={(e) => setEmail(e.target.value)} /></div>
          {err && <p className="err" role="alert" style={{ marginBottom: 12 }}>{err}</p>}
          <button className="btn gold" style={{ width: "100%" }}>Send reset link</button></form>)}
      <p style={{ marginTop: 16 }}><a href="#/login">Back to sign in</a></p>
    </div></div>
  );
}

export function Reset({ token }) {
  const { signIn } = useApp();
  const [pw, setPw] = useState(""); const [err, setErr] = useState("");
  const submit = async (e) => { e.preventDefault(); setErr(""); try { signIn(await api.reset({ token, password: pw })); go("dashboard"); } catch (x) { setErr(x.message); } };
  return (
    <div className="wrap"><form className="card auth" onSubmit={submit}>
      <h2 style={{ fontSize: 30, marginBottom: 12 }}>Choose a new password</h2>
      <div className="field"><label htmlFor="np">New password (8+ characters)</label><input id="np" type="password" minLength={8} required value={pw} onChange={(e) => setPw(e.target.value)} autoComplete="new-password" /></div>
      {err && <p className="err" role="alert" style={{ marginBottom: 12 }}>{err}</p>}
      <button className="btn gold" style={{ width: "100%" }}>Save and sign in</button>
    </form></div>
  );
}

export function Verify({ token }) {
  const { user, setUser } = useApp();
  const [state, setState] = useState("working");
  useEffect(() => { api.verify(token).then(() => { setState("ok"); if (user) setUser({ ...user, email_verified: true }); }).catch(() => setState("bad")); }, [token]);
  return (
    <div className="wrap"><div className="card auth" style={{ textAlign: "center" }}>
      {state === "working" && <p>Verifying…</p>}
      {state === "ok" && <><h2 style={{ fontSize: 30 }}>Email verified ✓</h2><p className="sub" style={{ margin: "10px 0 18px" }}>Thanks! Your account is confirmed.</p><a className="btn gold" href="#/setup">Start practising</a></>}
      {state === "bad" && <><h2 style={{ fontSize: 30 }}>That link didn't work</h2><p className="sub" style={{ margin: "10px 0 18px" }}>It may have expired. Sign in and request a new one from your profile.</p><a className="btn" href="#/login">Sign in</a></>}
    </div></div>
  );
}
