"""AI PR Reviewer — Connect → Repos → PRs → Analyze"""

import os, json
import streamlit as st
import urllib.request as _ur

from src.pipeline import run_review
from src.feedback.tracker import FeedbackTracker
from src.core.config import ReviewConfig
from src.context.user_profile import get_user_profile, list_user_repos
from src.context.change_detector import ChangeDetector


st.set_page_config(page_title="AI PR Reviewer", layout="wide")

for key in ["stage", "token", "user", "selected_repo", "selected_pr"]:
    if key not in st.session_state:
        st.session_state[key] = None if key != "stage" else "connect"


def api_get(url, token):
    req = _ur.Request(url, headers={"Authorization": f"Bearer {token}",
                                     "Accept": "application/vnd.github+json",
                                     "User-Agent": "ai-pr-reviewer"})
    with _ur.urlopen(req, timeout=15) as r:
        return json.loads(r.read())


def fetch_prs(owner, repo, token, state="all", limit=20):
    url = f"https://api.github.com/repos/{owner}/{repo}/pulls?state={state}&per_page={limit}&sort=updated&direction=desc"
    return api_get(url, token)


# ── Stage 1: Connect ────────────────────────

if st.session_state.stage == "connect":
    st.title("AI PR Reviewer")
    st.markdown("Connect your GitHub account to get started.")

    token_input = st.text_input("GitHub Personal Access Token", type="password",
                                placeholder="ghp_... or gho_...",
                                help="GitHub Settings > Developer settings > Tokens (classic) > repo scope")

    c1, c2 = st.columns(2)
    with c1:
        if st.button("Connect", type="primary", disabled=not token_input):
            with st.spinner("Verifying..."):
                user = get_user_profile(token_input.strip())
            if user:
                st.session_state.token = token_input.strip()
                st.session_state.user = user
                st.session_state.stage = "repos"
                st.rerun()
            else:
                st.error("Invalid token.")
    with c2:
        saved = os.getenv("GITHUB_TOKEN", "")
        if saved:
            if st.button("Use Saved Token"):
                user = get_user_profile(saved)
                if user:
                    st.session_state.token = saved
                    st.session_state.user = user
                    st.session_state.stage = "repos"
                    st.rerun()

    st.divider()
    st.caption("Token stays in your browser session — never stored on a server.")

# ── Stage 2: Repos ──────────────────────────

elif st.session_state.stage == "repos":
    st.title("Select Repository")
    user = st.session_state.user
    st.markdown(f"Connected as **{user.get('login')}**")
    if st.button("Disconnect"):
        st.session_state.stage = "connect"; st.rerun()
    st.divider()

    with st.spinner("Loading repositories..."):
        repos_list = list_user_repos(st.session_state.token, per_page=30)

    if not repos_list:
        st.info("No repositories found.")
    else:
        cols = st.columns(3)
        for i, r in enumerate(repos_list):
            with cols[i % 3]:
                priv = "private" if r.get("private") else "public"
                lang = r.get("language") or ""
                issues = r.get("open_issues_count", 0)
                label = f"{r['full_name']}\n{priv} · {lang} · {issues} issues"
                if st.button(label, key=f"repo_{i}", use_container_width=True):
                    st.session_state.selected_repo = r["full_name"]
                    st.session_state.stage = "prs"
                    st.rerun()

# ── Stage 3: Review Queue ─────────────────

elif st.session_state.stage == "prs":
    owner, repo = st.session_state.selected_repo.split("/")
    st.title(f"{owner}/{repo} — Review Queue")

    if st.button("Back to repos"):
        st.session_state.stage = "repos"; st.rerun()
    st.divider()

    # Section 1: Unreviewed Changes (auto-detection)
    st.subheader("Unreviewed Changes")
    detector = ChangeDetector()
    should_review, head_sha, commit_count = detector.check(owner, repo, st.session_state.token)
    if head_sha:
        if commit_count > 0:
            cols = st.columns([3, 1])
            with cols[0]:
                st.markdown(f"**{commit_count} new commit(s)** since last review")
                st.caption(f"HEAD: {head_sha[:7]}")
            with cols[1]:
                if should_review:
                    st.success(f"Threshold met ({commit_count} commits)")
                else:
                    st.info(f"Below threshold ({commit_count} < 3)")
                if st.button("Review Changes", key="review_changes", type="primary"):
                    # Find open PRs or use the latest commit context
                    prs = fetch_prs(owner, repo, st.session_state.token, state="open", limit=1)
                    if prs:
                        st.session_state.selected_pr = prs[0]["html_url"]
                    else:
                        st.session_state.selected_pr = f"https://github.com/{owner}/{repo}"
                    st.session_state.stage = "analyze"
                    st.rerun()
        else:
            st.caption("No new commits since last review.")
    else:
        st.caption("Unable to check for changes.")

    st.divider()

    # Section 2: Pull Requests
    st.subheader("Pull Requests")
    pr_state = st.selectbox("Filter", ["open", "closed", "all"], index=2, key="pr_filter")

    with st.spinner(f"Loading {pr_state} PRs..."):
        prs = fetch_prs(owner, repo, st.session_state.token, state=pr_state)

    if not prs:
        st.info(f"No {pr_state} PRs found.")
    else:
        st.caption(f"{len(prs)} PRs — click to review")
        for i, pr in enumerate(prs):
            cols = st.columns([3, 1, 0.8])
            with cols[0]:
                draft = " [DRAFT]" if pr.get("draft") else ""
                st.markdown(f"**#{pr['number']}**{draft} {pr['title'][:90]}")
                st.caption(f"by {pr['user']['login']} · {pr['state']} · +{pr.get('additions',0)}/-{pr.get('deletions',0)} · {pr.get('changed_files',0)} files")
            with cols[1]:
                st.markdown(f"{pr.get('comments',0)} comments")
            with cols[2]:
                if st.button("Review", key=f"sel_{i}"):
                    st.session_state.selected_pr = pr["html_url"]
                    st.session_state.stage = "analyze"
                    st.rerun()

