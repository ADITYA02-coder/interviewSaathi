import { createContext, useContext, useEffect, useState } from "react";
import { api, session } from "./lib/api.js";
import Landing from "./pages/Landing.jsx";
import Auth from "./pages/Auth.jsx";
import Setup from "./pages/Setup.jsx";
import Room from "./pages/Room.jsx";
import Report from "./pages/Report.jsx";
import Dashboard from "./pages/Dashboard.jsx";
import Profile from "./pages/Profile.jsx";
import { PracticeList, PracticeSolve } from "./pages/Practice.jsx";
import { Forgot, Reset, Verify } from "./pages/AuthExtras.jsx";
import Admin from "./pages/Admin.jsx";

const Ctx = createContext(null);
export const useApp = () => useContext(Ctx);

export const go = (path) => { location.hash = "#/" + path; };
const parse = () => { const [name = "", ...rest] = location.hash.replace(/^#\/?/, "").split("/"); return { name, arg: rest[0], rest }; };
const initials = (name = "") => name.trim().split(/\s+/).slice(0, 2).map((part) => part[0]).join("").toUpperCase() || "?";

export default function App() {
  const [route, setRoute] = useState(parse());
  const [user, setUser] = useState(null);
  const [meta, setMeta] = useState(null);
  const [ready, setReady] = useState(false);
  const [profileOpen, setProfileOpen] = useState(false);

  useEffect(() => { const f = () => { setRoute(parse()); setProfileOpen(false); window.scrollTo(0, 0); }; addEventListener("hashchange", f); return () => removeEventListener("hashchange", f); }, []);
  useEffect(() => {
    api.meta().then(setMeta).catch(() => setMeta({ gnani_configured: false, llm: "unknown", languages: [], roles: [], offline: true }));
    (session.token ? api.me().then(setUser).catch(() => { session.token = ""; }) : Promise.resolve()).finally(() => setReady(true));
  }, []);

  const signIn = ({ token, user }) => { session.token = token; setUser(user); };
  const signOut = () => { session.token = ""; setUser(null); go(""); };
  const ensureUser = async () => { if (user) return user; const r = await api.guest(); signIn(r); return r.user; };

  if (!ready) return null;
  const ctx = { user, setUser, signIn, signOut, ensureUser, meta };
  const { name, arg, rest } = route;
  if (name === "room") return <Ctx.Provider value={ctx}><Room id={arg} /></Ctx.Provider>;

  let page;
  if (name === "login") page = <Auth />;
  else if (name === "setup") page = <Setup />;
  else if (name === "report") page = <Report id={arg} />;
  else if (name === "dashboard") page = <Dashboard />;
  else if (name === "profile") page = <Profile />;
  else if (name === "forgot") page = <Forgot />;
  else if (name === "reset") page = <Reset token={arg} />;
  else if (name === "verify") page = <Verify token={arg} />;
  else if (name === "code") page = arg ? <PracticeSolve id={arg} /> : <PracticeList />;
  else if (name === "admin") page = user?.role === "admin" ? <Admin path={rest} /> : <div className="wrap"><p className="notice">Admins only. {user ? "Your account doesn't have admin access." : <a href="#/login">Sign in</a>}</p></div>;
  else page = <Landing />;

  return (
    <Ctx.Provider value={ctx}>
      <div className="shell">
        <header className="nav">
          <a className="logo" href="#/"><i /><span>Interview<span className="logo-accent">Saathi</span></span></a>
          <nav>
            <a href="#/setup" className={name === "setup" ? "on" : ""}>Practice room</a>
            <a href="#/code" className={name === "code" ? "on" : ""}>Coding lab</a>
            <a href="#/dashboard" className={name === "dashboard" ? "on" : ""}>Your progress</a>
            {user?.role === "admin" && <a href="#/admin" className={name === "admin" ? "on" : ""}>Admin</a>}
            {user && !user.is_guest ? (<div className="profile-menu">
              <button className={`profile-trigger ${name === "profile" ? "on" : ""}`} type="button" aria-label="Open profile menu" aria-expanded={profileOpen} onClick={() => setProfileOpen((open) => !open)}>
                <span className="profile-avatar" aria-hidden="true">{initials(user.name)}</span><span className="profile-caret" aria-hidden="true">⌄</span>
              </button>
              {profileOpen && <div className="profile-dropdown">
                <div className="profile-summary"><span className="profile-avatar large" aria-hidden="true">{initials(user.name)}</span><div><b>{user.name}</b><span>{user.email}</span></div></div>
                <a href="#/profile">Profile settings</a>
                {user.role === "admin" && <a href="#/admin">Admin console</a>}
                <button type="button" onClick={signOut}>Sign out</button>
              </div>}
            </div>)
              : <a href="#/login" className={name === "login" ? "on" : ""}>{user ? "Save my progress" : "Sign in"}</a>}
          </nav>
        </header>
        <main className={name ? "page" : ""}>{page}</main>
      </div>
    </Ctx.Provider>
  );
}
