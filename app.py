import streamlit as st
import pandas as pd

st.set_page_config(page_title="MSME Inventory Portal", layout="wide")

# --- PAGE NAVIGATION (app.py orchestrates only, no page content of its own) ---
pages = [
    st.Page("pages/dashboard.py", title="Dashboard", icon="📊"),
    st.Page("pages/forecasting.py", title="Forecasting", icon="🔮"),
    st.Page("pages/marketing.py", title="Marketing", icon="🏷️"),
    st.Page("pages/rul_model.py", title="RUL Model", icon="⏳"),
]
nav = st.navigation(pages)

# --- GLOBAL MASTER DATA UPLOAD (pinned to the bottom of the sidebar) ---
with st.sidebar:
    st.markdown("")  # spacer to push upload control toward the bottom
    st.divider()
    st.markdown("**📥 Global Master Data**")
    uploaded_file = st.file_uploader(
        "Upload store inventory CSV", type=["csv"], key="global_master_data_uploader"
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
