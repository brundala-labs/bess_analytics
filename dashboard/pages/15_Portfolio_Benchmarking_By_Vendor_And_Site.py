"""
Combined Portfolio Benchmarking by Vendor

Compare vendor performance across reliability, efficiency, and revenue metrics.
"""

import sys
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from dashboard.components.header import get_dashboard_config, render_header
from db.loader import get_connection

st.set_page_config(page_title="Vendor Benchmarking", page_icon="📊", layout="wide")

DASHBOARD_KEY = "combined_vendor_benchmarking"


@st.cache_data(ttl=300)
def load_vendor_data():
    """Load vendor comparison data."""
    conn = get_connection()

    # Site info with vendor
    sites = conn.execute("""
        SELECT
            site_id,
            name,
            bess_mw,
            bess_mwh,
            vendor_controller,
            cod_date
        FROM dim_site
    """).df()

    # Vendor performance summary
    vendor_summary = conn.execute("""
        SELECT
            s.vendor_controller as vendor,
            COUNT(DISTINCT s.site_id) as site_count,
            SUM(s.bess_mw) as total_mw,
            SUM(s.bess_mwh) as total_mwh
        FROM dim_site s
        GROUP BY s.vendor_controller
    """).df()

    # Availability by vendor
    availability_by_vendor = conn.execute("""
        SELECT
            s.vendor_controller as vendor,
            AVG(a.availability_pct) as avg_availability
        FROM dim_site s
        LEFT JOIN v_site_availability a ON s.site_id = a.site_id
        GROUP BY s.vendor_controller
    """).df()

    # SOH by vendor
    soh_by_vendor = conn.execute("""
        SELECT
            s.vendor_controller as vendor,
            AVG(bh.avg_soh) as avg_soh
        FROM dim_site s
        LEFT JOIN v_battery_health bh ON s.site_id = bh.site_id
        WHERE bh.date = (SELECT MAX(date) FROM v_battery_health)
        GROUP BY s.vendor_controller
    """).df()

    # Revenue by vendor
    revenue_by_vendor = conn.execute("""
        SELECT
            s.vendor_controller as vendor,
            SUM(fs.revenue_gbp) as total_revenue,
            SUM(fs.energy_mwh) as total_energy
        FROM dim_site s
        LEFT JOIN fact_settlement fs ON s.site_id = fs.site_id
        GROUP BY s.vendor_controller
    """).df()

    # Faults by vendor
    faults_by_vendor = conn.execute("""
        SELECT
            s.vendor_controller as vendor,
            COUNT(DISTINCT e.event_id) as fault_count,
            COUNT(DISTINCT CASE WHEN e.event_type = 'trip' THEN e.event_id END) as trip_count
        FROM dim_site s
        LEFT JOIN fact_events e ON s.site_id = e.site_id
        WHERE e.event_type IN ('fault', 'trip')
        GROUP BY s.vendor_controller
    """).df()

    # Efficiency by vendor
    efficiency_by_vendor = conn.execute("""
        SELECT
            s.vendor_controller as vendor,
            AVG(t.value) as avg_efficiency
        FROM dim_site s
        LEFT JOIN fact_telemetry t ON s.site_id = t.site_id
        WHERE t.tag = 'inverter_efficiency_pct'
        GROUP BY s.vendor_controller
    """).df()

    # Detailed site comparison
    site_metrics = conn.execute("""
        SELECT
            s.site_id,
            s.name,
            s.vendor_controller as vendor,
            s.bess_mw,
            AVG(a.availability_pct) as availability,
            AVG(bh.avg_soh) as soh,
            SUM(fs.revenue_gbp) as revenue,
            COUNT(DISTINCT e.event_id) as faults
        FROM dim_site s
        LEFT JOIN v_site_availability a ON s.site_id = a.site_id
        LEFT JOIN v_battery_health bh ON s.site_id = bh.site_id
        LEFT JOIN fact_settlement fs ON s.site_id = fs.site_id
        LEFT JOIN fact_events e ON s.site_id = e.site_id AND e.event_type IN ('fault', 'trip')
        GROUP BY s.site_id, s.name, s.vendor_controller, s.bess_mw
    """).df()

    conn.close()
    return (sites, vendor_summary, availability_by_vendor, soh_by_vendor,
            revenue_by_vendor, faults_by_vendor, efficiency_by_vendor, site_metrics)


