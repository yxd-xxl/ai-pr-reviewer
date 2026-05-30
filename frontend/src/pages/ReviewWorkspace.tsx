import { useParams } from "react-router-dom";
import DiffViewer from "../components/DiffViewer";

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

export default function ReviewWorkspace() {
  const { owner, repo, number } = useParams();

  return (
    <div style={{ display: "flex", height: "100vh" }}>
      <aside style={{ width: 280, borderRight: "1px solid #e5e7eb", padding: 16, overflow: "auto" }}>
        <h3>Files</h3>
        <p style={{ color: "#6b7280", fontSize: 14 }}>greet.py</p>
      </aside>
      <main style={{ flex: 1, overflow: "auto", padding: 16 }}>
        <h2>
          {owner}/{repo}#{number}
        </h2>
        <DiffViewer diff={sampleDiff} fileName="greet.py" />
      </main>
      <aside style={{ width: 340, borderLeft: "1px solid #e5e7eb", padding: 16 }}>
        <h3>Findings</h3>
        <p style={{ color: "#6b7280", fontSize: 14 }}>Select a finding to view details.</p>
      </aside>
    </div>
  );
}
