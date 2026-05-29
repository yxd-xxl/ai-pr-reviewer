"""Streamlit Dashboard for AI PR Reviewer."""

import os
import streamlit as st

from src.pipeline import run_review
from src.store.db import ReviewRepo
from src.delivery.markdown import render_markdown
from src.delivery.github_delivery import GitHubDelivery
from src.feedback.tracker import FeedbackTracker
from src.core.config import ReviewConfig


st.set_page_config(page_title="AI PR Reviewer", layout="wide")
st.title("AI PR Reviewer")

tab = st.sidebar.radio("View", ["Analyze", "History"], index=0)

# ── Sidebar ──────────────────────────────────

st.sidebar.header("Configuration")

token = st.sidebar.text_input("GitHub Token", type="password",
                               value=os.getenv("GITHUB_TOKEN", ""),
                               help="GitHub Personal Access Token")

_providers = ["mock", "deepseek", "anthropic", "openai"]
_default_provider = os.getenv("LLM_PROVIDER", "mock")
_default_idx = _providers.index(_default_provider) if _default_provider in _providers else 0
llm_provider = st.sidebar.selectbox("LLM Provider", _providers, index=_default_idx)

if llm_provider != "mock":
    for key, label in [("llm_key", "LLM API Key"), ("llm_base", "LLM Base URL"), ("llm_model", "LLM Model")]:
        if key not in st.session_state:
            st.session_state[key] = os.getenv(key.upper().replace("LLM_", "LLM_"), "")
    st.sidebar.text_input("LLM API Key", type="password", key="llm_key")
    st.sidebar.text_input("LLM Base URL", key="llm_base")
    st.sidebar.text_input("LLM Model", key="llm_model")

st.sidebar.divider()

# Review mode
mode = st.sidebar.selectbox("Review Mode", ["balanced", "fast", "deep"], index=0,
                             help="fast=security+bug only | balanced=all perspectives | deep=full verification")

llm_config = None
if llm_provider != "mock":
    llm_config = {"provider": llm_provider, "api_key": st.session_state.get("llm_key", ""),
                  "base_url": st.session_state.get("llm_base", ""), "model": st.session_state.get("llm_model", "")}

# ── Analyze Tab ─────────────────────────────

