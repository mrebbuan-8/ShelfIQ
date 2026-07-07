import streamlit as st
import pandas as pd

st.set_page_config(page_title="MSME Inventory Portal", layout="wide")

# --- GLOBAL DARK NAVY + GREEN CARD THEME (brand color #22c55e) ---
st.html(
    """
    <style>
        :root { --brand-green: #22c55e; }

        /* Section headings: green left-accent bar, e.g. "### Section Title" */
        [data-testid="stMain"] h2,
        [data-testid="stMain"] h3,
        [data-testid="stMain"] h4 {
            border-left: 4px solid var(--brand-green);
            padding-left: 0.75rem;
        }

        /* Sidebar nav rail: rounded, highlighted active page */
        section[data-testid="stSidebar"] a[data-testid="stSidebarNavLink"],
        section[data-testid="stSidebar"] li a {
            border-radius: 10px !important;
            margin: 2px 10px !important;
        }
        section[data-testid="stSidebar"] a[aria-current="page"] {
            background-color: rgba(34, 197, 94, 0.16) !important;
        }
        section[data-testid="stSidebar"] a[aria-current="page"] span {
            color: var(--brand-green) !important;
            font-weight: 700 !important;
        }

        /* Card-style content blocks: KPI tiles, tables, expanders */
        div[data-testid="stMetric"],
        div[data-testid="stExpander"],
        div[data-testid="stDataFrame"],
        div[data-testid="stVerticalBlockBorderWrapper"] {
            background: #131a2b;
            border: 1px solid rgba(148, 163, 184, 0.15);
            border-radius: 16px !important;
            overflow: hidden;
        }
        div[data-testid="stMetric"] {
            padding: 1rem !important;
        }
    </style>
    """
)

# --- PAGE NAVIGATION (app.py orchestrates only, no page content of its own) ---
pages = [
    st.Page("pages/dashboard.py", title="Dashboard", icon=":material/dashboard:"),
    st.Page("pages/forecasting.py", title="Forecasting", icon=":material/insights:"),
    st.Page("pages/marketing.py", title="Marketing", icon=":material/campaign:"),
    st.Page("pages/rul_model.py", title="RUL Model", icon=":material/schedule:"),
]
nav = st.navigation(pages)

# --- GLOBAL MASTER DATA UPLOAD (pinned to the bottom of the sidebar) ---
with st.sidebar:
    st.markdown("")  # spacer to push upload control toward the bottom
    st.divider()
    st.markdown("**📥 Global Master Data**")
    st.html(
        """
        <style>
            [data-testid="stFileUploader"] section button {
                width: 100% !important;
            }
            [data-testid="stFileUploader"] section {
                display: flex;
                flex-direction: column;
                align-items: center;
            }
            [data-testid="stFileUploader"] section small {
                display: block;
                width: 100%;
                text-align: center;
            }
        </style>
        """
    )
    uploaded_file = st.file_uploader(
        "Upload store inventory CSV",
        type=["csv"],
        key="global_master_data_uploader",
        label_visibility="collapsed",
    )

    if uploaded_file is not None:
        df = pd.read_csv(uploaded_file)

        # CRITICAL FIX: Convert date strings into DateTime objects immediately
        df['arrival_date'] = pd.to_datetime(df['arrival_date'])
        df['order_date'] = pd.to_datetime(df['order_date'])

        # Save the dataframe globally into memory across all sub-pages
        st.session_state['master_data'] = df

        st.success(f"🎉 Loaded {len(df):,} records.")

nav.run()
