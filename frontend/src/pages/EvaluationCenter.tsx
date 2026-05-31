import { useState, useEffect } from "react";

const API = "http://localhost:8000";
const COLORS: Record<string, string> = { bug: "#ef4444", security: "#f97316", performance: "#3b82f6", design: "#8b5cf6", failure: "#eab308", quality: "#10b981" };

function F1Bar({ label, value, color, max }: { label: string; value: number; color: string; max: number }) {
  const pct = (value / max) * 100;
  return (
    <div style={{ marginBottom: 14 }}>
      <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 4, fontSize: 13 }}>
        <span style={{ fontWeight: 500 }}>{label}</span>
        <span style={{ fontWeight: 700, color }}>{(value * 100).toFixed(0)}%</span>
      </div>
      <div style={{ height: 12, background: "#f1f5f9", borderRadius: 6, overflow: "hidden" }}>
        <div style={{ height: "100%", width: `${pct}%`, background: color, borderRadius: 6, transition: "width 0.6s ease", minWidth: pct > 0 ? 2 : 0 }} />
      </div>
    </div>
  );
}

const MetricCard = ({ icon, label, value, sub, color }: { icon: string; label: string; value: string; sub: string; color: string }) => (
  <div style={{ padding: "20px 24px", borderRadius: 12, background: "#fff", border: "1px solid #e2e8f0", boxShadow: "0 1px 3px rgba(0,0,0,0.04)" }}>
    <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 10 }}>
      <div style={{ width: 36, height: 36, borderRadius: 10, background: `${color}15`, display: "flex", alignItems: "center", justifyContent: "center", fontSize: 18 }}>{icon}</div>
      <span style={{ fontSize: 13, color: "#64748b", fontWeight: 500 }}>{label}</span>
    </div>
    <div style={{ fontSize: 32, fontWeight: 800, color: "#0f172a", lineHeight: 1 }}>{value}</div>
    <div style={{ fontSize: 12, color: "#94a3b8", marginTop: 4 }}>{sub}</div>
  </div>
);

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

  if (loading) return <p style={{ padding: 60, textAlign: "center", color: "#94a3b8", fontSize: 15 }}>Loading evaluation data…</p>;
  if (!data) return <p style={{ padding: 60, textAlign: "center", color: "#ef4444" }}>Failed to load.</p>;

  const b = data.baseline;
  const cats: any[] = data.categories || [];
  const maxF1 = Math.max(...cats.map(c => c.f1), 0.1);
  const f1Level = b.f1 >= 0.7 ? "Good" : b.f1 >= 0.5 ? "Fair" : "Needs Work";
  const f1Color = b.f1 >= 0.7 ? "#10b981" : b.f1 >= 0.5 ? "#eab308" : "#ef4444";

  return (
    <div style={{ maxWidth: 1040, margin: "0 auto", padding: "28px 24px" }}>
      {/* Header */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 28 }}>
        <div>
          <h1 style={{ fontSize: 26, fontWeight: 700, margin: 0, color: "#0f172a" }}>Evaluation Center</h1>
          <p style={{ color: "#64748b", fontSize: 14, margin: "4px 0 0" }}>Track prompt and model quality over time. {b.total_cases || 11} annotated test cases.</p>
        </div>
        <button onClick={runEval} disabled={running}
          style={{ padding: "10px 22px", borderRadius: 10, border: "none", background: running ? "#cbd5e1" : "#0f172a", color: "#fff", cursor: running ? "default" : "pointer", fontSize: 14, fontWeight: 600, whiteSpace: "nowrap" }}>
          {running ? `Running ${data?.baseline?.total_cases || 3} cases…` : "Run Evaluation"}
        </button>
      </div>

      {runResult && (
        <div style={{ padding: "12px 16px", marginBottom: 20, borderRadius: 10, background: runResult.status === "ok" ? "#f0fdf4" : "#fef2f2", border: `1px solid ${runResult.status === "ok" ? "#bbf7d0" : "#fecaca"}`, color: runResult.status === "ok" ? "#166534" : "#991b1b", fontSize: 13, fontWeight: 500 }}>
          {runResult.status === "ok" ? `Complete — P=${(runResult.precision*100).toFixed(0)}% · R=${(runResult.recall*100).toFixed(0)}% · F1=${runResult.f1.toFixed(3)}` : `Failed: ${runResult.message}`}
        </div>
      )}

      {/* Overall Score Banner */}
      <div style={{ padding: 24, borderRadius: 14, background: "#f8fafc", border: "1px solid #e2e8f0", marginBottom: 24, display: "flex", alignItems: "center", gap: 28 }}>
        <div style={{ textAlign: "center", minWidth: 90 }}>
          <div style={{ fontSize: 44, fontWeight: 800, color: f1Color, lineHeight: 1 }}>{b.f1.toFixed(2)}</div>
          <div style={{ fontSize: 12, color: "#64748b", marginTop: 2 }}>F1 Score</div>
          <div style={{ marginTop: 6, padding: "2px 10px", borderRadius: 20, background: `${f1Color}18`, color: f1Color, fontSize: 11, fontWeight: 600, display: "inline-block" }}>{f1Level}</div>
        </div>
        <div style={{ width: 1, height: 70, background: "#e2e8f0" }} />
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "10px 28px", flex: 1 }}>
          {[{ l: "Precision", v: `${(b.precision*100).toFixed(1)}%`, s: "Correct findings / total found" },
            { l: "Recall", v: `${(b.recall*100).toFixed(1)}%`, s: "Issues found / should have found" },
            { l: "Model", v: b.model, s: "LLM used for evaluation run" },
            { l: "Last Run", v: b.evaluated_at?.slice(0,10), s: `${b.total_cases||11} annotated test cases` }].map(m => (
            <div key={m.l}>
              <div style={{ fontSize: 11, color: "#94a3b8", fontWeight: 600, textTransform: "uppercase", letterSpacing: ".4px", marginBottom: 2 }}>{m.l}</div>
              <div style={{ fontSize: 18, fontWeight: 700, color: "#0f172a" }}>{m.v}</div>
              <div style={{ fontSize: 11, color: "#94a3b8", marginTop: 1 }}>{m.s}</div>
            </div>
          ))}
        </div>
      </div>

      {/* Two-column layout */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 20, marginBottom: 24 }}>
        {/* F1 Chart */}
        <div style={{ padding: 20, borderRadius: 12, background: "#fff", border: "1px solid #e2e8f0" }}>
          <h3 style={{ fontSize: 15, fontWeight: 600, margin: "0 0 18px", color: "#0f172a" }}>F1 Score by Analyzer</h3>
          {cats.map(c => <F1Bar key={c.cat} label={c.analyzer.replace("Analyzer","")} value={c.f1} color={COLORS[c.cat]||"#64748b"} max={maxF1} />)}
        </div>

        {/* Per-category Table */}
        <div style={{ padding: 20, borderRadius: 12, background: "#fff", border: "1px solid #e2e8f0" }}>
          <h3 style={{ fontSize: 15, fontWeight: 600, margin: "0 0 14px", color: "#0f172a" }}>Category Detail</h3>
          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
            <thead><tr style={{ borderBottom: "1px solid #e2e8f0" }}>
              <th style={{ padding: "6px 8px", textAlign: "left", fontWeight: 600, color: "#64748b", fontSize: 11 }}>CATEGORY</th>
              <th style={{ padding: "6px 8px", textAlign: "right", fontWeight: 600, color: "#64748b", fontSize: 11 }}>P</th>
              <th style={{ padding: "6px 8px", textAlign: "right", fontWeight: 600, color: "#64748b", fontSize: 11 }}>R</th>
              <th style={{ padding: "6px 8px", textAlign: "right", fontWeight: 600, color: "#64748b", fontSize: 11 }}>F1</th>
              <th style={{ padding: "6px 8px", textAlign: "right", fontWeight: 600, color: "#64748b", fontSize: 11 }}>STATUS</th>
            </tr></thead>
            <tbody>
              {cats.map(c => (
                <tr key={c.cat} style={{ borderBottom: "1px solid #f1f5f9" }}>
                  <td style={{ padding: "8px", display: "flex", alignItems: "center", gap: 8 }}>
                    <span style={{ width: 8, height: 8, borderRadius: 4, background: COLORS[c.cat], flexShrink: 0 }} />
                    <span style={{ fontWeight: 500 }}>{c.cat}</span>
                  </td>
                  <td style={{ padding: 8, textAlign: "right" }}>{(c.precision*100).toFixed(0)}%</td>
                  <td style={{ padding: 8, textAlign: "right" }}>{(c.recall*100).toFixed(0)}%</td>
                  <td style={{ padding: 8, textAlign: "right", fontWeight: 600, fontFamily: "monospace" }}>{c.f1.toFixed(2)}</td>
                  <td style={{ padding: 8, textAlign: "right" }}>
                    <span style={{ padding: "2px 8px", borderRadius: 12, fontSize: 11, fontWeight: 500,
                      background: c.f1>=0.6?"#f0fdf4":c.f1>=0.3?"#fefce8":"#fef2f2",
                      color: c.f1>=0.6?"#166534":c.f1>=0.3?"#854d0e":"#991b1b" }}>
                      {c.f1>=0.6?"Good":c.f1>=0.3?"Fair":"Poor"}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* History */}
      {data.history?.length > 0 && (
        <div style={{ padding: 20, borderRadius: 12, background: "#fff", border: "1px solid #e2e8f0" }}>
          <h3 style={{ fontSize: 15, fontWeight: 600, margin: "0 0 14px", color: "#0f172a" }}>Run History</h3>
          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
            <thead><tr style={{ borderBottom: "1px solid #e2e8f0" }}>
              <th style={{ padding: "6px 8px", textAlign: "left", color: "#64748b", fontSize: 11, fontWeight: 600 }}>DATE</th>
              <th style={{ padding: "6px 8px", textAlign: "right", color: "#64748b", fontSize: 11, fontWeight: 600 }}>PRECISION</th>
              <th style={{ padding: "6px 8px", textAlign: "right", color: "#64748b", fontSize: 11, fontWeight: 600 }}>RECALL</th>
              <th style={{ padding: "6px 8px", textAlign: "right", color: "#64748b", fontSize: 11, fontWeight: 600 }}>F1</th>
              <th style={{ padding: "6px 8px", textAlign: "right", color: "#64748b", fontSize: 11, fontWeight: 600 }}>Δ</th>
            </tr></thead>
            <tbody>
              {data.history.map((h: any, i: number) => {
                const prev = i > 0 ? data.history[i-1].f1 : h.f1;
                const delta = h.f1 - prev;
                return (
                  <tr key={i} style={{ borderBottom: "1px solid #f1f5f9" }}>
                    <td style={{ padding: 8 }}>{h.evaluated_at?.slice(0,16) || "?"}</td>
                    <td style={{ padding: 8, textAlign: "right" }}>{(h.precision*100).toFixed(0)}%</td>
                    <td style={{ padding: 8, textAlign: "right" }}>{(h.recall*100).toFixed(0)}%</td>
                    <td style={{ padding: 8, textAlign: "right", fontWeight: 600, fontFamily: "monospace" }}>{h.f1.toFixed(3)}</td>
                    <td style={{ padding: 8, textAlign: "right", color: delta >= 0 ? "#10b981" : "#ef4444", fontWeight: 600, fontSize: 12 }}>
                      {i === 0 ? "—" : `${delta >= 0 ? "+" : ""}${(delta*100).toFixed(1)}%`}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
