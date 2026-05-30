import { useState } from "react";
import { useNavigate } from "react-router-dom";

interface PR {
  id: string; repo: string; title: string; author: string;
  risk: number; files: number; ci: "pass" | "fail" | "pending";
  reviewed: boolean;
}

const mockPRs: PR[] = [
  { id: "1", repo: "ai-pr-reviewer", title: "feat: add fix patch generation", author: "dev1", risk: 72, files: 5, ci: "pass", reviewed: false },
  { id: "2", repo: "ai-pr-reviewer", title: "fix: null check in auth", author: "dev2", risk: 45, files: 2, ci: "fail", reviewed: true },
  { id: "3", repo: "api-server", title: "Add rate limiting middleware", author: "dev3", risk: 88, files: 8, ci: "pass", reviewed: false },
  { id: "4", repo: "frontend", title: "Update dashboard layout", author: "dev1", risk: 12, files: 3, ci: "pass", reviewed: false },
  { id: "5", repo: "ai-pr-reviewer", title: "docs: update README", author: "dev4", risk: 5, files: 1, ci: "pass", reviewed: true },
];

export default function ReviewQueue() {
  const navigate = useNavigate();
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [filter, setFilter] = useState("all");

  const toggle = (id: string) => {
    const next = new Set(selected);
    next.has(id) ? next.delete(id) : next.add(id);
    setSelected(next);
  };

  const filtered = mockPRs.filter((pr) => {
    if (filter === "unreviewed") return !pr.reviewed;
    if (filter === "high-risk") return pr.risk >= 70;
    return true;
  });

  return (
    <div style={{ padding: 24, maxWidth: 1200, margin: "0 auto" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
        <h1 style={{ fontSize: 28, fontWeight: 700 }}>Review Queue</h1>
        <div style={{ display: "flex", gap: 8 }}>
          <select value={filter} onChange={(e) => setFilter(e.target.value)}
            style={{ padding: "6px 12px", borderRadius: 6, border: "1px solid #d1d5db" }}>
            <option value="all">All PRs</option>
            <option value="unreviewed">Unreviewed</option>
            <option value="high-risk">High Risk</option>
          </select>
          <button disabled={selected.size === 0}
            style={{ padding: "6px 16px", borderRadius: 6, border: "none",
              background: selected.size > 0 ? "#2563eb" : "#d1d5db", color: "#fff", cursor: selected.size > 0 ? "pointer" : "default" }}>
            Review Selected ({selected.size})
          </button>
        </div>
      </div>

      <table style={{ width: "100%", borderCollapse: "collapse" }}>
        <thead>
          <tr style={{ borderBottom: "2px solid #e5e7eb", textAlign: "left" }}>
            <th style={{ padding: 8, width: 40 }}>#</th>
            <th style={{ padding: 8 }}>Repository</th>
            <th style={{ padding: 8 }}>Title</th>
            <th style={{ padding: 8 }}>Author</th>
            <th style={{ padding: 8 }}>Files</th>
            <th style={{ padding: 8 }}>CI</th>
            <th style={{ padding: 8 }}>Risk</th>
            <th style={{ padding: 8 }}>Status</th>
          </tr>
        </thead>
        <tbody>
          {filtered.map((pr) => (
            <tr key={pr.id} style={{ borderBottom: "1px solid #f3f4f6" }}>
              <td style={{ padding: 8 }}>
                <input type="checkbox" checked={selected.has(pr.id)} onChange={() => toggle(pr.id)} />
              </td>
              <td style={{ padding: 8, fontSize: 13 }}>{pr.repo}</td>
              <td style={{ padding: 8 }}>{pr.title}</td>
              <td style={{ padding: 8, fontSize: 13, color: "#6b7280" }}>{pr.author}</td>
              <td style={{ padding: 8, fontSize: 13 }}>{pr.files}</td>
              <td style={{ padding: 8 }}>
                <span style={{
                  color: pr.ci === "pass" ? "#16a34a" : pr.ci === "fail" ? "#dc2626" : "#ca8a04",
                  fontSize: 12,
                }}>
                  {pr.ci === "pass" ? "✓" : pr.ci === "fail" ? "✗" : "○"}
                </span>
              </td>
              <td style={{ padding: 8 }}>
                <span style={{
                  padding: "2px 8px", borderRadius: 4, fontSize: 12,
                  backgroundColor: pr.risk >= 70 ? "#fee2e2" : pr.risk >= 40 ? "#fef3c7" : "#dcfce7",
                  color: pr.risk >= 70 ? "#dc2626" : pr.risk >= 40 ? "#ca8a04" : "#16a34a",
                }}>
                  {pr.risk}/100
                </span>
              </td>
              <td style={{ padding: 8, fontSize: 12 }}>
                {pr.reviewed
                  ? <span style={{ color: "#16a34a" }}>Reviewed</span>
                  : <button onClick={() => navigate(`/review/${pr.repo}/pull/${pr.id}`)}
                      style={{ padding: "2px 10px", borderRadius: 4, border: "none",
                        background: "#2563eb", color: "#fff", cursor: "pointer", fontSize: 12 }}>
                      Review
                    </button>
                }
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      {filtered.length === 0 && (
        <p style={{ color: "#9ca3af", textAlign: "center", padding: 32 }}>No PRs match the current filter.</p>
      )}
    </div>
  );
}
