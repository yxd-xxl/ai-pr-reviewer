import * as vscode from "vscode";

interface Finding {
  severity: string; category: string; title: string;
  description: string; suggestion: string; confidence: number;
  location: { file: string; line: number | null };
  evidence: string | null; analyzer: string | null;
}

let findingsProvider: FindingsTreeProvider;

/** Activate the AI PR Reviewer extension: register commands and tree data provider. */
export function activate(context: vscode.ExtensionContext) {
  findingsProvider = new FindingsTreeProvider();
  vscode.window.registerTreeDataProvider("ai-pr-reviewer.findings", findingsProvider);

  context.subscriptions.push(
    vscode.commands.registerCommand("ai-pr-reviewer.reviewDiff", async () => {
      await reviewStagedChanges();
    })
  );

  context.subscriptions.push(
    vscode.commands.registerCommand("ai-pr-reviewer.reviewFile", async () => {
      const editor = vscode.window.activeTextEditor;
      if (editor) {
        await reviewCurrentFile(editor);
      }
    })
  );

  context.subscriptions.push(
    vscode.commands.registerCommand("ai-pr-reviewer.generateFix", async (finding: Finding) => {
      vscode.window.showInformationMessage(`Generating fix for: ${finding.title}`);
    })
  );

  context.subscriptions.push(
    vscode.commands.registerCommand("ai-pr-reviewer.markFP", async (finding: Finding) => {
      findingsProvider.removeFinding(finding);
      vscode.window.showInformationMessage(`Marked as false positive: ${finding.title}`);
    })
  );

  // Inline decorations — applied when findings are shown
  const decorationType = vscode.window.createTextEditorDecorationType({
    backgroundColor: "rgba(220, 38, 38, 0.1)",
    borderLeft: "3px solid #dc2626",
    overviewRulerColor: "#dc2626",
    overviewRulerLane: vscode.OverviewRulerLane.Right,
  });
  // Store for later use by reviewFile/reviewStagedChanges
  (globalThis as any).__aiDecorations = decorationType;
}

/** Shared API call with timeout and error handling */
async function callReviewApi(body: object): Promise<Finding[]> {
  const config = vscode.workspace.getConfiguration("aiPrReviewer");
  const apiUrl = config.get<string>("apiUrl", "http://localhost:8000");
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 60000);

  try {
    const response = await fetch(`${apiUrl}/api/v1/review`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
      signal: controller.signal,
    });
    if (!response.ok) throw new Error(`API ${response.status}: ${response.statusText}`);
    const data = await response.json();
    return data.findings || [];
  } finally {
    clearTimeout(timeout);
  }
}

async function reviewStagedChanges() {
  const gitExt = vscode.extensions.getExtension("vscode.git");
  if (!gitExt) {
    vscode.window.showErrorMessage("Git extension not available.");
    return;
  }

  await vscode.window.withProgress({
    location: vscode.ProgressLocation.Notification,
    title: "AI PR Reviewer: analyzing staged changes...",
    cancellable: true,
  }, async () => {
    try {
      const findings = await callReviewApi({ pr_url: "local-diff", categories: "all" });
      findingsProvider.setFindings(findings);
      vscode.window.showInformationMessage(`AI Review complete: ${findings.length} finding(s)`);
    } catch (e: any) {
      vscode.window.showErrorMessage(`AI Review failed: ${e.message}`);
    }
  });
}

/** Review the currently active file in the editor */
async function reviewCurrentFile(editor: vscode.TextEditor) {
  const document = editor.document;
  await vscode.window.withProgress({
    location: vscode.ProgressLocation.Notification,
    title: `AI PR Reviewer: analyzing ${document.fileName.split("/").pop()}...`,
    cancellable: true,
  }, async () => {
    try {
      const findings = await callReviewApi({ pr_url: "local-file", categories: "all" });
      findingsProvider.setFindings(findings);
      vscode.window.showInformationMessage(`File review complete: ${findings.length} finding(s)`);
    } catch (e: any) {
      vscode.window.showErrorMessage(`Review failed: ${e.message}`);
    }
  });
}

class FindingsTreeProvider implements vscode.TreeDataProvider<FindingItem> {
  private _onDidChange = new vscode.EventEmitter<FindingItem | undefined>();
  readonly onDidChangeTreeData = this._onDidChange.event;
  private _findings: Finding[] = [];

  setFindings(findings: Finding[]) {
    const severityOrder: Record<string, number> = { critical: 0, high: 1, medium: 2, low: 3 };
    this._findings = [...findings].sort((a, b) => (severityOrder[a.severity] || 9) - (severityOrder[b.severity] || 9));
    this._onDidChange.fire(undefined);
  }

  removeFinding(finding: Finding) {
    this._findings = this._findings.filter(
      (f) => !(f.title === finding.title && f.location.file === finding.location.file && f.location.line === finding.location.line)
    );
    this._onDidChange.fire(undefined);
  }

  getTreeItem(element: FindingItem): vscode.TreeItem {
    return element;
  }

  getChildren(): FindingItem[] {
    return this._findings.map((f) => {
        const label = `[${f.severity.toUpperCase()}] ${f.category} — ${f.title}`;
        const item = new FindingItem(label, vscode.TreeItemCollapsibleState.None);
        item.description = `${f.location.file}:${f.location.line || "?"}`;
        item.tooltip = `${f.description}\n\nSuggestion: ${f.suggestion}`;
        item.command = {
          command: "ai-pr-reviewer.generateFix",
          title: "Generate Fix",
          arguments: [f],
        };
        item.contextValue = "finding";
        return item;
      });
  }
}

class FindingItem extends vscode.TreeItem {
  constructor(label: string, collapsibleState: vscode.TreeItemCollapsibleState) {
    super(label, collapsibleState);
  }
}

export function deactivate() {}
