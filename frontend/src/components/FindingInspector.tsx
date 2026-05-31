import { useState } from "react";
import type { Finding } from "../types";

interface Props {
  finding: Finding | null;
  onFeedback: (fingerprint: string, state: string) => void;
  onAskFollowup: (fingerprint: string, question: string) => void;
}

const severityColors: Record<string, string> = {
  critical: "#dc2626", high: "#ea580c", medium: "#ca8a04", low: "#2563eb",
};

const FEEDBACK_STATES = [
  { value: "tp", label: "True Positive" },
  { value: "fp", label: "False Positive" },
  { value: "wont_fix", label: "Won't Fix" },
  { value: "duplicate", label: "Duplicate" },
  { value: "fixed", label: "Fixed" },
  { value: "dismissed", label: "Dismiss" },
];

export default function FindingInspector({ finding, onFeedback, onAskFollowup }: Props) {
  const [question, setQuestion] = useState("");
  const [feedbackState, setFeedbackState] = useState("");

  if (!finding) {
    return (
      <div style={{ padding: 16, color: "#9ca3af" }}>
        <p>Select a finding to view details.</p>
      </div>
    );
  }

  const fp = `${finding.location.file}:${finding.location.line}:${finding.title}`;

  return (
    <div style={{ padding: 16, overflow: "auto", height: "100%" }}>
      <h3 style={{ color: severityColors[finding.severity] }}>
        [{finding.severity.toUpperCase()}] {finding.category}
      </h3>
      <h4>{finding.title}</h4>

      <div style={{ marginTop: 12 }}>
        <strong>Location:</strong> {finding.location.file}
        {finding.location.line ? `:${finding.location.line}` : ""}
      </div>
      <div style={{ marginTop: 8 }}>
        <strong>Confidence:</strong> {(finding.confidence * 100).toFixed(0)}%
      </div>
      <div style={{ marginTop: 8 }}>
        <strong>Analyzer:</strong> {finding.analyzer || "unknown"}
      </div>

      <div style={{ marginTop: 16, padding: 12, background: "#f3f4f6", borderRadius: 8 }}>
        <p><strong>Description:</strong></p>
        <p>{finding.description}</p>
      </div>

      {finding.evidence && (
        <div style={{ marginTop: 12 }}>
          <strong>Evidence:</strong>
          <pre style={{ background: "#1e293b", color: "#e2e8f0", padding: 12, borderRadius: 6, fontSize: 12, overflow: "auto" }}>
            {finding.evidence}
          </pre>
        </div>
      )}

      <div style={{ marginTop: 16, padding: 12, background: "#f0fdf4", borderRadius: 8 }}>
        <p><strong>Suggestion:</strong></p>
        <p>{finding.suggestion}</p>
      </div>

      {finding.fix_patch && (
        <div style={{ marginTop: 12 }}>
          <strong>Fix Patch {finding.fix_verified ? "(Verified)" : "(Unverified)"}:</strong>
          <pre style={{ background: "#1e293b", color: "#e2e8f0", padding: 12, borderRadius: 6, fontSize: 12, overflow: "auto" }}>
            {finding.fix_patch}
          </pre>
        </div>
      )}

      <div style={{ marginTop: 20, borderTop: "1px solid #e5e7eb", paddingTop: 16 }}>
        <strong>Feedback:</strong>
        <select
          value={feedbackState}
          onChange={(e) => {
            setFeedbackState(e.target.value);
            if (e.target.value) onFeedback(fp, e.target.value);
          }}
          style={{ marginLeft: 8, padding: 4 }}
        >
          <option value="">Mark as...</option>
          {FEEDBACK_STATES.map((s) => (
            <option key={s.value} value={s.value}>{s.label}</option>
          ))}
        </select>
      </div>

      <div style={{ marginTop: 16 }}>
        <strong>Ask Follow-up:</strong>
        <input
          type="text"
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          placeholder="Is this really a bug?"
          style={{ width: "100%", padding: 8, marginTop: 4, borderRadius: 4, border: "1px solid #d1d5db" }}
          onKeyDown={(e) => {
            if (e.key === "Enter" && question.trim()) {
              onAskFollowup(fp, question);
              setQuestion("");
            }
          }}
        />
      </div>

      {finding.fix_patch && (
        <div style={{ marginTop: 16, borderTop: "1px solid #e5e7eb", paddingTop: 16 }}>
          <button onClick={() => {
            navigator.clipboard.writeText(finding.fix_patch || "");
            alert("Fix patch copied to clipboard. Apply it in your editor.");
          }}
            style={{ width: "100%", padding: "10px", borderRadius: 8, border: "none",
              background: finding.fix_verified ? "#16a34a" : "#2563eb", color: "#fff",
              cursor: "pointer", fontSize: 14, fontWeight: 600 }}>
            {finding.fix_verified ? "Apply Verified Fix" : "Copy Fix Patch"}
          </button>
          {!finding.fix_verified && (
            <p style={{ fontSize: 11, color: "#9ca3af", marginTop: 4, textAlign: "center" }}>
              This fix has not been independently verified. Review carefully.
            </p>
          )}
        </div>
      )}
    </div>
  );
}
