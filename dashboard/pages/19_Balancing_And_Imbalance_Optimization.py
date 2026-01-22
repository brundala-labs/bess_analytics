"""
Balancing And Imbalance Optimization Dashboard

Displays imbalance scores by rack, severity distribution, and balancing
action recommendations with priority.
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
    page_title="Balancing And Imbalance Optimization",
    page_icon="⚖️",
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
def load_imbalance_data(site_id: str = None, hours: int = 24):
    """Load imbalance detection data."""
    conn = get_connection()
    load_data(conn)

    query = """
        SELECT
            site_id, rack_id, ts, imbalance_score, severity,
            max_cell_delta_mv, max_temp_delta_c
        FROM fact_imbalance
        WHERE ts >= (SELECT MAX(ts) FROM fact_imbalance) - INTERVAL '{}' HOUR
    """.format(hours)

    if site_id:
        query = query.replace("WHERE", f"WHERE site_id = '{site_id}' AND")

    query += " ORDER BY ts DESC"
    df = conn.execute(query).df()
    conn.close()
    return df


@st.cache_data(ttl=300)
def load_imbalance_summary():
    """Load imbalance summary by rack."""
    conn = get_connection()
    load_data(conn)
    df = conn.execute("SELECT * FROM v_imbalance_summary").df()
    conn.close()
    return df


@st.cache_data(ttl=300)
def load_balancing_actions(site_id: str = None):
    """Load balancing actions."""
    conn = get_connection()
    load_data(conn)

    query = """
        SELECT
            action_id, site_id, rack_id, ts, action_type, priority,
            estimated_duration_min, estimated_recovery_mwh, status
        FROM fact_balancing_actions
        ORDER BY
            CASE priority
                WHEN 'urgent' THEN 1
                WHEN 'high' THEN 2
                WHEN 'medium' THEN 3
                ELSE 4
            END,
            ts DESC
    """

    if site_id:
        query = query.replace("ORDER BY", f"WHERE site_id = '{site_id}' ORDER BY")

    df = conn.execute(query).df()
    conn.close()
    return df


@st.cache_data(ttl=300)
def load_pending_actions():
    """Load pending balancing actions."""
    conn = get_connection()
    load_data(conn)
    df = conn.execute("SELECT * FROM v_pending_balancing_actions").df()
    conn.close()
    return df


def main():
    # Load data
    sites = load_sites()
    imbalance_summary = load_imbalance_summary()
    pending_actions = load_pending_actions()

    # Calculate KPIs
    if not imbalance_summary.empty:
        avg_imbalance = imbalance_summary["avg_imbalance_score"].mean()
        max_imbalance = imbalance_summary["max_imbalance_score"].max()
        critical_racks = len(imbalance_summary[imbalance_summary["max_imbalance_score"] > 60])
    else:
        avg_imbalance = 0
        max_imbalance = 0
        critical_racks = 0

    pending_count = len(pending_actions)
    total_recovery = pending_actions["estimated_recovery_mwh"].sum() if not pending_actions.empty else 0

    # Header
    render_header(
        title="Balancing And Imbalance Optimization",
        personas=["TMEIC Engineers", "Asset Managers", "Maintenance Team"],
        decisions=[
            "Prioritize balancing actions by severity",
            "Schedule maintenance for high-imbalance racks",
            "Optimize capacity recovery",
            "Prevent accelerated degradation",
        ],
        data_sources=[
            {"system": "Edge Intelligence", "tables": ["fact_imbalance"], "notes": "Rack-level analysis"},
            {"system": "Edge Intelligence", "tables": ["fact_balancing_actions"], "notes": "Action recommendations"},
        ],
        freshness="Updated every 15 minutes",
        kpis=[
            {"label": "Avg Imbalance Score", "value": avg_imbalance, "format": "number"},
            {"label": "Max Imbalance", "value": max_imbalance, "format": "number"},
            {"label": "Critical Racks", "value": critical_racks, "format": "integer"},
            {"label": "Pending Actions", "value": pending_count, "format": "integer"},
        ],
    )

    # Filters
    col1, col2 = st.columns(2)
    with col1:
        site_options = ["All Sites"] + [s["name"] for s in sites]
        selected_site_name = st.selectbox("Site", site_options)
        selected_site = None
        if selected_site_name != "All Sites":
            selected_site = next((s["site_id"] for s in sites if s["name"] == selected_site_name), None)

    with col2:
        hours_back = st.selectbox("Time Range", [6, 12, 24, 48, 72], index=2, format_func=lambda x: f"Last {x} hours")

    colors = get_plotly_colors()

    # Load filtered data
    imbalance_df = load_imbalance_data(selected_site, hours_back)
    actions_df = load_balancing_actions(selected_site)

    # Row 1: Imbalance Overview
    st.subheader("Imbalance Score Overview")

    col1, col2 = st.columns(2)

    with col1:
        if not imbalance_summary.empty:
            # Imbalance by rack
            fig = px.bar(
                imbalance_summary.sort_values("avg_imbalance_score", ascending=False),
                x="rack_id",
                y="avg_imbalance_score",
                color="avg_imbalance_score",
                color_continuous_scale="RdYlGn_r",
                range_color=[0, 100],
                title="Average Imbalance Score by Rack",
            )
            fig.add_hline(y=30, line_dash="dash", line_color="orange", annotation_text="Warning")
            fig.add_hline(y=60, line_dash="dash", line_color="red", annotation_text="Critical")
            fig.update_layout(height=350, xaxis_title="Rack", yaxis_title="Imbalance Score")
            style_plotly_chart(fig)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No imbalance summary data available.")

    with col2:
        if not imbalance_df.empty:
            # Severity distribution
            severity_counts = imbalance_df.groupby("severity").size().reset_index(name="count")
            fig = px.pie(
                severity_counts,
                values="count",
                names="severity",
                title="Imbalance by Severity",
                color="severity",
                color_discrete_map={
                    "critical": "#d32f2f",
                    "high": "#f57c00",
                    "medium": "#fbc02d",
                    "low": "#4caf50",
                },
            )
            fig.update_layout(height=350)
            style_plotly_chart(fig)
            st.plotly_chart(fig, use_container_width=True)

    # Row 2: Cell Deltas
    st.subheader("Cell Voltage and Temperature Deltas")

    col1, col2 = st.columns(2)

    with col1:
        if not imbalance_df.empty:
            fig = px.scatter(
                imbalance_df,
                x="max_cell_delta_mv",
                y="max_temp_delta_c",
                color="severity",
                size="imbalance_score",
                hover_data=["site_id", "rack_id"],
                title="Voltage vs Temperature Delta",
                color_discrete_map={
                    "critical": "#d32f2f",
                    "high": "#f57c00",
                    "medium": "#fbc02d",
                    "low": "#4caf50",
                },
            )
            fig.add_vline(x=50, line_dash="dash", line_color="orange")
            fig.add_vline(x=100, line_dash="dash", line_color="red")
            fig.add_hline(y=5, line_dash="dash", line_color="orange")
            fig.add_hline(y=10, line_dash="dash", line_color="red")
            fig.update_layout(
                height=350,
                xaxis_title="Max Cell Voltage Delta (mV)",
                yaxis_title="Max Temperature Delta (°C)",
            )
            style_plotly_chart(fig)
            st.plotly_chart(fig, use_container_width=True)

    with col2:
        if not imbalance_df.empty:
            # Imbalance trend
            hourly = imbalance_df.copy()
            hourly["hour"] = pd.to_datetime(hourly["ts"]).dt.floor("h")
            trend = hourly.groupby("hour")["imbalance_score"].mean().reset_index()

            fig = px.line(
                trend,
                x="hour",
                y="imbalance_score",
                title="Average Imbalance Score Trend",
            )
            fig.add_hline(y=30, line_dash="dash", line_color="orange")
            fig.add_hline(y=60, line_dash="dash", line_color="red")
            fig.update_layout(height=350)
            style_plotly_chart(fig)
            st.plotly_chart(fig, use_container_width=True)

    # Row 3: Balancing Actions
    st.subheader("Balancing Action Recommendations")

    if not pending_actions.empty:
        # Action priority summary
        col1, col2, col3 = st.columns(3)

        urgent = pending_actions[pending_actions["priority"] == "urgent"]
        high = pending_actions[pending_actions["priority"] == "high"]
        medium = pending_actions[pending_actions["priority"] == "medium"]

        with col1:
            st.metric(
                "Urgent Actions",
                len(urgent),
                delta=f"{urgent['estimated_recovery_mwh'].sum():.2f} MWh recoverable" if len(urgent) > 0 else None,
                delta_color="inverse",
            )

        with col2:
            st.metric(
                "High Priority",
                len(high),
                delta=f"{high['estimated_recovery_mwh'].sum():.2f} MWh recoverable" if len(high) > 0 else None,
            )

        with col3:
            st.metric(
                "Medium Priority",
                len(medium),
                delta=f"{medium['estimated_recovery_mwh'].sum():.2f} MWh recoverable" if len(medium) > 0 else None,
            )

        # Actions table
        st.markdown("#### Pending Actions Queue")

        def highlight_priority(val):
            colors = {
                "urgent": "background-color: #ffcdd2",
                "high": "background-color: #ffe0b2",
                "medium": "background-color: #fff9c4",
            }
            return colors.get(val, "")

        display_actions = pending_actions[[
            "site_id", "rack_id", "action_type", "priority",
            "estimated_duration_min", "estimated_recovery_mwh", "status"
        ]].rename(columns={
            "site_id": "Site",
            "rack_id": "Rack",
            "action_type": "Action Type",
            "priority": "Priority",
            "estimated_duration_min": "Duration (min)",
            "estimated_recovery_mwh": "Recovery (MWh)",
            "status": "Status",
        })

        st.dataframe(
            display_actions.style.map(highlight_priority, subset=["Priority"]).format({
                "Recovery (MWh)": "{:.3f}",
            }),
            use_container_width=True,
            height=300,
        )
    else:
        st.success("No pending balancing actions. All racks are within acceptable limits.")

    # Row 4: Recovery Potential
    st.subheader("Capacity Recovery Potential")

    if not actions_df.empty:
        col1, col2 = st.columns(2)

        with col1:
            # Recovery by action type
            recovery_by_type = actions_df.groupby("action_type")["estimated_recovery_mwh"].sum().reset_index()
            fig = px.bar(
                recovery_by_type,
                x="action_type",
                y="estimated_recovery_mwh",
                color="estimated_recovery_mwh",
                color_continuous_scale="Greens",
                title="Recoverable Energy by Action Type (MWh)",
            )
            fig.update_layout(height=300)
            style_plotly_chart(fig)
            st.plotly_chart(fig, use_container_width=True)

        with col2:
            # Recovery by site
            recovery_by_site = actions_df.groupby("site_id")["estimated_recovery_mwh"].sum().reset_index()
            fig = px.pie(
                recovery_by_site,
                values="estimated_recovery_mwh",
                names="site_id",
                title="Recoverable Energy by Site",
            )
            fig.update_layout(height=300)
            style_plotly_chart(fig)
            st.plotly_chart(fig, use_container_width=True)

    # Row 5: Rack Imbalance Details
    st.subheader("Rack Imbalance Details")

    if not imbalance_summary.empty:
        def highlight_score(val):
            if val > 60:
                return "background-color: #ffcdd2"
            elif val > 30:
                return "background-color: #fff9c4"
            return ""

        st.dataframe(
            imbalance_summary.style.map(
                highlight_score,
                subset=["avg_imbalance_score", "max_imbalance_score"]
            ).format({
                "avg_imbalance_score": "{:.1f}",
                "max_imbalance_score": "{:.1f}",
                "avg_voltage_delta_mv": "{:.0f}",
                "avg_temp_delta_c": "{:.1f}",
            }),
            use_container_width=True,
            height=250,
        )

    # Documentation
    with st.expander("Balancing Methodology"):
        st.markdown("""
        ### Edge Intelligence Balancing

        The Balancing Engine detects and addresses cell-level imbalances:

        **Imbalance Score (0-100):**
        - Combines voltage and temperature delta analysis
        - 0-30: Low - Normal variation
        - 30-60: Medium - Monitor closely
        - 60+: High/Critical - Action required

        **Detection Thresholds:**
        - Voltage: >50mV delta triggers warning, >100mV critical
        - Temperature: >5°C delta triggers warning, >10°C critical

        **Balancing Actions:**
        - **Immediate Balancing**: For critical imbalances, passive balancing cycle
        - **Scheduled Balancing**: For high severity, plan within 24 hours
        - **Monitoring**: For medium severity, increase observation frequency
        - **Thermal Management**: For temperature imbalances, review HVAC

        **Recovery Estimation:**
        - Estimates MWh capacity recoverable through balancing
        - Based on imbalance severity and rack capacity
        - Helps prioritize maintenance ROI

        **Priority Levels:**
        - Urgent: Immediate action required
        - High: Action within 24 hours
        - Medium: Plan for next maintenance window
        - Low: Monitor and include in routine maintenance
        """)

    render_footer()


if __name__ == "__main__":
    main()
