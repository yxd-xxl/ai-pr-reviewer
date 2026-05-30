import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";

const API = "http://localhost:8000";

interface Repo {
  full_name: string;
  private: boolean;
  language: string | null;
  open_issues_count: number;
  description: string | null;
}

export default function Connect() {
  const navigate = useNavigate();
  const [token, setToken] = useState(localStorage.getItem("ai_pr_token") || "");
  const [user, setUser] = useState<{ login: string } | null>(null);
  const [repos, setRepos] = useState<Repo[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [repoFilter, setRepoFilter] = useState("");

  // Check token on mount
  useEffect(() => {
    if (token) fetchUser();
  }, []);

  async function fetchUser() {
    setError("");
    setLoading(true);
    try {
      const resp = await fetch(`${API}/api/v1/auth/me`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (resp.ok) {
        const data = await resp.json();
        setUser(data);
        localStorage.setItem("ai_pr_token", token);
        fetchRepos();
      } else {
        localStorage.removeItem("ai_pr_token");
        setError("Invalid token (HTTP " + resp.status + "). Check your GitHub token and try again.");
      }
    } catch {
      setError("Cannot reach API server at " + API + ". Start backend: python -m uvicorn backend.main:app --port 8000");
    }
    setLoading(false);
  }

  async function fetchRepos() {
    setLoading(true);
    try {
      const resp = await fetch(`${API}/api/v1/repos?per_page=50`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      const data = await resp.json();
      setRepos(data.repos || []);
    } catch {
      setError("Failed to load repositories.");
    }
    setLoading(false);
  }

  function selectRepo(fullName: string) {
    localStorage.setItem("ai_pr_repo", fullName);
    navigate("/review-queue");
  }

  function disconnect() {
    localStorage.removeItem("ai_pr_token");
    localStorage.removeItem("ai_pr_repo");
    setToken(""); setUser(null); setRepos([]);
  }

  // Step 1: Token input
  if (!user) {
    return (
      <div style={{ maxWidth: 480, margin: "80px auto", padding: 32, textAlign: "center" }}>
        <h1 style={{ fontSize: 28, fontWeight: 700, marginBottom: 8 }}>AI PR Reviewer</h1>
        <p style={{ color: "#6b7280", marginBottom: 32 }}>
          Connect your GitHub account to start reviewing PRs.
        </p>

        {error && (
          <div style={{ padding: 12, background: "#fee2e2", color: "#dc2626", borderRadius: 8, marginBottom: 16 }}>
            {error}
          </div>
        )}

        <div style={{ marginBottom: 24 }}>
          <input
            type="password"
            value={token}
            onChange={(e) => { setToken(e.target.value); setError(""); }}
            onKeyDown={(e) => e.key === "Enter" && fetchUser()}
            placeholder="GitHub Personal Access Token (ghp_...)"
            style={{
              width: "100%", padding: "12px 16px", fontSize: 14,
              borderRadius: 8, border: "1px solid #d1d5db",
              boxSizing: "border-box",
            }}
          />
          <p style={{ fontSize: 12, color: "#9ca3af", marginTop: 8 }}>
            GitHub Settings → Developer settings → Tokens (classic) → repo scope
          </p>
        </div>

        <button
          onClick={fetchUser}
          disabled={!token}
          style={{
            width: "100%", padding: "12px", fontSize: 16, fontWeight: 600,
            borderRadius: 8, border: "none", cursor: token ? "pointer" : "default",
            background: token ? "#2563eb" : "#d1d5db", color: "#fff",
          }}
        >
          Connect with Token
        </button>

        <div style={{ margin: "24px 0", color: "#9ca3af" }}>or</div>

        <button
          onClick={async () => {
            try {
              const r = await fetch(`${API}/api/v1/auth/login`);
              const d = await r.json();
              if (d.url) window.location.href = d.url;
              else setError(d.message || "GitHub OAuth not configured. Use a personal token above.");
            } catch {
              setError("Cannot reach API server at " + API + ". Make sure backend is running.");
            }
          }}
          style={{
            width: "100%", padding: "12px", fontSize: 16, fontWeight: 600,
            borderRadius: 8, border: "1px solid #d1d5db", cursor: "pointer",
            background: "#24292f", color: "#fff",
          }}
        >
          Sign in with GitHub
        </button>
      </div>
    );
  }

  // Step 2: Repo selection
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
        <button onClick={disconnect}
          style={{ padding: "8px 16px", borderRadius: 6, border: "1px solid #d1d5db", cursor: "pointer", background: "#fff" }}>
          Disconnect
        </button>
      </div>

      <input
        type="text"
        value={repoFilter}
        onChange={(e) => setRepoFilter(e.target.value)}
        placeholder="Filter repositories..."
        style={{
          width: "100%", padding: "10px 16px", fontSize: 14,
          borderRadius: 8, border: "1px solid #d1d5db",
          marginBottom: 16, boxSizing: "border-box",
        }}
      />

      {loading ? (
        <p style={{ color: "#9ca3af", textAlign: "center", padding: 40 }}>Loading repositories...</p>
      ) : filtered.length === 0 ? (
        <p style={{ color: "#9ca3af", textAlign: "center", padding: 40 }}>No repositories found.</p>
      ) : (
        <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 12 }}>
          {filtered.map((r) => (
            <div
              key={r.full_name}
              onClick={() => selectRepo(r.full_name)}
              style={{
                padding: 16, borderRadius: 8,
                border: "1px solid #e5e7eb", cursor: "pointer",
                background: "#fff",
              }}
            >
              <div style={{ fontWeight: 600, marginBottom: 4 }}>{r.full_name}</div>
              <div style={{ fontSize: 12, color: "#6b7280" }}>
                {r.private ? "🔒 Private" : "🌐 Public"}
                {r.language ? ` · ${r.language}` : ""}
                {r.open_issues_count > 0 ? ` · ${r.open_issues_count} issues` : ""}
              </div>
              {r.description && (
                <div style={{ fontSize: 13, color: "#374151", marginTop: 8 }}>{r.description}</div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
