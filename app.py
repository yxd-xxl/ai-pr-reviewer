"""Streamlit Dashboard for AI PR Reviewer."""

import os, json, time
import streamlit as st

from src.pipeline import run_review
from src.store.db import ReviewRepo
from src.delivery.markdown import render_markdown
from src.delivery.github_delivery import GitHubDelivery
from src.feedback.tracker import FeedbackTracker
from src.core.config import ReviewConfig
from src.context.user_profile import get_user_profile, list_user_repos
from src.context.change_detector import ChangeDetector


st.set_page_config(page_title="AI PR Reviewer", layout="wide")

# ── Sidebar ──────────────────────────────────

with st.sidebar:
    st.header("AI PR Reviewer")
    tab = st.radio("", ["Analyze", "History", "Settings"], index=0,
                    format_func=lambda x: {"Analyze": "Analyze", "History": "History", "Settings": "Settings"}[x])

    st.divider()

    token = st.text_input("GitHub Token", type="password",
                          value=os.getenv("GITHUB_TOKEN", ""))

    if token and token.strip():
        with st.spinner():
            user = get_user_profile(token.strip())
        if user:
            st.success(f"Connected: **{user.get('login')}**")
        else:
            st.error("Invalid token")

    st.divider()

    _providers = ["mock", "deepseek"]
    llm_provider = st.selectbox("LLM", _providers,
                                index=0 if os.getenv("LLM_PROVIDER", "mock") == "mock" else 1)

    if llm_provider != "mock":
        for key in ["llm_key", "llm_base", "llm_model"]:
            if key not in st.session_state:
                st.session_state[key] = os.getenv(key.upper(), "")
        st.text_input("API Key", type="password", key="llm_key")
        st.text_input("Base URL", key="llm_base")
        st.text_input("Model", key="llm_model")

    mode = st.selectbox("Review Mode", ["balanced", "fast", "deep"],
                        help="fast=security+bug | balanced=all | deep=full verify")

    permission = st.selectbox("Permission", ["review-only", "selective-fix", "auto-fix"],
                              help="review-only=read | selective=choose | auto=full")

    st.divider()
    st.caption("22 PRs · 136 tests · 6 perspectives")

llm_config = None
if llm_provider != "mock":
    llm_config = {"provider": llm_provider, "api_key": st.session_state.get("llm_key", ""),
                  "base_url": st.session_state.get("llm_base", ""), "model": st.session_state.get("llm_model", "")}

# ── Analyze Tab ─────────────────────────────

