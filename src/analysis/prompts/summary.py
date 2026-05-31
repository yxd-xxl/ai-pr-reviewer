from src.core.types import ReviewContext


_SUMMARY_SYSTEM = """\
You are a senior code reviewer. Write a clear, structured PR summary that any \
developer can understand. Use plain language. Avoid jargon when possible. \
Structure your response with these sections:

## What Changed
Briefly list what files were added/modified and what the PR does.

## Risk Assessment
Which parts of the code are most likely to cause problems? Explain WHY in \
simple terms. Rate each risk area as HIGH/MEDIUM/LOW.

## Recommendation
One sentence: should this be merged as-is, reviewed carefully, or not merged? \
Explain your reasoning in one sentence."""

_SUMMARY_USER = """\
PR: {title}
Description: {description}
Author: {author}
Files changed ({count}):
{file_list}

Write a structured PR summary with the sections above."""


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
