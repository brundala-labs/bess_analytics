"""
ENKA RTM/Market Settlement Reconciliation

Settlement verification, dispute detection, and revenue reconciliation.
"""

import sys
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from dashboard.components.branding import apply_enka_theme, render_sidebar_branding, render_footer, style_plotly_chart
from dashboard.components.header import get_dashboard_config, render_header, render_filter_bar
from db.loader import get_connection

st.set_page_config(initial_sidebar_state="expanded", page_title="RTM Settlement", page_icon="📑", layout="wide")

# Apply ENKA branding
apply_enka_theme()
render_sidebar_branding()


DASHBOARD_KEY = "enka_rtm_settlement"


@st.cache_data(ttl=300)
def load_settlement_data():
    """Load settlement and reconciliation data."""
    conn = get_connection()

    # Daily settlements
    settlements = conn.execute("""
        SELECT
            s.date,
            s.site_id,
            d.name as site_name,
            s.service_id,
            svc.name as service_name,
            s.revenue_gbp,
            s.energy_mwh,
            s.avg_price_gbp_per_mwh
        FROM fact_settlement s
        JOIN dim_site d ON s.site_id = d.site_id
        JOIN dim_service svc ON s.service_id = svc.service_id
        ORDER BY s.date DESC
    """).df()

    # Revenue vs forecast
    revenue_vs_forecast = conn.execute("""
        SELECT
            date,
            site_id,
            site_name,
            actual_revenue,
            forecast_revenue,
            revenue_gap
        FROM v_revenue_loss_attribution
        ORDER BY date DESC
    """).df()

    # Data quality impact
    data_quality = conn.execute("""
        SELECT
            site_id,
            date,
            avg_completeness,
            total_missing_tags
        FROM v_data_quality_daily
        ORDER BY date DESC
    """).df()

    # Dispatch compliance
    dispatch_compliance = conn.execute("""
        SELECT
            site_id,
            date,
            dispatch_count,
            compliance_pct,
            total_deviation_mw
        FROM v_dispatch_compliance
        ORDER BY date DESC
    """).df()

    sites = conn.execute("SELECT site_id, name FROM dim_site").df().to_dict(orient="records")

    conn.close()
    return settlements, revenue_vs_forecast, data_quality, dispatch_compliance, sites


