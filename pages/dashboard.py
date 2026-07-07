import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

st.set_page_config(page_title="Operational Dashboard", layout="wide")

st.title(":material/dashboard: Store Performance & Inventory Dashboard")

# --- DATA RETRIEVAL BRIDGE ---
# Check if the user uploaded a file in app.py first
if 'master_data' in st.session_state:
    df = st.session_state['master_data'].copy()
    st.success("✅ Displaying metrics from the live user-uploaded dataset.")
else:
    # LOCAL DEVELOPMENT FALLBACK: Auto-loads your sample dataset file for offline debugging
    try:
        df = pd.read_csv('capstone_dataset_2years.csv')
        df['arrival_date'] = pd.to_datetime(df['arrival_date'])
        df['order_date'] = pd.to_datetime(df['order_date'])
        st.session_state['master_data'] = df
        st.warning("No inventory file has been uploaded yet, so we're showing sample data for now. Upload your store's CSV from the sidebar to see your own numbers.")
    except FileNotFoundError:
        st.error("We need your inventory file to build this dashboard. Please upload your CSV using the sidebar to continue.")
        st.stop()

# --- PRE-COMPUTE COLUMNS BEFORE SLICING ---
df['active_stock_value_retail'] = df['current_stock_level'] * df['base_price_php']

# --- TIME HORIZON ANCHORING ---
anchor_date = df['arrival_date'].max()
ninety_days_ago = anchor_date - timedelta(days=90)
current_month = anchor_date.month
current_year = anchor_date.year

# --- CALCULATE THE 4 KPIS ---
# KPI 1: Inventory Value
total_inventory_value = df['active_stock_value_retail'].sum()

# KPI 2: Stock Turnover Rate (90 Days)
df_90 = df[(df['arrival_date'] >= ninety_days_ago) & (df['arrival_date'] <= anchor_date)].copy()
if not df_90.empty:
    cogs_90 = (df_90['quantity_sold'] * df_90['cost_price']).sum()
    avg_inventory_cost = ((df_90['quantity_received'] - df_90['quantity_sold']) * df_90['cost_price']).mean()
    stock_turnover_rate = (cogs_90 / avg_inventory_cost) if avg_inventory_cost > 0 else 0.0
else:
    stock_turnover_rate = 0.0

# KPI 3 & 4: Monthly metrics
df_month = df[(df['arrival_date'].dt.month == current_month) & (df['arrival_date'].dt.year == current_year)].copy()

if not df_month.empty:
    running_profit_month = (df_month['quantity_sold'] * df_month['selling_price']).sum() - (df_month['quantity_sold'] * df_month['cost_price']).sum()
    avg_daily_demand_month = df_month['daily_demand'].mean()
else:
    running_profit_month = 0.0
    avg_daily_demand_month = 0.0

# --- 4. STREAMLIT KPI BOX LAYOUT RENDER ---
st.markdown("---")

# Global CSS Injector to recursively force alignment down all metric sub-div elements
st.html(
    """
    <style>
        /* Force container flexbox to center content */
        div[data-testid="stMetric"] {
            text-align: center !important;
            display: flex !important;
            flex-direction: column !important;
            align-items: center !important;
            justify-content: center !important;
            width: 100% !important;
        }
        
        /* Explicit text targeting as an extra layer of defense */
        [data-testid="stMetricValue"], 
        [data-testid="stMetricLabel"], 
        [data-testid="stMetricDelta"] {
            text-align: center !important;
            width: 100% !important;
        }
    </style>
    """
)

kpi_col1, kpi_col2, kpi_col3, kpi_col4 = st.columns(4)

with kpi_col1:
    st.metric(
        label="Total Inventory Value",
        value=f"₱{total_inventory_value:,.2f}",
        border=True,
        help="Total retail market value of items currently physically sitting on store shelves."
    )

with kpi_col2:
    st.metric(
        label="Stock Turnover Rate (90d)",
        value=f"{stock_turnover_rate:.2f} x",
        border=True,
        help="Measures how many times inventory is sold out and replenished over a 90-day cycle."
    )

