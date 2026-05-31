import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import ChangeMonitor from "../components/ChangeMonitor";

const API = "http://localhost:8000";
const CACHE_TTL = 5 * 60 * 1000; // 5 minutes

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
  const [filter, setFilter] = useState(() => sessionStorage.getItem("pr_filter") || "open");
  const [selected, setSelected] = useState<Set<number>>(new Set());
  const [bulkResults, setBulkResults] = useState<any[] | null>(null);
  const [bulkRunning, setBulkRunning] = useState(false);
  const [bulkConfig, setBulkConfig] = useState(false);
  const [bulkCategories, setBulkCategories] = useState("all");
  const [bulkMode, setBulkMode] = useState("balanced");
  const [bulkProgress, setBulkProgress] = useState({ done: 0, total: 0 });
  const repo = getRepo(); const token = getToken();

  useEffect(() => {
    if (!repo || !token) return;
    const cacheKey = `pr_cache_${repo}_${filter}`;
    const cached = sessionStorage.getItem(cacheKey);
    if (cached) {
      try {
        const { data, ts } = JSON.parse(cached);
        if (Date.now() - ts < CACHE_TTL) { setPrs(data); setLoading(false); return; }
      } catch {}
    }
    fetchPRs(cacheKey);
  }, [filter, repo]);

  async function fetchPRs(cacheKey?: string) {
    setLoading(true); setError("");
    try {
      const [o, r] = repo.split("/");
      const resp = await fetch(`${API}/api/v1/repos/${o}/${r}/prs?state=${filter}&limit=30`,
        { headers: { Authorization: `Bearer ${token}` } });
      const data = await resp.json();
      if (data.status === "ok") {
        setPrs(data.prs || []);
        const key = cacheKey || `pr_cache_${repo}_${filter}`;
        sessionStorage.setItem(key, JSON.stringify({ data: data.prs || [], ts: Date.now() }));
      } else setError(data.message || "Failed");
    } catch { setError("Cannot reach API server"); }
    setLoading(false);
  }

  function setCachedFilter(v: string) { sessionStorage.setItem("pr_filter", v); setFilter(v); }

  async function runBulkReview() {
    const toReview = selected.size > 0 ? prs.filter(p => selected.has(p.number)) : prs;
    setBulkConfig(false); setBulkRunning(true); setBulkResults(null);

    try {
      const resp = await fetch(`${API}/api/v1/batch-review`, {
        method: "POST",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
        body: JSON.stringify({ pr_urls: toReview.map(p => p.html_url), categories: bulkCategories, mode: bulkMode, llm_provider: localStorage.getItem("ai_pr_llm_provider") || "", llm_api_key: localStorage.getItem("ai_pr_llm_key") || "", llm_model: localStorage.getItem("ai_pr_llm_model") || "" }),
      });
      const d = await resp.json();
      if (d.status === "ok") {
        const results = d.results.map((r: any) => ({
          url: r.url, number: parseInt(r.url.split("/").pop()), title: r.title || "",
          status: r.status, findings: r.findings || 0,
          risk_score: r.risk_score || 0, risk_level: r.risk_level || "low",
        }));
        setBulkResults(results);
      } else {
        setError(d.message || d.detail || "Batch review failed");
      }
    } catch (e: any) { setError("Batch review failed: " + (e.message || "network error")); }
    setBulkRunning(false);
  }

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

  const [owner, repoName] = repo.split("/");

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
          <select value={filter} onChange={e => setCachedFilter(e.target.value)}
            style={{ padding: "6px 12px", borderRadius: 6, border: "1px solid #d1d5db" }}>
            <option value="open">Open</option><option value="closed">Closed</option><option value="all">All</option>
          </select>
          <button onClick={() => fetchPRs()}
            style={{ padding: "6px 12px", borderRadius: 6, border: "1px solid #d1d5db", background: "#fff", cursor: "pointer" }}>
            Refresh
          </button>
        </div>
      </div>

      <ChangeMonitor owner={owner} repo={repoName} token={token} />

      {error && <div style={{ padding: 12, background: "#fee2e2", color: "#dc2626", borderRadius: 8, margin: "12px 0" }}>{error}</div>}

      {loading ? <p style={{ textAlign: "center", padding: 40, color: "#9ca3af" }}>Loading pull requests...</p> :
       prs.length === 0 ? <p style={{ textAlign: "center", padding: 40, color: "#9ca3af" }}>No {filter} PRs.</p> :
        <table style={{ width: "100%", borderCollapse: "collapse" }}>
          <thead><tr style={{ borderBottom: "2px solid #e5e7eb", textAlign: "left" }}>
            <th style={{ padding: 8, width: 30 }}>#</th><th style={{ padding: 8 }}>Title</th>
            <th style={{ padding: 8 }}>Author</th><th style={{ padding: 8 }}>Files</th>
            <th style={{ padding: 8 }}>±Lines</th><th style={{ padding: 8 }}>State</th><th style={{ padding: 8, width: 100 }}></th>
          </tr></thead>
          <tbody>
            {prs.map(pr => (
              <tr key={pr.number} style={{ borderBottom: "1px solid #f3f4f6" }}>
                <td style={{ padding: 8 }}>
                  <input type="checkbox" checked={selected.has(pr.number)}
                    onChange={() => { const s = new Set(selected); s.has(pr.number) ? s.delete(pr.number) : s.add(pr.number); setSelected(s); }} />
                </td>
                <td style={{ padding: 8 }}><div style={{ fontWeight: 600 }}>{pr.title}</div>{pr.draft && <span style={{ fontSize: 11, color: "#9ca3af" }}>[DRAFT]</span>}</td>
                <td style={{ padding: 8, fontSize: 13, color: "#6b7280" }}>{pr.user.login}</td>
                <td style={{ padding: 8, fontSize: 13 }}>{pr.changed_files}</td>
                <td style={{ padding: 8, fontSize: 13 }}><span style={{ color: "#16a34a" }}>+{pr.additions}</span> / <span style={{ color: "#dc2626" }}>-{pr.deletions}</span></td>
                <td style={{ padding: 8 }}><span style={{ padding: "2px 8px", borderRadius: 4, fontSize: 12, background: pr.state === "open" ? "#dcfce7" : "#f3f4f6", color: pr.state === "open" ? "#16a34a" : "#6b7280" }}>{pr.state}</span></td>
                <td style={{ padding: 8 }}>
                  <button onClick={() => navigate(`/review/${repo}/${pr.number}`)}
                    style={{ padding: "4px 12px", borderRadius: 6, border: "none", background: "#2563eb", color: "#fff", cursor: "pointer", fontSize: 13 }}>Review</button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      }

      {/* Bulk Review section */}
      <div style={{ marginTop: 32, padding: 16, border: "1px solid #e5e7eb", borderRadius: 8 }}>
        <h3 style={{ fontSize: 16, marginBottom: 8 }}>Bulk Review</h3>
        <p style={{ fontSize: 13, color: "#6b7280", marginBottom: 12 }}>
          {selected.size > 0 ? `${selected.size} PR(s) selected. ` : `All ${prs.length} visible PRs. `}
          {bulkConfig ? "Configure and start:" : ""}
        </p>

        {!bulkConfig && !bulkRunning && (
          <button onClick={() => setBulkConfig(true)}
            style={{ padding: "8px 16px", borderRadius: 6, border: "none", background: "#2563eb", color: "#fff", cursor: "pointer", fontSize: 13 }}>
            Configure Bulk Review
          </button>
        )}

        {bulkConfig && (
          <div style={{ display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap" }}>
            <select value={bulkCategories} onChange={e => setBulkCategories(e.target.value)}
              style={{ padding: "6px 10px", borderRadius: 6, border: "1px solid #d1d5db", fontSize: 13 }}>
              <option value="all">All Categories</option>
              <option value="security">Security Only</option>
              <option value="bug">Bug Only</option>
              <option value="security,bug">Security + Bug</option>
            </select>
            <select value={bulkMode} onChange={e => setBulkMode(e.target.value)}
              style={{ padding: "6px 10px", borderRadius: 6, border: "1px solid #d1d5db", fontSize: 13 }}>
              <option value="fast">Fast</option>
              <option value="balanced">Balanced</option>
              <option value="deep">Deep</option>
            </select>
            <button onClick={runBulkReview}
              style={{ padding: "6px 14px", borderRadius: 6, border: "none", background: "#16a34a", color: "#fff", cursor: "pointer", fontSize: 13 }}>
              Start
            </button>
            <button onClick={() => setBulkConfig(false)}
              style={{ padding: "6px 14px", borderRadius: 6, border: "1px solid #d1d5db", background: "#fff", cursor: "pointer", fontSize: 13 }}>
              Cancel
            </button>
          </div>
        )}

        {bulkRunning && (
          <div style={{ marginTop: 8 }}>
            <div style={{ height: 4, background: "#e5e7eb", borderRadius: 2, overflow: "hidden" }}>
              <div style={{ height: "100%", width: `${(bulkProgress.done / bulkProgress.total) * 100}%`, background: "#2563eb", transition: "width 0.3s" }} />
            </div>
            <p style={{ fontSize: 12, color: "#6b7280", marginTop: 4 }}>{bulkProgress.done}/{bulkProgress.total} complete</p>
          </div>
        )}

        {bulkResults && (
          <div style={{ marginTop: 16 }}>
            <h4 style={{ fontSize: 14, marginBottom: 8 }}>Results</h4>
            {bulkResults.map((r: any, i: number) => (
              <div key={i} style={{ padding: "6px 0", borderBottom: "1px solid #f3f4f6", fontSize: 13, display: "flex", alignItems: "center", gap: 8 }}>
                <span>{r.status === "ok" ? "✓" : "✗"}</span>
                <a href={`/review/${repo}/${r.number}`}
                  style={{ color: "#2563eb", textDecoration: "none", flex: 1 }}
                  onClick={e => { e.preventDefault(); navigate(`/review/${repo}/${r.number}`); }}>
                  #{r.number} {r.title?.slice(0, 60)}
                </a>
                {r.status === "ok" && (
                  <span style={{ fontSize: 11 }}>
                    <span style={{ color: "#dc2626" }}>{r.findings} findings</span>
                    <span style={{ marginLeft: 8, padding: "1px 6px", borderRadius: 4, fontSize: 10,
                      background: (r.risk_score || 0) >= 70 ? "#fee2e2" : (r.risk_score || 0) >= 40 ? "#fef3c7" : "#dcfce7",
                      color: (r.risk_score || 0) >= 70 ? "#dc2626" : (r.risk_score || 0) >= 40 ? "#ca8a04" : "#16a34a" }}>
                      risk {r.risk_score || 0}
                    </span>
                  </span>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
