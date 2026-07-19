"""NovaRetail Customer Intelligence Dashboard.

Streamlit Community Cloud ready. Expects NR_dataset_Clean.csv to live in the
same repository directory as this file.
"""

# ---------------------------------------------------------------- STEP 1 ----
import streamlit as st
import pandas as pd
import plotly.express as px

# ---------------------------------------------------------------- STEP 2 ----
st.set_page_config(
    page_title="NovaRetail Customer Intelligence",
    layout="wide",
)

st.title("NovaRetail Customer Intelligence Dashboard")
st.subheader("Revenue, Segment & Risk Analysis")

DATA_FILE = "NR_dataset_Clean.csv"

REQUIRED_COLUMNS = [
    "label",
    "CustomerID",
    "TransactionDate",
    "ProductCategory",
    "PurchaseAmount",
    "CustomerAgeGroup",
    "CustomerGender",
    "CustomerRegion",
    "CustomerSatisfaction",
    "RetailChannel",
]

RISK_RED = "#C0392B"          # reserved exclusively for risk indicators
NEUTRAL_BLUE = "#2E5E8C"
ACCENT_TEAL = "#3E8E8A"
CHANNEL_COLORS = ["#2E5E8C", "#7FB2D9"]

SATISFACTION_COLORS = {
    "1": "#B35806",   # dark orange
    "2": "#F1A340",   # light orange
    "3": "#BFBFBF",   # neutral gray
    "4": "#8DBFE0",   # light blue
    "5": "#2166AC",   # dark blue
}

ALL = "All"


# ---------------------------------------------------------------- STEP 3 ----
@st.cache_data
def load_data(path: str) -> pd.DataFrame:
    """Load and clean the bundled dataset."""
    frame = pd.read_csv(path)
    frame.columns = [str(c).strip() for c in frame.columns]
    return frame


try:
    df_raw = load_data(DATA_FILE)
except FileNotFoundError:
    st.error("Dataset file NR_dataset_Clean.csv not found in repository.")
    st.stop()
except Exception as exc:  # noqa: BLE001 - surface any load problem gracefully
    st.error(f"Unable to load NR_dataset_Clean.csv: {exc}")
    st.stop()

# ------------------------------------------------- STEP 9 (column validation)
missing_columns = [c for c in REQUIRED_COLUMNS if c not in df_raw.columns]
if missing_columns:
    st.error("Missing required column(s): " + ", ".join(missing_columns))
    st.write(df_raw.columns)
    st.stop()

df = df_raw.copy()
df["TransactionDate"] = pd.to_datetime(df["TransactionDate"], errors="coerce")
df["PurchaseAmount"] = pd.to_numeric(df["PurchaseAmount"], errors="coerce")
df["CustomerSatisfaction"] = pd.to_numeric(
    df["CustomerSatisfaction"], errors="coerce"
)
df = df.dropna(subset=["PurchaseAmount", "TransactionDate"])

if df.empty:
    st.error("The dataset contains no usable rows after cleaning.")
    st.stop()


def options_for(column: str) -> list:
    """Dynamically derive filter options from the loaded data."""
    values = sorted(df[column].dropna().astype(str).unique().tolist())
    return [ALL] + values


# ---------------------------------------------------------------- STEP 4 ----
st.sidebar.header("Filters")

sel_segment = st.sidebar.multiselect(
    "Segment", options_for("label"), default=[ALL]
)
sel_category = st.sidebar.multiselect(
    "Product Category", options_for("ProductCategory"), default=[ALL]
)
sel_region = st.sidebar.multiselect(
    "Region", options_for("CustomerRegion"), default=[ALL]
)
sel_channel = st.sidebar.multiselect(
    "Retail Channel", options_for("RetailChannel"), default=[ALL]
)
sel_age = st.sidebar.multiselect(
    "Age Group", options_for("CustomerAgeGroup"), default=[ALL]
)
sel_gender = st.sidebar.multiselect(
    "Gender", options_for("CustomerGender"), default=[ALL]
)

min_date = df["TransactionDate"].min().date()
max_date = df["TransactionDate"].max().date()

start_date = st.sidebar.date_input(
    "Start Date", value=min_date, min_value=min_date, max_value=max_date
)
end_date = st.sidebar.date_input(
    "End Date", value=max_date, min_value=min_date, max_value=max_date
)

if isinstance(start_date, (list, tuple)):
    start_date = start_date[0]
if isinstance(end_date, (list, tuple)):
    end_date = end_date[-1]

if start_date > end_date:
    start_date, end_date = end_date, start_date


# ---------------------------------------------------------------- STEP 5 ----
def apply_filter(frame: pd.DataFrame, column: str, selection: list) -> pd.DataFrame:
    """Apply a multiselect filter. 'All' only applies when nothing else is picked."""
    if not selection:
        return frame
    picks = [s for s in selection if s != ALL]
    if not picks:
        return frame
    return frame[frame[column].astype(str).isin(picks)]