with kpi_col3:
    st.metric(
        label="Running Profit (Current Month)",
        value=f"₱{running_profit_month:,.2f}",
        #delta=f"₱{running_profit_month:,.2f}" if running_profit_month >= 0 else f"-₱{abs(running_profit_month):,.2f}",
        #delta_color="normal" if running_profit_month >= 0 else "inverse",
        border=True,
        help="Tells exactly how much money they are making on the items they've successfully sold, without letting big, upfront supplier bills distort their daily performance numbers."
    )

with kpi_col4:
    st.metric(
        label="Avg Daily Demand",
        value=f"{int(round(avg_daily_demand_month))} units/day",
        border=True,
        help="The baseline average product volume velocity purchased daily this month."
    )

with st.expander(":material/table_chart: Uploaded Data Preview", expanded=False):
    st.dataframe(df.head(5), use_container_width=True)

st.markdown("---")

####################################################################################################################################################################################
### PART 2

import plotly.graph_objects as go

tab1, tab2, tab3 = st.tabs([
    ":material/monitoring: Operational & Financial Trend Inquiries",
    ":material/emoji_events: Product Performance Rankings",
    ":material/receipt_long: Historical Inventory Ledger & Performance Breakdown",
])

with tab1:
    # --- 1. PRE-PROCESS TEMPORAL DIMENSIONS ---
    df['Year'] = df['arrival_date'].dt.year
    df['Month_Num'] = df['arrival_date'].dt.month
    df['Month_Name'] = df['arrival_date'].dt.strftime('%b')

    # Calculate the financial metrics
    df['total_cost_outlay'] = df['quantity_received'] * df['cost_price']
    df['total_revenue_realized'] = df['quantity_sold'] * df['selling_price']
    df['total_leakage_value'] = df['items_spoiled'] * df['cost_price']


    # --- 2. MAIN CANVAS FILTER INTERFACE (LEFT ALIGNED) ---
    # Create a split where the dropdown sits in the left 25% and the right 75% is a spacer buffer
    filter_wrapper_col, spacer_col = st.columns([1, 3])

    with filter_wrapper_col:
        # Set text alignment back to standard left rules for clean form layout flow
        st.html(
            """
            <style>
                .stSelectbox label { text-align: left !important; width: 100% !important; display: block !important; }
                div[data-testid="stSelectbox"] { margin-right: auto !important; width: 100% !important; }
            </style>
            """
        )

        year_options = ["All Years"] + sorted(list(df['Year'].unique().astype(str)))
        selected_year = st.selectbox(":material/calendar_month: Select Timeline Horizon", options=year_options)


    # --- 3. APPLY FILTER & AGGREGATE ---
    if selected_year == "All Years":
        df['Timeline_Axis'] = df['Year'].astype(str) + " - " + df['Month_Name']
        df_filtered = df.copy()
        df_filtered = df_filtered.sort_values(by=['Year', 'Month_Num'])
        group_col = 'Timeline_Axis'
    else:
        df_filtered = df[df['Year'] == int(selected_year)].copy()
        df_filtered = df_filtered.sort_values(by='Month_Num')
        group_col = 'Month_Name'

    # Grouping all fields simultaneously
    chart_data = df_filtered.groupby(group_col, sort=False)[
        ['total_cost_outlay', 'total_revenue_realized', 'total_leakage_value']
    ].sum().reset_index()

    # --- 4. RENDER SIDE-BY-SIDE CHARTS USING COLUMNS ---
    chart_col1, chart_col2 = st.columns(2)

    # --- CHART A: Capital Outlay vs Revenue ---
    with chart_col1:
        st.markdown("#### Capital Outlay vs. Revenue Realization")
        fig_rev = go.Figure()

        fig_rev.add_trace(go.Bar(
            x=chart_data[group_col],
            y=chart_data['total_cost_outlay'],
            name='Total Cost Price',
            marker_color='#FFA07A', # Soft Coral
            hovertemplate='₱%{y:,.2f}<extra></extra>'
        ))

        fig_rev.add_trace(go.Bar(
            x=chart_data[group_col],
            y=chart_data['total_revenue_realized'],
            name='Total Selling Price',
            marker_color='#20B2AA', # Light Sea Green
            hovertemplate='₱%{y:,.2f}<extra></extra>'
        ))

        fig_rev.update_layout(
            barmode='group', hovermode='x unified',
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            margin=dict(l=40, r=40, t=10, b=40),
            xaxis=dict(title="Timeline Period", tickangle=-45 if selected_year == "All Years" else 0),
            yaxis=dict(title="PHP Value", tickformat="₱,.2f"),
            height=400, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)"
        )
        st.plotly_chart(fig_rev, use_container_width=True)

    # --- CHART B: Capital Outlay vs Leakage Value ---
    with chart_col2:
        st.markdown("#### Capital Outlay vs. Capital Lost to Spoilage")
        fig_leak = go.Figure()

        fig_leak.add_trace(go.Bar(
            x=chart_data[group_col],
            y=chart_data['total_cost_outlay'],
            name='Total Cost Price',
            marker_color='#FFA07A', # Matches left chart for visual consistency
            hovertemplate='₱%{y:,.2f}<extra></extra>'
        ))

        fig_leak.add_trace(go.Bar(
            x=chart_data[group_col],
            y=chart_data['total_leakage_value'],
            name='Total Leakage Cost',
            marker_color='#DC143C', # Crimson Red to indicate waste
            hovertemplate='₱%{y:,.2f}<extra></extra>'
        ))

        fig_leak.update_layout(
            barmode='group', hovermode='x unified',
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            margin=dict(l=40, r=40, t=10, b=40),
            xaxis=dict(title="Timeline Period", tickangle=-45 if selected_year == "All Years" else 0),
            yaxis=dict(title="PHP Value", tickformat="₱,.2f"),
            height=400, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)"
        )
        st.plotly_chart(fig_leak, use_container_width=True)

