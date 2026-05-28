import { useState, useEffect, createContext, useContext } from "react";
import Login from "./pages/Login";
import Dashboard from "./pages/Dashboard";
import ReviewTable from "./pages/ReviewTable";
import Upload from "./pages/Upload";
import Batches from "./pages/Batches";

const API = import.meta.env.VITE_API_URL || "http://localhost:8000/api";
export const AppContext = createContext(null);

export function useApp() {
  return useContext(AppContext);
}

export default function App() {
  const [token, setToken] = useState(() => localStorage.getItem("token"));
  const [user, setUser] = useState(() => localStorage.getItem("user"));
  const [org, setOrg] = useState(() => localStorage.getItem("org"));
  const [page, setPage] = useState("dashboard");
  const [reviewKey, setReviewKey] = useState(0);

  function login(tok, username, orgName) {
    setToken(tok);
    setUser(username);
    setOrg(orgName);
    localStorage.setItem("token", tok);
    localStorage.setItem("user", username);
    localStorage.setItem("org", orgName);
  }

  function logout() {
    setToken(null);
    setUser(null);
    setOrg(null);
    localStorage.clear();
    setPage("dashboard");
  }

  async function apiFetch(path, opts = {}) {
    const res = await fetch(`${API}${path}`, {
      ...opts,
      headers: {
        ...(opts.headers || {}),
        ...(token ? { Authorization: `Token ${token}` } : {}),
        ...(opts.body && !(opts.body instanceof FormData)
          ? { "Content-Type": "application/json" }
          : {}),
      },
    });
    return res;
  }

  if (!token) {
    return <Login onLogin={login} API={API} />;
  }

  const navItems = [
    { id: "dashboard", label: "Dashboard" },
    { id: "review", label: "Review Records" },
    { id: "upload", label: "Upload Data" },
    { id: "batches", label: "Batches" },
  ];

  return (
    <AppContext.Provider value={{ apiFetch, user, org }}>
      <div className="min-h-screen bg-stone-950 text-stone-100 font-mono">
        {/* Top nav */}
        <header className="border-b border-stone-800 px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <span className="text-emerald-400 font-bold text-lg tracking-tight">
              breathe<span className="text-stone-400">/</span>esg
            </span>
            <span className="text-stone-600 text-xs">|</span>
            <span className="text-stone-500 text-xs">{org}</span>
          </div>

          <nav className="flex items-center gap-1">
            {navItems.map((n) => (
              <button
                key={n.id}
                onClick={() => setPage(n.id)}
                className={`px-3 py-1.5 rounded text-xs transition-colors ${
                  page === n.id
                    ? "bg-emerald-400/10 text-emerald-400 border border-emerald-400/30"
                    : "text-stone-400 hover:text-stone-200 hover:bg-stone-800"
                }`}
              >
                {n.label}
              </button>
            ))}
          </nav>

          <div className="flex items-center gap-3">
            <span className="text-stone-500 text-xs">{user}</span>
            <button
              onClick={logout}
              className="text-xs text-stone-600 hover:text-stone-400 transition-colors"
            >
              sign out
            </button>
          </div>
        </header>

        <main className="p-6">
          {page === "dashboard" && <Dashboard />}
          {page === "review" && <ReviewTable key={reviewKey} />}
          {page === "upload" && <Upload onDone={() => { setReviewKey(k => k + 1); setPage("review"); }} />}
          {page === "batches" && <Batches />}
        </main>
      </div>
    </AppContext.Provider>
  );
}