fdf = df.copy()
fdf = apply_filter(fdf, "label", sel_segment)
fdf = apply_filter(fdf, "ProductCategory", sel_category)
fdf = apply_filter(fdf, "CustomerRegion", sel_region)
fdf = apply_filter(fdf, "RetailChannel", sel_channel)
fdf = apply_filter(fdf, "CustomerAgeGroup", sel_age)
fdf = apply_filter(fdf, "CustomerGender", sel_gender)

date_mask = (fdf["TransactionDate"] >= pd.Timestamp(start_date)) & (
    fdf["TransactionDate"] <= pd.Timestamp(end_date)
)
fdf = fdf[date_mask]

st.sidebar.caption(f"{len(fdf):,} rows currently selected")

if fdf.empty:
    st.warning(
        "No transactions match the selected filters. "
        "Please broaden your selection."
    )
    st.stop()


# ---------------------------------------------------------------- STEP 6 ----
total_revenue = float(fdf["PurchaseAmount"].sum())
decline_mask = fdf["label"].astype(str).str.strip().str.lower() == "decline"
revenue_at_risk = float(fdf.loc[decline_mask, "PurchaseAmount"].sum())
risk_pct = (revenue_at_risk / total_revenue * 100) if total_revenue else 0.0
transactions = int(len(fdf))
unique_customers = int(fdf["CustomerID"].nunique())
median_purchase = float(fdf["PurchaseAmount"].median())
mean_purchase = float(fdf["PurchaseAmount"].mean())
satisfaction_series = fdf["CustomerSatisfaction"].dropna()
avg_satisfaction = float(satisfaction_series.mean()) if not satisfaction_series.empty else 0.0

k1, k2, k3, k4, k5 = st.columns(5)

with k1:
    st.metric("Total Revenue", f"${total_revenue:,.2f}")

with k2:
    st.metric("Revenue at Risk", f"${revenue_at_risk:,.2f}")
    st.caption(f"{risk_pct:.1f}% of filtered revenue (Decline segment)")

with k3:
    st.metric("Transactions", f"{transactions:,}")
    st.caption(f"{unique_customers:,} unique customers")

with k4:
    st.metric("Median Purchase", f"${median_purchase:,.2f}")
    st.caption(f"Mean: ${mean_purchase:,.2f}")

with k5:
    st.metric("Avg Satisfaction", f"{avg_satisfaction:.1f} / 5")

st.divider()


# ---------------------------------------------------------------- STEP 7 ----
CURRENCY_AXIS = dict(tickprefix="$", tickformat=",.0f")

row1_left, row1_right = st.columns(2)

# --- C1 Revenue by Segment ---------------------------------------------------
with row1_left:
    seg_rev = (
        fdf.groupby("label", as_index=False)["PurchaseAmount"]
        .sum()
        .sort_values("PurchaseAmount", ascending=False)
    )
    seg_order = seg_rev["label"].tolist()
    seg_colors = [
        RISK_RED if str(s).strip().lower() == "decline" else NEUTRAL_BLUE
        for s in seg_order
    ]
    fig1 = px.bar(
        seg_rev,
        x="label",
        y="PurchaseAmount",
        template="plotly_white",
        title="Revenue by Customer Segment",
        labels={"label": "Customer Segment", "PurchaseAmount": "Revenue (USD)"},
        text="PurchaseAmount",
    )
    fig1.update_traces(
        marker_color=seg_colors,
        texttemplate="$%{text:,.0f}",
        textposition="outside",
        hovertemplate="<b>%{x}</b><br>Revenue: $%{y:,.2f}<extra></extra>",
    )
    fig1.update_xaxes(categoryorder="array", categoryarray=seg_order,
                      title_text="Customer Segment")
    fig1.update_yaxes(title_text="Revenue (USD)", **CURRENCY_AXIS)
    fig1.update_layout(margin=dict(t=60, b=40, l=40, r=20))
    st.plotly_chart(fig1, use_container_width=True)

# --- C2 Revenue by Product Category -----------------------------------------
with row1_right:
    cat_rev = (
        fdf.groupby("ProductCategory", as_index=False)["PurchaseAmount"]
        .sum()
        .sort_values("PurchaseAmount", ascending=True)  # ascending -> largest on top
    )
    fig2 = px.bar(
        cat_rev,
        x="PurchaseAmount",
        y="ProductCategory",
        orientation="h",
        template="plotly_white",
        title="Revenue by Product Category",
        labels={
            "ProductCategory": "Product Category",
            "PurchaseAmount": "Revenue (USD)",
        },
    )
    fig2.update_traces(
        marker_color=ACCENT_TEAL,
        hovertemplate="<b>%{y}</b><br>Revenue: $%{x:,.2f}<extra></extra>",
    )
    fig2.update_yaxes(
        categoryorder="array",
        categoryarray=cat_rev["ProductCategory"].tolist(),
        title_text="Product Category",
    )
    fig2.update_xaxes(title_text="Revenue (USD)", **CURRENCY_AXIS)
    fig2.update_layout(margin=dict(t=60, b=40, l=40, r=20))
    st.plotly_chart(fig2, use_container_width=True)

row2_left, row2_right = st.columns(2)

