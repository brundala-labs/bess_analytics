"""
Combined Dispatch vs Asset Stress

Analyze the relationship between dispatch intensity and asset degradation.
"""

import sys
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
import numpy as np

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from dashboard.components.branding import apply_enka_theme, render_sidebar_branding, render_footer, style_plotly_chart
from dashboard.components.header import get_dashboard_config, render_header, render_filter_bar
from db.loader import get_connection

st.set_page_config(initial_sidebar_state="expanded", page_title="Dispatch vs Asset Stress", page_icon="⚖️", layout="wide")

# Apply ENKA branding
apply_enka_theme()
render_sidebar_branding()


DASHBOARD_KEY = "combined_dispatch_stress"


@st.cache_data(ttl=300)
def load_stress_data():
    """Load dispatch and stress correlation data."""
    conn = get_connection()

    # Daily dispatch intensity
    dispatch_intensity = conn.execute("""
        SELECT
            DATE_TRUNC('day', d.ts) as date,
            d.site_id,
            s.name as site_name,
            s.bess_mw,
            s.bess_mwh,
            COUNT(*) as dispatch_count,
            SUM(ABS(d.command_kw)) / 1000 as total_commanded_mw,
            AVG(ABS(d.actual_kw)) / 1000 as avg_power_mw,
            MAX(ABS(d.actual_kw)) / 1000 as max_power_mw
        FROM fact_dispatch d
        JOIN dim_site s ON d.site_id = s.site_id
        GROUP BY DATE_TRUNC('day', d.ts), d.site_id, s.name, s.bess_mw, s.bess_mwh
        ORDER BY date
    """).df()

    # Battery health by day
    battery_health = conn.execute("""
        SELECT
            bh.date,
            bh.site_id,
            s.name as site_name,
            bh.avg_soh,
            bh.avg_temp,
            bh.max_temp,
            bh.cycle_count
        FROM v_battery_health bh
        JOIN dim_site s ON bh.site_id = s.site_id
        ORDER BY bh.date
    """).df()

    # Revenue by day
    revenue = conn.execute("""
        SELECT
            date,
            site_id,
            SUM(revenue_gbp) as daily_revenue,
            SUM(energy_mwh) as daily_energy
        FROM fact_settlement
        GROUP BY date, site_id
    """).df()

    # Thermal events
    thermal_events = conn.execute("""
        SELECT
            site_id,
            DATE_TRUNC('day', start_ts) as date,
            COUNT(*) as thermal_events
        FROM fact_events
        WHERE code LIKE '%Temp%' OR code LIKE '%Thermal%' OR code LIKE '%OverTemp%'
        GROUP BY site_id, DATE_TRUNC('day', start_ts)
    """).df()

    sites = conn.execute("SELECT site_id, name FROM dim_site").df().to_dict(orient="records")

    conn.close()
    return dispatch_intensity, battery_health, revenue, thermal_events, sites


def calculate_metrics(dispatch, health, revenue):
    """Calculate dispatch stress metrics."""

    # Merge data
    combined = dispatch.merge(
        health[["date", "site_id", "avg_soh", "avg_temp", "max_temp", "cycle_count"]],
        on=["date", "site_id"],
        how="left"
    )

    combined = combined.merge(
        revenue[["date", "site_id", "daily_revenue", "daily_energy"]],
        on=["date", "site_id"],
        how="left"
    )

    # Calculate intensity score (0-100)
    combined["intensity_score"] = (
        (combined["avg_power_mw"] / combined["bess_mw"]) * 100
    ).clip(0, 100)

    # Calculate daily cycles estimate
    combined["daily_cycles"] = combined["daily_energy"] / combined["bess_mwh"]

    # Revenue per cycle
    combined["revenue_per_cycle"] = combined["daily_revenue"] / combined["daily_cycles"].replace(0, np.nan)

    return combined


