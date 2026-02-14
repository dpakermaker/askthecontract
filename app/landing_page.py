"""
landing_page.py — AskTheContract Landing Page & Auth UI
========================================================
Maximum polish version. Every detail refined.
"""

import streamlit as st
from auth_manager import register_user, authenticate_user, init_auth_tables


LANDING_CSS = """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

    /* ── Hide sidebar + Streamlit chrome ── */
    [data-testid="stSidebar"],
    [data-testid="stSidebarCollapsedControl"],
    #MainMenu, footer, header { display: none !important; visibility: hidden !important; }

    /* ── Warm gradient background ── */
    .stApp {
        background: linear-gradient(170deg, #F8FAFC 0%, #F1F5F9 40%, #EFF6FF 100%) !important;
    }

    /* ── Layout ── */
    .block-container {
        padding-top: 2rem !important;
        padding-bottom: 2rem !important;
    }

    /* ══════════════════════════════════════════
       CARD — elevated white card
       ══════════════════════════════════════════ */
    [data-testid="stVerticalBlockBorderWrapper"] {
        background: #FFFFFF !important;
        border: 1px solid #E2E8F0 !important;
        border-radius: 16px !important;
        box-shadow: 0 1px 2px rgba(0,0,0,0.06),
                    0 4px 8px rgba(0,0,0,0.04),
                    0 12px 24px rgba(0,0,0,0.03) !important;
        padding: 1rem 1rem 0.5rem 1rem !important;
        transition: box-shadow 0.3s ease !important;
    }
    [data-testid="stVerticalBlockBorderWrapper"]:hover {
        box-shadow: 0 1px 2px rgba(0,0,0,0.06),
                    0 4px 8px rgba(0,0,0,0.06),
                    0 16px 32px rgba(0,0,0,0.05) !important;
    }

    /* ══════════════════════════════════════════
       FORM OVERRIDES
       ══════════════════════════════════════════ */
    [data-testid="stForm"] {
        border: none !important;
        padding: 0 !important;
    }

    /* Labels */
    .stTextInput > label {
        font-family: 'Inter', -apple-system, sans-serif !important;
        font-size: 0.82rem !important;
        font-weight: 500 !important;
        color: #1E293B !important;
        margin-bottom: 4px !important;
    }

    /* Input fields */
    .stTextInput input {
        background: #F8FAFC !important;
        border: 1.5px solid #CBD5E1 !important;
        border-radius: 8px !important;
        color: #0F172A !important;
        font-family: 'Inter', -apple-system, sans-serif !important;
        font-size: 0.9rem !important;
        padding: 0.7rem 0.9rem !important;
        box-shadow: inset 0 1px 2px rgba(0, 0, 0, 0.04) !important;
        transition: border-color 0.2s ease, box-shadow 0.2s ease, background 0.2s ease !important;
    }
    .stTextInput input:focus {
        background: #FFFFFF !important;
        border-color: #3B82F6 !important;
        box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.12),
                    inset 0 1px 2px rgba(0, 0, 0, 0.02) !important;
        outline: none !important;
    }
    .stTextInput input::placeholder {
        color: #94A3B8 !important;
        font-size: 0.86rem !important;
    }

    /* Password eye icon — muted until hover */
    .stTextInput button[kind="icon"],
    .stTextInput [data-testid="stTextInputRootElement"] button {
        color: #CBD5E1 !important;
        transition: color 0.15s ease !important;
    }
    .stTextInput button[kind="icon"]:hover,
    .stTextInput [data-testid="stTextInputRootElement"] button:hover {
        color: #64748B !important;
    }

    /* Checkbox */
    .stCheckbox label span {
        font-family: 'Inter', -apple-system, sans-serif !important;
        font-size: 0.76rem !important;
        color: #64748B !important;
    }

    /* Help text */
    .stTextInput [data-testid="stTooltipHoverTarget"] {
        color: #94A3B8 !important;
    }

    /* ── Tabs ── */
    .stTabs [data-baseweb="tab-list"] {
        gap: 0 !important;
        border-bottom: 1.5px solid #E2E8F0 !important;
        margin-bottom: 1.25rem !important;
    }
    .stTabs [data-baseweb="tab"] {
        font-family: 'Inter', -apple-system, sans-serif !important;
        font-size: 0.86rem !important;
        font-weight: 500 !important;
        color: #78849B !important;
        padding: 0.65rem 1.25rem !important;
        background: transparent !important;
        transition: color 0.15s ease !important;
    }
    .stTabs [data-baseweb="tab"]:hover {
        color: #475569 !important;
    }
    .stTabs [aria-selected="true"] {
        color: #0F172A !important;
        font-weight: 600 !important;
    }
    .stTabs [data-baseweb="tab-highlight"] {
        background-color: #2563EB !important;
        height: 2px !important;
    }

    /* ── Submit button ── */
    .stFormSubmitButton button {
        background: #2563EB !important;
        color: #FFFFFF !important;
        font-family: 'Inter', -apple-system, sans-serif !important;
        font-size: 0.9rem !important;
        font-weight: 600 !important;
        border: none !important;
        border-radius: 8px !important;
        padding: 0.75rem 1rem !important;
        margin-top: 0.5rem !important;
        transition: all 0.2s ease !important;
        letter-spacing: -0.01em !important;
        box-shadow: 0 1px 3px rgba(37, 99, 235, 0.3),
                    0 2px 6px rgba(37, 99, 235, 0.15) !important;
    }
    .stFormSubmitButton button:hover {
        background: #1D4ED8 !important;
        box-shadow: 0 2px 4px rgba(37, 99, 235, 0.3),
                    0 6px 16px rgba(37, 99, 235, 0.2) !important;
        transform: translateY(-1px) !important;
    }
    .stFormSubmitButton button:active {
        background: #1E40AF !important;
        transform: translateY(0) !important;
        box-shadow: 0 1px 2px rgba(37, 99, 235, 0.3) !important;
    }

    /* ── Expanders ── */
    .stExpander {
        border: 1px solid #E2E8F0 !important;
        border-radius: 10px !important;
        background: #FFFFFF !important;
        margin-bottom: 0.4rem !important;
        box-shadow: 0 1px 2px rgba(0, 0, 0, 0.03) !important;
        transition: border-color 0.2s ease, box-shadow 0.2s ease !important;
    }
    .stExpander:hover {
        border-color: #CBD5E1 !important;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.06) !important;
    }
    /* Kill red focus border */
    .stExpander:focus-within,
    .stExpander:focus,
    .stExpander:active,
    .stExpander details,
    .stExpander details:focus,
    .stExpander details:active,
    .stExpander details[open] {
        border-color: #E2E8F0 !important;
        outline: none !important;
    }
    .stExpander details[open] {
        border-color: #CBD5E1 !important;
    }
    .stExpander summary {
        font-family: 'Inter', -apple-system, sans-serif !important;
        font-size: 0.82rem !important;
        font-weight: 500 !important;
        color: #64748B !important;
        transition: color 0.15s ease !important;
    }
    .stExpander summary:hover { color: #1E293B !important; }
    .stExpander summary:focus { outline: none !important; box-shadow: none !important; }
    .stExpander [data-testid="stExpanderToggleIcon"] { color: #94A3B8 !important; }
    .stExpander .stMarkdown p,
    .stExpander .stMarkdown li {
        font-family: 'Inter', -apple-system, sans-serif !important;
        font-size: 0.82rem !important;
        color: #475569 !important;
        line-height: 1.7 !important;
    }
    .stExpander .stMarkdown strong { color: #0F172A !important; }
    .stExpander .stMarkdown em { color: #64748B !important; }

    /* ── Alerts ── */
    .stAlert {
        font-family: 'Inter', -apple-system, sans-serif !important;
        font-size: 0.82rem !important;
        border-radius: 8px !important;
    }

    /* ══════════════════════════════════════════
       MOBILE RESPONSIVE
       On small screens, let the form go wider
       ══════════════════════════════════════════ */
    @media (max-width: 768px) {
        .block-container {
            padding-left: 1rem !important;
            padding-right: 1rem !important;
        }
        [data-testid="stVerticalBlockBorderWrapper"] {
            padding: 0.75rem 0.5rem 0.5rem 0.5rem !important;
            border-radius: 12px !important;
        }
    }
</style>
"""


