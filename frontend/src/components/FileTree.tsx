import type { Finding } from "../types";

interface FileNode {
  path: string;
  findings: Finding[];
  critical: number;
  high: number;
  medium: number;
  low: number;
}

interface Props {
  files: FileNode[];
  selectedFile: string | null;
  onSelect: (path: string) => void;
}

export default function FileTree({ files, selectedFile, onSelect }: Props) {
  return (
    <div style={{ padding: 8 }}>
      <h4 style={{ padding: "0 8px", marginBottom: 8 }}>Files</h4>
      {files.map((f) => (
        <div
          key={f.path}
          onClick={() => onSelect(f.path)}
          style={{
            padding: "6px 8px",
            cursor: "pointer",
            borderRadius: 4,
            backgroundColor: selectedFile === f.path ? "#dbeafe" : "transparent",
            fontSize: 13,
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
          }}
        >
          <span style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
            {f.path.split("/").pop() || f.path}
          </span>
          <span style={{ display: "flex", gap: 4, fontSize: 11 }}>
            {f.critical > 0 && <span style={{ color: "#dc2626" }}>●{f.critical}</span>}
            {f.high > 0 && <span style={{ color: "#ea580c" }}>●{f.high}</span>}
            {f.medium > 0 && <span style={{ color: "#ca8a04" }}>●{f.medium}</span>}
          </span>
        </div>
      ))}
      {files.length === 0 && (
        <p style={{ color: "#9ca3af", fontSize: 13, padding: 8 }}>No files with findings.</p>
      )}
    </div>
  );
}
