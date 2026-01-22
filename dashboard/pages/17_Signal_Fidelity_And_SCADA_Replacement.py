"""
Signal Fidelity And SCADA Replacement Dashboard

Displays corrected signals with trust scores, raw vs corrected SoC comparison,
SoE, SoP limits, and HSL/LSL safety bands.
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
    page_title="Signal Fidelity And SCADA Replacement",
    page_icon="📡",
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
def load_corrected_signals(site_id: str = None, hours: int = 24):
    """Load corrected signals data."""
    conn = get_connection()
    load_data(conn)

    query = """
        SELECT
            site_id, ts, soc_pct_raw, soc_pct_corrected, soe_mwh_corrected,
            sop_charge_kw, sop_discharge_kw, hsl_soc_pct, lsl_soc_pct,
            signal_trust_score, drift_detected, correction_applied
        FROM fact_corrected_signals
        WHERE ts >= (SELECT MAX(ts) FROM fact_corrected_signals) - INTERVAL '{}' HOUR
    """.format(hours)

    if site_id:
        query = query.replace("WHERE", f"WHERE site_id = '{site_id}' AND")

    query += " ORDER BY ts"
    df = conn.execute(query).df()
    conn.close()
    return df


@st.cache_data(ttl=300)
def load_latest_signals():
    """Load latest corrected signals per site."""
    conn = get_connection()
    load_data(conn)
    df = conn.execute("SELECT * FROM v_latest_corrected_signals").df()
    conn.close()
    return df


@st.cache_data(ttl=300)
def load_signal_health():
    """Load signal health summary."""
    conn = get_connection()
    load_data(conn)
    df = conn.execute("SELECT * FROM v_site_signal_health").df()
    conn.close()
    return df


def main():
    # Load data
    sites = load_sites()
    latest_signals = load_latest_signals()
    signal_health = load_signal_health()

    # Calculate KPIs
    if not latest_signals.empty:
        avg_trust_score = latest_signals["signal_trust_score"].mean()
        sites_with_drift = latest_signals["drift_detected"].sum()
        corrections_applied = latest_signals["correction_applied"].sum()
    else:
        avg_trust_score = 0
        sites_with_drift = 0
        corrections_applied = 0

    # Header
    render_header(
        title="Signal Fidelity And SCADA Replacement",
        personas=["ENKA Operations", "Asset Managers", "TMEIC Engineers"],
        decisions=[
            "Trust corrected signals over raw BMS data",
            "Identify sites with degraded signal quality",
            "Plan calibration and maintenance",
            "Validate SCADA replacement readiness",
        ],
        data_sources=[
            {"system": "Edge Intelligence", "tables": ["fact_corrected_signals"], "notes": "Real-time corrections"},
            {"system": "BMS", "tables": ["fact_telemetry"], "notes": "Raw signals"},
        ],
        freshness="Real-time (1-minute resolution)",
        kpis=[
            {"label": "Avg Trust Score", "value": avg_trust_score, "format": "number"},
            {"label": "Sites With Drift", "value": int(sites_with_drift), "format": "integer"},
            {"label": "Corrections Applied", "value": int(corrections_applied), "format": "integer"},
            {"label": "Sites Monitored", "value": len(sites), "format": "integer"},
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
    signals_df = load_corrected_signals(selected_site, hours_back)

    # Row 1: Trust Score Overview
    st.subheader("Signal Trust Score Overview")

    col1, col2 = st.columns(2)

    with col1:
        if not signal_health.empty:
            fig = px.bar(
                signal_health,
                x="site_id",
                y="avg_trust_score",
                color="avg_trust_score",
                color_continuous_scale="RdYlGn",
                range_color=[50, 100],
                title="Average Trust Score by Site",
            )
            fig.update_layout(height=300, xaxis_title="Site", yaxis_title="Trust Score")
            style_plotly_chart(fig)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No signal health data available.")

    with col2:
        if not signals_df.empty:
            # Trust score over time
            fig = px.line(
                signals_df,
                x="ts",
                y="signal_trust_score",
                color="site_id",
                title="Trust Score Trend",
            )
            fig.add_hline(y=70, line_dash="dash", line_color="orange", annotation_text="Warning Threshold")
            fig.update_layout(height=300)
            style_plotly_chart(fig)
            st.plotly_chart(fig, use_container_width=True)

    # Row 2: Raw vs Corrected SoC
    st.subheader("Raw vs Corrected State of Charge")

    if not signals_df.empty:
        # Create subplot with raw and corrected SoC
        fig = make_subplots(
            rows=2, cols=1,
            shared_xaxes=True,
            subplot_titles=("SoC Comparison", "Correction Delta"),
            vertical_spacing=0.12,
        )

        for site_id in signals_df["site_id"].unique():
            site_data = signals_df[signals_df["site_id"] == site_id]

            # Raw SoC
            fig.add_trace(
                go.Scatter(
                    x=site_data["ts"],
                    y=site_data["soc_pct_raw"],
                    name=f"{site_id} Raw",
                    line=dict(dash="dot"),
                    opacity=0.6,
                ),
                row=1, col=1,
            )

            # Corrected SoC
            fig.add_trace(
                go.Scatter(
                    x=site_data["ts"],
                    y=site_data["soc_pct_corrected"],
                    name=f"{site_id} Corrected",
                ),
                row=1, col=1,
            )

            # Delta
            delta = site_data["soc_pct_corrected"] - site_data["soc_pct_raw"]
            fig.add_trace(
                go.Scatter(
                    x=site_data["ts"],
                    y=delta,
                    name=f"{site_id} Delta",
                    fill="tozeroy",
                ),
                row=2, col=1,
            )

        fig.update_layout(height=500)
        fig.update_yaxes(title_text="SoC %", row=1, col=1)
        fig.update_yaxes(title_text="Delta %", row=2, col=1)
        style_plotly_chart(fig)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No corrected signals data available for the selected filters.")

    # Row 3: SoE and SoP
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("State of Energy (Usable)")
        if not signals_df.empty:
            fig = px.area(
                signals_df,
                x="ts",
                y="soe_mwh_corrected",
                color="site_id",
                title="Corrected SoE (MWh)",
            )
            fig.update_layout(height=300)
            style_plotly_chart(fig)
            st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.subheader("State of Power Limits")
        if not signals_df.empty:
            # Show latest SoP for each site
            latest = signals_df.groupby("site_id").last().reset_index()

            fig = go.Figure()
            fig.add_trace(go.Bar(
                name="Charge Limit",
                x=latest["site_id"],
                y=latest["sop_charge_kw"] / 1000,
                marker_color=ENKA_GREEN,
            ))
            fig.add_trace(go.Bar(
                name="Discharge Limit",
                x=latest["site_id"],
                y=latest["sop_discharge_kw"] / 1000,
                marker_color="#3498db",
            ))
            fig.update_layout(
                barmode="group",
                height=300,
                title="Current SoP Limits (MW)",
                yaxis_title="Power (MW)",
            )
            style_plotly_chart(fig)
            st.plotly_chart(fig, use_container_width=True)

    # Row 4: HSL/LSL Safety Bands
    st.subheader("Safety Operating Bands (HSL/LSL)")

    if not signals_df.empty and selected_site:
        site_data = signals_df[signals_df["site_id"] == selected_site]

        fig = go.Figure()

        # HSL band
        fig.add_trace(go.Scatter(
            x=site_data["ts"],
            y=site_data["hsl_soc_pct"],
            name="HSL (High Safety Limit)",
            line=dict(color="red", dash="dash"),
        ))

        # LSL band
        fig.add_trace(go.Scatter(
            x=site_data["ts"],
            y=site_data["lsl_soc_pct"],
            name="LSL (Low Safety Limit)",
            line=dict(color="red", dash="dash"),
            fill="tonexty",
            fillcolor="rgba(255,0,0,0.1)",
        ))

        # Corrected SoC
        fig.add_trace(go.Scatter(
            x=site_data["ts"],
            y=site_data["soc_pct_corrected"],
            name="Corrected SoC",
            line=dict(color=ENKA_GREEN, width=2),
        ))

        fig.update_layout(
            height=350,
            title=f"Operating Envelope - {selected_site}",
            yaxis_title="SoC %",
            yaxis_range=[0, 100],
        )
        style_plotly_chart(fig)
        st.plotly_chart(fig, use_container_width=True)
    elif not selected_site:
        st.info("Select a specific site to view HSL/LSL bands.")

    # Row 5: Signal Health Table
    st.subheader("Site Signal Health Summary")

    if not signal_health.empty:
        display_df = signal_health.copy()

        def highlight_trust(val):
            if val < 70:
                return "background-color: #ffcdd2"
            elif val < 85:
                return "background-color: #fff9c4"
            return ""

        st.dataframe(
            display_df.style.map(highlight_trust, subset=["avg_trust_score"]).format({
                "avg_trust_score": "{:.1f}",
                "avg_soc_error": "{:.2f}%",
            }),
            use_container_width=True,
            height=200,
        )

    # Documentation
    with st.expander("Signal Correction Methodology"):
        st.markdown("""
        ### Edge Intelligence Signal Correction

        The Signal Correction Engine provides enhanced signal fidelity by:

        **Trust Score (0-100):**
        - Measures confidence in corrected values
        - Factors: cell data availability, measurement consistency, drift magnitude
        - Below 70: Warning - review data quality
        - Below 50: Critical - manual verification needed

        **SoC Correction:**
        - Compares BMS SoC with cell-level voltage analysis
        - Applies weighted correction when drift exceeds threshold
        - Preserves BMS calibration for small deviations

        **HSL/LSL Safety Limits:**
        - HSL: High Safety Limit - maximum recommended SoC
        - LSL: Low Safety Limit - minimum recommended SoC
        - Dynamically adjusted based on temperature
        - Protects against over/under-charge damage

        **SoE (State of Energy):**
        - Usable energy in MWh within safety limits
        - Accounts for temperature derating
        - More accurate than nominal capacity * SoC

        **SoP (State of Power):**
        - Real-time charge/discharge limits
        - Accounts for SoC, temperature, and cell constraints
        - Used for dispatch optimization
        """)

    render_footer()


if __name__ == "__main__":
    main()
