"""
TMEIC Historian Explorer

Deep-dive telemetry exploration and data export for troubleshooting.
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from dashboard.components.branding import apply_enka_theme, render_sidebar_branding, render_footer, style_plotly_chart
from dashboard.components.header import get_dashboard_config, render_header
from db.loader import get_connection

st.set_page_config(initial_sidebar_state="expanded", page_title="Historian Explorer", page_icon="🔍", layout="wide")

# Apply ENKA branding
apply_enka_theme()
render_sidebar_branding("12_Historian_Explorer")


DASHBOARD_KEY = "tmeic_historian"


@st.cache_data(ttl=600)
def load_tag_list():
    """Load available tags."""
    conn = get_connection()
    tags = conn.execute("""
        SELECT DISTINCT tag
        FROM fact_telemetry
        ORDER BY tag
    """).df()
    conn.close()
    return tags["tag"].tolist()


@st.cache_data(ttl=600)
def load_sites():
    """Load site list."""
    conn = get_connection()
    sites = conn.execute("SELECT site_id, name FROM dim_site").df()
    conn.close()
    return sites.to_dict(orient="records")


@st.cache_data(ttl=60)
def load_telemetry(site_id: str, tags: list, start_date, end_date, resolution: str):
    """Load telemetry data for selected tags."""
    conn = get_connection()

    tag_list = ", ".join([f"'{t}'" for t in tags])

    resolution_map = {
        "1 minute": "ts",
        "5 minutes": "DATE_TRUNC('minute', ts) - INTERVAL '1 minute' * (EXTRACT(MINUTE FROM ts)::INT % 5)",
        "15 minutes": "DATE_TRUNC('minute', ts) - INTERVAL '1 minute' * (EXTRACT(MINUTE FROM ts)::INT % 15)",
        "1 hour": "DATE_TRUNC('hour', ts)",
    }
    time_bucket = resolution_map.get(resolution, "ts")

    query = f"""
        SELECT
            {time_bucket} as ts,
            tag,
            AVG(value) as value,
            MIN(value) as min_value,
            MAX(value) as max_value,
            COUNT(*) as sample_count
        FROM fact_telemetry
        WHERE site_id = '{site_id}'
        AND tag IN ({tag_list})
        AND ts >= '{start_date}'
        AND ts <= '{end_date}'
        GROUP BY {time_bucket}, tag
        ORDER BY ts
    """

    df = conn.execute(query).df()
    conn.close()
    return df


@st.cache_data(ttl=60)
def load_events(site_id: str, start_date, end_date):
    """Load events for timeline overlay."""
    conn = get_connection()

    df = conn.execute(f"""
        SELECT
            event_id,
            start_ts,
            end_ts,
            severity,
            event_type,
            code,
            description
        FROM fact_events
        WHERE site_id = '{site_id}'
        AND start_ts >= '{start_date}'
        AND start_ts <= '{end_date}'
        ORDER BY start_ts
    """).df()

    conn.close()
    return df


def main():
    sites = load_sites()
    tags = load_tag_list()

    # Simple KPIs for header
    kpi_values = {
        "total_tags_count": len(tags),
        "selected_data_points": 0,
        "data_date_range": "Select data",
        "export_status": "Ready",
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

    # Selection panel
    st.subheader("Data Selection")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        site_names = {s["site_id"]: s["name"] for s in sites}
        selected_site_name = st.selectbox("Site", list(site_names.values()))
        selected_site = [k for k, v in site_names.items() if v == selected_site_name][0]

    with col2:
        default_end = datetime(2024, 3, 15)
        default_start = default_end - timedelta(days=1)
        date_range = st.date_input(
            "Date Range",
            value=(default_start.date(), default_end.date())
        )
        if isinstance(date_range, tuple) and len(date_range) == 2:
            start_date, end_date = date_range
        else:
            start_date = date_range[0] if date_range else default_start.date()
            end_date = default_end.date()

    with col3:
        resolution = st.selectbox(
            "Resolution",
            ["1 minute", "5 minutes", "15 minutes", "1 hour"],
            index=1
        )

    with col4:
        selected_tags = st.multiselect(
            "Tags",
            tags,
            default=["p_kw", "soc_pct"] if "p_kw" in tags else tags[:2]
        )

    # Tag categories for quick selection
    st.markdown("**Quick Tag Groups:**")
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        if st.button("Power Tags"):
            selected_tags = [t for t in tags if t in ["p_kw", "q_kvar", "inverter_efficiency_pct"]]
            st.rerun()

    with col2:
        if st.button("Battery Tags"):
            selected_tags = [t for t in tags if t in ["soc_pct", "soh_pct", "temp_c_avg", "temp_c_max", "cycle_count"]]
            st.rerun()

    with col3:
        if st.button("Grid Tags"):
            selected_tags = [t for t in tags if t in ["v_pu", "f_hz"]]
            st.rerun()

    with col4:
        if st.button("Comms Tags"):
            selected_tags = [t for t in tags if t in ["comms_latency_ms", "comms_drop_rate", "controller_status"]]
            st.rerun()

    # Load and display data
    if selected_tags and selected_site:
        telemetry = load_telemetry(
            selected_site,
            selected_tags,
            start_date,
            end_date,
            resolution
        )

        events = load_events(selected_site, start_date, end_date)

        if not telemetry.empty:
            st.subheader("Telemetry Chart")

            # Create multi-axis chart
            fig = go.Figure()

            colors = px.colors.qualitative.Set1
            for idx, tag in enumerate(selected_tags):
                tag_data = telemetry[telemetry["tag"] == tag]
                if not tag_data.empty:
                    fig.add_trace(go.Scatter(
                        x=tag_data["ts"],
                        y=tag_data["value"],
                        name=tag,
                        mode="lines",
                        line=dict(color=colors[idx % len(colors)])
                    ))

            # Add event markers
            if not events.empty:
                for _, event in events.iterrows():
                    fig.add_vrect(
                        x0=event["start_ts"],
                        x1=event["end_ts"] if pd.notna(event["end_ts"]) else event["start_ts"],
                        fillcolor="red",
                        opacity=0.2,
                        line_width=0,
                        annotation_text=event["code"],
                        annotation_position="top left"
                    )

            fig.update_layout(
                height=450,
                title=f"Telemetry: {', '.join(selected_tags)}",
                xaxis_title="Time",
                yaxis_title="Value",
                legend=dict(orientation="h", yanchor="bottom", y=1.02)
            )

            st.plotly_chart(fig, use_container_width=True)

            # Statistics table
            st.subheader("Statistics")

            stats = telemetry.groupby("tag").agg({
                "value": ["mean", "min", "max", "std"],
                "sample_count": "sum"
            }).round(3)

            stats.columns = ["Mean", "Min", "Max", "Std Dev", "Samples"]
            stats = stats.reset_index()

            st.dataframe(stats, use_container_width=True)

            # Data table
            st.subheader("Raw Data")

            # Pivot for display
            if len(selected_tags) > 1:
                pivot = telemetry.pivot(index="ts", columns="tag", values="value").reset_index()
                display_df = pivot.head(500)
            else:
                display_df = telemetry[["ts", "value", "min_value", "max_value"]].head(500)

            st.dataframe(display_df, use_container_width=True, height=300)

            # Export button
            st.download_button(
                label="Download Data (CSV)",
                data=telemetry.to_csv(index=False),
                file_name=f"telemetry_{selected_site}_{start_date}_{end_date}.csv",
                mime="text/csv"
            )

            # Update KPI
            st.sidebar.metric("Data Points Loaded", f"{len(telemetry):,}")

        else:
            st.warning("No data found for selected parameters")

    # Events panel
    if selected_site:
        st.subheader("Events During Period")
        events = load_events(selected_site, start_date, end_date)

        if not events.empty:
            events_display = events[[
                "start_ts", "end_ts", "severity", "event_type", "code", "description"
            ]].copy()

            events_display["start_ts"] = events_display["start_ts"].dt.strftime("%Y-%m-%d %H:%M")
            events_display["end_ts"] = events_display["end_ts"].fillna("Ongoing")

            st.dataframe(
                events_display.rename(columns={
                    "start_ts": "Start",
                    "end_ts": "End",
                    "severity": "Severity",
                    "event_type": "Type",
                    "code": "Code",
                    "description": "Description"
                }),
                use_container_width=True,
                height=200,
            )
        else:
            st.info("No events during selected period")


if __name__ == "__main__":
    main()
