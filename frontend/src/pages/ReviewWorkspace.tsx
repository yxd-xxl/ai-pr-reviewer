import { useState } from "react";
import { useParams } from "react-router-dom";
import DiffViewer from "../components/DiffViewer";
import FindingInspector from "../components/FindingInspector";
import FileTree from "../components/FileTree";
import type { Finding } from "../types";

const sampleDiff = `@@ -1,5 +1,5 @@
 import os
-def greet(name):
-    print("Hello, " + name)
+def greet(name: str) -> None:
+    print(f"Hello, {name}")

-def main():
-    greet("World")
+def main() -> None:
+    greet("World")`;

const sampleFiles = [
  { path: "greet.py", findings: [], critical: 1, high: 0, medium: 1, low: 0 },
  { path: "utils.py", findings: [], critical: 0, high: 1, medium: 0, low: 0 },
];

export default function ReviewWorkspace() {
  const { owner, repo, number } = useParams();
  const [selectedFile, setSelectedFile] = useState<string | null>(null);
  const [selectedFinding, setSelectedFinding] = useState<Finding | null>(null);

  return (
    <div style={{ display: "flex", height: "100vh" }}>
      <aside style={{ width: 280, borderRight: "1px solid #e5e7eb", overflow: "auto" }}>
        <FileTree files={sampleFiles} selectedFile={selectedFile} onSelect={setSelectedFile} />
      </aside>
      <main style={{ flex: 1, overflow: "auto", padding: 16 }}>
        <h2>{owner}/{repo}#{number}</h2>
        <DiffViewer diff={sampleDiff} fileName={selectedFile || "greet.py"} />
      </main>
      <aside style={{ width: 380, borderLeft: "1px solid #e5e7eb" }}>
        <FindingInspector
          finding={selectedFinding}
          onFeedback={(fp, state) => console.log("Feedback:", fp, state)}
          onAskFollowup={(fp, q) => console.log("Followup:", fp, q)}
        />
      </aside>
    </div>
  );
}
