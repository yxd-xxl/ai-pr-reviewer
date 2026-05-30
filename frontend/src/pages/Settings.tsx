import { useState } from "react";

export default function Settings() {
  const [confidence, setConfidence] = useState(65);
  const [maxComments, setMaxComments] = useState(10);
  const [mode, setMode] = useState("balanced");

  return (
    <div style={{ padding: 24, maxWidth: 800, margin: "0 auto" }}>
      <h1 style={{ fontSize: 28, fontWeight: 700, marginBottom: 24 }}>Settings</h1>

      <section style={{ marginBottom: 32 }}>
        <h2 style={{ fontSize: 20, marginBottom: 16 }}>Review Rules</h2>
        <div style={{ marginBottom: 16 }}>
          <label style={{ display: "block", marginBottom: 4, fontWeight: 600 }}>Min Confidence: {confidence}%</label>
          <input type="range" min={0} max={100} value={confidence}
            onChange={(e) => setConfidence(Number(e.target.value))}
            style={{ width: "100%" }} />
          <span style={{ fontSize: 12, color: "#6b7280" }}>Findings below this threshold are filtered out.</span>
        </div>

        <div style={{ marginBottom: 16 }}>
          <label style={{ display: "block", marginBottom: 4, fontWeight: 600 }}>Max Inline Comments: {maxComments}</label>
          <input type="range" min={0} max={30} value={maxComments}
            onChange={(e) => setMaxComments(Number(e.target.value))}
            style={{ width: "100%" }} />
        </div>

        <div style={{ marginBottom: 16 }}>
          <label style={{ display: "block", marginBottom: 4, fontWeight: 600 }}>Review Mode</label>
          <select value={mode} onChange={(e) => setMode(e.target.value)}
            style={{ padding: "8px 12px", borderRadius: 6, border: "1px solid #d1d5db", width: "100%" }}>
            <option value="fast">Fast (security + bug only, no verification)</option>
            <option value="balanced">Balanced (all categories, verify critical/high)</option>
            <option value="deep">Deep (all categories, verify all, generate fixes)</option>
          </select>
        </div>
      </section>

      <section style={{ marginBottom: 32 }}>
        <h2 style={{ fontSize: 20, marginBottom: 16 }}>Integrations</h2>
        <div style={{ padding: 12, border: "1px solid #e5e7eb", borderRadius: 8, marginBottom: 8 }}>
          <strong>GitHub App:</strong> {""}
          <span style={{ color: "#16a34a" }}>Connected</span>
          <p style={{ fontSize: 13, color: "#6b7280", margin: "4px 0 0" }}>
            Installation ID: 12345678. Repos: ai-pr-reviewer, api-server.
          </p>
        </div>
        <div style={{ padding: 12, border: "1px solid #e5e7eb", borderRadius: 8, marginBottom: 8 }}>
          <strong>Slack:</strong> {""}
          <span style={{ color: "#9ca3af" }}>Not configured</span>
          <p style={{ fontSize: 13, color: "#6b7280", margin: "4px 0 0" }}>
            Add a Slack webhook URL to receive high-risk PR alerts.
          </p>
        </div>
        <div style={{ padding: 12, border: "1px solid #e5e7eb", borderRadius: 8 }}>
          <strong>SARIF Upload:</strong> {""}
          <span style={{ color: "#16a34a" }}>Enabled</span>
          <p style={{ fontSize: 13, color: "#6b7280", margin: "4px 0 0" }}>
            SARIF results are automatically uploaded to GitHub Code Scanning.
          </p>
        </div>
      </section>
    </div>
  );
}