def main():
    settlements, revenue_vs_forecast, data_quality, dispatch_compliance, sites = load_settlement_data()

    # Calculate KPIs
    settled_mtd = settlements[
        settlements["date"] >= settlements["date"].max().replace(day=1)
    ]["revenue_gbp"].sum() if not settlements.empty else 0

    unreconciled = abs(revenue_vs_forecast["revenue_gap"].sum()) if not revenue_vs_forecast.empty else 0

    missing_intervals = data_quality[data_quality["avg_completeness"] < 95].shape[0]

    dispatch_accuracy = dispatch_compliance["compliance_pct"].mean() if not dispatch_compliance.empty else 0

    avg_price = settlements["avg_price_gbp_per_mwh"].mean() if not settlements.empty else 0

    # Settled energy MTD
    settled_energy = settlements[
        settlements["date"] >= settlements["date"].max().replace(day=1)
    ]["energy_mwh"].sum() if not settlements.empty else 0

    # Dispatch variance (100 - compliance)
    dispatch_variance = 100 - dispatch_accuracy if dispatch_accuracy else 0

    kpi_values = {
        "settled_revenue_gbp": settled_mtd,
        "settled_energy_mwh": settled_energy,
        "avg_price_gbp_mwh": avg_price,
        "dispatch_variance_pct": dispatch_variance,
    }

    config = get_dashboard_config(DASHBOARD_KEY)

    kpis = []
    for kpi_def in config.get("kpis", []):
        kpis.append({
            "label": kpi_def.get("label"),
            "value": kpi_values.get(kpi_def.get("metric")),
            "format": kpi_def.get("format", "number"),
        })

    render_header(
        title=config.get("title"),
        personas=config.get("personas", []),
        decisions=config.get("decisions", []),
        data_sources=config.get("data_sources", []),
        freshness=config.get("freshness", ""),
        kpis=kpis,
    )

    # Filters
    filters = render_filter_bar(show_site=True, show_date_range=True, sites=sites)

    # Filter data
    filtered_settlements = settlements.copy()
    filtered_forecast = revenue_vs_forecast.copy()

    if filters.get("site_id"):
        filtered_settlements = filtered_settlements[filtered_settlements["site_id"] == filters["site_id"]]
        filtered_forecast = filtered_forecast[filtered_forecast["site_id"] == filters["site_id"]]

    # Charts
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Daily Settled Revenue")
        if not filtered_settlements.empty:
            daily = filtered_settlements.groupby("date")["revenue_gbp"].sum().reset_index()
            fig = px.bar(daily, x="date", y="revenue_gbp", title="Settlement by Day (£)")
            fig.update_layout(height=300)
            st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.subheader("Revenue by Service")
        if not filtered_settlements.empty:
            by_service = filtered_settlements.groupby("service_name")["revenue_gbp"].sum().reset_index()
            fig = px.pie(by_service, values="revenue_gbp", names="service_name", title="Revenue Split by Service")
            fig.update_layout(height=300)
            st.plotly_chart(fig, use_container_width=True)

    # Forecast vs Actual
    st.subheader("Actual vs Forecast Revenue")
    if not filtered_forecast.empty:
        daily_comparison = filtered_forecast.groupby("date").agg({
            "actual_revenue": "sum",
            "forecast_revenue": "sum"
        }).reset_index()

        fig = go.Figure()
        fig.add_trace(go.Bar(x=daily_comparison["date"], y=daily_comparison["forecast_revenue"],
                            name="Forecast", marker_color="lightblue"))
        fig.add_trace(go.Bar(x=daily_comparison["date"], y=daily_comparison["actual_revenue"],
                            name="Actual", marker_color="darkblue"))
        fig.update_layout(barmode="overlay", height=300, title="Forecast vs Actual Revenue")
        st.plotly_chart(fig, use_container_width=True)

    # Data quality and dispatch
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Data Completeness Impact")
        if not data_quality.empty:
            fig = px.line(
                data_quality.groupby("date")["avg_completeness"].mean().reset_index(),
                x="date",
                y="avg_completeness",
                title="Avg Data Completeness %"
            )
            fig.add_hline(y=95, line_dash="dash", line_color="red", annotation_text="Target 95%")
            fig.update_layout(height=250)
            st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.subheader("Dispatch Compliance")
        if not dispatch_compliance.empty:
            fig = px.line(
                dispatch_compliance.groupby("date")["compliance_pct"].mean().reset_index(),
                x="date",
                y="compliance_pct",
                title="Dispatch Compliance %"
            )
            fig.add_hline(y=95, line_dash="dash", line_color="red", annotation_text="Target 95%")
            fig.update_layout(height=250)
            st.plotly_chart(fig, use_container_width=True)

    # Settlement details table
    st.subheader("Settlement Details")
    if not filtered_settlements.empty:
        display = filtered_settlements[[
            "date", "site_name", "service_name", "energy_mwh", "avg_price_gbp_per_mwh", "revenue_gbp"
        ]].head(50)

        st.dataframe(
            display.rename(columns={
                "date": "Date",
                "site_name": "Site",
                "service_name": "Service",
                "energy_mwh": "Energy (MWh)",
                "avg_price_gbp_per_mwh": "Avg Price (£/MWh)",
                "revenue_gbp": "Revenue (£)"
            }).style.format({
                "Energy (MWh)": "{:.2f}",
                "Avg Price (£/MWh)": "£{:.2f}",
                "Revenue (£)": "£{:,.2f}"
            }),
            use_container_width=True,
            height=300,
        )


if __name__ == "__main__":
    main()
