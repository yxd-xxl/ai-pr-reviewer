import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";

const API = "http://localhost:8000";

export default function Connect() {
  const navigate = useNavigate();
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [user, setUser] = useState<{ login: string } | null>(null);
  const [repos, setRepos] = useState<any[]>([]);
  const [repoFilter, setRepoFilter] = useState("");

  useEffect(() => {
    const token = localStorage.getItem("ai_pr_token");
    const repo = localStorage.getItem("ai_pr_repo");

    // Already fully set up → skip to review queue
    if (token && repo) {
      fetch(`${API}/api/v1/auth/me`, { headers: { Authorization: `Bearer ${token}` } })
        .then(r => { if (r.ok) navigate("/review-queue"); })
        .catch(() => {});
      return;
    }

    // Logged in but no repo selected → auto-load user + repos
    if (token) {
      fetch(`${API}/api/v1/auth/me`, { headers: { Authorization: `Bearer ${token}` } })
        .then(r => r.json())
        .then(data => {
          if (data.login) { setUser(data); loadRepos(token); }
          else { localStorage.removeItem("ai_pr_token"); }
        })
        .catch(() => {});
    }

    // OAuth error from callback
    const params = new URLSearchParams(window.location.search);
    const oauthErr = params.get("error");
    if (oauthErr) {
      setError("OAuth failed: " + decodeURIComponent(oauthErr));
      window.history.replaceState({}, "", "/connect");
    }
  }, []);

  async function loadRepos(token: string) {
    setLoading(true);
    try {
      const resp = await fetch(`${API}/api/v1/repos?per_page=50`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      const data = await resp.json();
      setRepos(data.repos || []);
    } catch { setError("Failed to load repositories."); }
    setLoading(false);
  }

  function selectRepo(fullName: string) {
    localStorage.setItem("ai_pr_repo", fullName);
    navigate("/review-queue");
  }

  function logout() {
    localStorage.removeItem("ai_pr_token");
    localStorage.removeItem("ai_pr_repo");
    setUser(null); setRepos([]);
  }

  async function handleGitHubLogin() {
    setError(""); setLoading(true);
    try {
      const r = await fetch(`${API}/api/v1/auth/login`);
      const d = await r.json();
      if (d.url) window.location.href = d.url;
      else setError(d.message || "GitHub OAuth not configured.");
    } catch { setError("Cannot reach API server."); }
    setLoading(false);
  }

  // Step 1: Not logged in → show login
  if (!user) {
    return (
      <div style={{ maxWidth: 480, margin: "80px auto", padding: 32, textAlign: "center" }}>
        <h1 style={{ fontSize: 28, fontWeight: 700, marginBottom: 8 }}>AI PR Reviewer</h1>
        <p style={{ color: "#6b7280", marginBottom: 32 }}>AI-driven code review for your pull requests.</p>
        {error && <div style={{ padding: 12, background: "#fee2e2", color: "#dc2626", borderRadius: 8, marginBottom: 16 }}>{error}</div>}
        <button onClick={handleGitHubLogin} disabled={loading}
          style={{ width: "100%", padding: 14, fontSize: 16, fontWeight: 600, borderRadius: 8, border: "none",
            cursor: loading ? "default" : "pointer", background: "#24292f", color: "#fff", marginBottom: 24 }}>
          {loading ? "Connecting..." : "Sign in with GitHub"}
        </button>
        <div style={{ color: "#9ca3af", marginBottom: 24, fontSize: 14 }}>
          Sign in with your GitHub account.<br />An account will be created automatically on first sign-in.
        </div>
        <div style={{ borderTop: "1px solid #e5e7eb", paddingTop: 24, marginTop: 24 }}>
          <p style={{ fontSize: 13, color: "#9ca3af", marginBottom: 12 }}>Other methods coming soon:</p>
          <div style={{ display: "flex", gap: 12, justifyContent: "center" }}>
            <button disabled style={{ padding: "10px 24px", borderRadius: 8, border: "1px solid #e5e7eb", background: "#f9fafb", color: "#9ca3af", fontSize: 14, cursor: "not-allowed" }}>Email</button>
            <button disabled style={{ padding: "10px 24px", borderRadius: 8, border: "1px solid #e5e7eb", background: "#f9fafb", color: "#9ca3af", fontSize: 14, cursor: "not-allowed" }}>Phone</button>
          </div>
        </div>
      </div>
    );
  }

  // Step 2: Logged in → show repo selection
  const filtered = repoFilter
    ? repos.filter(r => r.full_name.toLowerCase().includes(repoFilter.toLowerCase()))
    : repos;

  return (
    <div style={{ maxWidth: 1000, margin: "0 auto", padding: 24 }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 24 }}>
        <div>
          <h1 style={{ fontSize: 28, fontWeight: 700 }}>Select Repository</h1>
          <p style={{ color: "#6b7280" }}>Connected as <strong>{user.login}</strong></p>
        </div>
        <button onClick={logout} style={{ padding: "8px 16px", borderRadius: 6, border: "1px solid #d1d5db", cursor: "pointer", background: "#fff" }}>Disconnect</button>
      </div>
      <input type="text" value={repoFilter} onChange={e => setRepoFilter(e.target.value)}
        placeholder="Filter repositories..." style={{ width: "100%", padding: "10px 16px", fontSize: 14, borderRadius: 8, border: "1px solid #d1d5db", marginBottom: 16, boxSizing: "border-box" }} />
      {loading ? <p style={{ color: "#9ca3af", textAlign: "center", padding: 40 }}>Loading repositories...</p>
       : filtered.length === 0 ? <p style={{ color: "#9ca3af", textAlign: "center", padding: 40 }}>No repositories found.</p>
       : <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 12 }}>
          {filtered.map((r: any) => (
            <div key={r.full_name} onClick={() => selectRepo(r.full_name)}
              style={{ padding: 16, borderRadius: 8, border: "1px solid #e5e7eb", cursor: "pointer", background: "#fff" }}>
              <div style={{ fontWeight: 600, marginBottom: 4 }}>{r.full_name}</div>
              <div style={{ fontSize: 12, color: "#6b7280" }}>
                {r.private ? "Private" : "Public"}{r.language ? ` · ${r.language}` : ""}{r.open_issues_count > 0 ? ` · ${r.open_issues_count} issues` : ""}
              </div>
            </div>
          ))}
        </div>
      }
    </div>
  );
}
