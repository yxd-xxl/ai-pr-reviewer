export interface Finding {
  severity: "critical" | "high" | "medium" | "low";
  category: string;
  location: { file: string; line: number | null };
  title: string;
  description: string;
  suggestion: string;
  confidence: number;
  evidence: string | null;
  fix_patch: string | null;
  fix_verified: boolean;
  analyzer: string | null;
}

export interface ReviewResult {
  summary: string;
  findings: Finding[];
  metadata: Record<string, unknown>;
  warnings: string[];
}

export interface PullRequest {
  owner: string;
  repo: string;
  number: number;
  title: string;
  url: string;
  author: string | null;
}
