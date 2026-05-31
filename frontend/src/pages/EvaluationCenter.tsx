import { useState, useEffect } from "react";

const API = "http://localhost:8000";
const sevColors: Record<string, string> = { bug: "#dc2626", security: "#ea580c", performance: "#2563eb", design: "#7c3aed", failure: "#ca8a04", quality: "#059669" };

function Bar({ label, value, color, max = 1 }: { label: string; value: number; color: string; max?: number }) {
  const pct = Math.round((value / max) * 100);
  return (
    <div style={{ marginBottom: 8 }}>
      <div style={{ display: "flex", justifyContent: "space-between", fontSize: 12, marginBottom: 2 }}>
        <span>{label}</span><span style={{ fontWeight: 600 }}>{(value * 100).toFixed(0)}%</span>
      </div>
      <div style={{ height: 8, background: "#e5e7eb", borderRadius: 4, overflow: "hidden" }}>
        <div style={{ height: "100%", width: `${pct}%`, background: color, borderRadius: 4, transition: "width 0.5s" }} />
      </div>
    </div>
  );
}

export default function EvaluationCenter() {
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [running, setRunning] = useState(false);
  const [runResult, setRunResult] = useState<any>(null);

  useEffect(() => {
    fetch(`${API}/api/v1/eval`).then(r => r.json()).then(d => { setData(d); setLoading(false); }).catch(() => setLoading(false));
  }, []);

  async function runEval() {
    setRunning(true); setRunResult(null);
    try {
      const token = localStorage.getItem("ai_pr_token") || "";
      const r = await fetch(`${API}/api/v1/eval/run`, { method: "POST", headers: { Authorization: `Bearer ${token}` } });
      const d = await r.json();
      setRunResult(d);
      if (d.status === "ok") { const r2 = await fetch(`${API}/api/v1/eval`); setData(await r2.json()); }
    } catch { setRunResult({ status: "error", message: "Failed" }); }
    setRunning(false);
  }

  if (loading) return <p style={{ padding: 40, textAlign: "center", color: "#9ca3af" }}>Loading...</p>;
  if (!data) return <p style={{ padding: 40, textAlign: "center", color: "#dc2626" }}>Failed to load evaluation data.</p>;

  const b = data.baseline;
  const cats = data.categories || [];
  const maxF1 = Math.max(...cats.map((c: any) => c.f1), 0.1);

  return (
    <div style={{ maxWidth: 1000, margin: "0 auto", padding: 24 }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 24 }}>
        <h1 style={{ fontSize: 28, fontWeight: 700, margin: 0 }}>Evaluation Center</h1>
        <button onClick={runEval} disabled={running}
          style={{ padding: "10px 20px", borderRadius: 8, border: "none", background: running ? "#d1d5db" : "#2563eb", color: "#fff", cursor: running ? "default" : "pointer", fontSize: 14, fontWeight: 600 }}>
          {running ? "Running 11 eval cases..." : "Run Evaluation"}
        </button>
      </div>

      {runResult && (
        <div style={{ padding: 12, marginBottom: 16, borderRadius: 8, background: runResult.status === "ok" ? "#dcfce7" : "#fee2e2", color: runResult.status === "ok" ? "#16a34a" : "#dc2626", fontSize: 14 }}>
          {runResult.status === "ok"
            ? `Eval complete: P=${(runResult.precision*100).toFixed(0)}% R=${(runResult.recall*100).toFixed(0)}% F1=${runResult.f1.toFixed(3)}`
            : `Eval failed: ${runResult.message}`}
        </div>
      )}

      {b && (
        <div style={{ display: "grid", gridTemplateColumns: "repeat(5, 1fr)", gap: 12, marginBottom: 32 }}>
          {[{ label: "Precision", value: `${(b.precision*100).toFixed(1)}%`, sub: "correct / total found" },
            { label: "Recall", value: `${(b.recall*100).toFixed(1)}%`, sub: "found / should find" },
            { label: "F1 Score", value: b.f1.toFixed(3), sub: "harmonic mean" },
            { label: "Model", value: b.model, sub: `${b.total_cases || 11} eval cases` },
            { label: "Evaluated", value: b.evaluated_at?.slice(0,10) || "?", sub: "last run date" }].map(m => (
            <div key={m.label} style={{ padding: 16, border: "1px solid #e5e7eb", borderRadius: 8, background: "#fff" }}>
              <div style={{ fontSize: 12, color: "#6b7280" }}>{m.label}</div>
              <div style={{ fontSize: 22, fontWeight: 700, margin: "4px 0" }}>{m.value}</div>
              <div style={{ fontSize: 11, color: "#9ca3af" }}>{m.sub}</div>
            </div>
          ))}
        </div>
      )}

      <h2 style={{ fontSize: 18, fontWeight: 600, marginBottom: 16 }}>F1 Score by Category</h2>
      {cats.map((c: any) => (
        <Bar key={c.cat} label={`${c.cat} (${c.analyzer})`} value={c.f1} color={sevColors[c.cat] || "#6b7280"} max={maxF1} />
      ))}

      <h2 style={{ fontSize: 18, fontWeight: 600, margin: "24px 0 12px" }}>Detailed Breakdown</h2>
      <table style={{ width: "100%", borderCollapse: "collapse" }}>
        <thead><tr style={{ borderBottom: "2px solid #e5e7eb", textAlign: "left" }}>
          <th style={{ padding: 8 }}>Category</th><th style={{ padding: 8 }}>Precision</th><th style={{ padding: 8 }}>Recall</th><th style={{ padding: 8 }}>F1</th><th style={{ padding: 8 }}>Analyzer</th><th style={{ padding: 8 }}>Status</th>
        </tr></thead>
        <tbody>
          {cats.map((c: any) => (
            <tr key={c.cat} style={{ borderBottom: "1px solid #f3f4f6" }}>
              <td style={{ padding: 8, fontWeight: 600, display: "flex", alignItems: "center", gap: 6 }}>
                <span style={{ width: 10, height: 10, borderRadius: "50%", background: sevColors[c.cat] || "#6b7280", display: "inline-block" }} />{c.cat}
              </td>
              <td style={{ padding: 8 }}>{(c.precision*100).toFixed(0)}%</td><td style={{ padding: 8 }}>{(c.recall*100).toFixed(0)}%</td>
              <td style={{ padding: 8, fontWeight: 600 }}>{c.f1.toFixed(2)}</td>
              <td style={{ padding: 8, fontSize: 12, color: "#6b7280" }}>{c.analyzer}</td>
              <td style={{ padding: 8 }}>
                <span style={{ padding: "2px 8px", borderRadius: 4, fontSize: 11,
                  background: c.f1 >= 0.6 ? "#dcfce7" : c.f1 >= 0.3 ? "#fef3c7" : "#fee2e2",
                  color: c.f1 >= 0.6 ? "#16a34a" : c.f1 >= 0.3 ? "#ca8a04" : "#dc2626" }}>
                  {c.f1 >= 0.6 ? "Good" : c.f1 >= 0.3 ? "Fair" : "Poor"}
                </span>
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      {data.history?.length > 0 && (
        <>
          <h2 style={{ fontSize: 18, fontWeight: 600, margin: "24px 0 12px" }}>Evaluation History</h2>
          <table style={{ width: "100%", borderCollapse: "collapse" }}>
            <thead><tr style={{ borderBottom: "2px solid #e5e7eb", textAlign: "left" }}>
              <th style={{ padding: 8 }}>Date</th><th style={{ padding: 8 }}>Precision</th><th style={{ padding: 8 }}>Recall</th><th style={{ padding: 8 }}>F1</th>
            </tr></thead>
            <tbody>{data.history.map((h: any, i: number) => (
              <tr key={i} style={{ borderBottom: "1px solid #f3f4f6" }}>
                <td style={{ padding: 8, fontSize: 13 }}>{h.evaluated_at?.slice(0, 19) || "?"}</td>
                <td style={{ padding: 8 }}>{(h.precision*100).toFixed(0)}%</td>
                <td style={{ padding: 8 }}>{(h.recall*100).toFixed(0)}%</td>
                <td style={{ padding: 8, fontWeight: 600 }}>{h.f1.toFixed(3)}</td>
              </tr>
            ))}</tbody>
          </table>
        </>
      )}
    </div>
  );
}
