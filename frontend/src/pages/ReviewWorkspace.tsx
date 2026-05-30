import { useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import DiffViewer from "../components/DiffViewer";
import FindingInspector from "../components/FindingInspector";
import FileTree from "../components/FileTree";
import type { Finding } from "../types";

const API = "http://localhost:8000";

function getToken() { return localStorage.getItem("ai_pr_token") || ""; }

export default function ReviewWorkspace() {
  const { owner, repo, number } = useParams();
  const navigate = useNavigate();
  const token = getToken();

  const [findings, setFindings] = useState<Finding[]>([]);
  const [summary, setSummary] = useState("");
  const [riskScore, setRiskScore] = useState(0);
  const [riskLevel, setRiskLevel] = useState("");
  const [timing, setTiming] = useState<Record<string, number>>({});
  const [selectedFinding, setSelectedFinding] = useState<Finding | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [filesCount, setFilesCount] = useState(0);

  const prUrl = `https://github.com/${owner}/${repo}/pull/${number}`;

  async function runAnalysis() {
    setLoading(true); setError(""); setFindings([]);
    try {
      const resp = await fetch(`${API}/api/v1/review`, {
        method: "POST",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
        body: JSON.stringify({ pr_url: prUrl, categories: "all", mode: "balanced" }),
      });
      const data = await resp.json();
      if (data.status === "ok") {
        setFindings(data.findings || []);
        setSummary(data.summary || "");
        setRiskScore(data.risk_score || 0);
        setRiskLevel(data.risk_level || "low");
        setFilesCount(data.files_count || 0);
        setTiming(data.timing || {});
        if (data.findings?.length > 0) setSelectedFinding(data.findings[0]);
      } else {
        setError(data.detail || "Analysis failed");
      }
    } catch {
      setError("Cannot reach API server at " + API);
    }
    setLoading(false);
  }

  function handleFeedback(fp: string, state: string) {
    fetch(`${API}/api/v1/feedback`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ fingerprint: fp, state, reason: "" }),
    }).catch(() => {});
  }

  const fileNodes = findings.reduce((acc, f) => {
    const path = f.location.file;
    let node = acc.find(n => n.path === path);
    if (!node) { node = { path, findings: [], critical: 0, high: 0, medium: 0, low: 0 }; acc.push(node); }
    node.findings.push(f);
    if (f.severity === "critical") node.critical++;
    else if (f.severity === "high") node.high++;
    else if (f.severity === "medium") node.medium++;
    else node.low++;
    return acc;
  }, [] as { path: string; findings: Finding[]; critical: number; high: number; medium: number; low: number }[]);

  const sevCounts = { critical: 0, high: 0, medium: 0, low: 0 };
  findings.forEach(f => { if (f.severity in sevCounts) sevCounts[f.severity as keyof typeof sevCounts]++; });

  return (
    <div style={{ display: "flex", height: "calc(100vh - 44px)" }}>
      <aside style={{ width: 260, borderRight: "1px solid #e5e7eb", overflow: "auto" }}>
        <div style={{ padding: 12 }}>
          <h3 style={{ margin: 0, fontSize: 16 }}>{owner}/{repo}#{number}</h3>
          <p style={{ fontSize: 12, color: "#6b7280", margin: "4px 0 12px" }}>{prUrl}</p>
          <button onClick={runAnalysis} disabled={loading}
            style={{ width: "100%", padding: "10px", borderRadius: 8, border: "none",
              background: loading ? "#d1d5db" : "#2563eb", color: "#fff",
              cursor: loading ? "default" : "pointer", fontSize: 14, fontWeight: 600 }}>
            {loading ? "Analyzing..." : "Run Analysis"}
          </button>
          {findings.length > 0 && (
            <div style={{ marginTop: 12 }}>
              <div style={{ fontSize: 13, color: "#6b7280", marginBottom: 4 }}>Results</div>
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 4 }}>
                <div style={{ padding: 4, background: "#f3f4f6", borderRadius: 4, textAlign: "center", fontSize: 12 }}>
                  <div style={{ fontWeight: 700 }}>{filesCount}</div><div>Files</div></div>
                <div style={{ padding: 4, background: "#f3f4f6", borderRadius: 4, textAlign: "center", fontSize: 12 }}>
                  <div style={{ fontWeight: 700 }}>{findings.length}</div><div>Findings</div></div>
                <div style={{ padding: 4, background: sevCounts.critical > 0 ? "#fee2e2" : "#f3f4f6", borderRadius: 4, textAlign: "center", fontSize: 12 }}>
                  <div style={{ fontWeight: 700, color: sevCounts.critical > 0 ? "#dc2626" : "#374151" }}>{sevCounts.critical}</div><div>Critical</div></div>
                <div style={{ padding: 4, background: sevCounts.high > 0 ? "#ffedd5" : "#f3f4f6", borderRadius: 4, textAlign: "center", fontSize: 12 }}>
                  <div style={{ fontWeight: 700, color: sevCounts.high > 0 ? "#ea580c" : "#374151" }}>{sevCounts.high}</div><div>High</div></div>
              </div>
            </div>
          )}
          {riskLevel && (
            <div style={{ marginTop: 8, padding: 8, borderRadius: 6, fontSize: 13, textAlign: "center",
              background: riskLevel === "critical" ? "#fee2e2" : riskLevel === "high" ? "#ffedd5" : riskLevel === "medium" ? "#fef3c7" : "#dcfce7",
              color: riskLevel === "critical" ? "#dc2626" : riskLevel === "high" ? "#ea580c" : riskLevel === "medium" ? "#ca8a04" : "#16a34a" }}>
              Risk: {riskScore}/100 ({riskLevel})
            </div>
          )}
        </div>
        <FileTree files={fileNodes} selectedFile={selectedFinding?.location.file || null}
          onSelect={() => {}} />
      </aside>

      <main style={{ flex: 1, overflow: "auto", padding: 16 }}>
        {error && <div style={{ padding: 12, background: "#fee2e2", color: "#dc2626", borderRadius: 8, marginBottom: 16 }}>{error}</div>}
        {loading && <p style={{ color: "#9ca3af", textAlign: "center", padding: 40 }}>Running AI analysis with DeepSeek... (fetch={timing.fetch || "?"}s analyze={timing.analyze || "?"}s)</p>}
        {!loading && findings.length === 0 && !error && (
          <div style={{ textAlign: "center", padding: 80, color: "#9ca3af" }}>
            <h2>AI PR Reviewer</h2>
            <p>Click "Run Analysis" in the sidebar to start reviewing this PR.</p>
            <p style={{ fontSize: 13 }}>The analysis uses SAST (Bandit/ESLint/staticcheck/Semgrep) + LLM to detect security issues, bugs, performance problems, and more.</p>
          </div>
        )}
        {findings.length > 0 && (
          <div>
            {summary && <div style={{ marginBottom: 16, padding: 12, background: "#f9fafb", borderRadius: 8, fontSize: 14, lineHeight: 1.6 }}>{summary}</div>}
            <div style={{ display: "flex", gap: 8, marginBottom: 16 }}>
              <button onClick={() => { const blob = new Blob([JSON.stringify({findings, summary}, null, 2)], {type:"application/json"}); const a=document.createElement("a"); a.href=URL.createObjectURL(blob); a.download=`pr-${number}-review.json`; a.click(); }}
                style={{ padding:"4px 12px", borderRadius:6, border:"1px solid #d1d5db", background:"#fff", cursor:"pointer", fontSize:13 }}>Download SARIF</button>
            </div>
          </div>
        )}
      </main>

      <aside style={{ width: 400, borderLeft: "1px solid #e5e7eb" }}>
        <FindingInspector finding={selectedFinding}
          onFeedback={handleFeedback}
          onAskFollowup={(fp, q) => console.log("Follow-up:", fp, q)} />
      </aside>
    </div>
  );
}
