"""
ENKA Lifecycle & Augmentation Planning

Battery health monitoring, degradation trends, and augmentation planning.
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

st.set_page_config(initial_sidebar_state="expanded", page_title="Lifecycle & Augmentation", page_icon="🔋", layout="wide")

# Apply ENKA branding
apply_enka_theme()
render_sidebar_branding()


DASHBOARD_KEY = "enka_lifecycle_augmentation"


@st.cache_data(ttl=300)
def load_lifecycle_data():
    """Load battery health and lifecycle data."""
    conn = get_connection()

    # Battery health trends
    health = conn.execute("""
        SELECT
            bh.site_id,
            s.name as site_name,
            bh.date,
            bh.avg_soh,
            bh.avg_soc,
            bh.avg_temp,
            bh.max_temp,
            bh.cycle_count
        FROM v_battery_health bh
        JOIN dim_site s ON bh.site_id = s.site_id
        ORDER BY bh.date
    """).df()

    # Latest health snapshot
    latest_health = conn.execute("""
        SELECT
            bh.site_id,
            s.name as site_name,
            s.bess_mwh,
            s.cod_date,
            bh.avg_soh,
            bh.avg_soc,
            bh.max_temp,
            bh.cycle_count
        FROM v_battery_health bh
        JOIN dim_site s ON bh.site_id = s.site_id
        WHERE bh.date = (SELECT MAX(date) FROM v_battery_health)
    """).df()

    # Maintenance history
    maintenance = conn.execute("""
        SELECT
            m.site_id,
            s.name as site_name,
            m.issue_category,
            COUNT(*) as ticket_count,
            SUM(m.cost_gbp) as total_cost,
            AVG(EXTRACT(EPOCH FROM (m.closed_ts - m.opened_ts)) / 3600) as avg_resolution_hours
        FROM fact_maintenance m
        JOIN dim_site s ON m.site_id = s.site_id
        WHERE m.closed_ts IS NOT NULL
        GROUP BY m.site_id, s.name, m.issue_category
    """).df()

    sites = conn.execute("SELECT site_id, name FROM dim_site").df().to_dict(orient="records")

    conn.close()
    return health, latest_health, maintenance, sites


def calculate_degradation_rate(health_df: pd.DataFrame) -> pd.DataFrame:
    """Calculate degradation rate per site."""
    rates = []
    for site_id in health_df["site_id"].unique():
        site_data = health_df[health_df["site_id"] == site_id].sort_values("date")
        if len(site_data) > 7:
            soh_start = site_data.head(7)["avg_soh"].mean()
            soh_end = site_data.tail(7)["avg_soh"].mean()
            days = (site_data["date"].max() - site_data["date"].min()).days
            if days > 0:
                monthly_rate = ((soh_start - soh_end) / days) * 30
                rates.append({
                    "site_id": site_id,
                    "site_name": site_data["site_name"].iloc[0],
                    "degradation_rate_per_month": monthly_rate
                })
    return pd.DataFrame(rates)


def main():
    health, latest_health, maintenance, sites = load_lifecycle_data()

    # Calculate degradation rates
    degradation = calculate_degradation_rate(health)

    # Calculate KPIs
    fleet_avg_soh = latest_health["avg_soh"].mean() if not latest_health.empty else 0
    sites_needing_aug = (latest_health["avg_soh"] < 85).sum() if not latest_health.empty else 0
    avg_cycles = latest_health["cycle_count"].mean() if not latest_health.empty else 0
    total_maint_cost = maintenance["total_cost"].sum() if not maintenance.empty else 0

    # Calculate degradation rate (% per year)
    avg_degradation_rate = degradation["degradation_rate_per_month"].mean() * 12 if not degradation.empty else 0

    # Years to augmentation (when SoH reaches 80%)
    years_to_aug = max(0, (fleet_avg_soh - 80) / avg_degradation_rate) if avg_degradation_rate > 0 else 10

    kpi_values = {
        "avg_soh_pct": fleet_avg_soh,
        "degradation_rate_pct_year": avg_degradation_rate,
        "warranty_excursions": int(sites_needing_aug),
        "years_to_augmentation": years_to_aug,
        "maintenance_cost_ytd": total_maint_cost,
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

    # SOH Trend
    st.subheader("State of Health (SOH) Trend")

    filtered_health = health.copy()
    if filters.get("site_id"):
        filtered_health = filtered_health[filtered_health["site_id"] == filters["site_id"]]

    if not filtered_health.empty:
        fig = px.line(
            filtered_health,
            x="date",
            y="avg_soh",
            color="site_name",
            title="SOH % Over Time"
        )
        fig.add_hline(y=85, line_dash="dash", line_color="orange", annotation_text="Augmentation Threshold")
        fig.add_hline(y=70, line_dash="dash", line_color="red", annotation_text="End of Life")
        fig.update_layout(height=350)
        st.plotly_chart(fig, use_container_width=True)

    # Health snapshot and temperature
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Current Health Status")
        if not latest_health.empty:
            fig = px.bar(
                latest_health,
                x="site_name",
                y="avg_soh",
                color="avg_soh",
                color_continuous_scale="RdYlGn",
                range_color=[70, 100],
                title="Current SOH by Site"
            )
            fig.add_hline(y=85, line_dash="dash", line_color="orange")
            fig.update_layout(height=300)
            st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.subheader("Temperature Trends")
        if not filtered_health.empty:
            fig = px.line(
                filtered_health,
                x="date",
                y="max_temp",
                color="site_name",
                title="Max Temperature (°C)"
            )
            fig.add_hline(y=45, line_dash="dash", line_color="red", annotation_text="Thermal Limit")
            fig.update_layout(height=300)
            st.plotly_chart(fig, use_container_width=True)

    # Cycle count and degradation
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Cycle Count Progression")
        if not filtered_health.empty:
            fig = px.line(
                filtered_health,
                x="date",
                y="cycle_count",
                color="site_name",
                title="Cumulative Cycles"
            )
            fig.update_layout(height=280)
            st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.subheader("Degradation Rate")
        if not degradation.empty:
            fig = px.bar(
                degradation,
                x="site_name",
                y="degradation_rate_per_month",
                color="degradation_rate_per_month",
                color_continuous_scale="Reds",
                title="SOH Loss per Month (%)"
            )
            fig.update_layout(height=280)
            st.plotly_chart(fig, use_container_width=True)

    # Maintenance impact
    st.subheader("Maintenance History & Cost")
    col1, col2 = st.columns(2)

    with col1:
        if not maintenance.empty:
            by_category = maintenance.groupby("issue_category").agg({
                "ticket_count": "sum",
                "total_cost": "sum"
            }).reset_index()

            fig = px.bar(
                by_category,
                x="issue_category",
                y="total_cost",
                color="ticket_count",
                title="Maintenance Cost by Category"
            )
            fig.update_layout(height=280)
            st.plotly_chart(fig, use_container_width=True)

    with col2:
        if not maintenance.empty:
            st.dataframe(
                maintenance[[
                    "site_name", "issue_category", "ticket_count", "total_cost", "avg_resolution_hours"
                ]].rename(columns={
                    "site_name": "Site",
                    "issue_category": "Category",
                    "ticket_count": "Tickets",
                    "total_cost": "Cost (£)",
                    "avg_resolution_hours": "Avg Resolution (hrs)"
                }).style.format({
                    "Cost (£)": "£{:,.0f}",
                    "Avg Resolution (hrs)": "{:.1f}"
                }),
                use_container_width=True,
                height=280,
            )

    # Augmentation planning table
    st.subheader("Augmentation Planning Summary")
    if not latest_health.empty:
        planning = latest_health.copy()
        planning["estimated_remaining_cycles"] = (planning["avg_soh"] - 70) * 100  # Rough estimate
        planning["urgency"] = planning["avg_soh"].apply(
            lambda x: "🔴 Critical" if x < 80 else ("🟡 Plan" if x < 90 else "🟢 Good")
        )

        st.dataframe(
            planning[[
                "site_name", "bess_mwh", "avg_soh", "cycle_count", "estimated_remaining_cycles", "urgency"
            ]].rename(columns={
                "site_name": "Site",
                "bess_mwh": "Capacity (MWh)",
                "avg_soh": "Current SOH %",
                "cycle_count": "Cycles",
                "estimated_remaining_cycles": "Est. Remaining Cycles",
                "urgency": "Status"
            }).style.format({
                "Current SOH %": "{:.1f}%",
                "Cycles": "{:.0f}",
                "Est. Remaining Cycles": "{:.0f}"
            }),
            use_container_width=True,
        )


if __name__ == "__main__":
    main()
