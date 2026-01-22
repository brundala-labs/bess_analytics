"""
Insights Report And Recommendations Dashboard

Automated findings and recommendations with estimated value impact.
Consolidates insights from all Edge Intelligence engines.
"""

import sys
from datetime import date, timedelta
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from dashboard.components.branding import (
    apply_enka_theme,
    render_sidebar_branding,
    render_footer,
    style_plotly_chart,
    get_plotly_colors,
    ENKA_GREEN,
)
from dashboard.components.header import render_header, render_filter_bar
from db.loader import get_connection, load_data

st.set_page_config(initial_sidebar_state="expanded", 
    page_title="Insights Report And Recommendations",
    page_icon="💡",
    layout="wide",
)

apply_enka_theme()
render_sidebar_branding()


@st.cache_data(ttl=300)
def load_sites():
    """Load site data."""
    conn = get_connection()
    load_data(conn)
    sites = conn.execute("SELECT site_id, name FROM dim_site").df()
    conn.close()
    return sites.to_dict("records")


@st.cache_data(ttl=300)
def load_insights(site_id: str = None, category: str = None, severity: str = None):
    """Load insights findings."""
    conn = get_connection()
    load_data(conn)

    query = """
        SELECT
            finding_id,
            ts,
            site_id,
            category,
            severity,
            title,
            description,
            recommendation,
            estimated_value_gbp,
            confidence,
            acknowledged,
            resolved
        FROM fact_insights_findings
        WHERE 1=1
    """
    params = []
    if site_id:
        query += " AND site_id = ?"
        params.append(site_id)
    if category:
        query += " AND category = ?"
        params.append(category)
    if severity:
        query += " AND severity = ?"
        params.append(severity)
    query += """
        ORDER BY
            CASE severity
                WHEN 'critical' THEN 1
                WHEN 'alert' THEN 2
                WHEN 'warning' THEN 3
                ELSE 4
            END,
            ts DESC
    """

    df = conn.execute(query, params).df()
    conn.close()
    return df


@st.cache_data(ttl=300)
def load_insights_summary():
    """Load insights summary by category and severity."""
    conn = get_connection()
    load_data(conn)
    df = conn.execute("""
        SELECT
            site_id,
            severity,
            category,
            finding_count,
            total_value_impact
        FROM v_insights_summary
    """).df()
    conn.close()
    return df


@st.cache_data(ttl=300)
def load_active_insights():
    """Load active (unresolved) insights."""
    conn = get_connection()
    load_data(conn)
    df = conn.execute("""
        SELECT
            f.*,
            s.name as site_name
        FROM fact_insights_findings f
        JOIN dim_site s ON f.site_id = s.site_id
        WHERE f.resolved = false
        ORDER BY
            CASE f.severity WHEN 'critical' THEN 1 WHEN 'alert' THEN 2 WHEN 'warning' THEN 3 ELSE 4 END,
            f.estimated_value_gbp DESC
    """).df()
    conn.close()
    return df