if tab == "Analyze":
    col_url, col_focus = st.columns([3, 1])
    with col_url:
        pr_url = st.text_input("PR URL", placeholder="https://github.com/owner/repo/pull/42")
    with col_focus:
        categories = st.selectbox("Focus", ["all", "security", "bug", "performance", "style"])

    # Repo quick-select
    if token and token.strip():
        with st.expander("Or pick from your repos"):
            repos_list = list_user_repos(token.strip(), per_page=10)
            if repos_list:
                cols = st.columns(4)
                for i, r in enumerate(repos_list[:8]):
                    with cols[i % 4]:
                        if st.button(f"{r['full_name']}", key=f"repo_{i}"):
                            # Check for open PRs
                            import urllib.request as _ur
                            url = f"https://api.github.com/repos/{r['full_name']}/pulls?state=open&per_page=1"
                            req = _ur.Request(url, headers={"Authorization": f"Bearer {token.strip()}",
                                                             "Accept": "application/vnd.github+json",
                                                             "User-Agent": "ai-pr-reviewer"})
                            try:
                                with _ur.urlopen(req, timeout=10) as resp:
                                    prs = json.loads(resp.read())
                                if prs:
                                    st.session_state["pr_url"] = prs[0]["html_url"]
                                    st.rerun()
                                else:
                                    st.info(f"No open PRs in {r['full_name']}")
                            except Exception:
                                st.warning("Could not fetch PRs")

    if "pr_url" in st.session_state and not pr_url:
        pr_url = st.session_state.pop("pr_url")

    if st.button("Analyze", type="primary", disabled=not token or not pr_url):
        if not token or not token.strip():
            st.error("Enter GitHub Token in sidebar.")
        elif not pr_url:
            st.error("Enter PR URL.")
        else:
            with st.spinner("Fetching PR and running analysis..."):
                try:
                    config = ReviewConfig(mode=mode, permission=permission)
                    pr, files, result = run_review(pr_url, token.strip(), llm_config=llm_config,
                                                   categories=categories, config=config)
                except Exception as e:
                    st.error(f"Error: {e}")
                    st.stop()

            # Stats row
            sev = {}
            for f in result.findings:
                sev[f.severity] = sev.get(f.severity, 0) + 1
            c1, c2, c3, c4, c5 = st.columns(5)
            c1.metric("Files", len(files))
            c2.metric("Findings", len(result.findings))
            c3.metric("Critical", sev.get("critical", 0))
            c4.metric("High", sev.get("high", 0))
            c5.metric("Medium", sev.get("medium", 0))

            st.subheader(pr.title)
            st.caption(f"[{pr.owner}/{pr.repo}#{pr.number}]({pr.url}) · "
                       f"{pr.author} · {pr.base_branch} ← {pr.head_branch}")

            with st.expander("Summary", expanded=True):
                st.markdown(result.summary)

            # Findings with checkboxes
            st.divider()
            st.subheader(f"Findings ({len(result.findings)})")
            sev_emoji = {"critical": "🔴", "high": "🟠", "medium": "🟡", "low": "🔵"}
            tracker = FeedbackTracker()

            selected = []
            for i, f in enumerate(result.findings):
                emoji = sev_emoji.get(f.severity, "⚪")
                fp_warn = " ⚠️ KNOWN FP" if tracker.is_known_fp(f) else ""
                is_checked = st.checkbox(
                    f"{emoji} [{f.severity.upper()}] `{f.category}` — {f.title}{fp_warn}",
                    key=f"sel_{i}", value=f.fix_patch is not None and f.fix_verified)
                if is_checked:
                    selected.append(i)

                with st.expander("Details", expanded=f.severity in ("critical", "high")):
                    st.markdown(f"**File:** `{f.location.file}`" +
                                (f":{f.location.line}" if f.location.line else ""))
                    st.markdown(f"**Confidence:** {f.confidence:.0%} · **{f.classification}**")
                    st.markdown(f"**Description:** {f.description}")
                    if f.evidence:
                        st.code(f.evidence, language="python" if f.location.file.endswith(".py") else None)
                    st.markdown(f"**Suggestion:** {f.suggestion}")

                    if f.fix_patch:
                        v = "✅ Verified" if f.fix_verified else "⚠️ Unverified"
                        with st.expander(f"Fix Patch ({v})"):
                            st.code(f.fix_patch, language="diff")

                    ca, cb, cc = st.columns(3)
                    with ca:
                        if st.button("Mark FP", key=f"fp_{i}"):
                            tracker.mark_fp(f); st.rerun()
                    with cb:
                        if st.button("Mark TP", key=f"tp_{i}"):
                            tracker.mark_tp(f); st.rerun()
                    with cc:
                        q = st.text_input("Ask", key=f"q_{i}", placeholder="Why?")
                        if q and st.button("Go", key=f"go_{i}"):
                            from src.analysis.llm_analyzer import LLMAnalyzer
                            from src.llm import create_adapter
                            from src.core.types import ReviewContext as RCtx
                            a = create_adapter(); an = LLMAnalyzer(a)
                            resp = an.followup(f, q, RCtx(pr=pr, files=files))
                            st.info(resp.get("answer", "No answer"))

            # Batch fix section
            if selected:
                st.divider()
                st.markdown(f"**{len(selected)} finding(s) selected**")
                if permission == "review-only":
                    st.info("Permission is 'review-only'. Change to 'selective-fix' in sidebar to enable fixes.")
                else:
                    if st.button(f"Generate Fix PR for {len(selected)} finding(s)", type="primary"):
                        from src.delivery.pr_generator import generate_fix_pr
                        indices = selected
                        actions = generate_fix_pr(result, pr, token.strip(),
                                                  finding_indices=indices, dry_run=True)
                        for a in actions:
                            st.code(a, language=None)
                        if st.button("CONFIRM — Create Fix PR", type="secondary"):
                            actions = generate_fix_pr(result, pr, token.strip(),
                                                      finding_indices=indices, dry_run=False)
                            for a in actions:
                                st.success(a)

            # Warnings / Errors / GitHub preview
            if result.warnings:
                st.divider()
                for w in result.warnings:
                    st.warning(w)
            if result.errors:
                for e in result.errors:
                    st.error(e)

            with st.expander("Markdown Report + GitHub Preview"):
                st.markdown(render_markdown(result))
                delivery = GitHubDelivery(token=token.strip(), dry_run=True)
                for a in delivery.deliver(result, pr):
                    st.code(a, language=None)

            timing = result.metadata.get("timing", {})
            st.caption(f"Fetch {timing.get('fetch','?')}s | Analyze {timing.get('analyze','?')}s | "
                       f"Post {timing.get('postprocess','?')}s | Total {timing.get('total','?')}s · "
                       f"Mode: {mode} · Permission: {permission}")

