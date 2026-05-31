import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import ChangeMonitor from "../components/ChangeMonitor";

const API = "http://localhost:8000";

interface PR {
  number: number; title: string; html_url: string;
  user: { login: string }; state: string; draft: boolean;
  additions: number; deletions: number; changed_files: number;
  comments: number; created_at: string;
}

function getToken() { return localStorage.getItem("ai_pr_token") || ""; }
function getRepo() { return localStorage.getItem("ai_pr_repo") || ""; }

export default function ReviewQueue() {
  const navigate = useNavigate();
  const [prs, setPrs] = useState<PR[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [filter, setFilter] = useState("open");
  const repo = getRepo(); const token = getToken();

  useEffect(() => { if (repo && token) fetchPRs(); }, [filter]);

  if (!repo || !token) return (
    <div style={{ maxWidth: 600, margin: "80px auto", textAlign: "center", padding: 24 }}>
      <h2>No repository selected</h2>
      <p style={{ color: "#6b7280", marginBottom: 24 }}>Select a repository to view its pull requests.</p>
      <button onClick={() => navigate("/connect")}
        style={{ padding: "10px 24px", borderRadius: 8, border: "none", background: "#2563eb", color: "#fff", cursor: "pointer", fontSize: 14 }}>
        Go to Repository Selection
      </button>
    </div>
  );

  async function fetchPRs() {
    setLoading(true); setError("");
    try {
      const [owner, rn] = repo.split("/");
      const resp = await fetch(`${API}/api/v1/repos/${owner}/${rn}/prs?state=${filter}&limit=30`,
        { headers: { Authorization: `Bearer ${token}` } });
      const data = await resp.json();
      data.status === "ok" ? setPrs(data.prs || []) : setError(data.message || "Failed");
    } catch { setError("Cannot reach API server"); }
    setLoading(false);
  }

  if (!repo || !token) return null;

  return (
    <div style={{ maxWidth: 1200, margin: "0 auto", padding: 24 }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
        <div>
          <h1 style={{ fontSize: 24, fontWeight: 700, margin: 0 }}>{repo} — Review Queue</h1>
          <button onClick={() => navigate("/connect")}
            style={{ background: "none", border: "none", color: "#6b7280", cursor: "pointer", padding: 0, fontSize: 13 }}>
            Change repository
          </button>
        </div>
        <div style={{ display: "flex", gap: 8 }}>
          <select value={filter} onChange={e => setFilter(e.target.value)}
            style={{ padding: "6px 12px", borderRadius: 6, border: "1px solid #d1d5db" }}>
            <option value="open">Open</option>
            <option value="closed">Closed</option>
            <option value="all">All</option>
          </select>
          <button onClick={fetchPRs}
            style={{ padding: "6px 12px", borderRadius: 6, border: "1px solid #d1d5db", background: "#fff", cursor: "pointer" }}>
            Refresh
          </button>
        </div>
      </div>
      <ChangeMonitor owner={owner} repo={repoName} token={token} />
      {error && <div style={{ padding: 12, background: "#fee2e2", color: "#dc2626", borderRadius: 8, marginBottom: 16 }}>{error}</div>}
      {loading ? <p style={{ textAlign: "center", padding: 40, color: "#9ca3af" }}>Loading pull requests...</p> :
       prs.length === 0 ? <p style={{ textAlign: "center", padding: 40, color: "#9ca3af" }}>No {filter} PRs.</p> :
        <table style={{ width: "100%", borderCollapse: "collapse" }}>
          <thead><tr style={{ borderBottom: "2px solid #e5e7eb", textAlign: "left" }}>
            <th style={{ padding: 8 }}>Title</th><th style={{ padding: 8 }}>Author</th>
            <th style={{ padding: 8 }}>Files</th><th style={{ padding: 8 }}>±Lines</th>
            <th style={{ padding: 8 }}>State</th><th style={{ padding: 8, width: 100 }}></th>
          </tr></thead>
          <tbody>
            {prs.map(pr => (
              <tr key={pr.number} style={{ borderBottom: "1px solid #f3f4f6" }}>
                <td style={{ padding: 8 }}>
                  <div style={{ fontWeight: 600 }}>{pr.title}</div>
                  {pr.draft && <span style={{ fontSize: 11, color: "#9ca3af" }}>[DRAFT]</span>}
                </td>
                <td style={{ padding: 8, fontSize: 13, color: "#6b7280" }}>{pr.user.login}</td>
                <td style={{ padding: 8, fontSize: 13 }}>{pr.changed_files}</td>
                <td style={{ padding: 8, fontSize: 13 }}>
                  <span style={{ color: "#16a34a" }}>+{pr.additions}</span> / <span style={{ color: "#dc2626" }}>-{pr.deletions}</span>
                </td>
                <td style={{ padding: 8 }}>
                  <span style={{ padding: "2px 8px", borderRadius: 4, fontSize: 12,
                    background: pr.state === "open" ? "#dcfce7" : "#f3f4f6",
                    color: pr.state === "open" ? "#16a34a" : "#6b7280" }}>{pr.state}</span>
                </td>
                <td style={{ padding: 8 }}>
                  <button onClick={() => navigate(`/review/${repo}/${pr.number}`)}
                    style={{ padding: "4px 12px", borderRadius: 6, border: "none",
                      background: "#2563eb", color: "#fff", cursor: "pointer", fontSize: 13 }}>Review</button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      }

      {/* Bulk Review section */}
      {prs.length > 0 && (
        <div style={{ marginTop: 32, padding: 16, border: "1px solid #e5e7eb", borderRadius: 8 }}>
          <h3 style={{ fontSize: 16, marginBottom: 8 }}>Bulk Review</h3>
          <p style={{ fontSize: 13, color: "#6b7280", marginBottom: 12 }}>
            Run analysis on all {prs.length} visible PRs in parallel (max 3 at a time).
          </p>
          <button onClick={async () => {
            const urls = prs.map(p => p.html_url);
            setLoading(true);
            try {
              const r = await fetch(`${API}/api/v1/batch-review`, {
                method: "POST",
                headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
                body: JSON.stringify({ pr_urls: urls, categories: "all" }),
              });
              const d = await r.json();
              let msg = `Batch review complete:\n`;
              d.results?.forEach((r: any) => {
                msg += `${r.status === "ok" ? "✓" : "✗"} ${r.url.split("/").pop()}: ${r.findings || 0} findings, risk ${r.risk_score || 0}\n`;
              });
              alert(msg);
            } catch { alert("Batch review failed."); }
            setLoading(false);
          }}
            style={{ padding: "8px 16px", borderRadius: 6, border: "none", background: "#2563eb", color: "#fff", cursor: "pointer", fontSize: 13 }}>
            Run Batch Review ({prs.length} PRs)
          </button>
        </div>
      )}
    </div>
  );
}
