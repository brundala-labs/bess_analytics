"""
ENKA Portfolio Executive Cockpit

Executive-level portfolio overview with key financial and operational metrics.
"""

import sys
from datetime import date, timedelta
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from dashboard.components.branding import apply_enka_theme, render_sidebar_branding, render_footer, style_plotly_chart
from dashboard.components.header import (
    get_dashboard_config,
    render_header,
    render_filter_bar,
    render_drilldown_table,
)
from dashboard.components.kpi_glossary import render_kpi_glossary
from db.loader import get_connection

st.set_page_config(page_title="Portfolio Executive Cockpit", page_icon="📊", layout="wide")

# Apply ENKA branding
apply_enka_theme()
render_sidebar_branding()


DASHBOARD_KEY = "enka_portfolio_executive"


@st.cache_data(ttl=300)
def load_portfolio_data():
    """Load portfolio summary data."""
    conn = get_connection()

    # Sites
    sites = conn.execute("SELECT * FROM dim_site").df()

    # Revenue MTD
    revenue = conn.execute("""
        SELECT
            site_id,
            SUM(revenue_gbp) as revenue_mtd
        FROM fact_settlement
        WHERE date >= DATE_TRUNC('month', (SELECT MAX(date) FROM fact_settlement))
        GROUP BY site_id
    """).df()

    # Availability (last 7 days)
    availability = conn.execute("""
        SELECT
            site_id,
            AVG(availability_pct) as availability
        FROM v_site_availability
        WHERE date >= (SELECT MAX(date) FROM v_site_availability) - INTERVAL '7 days'
        GROUP BY site_id
    """).df()

    # Battery health
    health = conn.execute("""
        SELECT
            site_id,
            AVG(avg_soh) as avg_soh,
            MAX(max_temp) as max_temp
        FROM v_battery_health
        WHERE date >= (SELECT MAX(date) FROM v_battery_health) - INTERVAL '7 days'
        GROUP BY site_id
    """).df()

    # Active events
    events = conn.execute("""
        SELECT
            site_id,
            COUNT(*) as active_faults
        FROM fact_events
        WHERE event_type IN ('fault', 'trip')
        AND end_ts > (SELECT MAX(ts) FROM fact_telemetry) - INTERVAL '24 hours'
        GROUP BY site_id
    """).df()

    # Merge all data
    portfolio = sites.merge(revenue, on="site_id", how="left")
    portfolio = portfolio.merge(availability, on="site_id", how="left")
    portfolio = portfolio.merge(health, on="site_id", how="left")
    portfolio = portfolio.merge(events, on="site_id", how="left")
    portfolio = portfolio.fillna({"revenue_mtd": 0, "availability": 0, "avg_soh": 0, "active_faults": 0})

    conn.close()
    return portfolio


@st.cache_data(ttl=300)
def load_revenue_trend():
    """Load revenue trend data."""
    conn = get_connection()
    df = conn.execute("""
        SELECT
            date,
            site_id,
            SUM(revenue_gbp) as revenue
        FROM fact_settlement
        GROUP BY date, site_id
        ORDER BY date
    """).df()
    conn.close()
    return df


@st.cache_data(ttl=300)
def load_event_summary():
    """Load event summary."""
    conn = get_connection()
    df = conn.execute("""
        SELECT
            site_id,
            event_type,
            severity,
            COUNT(*) as count,
            AVG(EXTRACT(EPOCH FROM (end_ts - start_ts)) / 60) as avg_duration_min
        FROM fact_events
        GROUP BY site_id, event_type, severity
    """).df()
    conn.close()
    return df


