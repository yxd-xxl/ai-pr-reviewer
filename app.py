"""Streamlit Dashboard for AI PR Reviewer — pure display layer."""

import os

import streamlit as st

from src.pipeline import run_review
from src.delivery.markdown import render_markdown
from src.delivery.github_delivery import GitHubDelivery


st.set_page_config(page_title="AI PR Reviewer", layout="wide")
st.title("AI PR Reviewer")

# ── Sidebar ──────────────────────────────────

st.sidebar.header("Configuration")

token = st.sidebar.text_input("GitHub Token", type="password",
                               value=os.getenv("GITHUB_TOKEN", ""),
                               help="GitHub Personal Access Token (repo scope)")

_providers = ["mock", "deepseek", "anthropic", "openai"]
_default_provider = os.getenv("LLM_PROVIDER", "mock")
_default_idx = _providers.index(_default_provider) if _default_provider in _providers else 0
llm_provider = st.sidebar.selectbox(
    "LLM Provider",
    _providers,
    index=_default_idx,
    help="mock = no API key needed",
)

if llm_provider != "mock":
    if "llm_key" not in st.session_state:
        st.session_state["llm_key"] = os.getenv("LLM_API_KEY", "")
    if "llm_base" not in st.session_state:
        st.session_state["llm_base"] = os.getenv("LLM_BASE_URL", "")
    if "llm_model" not in st.session_state:
        st.session_state["llm_model"] = os.getenv("LLM_MODEL", "")

    st.sidebar.text_input("LLM API Key", type="password", key="llm_key")
    st.sidebar.text_input("LLM Base URL", key="llm_base")
    st.sidebar.text_input("LLM Model", key="llm_model")

st.sidebar.divider()
st.sidebar.caption("Mock mode works without any tokens or keys.")

# ── Build LLM config from sidebar (pass to pipeline, never touch os.environ) ─

llm_config: dict | None = None
if llm_provider != "mock":
    llm_config = {
        "provider": llm_provider,
        "api_key": st.session_state.get("llm_key", ""),
        "base_url": st.session_state.get("llm_base", ""),
        "model": st.session_state.get("llm_model", ""),
    }

# ── Main ─────────────────────────────────────

pr_url = st.text_input("PR URL", placeholder="https://github.com/owner/repo/pull/42")

col1, col2 = st.columns([3, 1])
with col2:
    categories = st.selectbox(
        "Focus", ["all", "security", "bug", "performance", "style"],
        index=0, help="Analysis dimension"
    )

if st.button("Analyze", type="primary", disabled=not token or not pr_url):
    if not token or not token.strip():
        st.error("Please enter your GitHub Token in the sidebar.")
    elif not pr_url:
        st.error("Please enter a PR URL.")
    else:
        try:
            with st.spinner("Fetching PR and running analysis..."):
                pr, files, result = run_review(
                    pr_url, token.strip(), llm_config=llm_config,
                    categories=categories,
                )
        except Exception as e:
            msg = str(e)
            if "401" in msg or "Bad credentials" in msg:
                st.error(
                    "GitHub authentication failed. Check your token:\n\n"
                    "1. Go to GitHub → Settings → Developer settings → "
                    "Personal access tokens\n"
                    "2. Ensure the token has 'repo' scope\n"
                    "3. Paste the token in the sidebar"
                )
            else:
                st.error(f"Pipeline error: {e}")
            st.stop()

        # ── PR Info ───────────────────────────
        st.header(pr.title)
        st.caption(f"[{pr.owner}/{pr.repo}#{pr.number}]({pr.url}) · "
                   f"by {pr.author} · {pr.base_branch} ← {pr.head_branch}")

        # ── Stats ─────────────────────────────
        col1, col2, col3, col4 = st.columns(4)
        sev = {}
        for f in result.findings:
            sev[f.severity] = sev.get(f.severity, 0) + 1
        col1.metric("Files", len(files))
        col2.metric("Findings", len(result.findings))
        col3.metric("Critical", sev.get("critical", 0), delta_color="inverse")
        col4.metric("High", sev.get("high", 0), delta_color="inverse")

        # ── Summary ───────────────────────────
        st.divider()
        st.subheader("Summary")
        st.markdown(result.summary)

        # ── Findings ──────────────────────────
        if result.findings:
            st.divider()
            st.subheader(f"Findings ({len(result.findings)})")

            sev_emoji = {
                "critical": "🔴", "high": "🟠",
                "medium": "🟡", "low": "🔵",
            }

            for i, f in enumerate(result.findings):
                emoji = sev_emoji.get(f.severity, "⚪")
                with st.expander(
                    f"{emoji} [{f.severity.upper()}] `{f.category}` — {f.title}",

                ):
                    c1, c2 = st.columns(2)
                    with c1:
                        st.markdown(f"**File:** `{f.location.file}`"
                                    + (f":{f.location.line}" if f.location.line else ""))
                        st.markdown(f"**Confidence:** {f.confidence:.0%}")
                    with c2:
                        st.markdown(f"**Severity:** `{f.severity}`")
                        st.markdown(f"**Category:** `{f.category}`")

                    st.markdown(f"**Description:** {f.description}")
                    if f.evidence:
                        st.code(f.evidence, language="python" if
                                f.location.file.endswith(".py") else None)
                    st.markdown(f"**Suggestion:** {f.suggestion}")

        # ── Warnings / Errors ─────────────────
        if result.warnings or result.errors:
            st.divider()
            if result.warnings:
                st.subheader("Warnings")
                for w in result.warnings:
                    st.warning(w)
            if result.errors:
                st.subheader("Errors")
                for e in result.errors:
                    st.error(e)

        # ── Markdown Preview ──────────────────
        st.divider()
        with st.expander("Markdown Report Preview"):
            st.markdown(render_markdown(result))

        # ── GitHub Dry-Run ────────────────────
        st.divider()
        with st.expander("GitHub Comment Preview (dry-run)"):
            delivery = GitHubDelivery(token=token, dry_run=True)
            actions = delivery.deliver(result, pr)
            for a in actions:
                st.code(a, language=None)

        # ── Metadata ──────────────────────────
        st.divider()
        timing = result.metadata.get("timing", {})
        st.caption(
            "Fetch {}s | Analyze {}s | Post {}s | Total {}s".format(
                timing.get("fetch","?"), timing.get("analyze","?"),
                timing.get("postprocess","?"), timing.get("total","?"))
        )
        st.caption(f"Analyzer: {result.metadata.get('analyzer', '?')} · "
                   f"Model: {result.metadata.get('model', '?')}")
