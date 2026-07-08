import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from sklearn.ensemble import RandomForestClassifier

st.set_page_config(page_title="RUL Spoilage Predictor", layout="wide")

st.title(":material/schedule: Spoilage/Expiry Prediction")
st.markdown("Run the Machine Learning pipeline to dynamically train a Random Forest and generate the latest active spoilage risks for the current inventory.")

if 'master_data' not in st.session_state:
    st.warning("We need your inventory file to run the spoilage model. Please upload your CSV using the sidebar to continue.")
    st.stop()

df = st.session_state['master_data'].copy()

st.divider()

with st.spinner("Training Spoilage Engine..."):
    try:
        # 1. Target Variable (Ground Truth)
        df['will_spoil'] = np.where(df['items_spoiled'] > 0, 1, 0)

        # Convert dates early so both training and inference use the same scale
        df['expiry_date'] = pd.to_datetime(df['expiry_date'])
        df['arrival_date'] = pd.to_datetime(df['arrival_date'])

        # 2. Semantic Feature Mapping (TRAINING)
        df['stock_to_sell'] = df['quantity_received']
        # Compute from dates (consistent with inference) instead of raw shelf life column
        df['days_to_sell'] = (df['expiry_date'] - df['arrival_date']).dt.days

        sensitivity_map = {'Low': 1, 'Medium': 2, 'High': 3}
        df['sensitivity_score'] = df['spoilage_sensitivity'].map(sensitivity_map).fillna(2)

        features = [
            'stock_to_sell',
            'days_to_sell',
            'daily_demand',
            'supplier_lead_time_days',
            'sensitivity_score'
        ]

        df_train = df.dropna(subset=features + ['will_spoil']).copy()
        X = df_train[features]
        y = df_train['will_spoil']

        # Train model
        model = RandomForestClassifier(n_estimators=100, random_state=42, n_jobs=-1)
        model.fit(X, y)

        # Feature importance
        importances = model.feature_importances_
        indices = np.argsort(importances)[::-1]

        feature_name_map = {
            'stock_to_sell': 'Current Stock',
            'days_to_sell': 'Days to Sell',
            'daily_demand': 'Daily Demand',
            'supplier_lead_time_days': 'Supplier Lead Time',
            'sensitivity_score': 'Spoilage Sensitivity'
        }
        friendly_features = [feature_name_map.get(features[i], features[i]) for i in indices]

        df_importances = pd.DataFrame({
            "Feature": friendly_features,
            "Importance Score": importances[indices]
        }).sort_values("Importance Score", ascending=True).set_index("Feature")

        st.session_state['feature_df'] = df_importances

        # 3. INFERENCE: Predict on CURRENT stock levels
        # Use today's actual date (not max arrival date)
        current_date = pd.Timestamp.today().normalize()

        df_pred = df.copy()
        df_pred['stock_to_sell'] = df_pred['current_stock_level']
        df_pred['days_to_sell'] = (df_pred['expiry_date'] - current_date).dt.days
        df_pred['sensitivity_score'] = df_pred['spoilage_sensitivity'].map(sensitivity_map).fillna(2)

        # Drop rows with NaNs in features just to be safe during prediction
        df_pred = df_pred.dropna(subset=features)

        def map_urgency(days):
            if days >= 5: return 4
            elif days >= 3: return 3
            elif days >= 1: return 2
            else: return 1

        df_pred['spoilage_risk_probability'] = df_pred['days_to_sell'].apply(map_urgency)
        df_pred['predicted_spoil_risk'] = model.predict(df_pred[features])

        # Filter for active integration targets
        df_integration = df_pred[(df_pred['predicted_spoil_risk'] == 1) &
                                  (df_pred['current_stock_level'] > 0) &
                                  (df_pred['days_to_sell'] >= 0)].copy()

        export_cols = [
            'item_sku', 'product_name', 'product_category', 'supplier_name',
            'arrival_date', 'expiry_date', 'current_stock_level', 'daily_demand',
            'spoilage_risk_probability', 'days_to_sell', 'selling_price',
            'items_spoiled'
        ]
        # Only keep columns that actually exist in the dataframe
        export_cols = [c for c in export_cols if c in df_integration.columns]

        # Convert dates to strings for cleaner display
        for col in ['arrival_date', 'expiry_date']:
            df_integration[col] = df_integration[col].dt.strftime('%Y-%m-%d')

        st.session_state['active_risks'] = df_integration[export_cols]

    except Exception as e:
        st.error(f"Execution error: {str(e)}")
        st.stop()

