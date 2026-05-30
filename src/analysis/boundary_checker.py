"""Architecture boundary checker — structured rule engine for dependency violations."""

import re
from dataclasses import dataclass, field

from src.core.types import FileChange, Finding, Location


@dataclass
class BoundaryRule:
    name: str
    description: str
    pattern: str          # regex matching import statements
    severity: str = "high"
    message: str = ""


@dataclass
class BoundaryConfig:
    rules: list[BoundaryRule] = field(default_factory=list)
    allowlist: list[str] = field(default_factory=list)


# Built-in default rules
DEFAULT_RULES = [
    BoundaryRule(
        name="no-core-imports-other-modules",
        description="core/ should not depend on other src/ modules (dependency inversion)",
        pattern=r'from\s+src\.(context|analysis|delivery|security|service|store|feedback|cli)',
        severity="high",
        message="Core module importing outer layer — violates hexagonal architecture.",
    ),
    BoundaryRule(
        name="no-feature-cross-imports",
        description="Features should not import each other's internals",
        pattern=r'from\s+\w+\.features\.(?!common)\w+',
        severity="medium",
        message="Cross-feature import detected — consider using shared/common module.",
    ),
    BoundaryRule(
        name="no-circular-imports",
        description="Detect potential circular imports (A imports B, B imports A)",
        pattern=r'',
        severity="high",
        message="Potential circular dependency detected.",
    ),
    BoundaryRule(
        name="no-hardcoded-secrets",
        description="Detect hardcoded API keys, tokens, passwords",
        pattern=r'(?i)(api_key|token|password|secret)\s*=\s*["\'][^"\']+["\']',
        severity="critical",
        message="Hardcoded credential detected — use environment variables or secret manager.",
    ),
]


def load_boundary_config(path: str | None = None) -> BoundaryConfig:
    """Load boundary rules from YAML config file. Falls back to built-in defaults."""
    config = BoundaryConfig(rules=list(DEFAULT_RULES))
    if path is None:
        return config

    try:
        import yaml
        from pathlib import Path
        if not Path(path).exists():
            return config
        with open(path, encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        for rule_data in data.get("rules", []):
            config.rules.append(BoundaryRule(**rule_data))
    except Exception:
        pass
    return config


def check_boundaries(files: list[FileChange],
                     config: BoundaryConfig | None = None) -> list[Finding]:
    """Check changed files against architecture boundary rules."""
    if config is None:
        config = BoundaryConfig(rules=list(DEFAULT_RULES))

    findings: list[Finding] = []

    for fc in files:
        if fc.is_binary or fc.status == "removed":
            continue

        content = fc.full_content or fc.diff

        for rule in config.rules:
            if not rule.pattern:
                continue

            matches = re.finditer(rule.pattern, content, re.MULTILINE)
            for m in matches:
                # Check allowlist
                matched_text = m.group(0)
                if any(allowed in matched_text for allowed in config.allowlist):
                    continue

                line_num = _find_line(content, matched_text)
                findings.append(Finding(
                    severity=rule.severity,
                    category="architecture",
                    location=Location(file=fc.path, line=line_num),
                    title=f"Boundary violation: {rule.name}",
                    description=f"{rule.message}\n\nRule: {rule.description}\n\n"
                               f"Detected: `{matched_text.strip()}`",
                    suggestion="Refactor to comply with architecture rules.",
                    confidence=0.95,
                    evidence=matched_text.strip(),
                    analyzer="boundary-checker",
                    rule_id=rule.name,
                ))

    # Circular import detection
    imports_map: dict[str, set[str]] = {}
    for fc in files:
        if fc.is_binary:
            continue
        mod = _module_name(fc.path)
        content = fc.full_content or fc.diff
        imports = set(re.findall(r'(?:from\s+(\S+)\s+)?import\s+(\S+)', content))
        imports_map[mod] = {f"{f[0]}.{f[1]}" if f[0] else f[1] for f in imports if f[0] or f[1]}

    for mod_a, imports_a in imports_map.items():
        for mod_b, imports_b in imports_map.items():
            if mod_a >= mod_b:
                continue
            if mod_b in imports_a and mod_a in imports_b:
                findings.append(Finding(
                    severity="high",
                    category="architecture",
                    location=Location(file=""),
                    title=f"Circular dependency: {mod_a} <-> {mod_b}",
                    description=f"Modules {mod_a} and {mod_b} import each other.",
                    suggestion="Break the cycle by introducing an interface or shared module.",
                    confidence=0.95,
                    evidence=f"{mod_a} imports {mod_b}, {mod_b} imports {mod_a}",
                    analyzer="boundary-checker",
                ))

    return findings


def _find_line(content: str, snippet: str) -> int | None:
    lines = content.split("\n")
    for i, line in enumerate(lines, 1):
        if snippet.split("\n")[0].strip() in line:
            return i
    return None


def _module_name(path: str) -> str:
    return path.replace("/", ".").replace(".py", "").replace(".ts", "").replace(".js", "")
