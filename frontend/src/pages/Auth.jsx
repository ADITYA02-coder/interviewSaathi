import { useState } from "react";
import { api } from "../lib/api.js";
import { go, useApp } from "../App.jsx";

export default function Auth() {
  const { signIn, user } = useApp();
  const [tab, setTab] = useState("register");
  const [f, setF] = useState({ name: "", email: "", password: "" });
  const [err, setErr] = useState(""); const [busy, setBusy] = useState(false);
  const set = (k) => (e) => setF({ ...f, [k]: e.target.value });

  const submit = async (e) => {
    e.preventDefault(); setErr(""); setBusy(true);
    try {
      const r = tab === "login" ? await api.login({ email: f.email, password: f.password }) : await api.register(f);
      signIn(r); go("dashboard");
    } catch (x) { setErr(x.message); } finally { setBusy(false); }
  };
  return (
    <div className="wrap"><div className="card auth">
      <h2 style={{ fontSize: 30, marginBottom: 6 }}>{tab === "login" ? "Welcome back" : "Save your progress"}</h2>
      <p className="sub" style={{ marginBottom: 18 }}>{user?.is_guest && tab === "register" ? "Your guest interviews will move to your new account." : "Create an account to keep your interview history and track improvement."}</p>
      <div className="tabs" role="tablist"><button type="button" className={tab === "register" ? "on" : ""} onClick={() => setTab("register")}>Create account</button><button type="button" className={tab === "login" ? "on" : ""} onClick={() => setTab("login")}>Sign in</button></div>
      <form onSubmit={submit}>
        {tab === "register" && <div className="field"><label htmlFor="n">Your name</label><input id="n" type="text" required value={f.name} onChange={set("name")} autoComplete="name" /></div>}
        <div className="field"><label htmlFor="e">Email</label><input id="e" type="email" required value={f.email} onChange={set("email")} autoComplete="email" /></div>
        <div className="field"><label htmlFor="p">Password {tab === "register" && <span className="sub">(8+ characters)</span>}</label><input id="p" type="password" required minLength={8} value={f.password} onChange={set("password")} autoComplete={tab === "login" ? "current-password" : "new-password"} /></div>
        {err && <p className="err" role="alert" style={{ marginBottom: 12 }}>{err}</p>}
        {tab === "login" && <p style={{ margin: "-4px 0 14px", fontSize: 14 }}><a href="#/forgot">Forgot your password?</a></p>}
        <button className="btn gold" style={{ width: "100%" }} disabled={busy}>{busy ? "Please wait…" : tab === "login" ? "Sign in" : "Create account"}</button>
      </form>
    </div></div>
  );
}
