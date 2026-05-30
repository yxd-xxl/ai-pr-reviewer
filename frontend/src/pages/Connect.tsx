import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";

const API = "http://localhost:8000";

export default function Connect() {
  const navigate = useNavigate();
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  // Stay on repo selection unless BOTH logged in AND repo selected
  useEffect(() => {
    const token = localStorage.getItem("ai_pr_token");
    const repo = localStorage.getItem("ai_pr_repo");
    if (token && repo) {
      fetch(`${API}/api/v1/auth/me`, { headers: { Authorization: `Bearer ${token}` } })
        .then(r => { if (r.ok) navigate("/review-queue"); })
        .catch(() => {});
    }
    // Show OAuth error from failed callback
    const params = new URLSearchParams(window.location.search);
    const oauthErr = params.get("error");
    if (oauthErr) {
      setError("OAuth failed: " + decodeURIComponent(oauthErr));
      window.history.replaceState({}, "", "/connect");
    }
  }, []);

  async function handleGitHubLogin() {
    setError(""); setLoading(true);
    try {
      const r = await fetch(`${API}/api/v1/auth/login`);
      const d = await r.json();
      if (d.url) window.location.href = d.url;
      else setError(d.message || "GitHub OAuth not configured.");
    } catch {
      setError("Cannot reach API server. Make sure backend is running.");
    }
    setLoading(false);
  }

  return (
    <div style={{ maxWidth: 480, margin: "80px auto", padding: 32, textAlign: "center" }}>
      <h1 style={{ fontSize: 28, fontWeight: 700, marginBottom: 8 }}>AI PR Reviewer</h1>
      <p style={{ color: "#6b7280", marginBottom: 32 }}>
        AI-driven code review for your pull requests.
      </p>

      {error && (
        <div style={{ padding: 12, background: "#fee2e2", color: "#dc2626", borderRadius: 8, marginBottom: 16 }}>
          {error}
        </div>
      )}

      <button onClick={handleGitHubLogin} disabled={loading}
        style={{
          width: "100%", padding: 14, fontSize: 16, fontWeight: 600,
          borderRadius: 8, border: "none", cursor: loading ? "default" : "pointer",
          background: "#24292f", color: "#fff", marginBottom: 24,
        }}>
        {loading ? "Connecting..." : "Sign in with GitHub"}
      </button>

      <div style={{ color: "#9ca3af", marginBottom: 24, fontSize: 14 }}>
        Sign in with your GitHub account to get started.<br />
        An account will be created automatically on first sign-in.
      </div>

      <div style={{ borderTop: "1px solid #e5e7eb", paddingTop: 24, marginTop: 24 }}>
        <p style={{ fontSize: 13, color: "#9ca3af", marginBottom: 12 }}>
          Other sign-in methods coming soon:
        </p>
        <div style={{ display: "flex", gap: 12, justifyContent: "center" }}>
          <button disabled style={{ padding: "10px 24px", borderRadius: 8, border: "1px solid #e5e7eb", background: "#f9fafb", color: "#9ca3af", fontSize: 14, cursor: "not-allowed" }}>
            Email
          </button>
          <button disabled style={{ padding: "10px 24px", borderRadius: 8, border: "1px solid #e5e7eb", background: "#f9fafb", color: "#9ca3af", fontSize: 14, cursor: "not-allowed" }}>
            Phone
          </button>
        </div>
      </div>

      <p style={{ fontSize: 12, color: "#9ca3af", marginTop: 32 }}>
        By signing in, you agree to our Terms of Service.
      </p>
    </div>
  );
}
