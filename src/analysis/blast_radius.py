"""Blast radius analysis — compute change impact scope from call graph."""

from dataclasses import dataclass, field

from src.core.types import FileChange
try:
    from src.analysis.call_chain import CallGraph, build_call_graph, find_callers
except ImportError:
    CallGraph = None  # type: ignore
    build_call_graph = None  # type: ignore
    find_callers = None  # type: ignore


@dataclass
class BlastRadius:
    affected_files: list[str] = field(default_factory=list)
    affected_functions: list[str] = field(default_factory=list)
    affected_modules: list[str] = field(default_factory=list)
    risk_level: str = "low"  # low | medium | high | critical

    @property
    def total_affected(self) -> int:
        return len(self.affected_files) + len(self.affected_functions)

    def _compute_level(self):
        n = self.total_affected
        if n < 5:
            self.risk_level = "low"
        elif n < 15:
            self.risk_level = "medium"
        elif n < 30:
            self.risk_level = "high"
        else:
            self.risk_level = "critical"


def compute_blast_radius(files: list[FileChange]) -> BlastRadius:
    """Compute the blast radius of changes by building call graph and tracing impact."""
    if build_call_graph is None:
        return BlastRadius(affected_files=[f.path for f in files if not f.is_binary])

    graph = build_call_graph(files)

    affected_files: set[str] = set()
    affected_functions: set[str] = set()
    affected_modules: set[str] = set()

    for fc in files:
        if fc.is_binary or fc.status == "removed":
            continue

        content = fc.full_content or fc.diff
        module_name = _module_name(fc.path)

        # Parse function definitions in this file
        import re
        funcs = re.findall(r'^\s*def\s+(\w+)\s*\(', content, re.MULTILINE)
        for func_name in funcs:
            full_name = f"{module_name}.{func_name}"
            callers = find_callers(full_name, graph)
            if callers:
                affected_functions.add(full_name)
                affected_functions.update(callers)
                for caller in callers:
                    # Extract module from caller name
                    mod = ".".join(caller.split(".")[:-1])
                    if mod:
                        affected_modules.add(mod)

        # Track affected files through imports
        for node in graph.nodes.get(module_name, []):
            if node != module_name:
                affected_modules.add(node)

    affected_files = {fc.path for fc in files if not fc.is_binary}
    radius = BlastRadius(
        affected_files=sorted(affected_files),
        affected_functions=sorted(affected_functions),
        affected_modules=sorted(affected_modules),
    )
    radius._compute_level()
    return radius


def format_blast_radius_report(radius: BlastRadius) -> str:
    """Render blast radius as a Markdown report section."""
    lines = [
        "## Blast Radius",
        "",
        f"**Risk Level:** {radius.risk_level.upper()}",
        f"**Affected Files:** {len(radius.affected_files)}",
        f"**Affected Functions:** {len(radius.affected_functions)}",
        f"**Affected Modules:** {len(radius.affected_modules)}",
        "",
    ]
    if radius.affected_functions:
        lines.append("### Impacted Functions")
        for fn in radius.affected_functions[:10]:
            lines.append(f"  - `{fn}`")
        if len(radius.affected_functions) > 10:
            lines.append(f"  - ... and {len(radius.affected_functions) - 10} more")
    return "\n".join(lines)


def blast_radius_risk_penalty(radius: BlastRadius) -> int:
    """Compute risk score penalty from blast radius (0-20)."""
    mapping = {"low": 0, "medium": 5, "high": 12, "critical": 20}
    return mapping.get(radius.risk_level, 0)


def _module_name(path: str) -> str:
    return path.replace("/", ".").replace(".py", "").replace(".ts", "").replace(".js", "").replace(".go", "")
