"""SARIF 2.1.0 output for GitHub Code Scanning integration."""

import json
from src.core.types import ReviewResult, PullRequest


def render_sarif(result: ReviewResult, pr: PullRequest) -> str:
    rules = {}
    results_list = []

    for f in result.findings:
        rule_id = f"ai-pr-reviewer/{f.category}/{f.severity}"
        if rule_id not in rules:
            rules[rule_id] = {
                "id": rule_id,
                "name": f"{f.category.title()} - {f.severity.title()}",
                "shortDescription": {"text": f"AI-detected {f.category} issue"},
                "helpUri": "https://github.com/yxd-xxl/ai-pr-reviewer",
            }

        region = {}
        if f.location.line:
            region["startLine"] = f.location.line
        if f.location.end_line:
            region["endLine"] = f.location.end_line

        results_list.append({
            "ruleId": rule_id,
            "level": _map_level(f.severity),
            "message": {"text": f"{f.title}: {f.description}"},
            "locations": [{
                "physicalLocation": {
                    "artifactLocation": {"uri": f.location.file},
                    "region": region,
                }
            }],
            "properties": {
                "confidence": f.confidence,
                "classification": f.classification,
                "suggestion": f.suggestion,
            },
        })

    sarif = {
        "$schema": "https://raw.githubusercontent.com/oasis-tcs/sarif-spec/master/Schemata/sarif-schema-2.1.0.json",
        "version": "2.1.0",
        "runs": [{
            "tool": {
                "driver": {
                    "name": "AI PR Reviewer",
                    "informationUri": "https://github.com/yxd-xxl/ai-pr-reviewer",
                    "rules": list(rules.values()),
                }
            },
            "results": results_list,
        }],
    }

    return json.dumps(sarif, indent=2, ensure_ascii=False)


def _map_level(severity: str) -> str:
    return {
        "critical": "error",
        "high": "error",
        "medium": "warning",
        "low": "note",
    }.get(severity, "warning")


def upload_sarif_to_code_scanning(token: str, owner: str, repo: str,
                                   sarif_json: str, commit_sha: str = "HEAD") -> dict:
    """Upload SARIF results to GitHub Code Scanning API."""
    import urllib.request
    body = json.dumps({
        "commit_sha": commit_sha,
        "ref": "refs/heads/main",
        "sarif": sarif_json,
    }).encode()
    url = f"https://api.github.com/repos/{owner}/{repo}/code-scanning/sarifs"
    req = urllib.request.Request(url, data=body, headers={
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "Content-Type": "application/json",
        "User-Agent": "ai-pr-reviewer",
    }, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read())
    except Exception as e:
        return {"error": str(e)}
