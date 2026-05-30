import { useMemo } from "react";
import type { Finding } from "../types";

interface DiffViewerProps {
  diff: string;
  findings?: Finding[];
  fileName?: string;
}

interface DiffLine {
  type: "add" | "remove" | "context" | "header";
  content: string;
  oldLine?: number;
  newLine?: number;
}

function parseDiff(diff: string): DiffLine[] {
  const lines: DiffLine[] = [];
  let oldLine = 0;
  let newLine = 0;

  for (const line of diff.split("\n")) {
    if (line.startsWith("@@")) {
      const match = line.match(/@@ -(\d+)(?:,\d+)? \+(\d+)(?:,\d+)? @@/);
      if (match) {
        oldLine = parseInt(match[1]);
        newLine = parseInt(match[2]);
      }
      lines.push({ type: "header", content: line });
    } else if (line.startsWith("+") && !line.startsWith("+++")) {
      newLine++;
      lines.push({ type: "add", content: line, newLine });
    } else if (line.startsWith("-") && !line.startsWith("---")) {
      oldLine++;
      lines.push({ type: "remove", content: line, oldLine });
    } else {
      oldLine++;
      newLine++;
      lines.push({ type: "context", content: line, oldLine, newLine });
    }
  }
  return lines;
}

function getFindingsAtLine(findings: Finding[], file: string, line: number): Finding[] {
  return findings.filter(
    (f) => f.location.file === file && f.location.line === line
  );
}

const severityColors: Record<string, string> = {
  critical: "#dc2626",
  high: "#ea580c",
  medium: "#ca8a04",
  low: "#2563eb",
};

export default function DiffViewer({ diff, findings = [], fileName = "" }: DiffViewerProps) {
  const lines = useMemo(() => parseDiff(diff), [diff]);

  return (
    <div style={{ fontFamily: "monospace", fontSize: 13, lineHeight: "20px", overflow: "auto" }}>
      {lines.map((line, i) => {
        const lineFindings = line.newLine
          ? getFindingsAtLine(findings, fileName, line.newLine)
          : [];

        const bgColor =
          line.type === "add"
            ? "#dcfce7"
            : line.type === "remove"
            ? "#fee2e2"
            : line.type === "header"
            ? "#dbeafe"
            : "transparent";

        return (
          <div
            key={i}
            style={{
              backgroundColor: bgColor,
              display: "flex",
              minHeight: 20,
              position: "relative",
            }}
          >
            <span style={{ width: 50, textAlign: "right", color: "#9ca3af", paddingRight: 8, userSelect: "none", flexShrink: 0 }}>
              {line.newLine ?? (line.oldLine ?? "")}
            </span>
            <span style={{ flex: 1, whiteSpace: "pre-wrap", wordBreak: "break-all" }}>
              {line.content}
            </span>
            {lineFindings.map((f, j) => (
              <span
                key={j}
                title={`[${f.severity}] ${f.title}: ${f.description}`}
                style={{
                  position: "absolute",
                  right: 4,
                  top: 0,
                  width: 10,
                  height: 10,
                  borderRadius: "50%",
                  backgroundColor: severityColors[f.severity] || "#9ca3af",
                  cursor: "pointer",
                }}
              />
            ))}
          </div>
        );
      })}
    </div>
  );
}