def show_landing_page():
    if "auth_tables_initialized" not in st.session_state:
        init_auth_tables()
        st.session_state.auth_tables_initialized = True

    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
        st.session_state.user_id = None
        st.session_state.user_email = None
        st.session_state.display_name = None

    if st.session_state.authenticated:
        return True

    st.markdown(LANDING_CSS, unsafe_allow_html=True)

    # ── Centered layout ──
    spacer_l, center, spacer_r = st.columns([1, 0.85, 1])

    with center:

        # ═══════════════════════════════════
        # GROUP 1: Brand + Headline
        # ═══════════════════════════════════
        st.markdown("""
        <div style="text-align:center; margin-bottom:2rem;">
            <div style="font-family:'Inter',sans-serif; font-size:0.92rem; font-weight:700;
                        letter-spacing:-0.02em; color:#2563EB; margin-bottom:1.5rem;">
                AskTheContract
            </div>
            <div style="font-family:'Inter',sans-serif; font-size:1.65rem; font-weight:700;
                        color:#0F172A; letter-spacing:-0.03em; line-height:1.2; margin-bottom:0.6rem;">
                Your contract, searchable<br>in seconds.
            </div>
            <div style="font-family:'Inter',sans-serif; font-size:0.88rem; color:#64748B;
                        line-height:1.55; font-weight:400;">
                Exact language. Page numbers. Section references.<br>
                Built by a line pilot, for line pilots.
            </div>
        </div>
        """, unsafe_allow_html=True)

        # ═══════════════════════════════════
        # GROUP 2: Form Card
        # ═══════════════════════════════════
        with st.container(border=True):

            # Trust badge inside the card
            st.markdown("""
            <div style="text-align:center; margin-bottom:0.5rem; margin-top:0.25rem;">
                <div style="display:inline-flex; align-items:center; gap:0.35rem;
                            background:#F0FDF4; border:1px solid #BBF7D0;
                            border-radius:100px; padding:0.3rem 0.85rem;">
                    <span style="font-size:0.68rem;">🔒</span>
                    <span style="font-family:'Inter',sans-serif; font-size:0.71rem; font-weight:500;
                                color:#166534; letter-spacing:0.01em;">
                        Your information is never sold or shared
                    </span>
                </div>
            </div>
            """, unsafe_allow_html=True)

            _show_auth_forms()

        # ═══════════════════════════════════
        # GROUP 3: Secondary Info
        # ═══════════════════════════════════
        st.markdown("<div style='height:1.5rem'></div>", unsafe_allow_html=True)

        with st.expander("How it works"):
            st.markdown("""
**Ask a question** in your own words — no need to know section numbers.

**Get exact contract language** pulled directly from the JCBA with page numbers and section references so you can verify for yourself.

**Know if it's clear or ambiguous** — the tool tells you when language could be read multiple ways.

*It's the tool I wish existed every time I sat on reserve wondering if I was reading a section right.*
            """)

        with st.expander("Privacy — what we store & why"):
            st.markdown("""
This tool was built by a fellow line pilot — not a tech company, not management, not the union.

**What we store:**
- **Your email address** — so you can log in. That's your only personal info.
- **Questions & answers** — saved in a shared cache so the next pilot who asks something similar gets an instant answer. No names attached — just the question and the contract language.
- **Feedback flags** — when someone flags a bad answer, it helps us fix it and make the tool more accurate for everyone.

**What we will never do:**
- **We will never sell your information.** Not to anyone. Not ever.
- **We will never share your data** with management, your airline, or any third party.
- **We will never use your questions against you.** This tool exists to help pilots — not to create leverage for anyone else.

**Why it works this way:**

Every question a pilot asks makes this tool smarter and faster for the next pilot. Cached answers mean less waiting. Feedback flags mean more accuracy. The more pilots use it, the better it gets for everyone. Pilots helping pilots.
            """)

        with st.expander("Legal disclaimer"):
            st.markdown("""
AskTheContract is a **contract language search tool**, not a source of legal advice. The answers provided are direct excerpts from your collective bargaining agreement (JCBA) and are presented for informational and reference purposes only.

This tool does not interpret, advise, or render opinions on contract language. It is not a substitute for consulting with your union representative, grievance committee, or legal counsel. Always verify critical contract language against your official JCBA document.

AskTheContract is an independent tool built by a fellow pilot. It is **not affiliated with, endorsed by, or operated by** any airline, union, or labor organization.
            """)

        # Footer with separator
        st.markdown("""
        <div style="margin-top:2rem; padding-top:1rem; border-top:1px solid #E2E8F0; text-align:center; padding-bottom:1rem;">
            <span style="font-family:'Inter',sans-serif; font-size:0.7rem; color:#94A3B8;">
                © 2026 AskTheContract · Independent pilot tool
            </span>
        </div>
        """, unsafe_allow_html=True)

    return False


