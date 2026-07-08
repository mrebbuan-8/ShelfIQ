import streamlit as st
import pandas as pd

st.set_page_config(page_title="Marketing Action Engine", layout="wide")

st.title(":material/campaign: Marketing Action Engine")
st.markdown(
    "Turns each item's spoilage risk into a concrete next business action: "
    "discount it, upcycle it, or leave it alone."
)

# STEP 0: CONFIG - the one place you edit once RUL variable names change
COLUMN_MAP = {
    "days_left": "days_to_sell",       # comes from the RUL page's active_risks export
    "product_name": "product_name",
    "product_category": "product_category",
    "items_spoiled": "items_spoiled",
    "cost_price": "cost_price",
    "selling_price": "selling_price",
}


# STEP 1: PILLAR 1 - THE DISCOUNT TIER LOGIC (4 tiers)

def get_discount_tier(days_left, items_spoiled: int = 0):
    if items_spoiled and items_spoiled > 0:
        return "Out of Scope (Spoiled)", None

    if days_left is None or pd.isna(days_left):
        return "Unknown", None

    if days_left < 0:
        return "Out of Scope (Spoiled)", None
    elif days_left < 1:
        return "Tier 4: Final Markdown", 0.40
    elif days_left <= 2:
        return "Tier 3: Priority Sell", 0.20
    elif days_left <= 5:
        return "Tier 2: Early Markdown", 0.08
    else:
        return "Tier 1: Watch", 0.0


# STEP 2: PILLAR 2 - THE UPCYCLING LOGIC (fixed to match real data)

UPCYCLE_RULES = {
    # --- Dairy ---
    "Fresh Milk 1L":              ["Cottage Cheese", "Milk Pudding Cups"],
    "Greek Yogurt 500g":          ["Yogurt Popsicles", "Yogurt Smoothie Packs"],
    "Chilled Cheese Block 500g":  ["Cheese Spread", "Cheese Sauce Base"],

    # --- Produce ---
    "Premium Berries 250g":       ["Berry Jam", "Fruit Compote"],
    "Organic Salad Mix":          ["Vegetable Soup Pack", "Stir-Fry Mix"],
    "Local Calamansi Pack 500g":  ["Calamansi Concentrate", "Calamansi Marmalade"],

    # --- Beverages ---
    "Cold Brew Coffee 250ml":     ["Coffee Concentrate Syrup", "Coffee Jelly Cups"],
    "Chilled Fruit Juice 1L":     ["Fruit Popsicles", "Fruit Sorbet"],
}


def get_upcycle_suggestion(product_name: str, tier: str):
    """
    Only recommends upcycling when:
      1. The item is already urgent (Tier 3 or Tier 4), AND
      2. Its specific product has a matching transformation on file.

    Returns a list of possible upcycled products, or None.
    """
    urgent_tiers = ["Tier 3: Priority Sell", "Tier 4: Final Markdown"]

    if tier in urgent_tiers and product_name in UPCYCLE_RULES:
        return UPCYCLE_RULES[product_name]

    return None


# STEP 3: WHERE THE TWO PILLARS MEET

def get_marketing_action(days_left, product_name: str, items_spoiled: int = 0):
    """
    This is the 'front desk' function -- it runs Pillar 1, then decides
    whether Pillar 2 should join in, following the exact decision path
    from the two-pillar workflow diagram:

        Tier 1 (Watch)          -> discount only (0%, e.g., no action)
        Tier 2 (Early Markdown) -> discount only
        Tier 3 (Priority Sell)  -> match found? recommend upcycle
                                    ALONGSIDE the discount
                                 -> no match? discount only
        Tier 4 (Final Markdown) -> match found? STRONGLY recommend
                                    upcycle (better value than discount)
                                 -> no match? discount only
        Spoiled                 -> out of scope entirely
    """
    tier, discount_pct = get_discount_tier(days_left, items_spoiled)
    upcycle_options = get_upcycle_suggestion(product_name, tier)

    if tier in ("Out of Scope (Spoiled)", "Unknown"):
        action_type = "none"
    elif tier == "Tier 1: Watch":
        action_type = "No Action Needed"
    elif upcycle_options and tier == "Tier 3: Priority Sell":
        action_type = "Upcycle Optional (Alongside Discount)"
    elif upcycle_options and tier == "Tier 4: Final Markdown":
        action_type = "Upcycle Strongly Recommended"
    else:
        action_type = "Discount Only"

    return {
        "tier": tier,
        "discount_pct": discount_pct,
        "upcycle_options": upcycle_options,
        "action_type": action_type,
    }


# STEP 4: THE PROFIT CALCULATION (simple before/after comparison, per spec)

