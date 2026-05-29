from src.core.types import ReviewContext


_SUMMARY_SYSTEM = """\
You are a senior code reviewer. Analyze the given PR and produce a concise \
summary of what changed and potential risks."""

_SUMMARY_USER = """\
PR: {title}
Description: {description}
Author: {author}
Files changed ({count}):
{file_list}

Write a 3-5 sentence summary of this PR, highlighting:
1. What was changed
2. Which areas carry the most risk
3. Whether the change scope is appropriate for the description"""


def build_summary_prompt(ctx: ReviewContext) -> tuple[str, str]:
    files = "\n".join(f"  - {f.path} ({f.status}, +{f.additions}/-{f.deletions})"
                      for f in ctx.files[:20])
    user = _SUMMARY_USER.format(
        title=ctx.pr.title,
        description=ctx.pr.description or "(none)",
        author=ctx.pr.author or "unknown",
        count=len(ctx.files),
        file_list=files,
    )
    if ctx.conventions:
        conv_text = "\n".join(
            f"### {c.source} ({c.type})\n{c.content}"
            for c in ctx.conventions
        )
        user += f"\n\nProject conventions:\n{conv_text}"
    return _SUMMARY_SYSTEM, user