def main():
    (sites, vendor_summary, availability, soh, revenue, faults,
     efficiency, site_metrics) = load_vendor_data()

    # Merge all vendor metrics
    vendor_metrics = vendor_summary.copy()
    vendor_metrics = vendor_metrics.merge(availability, on="vendor", how="left")
    vendor_metrics = vendor_metrics.merge(soh, on="vendor", how="left")
    vendor_metrics = vendor_metrics.merge(revenue, on="vendor", how="left")
    vendor_metrics = vendor_metrics.merge(faults, on="vendor", how="left")
    vendor_metrics = vendor_metrics.merge(efficiency, on="vendor", how="left")

    # Calculate derived metrics
    vendor_metrics["revenue_per_mw"] = vendor_metrics["total_revenue"] / vendor_metrics["total_mw"]
    vendor_metrics["faults_per_mw"] = vendor_metrics["fault_count"] / vendor_metrics["total_mw"]

    # Calculate KPIs
    vendor_count = len(vendor_metrics)

    best_availability = vendor_metrics.loc[vendor_metrics["avg_availability"].idxmax(), "vendor"] if not vendor_metrics.empty else "N/A"
    best_revenue = vendor_metrics.loc[vendor_metrics["revenue_per_mw"].idxmax(), "vendor"] if not vendor_metrics.empty else "N/A"
    lowest_faults = vendor_metrics.loc[vendor_metrics["faults_per_mw"].idxmin(), "vendor"] if not vendor_metrics.empty else "N/A"

    # Efficiency gap
    if not vendor_metrics.empty and len(vendor_metrics) > 1:
        eff_values = vendor_metrics["avg_efficiency"].dropna()
        efficiency_gap = eff_values.max() - eff_values.min() if len(eff_values) > 1 else 0
    else:
        efficiency_gap = 0

    # Recommendation based on overall score
    if not vendor_metrics.empty:
        vendor_metrics["score"] = (
            vendor_metrics["avg_availability"].fillna(0) * 0.3 +
            vendor_metrics["avg_soh"].fillna(0) * 0.2 +
            (100 - vendor_metrics["faults_per_mw"].fillna(0) * 10) * 0.3 +
            vendor_metrics["avg_efficiency"].fillna(0) * 0.2
        )
        recommended = vendor_metrics.loc[vendor_metrics["score"].idxmax(), "vendor"]
    else:
        recommended = "N/A"

    kpi_values = {
        "vendor_count": vendor_count,
        "best_vendor_availability": best_availability,
        "best_vendor_revenue_mw": best_revenue,
        "lowest_fault_rate_vendor": lowest_faults,
        "efficiency_gap_pct": efficiency_gap,
        "recommended_vendor": recommended,
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

    # Vendor comparison cards
    st.subheader("Vendor Overview")

    if not vendor_metrics.empty:
        cols = st.columns(len(vendor_metrics))

        for idx, (_, vendor) in enumerate(vendor_metrics.iterrows()):
            with cols[idx]:
                st.markdown(f"### {vendor['vendor']}")
                st.metric("Sites", int(vendor["site_count"]))
                st.metric("Total MW", f"{vendor['total_mw']:.0f}")
                st.metric("Availability", f"{vendor['avg_availability']:.1f}%" if pd.notna(vendor['avg_availability']) else "N/A")
                st.metric("Avg SOH", f"{vendor['avg_soh']:.1f}%" if pd.notna(vendor['avg_soh']) else "N/A")

    # Radar chart comparison
    st.subheader("Performance Comparison")

    col1, col2 = st.columns(2)

    with col1:
        if not vendor_metrics.empty:
            # Normalize metrics for radar chart
            radar_data = vendor_metrics.copy()
            radar_data["norm_availability"] = radar_data["avg_availability"] / 100
            radar_data["norm_soh"] = radar_data["avg_soh"] / 100
            radar_data["norm_efficiency"] = radar_data["avg_efficiency"] / 100
            radar_data["norm_reliability"] = 1 - (radar_data["faults_per_mw"] / radar_data["faults_per_mw"].max()).fillna(0)
            radar_data["norm_revenue"] = radar_data["revenue_per_mw"] / radar_data["revenue_per_mw"].max()

            categories = ["Availability", "SOH", "Efficiency", "Reliability", "Revenue/MW"]

            fig = go.Figure()

            for _, vendor in radar_data.iterrows():
                fig.add_trace(go.Scatterpolar(
                    r=[
                        vendor["norm_availability"],
                        vendor["norm_soh"],
                        vendor["norm_efficiency"],
                        vendor["norm_reliability"],
                        vendor["norm_revenue"]
                    ],
                    theta=categories,
                    fill="toself",
                    name=vendor["vendor"]
                ))

            fig.update_layout(
                polar=dict(radialaxis=dict(visible=True, range=[0, 1])),
                showlegend=True,
                height=400,
                title="Vendor Performance Radar"
            )
            st.plotly_chart(fig, use_container_width=True)

    with col2:
        if not vendor_metrics.empty:
            # Bar chart comparison
            metrics_to_compare = ["avg_availability", "avg_soh", "avg_efficiency"]
            metric_labels = ["Availability %", "SOH %", "Efficiency %"]

            comparison_df = vendor_metrics.melt(
                id_vars=["vendor"],
                value_vars=metrics_to_compare,
                var_name="metric",
                value_name="value"
            )
            comparison_df["metric"] = comparison_df["metric"].map(dict(zip(metrics_to_compare, metric_labels)))

            fig = px.bar(
                comparison_df,
                x="metric",
                y="value",
                color="vendor",
                barmode="group",
                title="Key Metrics by Vendor"
            )
            fig.update_layout(height=400)
            st.plotly_chart(fig, use_container_width=True)

    # Reliability comparison
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Fault Rate by Vendor")
        if not vendor_metrics.empty:
            fig = px.bar(
                vendor_metrics,
                x="vendor",
                y="faults_per_mw",
                color="vendor",
                title="Faults per MW of Capacity"
            )
            fig.update_layout(height=300)
            st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.subheader("Revenue Performance")
        if not vendor_metrics.empty:
            fig = px.bar(
                vendor_metrics,
                x="vendor",
                y="revenue_per_mw",
                color="vendor",
                title="Revenue per MW (£)"
            )
            fig.update_layout(height=300)
            st.plotly_chart(fig, use_container_width=True)

    # Site-level comparison
    st.subheader("Site-Level Benchmarking")

    if not site_metrics.empty:
        # Scatter plot
        fig = px.scatter(
            site_metrics,
            x="availability",
            y="revenue",
            size="bess_mw",
            color="vendor",
            hover_data=["name", "soh", "faults"],
            title="Site Performance: Availability vs Revenue"
        )
        fig.update_layout(height=400)
        st.plotly_chart(fig, use_container_width=True)

        # Detailed table
        st.dataframe(
            site_metrics[[
                "name", "vendor", "bess_mw", "availability", "soh", "revenue", "faults"
            ]].rename(columns={
                "name": "Site",
                "vendor": "Vendor",
                "bess_mw": "MW",
                "availability": "Availability %",
                "soh": "SOH %",
                "revenue": "Revenue (£)",
                "faults": "Faults"
            }).style.format({
                "Availability %": "{:.1f}",
                "SOH %": "{:.1f}",
                "Revenue (£)": "£{:,.0f}"
            }),
            use_container_width=True,
        )

    # Recommendations
    st.subheader("Vendor Recommendations")

    if not vendor_metrics.empty:
        best_vendor = vendor_metrics.loc[vendor_metrics["score"].idxmax()]

        col1, col2 = st.columns([1, 2])

        with col1:
            st.success(f"**Recommended Vendor: {best_vendor['vendor']}**")
            st.metric("Overall Score", f"{best_vendor['score']:.1f}")

        with col2:
            st.markdown("**Key Strengths:**")
            strengths = []

            if best_vendor["avg_availability"] == vendor_metrics["avg_availability"].max():
                strengths.append("Highest availability")
            if best_vendor["avg_soh"] == vendor_metrics["avg_soh"].max():
                strengths.append("Best battery health preservation")
            if best_vendor["faults_per_mw"] == vendor_metrics["faults_per_mw"].min():
                strengths.append("Lowest fault rate")
            if best_vendor["revenue_per_mw"] == vendor_metrics["revenue_per_mw"].max():
                strengths.append("Best revenue performance")

            for strength in strengths:
                st.markdown(f"- {strength}")

        # Detailed comparison table
        st.markdown("**Vendor Comparison Summary:**")

        summary = vendor_metrics[[
            "vendor", "site_count", "total_mw", "avg_availability",
            "avg_soh", "faults_per_mw", "revenue_per_mw", "score"
        ]].copy()

        def highlight_best(s):
            is_best = s == s.max() if s.name not in ["faults_per_mw"] else s == s.min()
            return ["background-color: #c8e6c9" if v else "" for v in is_best]

        st.dataframe(
            summary.rename(columns={
                "vendor": "Vendor",
                "site_count": "Sites",
                "total_mw": "Total MW",
                "avg_availability": "Availability %",
                "avg_soh": "SOH %",
                "faults_per_mw": "Faults/MW",
                "revenue_per_mw": "£/MW",
                "score": "Score"
            }).style.apply(highlight_best, subset=[
                "Availability %", "SOH %", "Faults/MW", "£/MW", "Score"
            ]).format({
                "Availability %": "{:.1f}",
                "SOH %": "{:.1f}",
                "Faults/MW": "{:.2f}",
                "£/MW": "£{:,.0f}",
                "Score": "{:.1f}"
            }),
            use_container_width=True,
        )


if __name__ == "__main__":
    main()
