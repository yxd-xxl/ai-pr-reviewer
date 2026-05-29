import re
from src.core.types import FileChange, DiffHunk

_HEADER_RE = re.compile(r"^diff --git a/(.+) b/(.+)$")
_HUNK_RE = re.compile(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@(.*)")
_RENAME_RE = re.compile(r"^rename (?:from|to) (.+)$")


def parse_unified_diff(diff_text: str) -> list[FileChange]:
    if not diff_text.strip():
        return []

    raw_files = _split_by_file(diff_text)
    return [_parse_one_file(chunks) for chunks in raw_files]


def _split_by_file(diff_text: str) -> list[list[str]]:
    result: list[list[str]] = []
    current: list[str] = []
    for line in diff_text.split("\n"):
        if _HEADER_RE.match(line) and current:
            result.append(current)
            current = []
        current.append(line)
    if current:
        result.append(current)
    return result


def _parse_one_file(lines: list[str]) -> FileChange:
    header = lines[0]
    m = _HEADER_RE.match(header)
    old_path = m.group(1) if m else ""
    new_path = m.group(2) if m else ""

    path = new_path
    status = "modified"
    old_path_final: str | None = None
    is_binary = False

    for line in lines[1:]:
        if line.startswith("rename from "):
            status = "renamed"
            old_path_final = _RENAME_RE.match(line).group(1) if _RENAME_RE.match(line) else line
        elif line.startswith("new file"):
            status = "added"
        elif line.startswith("deleted file"):
            status = "removed"
        elif "Binary files" in line:
            is_binary = True

    if is_binary:
        return FileChange(
            path=path, status=status, language="", diff="\n".join(lines),
            old_path=old_path_final, is_binary=True,
        )

    hunks: list[DiffHunk] = []
    additions = 0
    deletions = 0

    i = 0
    while i < len(lines):
        hm = _HUNK_RE.match(lines[i])
        if hm:
            old_start = int(hm.group(1))
            old_lines = int(hm.group(2)) if hm.group(2) else 1
            new_start = int(hm.group(3))
            new_lines = int(hm.group(4)) if hm.group(4) else 1
            hunk_lines: list[str] = [lines[i]]
            i += 1
            while i < len(lines) and not _HUNK_RE.match(lines[i]) and not _HEADER_RE.match(lines[i]):
                hunk_lines.append(lines[i])
                if lines[i].startswith("+") and not lines[i].startswith("+++"):
                    additions += 1
                elif lines[i].startswith("-") and not lines[i].startswith("---"):
                    deletions += 1
                i += 1
            hunks.append(DiffHunk(
                old_start=old_start, old_lines=old_lines,
                new_start=new_start, new_lines=new_lines,
                content="\n".join(hunk_lines),
            ))
        else:
            i += 1

    # Detect language from extension (using registry)
    from src.langs.registry import detect_language
    language = detect_language(path)

    return FileChange(
        path=path, status=status, language=language,
        diff="\n".join(lines), hunks=hunks,
        old_path=old_path_final, is_binary=False,
        additions=additions, deletions=deletions,
    )
