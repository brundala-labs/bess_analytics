"""
TMEIC Controller Health & Communications

Communication health monitoring, latency tracking, and data completeness.
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

st.set_page_config(page_title="Controller Health", page_icon="📡", layout="wide")

# Apply ENKA branding
apply_enka_theme()
render_sidebar_branding()


DASHBOARD_KEY = "tmeic_controller_health"


@st.cache_data(ttl=120)
def load_comms_data():
    """Load communications health data."""
    conn = get_connection()

    # Comms latency trend
    latency_trend = conn.execute("""
        SELECT
            DATE_TRUNC('hour', t.ts) as hour,
            t.site_id,
            s.name as site_name,
            AVG(t.value) as avg_latency,
            MAX(t.value) as max_latency,
            MIN(t.value) as min_latency
        FROM fact_telemetry t
        JOIN dim_site s ON t.site_id = s.site_id
        WHERE t.tag = 'comms_latency_ms'
        GROUP BY DATE_TRUNC('hour', t.ts), t.site_id, s.name
        ORDER BY hour
    """).df()

    # Comms drop events
    drop_trend = conn.execute("""
        SELECT
            DATE_TRUNC('hour', t.ts) as hour,
            t.site_id,
            s.name as site_name,
            AVG(t.value) as avg_drop_rate,
            COUNT(CASE WHEN t.value > 0 THEN 1 END) as drop_minutes
        FROM fact_telemetry t
        JOIN dim_site s ON t.site_id = s.site_id
        WHERE t.tag = 'comms_drop_rate'
        GROUP BY DATE_TRUNC('hour', t.ts), t.site_id, s.name
        ORDER BY hour
    """).df()

    # Data quality
    data_quality = conn.execute("""
        SELECT
            dq.ts_hour,
            dq.site_id,
            s.name as site_name,
            dq.completeness_pct,
            dq.missing_tags_count
        FROM fact_data_quality dq
        JOIN dim_site s ON dq.site_id = s.site_id
        ORDER BY dq.ts_hour
    """).df()

    # Daily quality summary
    daily_quality = conn.execute("""
        SELECT
            site_id,
            date,
            avg_completeness,
            min_completeness,
            total_missing_tags
        FROM v_data_quality_daily
        ORDER BY date
    """).df()

    # Comms-related events
    comms_events = conn.execute("""
        SELECT
            e.event_id,
            e.site_id,
            s.name as site_name,
            e.start_ts,
            e.end_ts,
            EXTRACT(EPOCH FROM (e.end_ts - e.start_ts)) / 60 as duration_min,
            e.code,
            e.description
        FROM fact_events e
        JOIN dim_site s ON e.site_id = s.site_id
        WHERE e.event_type = 'comms_drop'
        ORDER BY e.start_ts DESC
    """).df()

    sites = conn.execute("SELECT site_id, name FROM dim_site").df().to_dict(orient="records")

    conn.close()
    return latency_trend, drop_trend, data_quality, daily_quality, comms_events, sites


def main():
    latency_trend, drop_trend, data_quality, daily_quality, comms_events, sites = load_comms_data()

    # Calculate KPIs
    # Latest hour stats
    if not latency_trend.empty:
        latest_hour = latency_trend[latency_trend["hour"] == latency_trend["hour"].max()]
        avg_latency = latest_hour["avg_latency"].mean()
    else:
        avg_latency = 0

    if not data_quality.empty:
        latest_quality = data_quality[data_quality["ts_hour"] == data_quality["ts_hour"].max()]
        completeness = latest_quality["completeness_pct"].mean()
        missing_tags = latest_quality["missing_tags_count"].sum()
    else:
        completeness = 0
        missing_tags = 0

    # Calculate uptime (inverse of drop rate)
    if not drop_trend.empty:
        total_hours = len(drop_trend["hour"].unique())
        drop_hours = (drop_trend["avg_drop_rate"] > 0).sum()
        uptime = ((total_hours - drop_hours) / total_hours) * 100 if total_hours > 0 else 100
    else:
        uptime = 100

    # 24h comms drops
    drops_24h = len(comms_events[comms_events["start_ts"] >= comms_events["start_ts"].max() - pd.Timedelta(hours=24)]) if not comms_events.empty else 0

    # Sites with issues
    sites_with_issues = 0
    if not daily_quality.empty:
        latest_day = daily_quality[daily_quality["date"] == daily_quality["date"].max()]
        sites_with_issues = (latest_day["avg_completeness"] < 95).sum()

    kpi_values = {
        "comms_uptime_pct": uptime,
        "avg_comms_latency_ms": avg_latency,
        "data_completeness_pct": completeness,
        "comms_drops_24h": drops_24h,
        "sites_comms_issues": sites_with_issues,
        "missing_tags_count": int(missing_tags),
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
    filtered_latency = latency_trend.copy()
    filtered_quality = data_quality.copy()
    filtered_events = comms_events.copy()

    if filters.get("site_id"):
        filtered_latency = filtered_latency[filtered_latency["site_id"] == filters["site_id"]]
        filtered_quality = filtered_quality[filtered_quality["site_id"] == filters["site_id"]]
        filtered_events = filtered_events[filtered_events["site_id"] == filters["site_id"]]

    # Latency chart
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Communication Latency")
        if not filtered_latency.empty:
            fig = px.line(
                filtered_latency,
                x="hour",
                y="avg_latency",
                color="site_name",
                title="Avg Latency (ms) by Hour"
            )
            fig.add_hline(y=100, line_dash="dash", line_color="orange", annotation_text="Warning")
            fig.add_hline(y=500, line_dash="dash", line_color="red", annotation_text="Critical")
            fig.update_layout(height=300)
            st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.subheader("Data Completeness")
        if not filtered_quality.empty:
            fig = px.line(
                filtered_quality,
                x="ts_hour",
                y="completeness_pct",
                color="site_name",
                title="Data Completeness % by Hour"
            )
            fig.add_hline(y=95, line_dash="dash", line_color="orange", annotation_text="Target 95%")
            fig.update_layout(height=300)
            st.plotly_chart(fig, use_container_width=True)

    # Heatmap of data quality by site
    st.subheader("Data Quality Heatmap")

    if not daily_quality.empty:
        pivot = daily_quality.pivot(index="site_id", columns="date", values="avg_completeness")
        fig = px.imshow(
            pivot.values,
            x=[str(d)[:10] for d in pivot.columns],
            y=pivot.index.tolist(),
            color_continuous_scale="RdYlGn",
            zmin=80,
            zmax=100,
            aspect="auto",
            title="Daily Data Completeness by Site"
        )
        fig.update_layout(height=200)
        st.plotly_chart(fig, use_container_width=True)

    # Missing tags and comms events
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Missing Tags Trend")
        if not filtered_quality.empty:
            fig = px.bar(
                filtered_quality.groupby("ts_hour")["missing_tags_count"].sum().reset_index(),
                x="ts_hour",
                y="missing_tags_count",
                title="Missing Tags Count by Hour"
            )
            fig.update_layout(height=280)
            st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.subheader("Recent Comms Drop Events")
        if not filtered_events.empty:
            display_events = filtered_events.head(10)[[
                "site_name", "start_ts", "duration_min", "code"
            ]].copy()

            display_events["start_ts"] = display_events["start_ts"].dt.strftime("%Y-%m-%d %H:%M")

            st.dataframe(
                display_events.rename(columns={
                    "site_name": "Site",
                    "start_ts": "Start",
                    "duration_min": "Duration (min)",
                    "code": "Code"
                }),
                use_container_width=True,
                height=280,
            )
        else:
            st.success("No recent comms drop events")

    # Site health summary
    st.subheader("Site Communication Health Summary")

    if not daily_quality.empty:
        latest = daily_quality[daily_quality["date"] == daily_quality["date"].max()]

        summary = latest.copy()
        summary["status"] = summary["avg_completeness"].apply(
            lambda x: "🟢 Healthy" if x >= 98 else ("🟡 Degraded" if x >= 95 else "🔴 Critical")
        )

        for site in sites:
            if site["site_id"] not in summary["site_id"].values:
                summary = pd.concat([summary, pd.DataFrame([{
                    "site_id": site["site_id"],
                    "avg_completeness": 0,
                    "status": "⚫ No Data"
                }])], ignore_index=True)

        st.dataframe(
            summary[[
                "site_id", "avg_completeness", "min_completeness", "total_missing_tags", "status"
            ]].rename(columns={
                "site_id": "Site",
                "avg_completeness": "Avg Completeness %",
                "min_completeness": "Min Completeness %",
                "total_missing_tags": "Missing Tags",
                "status": "Status"
            }),
            use_container_width=True,
        )


if __name__ == "__main__":
    main()