with tab2:
    # --- 1. COMPUTE AGGREGATIONS BASED ON FILTERED TIMELINE ---
    # Aggregate totals per product name from the filtered dataset (df_filtered from the chart section)
    product_summary = df_filtered.groupby('product_name').agg({
        'quantity_sold': 'sum',
        'selling_price': 'mean',
        'cost_price': 'mean',
        'items_spoiled': 'sum'
    }).reset_index()

    # Calculate total profit per product using the accrual matching approach
    product_summary['Total Revenue'] = product_summary['quantity_sold'] * product_summary['selling_price']
    product_summary['Total COGS'] = product_summary['quantity_sold'] * product_summary['cost_price']
    product_summary['Net Profit (PHP)'] = product_summary['Total Revenue'] - product_summary['Total COGS']

    # Clean up dataframe names and round values for user presentation
    product_summary = product_summary.rename(columns={
        'product_name': 'Product Name',
        'items_spoiled': 'Units Spoiled'
    })


    # --- 2. ISOLATE TOP 5 WINNERS & LOSERS ---
    # Top 5 Profitable Items
    top_profitable = product_summary.sort_values(by='Net Profit (PHP)', ascending=False).head(5)[
        ['Product Name', 'Net Profit (PHP)']
    ].reset_index(drop=True)
    # Add ranking index starting at 1
    top_profitable.index += 1

    # Top 5 Most Spoiled Items
    top_spoiled = product_summary.sort_values(by='Units Spoiled', ascending=False).head(5)[
        ['Product Name', 'Units Spoiled']
    ].reset_index(drop=True)
    top_spoiled.index += 1


    # --- 3. RENDER TABLES SIDE-BY-SIDE IN COLUMNS ---
    table_col1, table_col2 = st.columns(2)

    with table_col1:
        st.markdown("#### :green[:material/trending_up:] Top 5 Most Profitable Products")
        st.dataframe(
            top_profitable.style.format({'Net Profit (PHP)': '₱{:,.2f}'}),
            use_container_width=True
        )

    with table_col2:
        st.markdown("#### :red[:material/trending_down:] Top 5 Highest Spoilage Products")
        st.dataframe(
            top_spoiled.style.format({'Units Spoiled': '{:,.0f} units'}),
            use_container_width=True
        )

