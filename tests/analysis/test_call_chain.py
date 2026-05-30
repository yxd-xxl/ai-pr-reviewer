"""Tests for cross-file call chain analysis."""

from src.analysis.call_chain import (
    CallGraph, build_call_graph, find_callers, compute_impact, generate_call_chain_context,
)
from src.core.types import FileChange


def _make_file(path="src/app.py", content="", status="modified"):
    return FileChange(
        path=path, status=status, language="python",
        diff=content, additions=1, deletions=0, full_content=content,
    )


class TestCallGraph:
    def test_add_edge(self):
        g = CallGraph()
        g.add_edge("mod.foo", "mod.bar")
        assert ("mod.foo", "mod.bar") in g.edges
        assert "mod.bar" in g.functions
        assert "mod.foo" in g.functions["mod.bar"]


class TestBuildCallGraph:
    def test_parses_imports(self):
        fc = _make_file("src/app.py", "import os\nfrom utils import helper\n")
        g = build_call_graph([fc])
        assert "src.app" in g.nodes

    def test_parses_function_defs(self):
        fc = _make_file("src/app.py", "def greet():\n    pass\n")
        g = build_call_graph([fc])
        assert "src.app.greet" in g.functions

    def test_skips_binary(self):
        fc = _make_file("img.png", "", "added")
        fc.is_binary = True
        g = build_call_graph([fc])
        assert g.nodes == {}

    def test_skips_removed(self):
        fc = _make_file("old.py", "def old():\n    pass\n", "removed")
        g = build_call_graph([fc])
        assert g.nodes == {}


class TestFindCallers:
    def test_no_callers(self):
        g = CallGraph()
        assert find_callers("unknown", g) == []

    def test_finds_callers(self):
        g = CallGraph()
        g.add_edge("a.foo", "b.bar")
        assert "a.foo" in find_callers("b.bar", g)


class TestComputeImpact:
    def test_zero_impact(self):
        g = CallGraph()
        assert compute_impact("unknown", g) == 0

    def test_one_caller(self):
        g = CallGraph()
        g.add_edge("a.foo", "b.bar")
        assert compute_impact("b.bar", g) == 1


class TestGenerateContext:
    def test_generates_for_modified_function(self):
        fc = _make_file("src/handler.py", "def handle():\n    process()\n")
        g = build_call_graph([fc])
        ctx = generate_call_chain_context(fc, g)
        assert "src.handler.handle" in ctx or "callers" in ctx.lower()

    def test_empty_for_binary(self):
        fc = _make_file("img.png", "", "added")
        fc.is_binary = True
        assert generate_call_chain_context(fc, CallGraph()) == ""
