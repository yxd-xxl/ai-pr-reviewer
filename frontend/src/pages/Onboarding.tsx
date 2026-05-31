import { useState } from "react";
import { useNavigate } from "react-router-dom";

const API = "http://localhost:8000";

interface Step { title: string; description: string; configured: boolean; action: string; }

export default function Onboarding() {
  const navigate = useNavigate();
  const [step, setStep] = useState(0);
  const [ghToken, setGhToken] = useState("");
  const [ghDone, setGhDone] = useState(false);
  const [llmProvider, setLlmProvider] = useState("deepseek");
  const [llmKey, setLlmKey] = useState("");
  const [llmDone, setLlmDone] = useState(false);

  const steps: Step[] = [
    { title: "Welcome!", description: "Let's get you set up in 3 steps.", configured: true, action: "Next" },
    { title: "GitHub Token", description: "Connect your GitHub account so AI PR Reviewer can access your repos and post comments.", configured: ghDone, action: "Save & Continue" },
    { title: "AI Model", description: "Choose which AI model to use for code review. DeepSeek is recommended for best value.", configured: llmDone, action: "Save & Continue" },
    { title: "You're Ready!", description: "All configured. Start reviewing PRs!", configured: true, action: "Go to Dashboard" },
  ];

  function saveGhToken() {
    if (!ghToken.trim()) return;
    fetch(`${API}/api/v1/auth/token?token=${encodeURIComponent(ghToken)}`, { method: "POST" })
      .then(r => r.json()).then(d => {
        if (d.access_token) { localStorage.setItem("ai_pr_token", d.access_token); setGhDone(true); }
      });
  }

  function saveLlmConfig() {
    localStorage.setItem("ai_pr_llm_provider", llmProvider);
    if (llmKey) localStorage.setItem("ai_pr_llm_key", llmKey);
    // Persist to backend
    const token = localStorage.getItem("ai_pr_token") || "";
    if (token) {
      fetch(`${API}/api/v1/settings`, {
        method: "POST", headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
        body: JSON.stringify({ llm_provider: llmProvider, llm_api_key: llmKey }),
      }).catch(() => {});
    }
    setLlmDone(true);
  }

  function next() {
    if (step === 1 && !ghDone) { saveGhToken(); return; }
    if (step === 2 && !llmDone) { saveLlmConfig(); return; }
    if (step >= 3) { localStorage.removeItem("ai_pr_new_user"); navigate("/connect"); return; }
    setStep(step + 1);
  }

  function skip() { setStep(step + 1); }

  const s = steps[step];

  return (
    <div style={{ maxWidth: 520, margin: "80px auto", padding: 32 }}>
      <div style={{ display: "flex", gap: 8, marginBottom: 24 }}>
        {steps.map((_, i) => (
          <div key={i} style={{ flex: 1, height: 4, borderRadius: 2, background: i <= step ? "#2563eb" : "#e5e7eb" }} />
        ))}
      </div>
      <h2 style={{ fontSize: 22, fontWeight: 700, marginBottom: 8 }}>{s.title}</h2>
      <p style={{ color: "#6b7280", marginBottom: 24, fontSize: 14 }}>{s.description}</p>

      {step === 1 && (
        <div>
          <input type="password" value={ghToken} onChange={e => setGhToken(e.target.value)}
            placeholder="ghp_... (repo scope)" style={{ width: "100%", padding: "10px 14px", borderRadius: 6, border: "1px solid #d1d5db", fontSize: 14, marginBottom: 8, boxSizing: "border-box" }} />
          <p style={{ fontSize: 11, color: "#9ca3af", marginBottom: 16 }}>GitHub Settings → Developer settings → Tokens (classic) → Select scopes: repo. You can skip this and configure later in Settings.</p>
        </div>
      )}

      {step === 2 && (
        <div>
          <select value={llmProvider} onChange={e => setLlmProvider(e.target.value)}
            style={{ width: "100%", padding: "10px 14px", borderRadius: 6, border: "1px solid #d1d5db", fontSize: 14, marginBottom: 8 }}>
            <option value="deepseek">DeepSeek (Recommended)</option>
            <option value="anthropic">Anthropic Claude</option>
            <option value="openai">OpenAI GPT-4o</option>
            <option value="mock">Mock (no API key)</option>
          </select>
          {llmProvider !== "mock" && (
            <input type="password" value={llmKey} onChange={e => setLlmKey(e.target.value)}
              placeholder="API Key" style={{ width: "100%", padding: "10px 14px", borderRadius: 6, border: "1px solid #d1d5db", fontSize: 14, marginBottom: 8, boxSizing: "border-box" }} />
          )}
          <p style={{ fontSize: 11, color: "#9ca3af" }}>You can change this later in Settings.</p>
        </div>
      )}

      {step === 3 && (
        <div style={{ textAlign: "center", padding: 20, background: "#f0fdf4", borderRadius: 8 }}>
          <p style={{ fontSize: 40, margin: 0 }}>✅</p>
          <p style={{ fontSize: 14, color: "#16a34a", marginTop: 8 }}>All set! Your account is ready.</p>
        </div>
      )}

      <div style={{ display: "flex", gap: 12, marginTop: 20 }}>
        <button onClick={next}
          style={{ flex: 1, padding: 12, borderRadius: 8, border: "none", background: "#2563eb", color: "#fff", cursor: "pointer", fontSize: 14, fontWeight: 600 }}>
          {s.action}
        </button>
        {step >= 1 && step <= 2 && (
          <button onClick={skip}
            style={{ padding: "12px 20px", borderRadius: 8, border: "1px solid #d1d5db", background: "#fff", cursor: "pointer", fontSize: 14, color: "#6b7280" }}>
            Skip
          </button>
        )}
      </div>
    </div>
  );
}
