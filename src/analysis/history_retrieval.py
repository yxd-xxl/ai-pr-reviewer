"""Historical similar issue retrieval — find past findings similar to current ones."""

from dataclasses import dataclass
from difflib import SequenceMatcher


@dataclass
class SimilarFinding:
    title: str
    file: str
    severity: str
    category: str
    similarity_score: float
    resolution: str = "unknown"
    review_run_id: int = 0


def find_similar_findings(finding_title: str, history: list[dict],
                          min_score: float = 0.6, limit: int = 5) -> list[SimilarFinding]:
    """Find similar past findings by title similarity."""
    results: list[SimilarFinding] = []

    for h in history:
        hist_title = h.get("title", "")
        if not hist_title:
            continue

        score = SequenceMatcher(None, finding_title.lower(), hist_title.lower()).ratio()
        if score >= min_score:
            results.append(SimilarFinding(
                title=hist_title,
                file=h.get("file", ""),
                severity=h.get("severity", "medium"),
                category=h.get("category", ""),
                similarity_score=round(score, 2),
                resolution=h.get("resolution", "unknown"),
                review_run_id=h.get("review_run_id", 0),
            ))

    results.sort(key=lambda r: -r.similarity_score)
    return results[:limit]


def generate_history_context(similar: list[SimilarFinding]) -> str:
    """Generate prompt-ready text describing similar past issues."""
    if not similar:
        return ""

    lines = [
        "Historically, similar issues have been found in this repository:",
        "",
    ]
    for s in similar:
        lines.append(
            f"- [{s.severity.upper()}] {s.title} "
            f"(`{s.file}`, similarity={s.similarity_score:.0%})"
        )
        if s.resolution != "unknown":
            lines.append(f"  - Resolution: {s.resolution}")

    return "\n".join(lines)


def search_repo_history(finding_title: str, repo: str,
                        limit: int = 5) -> list[SimilarFinding]:
    """Search review history in SQLite for similar findings."""
    try:
        from src.store.db import ReviewRepo
        db = ReviewRepo()
        try:
            rows = db.get_history(repo=repo, limit=100)
            all_findings = []
            for r in rows:
                findings = db.get_findings(r["id"])
                for f in findings:
                    f["review_run_id"] = r["id"]
                    all_findings.append(dict(f))
            return find_similar_findings(finding_title, all_findings, limit=limit)
        finally:
            db.close()
    except Exception:
        return []
