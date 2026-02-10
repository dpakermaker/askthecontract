import streamlit as st
import sys
from pathlib import Path

# Add parent directory to path so we can import contract_logger
sys.path.append(str(Path(__file__).parent.parent))
from contract_logger import ContractLogger

st.set_page_config(page_title="Admin Dashboard", page_icon="🔒", layout="wide")

# ============================================================
# ADMIN PASSWORD GATE
# ============================================================
if 'admin_authenticated' not in st.session_state:
    st.session_state.admin_authenticated = False

if not st.session_state.admin_authenticated:
    st.title("🔒 Admin Dashboard")
    st.write("Authorized access only.")

    with st.form("admin_login"):
        password = st.text_input("Admin password:", type="password")
        submitted = st.form_submit_button("Login", type="primary")
        if submitted:
            try:
                correct = st.secrets["ADMIN_PASSWORD"]
            except Exception:
                correct = "nacadmin2026"
            if password == correct:
                st.session_state.admin_authenticated = True
                st.rerun()
            else:
                st.error("Incorrect admin password.")
    st.stop()

# ============================================================
# ADMIN DASHBOARD
# ============================================================
st.title("📊 Admin Dashboard")

@st.cache_resource
def get_logger():
    return ContractLogger()

logger = get_logger()

# --- Contract selector ---
contracts = logger.admin_get_contracts()

if not contracts:
    st.warning("No question data found yet. Questions will appear here after pilots start using the app.")
    st.stop()

selected = st.selectbox("Select Contract:", contracts)

st.write("---")

# ============================================================
# OVERVIEW
# ============================================================
st.header(f"📋 {selected} — Overview")

summary = logger.admin_summary(selected)
tier1_api = logger.admin_tier1_vs_api(selected)

col1, col2, col3, col4, col5 = st.columns(5)
with col1:
    st.metric("Total Questions", summary['total'])
with col2:
    st.metric("Avg Response", f"{summary['avg_time']:.1f}s" if summary['avg_time'] else "N/A")
with col3:
    clear = summary['status_counts'].get('CLEAR', 0)
    total = summary['total']
    st.metric("CLEAR Rate", f"{clear/total*100:.0f}%" if total > 0 else "N/A")
with col4:
    st.metric("Tier 1 (Free)", tier1_api['tier1'])
with col5:
    st.metric("API Calls", tier1_api['api'])

# Cost estimate
api_count = tier1_api['api']
est_cost_low = api_count * 0.026  # ~2.6¢ cache read
est_cost_high = api_count * 0.043  # ~4.3¢ cache write
st.caption(f"💰 Estimated API cost: ${est_cost_low:.2f} – ${est_cost_high:.2f} ({api_count} API calls × 2.6–4.3¢ avg)")

# Status breakdown
st.subheader("Status Breakdown")
col1, col2, col3 = st.columns(3)
with col1:
    st.metric("🔵 CLEAR", summary['status_counts'].get('CLEAR', 0))
with col2:
    st.metric("🟡 AMBIGUOUS", summary['status_counts'].get('AMBIGUOUS', 0))
with col3:
    st.metric("⚪ NOT ADDRESSED", summary['status_counts'].get('NOT_ADDRESSED', 0))

st.write("---")

# ============================================================
# QUESTIONS BY CATEGORY
# ============================================================
st.header("📂 Questions by Category")

categories = logger.admin_questions_by_category(selected)
if categories:
    total_cat = sum(c[1] for c in categories)
    for cat, count in categories:
        pct = count / total_cat * 100 if total_cat > 0 else 0
        st.progress(pct / 100, text=f"{cat}: {count} ({pct:.0f}%)")
else:
    st.caption("No category data yet.")

st.write("---")

# ============================================================
# TOP 20 MOST ASKED
# ============================================================
st.header("🔥 Top 20 Most Asked Questions")

top = logger.admin_top_questions(selected, limit=20)
if top:
    for i, (q_text, count) in enumerate(top, 1):
        label = f"**{i}.** {q_text}"
        if count > 1:
            label += f"  ·  *{count}x*"
        st.markdown(label)
else:
    st.caption("No questions logged yet.")

st.write("---")

# ============================================================
# AMBIGUOUS QUESTIONS (CONTRACT UNCLEAR)
# ============================================================
st.header("🟡 Ambiguous Questions — Where the Contract is Unclear")
st.caption("These questions came back AMBIGUOUS. Useful for identifying provisions that need clearer language.")

ambiguous = logger.admin_ambiguous_questions(selected)
if ambiguous:
    for q_text, count in ambiguous:
        label = f"• {q_text}"
        if count > 1:
            label += f"  ·  *{count}x*"
        st.markdown(label)
else:
    st.caption("No ambiguous answers recorded. That's a good sign.")

st.write("---")

# ============================================================
# USER SATISFACTION (RATINGS)
# ============================================================
st.header("👍 User Satisfaction")

ratings = logger.admin_ratings(selected)
if ratings['total'] > 0:
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("👍 Thumbs Up", ratings['up'])
    with col2:
        st.metric("👎 Thumbs Down", ratings['down'])
    with col3:
        st.metric("Satisfaction", f"{ratings['satisfaction']}%")

    if ratings['down_questions']:
        st.subheader("Questions Needing Review (Thumbs Down)")
        for q_text, ts in ratings['down_questions']:
            date_str = ts[:10] if ts else ""
            st.markdown(f"• {q_text}  ·  *{date_str}*")
else:
    st.caption("No ratings yet.")

st.write("---")

# ============================================================
# RECENT QUESTIONS LOG
# ============================================================
st.header("📋 Recent Questions Log")

recent = logger.admin_recent_questions(selected, limit=50)
if recent:
    for ts, q_text, status, rt in recent:
        time_str = ts[5:16] if ts else "?"  # MM-DD HH:MM
        rt_str = f"{rt:.1f}s" if rt else "0.0s"
        status_icon = "🔵" if status == "CLEAR" else "🟡" if status == "AMBIGUOUS" else "⚪"
        st.caption(f"{time_str} | {status_icon} {status} | {rt_str} | {q_text[:80]}")
else:
    st.caption("No questions logged yet.")

st.write("---")

# ============================================================
# CSV EXPORT
# ============================================================
st.header("📤 Export Data")

csv_data = logger.admin_export_csv(selected)
if csv_data and len(csv_data.split("\n")) > 1:
    st.download_button(
        label=f"⬇️ Download {selected} Questions (CSV)",
        data=csv_data,
        file_name=f"{selected}_questions_export.csv",
        mime="text/csv"
    )
    st.caption(f"{len(csv_data.split(chr(10))) - 1} questions in export")
else:
    st.caption("No data to export.")

# ---- Footer ----
st.write("---")
st.caption("🔒 Admin Dashboard — data is per-contract and isolated. No cross-contract data leaks.")

# Logout
if st.button("🚪 Admin Logout"):
    st.session_state.admin_authenticated = False
    st.rerun()
