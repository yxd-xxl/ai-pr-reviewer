import { useState, useEffect } from "react";
import { useParams, useNavigate } from "react-router-dom";
import DiffViewer from "../components/DiffViewer";
import FindingInspector from "../components/FindingInspector";
import FileTree from "../components/FileTree";
import type { Finding } from "../types";

const API = "http://localhost:8000";

function getToken() { return localStorage.getItem("ai_pr_token") || ""; }

// Cache PR list filter state so returning doesn't reset
function getCachedFilter() { return sessionStorage.getItem("pr_filter") || "open"; }
function setCachedFilter(v: string) { sessionStorage.setItem("pr_filter", v); }

export default function ReviewWorkspace() {
  const { owner, repo, number } = useParams();
  const navigate = useNavigate();
  const token = getToken();
  const prUrl = `https://github.com/${owner}/${repo}/pull/${number}`;

  const [findings, setFindings] = useState<Finding[]>([]);
  const [summary, setSummary] = useState("");
  const [riskScore, setRiskScore] = useState(0);
  const [riskLevel, setRiskLevel] = useState("");
  const [timing, setTiming] = useState<Record<string, number>>({});
  const [selectedFinding, setSelectedFinding] = useState<Finding | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [filesCount, setFilesCount] = useState(0);
  const [categories, setCategories] = useState("all");
  const [mode, setMode] = useState("balanced");

  async function runAnalysis() {
    setLoading(true); setError(""); setFindings([]);
    try {
      const resp = await fetch(`${API}/api/v1/review`, {
        method: "POST",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
        body: JSON.stringify({ pr_url: prUrl, categories, mode }),
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
    } catch { setError("Cannot reach API server."); }
    setLoading(false);
  }

  function handleFeedback(fp: string, state: string) {
    fetch(`${API}/api/v1/feedback`, {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ fingerprint: fp, state, reason: "" }),
    }).catch(() => {});
  }

  function downloadJSON() {
    const blob = new Blob([JSON.stringify({ findings, summary, risk_score: riskScore }, null, 2)], { type: "application/json" });
    const a = document.createElement("a"); a.href = URL.createObjectURL(blob);
    a.download = `pr-${number}-review.json`; a.click();
  }

  const fileNodes = findings.reduce((acc, f) => {
    const path = f.location.file;
    let node = acc.find(n => n.path === path);
    if (!node) { node = { path, findings: [], critical: 0, high: 0, medium: 0, low: 0 }; acc.push(node); }
    node.findings.push(f);
    if (f.severity === "critical") node.critical++; else if (f.severity === "high") node.high++;
    else if (f.severity === "medium") node.medium++; else node.low++;
    return acc;
  }, [] as { path: string; findings: Finding[]; critical: number; high: number; medium: number; low: number }[]);

  const sevCounts = { critical: 0, high: 0, medium: 0, low: 0 };
  findings.forEach(f => { if (f.severity in sevCounts) sevCounts[f.severity as keyof typeof sevCounts]++; });

  return (
    <div style={{ display: "flex", height: "calc(100vh - 44px)" }}>
      {/* Left sidebar — config + file tree */}
      <aside style={{ width: 260, borderRight: "1px solid #e5e7eb", overflow: "auto", display: "flex", flexDirection: "column" }}>
        <div style={{ padding: 12 }}>
          <button onClick={() => navigate("/review-queue")}
            style={{ background: "none", border: "none", color: "#2563eb", cursor: "pointer", fontSize: 13, padding: 0, marginBottom: 8 }}>
            ← Back to Review Queue
          </button>
          <h3 style={{ margin: "0 0 4px", fontSize: 15 }}>{owner}/{repo}#{number}</h3>
          <a href={prUrl} target="_blank" style={{ fontSize: 11, color: "#6b7280" }}>{prUrl}</a>

          {/* Config */}
          <div style={{ marginTop: 12, display: "flex", flexDirection: "column", gap: 6 }}>
            <select value={categories} onChange={e => setCategories(e.target.value)}
              style={{ padding: "4px 8px", borderRadius: 4, border: "1px solid #d1d5db", fontSize: 12 }}>
              <option value="all">All Categories</option>
              <option value="security">Security Only</option>
              <option value="bug">Bug Only</option>
              <option value="security,bug">Security + Bug</option>
              <option value="security,bug,performance,style,architecture,failure">All (6 Analyzers)</option>
            </select>
            <select value={mode} onChange={e => setMode(e.target.value)}
              style={{ padding: "4px 8px", borderRadius: 4, border: "1px solid #d1d5db", fontSize: 12 }}>
              <option value="fast">Fast</option>
              <option value="balanced">Balanced</option>
              <option value="deep">Deep</option>
            </select>
          </div>

          <button onClick={runAnalysis} disabled={loading}
            style={{ width: "100%", marginTop: 8, padding: "10px", borderRadius: 8, border: "none",
              background: loading ? "#d1d5db" : "#2563eb", color: "#fff",
              cursor: loading ? "default" : "pointer", fontSize: 14, fontWeight: 600 }}>
            {loading ? `Analyzing... (${Object.values(timing)[0] || "?"}s)` : "Run Analysis"}
          </button>

          {/* Metrics */}
          {findings.length > 0 && (
            <div style={{ marginTop: 12 }}>
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 4 }}>
                <div style={{ padding: 4, background: "#f3f4f6", borderRadius: 4, textAlign: "center", fontSize: 11 }}>
                  <div style={{ fontWeight: 700 }}>{filesCount}</div><div>Files</div></div>
                <div style={{ padding: 4, background: "#f3f4f6", borderRadius: 4, textAlign: "center", fontSize: 11 }}>
                  <div style={{ fontWeight: 700 }}>{findings.length}</div><div>Findings</div></div>
                <div style={{ padding: 4, background: sevCounts.critical > 0 ? "#fee2e2" : "#f3f4f6", borderRadius: 4, textAlign: "center", fontSize: 11 }}>
                  <div style={{ fontWeight: 700, color: sevCounts.critical > 0 ? "#dc2626" : "#374151" }}>{sevCounts.critical}</div><div>Critical</div></div>
                <div style={{ padding: 4, background: sevCounts.high > 0 ? "#ffedd5" : "#f3f4f6", borderRadius: 4, textAlign: "center", fontSize: 11 }}>
                  <div style={{ fontWeight: 700, color: sevCounts.high > 0 ? "#ea580c" : "#374151" }}>{sevCounts.high}</div><div>High</div></div>
              </div>
              {riskLevel && (
                <div style={{ marginTop: 8, padding: 6, borderRadius: 6, fontSize: 12, textAlign: "center",
                  background: riskLevel === "critical" ? "#fee2e2" : riskLevel === "high" ? "#ffedd5" : riskLevel === "medium" ? "#fef3c7" : "#dcfce7",
                  color: riskLevel === "critical" ? "#dc2626" : riskLevel === "high" ? "#ea580c" : riskLevel === "medium" ? "#ca8a04" : "#16a34a" }}>
                  Risk: {riskScore}/100 ({riskLevel})
                </div>
              )}
              <button onClick={downloadJSON}
                style={{ width: "100%", marginTop: 8, padding: "6px", borderRadius: 6, border: "1px solid #d1d5db", background: "#fff", cursor: "pointer", fontSize: 12 }}>
                Download Report (JSON)
              </button>
              <button onClick={async () => {
                const r = await fetch(`${API}/api/v1/post-comments?pr_url=${encodeURIComponent(prUrl)}&dry_run=false`, { method: "POST", headers: { Authorization: `Bearer ${token}` } });
                const d = await r.json();
                alert(d.status === "ok" ? `Posted ${d.findings_count} findings as inline comments.` : `Failed: ${d.message}`);
              }}
                style={{ width: "100%", marginTop: 4, padding: "6px", borderRadius: 6, border: "1px solid #16a34a", background: "#fff", color: "#16a34a", cursor: "pointer", fontSize: 12 }}>
                Post Comments to PR
              </button>
            </div>
          )}

          {/* Timing */}
          {Object.keys(timing).length > 0 && (
            <div style={{ marginTop: 8, fontSize: 10, color: "#9ca3af" }}>
              Fetch: {timing.fetch}s | Analyze: {timing.analyze}s | Total: {timing.total}s
            </div>
          )}
        </div>

        {/* File tree */}
        <div style={{ flex: 1, overflow: "auto" }}>
          <FileTree files={fileNodes} selectedFile={selectedFinding?.location.file || null} onSelect={() => {}} />
        </div>
      </aside>

      {/* Center — summary + findings list */}
      <main style={{ flex: 1, overflow: "auto", padding: 16 }}>
        {error && <div style={{ padding: 12, background: "#fee2e2", color: "#dc2626", borderRadius: 8, marginBottom: 16 }}>{error}</div>}
        {!loading && findings.length === 0 && !error && (
          <div style={{ textAlign: "center", padding: 80, color: "#9ca3af" }}>
            <h2>AI PR Reviewer</h2>
            <p>Select categories and mode in the sidebar, then click "Run Analysis".</p>
            <p style={{ fontSize: 13 }}>SAST (Bandit/ESLint/staticcheck/Semgrep) + LLM analysis with 6 independent analyzers.</p>
          </div>
        )}
        {summary && <div style={{ marginBottom: 16, padding: 12, background: "#f9fafb", borderRadius: 8, fontSize: 14, lineHeight: 1.6, whiteSpace: "pre-wrap" }}>{summary}</div>}
        {findings.map((f, i) => (
          <div key={i} onClick={() => setSelectedFinding(f)}
            style={{ padding: 10, marginBottom: 4, borderRadius: 6, cursor: "pointer",
              background: selectedFinding === f ? "#dbeafe" : "#fff",
              border: `1px solid ${selectedFinding === f ? "#2563eb" : "#e5e7eb"}` }}>
            <span style={{ color: {critical:"#dc2626",high:"#ea580c",medium:"#ca8a04",low:"#2563eb"}[f.severity]||"#6b7280", fontWeight: 600, fontSize: 12 }}>
              [{f.severity.toUpperCase()}]
            </span>
            <span style={{ fontSize: 12, color: "#6b7280", marginLeft: 8 }}>{f.category}</span>
            <span style={{ marginLeft: 8, fontSize: 14 }}>{f.title}</span>
            <span style={{ float: "right", fontSize: 11, color: "#9ca3af" }}>{f.location.file}:{f.location.line}</span>
          </div>
        ))}
        {findings.length > 0 && <p style={{ fontSize: 12, color: "#9ca3af", marginTop: 8 }}>Click a finding to see details in the right panel.</p>}
      </main>

      {/* Right — Finding Inspector */}
      <aside style={{ width: 400, borderLeft: "1px solid #e5e7eb" }}>
        <FindingInspector finding={selectedFinding}
          onFeedback={handleFeedback}
          onAskFollowup={() => {}} />
      </aside>
    </div>
  );
}
