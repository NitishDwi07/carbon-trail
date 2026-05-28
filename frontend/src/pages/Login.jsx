import { useState } from "react";

export default function Login({ onLogin, API }) {
  const [username, setUsername] = useState("analyst");
  const [password, setPassword] = useState("password123");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [mode, setMode] = useState("login"); // login | register

  async function submit(e) {
    e.preventDefault();
    setLoading(true);
    setError("");
    try {
      const endpoint = mode === "login" ? "login" : "register";
      const body = mode === "login"
        ? { username, password }
        : { username, password, org_name: "Demo Corp" };

      const res = await fetch(`${API}/auth/${endpoint}/`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || "Auth failed");
      onLogin(data.token, data.username, data.org);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen bg-stone-950 font-mono flex items-center justify-center">
      <div className="w-full max-w-sm">
        {/* Logo */}
        <div className="text-center mb-10">
          <h1 className="text-2xl font-bold text-stone-100 tracking-tight">
            breathe<span className="text-emerald-400">/</span>esg
          </h1>
          <p className="text-stone-500 text-xs mt-1">emissions data ingestion platform</p>
        </div>

        <div className="bg-stone-900 border border-stone-800 rounded-lg p-6">
          <div className="flex gap-1 mb-6 bg-stone-950 rounded p-1">
            {["login", "register"].map((m) => (
              <button
                key={m}
                onClick={() => setMode(m)}
                className={`flex-1 py-1.5 text-xs rounded transition-colors ${
                  mode === m
                    ? "bg-emerald-400/10 text-emerald-400 border border-emerald-400/20"
                    : "text-stone-500 hover:text-stone-300"
                }`}
              >
                {m}
              </button>
            ))}
          </div>

          <form onSubmit={submit} className="space-y-4">
            <div>
              <label className="block text-xs text-stone-400 mb-1">username</label>
              <input
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                className="w-full bg-stone-950 border border-stone-700 rounded px-3 py-2 text-sm text-stone-100 focus:outline-none focus:border-emerald-500 transition-colors"
                required
              />
            </div>
            <div>
              <label className="block text-xs text-stone-400 mb-1">password</label>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full bg-stone-950 border border-stone-700 rounded px-3 py-2 text-sm text-stone-100 focus:outline-none focus:border-emerald-500 transition-colors"
                required
              />
            </div>

            {error && (
              <p className="text-red-400 text-xs bg-red-400/10 border border-red-400/20 rounded px-3 py-2">
                {error}
              </p>
            )}

            <button
              type="submit"
              disabled={loading}
              className="w-full bg-emerald-500 hover:bg-emerald-400 disabled:opacity-50 text-stone-950 font-bold text-sm py-2 rounded transition-colors"
            >
              {loading ? "..." : mode === "login" ? "sign in" : "create account"}
            </button>
          </form>

          {mode === "login" && (
            <p className="text-stone-600 text-xs text-center mt-4">
              demo: analyst / password123
            </p>
          )}
        </div>
      </div>
    </div>
  );
}
