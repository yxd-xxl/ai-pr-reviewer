import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { t } from "../i18n";

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
  const riskDist = { low: reviews.filter(r => (r.risk_score||0) < 15).length, medium: reviews.filter(r => (r.risk_score||0) >= 15 && (r.risk_score||0) < 40).length, high: reviews.filter(r => (r.risk_score||0) >= 40 && (r.risk_score||0) < 70).length, critical: reviews.filter(r => (r.risk_score||0) >= 70).length };
  const repos = [...new Set(reviews.map(r => r.repo).filter(Boolean))];

  if (loading) return <p style={{ padding: 60, textAlign: "center", color: "#94a3b8", fontSize: 15 }}>Loading dashboard…</p>;

  return (
    <div style={{ maxWidth: 1040, margin: "0 auto", padding: "28px 24px" }}>
      {/* Header */}
      <div style={{ marginBottom: 24 }}>
        <h1 style={{ fontSize: 26, fontWeight: 700, margin: 0, color: "#0f172a" }}>{t("Dashboard")}</h1>
        <p style={{ color: "#64748b", fontSize: 14, margin: "4px 0 0" }}>
          {reviews.length > 0 ? `${reviews.length} reviews across ${repos.length} ${t("repositories")}` : t("Connect a repository to start reviewing PRs.")}
        </p>
      </div>

      {/* Stat cards */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 14, marginBottom: 24 }}>
        {[
          { icon: "📋", label: t("Total Reviews"), value: reviews.length, sub: `${repos.length} ${t("repositories")}`, color: "#3b82f6" },
          { icon: "🔍", label: t("Total Findings"), value: totalFindings, sub: `${reviews.length > 0 ? (totalFindings / reviews.length).toFixed(1) : "0"} ${t("per review")}`, color: "#8b5cf6" },
          { icon: "⚠️", label: t("Avg Risk Score"), value: `${avgRisk}/100`, sub: t(avgRisk >= 40 ? "Needs attention" : avgRisk >= 15 ? "Moderate" : "Healthy"), color: avgRisk >= 40 ? "#ef4444" : avgRisk >= 15 ? "#f97316" : "#10b981" },
          { icon: "🏷️", label: t("High Risk PRs"), value: riskDist.critical + riskDist.high, sub: `${riskDist.critical} critical · ${riskDist.high} high`, color: (riskDist.critical+riskDist.high) > 0 ? "#ef4444" : "#10b981" },
        ].map(m => (
          <div key={m.label} style={{ padding: "18px 20px", borderRadius: 12, background: "#fff", border: "1px solid #e2e8f0", boxShadow: "0 1px 3px rgba(0,0,0,0.04)" }}>
            <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 10 }}>
              <div style={{ width: 36, height: 36, borderRadius: 10, background: `${m.color}12`, display: "flex", alignItems: "center", justifyContent: "center", fontSize: 18 }}>{m.icon}</div>
              <span style={{ fontSize: 13, color: "#64748b", fontWeight: 500 }}>{m.label}</span>
            </div>
            <div style={{ fontSize: 30, fontWeight: 800, color: "#0f172a", lineHeight: 1 }}>{m.value}</div>
            <div style={{ fontSize: 12, color: "#94a3b8", marginTop: 4 }}>{m.sub}</div>
          </div>
        ))}
      </div>

      {/* Two column */}
      <div style={{ display: "grid", gridTemplateColumns: "2fr 1fr", gap: 20, marginBottom: 24 }}>
        {/* Recent Reviews */}
        <div style={{ padding: 20, borderRadius: 12, background: "#fff", border: "1px solid #e2e8f0" }}>
          <h3 style={{ fontSize: 15, fontWeight: 600, margin: "0 0 16px", color: "#0f172a" }}>{t("Recent Reviews")}</h3>
          {reviews.length === 0 ? (
            <p style={{ color: "#94a3b8", fontSize: 14, textAlign: "center", padding: 30 }}>{t("No reviews yet. Go to the Review Queue to start.")}</p>
          ) : (
            <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
              <thead><tr style={{ borderBottom: "1px solid #e2e8f0" }}>
                <th style={{ padding: "6px 8px", textAlign: "left", color: "#64748b", fontSize: 11, fontWeight: 600 }}>{t("PR")}</th>
                <th style={{ padding: "6px 8px", textAlign: "left", color: "#64748b", fontSize: 11, fontWeight: 600 }}>{t("REPO")}</th>
                <th style={{ padding: "6px 8px", textAlign: "left", color: "#64748b", fontSize: 11, fontWeight: 600 }}>{t("MODE")}</th>
                <th style={{ padding: "6px 8px", textAlign: "left", color: "#64748b", fontSize: 11, fontWeight: 600 }}>{t("CATEGORIES")}</th>
                <th style={{ padding: "6px 8px", textAlign: "right", color: "#64748b", fontSize: 11, fontWeight: 600 }}>{t("FINDINGS")}</th>
                <th style={{ padding: "6px 8px", textAlign: "right", color: "#64748b", fontSize: 11, fontWeight: 600 }}>{t("RISK")}</th>
                <th style={{ padding: "6px 8px", textAlign: "right", color: "#64748b", fontSize: 11, fontWeight: 600 }}>{t("DATE")}</th>
              </tr></thead>
              <tbody>
                {reviews.slice(0, 15).map(r => (
                  <tr key={r.id} style={{ borderBottom: "1px solid #f1f5f9", cursor: "pointer" }}
                    onClick={() => navigate(`/review-report/${r.id}`)}
                    title="Click to view full report">
                    <td style={{ padding: 8, maxWidth: 240, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{r.pr_title || `#${r.id}`}</td>
                    <td style={{ padding: 8, fontSize: 12, color: "#64748b" }}>{r.repo}</td>
                    <td style={{ padding: 8 }}><span style={{ fontSize: 11, padding: "1px 6px", borderRadius: 8, background: r.mode==="deep"?"#ede9fe":r.mode==="fast"?"#fefce8":"#f0fdf4", color: r.mode==="deep"?"#7c3aed":r.mode==="fast"?"#854d0e":"#166534" }}>{r.mode || "balanced"}</span></td>
                    <td style={{ padding: 8, fontSize: 11, color: "#64748b", maxWidth: 100, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{r.categories || "all"}</td>
                    <td style={{ padding: 8, textAlign: "right" }}>{r.findings_count}</td>
                    <td style={{ padding: 8, textAlign: "right" }}>
                      <span style={{ padding: "2px 8px", borderRadius: 12, fontSize: 11, fontWeight: 500,
                        background: (r.risk_score||0)>=70?"#fef2f2":(r.risk_score||0)>=40?"#fefce8":"#f0fdf4",
                        color: (r.risk_score||0)>=70?"#991b1b":(r.risk_score||0)>=40?"#854d0e":"#166534" }}>
                        {r.risk_score || 0}
                      </span>
                    </td>
                    <td style={{ padding: 8, fontSize: 11, color: "#94a3b8", textAlign: "right" }}>{(r.created_at||"").slice(0,10)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>

        {/* Risk Distribution */}
        <div style={{ padding: 20, borderRadius: 12, background: "#fff", border: "1px solid #e2e8f0" }}>
          <h3 style={{ fontSize: 15, fontWeight: 600, margin: "0 0 16px", color: "#0f172a" }}>{t("Risk Distribution")}</h3>
          {reviews.length === 0 ? (
            <p style={{ color: "#94a3b8", fontSize: 14, textAlign: "center", padding: 30 }}>{t("No data yet.")}</p>
          ) : (
            <div>
              {[{ label: t("Critical"), count: riskDist.critical, color: "#ef4444" },
                { label: t("High"), count: riskDist.high, color: "#f97316" },
                { label: t("Medium"), count: riskDist.medium, color: "#eab308" },
                { label: t("Low"), count: riskDist.low, color: "#10b981" }].map(r => (
                <div key={r.label} style={{ marginBottom: 12 }}>
                  <div style={{ display: "flex", justifyContent: "space-between", fontSize: 13, marginBottom: 4 }}>
                    <span style={{ fontWeight: 500 }}>{r.label}</span>
                    <span style={{ color: r.color, fontWeight: 600 }}>{r.count}</span>
                  </div>
                  <div style={{ height: 8, background: "#f1f5f9", borderRadius: 4, overflow: "hidden" }}>
                    <div style={{ height: "100%", width: `${reviews.length > 0 ? (r.count/reviews.length)*100 : 0}%`, background: r.color, borderRadius: 4 }} />
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Quick actions */}
      <div style={{ padding: 20, borderRadius: 12, background: "#fff", border: "1px solid #e2e8f0" }}>
        <h3 style={{ fontSize: 15, fontWeight: 600, margin: "0 0 14px", color: "#0f172a" }}>{t("Quick Actions")}</h3>
        <div style={{ display: "flex", gap: 12 }}>
          {[{ label: t("Review Queue"), to: "/review-queue", icon: "📋" },
            { label: t("Select Repository"), to: "/connect", icon: "📂" },
            { label: t("Evaluation"), to: "/evaluation", icon: "📊" },
            { label: t("Settings"), to: "/settings", icon: "⚙️" }].map(a => (
            <button key={a.to} onClick={() => navigate(a.to)}
              style={{ padding: "12px 20px", borderRadius: 10, border: "1px solid #e2e8f0", background: "#f8fafc", cursor: "pointer", fontSize: 13, fontWeight: 500, color: "#0f172a", display: "flex", alignItems: "center", gap: 8 }}>
              {a.icon} {a.label}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
