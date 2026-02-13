import streamlit as st
import sys
from pathlib import Path

# Add parent directory to path so we can import contract_logger
sys.path.append(str(Path(__file__).parent.parent))
from contract_logger import ContractLogger

st.set_page_config(page_title="AskTheContract — Admin", page_icon="✈️", layout="wide")

# ============================================================
# PROFESSIONAL CSS THEME
# ============================================================
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');

    /* ── Global ── */
    html, body, [class*="css"] {
        font-family: 'DM Sans', -apple-system, BlinkMacSystemFont, sans-serif;
    }
    .stApp {
        background: linear-gradient(180deg, #f8fafc 0%, #ffffff 100%);
    }
    #MainMenu, footer, header { visibility: hidden; }
    .block-container {
        padding-top: 2rem !important;
        max-width: 1200px;
    }

    /* ── Metric cards ── */
    div[data-testid="stMetric"] {
        background: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 10px;
        padding: 1rem 1.25rem;
        text-align: center;
        box-shadow: 0 1px 3px rgba(15, 23, 42, 0.04);
    }
    div[data-testid="stMetric"] label {
        font-family: 'DM Sans', sans-serif !important;
        font-size: 0.7rem !important;
        font-weight: 600 !important;
        text-transform: uppercase !important;
        letter-spacing: 0.06em !important;
        color: #64748b !important;
    }
    div[data-testid="stMetric"] [data-testid="stMetricValue"] {
        font-family: 'DM Sans', sans-serif !important;
        font-weight: 700 !important;
        color: #0f172a !important;
        letter-spacing: -0.03em !important;
    }

    /* ── Tab styling ── */
    .stTabs [data-baseweb="tab-list"] {
        gap: 0;
        background: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 10px;
        padding: 0.25rem;
    }
    .stTabs [data-baseweb="tab"] {
        font-family: 'DM Sans', sans-serif;
        font-weight: 600;
        font-size: 0.85rem;
        color: #64748b;
        border-radius: 8px;
        padding: 0.6rem 1.25rem;
        background: transparent;
        border: none;
    }
    .stTabs [aria-selected="true"] {
        background: #0f172a !important;
        color: #ffffff !important;
    }

    /* ── Buttons ── */
    .stButton > button {
        font-family: 'DM Sans', sans-serif;
        font-weight: 600;
        border-radius: 8px;
    }

    /* ── Select boxes ── */
    .stSelectbox label {
        font-family: 'DM Sans', sans-serif !important;
        font-weight: 600 !important;
        font-size: 0.78rem !important;
        color: #64748b !important;
        text-transform: uppercase !important;
        letter-spacing: 0.04em !important;
    }

    /* ── Progress bars ── */
    .stProgress > div > div {
        background: #f1f5f9;
        border-radius: 100px;
        height: 6px !important;
    }
    .stProgress > div > div > div {
        background: #1e293b;
        border-radius: 100px;
    }

    /* ── Captions ── */
    .stCaption, [data-testid="stCaptionContainer"] {
        font-family: 'DM Sans', sans-serif;
    }

    /* ── Markdown text ── */
    .stMarkdown {
        font-family: 'DM Sans', sans-serif;
    }

    /* ── Dividers ── */
    hr {
        border-color: #e2e8f0;
    }
</style>
""", unsafe_allow_html=True)

# ============================================================
# PASSWORD GATE
# ============================================================
if 'admin_authenticated' not in st.session_state:
    st.session_state.admin_authenticated = False

if not st.session_state.admin_authenticated:
    st.markdown("")
    st.markdown("")
    col_l, col_m, col_r = st.columns([1, 1, 1])
    with col_m:
        st.markdown("#### ✈️ Admin Dashboard")
        st.caption("Authorized access only")
        with st.form("admin_login"):
            password = st.text_input("Password", type="password", label_visibility="collapsed", placeholder="Enter admin password")
            submitted = st.form_submit_button("Sign In", type="primary", use_container_width=True)
            if submitted:
                try:
                    correct = st.secrets["ADMIN_PASSWORD"]
                except Exception:
                    correct = "nacadmin2026"
                if password == correct:
                    st.session_state.admin_authenticated = True
                    st.rerun()
                else:
                    st.error("Incorrect password.")
    st.stop()

# ============================================================
# DASHBOARD
# ============================================================
@st.cache_resource
def get_logger():
    return ContractLogger()

logger = get_logger()
contracts = logger.admin_get_contracts()

if not contracts:
    st.info("No data yet. Questions will appear after pilots start using the app.")
    st.stop()

# ── Header ──
st.markdown("""
<div style="display:flex; align-items:center; justify-content:space-between; padding:1.25rem 1.75rem; background:#0f172a; border-radius:12px; margin-bottom:1.5rem; box-shadow:0 4px 24px rgba(15,23,42,0.12);">
    <div style="display:flex; align-items:center; gap:0.75rem;">
        <span style="color:#fff; font-size:1.35rem; font-weight:700; letter-spacing:-0.02em;">✈️ AskTheContract</span>
        <span style="background:#2563eb; color:#fff; font-size:0.7rem; font-weight:600; padding:0.2rem 0.6rem; border-radius:100px; letter-spacing:0.04em; text-transform:uppercase;">Admin</span>
    </div>
</div>
""", unsafe_allow_html=True)

# Contract selector
if len(contracts) > 1:
    selected = st.selectbox("CONTRACT", contracts)
else:
    selected = contracts[0]
    st.caption(f"CONTRACT: **{selected}**")

# ── Key metrics ──
summary = logger.admin_summary(selected)
tier1_api = logger.admin_tier1_vs_api(selected)
total = summary['total']
clear_count = summary['status_counts'].get('CLEAR', 0)
ambiguous_count = summary['status_counts'].get('AMBIGUOUS', 0)
not_addressed_count = summary['status_counts'].get('NOT_ADDRESSED', 0)
clear_rate = f"{clear_count/total*100:.0f}%" if total > 0 else "—"
avg_time = f"{summary['avg_time']:.1f}s" if summary['avg_time'] else "—"
api_count = tier1_api['api']
est_cost = f"${api_count * 0.034:.2f}"

c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Total Questions", total)
c2.metric("Clear Rate", clear_rate)
c3.metric("Avg Response", avg_time)
c4.metric("Tier 1 (Free)", tier1_api['tier1'])
c5.metric("Est. API Cost", est_cost, f"{api_count} calls")

# Status bar
st.markdown(f"""
<div style="display:flex; align-items:center; gap:1.5rem; padding:0.75rem 1.25rem; background:#fff; border:1px solid #e2e8f0; border-radius:10px; margin:0.5rem 0 1.5rem 0; font-size:0.82rem; font-weight:500; color:#475569;">
    <span><span style="display:inline-block; width:8px; height:8px; border-radius:50%; background:#3b82f6; margin-right:6px;"></span>Clear: {clear_count}</span>
    <span><span style="display:inline-block; width:8px; height:8px; border-radius:50%; background:#d97706; margin-right:6px;"></span>Ambiguous: {ambiguous_count}</span>
    <span><span style="display:inline-block; width:8px; height:8px; border-radius:50%; background:#94a3b8; margin-right:6px;"></span>Not Addressed: {not_addressed_count}</span>
    <span style="margin-left:auto;"><span style="display:inline-block; width:8px; height:8px; border-radius:50%; background:#16a34a; margin-right:6px;"></span>System Healthy</span>
</div>
""", unsafe_allow_html=True)

# ============================================================
# CACHE REVIEW HELPER
# ============================================================
def _render_admin_entry(entry, contract_id, cache, is_flagged=False, compact=False):
    """Render a single cache entry with action buttons."""
    flag_icon = f"🚩×{entry.get('thumbs_down', 0)} " if entry.get('thumbs_down', 0) > 0 else ""
    served = f"served {entry.get('serve_count', 0)}×" if entry.get('serve_count', 0) > 0 else "never served"
    reviewed_icon = " ✅" if entry.get('reviewed', 0) else ""
    q_short = entry['question'][:70] + ('...' if len(entry['question']) > 70 else '')
    label = f"{flag_icon}📂 {entry['category'] or 'Uncategorized'}  ·  {served}{reviewed_icon}  ·  {q_short}"

    with st.expander(label, expanded=is_flagged):
        st.markdown(f"**Question:** {entry['question']}")
        st.caption(f"Status: {entry['status']}  ·  Cached: {entry['created_at']}  ·  Served: {entry.get('serve_count', 0)}×  ·  👎: {entry.get('thumbs_down', 0)}  ·  ID: {entry['id']}")

        # Show pilot feedback if flagged
        if entry.get('thumbs_down', 0) > 0:
            feedback = cache.get_feedback(entry['question'], contract_id)
            if feedback:
                st.markdown("**Pilot Feedback:**")
                for fb in feedback:
                    st.markdown(f"""
                    <div style="padding:0.5rem 0.75rem; background:#fef3c7; border-left:3px solid #f59e0b; border-radius:4px; margin:0.25rem 0; font-size:0.85rem;">
                        💬 "{fb['comment']}" <span style="color:#9ca3af; font-size:0.75rem;">— {fb['created_at']}</span>
                    </div>
                    """, unsafe_allow_html=True)
            else:
                st.caption("👎 flagged but no comment left")

        if not compact:
            if entry['status'] == 'CLEAR':
                st.success(entry['answer'])
            elif entry['status'] == 'AMBIGUOUS':
                st.warning(entry['answer'])
            else:
                st.info(entry['answer'])
        else:
            truncated = entry['answer'][:500] + ('...' if len(entry['answer']) > 500 else '')
            st.text(truncated)

        col_del, col_ok, col_spacer = st.columns([1, 1, 2])
        with col_del:
            if st.button("🗑️ Delete", key=f"adm_del_{entry['id']}"):
                cache.delete_entry(entry['id'], contract_id)
                st.rerun()
        with col_ok:
            if not entry.get('reviewed', 0):
                if st.button("✅ Approve", key=f"adm_ok_{entry['id']}"):
                    cache.mark_reviewed(entry['id'])
                    st.rerun()
            else:
                st.caption("✅ Reviewed")

# ============================================================
# TABS
# ============================================================
tab_questions, tab_cache, tab_satisfaction, tab_logs, tab_export = st.tabs([
    "Questions", "Cache Review", "Satisfaction", "Logs", "Export"
])

# ── QUESTIONS TAB ──
with tab_questions:
    col_left, col_right = st.columns([3, 2], gap="large")

    with col_left:
        st.markdown("**Most Asked Questions**")
        top = logger.admin_top_questions(selected, limit=15)
        if top:
            for i, (q_text, count) in enumerate(top, 1):
                st.caption(f"`{i:02d}`  {q_text}  ·  **{count}×**")
        else:
            st.caption("No questions yet.")

    with col_right:
        st.markdown("**By Category**")
        categories = logger.admin_questions_by_category(selected)
        if categories:
            total_cat = sum(c[1] for c in categories)
            for cat, count in categories:
                pct = count / total_cat * 100 if total_cat > 0 else 0
                st.progress(pct / 100, text=f"{cat}: {count}")
        else:
            st.caption("No category data yet.")

        st.markdown("")
        st.markdown("**Ambiguous — Contract Unclear**")
        ambiguous = logger.admin_ambiguous_questions(selected)
        if ambiguous:
            for q_text, count in ambiguous:
                count_str = f"  ·  **{count}×**" if count > 1 else ""
                st.caption(f"🟡 {q_text}{count_str}")
        else:
            st.caption("No ambiguous answers recorded ✓")

# ── CACHE REVIEW TAB ──
with tab_cache:
    try:
        from cache_manager import get_semantic_cache
        cache = get_semantic_cache()

        cache_stats = cache.stats()
        category_stats = cache.get_category_stats(selected)
        contract_total = cache_stats['contracts'].get(selected, 0)

        c1, c2, c3 = st.columns(3)
        c1.metric("Cached Answers", contract_total)
        c2.metric("Categories", len(category_stats))
        turso_str = "✅ Connected" if cache_stats['turso_connected'] else "Memory Only"
        c3.metric("Turso", turso_str)

        if not cache_stats['turso_connected']:
            st.info("💡 **Cache data lives in Turso Cloud.** You're running locally without Turso credentials, so cache shows empty. Deploy to Railway and check askthecontract.com/admin to see your real cached answers.")
        else:
            # Load all entries for review
            all_entries = cache.get_all_entries(selected)

            if all_entries:
                # Split into groups
                flagged = [e for e in all_entries if e.get('thumbs_down', 0) > 0]
                high_impact = [e for e in all_entries if e.get('thumbs_down', 0) == 0 and e.get('reviewed', 0) == 0]
                high_impact.sort(key=lambda x: x.get('serve_count', 0), reverse=True)
                reviewed_count = sum(1 for e in all_entries if e.get('reviewed', 0) == 1 and e.get('thumbs_down', 0) == 0)

                # Review summary
                st.markdown(
                    f"**🚩 {len(flagged)}** flagged by pilots  ·  "
                    f"**📊 {len(high_impact)}** unreviewed  ·  "
                    f"**✅ {reviewed_count}** approved"
                )

                st.markdown("---")

                # ---- FLAGGED BY PILOTS ----
                if flagged:
                    st.markdown(f"### 🚩 Flagged by Pilots ({len(flagged)})")
                    st.caption("These got 👎 — review the answer, read pilot feedback, delete bad ones")
                    for entry in flagged:
                        _render_admin_entry(entry, selected, cache, is_flagged=True)
                else:
                    st.success("🚩 No flagged answers — pilots haven't reported any problems.")

                st.markdown("---")

                # ---- HIGH IMPACT UNREVIEWED ----
                if high_impact:
                    show_count = min(10, len(high_impact))
                    st.markdown(f"### 📊 High-Impact Unreviewed (top {show_count} of {len(high_impact)})")
                    st.caption("Most-served answers you haven't checked yet")
                    for entry in high_impact[:show_count]:
                        _render_admin_entry(entry, selected, cache, is_flagged=False)
                    st.markdown("---")

                # ---- BROWSE ALL ----
                with st.expander(f"📋 Browse All Cached Answers ({len(all_entries)})", expanded=False):
                    if category_stats:
                        filter_cats = ["All"] + sorted(category_stats.keys())
                        selected_cat = st.selectbox("Filter by category:", filter_cats, key="admin_cache_browse")
                        if selected_cat != "All":
                            browse = [e for e in all_entries if e['category'] == selected_cat]
                        else:
                            browse = all_entries
                    else:
                        browse = all_entries

                    for entry in browse:
                        _render_admin_entry(entry, selected, cache, is_flagged=False, compact=True)

                st.markdown("---")

                # ---- BULK CLEAR BY CATEGORY ----
                st.markdown("### 🗑️ Clear by Category")
                st.caption("Use when you deploy code changes, add LOAs/MOAs, or fix retrieval rules.")

                if category_stats:
                    for cat, count in sorted(category_stats.items(), key=lambda x: x[1], reverse=True):
                        pct = count / max(contract_total, 1) * 100
                        st.progress(pct / 100, text=f"{cat}: {count}")

                    clear_options = ["Select a category..."] + sorted(category_stats.keys()) + ["⚠️ ALL CATEGORIES"]
                    clear_choice = st.selectbox("Clear cache for:", clear_options, key="admin_cache_clear")

                    if clear_choice and clear_choice != "Select a category...":
                        if clear_choice == "⚠️ ALL CATEGORIES":
                            st.warning(f"This will delete all {contract_total} cached answers for {selected}.")
                            if st.button("Clear All Cached Answers", type="primary"):
                                cache.clear(contract_id=selected)
                                st.success(f"Cleared {contract_total} cached answers.")
                                st.rerun()
                        else:
                            count = category_stats.get(clear_choice, 0)
                            st.info(f"This will delete {count} cached answers in **{clear_choice}**. Other categories stay warm.")
                            if st.button(f"Clear {clear_choice}", type="primary"):
                                removed = cache.clear_category(selected, clear_choice)
                                st.success(f"Cleared {removed} cached answers.")
                                st.rerun()
            else:
                st.caption("No cached answers for this contract yet. Cache populates as pilots ask questions.")

    except Exception as e:
        st.warning(f"Cache management unavailable: {e}")

# ── SATISFACTION TAB ──
with tab_satisfaction:
    ratings = logger.admin_ratings(selected)
    if ratings['total'] > 0:
        c1, c2, c3 = st.columns(3)
        c1.metric("Thumbs Up", ratings['up'])
        c2.metric("Thumbs Down", ratings['down'])
        c3.metric("Satisfaction", f"{ratings['satisfaction']}%")

        if ratings['down_questions']:
            st.markdown("")
            st.markdown("**Needs Review**")
            for q_text, ts in ratings['down_questions']:
                date_str = ts[:10] if ts else ""
                st.caption(f"🔴 {q_text}  ·  *{date_str}*")
    else:
        st.caption("No ratings yet. Ratings appear as pilots use the thumbs up/down buttons.")

# ── LOGS TAB ──
with tab_logs:
    recent = logger.admin_recent_questions(selected, limit=50)
    if recent:
        for ts, q_text, status, rt in recent:
            time_str = ts[5:16] if ts else "—"
            rt_str = f"{rt:.1f}s" if rt else "0.0s"
            icon = "🔵" if status == "CLEAR" else "🟡" if status == "AMBIGUOUS" else "⚪"
            st.caption(f"`{time_str}`  {icon}  `{rt_str}`  {q_text}")
    else:
        st.caption("No questions logged yet.")

# ── EXPORT TAB ──
with tab_export:
    csv_data = logger.admin_export_csv(selected)
    if csv_data and len(csv_data.split("\n")) > 1:
        row_count = len(csv_data.split(chr(10))) - 1
        st.markdown(f"**{selected}** — {row_count} questions available")
        st.download_button(
            label=f"Download CSV ({row_count} rows)",
            data=csv_data,
            file_name=f"{selected}_questions_export.csv",
            mime="text/csv",
            use_container_width=True
        )
    else:
        st.caption("No data to export.")

# ── Footer ──
st.markdown("---")
c1, c2 = st.columns([4, 1])
with c1:
    st.caption("AskTheContract Admin — data is per-contract and isolated")
with c2:
    if st.button("Sign Out"):
        st.session_state.admin_authenticated = False
        st.rerun()
