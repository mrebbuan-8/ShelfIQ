import streamlit as st
import pandas as pd

st.set_page_config(page_title="MSME Inventory Portal", layout="wide")

# --- GLOBAL DARK NAVY + GREEN CARD THEME (brand color #22c55e) ---
st.html(
    """
    <style>
        :root { --brand-green: #22c55e; }

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
        section[data-testid="stSidebar"] a[data-testid="stSidebarNavLink"] span {
            font-size: 1.05rem !important;
        }

        /* Divider between the nav menu and the Global Master Data section */
        section[data-testid="stSidebar"] hr {
            margin: 0.75rem 0 1rem 0;
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

        /* Sidebar logo (rendered via st.logo, pinned above the nav menu) */
        [data-testid="stSidebarHeader"] {
            display: flex;
            flex-direction: column;
            align-items: flex-start;
            padding: 1.25rem 1rem 1rem 1rem;
        }
        [data-testid="stSidebarHeader"] img {
            border-radius: 12px;
            margin: 0;
        }
        [data-testid="stSidebarHeader"]::after {
            content: "v1";
            display: block;
            color: #6b7280;
            font-size: 0.75rem;
            text-align: left;
            margin-top: 0.4rem;
        }
    </style>
    """
)

# --- SIDEBAR LOGO (pinned above the nav menu) ---
st.logo("assets/shelfiq_logo.png", size="large")

# --- PAGE NAVIGATION (app.py orchestrates only, no page content of its own) ---
pages = [
    st.Page("pages/dashboard.py", title="Dashboard", icon=":material/dashboard:"),
    st.Page("pages/rul_model.py", title="Spoilage/Expiry Prediction", icon=":material/schedule:"),
    st.Page("pages/marketing.py", title="Marketing Action Engine", icon=":material/campaign:"),
    st.Page("pages/forecasting.py", title="Forecasting", icon=":material/insights:"),
]
nav = st.navigation(pages)

# --- GLOBAL MASTER DATA UPLOAD (pinned to the bottom of the sidebar) ---
with st.sidebar:
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
