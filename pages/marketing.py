import streamlit as st
import pandas as pd

st.set_page_config(page_title="Marketing & Action Engine", layout="wide")

st.title("🏷️ Marketing & Action Engine")
st.markdown("Automated discounting and upcycling recommendations based on ML Spoilage Predictions.")

st.divider()

if 'active_risks' not in st.session_state:
    st.warning("⚠️ No spoilage predictions found. Please run the **Spoilage ML Pipeline** on the RUL Model page first.")
    st.stop()

df_risks = st.session_state['active_risks'].copy()

if df_risks.empty:
    st.info("No active risks to action. Your inventory is looking great!")
    st.stop()

st.subheader("Marketing Action Board")
st.markdown("Execute these specific strategies to recover maximum value from items nearing spoilage.")

# Upcycle config
UPCYCLE_RULES = ['Produce', 'Dairy']

def generate_action(row):
    tier = row.get('spoilage_risk_probability')
    category = row.get('product_category', '')
    can_upcycle = category in UPCYCLE_RULES
    
    # Tier mapping based on RUL logic:
    # 1: Final Markdown (<24 hrs)
    # 2: Priority Sell (1-2 days)
    # 3: Early Markdown (3-5 days)
    # 4: Watch (5+ days)
    
    if tier == 4:
        return "No action"
    elif tier == 3:
        return "Discount 5-10%"
    elif tier == 2:
        if can_upcycle:
            return "Recommend Upcycle (alongside or instead of discount)"
        else:
            return "Discount 15-25%"
    elif tier == 1:
        if can_upcycle:
            return "Strongly recommend Upcycle (best value recovery)"
        else:
            return "Discount 30-50%"
    else:
        return "Review manually"

df_risks['Recommended Action'] = df_risks.apply(generate_action, axis=1)

# Map raw integers to beautiful Tier Badges for the UI
tier_map = {
    1: "🔴 Final Markdown",
    2: "🟠 Priority Sell",
    3: "🟡 Early Markdown",
    4: "🟢 Watch"
}
df_risks['Urgency Tier'] = df_risks['spoilage_risk_probability'].map(tier_map)

# Select and rename columns for display
display_cols = [
    'item_sku', 
    'product_name', 
    'product_category', 
    'current_stock_level', 
    'Urgency Tier', 
    'Recommended Action'
]

df_display = df_risks[display_cols].rename(columns={
    'item_sku': 'SKU',
    'product_name': 'Product Name',
    'product_category': 'Category',
    'current_stock_level': 'Stock Level'
})

st.dataframe(
    df_display,
    use_container_width=True,
    hide_index=True
)

st.markdown("---")

col1, col2 = st.columns([1, 2])
with col1:
    csv = df_display.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="Download Action Plan (CSV)",
        data=csv,
        file_name="marketing_action_plan.csv",
        mime="text/csv",
        use_container_width=True,
        type="primary"
    )
