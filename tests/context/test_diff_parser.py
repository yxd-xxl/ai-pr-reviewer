import pytest
from src.context.diff_parser import parse_unified_diff


SAMPLE_DIFF = """diff --git a/src/app.py b/src/app.py
index 1234567..abcdefg 100644
--- a/src/app.py
+++ b/src/app.py
@@ -1,3 +1,5 @@
 def hello():
-    pass
+    print("hello")
+
+def world():
+    return "world"

@@ -10,6 +12,7 @@
 def main():
-    hello()
+    hello()
+    world()
"""


class TestParseUnifiedDiff:
    def test_extracts_file_path(self):
        files = parse_unified_diff(SAMPLE_DIFF)
        assert len(files) == 1
        assert files[0].path == "src/app.py"

    def test_counts_additions_and_deletions(self):
        files = parse_unified_diff(SAMPLE_DIFF)
        f = files[0]
        assert f.additions >= 0
        assert f.deletions >= 0

    def test_extracts_hunks(self):
        files = parse_unified_diff(SAMPLE_DIFF)
        assert len(files[0].hunks) == 2

    def test_hunk_line_numbers(self):
        files = parse_unified_diff(SAMPLE_DIFF)
        h1 = files[0].hunks[0]
        assert h1.old_start == 1
        assert h1.new_start == 1

    def test_empty_diff(self):
        files = parse_unified_diff("")
        assert files == []

    def test_binary_file(self):
        diff = "diff --git a/img.png b/img.png\nBinary files a/img.png and b/img.png differ\n"
        files = parse_unified_diff(diff)
        assert len(files) == 1
        assert files[0].is_binary is True

    def test_renamed_file(self):
        diff = """diff --git a/old.py b/new.py
similarity index 100%
rename from old.py
rename to new.py
"""
        files = parse_unified_diff(diff)
        assert len(files) == 1
        assert files[0].path == "new.py"
        assert files[0].old_path == "old.py"
        assert files[0].status == "renamed"

    def test_multiple_files(self):
        diff = """diff --git a/a.py b/a.py
--- a/a.py
+++ b/a.py
@@ -1,1 +1,1 @@
-old
+new
diff --git a/b.py b/b.py
--- a/b.py
+++ b/b.py
@@ -1,1 +1,1 @@
-old2
+new2
"""
        files = parse_unified_diff(diff)
        assert len(files) == 2