# --- C3 Satisfaction Distribution by Segment --------------------------------
with row2_left:
    sat_df = fdf.dropna(subset=["CustomerSatisfaction"]).copy()
    if sat_df.empty:
        st.info("No satisfaction scores available for the current selection.")
    else:
        sat_df["SatisfactionLabel"] = (
            sat_df["CustomerSatisfaction"].astype(int).astype(str)
        )
        counts = (
            sat_df.groupby(["label", "SatisfactionLabel"], as_index=False)
            .size()
            .rename(columns={"size": "Transactions"})
        )
        totals = counts.groupby("label")["Transactions"].transform("sum")
        counts["Percentage"] = counts["Transactions"] / totals * 100

        sat_order = sorted(
            sat_df["SatisfactionLabel"].unique().tolist(), key=lambda v: int(v)
        )
        fig3 = px.bar(
            counts,
            x="Percentage",
            y="label",
            color="SatisfactionLabel",
            orientation="h",
            template="plotly_white",
            title="Satisfaction Distribution by Segment",
            color_discrete_map=SATISFACTION_COLORS,
            category_orders={
                "SatisfactionLabel": sat_order,
                "label": [s for s in seg_order if s in set(counts["label"])],
            },
            labels={
                "Percentage": "Share of Transactions (%)",
                "label": "Customer Segment",
                "SatisfactionLabel": "Satisfaction",
            },
            custom_data=["Transactions"],
        )
        fig3.update_traces(
            hovertemplate=(
                "<b>%{y}</b><br>Share: %{x:.1f}%"
                "<br>Transactions: %{customdata[0]}<extra></extra>"
            )
        )
        fig3.update_xaxes(
            title_text="Share of Transactions (%)",
            range=[0, 100],
            ticksuffix="%",
        )
        fig3.update_yaxes(title_text="Customer Segment")
        fig3.update_layout(
            barmode="stack",
            legend_title_text="Satisfaction",
            margin=dict(t=60, b=40, l=40, r=20),
        )
        st.plotly_chart(fig3, use_container_width=True)

# --- C4 Revenue by Region and Channel ---------------------------------------
with row2_right:
    reg_rev = (
        fdf.groupby(["CustomerRegion", "RetailChannel"], as_index=False)[
            "PurchaseAmount"
        ].sum()
    )
    region_order = (
        reg_rev.groupby("CustomerRegion")["PurchaseAmount"]
        .sum()
        .sort_values(ascending=False)
        .index.tolist()
    )
    fig4 = px.bar(
        reg_rev,
        x="CustomerRegion",
        y="PurchaseAmount",
        color="RetailChannel",
        barmode="group",
        template="plotly_white",
        title="Revenue by Region and Channel",
        color_discrete_sequence=CHANNEL_COLORS,
        category_orders={"CustomerRegion": region_order},
        labels={
            "CustomerRegion": "Region",
            "PurchaseAmount": "Revenue (USD)",
            "RetailChannel": "Retail Channel",
        },
    )
    fig4.update_traces(
        hovertemplate="<b>%{x}</b><br>Revenue: $%{y:,.2f}<extra></extra>"
    )
    fig4.update_xaxes(title_text="Region")
    fig4.update_yaxes(title_text="Revenue (USD)", **CURRENCY_AXIS)
    fig4.update_layout(
        legend_title_text="Retail Channel",
        margin=dict(t=60, b=40, l=40, r=20),
    )
    st.plotly_chart(fig4, use_container_width=True)

# --- C5 Daily Revenue Trend (full width) ------------------------------------
daily = (
    fdf.set_index("TransactionDate")["PurchaseAmount"]
    .resample("D")
    .sum()
)
full_range = pd.date_range(
    start=fdf["TransactionDate"].min().normalize(),
    end=fdf["TransactionDate"].max().normalize(),
    freq="D",
)
daily = daily.reindex(full_range, fill_value=0).reset_index()
daily.columns = ["TransactionDate", "PurchaseAmount"]

fig5 = px.line(
    daily,
    x="TransactionDate",
    y="PurchaseAmount",
    markers=True,
    template="plotly_white",
    title="Daily Revenue Trend",
    labels={"TransactionDate": "Date", "PurchaseAmount": "Revenue (USD)"},
)
fig5.update_traces(
    line_color=NEUTRAL_BLUE,
    hovertemplate="<b>%{x|%Y-%m-%d}</b><br>Revenue: $%{y:,.2f}<extra></extra>",
)
fig5.update_xaxes(title_text="Date", tickformat="%b %d")
fig5.update_yaxes(title_text="Revenue (USD)", **CURRENCY_AXIS)
fig5.update_layout(margin=dict(t=60, b=40, l=40, r=20))
st.plotly_chart(fig5, use_container_width=True)
st.caption(
    "Data covers 36 days (Jan 15 - Feb 20, 2023). Daily granularity only; "
    "the window is too short to support seasonality analysis."
)

st.divider()


# ---------------------------------------------------------------- STEP 8 ----
st.header("Transaction Detail")

detail = fdf.copy()
detail["TransactionDate"] = detail["TransactionDate"].dt.strftime("%Y-%m-%d")
detail = detail[REQUIRED_COLUMNS]

st.dataframe(detail, hide_index=True, use_container_width=True)
