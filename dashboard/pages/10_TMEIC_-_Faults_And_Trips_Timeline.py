"""
TMEIC Faults/Trips Timeline

Fault tracking, root cause analysis, and maintenance correlation.
"""

import sys
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from dashboard.components.header import get_dashboard_config, render_header, render_filter_bar
from db.loader import get_connection

st.set_page_config(page_title="Faults Timeline", page_icon="⚠️", layout="wide")

DASHBOARD_KEY = "tmeic_faults_timeline"


@st.cache_data(ttl=120)
def load_faults_data():
    """Load fault and maintenance data."""
    conn = get_connection()

    # All events
    events = conn.execute("""
        SELECT
            e.event_id,
            e.site_id,
            s.name as site_name,
            e.asset_id,
            a.asset_type,
            e.start_ts,
            e.end_ts,
            EXTRACT(EPOCH FROM (COALESCE(e.end_ts, e.start_ts + INTERVAL '60 minutes') - e.start_ts)) / 60 as duration_min,
            e.severity,
            e.event_type,
            e.code,
            e.description
        FROM fact_events e
        JOIN dim_site s ON e.site_id = s.site_id
        JOIN dim_asset a ON e.asset_id = a.asset_id
        ORDER BY e.start_ts DESC
    """).df()

    # Maintenance tickets
    maintenance = conn.execute("""
        SELECT
            m.ticket_id,
            m.site_id,
            s.name as site_name,
            m.asset_id,
            m.opened_ts,
            m.closed_ts,
            EXTRACT(EPOCH FROM (COALESCE(m.closed_ts, m.opened_ts + INTERVAL '24 hours') - m.opened_ts)) / 3600 as resolution_hours,
            m.issue_category,
            m.resolution,
            m.cost_gbp
        FROM fact_maintenance m
        JOIN dim_site s ON m.site_id = s.site_id
        ORDER BY m.opened_ts DESC
    """).df()

    # Fault code frequency
    fault_codes = conn.execute("""
        SELECT
            code,
            COUNT(*) as count,
            AVG(EXTRACT(EPOCH FROM (end_ts - start_ts)) / 60) as avg_duration_min
        FROM fact_events
        WHERE event_type IN ('fault', 'trip')
        GROUP BY code
        ORDER BY count DESC
    """).df()

    sites = conn.execute("SELECT site_id, name FROM dim_site").df().to_dict(orient="records")

    conn.close()
    return events, maintenance, fault_codes, sites


