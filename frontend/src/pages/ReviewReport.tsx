import { useState, useEffect } from "react";
import { useParams, useNavigate } from "react-router-dom";
import MarkdownRenderer from "../components/MarkdownRenderer";
import FindingInspector from "../components/FindingInspector";

const API = "http://localhost:8000";

export default function ReviewReport() {
  const { runId } = useParams();
  const navigate = useNavigate();
  const [review, setReview] = useState<any>(null);
  const [findings, setFindings] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [selected, setSelected] = useState<any>(null);

  useEffect(() => {
    // Fetch review by run ID from the history API
    fetch(`${API}/api/v1/reviews?limit=100`)
      .then(r => r.json()).then(d => {
        const rows = d.reviews || [];
        const match = rows.find((r: any) => String(r.id) === runId);
        if (match) {
          setReview(match);
          // Fetch findings for this run
          fetch(`${API}/api/v1/review/${match.id}`)
            .then(r => r.json()).then(fd => {
              const ff = (fd.findings || []).map((f: any) => ({
                ...f,
                location: f.location || { file: f.file || "", line: f.line },
              }));
              setFindings(ff);
              if (ff.length > 0) setSelected(ff[0]);
            }).catch(() => {});
        }
        setLoading(false);
      }).catch(() => setLoading(false));
  }, [runId]);

  if (loading) return <p style={{ padding: 60, textAlign: "center", color: "#94a3b8" }}>Loading report…</p>;
  if (!review) return <p style={{ padding: 60, textAlign: "center", color: "#dc2626" }}>Report not found.</p>;

  const riskLevel = (review.risk_score || 0) >= 70 ? "critical" : (review.risk_score || 0) >= 40 ? "high" : (review.risk_score || 0) >= 15 ? "medium" : "low";
  const riskColor = riskLevel === "critical" ? "#ef4444" : riskLevel === "high" ? "#f97316" : riskLevel === "medium" ? "#eab308" : "#10b981";

  return (
    <div style={{ display: "flex", height: "calc(100vh - 44px)" }}>
      {/* Left: Report header + metadata */}
      <aside style={{ width: 320, borderRight: "1px solid #e2e8f0", overflow: "auto", padding: 20 }}>
        <button onClick={() => navigate("/dashboard")}
          style={{ background: "none", border: "none", color: "#2563eb", cursor: "pointer", fontSize: 13, padding: 0, marginBottom: 16 }}>
          ← Back to Dashboard
        </button>

        <h2 style={{ fontSize: 18, fontWeight: 700, margin: "0 0 8px", wordBreak: "break-word" }}>
          {review.pr_title || `PR Review #${review.id}`}
        </h2>
        {review.pr_url && (
          <a href={review.pr_url} target="_blank" style={{ fontSize: 12, color: "#2563eb", wordBreak: "break-all" }}>
            {review.pr_url}
          </a>
        )}

        <div style={{ marginTop: 20, display: "flex", flexDirection: "column", gap: 8 }}>
          <Meta label="Run ID" value={`#${review.id}`} />
          <Meta label="Date" value={(review.created_at || "").slice(0, 19)} />
          <Meta label="Repo" value={review.repo || "—"} />
          <Meta label="Mode" value={<span style={{ padding: "2px 8px", borderRadius: 8, fontSize: 12, background: review.mode === "deep" ? "#ede9fe" : review.mode === "fast" ? "#fefce8" : "#f0fdf4", color: review.mode === "deep" ? "#7c3aed" : review.mode === "fast" ? "#854d0e" : "#166534" }}>{review.mode || "balanced"}</span>} />
          <Meta label="Categories" value={review.categories || "all"} />
          <Meta label="LLM" value={review.llm_provider || review.llm_model || "—"} />
          <Meta label="Findings" value={String(review.findings_count || 0)} />
          <Meta label="Risk Score" value={<span style={{ fontWeight: 700, color: riskColor }}>{review.risk_score || 0}/100 — {riskLevel}</span>} />
        </div>

        <div style={{ marginTop: 20, display: "flex", flexDirection: "column", gap: 8 }}>
          <button onClick={() => {
            const blob = new Blob([JSON.stringify({ review, findings }, null, 2)], { type: "application/json" });
            const a = document.createElement("a"); a.href = URL.createObjectURL(blob);
            a.download = `review-${review.id}.json`; a.click();
          }}
            style={{ padding: "8px 12px", borderRadius: 6, border: "1px solid #d1d5db", background: "#fff", cursor: "pointer", fontSize: 12 }}>
            Download JSON
          </button>
          <button onClick={() => {
            if (review.pr_url) {
              const parts = review.pr_url.split("/");
              navigate(`/review/${parts[3]}/${parts[4]}/${parts[6]}`);
            }
          }}
            style={{ padding: "8px 12px", borderRadius: 6, border: "none", background: "#2563eb", color: "#fff", cursor: "pointer", fontSize: 12 }}>
            Re-run Analysis
          </button>
        </div>
      </aside>

      {/* Center: Findings list */}
      <main style={{ flex: 1, overflow: "auto", padding: 20 }}>
        <h3 style={{ fontSize: 16, fontWeight: 600, marginBottom: 12 }}>Findings ({findings.length})</h3>
        {findings.length === 0 ? (
          <p style={{ color: "#94a3b8" }}>No findings recorded for this review.</p>
        ) : (
          findings.map((f: any, i: number) => {
            const sevColor: Record<string, string> = { critical: "#ef4444", high: "#f97316", medium: "#eab308", low: "#3b82f6" };
            return (
              <div key={i} onClick={() => setSelected(f)}
                style={{ padding: "12px 14px", marginBottom: 6, borderRadius: 8, cursor: "pointer",
                  background: selected === f ? "#e8f0fe" : "#fff",
                  border: `1px solid ${selected === f ? "#2563eb" : "#e2e8f0"}`,
                  borderLeft: `4px solid ${sevColor[f.severity] || "#6b7280"}` }}>
                <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 4 }}>
                  <span style={{ padding: "2px 8px", borderRadius: 4, fontSize: 11, fontWeight: 700, color: "#fff", background: sevColor[f.severity] || "#6b7280" }}>
                    {f.severity?.toUpperCase()}
                  </span>
                  <span style={{ padding: "2px 8px", borderRadius: 4, fontSize: 11, background: "#f3f4f6" }}>{f.category}</span>
                  <span style={{ fontSize: 11, color: "#94a3b8", marginLeft: "auto" }}>
                    {(f.location || f).file}:{(f.location || f).line}
                  </span>
                </div>
                <div style={{ fontSize: 14, fontWeight: 500 }}>{f.title}</div>
              </div>
            );
          })
        )}
      </main>

      {/* Right: Finding detail */}
      <aside style={{ width: 400, borderLeft: "1px solid #e2e8f0" }}>
        <FindingInspector finding={selected} onFeedback={() => {}} onAskFollowup={() => {}} />
      </aside>
    </div>
  );
}

function Meta({ label, value }: { label: string; value: any }) {
  return (
    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", fontSize: 13 }}>
      <span style={{ color: "#64748b" }}>{label}</span>
      <span style={{ fontWeight: 500 }}>{value}</span>
    </div>
  );
}
