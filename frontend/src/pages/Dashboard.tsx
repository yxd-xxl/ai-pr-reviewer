import { useNavigate } from "react-router-dom";

interface MetricCard {
  label: string; value: string | number; trend?: string;
}

const mockMetrics: MetricCard[] = [
  { label: "Today's Focus", value: "3 PRs", trend: "2 need review" },
  { label: "Open PRs", value: 12, trend: "+3 this week" },
  { label: "High Risk", value: 2, trend: "↓ from 5" },
  { label: "Avg Review Time", value: "47s", trend: "per PR" },
];

const mockRecent = [
  { repo: "ai-pr-reviewer", pr: "#42 Fix patch gen", risk: 72, time: "2 min ago" },
  { repo: "ai-pr-reviewer", pr: "#41 Streamlit UI", risk: 35, time: "15 min ago" },
  { repo: "api-server", pr: "#128 Auth callback", risk: 88, time: "1 hour ago" },
];

export default function Dashboard() {
  return (
    <div style={{ padding: 24, maxWidth: 1200, margin: "0 auto" }}>
      <h1 style={{ fontSize: 28, fontWeight: 700 }}>Dashboard</h1>
      <p style={{ color: "#6b7280", marginBottom: 24 }}>AI PR Reviewer — your team's review health at a glance.</p>

      <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 16, marginBottom: 32 }}>
        {mockMetrics.map((m) => (
          <div key={m.label} style={{ padding: 20, border: "1px solid #e5e7eb", borderRadius: 8, background: "#fff" }}>
            <div style={{ fontSize: 13, color: "#6b7280" }}>{m.label}</div>
            <div style={{ fontSize: 28, fontWeight: 700, margin: "4px 0" }}>{m.value}</div>
            {m.trend && <div style={{ fontSize: 12, color: "#059669" }}>{m.trend}</div>}
          </div>
        ))}
      </div>

      <h2 style={{ fontSize: 20, marginBottom: 12 }}>Recent Reviews</h2>
      <table style={{ width: "100%", borderCollapse: "collapse" }}>
        <thead>
          <tr style={{ borderBottom: "2px solid #e5e7eb", textAlign: "left" }}>
            <th style={{ padding: 8 }}>Repository</th>
            <th style={{ padding: 8 }}>PR</th>
            <th style={{ padding: 8 }}>Risk</th>
            <th style={{ padding: 8 }}>Time</th>
          </tr>
        </thead>
        <tbody>
          {mockRecent.map((r, i) => (
            <tr key={i} style={{ borderBottom: "1px solid #f3f4f6" }}>
              <td style={{ padding: 8 }}>{r.repo}</td>
              <td style={{ padding: 8 }}>{r.pr}</td>
              <td style={{ padding: 8 }}>
                <span style={{
                  padding: "2px 8px", borderRadius: 4, fontSize: 12,
                  backgroundColor: r.risk >= 70 ? "#fee2e2" : r.risk >= 40 ? "#fef3c7" : "#dcfce7",
                  color: r.risk >= 70 ? "#dc2626" : r.risk >= 40 ? "#ca8a04" : "#16a34a",
                }}>
                  {r.risk}/100
                </span>
              </td>
              <td style={{ padding: 8, color: "#9ca3af" }}>{r.time}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
