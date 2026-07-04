import streamlit as st
import pandas as pd

st.set_page_config(page_title="MSME Inventory Portal", layout="wide")

st.title("🏪 MSME Perishable Inventory Control Suite")
st.markdown("Welcome! Please upload your store's 2-year inventory tracking spreadsheet to get started.")

# 1. Master File Uploader Component
uploaded_file = st.file_uploader("Choose your store's inventory CSV file", type=["csv"])

if uploaded_file is not None:
    # Read the file directly into a standard Pandas DataFrame
    df = pd.read_csv(uploaded_file)
    
    # CRITICAL FIX: Convert date strings into DateTime objects immediately
    df['arrival_date'] = pd.to_datetime(df['arrival_date'])
    df['order_date'] = pd.to_datetime(df['order_date'])
    
    # Save the dataframe globally into memory across all sub-pages
    st.session_state['master_data'] = df
    
    st.success(f"🎉 Successful Ingestion! Loaded {len(df):,} transaction records safely into application memory.")
    
    # Display a sneak peek matrix of the data to the owner
    st.subheader("📋 Uploaded Data Preview")
    st.dataframe(df.head(5), use_container_width=True)
    
    st.info("👈 Use the sidebar navigation menu to jump into your operational Dashboards, Spoilage Models, and Reports!")
else:
    st.warning("📥 Waiting for your inventory CSV upload before initiating metrics processing pipelines.")