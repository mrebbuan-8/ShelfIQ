import pandas as pd
import numpy as np
import streamlit as st
from streamlit_calendar import calendar
from datetime import datetime, timedelta

from xgboost import XGBRegressor

# this is meant for data analysis, preprocessing, and model training for the forecasting task

# five sections
# upload csv
# preprocess data
# train model
# user chooses forecast horizon
# generate forecast + display calendar

def inventory_replenishment(
    forecast_df,
    current_inventory,
    safety_stock=20
):
    """
    Uses forecasted demand to determine:
    - Expected End-of-Day inventory
    - Restock day
    - Restock quantity
    """

    forecast = forecast_df.copy()

    remaining_inventory = current_inventory

    projected_inventory = []
    restock_day = None

    for i, demand in enumerate(forecast["Forecast Qty"]):

        remaining_inventory -= demand
        projected_inventory.append(remaining_inventory)

        if restock_day is None and remaining_inventory <= safety_stock:
            restock_day = i + 1

    forecast["Projected Inventory"] = projected_inventory

    if restock_day is None:

        recommendation = "Inventory is sufficient."

        reorder_qty = 0

    else:

        future_demand = forecast.iloc[restock_day-1:]["Forecast Qty"].sum()

        reorder_qty = future_demand + safety_stock

        recommendation = (
            f"Restock {reorder_qty} units "
            f"in {restock_day} day(s)"
        )

    return forecast, recommendation

def forecast_future(xgb_model, df, sku, forecast_days):
    
    # filter one SKU
    sku_df = (
        df[df["item_sku"]== sku]
        .sort_values("order_date")
        .copy()
    )
    
    # historical demand
    history = sku_df['daily_demand'].tolist()
    
    # last available date
    last_date = sku_df['order_date'].max()
    
    predictions = []
    dates = []
    
    for day in range(forecast_days):
        
        future_input = pd.DataFrame({
            "lag_1":[history[-1]],
            "lag_7":[history[-7]],
            "lag_14": [history[-14]],
            "lag_30": [history[-30]]
        })
        
        prediction = float(xgb_model.predict(future_input)[0])
        
        predictions.append(round(prediction, 2))
        
        dates.append(last_date + pd.Timedelta(days=day + 1))
        
        history.append(prediction)
        
    forecast_df = pd.DataFrame({
        "Forecast Date": dates,
        "Forecast Demand": predictions
    })

    return forecast_df



# # initialize page configuration
# st.title("Inventory Forecasting")
# st.set_page_config(layout='wide',
#                    page_title='Inventory Forecasting and Replenishment Decision Support System'
# )



# # title
st.title(":material/insights: Inventory Forecasting and Replenishment Decision Support System")
st.subheader("A machine learning–based inventory forecasting and decision support system.")

# # csv upload
# uploaded_file = st.file_uploader('upload your csv file', type=['csv'])

# if uploaded_file:
#     df = pd.read_csv(uploaded_file)

# --- DATA RETRIEVAL BRIDGE ---
# Check if the user uploaded a file in app.py first
if "master_data" in st.session_state:
    df = st.session_state["master_data"].copy()
    st.success("✅ Displaying metrics from the live user-uploaded dataset.")
else:
    # LOCAL DEVELOPMENT FALLBACK
    try:
        df = pd.read_csv("capstone_dataset_2years.csv")
        df["arrival_date"] = pd.to_datetime(df["arrival_date"])
        df["order_date"] = pd.to_datetime(df["order_date"])

        st.session_state["master_data"] = df

        st.warning(
            "No inventory file has been uploaded yet, so we're showing sample data for now. "
            "Upload your store's CSV from the sidebar to see your own forecast."
        )

    except FileNotFoundError:
        st.error(
            "We need your inventory file to generate a forecast. "
            "Please upload your CSV using the sidebar to continue."
        )
        st.stop()

    
# to prevent alteration
df_copy = df.copy()

# standardize column names
df_copy.rename(columns={"Product Origin":"product_origin", "Order Transaction ID":"order_id", "shelf life days":"shelf_life_days"}, inplace=True)