if tab == "Analyze":
    pr_url = st.text_input("PR URL", placeholder="https://github.com/owner/repo/pull/42")

    col1, col2 = st.columns([3, 1])
    with col2:
        categories = st.selectbox("Focus", ["all", "security", "bug", "performance", "style"], index=0)

    if st.button("Analyze", type="primary", disabled=not token or not pr_url):
        if not token or not token.strip():
            st.error("Please enter your GitHub Token in the sidebar.")
        elif not pr_url:
            st.error("Please enter a PR URL.")
        else:
            try:
                config = ReviewConfig(mode=mode)
                with st.spinner("Fetching PR and running analysis..."):
                    pr, files, result = run_review(pr_url, token.strip(), llm_config=llm_config,
                                                   categories=categories, config=config)
            except Exception as e:
                st.error(f"Pipeline error: {e}")
                st.stop()

            # ── PR Info ───────────────────
            st.header(pr.title)
            st.caption(f"[{pr.owner}/{pr.repo}#{pr.number}]({pr.url}) · "
                       f"by {pr.author} · {pr.base_branch} ← {pr.head_branch}")

            # ── Stats ─────────────────────
            sev = {}
            for f in result.findings:
                sev[f.severity] = sev.get(f.severity, 0) + 1
            c1, c2, c3, c4, c5 = st.columns(5)
            c1.metric("Files", len(files))
            c2.metric("Findings", len(result.findings))
            c3.metric("Critical", sev.get("critical", 0))
            c4.metric("High", sev.get("high", 0))
            c5.metric("Medium", sev.get("medium", 0))

            # ── Summary ───────────────────
            st.divider()
            with st.expander("Summary", expanded=True):
                st.markdown(result.summary)

            # ── Findings ──────────────────
            st.divider()
            st.subheader(f"Findings ({len(result.findings)})")

            sev_emoji = {"critical": "🔴", "high": "🟠", "medium": "🟡", "low": "🔵"}
            tracker = FeedbackTracker()

            for i, f in enumerate(result.findings):
                emoji = sev_emoji.get(f.severity, "⚪")
                fp_label = " ⚠️ KNOWN FP" if tracker.is_known_fp(f) else ""
                with st.expander(f"{emoji} [{f.severity.upper()}] `{f.category}` — {f.title}{fp_label}", expanded=f.severity in ("critical", "high")):
                    c_left, c_right = st.columns([3, 1])
                    with c_left:
                        st.markdown(f"**File:** `{f.location.file}`" + (f":{f.location.line}" if f.location.line else ""))
                        st.markdown(f"**Confidence:** {f.confidence:.0%} · **Classification:** {f.classification}")
                    with c_right:
                        st.markdown(f"`{f.severity}` · `{f.category}`")

                    st.markdown(f"**Description:** {f.description}")
                    if f.evidence:
                        st.code(f.evidence, language="python" if f.location.file.endswith(".py") else None)
                    st.markdown(f"**Suggestion:** {f.suggestion}")

                    # Fix patch
                    if f.fix_patch:
                        verified = "✅ Verified" if f.fix_verified else "⚠️ Unverified"
                        with st.expander(f"Fix Patch ({verified})", expanded=False):
                            st.code(f.fix_patch, language="diff")

                    # Actions row
                    col_a, col_b, col_c = st.columns(3)
                    with col_a:
                        if st.button(f"Mark as FP", key=f"fp_{i}"):
                            tracker.mark_fp(f)
                            st.success("Marked as false positive")
                            st.rerun()
                    with col_b:
                        if st.button(f"Mark as TP", key=f"tp_{i}"):
                            tracker.mark_tp(f)
                            st.success("Marked as true positive")
                            st.rerun()
                    with col_c:
                        question = st.text_input("Ask about this", key=f"q_{i}", placeholder="Why?")
                        if question and st.button("Ask", key=f"ask_{i}"):
                            from src.analysis.llm_analyzer import LLMAnalyzer
                            from src.llm import create_adapter
                            from src.core.types import ReviewContext as RCtx
                            ctx = RCtx(pr=pr, files=files)
                            adapter = create_adapter()
                            analyzer = LLMAnalyzer(adapter)
                            resp = analyzer.followup(f, question, ctx)
                            st.info(resp.get("answer", "No answer"))

            # ── Warnings/Errors ────────────
            if result.warnings or result.errors:
                st.divider()
                for w in result.warnings:
                    st.warning(w)
                for e in result.errors:
                    st.error(e)

            # ── Markdown Preview ──────────
            st.divider()
            with st.expander("Markdown Report", expanded=False):
                st.markdown(render_markdown(result))

            # ── GitHub Dry-Run ────────────
            with st.expander("GitHub Comment Preview"):
                delivery = GitHubDelivery(token=token.strip(), dry_run=True)
                for a in delivery.deliver(result, pr):
                    st.code(a, language=None)

            # ── Timing ─────────────────────
            timing = result.metadata.get("timing", {})
            st.caption(f"Fetch {timing.get('fetch','?')}s | Analyze {timing.get('analyze','?')}s | "
                       f"Post {timing.get('postprocess','?')}s | Total {timing.get('total','?')}s · "
                       f"Analyzer: {result.metadata.get('analyzer','?')} · Model: {result.metadata.get('model','?')}")

# ── History Tab ────────────────────────────

if tab == "History":
    st.subheader("Review History")
    db = ReviewRepo()
    rows = db.get_history(limit=30)
    if not rows:
        st.info("No review history yet. Run an analysis first.")
    else:
        c1, c2, c3 = st.columns(3)
        c1.metric("Total Reviews", len(rows))
        c2.metric("Total Findings", sum(r["findings_count"] for r in rows))
        avg = sum(r["risk_score"] for r in rows) / len(rows) if len(rows) else 0
        c3.metric("Avg Risk", f"{avg:.0f}/100")
        st.divider()
        for r in rows:
            with st.expander(f"{r['pr_title'][:80]} | {r['findings_count']} findings | risk {r['risk_score']}"):
                st.caption(f"{r['repo']} | {r['created_at'][:19]}")
                st.markdown(f"[Open PR]({r['pr_url']})")
                for f in db.get_findings(r["id"]):
                    st.markdown(f"- **[{f['severity']}]** {f['title']} (`{f['file']}`)")
        db.close()
