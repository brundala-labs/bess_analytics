"""
Combined SLA & Warranty Evidence Pack

SLA compliance tracking and warranty evidence documentation.
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

st.set_page_config(page_title="SLA & Warranty Evidence", page_icon="📋", layout="wide")

DASHBOARD_KEY = "combined_sla_warranty"


@st.cache_data(ttl=300)
def load_sla_data():
    """Load SLA and warranty data."""
    conn = get_connection()

    # SLA compliance
    sla_compliance = conn.execute("""
        SELECT
            sla_id,
            site_id,
            site_name,
            metric_name,
            threshold,
            actual_value,
            status,
            penalty_rate_per_hour
        FROM v_sla_compliance
    """).df()

    # SLA definitions
    sla_definitions = conn.execute("""
        SELECT
            sla.sla_id,
            sla.site_id,
            s.name as site_name,
            sla.metric_name,
            sla.threshold,
            sla.penalty_rate_per_hour
        FROM dim_sla sla
        JOIN dim_site s ON sla.site_id = s.site_id
    """).df()

    # Daily availability for SLA tracking
    availability = conn.execute("""
        SELECT
            site_id,
            date,
            availability_pct
        FROM v_site_availability
        ORDER BY date
    """).df()

    # Events that impact SLA
    sla_events = conn.execute("""
        SELECT
            e.event_id,
            e.site_id,
            s.name as site_name,
            e.start_ts,
            e.end_ts,
            EXTRACT(EPOCH FROM (e.end_ts - e.start_ts)) / 3600 as duration_hours,
            e.severity,
            e.event_type,
            e.code,
            e.description
        FROM fact_events e
        JOIN dim_site s ON e.site_id = s.site_id
        WHERE e.event_type IN ('fault', 'trip')
        AND e.severity IN ('critical', 'high')
        ORDER BY e.start_ts DESC
    """).df()

    # Operating excursions (temperature, voltage out of spec)
    excursions = conn.execute("""
        SELECT
            t.site_id,
            s.name as site_name,
            t.ts,
            t.tag,
            t.value
        FROM fact_telemetry t
        JOIN dim_site s ON t.site_id = s.site_id
        WHERE (t.tag = 'temp_c_max' AND t.value > 45)
           OR (t.tag = 'v_pu' AND (t.value < 0.9 OR t.value > 1.1))
        ORDER BY t.ts DESC
    """).df()

    sites = conn.execute("SELECT site_id, name FROM dim_site").df().to_dict(orient="records")

    conn.close()
    return sla_compliance, sla_definitions, availability, sla_events, excursions, sites


def main():
    sla_compliance, sla_definitions, availability, sla_events, excursions, sites = load_sla_data()

    # Calculate KPIs
    sla_breaches = (sla_compliance["status"] == "BREACH").sum() if not sla_compliance.empty else 0

    # Penalty exposure (daily penalty for breaches)
    if not sla_compliance.empty:
        penalty_exposure = sla_compliance[
            sla_compliance["status"] == "BREACH"
        ]["penalty_rate_per_hour"].sum() * 24 * 30  # Monthly estimate
    else:
        penalty_exposure = 0

    warranty_claims = 3  # Mock - pending warranty claims

    evidence_ready = len(sla_events) if not sla_events.empty else 0

    compliance_score = ((sla_compliance["status"] == "COMPLIANT").sum() /
                       len(sla_compliance) * 100) if not sla_compliance.empty else 100

    # Days since last breach
    if not sla_events.empty and len(sla_events) > 0:
        last_event = sla_events["start_ts"].max()
        days_since = (pd.Timestamp.now() - last_event).days
    else:
        days_since = 30

    kpi_values = {
        "sla_breaches_mtd": sla_breaches,
        "penalty_exposure_gbp": penalty_exposure,
        "warranty_claims_pending": warranty_claims,
        "evidence_packets_ready": evidence_ready,
        "sla_compliance_score": compliance_score,
        "days_since_breach": days_since,
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

    # SLA Compliance Overview
    st.subheader("SLA Compliance Status")

    col1, col2 = st.columns([2, 1])

    with col1:
        if not sla_compliance.empty:
            # Status by site and metric
            pivot = sla_compliance.pivot(
                index="site_name",
                columns="metric_name",
                values="status"
            ).fillna("N/A")

            def color_status(val):
                if val == "COMPLIANT":
                    return "background-color: #c8e6c9"
                elif val == "BREACH":
                    return "background-color: #ffcdd2"
                return ""

            st.dataframe(
                pivot.style.applymap(color_status),
                use_container_width=True,
            )

    with col2:
        if not sla_compliance.empty:
            status_counts = sla_compliance["status"].value_counts()
            fig = px.pie(
                values=status_counts.values,
                names=status_counts.index,
                color=status_counts.index,
                color_discrete_map={"COMPLIANT": "#4caf50", "BREACH": "#f44336"},
                title="Overall SLA Status"
            )
            fig.update_layout(height=250)
            st.plotly_chart(fig, use_container_width=True)

    # Availability trend
    st.subheader("Availability Trend vs SLA Threshold")

    if not availability.empty:
        filtered_avail = availability.copy()
        if filters.get("site_id"):
            filtered_avail = filtered_avail[filtered_avail["site_id"] == filters["site_id"]]

        # Get threshold (assume 95% from SLA)
        threshold = 95

        fig = go.Figure()

        for site_id in filtered_avail["site_id"].unique():
            site_data = filtered_avail[filtered_avail["site_id"] == site_id]
            site_name = [s["name"] for s in sites if s["site_id"] == site_id][0]
            fig.add_trace(go.Scatter(
                x=site_data["date"],
                y=site_data["availability_pct"],
                name=site_name,
                mode="lines"
            ))

        fig.add_hline(y=threshold, line_dash="dash", line_color="red",
                     annotation_text=f"SLA Threshold ({threshold}%)")
        fig.update_layout(height=300, title="Daily Availability vs SLA")
        st.plotly_chart(fig, use_container_width=True)

    # SLA Events (Evidence)
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("SLA-Impacting Events")
        if not sla_events.empty:
            display = sla_events.head(20)[[
                "site_name", "start_ts", "duration_hours", "severity", "code"
            ]].copy()

            display["start_ts"] = display["start_ts"].dt.strftime("%Y-%m-%d %H:%M")

            def severity_color(val):
                colors = {"critical": "background-color: #ffcdd2", "high": "background-color: #ffe0b2"}
                return colors.get(val, "")

            st.dataframe(
                display.rename(columns={
                    "site_name": "Site",
                    "start_ts": "Start",
                    "duration_hours": "Hours",
                    "severity": "Severity",
                    "code": "Code"
                }).style.applymap(severity_color, subset=["Severity"]).format({
                    "Hours": "{:.1f}"
                }),
                use_container_width=True,
                height=300,
            )

    with col2:
        st.subheader("Operating Excursions")
        if not excursions.empty:
            excursion_summary = excursions.groupby(["site_name", "tag"]).size().reset_index(name="count")

            fig = px.bar(
                excursion_summary,
                x="site_name",
                y="count",
                color="tag",
                barmode="group",
                title="Excursion Count by Type"
            )
            fig.update_layout(height=300)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.success("No operating excursions detected")

    # Warranty Evidence Pack
    st.subheader("Warranty Evidence Pack Generator")

    col1, col2 = st.columns([1, 2])

    with col1:
        selected_site = st.selectbox(
            "Select Site for Evidence Pack",
            [s["name"] for s in sites]
        )

        evidence_type = st.multiselect(
            "Include Evidence",
            ["SLA Violations", "Operating Excursions", "Event Timeline", "Telemetry Export"],
            default=["SLA Violations", "Event Timeline"]
        )

        if st.button("Generate Evidence Pack"):
            st.success("Evidence pack generated! Download link below.")
            st.download_button(
                "Download Evidence Pack (CSV)",
                data="Event ID,Date,Type,Description\nMock,2024-03-10,Fault,Sample evidence",
                file_name=f"evidence_pack_{selected_site.replace(' ', '_')}.csv",
                mime="text/csv"
            )

    with col2:
        st.markdown("**Evidence Pack Contents:**")

        if "SLA Violations" in evidence_type:
            st.markdown("- SLA breach history and duration")
            st.markdown("- Availability metrics by period")

        if "Operating Excursions" in evidence_type:
            st.markdown("- Temperature excursion log")
            st.markdown("- Voltage/frequency anomalies")

        if "Event Timeline" in evidence_type:
            st.markdown("- Fault/trip event details")
            st.markdown("- Maintenance ticket correlation")

        if "Telemetry Export" in evidence_type:
            st.markdown("- Raw telemetry during events")
            st.markdown("- Control setpoint history")

    # Penalty calculation
    st.subheader("Penalty Exposure Analysis")

    if not sla_compliance.empty and sla_breaches > 0:
        penalty_detail = sla_compliance[sla_compliance["status"] == "BREACH"].copy()
        penalty_detail["daily_penalty"] = penalty_detail["penalty_rate_per_hour"] * 24
        penalty_detail["monthly_penalty"] = penalty_detail["daily_penalty"] * 30

        st.dataframe(
            penalty_detail[[
                "site_name", "metric_name", "threshold", "actual_value",
                "daily_penalty", "monthly_penalty"
            ]].rename(columns={
                "site_name": "Site",
                "metric_name": "Metric",
                "threshold": "Threshold",
                "actual_value": "Actual",
                "daily_penalty": "Daily Penalty (£)",
                "monthly_penalty": "Monthly Penalty (£)"
            }).style.format({
                "Threshold": "{:.1f}",
                "Actual": "{:.1f}",
                "Daily Penalty (£)": "£{:,.0f}",
                "Monthly Penalty (£)": "£{:,.0f}"
            }),
            use_container_width=True,
        )

        total_monthly = penalty_detail["monthly_penalty"].sum()
        st.error(f"Total Monthly Penalty Exposure: £{total_monthly:,.0f}")
    else:
        st.success("No active SLA breaches - no penalty exposure")


if __name__ == "__main__":
    main()