# convert dates to datetime types
df_copy['order_date'] = pd.to_datetime(df_copy['order_date'])
df_copy['arrival_date'] = pd.to_datetime(df_copy['arrival_date'])
# convert data to tabular format

# sort data by SKU and order date
df_copy = (
    df_copy
    .sort_values(by=['item_sku', 'order_date'])
    .reset_index(drop=True)
)

# lag features
# lag 1: previous day's demand
df_copy['lag_1'] = (
    df_copy
    .groupby('item_sku')['daily_demand']
    .shift(1)
)

# lag 7: one week ago demand
df_copy['lag_7'] = (
    df_copy
    .groupby('item_sku')['daily_demand']
    .shift(7)
)

# lag 14: two weeks ago demand
df_copy['lag_14'] = (
    df_copy
    .groupby('item_sku')['daily_demand']
    .shift(14)
)

# lag 30: month ago demand
df_copy['lag_30'] = (
    df_copy
    .groupby('item_sku')['daily_demand']
    .shift(30)
)

    # Lag features answer: "What happened on a specific previous day?"
# Rolling mean features answer: "What has demand been like recently, on average?"

# To predict:
# 'What to restock?'
# 'When to restock?'
# 'How much to restock?'

# The model benefits from knowing both:
# yesterday's demand (lag_1)
# the recent demand trend (rolling_mean_7)


# 7 day rolling average demand
df_copy['rolling_mean_7'] = (
    df_copy
    .groupby("item_sku")['daily_demand']
    .transform(lambda x: x.rolling(window=7).mean())
)

# 30 days rolling average demand
df_copy['rolling_mean_30'] = (
    df_copy
    .groupby("item_sku")['daily_demand']
    .transform(lambda x: x.rolling(window=30).mean())
)

df_copy = df_copy.dropna().reset_index(drop=True)


forecast_horizon = 7

train = (
    df_copy
    .groupby("item_sku", group_keys=False)
    .apply(lambda x: x.iloc[:-forecast_horizon])
    .reset_index(drop=True)
)

test = (
    df_copy
    .groupby("item_sku", group_keys=False)
    .apply(lambda x: x.iloc[-forecast_horizon:])
    .reset_index(drop=True)
)

# train test sets
x_train = train[['lag_1', 'lag_7', 'lag_14', 'lag_30']]
y_train = train['daily_demand']

x_test = test[['lag_1', 'lag_7', 'lag_14', 'lag_30']]
y_test = test['daily_demand']

# Train XGBoost
xgb = XGBRegressor(random_state=42)
xgb.fit(x_train, y_train)
y_pred_xgb = xgb.predict(x_test)


if "forecast_days" not in st.session_state:
    st.session_state.forecast_days = None
    
st.subheader("Forecast Horizon")

col1, col2, col3 = st.columns(3)

if col1.button("7 Days Forecast", use_container_width=True):
    st.session_state.forecast_days = 7

if col2.button("14 Days Forecast", use_container_width=True):
    st.session_state.forecast_days = 14
    
if col3.button("30 Days Forecast", use_container_width=True):
    st.session_state.forecast_days = 30


current_inventory = st.number_input(
    "Current Inventory",
    min_value=0,
    value=120,
    step=1
)

safety_stock = st.number_input(
    "Safety Stock",
    min_value=0,
    value=20,
    step=1,
    help="Minimum inventory level before a restock is recommended."
)


