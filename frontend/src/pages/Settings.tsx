import { useState } from "react";
import { useNavigate } from "react-router-dom";

const API = "http://localhost:8000";

export default function Settings() {
  const navigate = useNavigate();
  const [confidence, setConfidence] = useState(65);
  const [maxComments, setMaxComments] = useState(10);
  const [mode, setMode] = useState("balanced");
  const [ghToken, setGhToken] = useState("");
  const [ghTokenSaved, setGhTokenSaved] = useState(false);
  const [llmSaved, setLlmSaved] = useState(false);

  function saveGhToken() {
    if (!ghToken.trim()) return;
    fetch(`${API}/api/v1/auth/token?token=${encodeURIComponent(ghToken)}`, { method: "POST" })
      .then(r => r.json())
      .then(d => {
        if (d.access_token) {
          localStorage.setItem("ai_pr_token", d.access_token);
          setGhTokenSaved(true);
          setTimeout(() => setGhTokenSaved(false), 2000);
        }
      });
  }

  function logout() {
    localStorage.removeItem("ai_pr_token");
    localStorage.removeItem("ai_pr_repo");
    navigate("/connect");
  }

  return (
    <div style={{ maxWidth: 800, margin: "0 auto", padding: 24 }}>
      <h1 style={{ fontSize: 28, fontWeight: 700, marginBottom: 24 }}>Settings</h1>

      <section style={{ marginBottom: 32 }}>
        <h2 style={{ fontSize: 20, marginBottom: 16 }}>GitHub Connection</h2>
        <p style={{ fontSize: 14, color: "#6b7280", marginBottom: 12 }}>
          Configure a GitHub Personal Access Token for API access. This is stored securely and used when reviewing PRs.
        </p>
        <div style={{ display: "flex", gap: 8, marginBottom: 8 }}>
          <input type="password" value={ghToken} onChange={e => setGhToken(e.target.value)}
            placeholder="ghp_... (repo scope required)"
            style={{ flex: 1, padding: "8px 12px", borderRadius: 6, border: "1px solid #d1d5db", fontSize: 14 }} />
          <button onClick={saveGhToken}
            style={{ padding: "8px 16px", borderRadius: 6, border: "none", background: ghToken ? "#2563eb" : "#d1d5db", color: "#fff", cursor: ghToken ? "pointer" : "default", fontSize: 14 }}>
            {ghTokenSaved ? "Saved ✓" : "Save"}
          </button>
        </div>
        <p style={{ fontSize: 12, color: "#9ca3af" }}>
          GitHub Settings → Developer settings → Tokens (classic) → Select scopes: repo
        </p>
      </section>

      <section style={{ marginBottom: 32 }}>
        <h2 style={{ fontSize: 20, marginBottom: 16 }}>Review Rules</h2>
        <div style={{ marginBottom: 16 }}>
          <label style={{ display: "block", marginBottom: 4, fontWeight: 600 }}>Min Confidence: {confidence}%</label>
          <input type="range" min={0} max={100} value={confidence} onChange={e => { const v = Number(e.target.value); setConfidence(v); localStorage.setItem("ai_pr_min_confidence", String(v)); }} style={{ width: "100%" }} />
        </div>
        <div style={{ marginBottom: 16 }}>
          <label style={{ display: "block", marginBottom: 4, fontWeight: 600 }}>Max Inline Comments: {maxComments}</label>
          <input type="range" min={0} max={30} value={maxComments} onChange={e => { const v = Number(e.target.value); setMaxComments(v); localStorage.setItem("ai_pr_max_comments", String(v)); }} style={{ width: "100%" }} />
        </div>
        <div style={{ marginBottom: 16 }}>
          <label style={{ display: "block", marginBottom: 4, fontWeight: 600 }}>Review Mode</label>
          <select value={mode} onChange={e => { setMode(e.target.value); localStorage.setItem("ai_pr_mode", e.target.value); }} style={{ padding: "8px 12px", borderRadius: 6, border: "1px solid #d1d5db", width: "100%" }}>
            <option value="fast">Fast</option><option value="balanced">Balanced</option><option value="deep">Deep</option>
          </select>
        </div>
      </section>

      <section style={{ marginBottom: 32 }}>
        <h2 style={{ fontSize: 20, marginBottom: 16 }}>LLM Configuration</h2>
        <p style={{ fontSize: 14, color: "#6b7280", marginBottom: 12 }}>
          Configure the AI model used for code review. Saved to your browser — takes effect on next review.
        </p>
        <div style={{ display: "flex", gap: 8, marginBottom: 8 }}>
          <select id="llmProvider" defaultValue={localStorage.getItem("ai_pr_llm_provider") || "deepseek"}
            style={{ padding: "8px 12px", borderRadius: 6, border: "1px solid #d1d5db", fontSize: 14 }}>
            <option value="deepseek">DeepSeek (Recommended)</option>
            <option value="anthropic">Anthropic Claude</option>
            <option value="openai">OpenAI GPT-4o</option>
            <option value="mock">Mock (no API key)</option>
          </select>
          <input id="llmKey" type="password" defaultValue={localStorage.getItem("ai_pr_llm_key") || ""}
            placeholder="API Key" style={{ flex: 1, padding: "8px 12px", borderRadius: 6, border: "1px solid #d1d5db", fontSize: 14 }} />
          <button onClick={() => {
            const p = (document.getElementById("llmProvider") as HTMLSelectElement).value;
            const k = (document.getElementById("llmKey") as HTMLInputElement).value;
            localStorage.setItem("ai_pr_llm_provider", p);
            localStorage.setItem("ai_pr_llm_key", k);
            setLlmSaved(true); setTimeout(() => setLlmSaved(false), 2000);
          }}
            style={{ padding: "8px 14px", borderRadius: 6, border: "none", background: llmSaved ? "#16a34a" : "#2563eb", color: "#fff", cursor: "pointer", fontSize: 13, whiteSpace: "nowrap" }}>
            {llmSaved ? "Saved ✓" : "Save"}
          </button>
        </div>
      </section>

      <section style={{ marginBottom: 32 }}>
        <h2 style={{ fontSize: 20, marginBottom: 16 }}>Integrations</h2>
        <div style={{ padding: 12, border: "1px solid #e5e7eb", borderRadius: 8, marginBottom: 8 }}>
          <strong>GitHub App:</strong> <span style={{ color: "#16a34a" }}>Connected</span>
        </div>
        <div style={{ padding: 12, border: "1px solid #e5e7eb", borderRadius: 8 }}>
          <strong>Slack:</strong> <span style={{ color: "#9ca3af" }}>Not configured</span>
        </div>
      </section>

      <section style={{ marginBottom: 32 }}>
        <h2 style={{ fontSize: 20, marginBottom: 16 }}>Webhook</h2>
        <p style={{ fontSize: 14, color: "#6b7280", marginBottom: 12 }}>
          Add this URL to your GitHub repo webhook settings for automatic PR review on push.
        </p>
        <div style={{ padding: 10, background: "#f9fafb", borderRadius: 6, fontFamily: "monospace", fontSize: 12, marginBottom: 8 }}>
          https://your-domain.com/api/webhook
        </div>
        <input type="password" placeholder="Webhook Secret (optional)" style={{ width: "100%", padding: "8px 12px", borderRadius: 6, border: "1px solid #d1d5db", fontSize: 14 }} />
      </section>

      <section>
        <h2 style={{ fontSize: 20, marginBottom: 16, color: "#dc2626" }}>Danger Zone</h2>
        <button onClick={logout}
          style={{ padding: "10px 20px", borderRadius: 8, border: "1px solid #dc2626", background: "#fff", color: "#dc2626", cursor: "pointer", fontSize: 14, fontWeight: 600 }}>
          Sign Out
        </button>
      </section>
    </div>
  );
}
