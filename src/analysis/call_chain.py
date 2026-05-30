"""Cross-file call chain analysis — build call graphs, find callers, compute impact."""

import re
from dataclasses import dataclass, field

from src.core.types import FileChange

_IMPORT_RE = re.compile(r'(?:from\s+(\S+)\s+)?import\s+(\S+)')
_FUNC_DEF_RE = re.compile(r'^\s*def\s+(\w+)\s*\(')
_FUNC_CALL_RE = re.compile(r'(\w+)\.(\w+)\s*\(|(\w+)\s*\(')


@dataclass
class CallGraph:
    nodes: dict[str, list[str]] = field(default_factory=dict)  # module -> [imports]
    functions: dict[str, list[str]] = field(default_factory=dict)  # func -> [callers]
    edges: list[tuple[str, str]] = field(default_factory=list)  # (caller, callee)

    def add_edge(self, caller: str, callee: str):
        self.edges.append((caller, callee))
        self.functions.setdefault(callee, []).append(caller)


def build_call_graph(files: list[FileChange]) -> CallGraph:
    """Build a call graph from changed files. Parses imports and function calls."""
    graph = CallGraph()

    for fc in files:
        if fc.is_binary or fc.status == "removed":
            continue

        content = fc.full_content or fc.diff
        module_name = fc.path.replace("/", ".").replace(".py", "").replace(".ts", "").replace(".js", "")

        # Parse imports
        imports = _IMPORT_RE.findall(content)
        for from_mod, imported in imports:
            node = from_mod or imported.split(".")[0]
            graph.nodes.setdefault(module_name, []).append(node)

        # Parse function definitions
        funcs = _FUNC_DEF_RE.findall(content)
        for func_name in funcs:
            graph.functions.setdefault(f"{module_name}.{func_name}", [])

        # Parse function calls (basic)
        calls = _FUNC_CALL_RE.findall(content)
        for obj, method, standalone in calls:
            callee = f"{obj}.{method}" if obj else standalone
            if callee:
                for func_name in funcs:
                    graph.add_edge(f"{module_name}.{func_name}", callee)

    return graph


def find_callers(function_name: str, graph: CallGraph) -> list[str]:
    """Find all callers of a function in the call graph."""
    return graph.functions.get(function_name, [])


def compute_impact(function_name: str, graph: CallGraph) -> int:
    """Compute impact score (number of callers) for a function."""
    return len(find_callers(function_name, graph))


def generate_call_chain_context(fc: FileChange, graph: CallGraph) -> str:
    """Generate prompt context describing which callers may be affected."""
    if fc.is_binary or fc.status == "removed":
        return ""

    module_name = fc.path.replace("/", ".").replace(".py", "").replace(".ts", "").replace(".js", "")
    funcs = _FUNC_DEF_RE.findall(fc.full_content or fc.diff)

    if not funcs:
        return ""

    lines = ["The following callers may be affected by changes in this file:", ""]
    for func_name in funcs:
        full_name = f"{module_name}.{func_name}"
        callers = find_callers(full_name, graph)
        if callers:
            lines.append(f"  - {full_name}: called by {', '.join(callers[:5])}")
        else:
            lines.append(f"  - {full_name}: no known callers")
    return "\n".join(lines)