if st.session_state.forecast_days is not None:
    
    all_forecasts = []
    
    for sku in df_copy['item_sku'].unique() :
        
        forecast = forecast_future(
            xgb_model=xgb,
            df=df_copy,
            sku=sku,
            forecast_days=st.session_state.forecast_days
        )
        
        product_name = (
            df_copy.loc[
                df_copy['item_sku'] == sku,
                "product_name"
            ].iloc[0]
        )
        
        forecast['item_sku'] = sku
        forecast['product_name'] = product_name
        

        forecast["Forecast Qty"] = (
            forecast["Forecast Demand"]
            .round()
            .astype(int)
        )

        forecast, recommendation = inventory_replenishment(
            forecast_df=forecast,
            current_inventory=current_inventory,
            safety_stock=safety_stock
        )

        forecast["Current Inventory"] = current_inventory
        forecast["Recommendation"] = recommendation 
        
        all_forecasts.append(forecast)
        
    forecast_results = pd.concat(
            all_forecasts,
            ignore_index=True
        )
    
    
    st.success(f"{st.session_state.forecast_days}-Day Forecast Generated")
        
    # calendar events
    calendar_events = []
    
    summary = (
        forecast_results
        .groupby("Forecast Date")
        .agg(
            Items=('product_name', 'nunique'),
            Units=('Forecast Qty', 'sum')
        )
        .reset_index()
    )
    
    for _, row in summary.iterrows():
        
        calendar_events.append(
            {
                "title": f"Forecast: {row['Items']} Items | {row['Units']} Units 📦",
                "start": row['Forecast Date'].strftime("%Y-%m-%d"),
                "end": row['Forecast Date'].strftime("%Y-%m-%d")
            }
        )
        
        
    calendar_options = {
        "initialView": "dayGridMonth",
        "selectable": True,
        "editable" : True,
        "contentHeight": 600,
    }
    
    calendar_data = calendar(
        events=calendar_events,
        options=calendar_options,
        custom_css="""
                .fc-toolbar-title {
                    font-size: 2rem;
                    font-weight: 700;
                }

                .fc-daygrid-event {
                    border-radius: 8px;
                    padding: 2px 6px;
                    font-size: 0.85rem;
                }

                .fc-event-title {
                    font-weight: 600;
                }

                .fc-daygrid-day-number {
                    font-weight: 600;
                }

                .fc-col-header-cell {
                    font-weight: bold;
                }

                .fc-day-today {
                    background-color: rgba(255, 215, 0, 0.12) !important;
                }
            """,
        key="calendar"
    )
    
    # for clicked calendar date
    clicked_date = None
    
    if (
        calendar_data
        and calendar_data.get("callback") == "eventClick"
    ):
        
        clicked_date = pd.to_datetime(
            calendar_data['eventClick']['event']['start']
        )
    
    # product filter
    st.subheader("🛒 Restock Schedule")
    
    products = ['All'] + sorted(
        forecast_results['product_name'].unique().tolist()
    )
    
    selected_product = st.selectbox(
        "Filter by Product",
        products
    )  
    
    if selected_product != "All":

        selected_data = forecast_results[
            forecast_results["product_name"] == selected_product
        ]

        current_inventory = selected_data["Current Inventory"].iloc[0]

        today_demand = selected_data["Forecast Qty"].iloc[0]

        eod_inventory = (
            current_inventory
            - today_demand
        )

        recommendation = selected_data["Recommendation"].iloc[0]

        c1, c2, c3 = st.columns(3)

        c1.metric(
            "Current Inventory",
            current_inventory
        )

        c2.metric(
            "Today's Forecast",
            today_demand
        )

        c3.metric(
            "Expected End of Day",
            eod_inventory
        )

        st.success(recommendation)
        
    
    # start with all forecasts
    filtered = forecast_results.copy()
    
    if clicked_date is not None:
        
        st.info(
            f"Showing forecasts for **{clicked_date.strftime('%B %d, %Y')}**"
        )
        
        filtered = filtered[
            filtered['Forecast Date'] == clicked_date
        ]
    
    if selected_product != "All":
        
        filtered = filtered[
            filtered['product_name'] == selected_product
        
        ]
    
    filtered = filtered.rename(columns={
        "product_name": "Product Name",
        "Forecast Qty": "Forecasted Quantity"
        }
    )
    
    # remove time from forecsat date
    filtered['Forecast Date'] = filtered['Forecast Date'].dt.strftime("%B %d, %Y")
        
    # display table    
    st.dataframe(
        
        filtered[
            [
                "Product Name",
                "Recommendation",
                "Forecasted Quantity",
                "Forecast Date"
            ]
        ],
        use_container_width=True
    )