import streamlit as st
import pandas as pd

st.set_page_config(
    page_title="ShelfIQ | Perishable Inventory Suite",
    page_icon="🛒",
    layout="wide"
)

st.title("🛒 ShelfIQ")
st.subheader("MSME Perishable Inventory Management Suite")
st.divider()

# --- Global File Upload ---
uploaded_file = st.file_uploader(
    "Upload your inventory file (merchant_comprehensive_inventory.csv)",
    type=["csv"]
)

if uploaded_file is not None:
    try:
        df = pd.read_csv(uploaded_file)
        st.session_state["master_data"] = df
        st.success(f"File loaded successfully — {len(df)} rows detected.")

        # Executive summary (only what we can derive from raw upload)
        st.divider()
        st.subheader("📊 Executive Summary")

        col1, col2, col3 = st.columns(3)
        col1.metric("Total Rows Loaded", len(df))
        col2.metric("Total Columns", len(df.columns))
        col3.metric("File Name", uploaded_file.name)

        st.caption("Navigate to a module page using the sidebar to begin analysis.")

    except Exception as e:
        st.error(f"Could not read file: {e}")

else:
    st.info("Please upload your inventory CSV file above to get started.")
    if "master_data" in st.session_state:
        del st.session_state["master_data"]