# ── Stage 4: Analyze ────────────────────────

elif st.session_state.stage == "analyze":
    pr_url = st.session_state.selected_pr
    token = st.session_state.token

    if not pr_url:
        st.info("No PR selected.")
        st.stop()

    with st.sidebar:
        st.subheader("Review Config")
        mode = st.selectbox("Mode", ["balanced", "fast", "deep"])
        permission = st.selectbox("Permission", ["review-only", "selective-fix"])
        categories = st.selectbox("Focus", ["all", "security", "bug", "performance", "style"])
        llm_choice = st.selectbox("LLM", ["mock", "deepseek"],
                                  index=1 if os.getenv("LLM_PROVIDER","mock")!="mock" else 0)
        api_key = ""
        if llm_choice != "mock":
            api_key = st.text_input("API Key", type="password", value=os.getenv("LLM_API_KEY",""))

    if st.sidebar.button("Run Analysis", type="primary", use_container_width=True):
        with st.spinner("Analyzing..."):
            config = ReviewConfig(mode=mode, permission=permission)
            llm_cfg = None
            if llm_choice != "mock" and api_key:
                llm_cfg = {"provider": llm_choice, "api_key": api_key,
                          "base_url": os.getenv("LLM_BASE_URL","https://api.deepseek.com"),
                          "model": os.getenv("LLM_MODEL","deepseek-chat")}
            try:
                pr, files, result = run_review(pr_url, token, llm_config=llm_cfg,
                                               categories=categories, config=config)
                st.session_state.last_result = (pr, files, result)
            except Exception as e:
                st.error(f"Analysis failed: {e}")
                st.stop()

    if "last_result" not in st.session_state:
        st.info("Select config in sidebar and click 'Run Analysis'.")
    else:
        pr, files, result = st.session_state.last_result

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
        st.caption(f"[{pr.owner}/{pr.repo}#{pr.number}]({pr.url}) · {pr.author}")

        with st.expander("Summary", expanded=True):
            st.markdown(result.summary)

        st.divider()
        st.subheader(f"Findings ({len(result.findings)})")
        sev_emoji = {"critical": "🔴", "high": "🟠", "medium": "🟡", "low": "🔵"}
        tracker = FeedbackTracker()
        selected = []

        for i, f in enumerate(result.findings):
            fp_warn = " ⚠️ FP" if tracker.is_known_fp(f) else ""
            label = f"{sev_emoji.get(f.severity,'')} [{f.severity.upper()}] {f.category} — {f.title}{fp_warn}"
            checked = st.checkbox(label, key=f"chk_{i}",
                                  value=f.fix_patch is not None and f.fix_verified)
            if checked:
                selected.append(i)

            with st.expander("Details"):
                st.markdown(f"**{f.location.file}**" + (f":{f.location.line}" if f.location.line else ""))
                st.markdown(f"Confidence: {f.confidence:.0%} · {f.classification}")
                st.markdown(f.description)
                if f.evidence:
                    st.code(f.evidence, language="python" if f.location.file.endswith(".py") else None)
                st.markdown(f"**-> {f.suggestion}**")
                if f.fix_patch:
                    v = "Verified" if f.fix_verified else "Unverified"
                    st.code(f.fix_patch, language="diff")
                    st.caption(v)
                ca, cb = st.columns(2)
                with ca:
                    if st.button("Mark FP", key=f"fp_{i}"): tracker.mark_fp(f); st.rerun()
                with cb:
                    if st.button("Mark TP", key=f"tp_{i}"): tracker.mark_tp(f); st.rerun()

        if selected and permission != "review-only":
            st.divider()
            st.markdown(f"**{len(selected)} selected**")
            if st.button("Generate Fix PR", type="primary"):
                from src.delivery.pr_generator import generate_fix_pr
                actions = generate_fix_pr(result, pr, token, finding_indices=selected, dry_run=True)
                for a in actions:
                    st.code(a, language=None)
                if st.button("CONFIRM — Create Fix PR"):
                    for a in generate_fix_pr(result, pr, token, finding_indices=selected, dry_run=False):
                        st.success(a) if "Created" in a else st.code(a)

        if result.warnings:
            st.divider()
            for w in result.warnings:
                st.warning(w)

        t = result.metadata.get("timing", {})
        st.caption(f"Fetch {t.get('fetch','?')}s | Analyze {t.get('analyze','?')}s | Total {t.get('total','?')}s")

    if st.button("Back to PRs"):
        st.session_state.stage = "prs"
        if "last_result" in st.session_state:
            del st.session_state.last_result
        st.rerun()