def main():
    # Load data
    portfolio = load_portfolio_data()
    revenue_trend = load_revenue_trend()

    # Calculate KPI values
    kpi_values = {
        "portfolio_revenue_mtd_gbp": portfolio["revenue_mtd"].sum(),
        "portfolio_availability_pct": portfolio["availability"].mean(),
        "total_energy_mwh": portfolio["bess_mwh"].sum(),
        "active_fault_count": int(portfolio["active_faults"].sum()),
        "sites_below_target": int((portfolio["availability"] < 95).sum()),
        "avg_soh_pct": portfolio["avg_soh"].mean(),
    }

    # Get dashboard config
    config = get_dashboard_config(DASHBOARD_KEY)

    # Build KPIs
    kpis = []
    for kpi_def in config.get("kpis", []):
        kpis.append({
            "label": kpi_def.get("label"),
            "value": kpi_values.get(kpi_def.get("metric")),
            "format": kpi_def.get("format", "number"),
        })

    # Render header
    render_header(
        title=config.get("title", "Portfolio Executive Cockpit"),
        personas=config.get("personas", []),
        decisions=config.get("decisions", []),
        data_sources=config.get("data_sources", []),
        freshness=config.get("freshness", ""),
        kpis=kpis,
    )

    # Main content
    col1, col2 = st.columns([2, 1])

    with col1:
        # Revenue trend chart
        st.subheader("Revenue Trend by Site")
        fig = px.area(
            revenue_trend,
            x="date",
            y="revenue",
            color="site_id",
            title="Daily Revenue (GBP)",
        )
        fig.update_layout(height=350)
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        # Portfolio composition
        st.subheader("Portfolio Composition")
        fig = px.pie(
            portfolio,
            values="bess_mw",
            names="name",
            title="Capacity by Site (MW)",
        )
        fig.update_layout(height=350)
        st.plotly_chart(fig, use_container_width=True)

    # Site performance table
    st.subheader("Site Performance Summary")

    display_df = portfolio[[
        "name", "bess_mw", "bess_mwh", "vendor_controller",
        "revenue_mtd", "availability", "avg_soh", "active_faults"
    ]].copy()

    display_df.columns = [
        "Site", "MW", "MWh", "Vendor",
        "Revenue MTD (£)", "Availability %", "Avg SOH %", "Active Faults"
    ]

    # Color coding
    def highlight_issues(row):
        styles = [''] * len(row)
        if row["Availability %"] < 95:
            styles[5] = 'background-color: #ffcdd2'
        if row["Avg SOH %"] < 90:
            styles[6] = 'background-color: #ffecb3'
        if row["Active Faults"] > 0:
            styles[7] = 'background-color: #ffcdd2'
        return styles

    st.dataframe(
        display_df.style.apply(highlight_issues, axis=1).format({
            "Revenue MTD (£)": "£{:,.0f}",
            "Availability %": "{:.1f}%",
            "Avg SOH %": "{:.1f}%",
        }),
        use_container_width=True,
        height=200,
    )

    # Bottom row - Availability heatmap and Events
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Site Availability Heatmap")
        conn = get_connection()
        avail_daily = conn.execute("""
            SELECT site_id, date, availability_pct
            FROM v_site_availability
            ORDER BY date
        """).df()
        conn.close()

        if not avail_daily.empty:
            pivot = avail_daily.pivot(index="site_id", columns="date", values="availability_pct")
            fig = px.imshow(
                pivot.values,
                x=[str(d)[:10] for d in pivot.columns],
                y=pivot.index.tolist(),
                color_continuous_scale="RdYlGn",
                zmin=80,
                zmax=100,
                aspect="auto",
            )
            fig.update_layout(height=250)
            st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.subheader("Recent Events")
        event_summary = load_event_summary()
        if not event_summary.empty:
            fig = px.bar(
                event_summary.groupby("event_type")["count"].sum().reset_index(),
                x="event_type",
                y="count",
                color="event_type",
                title="Events by Type",
            )
            fig.update_layout(height=250, showlegend=False)
            st.plotly_chart(fig, use_container_width=True)

    # KPI Glossary
    st.divider()
    render_kpi_glossary(
        kpi_keys=config.get("kpi_glossary_keys", [
            "soc_pct", "soh_pct", "availability_pct", "power_kw", "energy_mwh", "lost_revenue_gbp"
        ]),
        title="KPI Definitions And Sources"
    )


if __name__ == "__main__":
    main()
