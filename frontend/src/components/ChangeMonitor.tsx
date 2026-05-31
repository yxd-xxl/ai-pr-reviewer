import { useState, useEffect } from "react";

const API = "http://localhost:8000";

interface Props {
  owner: string;
  repo: string;
  token: string;
}

export default function ChangeMonitor({ owner, repo, token }: Props) {
  const [checking, setChecking] = useState(true);
  const [changes, setChanges] = useState<any>(null);
  const [proposal, setProposal] = useState<any>(null);
  const [creating, setCreating] = useState(false);

  useEffect(() => { checkChanges(); }, []);

  async function checkChanges() {
    setChecking(true);
    try {
      const r = await fetch(`${API}/api/v1/check-changes?owner=${owner}&repo=${repo}`, {
        method: "POST", headers: { Authorization: `Bearer ${token}` },
      });
      const d = await r.json();
      setChanges(d);
      if (d.has_changes) {
        const r2 = await fetch(`${API}/api/v1/generate-proposal?owner=${owner}&repo=${repo}`, {
          method: "POST", headers: { Authorization: `Bearer ${token}` },
        });
        const d2 = await r2.json();
        setProposal(d2.proposal);
      }
    } catch {}
    setChecking(false);
  }

  async function createPR() {
    if (!proposal) return;
    setCreating(true);
    try {
      const r = await fetch(`${API}/api/v1/create-pr?owner=${owner}&repo=${repo}&title=${encodeURIComponent(proposal.suggested_title)}&description=${encodeURIComponent(proposal.suggested_description || "")}`, {
        method: "POST", headers: { Authorization: `Bearer ${token}` },
      });
      const d = await r.json();
      if (d.url) window.open(d.url, "_blank");
    } catch {}
    setCreating(false);
  }

  if (checking) return <div style={{ padding: 12, color: "#9ca3af", fontSize: 13 }}>Checking for new commits...</div>;
  if (!changes?.has_changes) return (
    <div style={{ padding: 12, fontSize: 13, color: "#6b7280" }}>
      {changes?.commit_count ? `${changes.commit_count} commit(s) — below review threshold.` : "No new commits since last review."}
      <button onClick={checkChanges} style={{ marginLeft: 8, background: "none", border: "none", color: "#2563eb", cursor: "pointer", fontSize: 12 }}>Re-check</button>
    </div>
  );

  return (
    <div style={{ padding: 12, background: "#f0fdf4", borderRadius: 8, border: "1px solid #bbf7d0" }}>
      <div style={{ fontWeight: 600, fontSize: 14, color: "#16a34a", marginBottom: 4 }}>
        {changes.commit_count} new commit(s), {changes.files?.length || 0} file(s) changed
      </div>
      {proposal && (
        <div style={{ marginTop: 8 }}>
          <div style={{ fontSize: 13, fontWeight: 600 }}>Proposed PR: {proposal.suggested_title}</div>
          <div style={{ fontSize: 12, color: "#6b7280", marginTop: 4 }}>{proposal.suggested_description?.slice(0, 200)}</div>
          {changes.files && (
            <div style={{ marginTop: 4, fontSize: 11, color: "#9ca3af" }}>
              Files: {changes.files.map((f: any) => f.path).join(", ")}
            </div>
          )}
          <div style={{ marginTop: 8, display: "flex", gap: 8 }}>
            <button onClick={createPR} disabled={creating}
              style={{ padding: "4px 12px", borderRadius: 6, border: "none", background: "#16a34a", color: "#fff", cursor: "pointer", fontSize: 12 }}>
              {creating ? "Creating..." : "Create PR from Changes"}
            </button>
            <button onClick={checkChanges}
              style={{ padding: "4px 12px", borderRadius: 6, border: "1px solid #d1d5db", background: "#fff", cursor: "pointer", fontSize: 12 }}>
              Dismiss
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