def main():
    dispatch, health, revenue, thermal_events, sites = load_stress_data()

    combined = calculate_metrics(dispatch, health, revenue)

    # Calculate KPIs
    if not combined.empty:
        latest = combined[combined["date"] == combined["date"].max()]
        intensity_score = latest["intensity_score"].mean()

        # Degradation rate (SOH change over period)
        if not health.empty:
            health_grouped = health.groupby("site_id").agg({
                "avg_soh": ["first", "last"],
                "date": ["min", "max"]
            })
            health_grouped.columns = ["soh_first", "soh_last", "date_first", "date_last"]
            health_grouped["days"] = (health_grouped["date_last"] - health_grouped["date_first"]).dt.days
            health_grouped["degradation_rate"] = (health_grouped["soh_first"] - health_grouped["soh_last"]) / health_grouped["days"] * 30
            degradation_rate = health_grouped["degradation_rate"].mean()
        else:
            degradation_rate = 0

        revenue_per_cycle = combined["revenue_per_cycle"].mean()
        thermal_stress = len(thermal_events)
        cycles_this_month = combined[
            combined["date"] >= combined["date"].max().replace(day=1)
        ]["daily_cycles"].sum()

        # Optimal dispatch score (balances revenue vs degradation)
        optimal_score = min(100, (revenue_per_cycle / 100) * (1 - degradation_rate * 10)) if revenue_per_cycle > 0 else 50
    else:
        intensity_score = 0
        degradation_rate = 0
        revenue_per_cycle = 0
        thermal_stress = 0
        optimal_score = 50
        cycles_this_month = 0

    kpi_values = {
        "dispatch_intensity_score": intensity_score,
        "degradation_rate_pct_month": degradation_rate,
        "revenue_per_cycle": revenue_per_cycle,
        "thermal_stress_events": thermal_stress,
        "optimal_dispatch_score": optimal_score,
        "cycles_this_month": cycles_this_month,
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
    filtered = combined.copy()
    if filters.get("site_id"):
        filtered = filtered[filtered["site_id"] == filters["site_id"]]

    # Intensity vs SOH scatter
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Dispatch Intensity vs SOH")
        if not filtered.empty:
            fig = px.scatter(
                filtered,
                x="intensity_score",
                y="avg_soh",
                color="site_name",
                size="daily_revenue",
                hover_data=["date", "avg_temp"],
                title="Intensity Score vs State of Health"
            )
            fig.update_layout(height=350)
            st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.subheader("Temperature vs Daily Cycles")
        if not filtered.empty:
            fig = px.scatter(
                filtered,
                x="daily_cycles",
                y="max_temp",
                color="site_name",
                title="Cycling Impact on Temperature"
            )
            fig.add_hline(y=45, line_dash="dash", line_color="red", annotation_text="Thermal Limit")
            fig.update_layout(height=350)
            st.plotly_chart(fig, use_container_width=True)

    # Revenue vs degradation tradeoff
    st.subheader("Revenue vs Degradation Tradeoff")

    if not filtered.empty:
        site_summary = filtered.groupby("site_name").agg({
            "daily_revenue": "sum",
            "daily_cycles": "sum",
            "intensity_score": "mean",
            "avg_soh": ["first", "last"]
        }).reset_index()

        site_summary.columns = ["site_name", "total_revenue", "total_cycles", "avg_intensity", "soh_start", "soh_end"]
        site_summary["soh_change"] = site_summary["soh_start"] - site_summary["soh_end"]
        site_summary["revenue_per_soh_point"] = site_summary["total_revenue"] / site_summary["soh_change"].replace(0, np.nan)

        fig = px.scatter(
            site_summary,
            x="total_cycles",
            y="total_revenue",
            size="soh_change",
            color="site_name",
            hover_data=["avg_intensity", "revenue_per_soh_point"],
            title="Total Revenue vs Total Cycles (bubble size = SOH loss)"
        )
        fig.update_layout(height=350)
        st.plotly_chart(fig, use_container_width=True)

    # Time series
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Daily Intensity Trend")
        if not filtered.empty:
            daily = filtered.groupby(["date", "site_name"])["intensity_score"].mean().reset_index()
            fig = px.line(
                daily,
                x="date",
                y="intensity_score",
                color="site_name",
                title="Dispatch Intensity Score Over Time"
            )
            fig.update_layout(height=280)
            st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.subheader("Cycle Count Trend")
        if not filtered.empty:
            fig = px.line(
                filtered.groupby(["date", "site_name"])["daily_cycles"].sum().reset_index(),
                x="date",
                y="daily_cycles",
                color="site_name",
                title="Daily Equivalent Full Cycles"
            )
            fig.update_layout(height=280)
            st.plotly_chart(fig, use_container_width=True)

    # Thermal stress
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Max Temperature Trend")
        if not filtered.empty:
            fig = px.line(
                filtered,
                x="date",
                y="max_temp",
                color="site_name",
                title="Daily Maximum Temperature"
            )
            fig.add_hline(y=40, line_dash="dash", line_color="orange", annotation_text="Warning")
            fig.add_hline(y=45, line_dash="dash", line_color="red", annotation_text="Critical")
            fig.update_layout(height=280)
            st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.subheader("Revenue per Cycle")
        if not filtered.empty:
            fig = px.line(
                filtered.groupby(["date", "site_name"])["revenue_per_cycle"].mean().reset_index(),
                x="date",
                y="revenue_per_cycle",
                color="site_name",
                title="Revenue per Equivalent Full Cycle (£)"
            )
            fig.update_layout(height=280)
            st.plotly_chart(fig, use_container_width=True)

    # Recommendations
    st.subheader("Dispatch Strategy Recommendations")

    if not filtered.empty:
        site_analysis = site_summary.copy() if 'site_summary' in dir() else pd.DataFrame()

        if not site_analysis.empty:
            for _, site in site_analysis.iterrows():
                with st.expander(f"📊 {site['site_name']}"):
                    col1, col2, col3 = st.columns(3)

                    with col1:
                        st.metric("Total Revenue", f"£{site['total_revenue']:,.0f}")
                    with col2:
                        st.metric("Total Cycles", f"{site['total_cycles']:.1f}")
                    with col3:
                        st.metric("SOH Loss", f"{site['soh_change']:.2f}%")

                    # Recommendation based on intensity
                    if site["avg_intensity"] > 80:
                        st.warning("High intensity dispatch detected. Consider reducing peak power to extend battery life.")
                    elif site["avg_intensity"] < 30:
                        st.info("Low utilization. Could potentially increase dispatch to improve revenue.")
                    else:
                        st.success("Dispatch intensity is balanced.")

                    if pd.notna(site.get("revenue_per_soh_point")) and site["revenue_per_soh_point"] < 10000:
                        st.warning("Low revenue efficiency per SOH point. Review trading strategy.")


if __name__ == "__main__":
    main()
