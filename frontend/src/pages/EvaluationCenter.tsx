interface PromptVersion {
  version: string; category: string; precision: number; recall: number; f1: number; fp: number; fn: number;
}

const mockVersions: PromptVersion[] = [
  { version: "security-v4", category: "security", precision: 0.82, recall: 0.68, f1: 0.74, fp: 3, fn: 4 },
  { version: "security-v5", category: "security", precision: 0.90, recall: 0.72, f1: 0.80, fp: 1, fn: 3 },
  { version: "bug-v3", category: "bug", precision: 0.88, recall: 0.55, f1: 0.68, fp: 2, fn: 5 },
  { version: "failure-v1", category: "failure", precision: 0.85, recall: 0.40, f1: 0.54, fp: 1, fn: 6 },
];

export default function EvaluationCenter() {
  return (
    <div style={{ padding: 24, maxWidth: 1200, margin: "0 auto" }}>
      <h1 style={{ fontSize: 28, fontWeight: 700, marginBottom: 8 }}>Evaluation Center</h1>
      <p style={{ color: "#6b7280", marginBottom: 24 }}>Prompt version comparison and quality metrics.</p>

      <h2 style={{ fontSize: 20, marginBottom: 12 }}>Prompt Versions</h2>
      <table style={{ width: "100%", borderCollapse: "collapse" }}>
        <thead>
          <tr style={{ borderBottom: "2px solid #e5e7eb", textAlign: "left" }}>
            <th style={{ padding: 8 }}>Version</th>
            <th style={{ padding: 8 }}>Category</th>
            <th style={{ padding: 8 }}>Precision</th>
            <th style={{ padding: 8 }}>Recall</th>
            <th style={{ padding: 8 }}>F1</th>
            <th style={{ padding: 8 }}>FP</th>
            <th style={{ padding: 8 }}>FN</th>
          </tr>
        </thead>
        <tbody>
          {mockVersions.map((v) => (
            <tr key={v.version} style={{ borderBottom: "1px solid #f3f4f6" }}>
              <td style={{ padding: 8, fontWeight: 600 }}>{v.version}</td>
              <td style={{ padding: 8 }}>{v.category}</td>
              <td style={{ padding: 8 }}>{(v.precision * 100).toFixed(0)}%</td>
              <td style={{ padding: 8 }}>{(v.recall * 100).toFixed(0)}%</td>
              <td style={{ padding: 8, fontWeight: 600 }}>{v.f1.toFixed(2)}</td>
              <td style={{ padding: 8, color: "#dc2626" }}>{v.fp}</td>
              <td style={{ padding: 8, color: "#ea580c" }}>{v.fn}</td>
            </tr>
          ))}
        </tbody>
      </table>

      <h2 style={{ fontSize: 20, margin: "24px 0 12px" }}>Model Comparison</h2>
      <table style={{ width: "100%", borderCollapse: "collapse" }}>
        <thead>
          <tr style={{ borderBottom: "2px solid #e5e7eb", textAlign: "left" }}>
            <th style={{ padding: 8 }}>Model</th>
            <th style={{ padding: 8 }}>Precision</th>
            <th style={{ padding: 8 }}>Recall</th>
            <th style={{ padding: 8 }}>Avg Latency</th>
            <th style={{ padding: 8 }}>Avg Cost/PR</th>
          </tr>
        </thead>
        <tbody>
          <tr style={{ borderBottom: "1px solid #f3f4f6" }}>
            <td style={{ padding: 8, fontWeight: 600 }}>DeepSeek V4</td>
            <td style={{ padding: 8 }}>88.9%</td>
            <td style={{ padding: 8 }}>36.4%</td>
            <td style={{ padding: 8 }}>89s</td>
            <td style={{ padding: 8 }}>$0.04</td>
          </tr>
          <tr style={{ borderBottom: "1px solid #f3f4f6" }}>
            <td style={{ padding: 8, fontWeight: 600, color: "#9ca3af" }}>Anthropic (planned)</td>
            <td style={{ padding: 8, color: "#9ca3af" }}>—</td>
            <td style={{ padding: 8, color: "#9ca3af" }}>—</td>
            <td style={{ padding: 8, color: "#9ca3af" }}>—</td>
            <td style={{ padding: 8, color: "#9ca3af" }}>—</td>
          </tr>
        </tbody>
      </table>
    </div>
  );
}