st.subheader("Active Spoilage Risks")
st.markdown("These are the items currently in stock that the model predicts will spoil before selling out.")

if 'active_risks' in st.session_state:
    df_risks = st.session_state['active_risks']
    
    total_risks = len(df_risks)
    critical_risks = len(df_risks[df_risks['spoilage_risk_probability'] == 1])

    # Most at-risk item: lowest days_to_sell (soonest to expire)
    most_at_risk_row = df_risks.sort_values('days_to_sell').iloc[0]
    most_at_risk_item = most_at_risk_row['product_name']

    # Category with the most Final Markdown (<24 hrs) items
    final_markdown_df = df_risks[df_risks['spoilage_risk_probability'] == 1]
    if not final_markdown_df.empty:
        most_urgent_category = final_markdown_df['product_category'].value_counts().idxmax()
    else:
        most_urgent_category = "None"

    col_m1, col_m2, col_m3, col_m4 = st.columns(4)
    col_m1.metric(label="Total Active Risks Identified", value=f"{total_risks:,}")
    col_m2.metric(label="Final Markdown (<24 hrs)", value=f"{critical_risks:,}", help="Urgent action required")
    col_m3.metric(label="Most At-Risk Item", value=most_at_risk_item)
    col_m4.metric(label="Most Urgent Category", value=most_urgent_category)
    
    csv = df_risks.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="Download Spoilage Report (CSV)",
        data=csv,
        file_name="spoilage_risks_report.csv",
        mime="text/csv",
        use_container_width=True
    )
    
    tier_map = {
        1: "Final Markdown (<24 hrs)",
        2: "Priority Sell (1-2 days)",
        3: "Early Markdown (3-5 days)",
        4: "Watch (5+ days)"
    }
    
    UPCYCLE_RULES = ['Produce', 'Dairy']
    
    def generate_action(row):
        tier = row['spoilage_risk_probability']
        category = row['product_category']
        can_upcycle = category in UPCYCLE_RULES
        
        if tier == 4:
            return "No action"
        elif tier == 3:
            return "Discount 5-10%"
        elif tier == 2:
            if can_upcycle:
                return "Recommend Upcycle"
            else:
                return "Discount 15-25%"
        elif tier == 1:
            if can_upcycle:
                return "Strongly recommend Upcycle"
            else:
                return "Discount 30-50%"
        return "Review manually"

    df_risks['Recommended Action'] = df_risks.apply(generate_action, axis=1)
    
    display_df = df_risks.rename(columns={
        'item_sku': 'SKU',
        'product_name': 'Product Name',
        'product_category': 'Category',
        'supplier_name': 'Supplier',
        'arrival_date': 'Arrival Date',
        'expiry_date': 'Expiry Date',
        'current_stock_level': 'Stock Level',
        'daily_demand': 'Daily Demand',
        'predicted_spoil_risk': 'Risk Flag',
        'spoilage_risk_probability': 'Urgency Tier',
        'days_to_sell': 'Days to Sell',
        'selling_price': 'Selling Price',
        'items_spoiled': 'Items Spoiled'
    })
    
    display_df['Urgency Tier'] = display_df['Urgency Tier'].map(tier_map)
    
    st.dataframe(
        display_df, 
        use_container_width=True,
        column_config={
            "Urgency Tier": st.column_config.TextColumn(
                "Urgency Tier",
                help="Based on Remaining Useful Life (RUL)."
            ),
            "Recommended Action": st.column_config.TextColumn(
                "Recommended Action",
                help="Automated strategy based on RUL tier."
            ),
            "Risk Flag": None,
        }
    )
else:
    st.info("No predictions found. Please run the pipeline to generate risks.")
