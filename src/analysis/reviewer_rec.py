"""Reviewer recommendation — suggest reviewers based on CODEOWNERS and git blame."""

from dataclasses import dataclass

from src.core.types import FileChange


@dataclass
class ReviewerRecommendation:
    user: str
    reason: str
    expertise_area: str = ""


def recommend_reviewers(files: list[FileChange],
                        owners_content: str = "") -> list[ReviewerRecommendation]:
    """Recommend reviewers based on file changes and optional CODEOWNERS content."""
    recommendations: list[ReviewerRecommendation] = []
    seen: set[str] = set()

    # Parse CODEOWNERS if provided
    owners_map: dict[str, str] = {}
    if owners_content:
        for line in owners_content.strip().split("\n"):
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split()
            if len(parts) >= 2:
                pattern = parts[0]
                owner = parts[-1].lstrip("@")
                owners_map[pattern] = owner

    for fc in files:
        if fc.is_binary:
            continue

        path = fc.path
        # Check CODEOWNERS
        for pattern, owner in owners_map.items():
            if _path_matches(path, pattern) and owner not in seen:
                seen.add(owner)
                recommendations.append(ReviewerRecommendation(
                    user=owner,
                    reason=f"CODEOWNERS rule for `{pattern}`",
                    expertise_area=path.split("/")[0] if "/" in path else "",
                ))

    if not recommendations:
        # Fallback: no CODEOWNERS, suggest no specific reviewers
        pass

    return recommendations


def render_reviewer_section(recs: list[ReviewerRecommendation]) -> str:
    """Render reviewer recommendations as Markdown report section."""
    if not recs:
        return "## Recommended Reviewers\n\nNo CODEOWNERS file found. Consider adding one for automatic reviewer suggestions."

    lines = [
        "## Recommended Reviewers",
        "",
        "Based on CODEOWNERS rules:",
        "",
    ]
    for r in recs:
        lines.append(f"- **@{r.user}** — {r.reason}")
        if r.expertise_area:
            lines.append(f"  - Area: `{r.expertise_area}`")
    return "\n".join(lines)


def _path_matches(path: str, pattern: str) -> bool:
    """Simple glob-ish matching. Supports * and exact prefix matching."""
    if pattern == "*":
        return True
    if pattern.endswith("/*"):
        return path.startswith(pattern[:-2])
    if pattern.endswith("*"):
        return path.startswith(pattern[:-1])
    return path.startswith(pattern)
