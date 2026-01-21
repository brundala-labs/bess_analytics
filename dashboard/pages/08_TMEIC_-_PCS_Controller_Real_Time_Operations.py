"""
TMEIC PCS/Controller Real-time Operations

Real-time monitoring of controller status, power output, and alarms.
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

st.set_page_config(page_title="PCS Real-time Ops", page_icon="⚡", layout="wide")

DASHBOARD_KEY = "tmeic_realtime_ops"


@st.cache_data(ttl=60)  # Short cache for real-time data
def load_realtime_data():
    """Load current operational data."""
    conn = get_connection()

    # Latest telemetry per site
    latest_telemetry = conn.execute("""
        WITH ranked AS (
            SELECT
                t.site_id,
                s.name as site_name,
                t.tag,
                t.value,
                t.ts,
                ROW_NUMBER() OVER (PARTITION BY t.site_id, t.tag ORDER BY t.ts DESC) as rn
            FROM fact_telemetry t
            JOIN dim_site s ON t.site_id = s.site_id
        )
        SELECT site_id, site_name, tag, value, ts
        FROM ranked
        WHERE rn = 1
    """).df()

    # Recent power trend (last 2 hours worth)
    power_trend = conn.execute("""
        SELECT
            t.ts,
            t.site_id,
            s.name as site_name,
            t.value as power_kw
        FROM fact_telemetry t
        JOIN dim_site s ON t.site_id = s.site_id
        WHERE t.tag = 'p_kw'
        AND t.ts >= (SELECT MAX(ts) FROM fact_telemetry) - INTERVAL '2 hours'
        ORDER BY t.ts
    """).df()

    # Active alarms
    active_alarms = conn.execute("""
        SELECT
            e.event_id,
            e.site_id,
            s.name as site_name,
            e.asset_id,
            e.severity,
            e.event_type,
            e.code,
            e.description,
            e.start_ts,
            e.end_ts
        FROM fact_events e
        JOIN dim_site s ON e.site_id = s.site_id
        WHERE e.end_ts > (SELECT MAX(ts) FROM fact_telemetry) - INTERVAL '1 hour'
           OR e.end_ts IS NULL
        ORDER BY e.start_ts DESC
    """).df()

    # Current dispatch
    current_dispatch = conn.execute("""
        WITH latest AS (
            SELECT
                d.site_id,
                s.name as site_name,
                d.service_id,
                svc.name as service_name,
                d.command_kw,
                d.actual_kw,
                d.ts,
                ROW_NUMBER() OVER (PARTITION BY d.site_id ORDER BY d.ts DESC) as rn
            FROM fact_dispatch d
            JOIN dim_site s ON d.site_id = s.site_id
            JOIN dim_service svc ON d.service_id = svc.service_id
        )
        SELECT site_id, site_name, service_name, command_kw, actual_kw, ts
        FROM latest
        WHERE rn = 1
    """).df()

    sites = conn.execute("SELECT site_id, name FROM dim_site").df().to_dict(orient="records")

    conn.close()
    return latest_telemetry, power_trend, active_alarms, current_dispatch, sites


def main():
    latest_telemetry, power_trend, active_alarms, current_dispatch, sites = load_realtime_data()

    # Pivot telemetry for easy access
    if not latest_telemetry.empty:
        telemetry_pivot = latest_telemetry.pivot(
            index=["site_id", "site_name"],
            columns="tag",
            values="value"
        ).reset_index()
    else:
        telemetry_pivot = pd.DataFrame()

    # Calculate KPIs
    current_power = telemetry_pivot["p_kw"].sum() / 1000 if "p_kw" in telemetry_pivot.columns else 0
    current_freq = telemetry_pivot["f_hz"].mean() if "f_hz" in telemetry_pivot.columns else 50.0
    current_soc = telemetry_pivot["soc_pct"].mean() if "soc_pct" in telemetry_pivot.columns else 0
    active_alarm_count = len(active_alarms)
    controller_status = "Online" if telemetry_pivot["controller_status"].mean() > 0.5 else "Offline" if not telemetry_pivot.empty else "Unknown"

    # Dispatch compliance
    if not current_dispatch.empty:
        compliance = (current_dispatch["actual_kw"] / current_dispatch["command_kw"].replace(0, 1)).mean() * 100
    else:
        compliance = 100

    kpi_values = {
        "current_power_mw": current_power,
        "current_frequency_hz": current_freq,
        "current_soc_pct": current_soc,
        "active_alarm_count": active_alarm_count,
        "controller_status": controller_status,
        "dispatch_compliance_pct": compliance,
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

    # Site selector
    filters = render_filter_bar(show_site=True, show_date_range=False, sites=sites)

    # Real-time power chart
    st.subheader("Real-time Power Output")

    filtered_power = power_trend.copy()
    if filters.get("site_id"):
        filtered_power = filtered_power[filtered_power["site_id"] == filters["site_id"]]

    if not filtered_power.empty:
        fig = px.line(
            filtered_power,
            x="ts",
            y="power_kw",
            color="site_name",
            title="Power Output (kW) - Last 2 Hours"
        )
        fig.add_hline(y=0, line_dash="dash", line_color="gray")
        fig.update_layout(height=350)
        st.plotly_chart(fig, use_container_width=True)

    # Site status cards
    st.subheader("Site Status Overview")

    if not telemetry_pivot.empty:
        cols = st.columns(len(telemetry_pivot))
        for idx, (_, row) in enumerate(telemetry_pivot.iterrows()):
            with cols[idx]:
                site_name = row["site_name"]
                power = row.get("p_kw", 0) / 1000
                soc = row.get("soc_pct", 0)
                freq = row.get("f_hz", 50)
                status = "🟢" if row.get("controller_status", 0) > 0.5 else "🔴"

                st.markdown(f"### {status} {site_name}")
                st.metric("Power (MW)", f"{power:.2f}")
                st.metric("SOC", f"{soc:.1f}%")
                st.metric("Frequency", f"{freq:.2f} Hz")

    # Current dispatch and alarms
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Current Dispatch Commands")
        if not current_dispatch.empty:
            st.dataframe(
                current_dispatch[[
                    "site_name", "service_name", "command_kw", "actual_kw"
                ]].rename(columns={
                    "site_name": "Site",
                    "service_name": "Service",
                    "command_kw": "Command (kW)",
                    "actual_kw": "Actual (kW)"
                }),
                use_container_width=True,
                height=200,
            )

    with col2:
        st.subheader("Active Alarms")
        if not active_alarms.empty:
            alarm_display = active_alarms[[
                "site_name", "severity", "event_type", "code"
            ]].copy()

            alarm_display["severity_icon"] = alarm_display["severity"].map({
                "critical": "🔴",
                "high": "🟠",
                "medium": "🟡",
                "low": "🟢"
            })

            st.dataframe(
                alarm_display[[
                    "severity_icon", "site_name", "event_type", "code"
                ]].rename(columns={
                    "severity_icon": "⚠️",
                    "site_name": "Site",
                    "event_type": "Type",
                    "code": "Code"
                }),
                use_container_width=True,
                height=200,
            )
        else:
            st.success("No active alarms")

    # Grid parameters
    st.subheader("Grid Parameters")

    if not telemetry_pivot.empty:
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            v_pu = telemetry_pivot["v_pu"].mean() if "v_pu" in telemetry_pivot.columns else 1.0
            st.metric("Voltage (p.u.)", f"{v_pu:.3f}")

        with col2:
            freq = telemetry_pivot["f_hz"].mean() if "f_hz" in telemetry_pivot.columns else 50.0
            st.metric("Frequency (Hz)", f"{freq:.3f}")

        with col3:
            q_kvar = telemetry_pivot["q_kvar"].sum() / 1000 if "q_kvar" in telemetry_pivot.columns else 0
            st.metric("Reactive Power (Mvar)", f"{q_kvar:.2f}")

        with col4:
            efficiency = telemetry_pivot["inverter_efficiency_pct"].mean() if "inverter_efficiency_pct" in telemetry_pivot.columns else 0
            st.metric("Efficiency (%)", f"{efficiency:.1f}")

    # Auto-refresh hint
    st.caption("💡 Data refreshes every 60 seconds. Use browser refresh for immediate update.")


if __name__ == "__main__":
    main()