with tab3:
    # --- 1. DUAL TIME FILTERS (ALIGNED ON THE LEFT) ---
    # Create two small columns on the left side of the screen for your dropdowns
    filter_col1, filter_col2, spacer_col = st.columns([1.2, 1.2, 2.6])

    with filter_col1:
        year_options = ["All Years"] + sorted(list(df['Year'].unique().astype(str)))
        selected_table_year = st.selectbox(":material/calendar_month: Table Year Horizon", options=year_options, key="table_year_picker")

    # Generate available month filters dynamically based on the selected year
    with filter_col2:
        if selected_table_year == "All Years":
            df_table_filtered = df.copy()
            month_options = ["All Months"]
        else:
            df_table_filtered = df[df['Year'] == int(selected_table_year)].copy()
            # Get list of short month names present in that year (e.g., Jan, Feb)
            sorted_months = df_table_filtered.sort_values('Month_Num')['Month_Name'].unique()
            month_options = ["All Months"] + list(sorted_months)

        selected_table_month = st.selectbox(":material/date_range: Table Month Filter", options=month_options, key="table_month_picker")

    # Apply the month mask if a specific month is selected
    if selected_table_month != "All Months":
        df_table_filtered = df_table_filtered[df_table_filtered['Month_Name'] == selected_table_month]


    # --- 2. CALCULATE HISTORICAL AGGREGATIONS & METRICS ---
    if not df_table_filtered.empty:
        # Group by product name to calculate totals for the selected time window
        ledger_df = df_table_filtered.groupby('product_name').agg({
            'quantity_received': 'sum',
            'quantity_sold': 'sum',
            'items_spoiled': 'sum'
        }).reset_index()

        # Get Current Stock Level: Grab the final recorded shelf balance inside this specific time selection
        latest_rows = df_table_filtered.sort_values('arrival_date').groupby('product_name').last().reset_index()
        stock_mapping = dict(zip(latest_rows['product_name'], latest_rows['current_stock_level']))
        ledger_df['Current Stock Level'] = ledger_df['product_name'].map(stock_mapping)

        # Calculate Profit using the accrual framework (Matched COGS)
        # 1. Grab average wholesale and retail pricing metrics for accuracy
        price_mapping = df_table_filtered.groupby('product_name').agg({'selling_price': 'mean', 'cost_price': 'mean'}).reset_index()
        selling_dict = dict(zip(price_mapping['product_name'], price_mapping['selling_price']))
        cost_dict = dict(zip(price_mapping['product_name'], price_mapping['cost_price']))

        # 2. Run equations
        ledger_df['Profit'] = (ledger_df['quantity_sold'] * ledger_df['product_name'].map(selling_dict)) - \
                               (ledger_df['quantity_sold'] * ledger_df['product_name'].map(cost_dict))

        # Calculate Leakage Cost (Spoiled units multiplied by wholesale cost price)
        ledger_df['Leakage'] = ledger_df['items_spoiled'] * ledger_df['product_name'].map(cost_dict)

        # Rename columns to match clean layout styling
        ledger_df = ledger_df.rename(columns={
            'product_name': 'Product Name',
            'quantity_received': 'Qty Received',
            'quantity_sold': 'Qty Sold',
            'items_spoiled': 'Units Spoiled'
        })
    else:
        ledger_df = pd.DataFrame()


    # --- 3. RENDER THE RETAIL LEDGER DATA FRAME ---
    if not ledger_df.empty:
        st.dataframe(
            ledger_df.style.format({
                'Qty Received': '{:,.0f} units',
                'Qty Sold': '{:,.0f} units',
                'Units Spoiled': '{:,.0f} units',
                'Current Stock Level': '{:,.0f} units',
                'Profit': '₱{:,.2f}',
                'Leakage': '₱{:,.2f}'
            }),
            use_container_width=True,
            hide_index=True
        )
    else:
        st.info("No operational records match this specific Year/Month time filter configuration.")