def main():
    # Load data
    sites = load_sites()
    insights_summary = load_insights_summary()
    active_insights = load_active_insights()

    # Calculate KPIs
    if not active_insights.empty:
        total_value_at_risk = active_insights["estimated_value_gbp"].sum()
        critical_count = len(active_insights[active_insights["severity"] == "critical"])
        alert_count = len(active_insights[active_insights["severity"] == "alert"])
    else:
        total_value_at_risk = 0
        critical_count = 0
        alert_count = 0

    unresolved_count = len(active_insights)

    # Header
    render_header(
        title="Insights Report And Recommendations",
        personas=["ENKA Management", "Operations", "Asset Managers"],
        decisions=[
            "Prioritize maintenance based on value impact",
            "Address critical findings immediately",
            "Track value recovery from resolved issues",
            "Review automated recommendations",
        ],
        data_sources=[
            {"system": "Edge Intelligence", "tables": ["fact_insights_findings"], "notes": "Automated findings"},
            {"system": "All Edge Engines", "tables": ["v_insights_summary"], "notes": "Consolidated analysis"},
        ],
        freshness="Real-time analysis",
        kpis=[
            {"label": "Value At Risk", "value": total_value_at_risk, "format": "currency"},
            {"label": "Critical Findings", "value": critical_count, "format": "integer"},
            {"label": "Alerts", "value": alert_count, "format": "integer"},
            {"label": "Unresolved", "value": unresolved_count, "format": "integer"},
        ],
    )

    # Filters
    col1, col2, col3 = st.columns(3)
    with col1:
        site_options = ["All Sites"] + [s["name"] for s in sites]
        selected_site_name = st.selectbox("Site", site_options)
        selected_site = None
        if selected_site_name != "All Sites":
            selected_site = next((s["site_id"] for s in sites if s["name"] == selected_site_name), None)

    with col2:
        categories = ["All Categories", "signal_quality", "energy_availability",
                      "power_constraints", "cell_imbalance", "thermal", "operational"]
        selected_category = st.selectbox("Category", categories)
        if selected_category == "All Categories":
            selected_category = None

    with col3:
        severities = ["All Severities", "critical", "alert", "warning", "info"]
        selected_severity = st.selectbox("Severity", severities)
        if selected_severity == "All Severities":
            selected_severity = None

    colors = get_plotly_colors()

    # Load filtered insights
    insights_df = load_insights(selected_site, selected_category, selected_severity)

    # Row 1: Value at Risk Overview
    st.subheader("Value Impact Analysis")

    col1, col2 = st.columns(2)

    with col1:
        if not insights_summary.empty:
            # Value by category
            cat_value = insights_summary.groupby("category")["total_value_impact"].sum().reset_index()
            cat_value = cat_value.sort_values("total_value_impact", ascending=False)

            fig = px.bar(
                cat_value,
                x="category",
                y="total_value_impact",
                title="Value At Risk by Category (£)",
                color="total_value_impact",
                color_continuous_scale="Reds",
            )
            fig.update_layout(height=350, xaxis_title="Category", yaxis_title="Value (£)")
            style_plotly_chart(fig)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No insights summary data available.")

    with col2:
        if not insights_summary.empty:
            # Findings by severity
            sev_counts = insights_summary.groupby("severity")["finding_count"].sum().reset_index()

            fig = px.pie(
                sev_counts,
                values="finding_count",
                names="severity",
                title="Findings by Severity",
                color="severity",
                color_discrete_map={
                    "critical": "#d32f2f",
                    "alert": "#f57c00",
                    "warning": "#fbc02d",
                    "info": "#1976d2",
                },
            )
            fig.update_layout(height=350)
            style_plotly_chart(fig)
            st.plotly_chart(fig, use_container_width=True)

    # Row 2: Active Insights Cards
    st.subheader("Active Insights")

    if not insights_df.empty:
        # Filter to unresolved
        active_df = insights_df[insights_df["resolved"] == False]

        if active_df.empty:
            st.success("All insights have been resolved!")
        else:
            # Severity tabs
            tabs = st.tabs(["Critical", "Alert", "Warning", "Info"])

            severity_map = {"critical": 0, "alert": 1, "warning": 2, "info": 3}

            for sev, tab_idx in severity_map.items():
                with tabs[tab_idx]:
                    sev_insights = active_df[active_df["severity"] == sev]

                    if sev_insights.empty:
                        st.info(f"No {sev} findings.")
                    else:
                        for _, insight in sev_insights.head(10).iterrows():
                            severity_colors = {
                                "critical": "#d32f2f",
                                "alert": "#f57c00",
                                "warning": "#fbc02d",
                                "info": "#1976d2",
                            }
                            border_color = severity_colors.get(insight["severity"], "#ccc")

                            with st.container(border=True):
                                col1, col2 = st.columns([4, 1])

                                with col1:
                                    st.markdown(f"**{insight['title']}**")
                                    st.caption(f"{insight['site_id']} | {insight['category']} | {insight['ts']}")
                                    st.markdown(insight["description"])

                                    with st.expander("Recommendation"):
                                        st.markdown(insight["recommendation"])

                                with col2:
                                    st.metric(
                                        "Value Impact",
                                        f"£{insight['estimated_value_gbp']:,.0f}",
                                    )
                                    st.metric(
                                        "Confidence",
                                        f"{insight['confidence']*100:.0f}%",
                                    )

                                    ack_status = "Acknowledged" if insight["acknowledged"] else "Pending"
                                    st.caption(ack_status)
    else:
        st.info("No insights available for the selected filters.")

    # Row 3: Insights Trend
    st.subheader("Insights Trend Over Time")

    if not insights_df.empty:
        # Group by date and severity
        insights_df["date"] = pd.to_datetime(insights_df["ts"]).dt.date
        trend_df = insights_df.groupby(["date", "severity"]).size().reset_index(name="count")

        fig = px.area(
            trend_df,
            x="date",
            y="count",
            color="severity",
            title="Findings Generated Over Time",
            color_discrete_map={
                "critical": "#d32f2f",
                "alert": "#f57c00",
                "warning": "#fbc02d",
                "info": "#1976d2",
            },
        )
        fig.update_layout(height=300)
        style_plotly_chart(fig)
        st.plotly_chart(fig, use_container_width=True)

    # Row 4: Site Comparison
    st.subheader("Value At Risk by Site")

    if not insights_summary.empty:
        site_value = insights_summary.groupby("site_id")["total_value_impact"].sum().reset_index()
        site_value = site_value.sort_values("total_value_impact", ascending=True)

        fig = px.bar(
            site_value,
            x="total_value_impact",
            y="site_id",
            orientation="h",
            title="Total Value at Risk by Site (£)",
            color="total_value_impact",
            color_continuous_scale="Reds",
        )
        fig.update_layout(height=250, xaxis_title="Value (£)", yaxis_title="Site")
        style_plotly_chart(fig)
        st.plotly_chart(fig, use_container_width=True)

    # Row 5: Full Insights Table
    st.subheader("All Insights")

    if not insights_df.empty:
        display_df = insights_df.copy()
        display_df["ts"] = pd.to_datetime(display_df["ts"]).dt.strftime("%Y-%m-%d %H:%M")
        display_df["confidence"] = (display_df["confidence"] * 100).round(0)

        # Status column
        display_df["status"] = display_df.apply(
            lambda r: "Resolved" if r["resolved"] else ("Acknowledged" if r["acknowledged"] else "Active"),
            axis=1
        )

        def highlight_severity(val):
            colors = {
                "critical": "background-color: #ffcdd2",
                "alert": "background-color: #ffe0b2",
                "warning": "background-color: #fff9c4",
            }
            return colors.get(val, "")

        st.dataframe(
            display_df[[
                "ts", "site_id", "category", "severity", "title",
                "estimated_value_gbp", "confidence", "status"
            ]].rename(columns={
                "ts": "Time",
                "site_id": "Site",
                "category": "Category",
                "severity": "Severity",
                "title": "Title",
                "estimated_value_gbp": "Value (£)",
                "confidence": "Confidence %",
                "status": "Status",
            }).style.map(
                highlight_severity, subset=["Severity"]
            ).format({
                "Value (£)": "£{:,.0f}",
            }),
            use_container_width=True,
            height=400,
        )

    # Export option
    st.divider()

    col1, col2 = st.columns([3, 1])
    with col2:
        if not insights_df.empty:
            csv = insights_df.to_csv(index=False)
            st.download_button(
                label="Export Insights (CSV)",
                data=csv,
                file_name="insights_report.csv",
                mime="text/csv",
            )

    # Documentation
    with st.expander("Insights Generation Methodology"):
        st.markdown("""
        ### Automated Insights Engine

        The Insights Engine consolidates signals from all Edge Intelligence components:

        **Categories:**
        - **Signal Quality**: Trust score degradation, SoC drift
        - **Energy Availability**: Low energy reserves, time-to-empty warnings
        - **Power Constraints**: Capacity derates, thermal limits
        - **Cell Imbalance**: Rack-level imbalances requiring action
        - **Thermal**: Temperature anomalies
        - **Operational**: General operational issues

        **Severity Levels:**
        - **Critical**: Immediate action required
        - **Alert**: Action required within 24 hours
        - **Warning**: Monitor closely, plan action
        - **Info**: Informational, no action needed

        **Value Estimation:**
        Value impact is estimated based on:
        - Potential lost revenue from reduced capacity
        - SoH degradation costs
        - Maintenance and repair costs
        - Grid penalty risk

        **Confidence Score:**
        Indicates reliability of the finding (0-100%).
        Higher confidence means more certain diagnosis.
        """)

    render_footer()


if __name__ == "__main__":
    main()