def estimate_upcycle_recovery(selling_price: float, discount_pct: float,
                               labor_cost_php: float = 20.0,
                               upcycle_price_uplift: float = 1.20) -> dict:
    """
    A simple, assumption-based comparison (NOT a second ML model --
    the spec is explicit that a lookup + manual cost assumption is
    all this needs). Compares:
        - what the item would fetch if just discounted raw
        - what it could fetch if turned into a finished, upcycled product
    """
    if selling_price is None or pd.isna(selling_price):
        return {"discounted_raw_value": None, "upcycled_value": None, "recovery_php": None}

    discounted_raw_value = selling_price * (1 - discount_pct)
    upcycled_value = (selling_price * upcycle_price_uplift) - labor_cost_php
    recovery_php = round(upcycled_value - discounted_raw_value, 2)

    return {
        "discounted_raw_value": round(discounted_raw_value, 2),
        "upcycled_value": round(upcycled_value, 2),
        "recovery_php": recovery_php,
    }


# ============================================================
# STEP 5: APPLYING THIS TO A WHOLE INVENTORY TABLE (DataFrame)
# ============================================================
def apply_marketing_actions(df: pd.DataFrame) -> pd.DataFrame:
    """
    Takes the risk-flagged DataFrame (from st.session_state['active_risks'],
    produced by the RUL page) and adds the marketing columns the dashboard
    and this page render.
    """
    days_col = COLUMN_MAP["days_left"]
    name_col = COLUMN_MAP["product_name"]
    spoiled_col = COLUMN_MAP["items_spoiled"]
    price_col = COLUMN_MAP["selling_price"]

    df = df.copy()
    actions = df.apply(
        lambda row: get_marketing_action(
            row.get(days_col),
            row.get(name_col),
            row.get(spoiled_col, 0),
        ),
        axis=1,
    )

    df["tier"] = actions.apply(lambda r: r["tier"])
    df["discount_pct"] = actions.apply(lambda r: r["discount_pct"])
    df["upcycle_options"] = actions.apply(lambda r: r["upcycle_options"])
    df["action_type"] = actions.apply(lambda r: r["action_type"])

    # Only compute recovery estimates where a discount % actually exists
    recovery = df.apply(
        lambda row: estimate_upcycle_recovery(row.get(price_col), row["discount_pct"])
        if row["upcycle_options"] is not None else
        {"discounted_raw_value": None, "upcycled_value": None, "recovery_php": None},
        axis=1,
    )
    df["discounted_raw_value_php"] = recovery.apply(lambda r: r["discounted_raw_value"])
    df["upcycled_value_php"] = recovery.apply(lambda r: r["upcycled_value"])
    df["upcycle_recovery_php"] = recovery.apply(lambda r: r["recovery_php"])

    return df


# ============================================================
# STEP 6: STREAMLIT PAGE
# ============================================================
if "active_risks" not in st.session_state:
    st.warning(
        "No spoilage risk results yet. Please run the spoilage model on the "
        "**RUL Model** page first, then come back here for marketing recommendations."
    )
    st.stop()

result = apply_marketing_actions(st.session_state["active_risks"])
st.session_state["marketing_actions"] = result

st.divider()

# --- KPI SUMMARY ---
actionable = result[~result["tier"].isin(["Out of Scope (Spoiled)", "Unknown"])]
total_recovery = actionable["upcycle_recovery_php"].dropna()
total_recovery = total_recovery[total_recovery > 0].sum()
upcycle_count = result["action_type"].isin(
    ["upcycle_recommended_alongside_discount", "upcycle_strongly_recommended"]
).sum()

kpi1, kpi2, kpi3 = st.columns(3)
kpi1.metric("Items Flagged for Action", f"{len(actionable):,}")
kpi2.metric("Items Recommended for Upcycling", f"{upcycle_count:,}")
kpi3.metric("Extra Value Recoverable vs. Discount-Only", f"₱{total_recovery:,.2f}")

st.divider()

# --- FILTER + TABLE ---
tier_options = ["All Tiers"] + sorted(result["tier"].unique().tolist())
selected_tier = st.selectbox("Filter by tier", options=tier_options)

display_df = result if selected_tier == "All Tiers" else result[result["tier"] == selected_tier]

display_df = display_df.rename(columns={
    "item_sku": "SKU",
    "product_name": "Product Name",
    "product_category": "Category",
    "tier": "Tier",
    "discount_pct": "Discount %",
    "upcycle_options": "Upcycle Options",
    "action_type": "Action Type",
    "upcycle_recovery_php": "Extra Recovery (₱)",
})

# Convert decimal fraction (0.0–0.40) to percentage points (0–40) for display only
display_df["Discount %"] = display_df["Discount %"] * 100

st.dataframe(
    display_df[[
        "SKU", "Product Name", "Category", "Tier", "Discount %",
        "Action Type", "Upcycle Options", "Extra Recovery (₱)",
    ]],
    use_container_width=True,
    hide_index=True,
    column_config={
        "Discount %": st.column_config.NumberColumn(format="%.0f%%"),
        "Extra Recovery (₱)": st.column_config.NumberColumn(format="₱%.2f"),
    },
)

csv = result.to_csv(index=False).encode("utf-8")
st.download_button(
    "Download Marketing Actions (CSV)",
    data=csv,
    file_name="marketing_actions.csv",
    mime="text/csv",
)