# ── History Tab ────────────────────────────

if tab == "History":
    st.subheader("Review History")
    db = ReviewRepo()
    rows = db.get_history(limit=50)
    if not rows:
        st.info("No reviews yet.")
    else:
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Reviews", len(rows))
        c2.metric("Findings", sum(r["findings_count"] for r in rows))
        avg = sum(r["risk_score"] for r in rows) / len(rows) if len(rows) else 0
        c3.metric("Avg Risk", f"{avg:.0f}/100")
        c4.metric("Modes", ", ".join(sorted(set(r["mode"] for r in rows))[:3]))
        st.divider()
        for r in rows:
            with st.expander(f"{r['pr_title'][:80]} | {r['findings_count']} findings | risk {r['risk_score']} | {r['mode']}"):
                st.caption(f"{r['repo']} | {r['created_at'][:19]} | {r['categories']}")
                st.markdown(f"[Open PR]({r['pr_url']})")
                for f in db.get_findings(r["id"]):
                    st.markdown(f"- **[{f['severity']}]** {f['title']} (`{f['file']}`)")
        db.close()

# ── Settings Tab ────────────────────────────

if tab == "Settings":
    st.subheader("Project Configuration")
    try:
        import yaml
        if st.button("Generate .ai-pr-reviewer.yml"):
            config = {
                "review": {"mode": "balanced", "min_confidence": 0.65,
                           "max_inline_comments": 10,
                           "categories": ["security","bug","performance","architecture","style"],
                           "auto_fix_categories": ["security","bug"],
                           "permission": "review-only"},
                "conventions": [".claude/CLAUDE.md"],
                "delivery": {"mode": "dry-run", "inline_comments": True, "summary_comment": True},
            }
            st.code(yaml.dump(config, default_flow_style=False, sort_keys=False), language="yaml")
            st.caption("Copy to .ai-pr-reviewer.yml in your repo root")

        if os.path.exists(".ai-pr-reviewer.yml"):
            with open(".ai-pr-reviewer.yml") as f:
                st.code(f.read(), language="yaml")
    except ImportError:
        st.info("PyYAML not installed — config preview unavailable")

    st.divider()
    st.subheader("Quick Start Commands")
    st.code("""# CLI review
python -m src.cli.main review <PR_URL> --categories security

# Auto-detect changes
python -m src.cli.main auto owner/repo

# Generate fix PR (dry-run)
python -m src.cli.main fix <PR_URL>

# Ask about a finding
python -m src.cli.main ask <PR_URL> --finding 1 --question "Why?"

# View history
python -m src.cli.main history
python -m src.cli.main trends

# Profile
python -m src.cli.main profile
python -m src.cli.main repos
""", language="bash")

    st.divider()
    st.subheader("Architecture")
    st.markdown("""
| Layer | Modules |
|-------|---------|
| Core | types, config, confidence |
| Context | GitHub/GitLab client, diff parser, conventions, change detector |
| Analysis | 6-perspective LLM, security, registry, mode, followup, fix, verify |
| Delivery | Markdown, GitHub inline, SARIF, PR generator, webhook |
| PostProcess | filter, dedup, evidence gate, feedback gate |
| Store | SQLite review repository |
| Security | Bandit SAST pre-filter |
| Langs | Python, JS/TS, Go plugin registry |
""")

    st.divider()
    st.caption("22 PRs · 136 tests · 6 CLI commands")
