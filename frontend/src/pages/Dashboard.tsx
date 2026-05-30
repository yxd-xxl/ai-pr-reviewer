import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";

const API = "http://localhost:8000";
function getToken() { return localStorage.getItem("ai_pr_token") || ""; }

export default function Dashboard() {
  const navigate = useNavigate();
  const [reviews, setReviews] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const t = getToken();
    if (!t) { navigate("/connect"); return; }
    fetch(`${API}/api/v1/reviews?limit=50`, { headers: { Authorization: `Bearer ${t}` } })
      .then(r => r.json()).then(d => { setReviews(d.reviews || []); setLoading(false); })
      .catch(() => setLoading(false));
  }, []);

  const totalFindings = reviews.reduce((s, r) => s + (r.findings_count || 0), 0);
  const avgRisk = reviews.length ? Math.round(reviews.reduce((s: number, r: any) => s + (r.risk_score || 0), 0) / reviews.length) : 0;

  return (
    <div style={{ maxWidth: 1200, margin: "0 auto", padding: 24 }}>
      <h1 style={{ fontSize: 28, fontWeight: 700, marginBottom: 24 }}>Review History</h1>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 16, marginBottom: 32 }}>
        {[{ label: "Total Reviews", value: reviews.length },
          { label: "Total Findings", value: totalFindings },
          { label: "Avg Risk Score", value: `${avgRisk}/100` },
          { label: "Status", value: "Connected" }].map(m => (
          <div key={m.label} style={{ padding: 20, border: "1px solid #e5e7eb", borderRadius: 8, background: "#fff" }}>
            <div style={{ fontSize: 13, color: "#6b7280" }}>{m.label}</div>
            <div style={{ fontSize: 28, fontWeight: 700 }}>{m.value}</div>
          </div>
        ))}
      </div>
      {loading ? <p style={{ color: "#9ca3af", textAlign: "center", padding: 40 }}>Loading review history...</p> :
       reviews.length === 0 ? <p style={{ color: "#9ca3af", textAlign: "center", padding: 40 }}>No reviews yet. Connect a repo and start reviewing!</p> :
        <table style={{ width: "100%", borderCollapse: "collapse" }}>
          <thead><tr style={{ borderBottom: "2px solid #e5e7eb", textAlign: "left" }}>
            <th style={{ padding: 8 }}>ID</th><th style={{ padding: 8 }}>Repo</th>
            <th style={{ padding: 8 }}>PR</th><th style={{ padding: 8 }}>Mode</th>
            <th style={{ padding: 8 }}>Findings</th><th style={{ padding: 8 }}>Risk</th>
            <th style={{ padding: 8 }}>Date</th>
          </tr></thead>
          <tbody>{reviews.map(r => (
            <tr key={r.id} style={{ borderBottom: "1px solid #f3f4f6" }}>
              <td style={{ padding: 8 }}>#{r.id}</td>
              <td style={{ padding: 8, fontSize: 13 }}>{r.repo}</td>
              <td style={{ padding: 8, fontSize: 13, maxWidth: 300, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{r.pr_title}</td>
              <td style={{ padding: 8 }}>{r.mode}</td>
              <td style={{ padding: 8 }}>{r.findings_count}</td>
              <td style={{ padding: 8 }}><span style={{ padding: "2px 8px", borderRadius: 4, fontSize: 12,
                background: (r.risk_score||0) >= 70 ? "#fee2e2" : (r.risk_score||0) >= 40 ? "#fef3c7" : "#dcfce7",
                color: (r.risk_score||0) >= 70 ? "#dc2626" : (r.risk_score||0) >= 40 ? "#ca8a04" : "#16a34a" }}>{r.risk_score || 0}</span></td>
              <td style={{ padding: 8, fontSize: 12, color: "#9ca3af" }}>{r.created_at?.slice(0, 19) || ""}</td>
            </tr>
          ))}</tbody>
        </table>
      }
    </div>
  );
}