def _show_auth_forms():
    tab_login, tab_register = st.tabs(["Log in", "Create account"])

    with tab_login:
        with st.form("login_form", clear_on_submit=False):
            email = st.text_input("Email address", placeholder="you@example.com", key="login_email")
            password = st.text_input("Password", type="password", placeholder="Enter your password", key="login_password")
            submitted = st.form_submit_button("Continue", use_container_width=True)

            if submitted:
                if not email or not password:
                    st.error("Please enter your email and password.")
                else:
                    result = authenticate_user(email, password)
                    if result["success"]:
                        st.session_state.authenticated = True
                        st.session_state.user_id = result["user_id"]
                        st.session_state.user_email = email.strip().lower()
                        st.session_state.display_name = result["display_name"]
                        st.rerun()
                    else:
                        st.error(result["message"])

    with tab_register:
        with st.form("register_form", clear_on_submit=False):
            new_email = st.text_input("Email address", placeholder="you@example.com", key="reg_email")
            new_display = st.text_input(
                "Display name (optional)",
                placeholder="Callsign, first name, or leave blank",
                key="reg_display",
                help="Just for your greeting. Leave blank if you prefer."
            )
            new_password = st.text_input("Create password", type="password", placeholder="At least 6 characters", key="reg_password")
            new_password2 = st.text_input("Confirm password", type="password", placeholder="Type it again", key="reg_password2")

            agree = st.checkbox(
                "I understand this is a contract search tool, not legal advice.",
                key="reg_agree"
            )

            submitted = st.form_submit_button("Create account", use_container_width=True)

            if submitted:
                if not new_email or not new_password:
                    st.error("Please fill in your email and password.")
                elif new_password != new_password2:
                    st.error("Passwords don't match.")
                elif not agree:
                    st.error("Please acknowledge the disclaimer to continue.")
                else:
                    result = register_user(new_email, new_password, new_display)
                    if result["success"]:
                        login_result = authenticate_user(new_email, new_password)
                        if login_result["success"]:
                            st.session_state.authenticated = True
                            st.session_state.user_id = login_result["user_id"]
                            st.session_state.user_email = new_email.strip().lower()
                            st.session_state.display_name = login_result["display_name"]
                            st.rerun()
                        else:
                            st.success(result["message"] + " Please log in.")
                    else:
                        st.error(result["message"])


def show_logout_button():
    display = st.session_state.get("display_name", "Pilot")
    st.sidebar.markdown(f"**Logged in as:** {display}")
    if st.sidebar.button("Log Out", use_container_width=True):
        st.session_state.authenticated = False
        st.session_state.user_id = None
        st.session_state.user_email = None
        st.session_state.display_name = None
        st.rerun()