def main():
    events, maintenance, fault_codes, sites = load_faults_data()

    # Filter to faults and trips
    faults = events[events["event_type"].isin(["fault", "trip"])]

    # Calculate KPIs
    active_faults = len(faults[faults["end_ts"].isna() | (faults["end_ts"] > faults["start_ts"].max() - pd.Timedelta(hours=1))])
    faults_7d = len(faults[faults["start_ts"] >= faults["start_ts"].max() - pd.Timedelta(days=7)])

    # MTTR calculation
    resolved = maintenance[maintenance["closed_ts"].notna()]
    avg_mttr = resolved["resolution_hours"].mean() if not resolved.empty else 0

    # Top fault code
    top_code = fault_codes["code"].iloc[0] if not fault_codes.empty else "N/A"

    # Trips in 30 days
    trips_30d = len(faults[(faults["event_type"] == "trip") &
                          (faults["start_ts"] >= faults["start_ts"].max() - pd.Timedelta(days=30))])

    # Repeat fault rate
    if not fault_codes.empty:
        total_faults = fault_codes["count"].sum()
        repeat_faults = fault_codes[fault_codes["count"] > 1]["count"].sum()
        repeat_rate = (repeat_faults / total_faults) * 100 if total_faults > 0 else 0
    else:
        repeat_rate = 0

    kpi_values = {
        "active_faults": active_faults,
        "faults_7d": faults_7d,
        "avg_mttr_hours": avg_mttr,
        "top_fault_code": top_code,
        "trips_30d": trips_30d,
        "repeat_fault_rate_pct": repeat_rate,
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
    filtered_events = faults.copy()
    if filters.get("site_id"):
        filtered_events = filtered_events[filtered_events["site_id"] == filters["site_id"]]

    # Event type filter
    event_types = st.multiselect(
        "Event Types",
        ["fault", "trip"],
        default=["fault", "trip"]
    )
    filtered_events = filtered_events[filtered_events["event_type"].isin(event_types)]

    # Timeline chart
    st.subheader("Fault/Trip Timeline")

    if not filtered_events.empty:
        # Create timeline visualization
        timeline_df = filtered_events.head(50).copy()
        timeline_df["end_ts"] = timeline_df["end_ts"].fillna(timeline_df["start_ts"].max())

        fig = px.timeline(
            timeline_df,
            x_start="start_ts",
            x_end="end_ts",
            y="site_name",
            color="severity",
            color_discrete_map={
                "critical": "#d32f2f",
                "high": "#f57c00",
                "medium": "#fbc02d",
                "low": "#388e3c"
            },
            hover_data=["code", "description"],
            title="Event Timeline (Recent 50)"
        )
        fig.update_layout(height=300)
        st.plotly_chart(fig, use_container_width=True)

    # Fault analysis
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Top Fault Codes")
        if not fault_codes.empty:
            fig = px.bar(
                fault_codes.head(10),
                x="code",
                y="count",
                color="count",
                color_continuous_scale="Reds",
                title="Most Frequent Fault Codes"
            )
            fig.update_layout(height=300)
            st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.subheader("Events by Severity")
        if not filtered_events.empty:
            severity_counts = filtered_events.groupby("severity").size().reset_index(name="count")
            fig = px.pie(
                severity_counts,
                values="count",
                names="severity",
                color="severity",
                color_discrete_map={
                    "critical": "#d32f2f",
                    "high": "#f57c00",
                    "medium": "#fbc02d",
                    "low": "#388e3c"
                },
                title="Distribution by Severity"
            )
            fig.update_layout(height=300)
            st.plotly_chart(fig, use_container_width=True)

    # Daily fault trend
    st.subheader("Daily Event Trend")

    if not filtered_events.empty:
        daily = filtered_events.copy()
        daily["date"] = daily["start_ts"].dt.date
        daily_counts = daily.groupby(["date", "event_type"]).size().reset_index(name="count")

        fig = px.bar(
            daily_counts,
            x="date",
            y="count",
            color="event_type",
            barmode="stack",
            title="Events per Day"
        )
        fig.update_layout(height=280)
        st.plotly_chart(fig, use_container_width=True)

    # MTTR analysis and maintenance link
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Mean Time to Repair (MTTR)")
        if not maintenance.empty:
            mttr_by_category = maintenance.groupby("issue_category")["resolution_hours"].mean().reset_index()

            fig = px.bar(
                mttr_by_category,
                x="issue_category",
                y="resolution_hours",
                color="resolution_hours",
                color_continuous_scale="Blues",
                title="MTTR by Issue Category (Hours)"
            )
            fig.update_layout(height=280)
            st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.subheader("Maintenance Tickets")
        if not maintenance.empty:
            display = maintenance.head(10)[[
                "site_name", "issue_category", "resolution", "resolution_hours", "cost_gbp"
            ]].copy()

            st.dataframe(
                display.rename(columns={
                    "site_name": "Site",
                    "issue_category": "Category",
                    "resolution": "Resolution",
                    "resolution_hours": "Hours",
                    "cost_gbp": "Cost (£)"
                }).style.format({
                    "Hours": "{:.1f}",
                    "Cost (£)": "£{:,.0f}"
                }),
                use_container_width=True,
                height=280,
            )

    # Detailed event table
    st.subheader("Event Details")

    if not filtered_events.empty:
        display_events = filtered_events.head(30)[[
            "start_ts", "site_name", "asset_type", "severity", "event_type", "code", "duration_min"
        ]].copy()

        display_events["start_ts"] = display_events["start_ts"].dt.strftime("%Y-%m-%d %H:%M")

        def severity_color(val):
            colors = {
                "critical": "background-color: #ffcdd2",
                "high": "background-color: #ffe0b2",
                "medium": "background-color: #fff9c4",
                "low": "background-color: #c8e6c9"
            }
            return colors.get(val, "")

        st.dataframe(
            display_events.rename(columns={
                "start_ts": "Start Time",
                "site_name": "Site",
                "asset_type": "Asset Type",
                "severity": "Severity",
                "event_type": "Type",
                "code": "Code",
                "duration_min": "Duration (min)"
            }).style.applymap(severity_color, subset=["Severity"]).format({
                "Duration (min)": "{:.0f}"
            }),
            use_container_width=True,
            height=350,
        )


if __name__ == "__main__":
    main()
