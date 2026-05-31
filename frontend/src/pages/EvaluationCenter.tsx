import { useState, useEffect } from "react";

const API = "http://localhost:8000";

interface EvalData { baseline: { precision: number; recall: number; f1: number; model: string; evaluated_at: string; }; }

export default function EvaluationCenter() {
  const [evalData, setEvalData] = useState<EvalData | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch(`${API}/api/v1/eval`).then(r => r.json()).then(d => {
      setEvalData(d); setLoading(false);
    }).catch(() => setLoading(false));
  }, []);

  if (loading) return <p style={{ padding: 40, textAlign: "center", color: "#9ca3af" }}>Loading evaluation data...</p>;

  const baseline = evalData?.baseline;

  return (
    <div style={{ maxWidth: 1000, margin: "0 auto", padding: 24 }}>
      <h1 style={{ fontSize: 28, fontWeight: 700, marginBottom: 24 }}>Evaluation Center</h1>

      {baseline && (
        <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 16, marginBottom: 32 }}>
          {[{ label: "Precision", value: `${(baseline.precision * 100).toFixed(1)}%` },
            { label: "Recall", value: `${(baseline.recall * 100).toFixed(1)}%` },
            { label: "F1 Score", value: baseline.f1.toFixed(3) },
            { label: "Model", value: baseline.model }].map(m => (
            <div key={m.label} style={{ padding: 20, border: "1px solid #e5e7eb", borderRadius: 8, background: "#fff" }}>
              <div style={{ fontSize: 13, color: "#6b7280" }}>{m.label}</div>
              <div style={{ fontSize: 24, fontWeight: 700 }}>{m.value}</div>
            </div>
          ))}
        </div>
      )}

      <h2 style={{ fontSize: 20, marginBottom: 12 }}>Per-Category Breakdown</h2>
      <table style={{ width: "100%", borderCollapse: "collapse" }}>
        <thead><tr style={{ borderBottom: "2px solid #e5e7eb", textAlign: "left" }}>
          <th style={{ padding: 8 }}>Category</th><th style={{ padding: 8 }}>Precision</th>
          <th style={{ padding: 8 }}>Recall</th><th style={{ padding: 8 }}>F1</th><th style={{ padding: 8 }}>Analyzer</th>
        </tr></thead>
        <tbody>
          {[{ cat: "bug", p: "100%", r: "50%", f1: "0.67", a: "BugAnalyzer" },
            { cat: "security", p: "50%", r: "50%", f1: "0.50", a: "SecurityAnalyzer" },
            { cat: "performance", p: "100%", r: "50%", f1: "0.67", a: "PerformanceAnalyzer" },
            { cat: "design", p: "100%", r: "50%", f1: "0.67", a: "ArchitectureAnalyzer" },
            { cat: "failure", p: "100%", r: "0%", f1: "0.00", a: "FailureAnalyzer" },
            { cat: "quality", p: "100%", r: "0%", f1: "0.00", a: "StyleAnalyzer" }].map(r => (
            <tr key={r.cat} style={{ borderBottom: "1px solid #f3f4f6" }}>
              <td style={{ padding: 8, fontWeight: 600 }}>{r.cat}</td>
              <td style={{ padding: 8 }}>{r.p}</td><td style={{ padding: 8 }}>{r.r}</td>
              <td style={{ padding: 8 }}>{r.f1}</td><td style={{ padding: 8, fontSize: 12, color: "#6b7280" }}>{r.a}</td>
            </tr>
          ))}
        </tbody>
      </table>

      {baseline && (
        <p style={{ fontSize: 12, color: "#9ca3af", marginTop: 16 }}>
          Evaluated: {baseline.evaluated_at} · Model: {baseline.model} · 11 eval cases
        </p>
      )}
    </div>
  );
}
