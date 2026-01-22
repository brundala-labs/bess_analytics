"""
Predictive Energy And Power Availability Dashboard

Displays time-to-empty/full forecasts, predicted SoC at various horizons,
and confidence visualization.
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
    page_title="Predictive Energy And Power Availability",
    page_icon="🔮",
    layout="wide",
)

apply_enka_theme()
render_sidebar_branding()


@st.cache_data(ttl=300)
def load_sites():
    """Load site data."""
    conn = get_connection()
    load_data(conn)
    sites = conn.execute("SELECT site_id, name, bess_mwh FROM dim_site").df()
    conn.close()
    return sites.to_dict("records")


@st.cache_data(ttl=300)
def load_forecasts(site_id: str = None, hours: int = 24):
    """Load forecast data."""
    conn = get_connection()
    load_data(conn)

    query = """
        SELECT
            site_id, ts, horizon_min, predicted_soc_pct,
            time_to_empty_min, time_to_full_min, confidence_pct,
            available_energy_mwh
        FROM fact_forecasts
        WHERE ts >= (SELECT MAX(ts) FROM fact_forecasts) - INTERVAL '{}' HOUR
    """.format(hours)

    if site_id:
        query = query.replace("WHERE", f"WHERE site_id = '{site_id}' AND")

    query += " ORDER BY ts, horizon_min"
    df = conn.execute(query).df()
    conn.close()
    return df


@st.cache_data(ttl=300)
def load_forecast_summary():
    """Load latest forecast summary."""
    conn = get_connection()
    load_data(conn)
    df = conn.execute("SELECT * FROM v_forecast_summary").df()
    conn.close()
    return df


@st.cache_data(ttl=300)
def load_constraints(site_id: str = None):
    """Load active constraints."""
    conn = get_connection()
    load_data(conn)

    query = "SELECT * FROM v_active_constraints"
    if site_id:
        query += f" WHERE site_id = '{site_id}'"

    df = conn.execute(query).df()
    conn.close()
    return df


def main():
    # Load data
    sites = load_sites()
    forecast_summary = load_forecast_summary()

    # Calculate KPIs
    if not forecast_summary.empty:
        avg_time_to_empty = forecast_summary["time_to_empty_min"].mean()
        min_time_to_empty = forecast_summary["time_to_empty_min"].min()
        avg_confidence = forecast_summary["confidence_pct"].mean()
        total_available_energy = forecast_summary["available_energy_mwh"].sum()
    else:
        avg_time_to_empty = 0
        min_time_to_empty = 0
        avg_confidence = 0
        total_available_energy = 0

    # Header
    render_header(
        title="Predictive Energy And Power Availability",
        personas=["Trading Desk", "ENKA Operations", "Grid Services"],
        decisions=[
            "Optimize dispatch based on predicted availability",
            "Alert when time-to-empty approaches commitments",
            "Plan charge cycles proactively",
            "Manage grid service delivery risk",
        ],
        data_sources=[
            {"system": "Edge Intelligence", "tables": ["fact_forecasts"], "notes": "Multi-horizon predictions"},
            {"system": "Edge Intelligence", "tables": ["fact_constraints"], "notes": "Active constraints"},
        ],
        freshness="Real-time forecasts updated every 5 minutes",
        kpis=[
            {"label": "Avg Time to Empty", "value": avg_time_to_empty, "format": "number", "suffix": " min"},
            {"label": "Min Time to Empty", "value": min_time_to_empty, "format": "number", "suffix": " min"},
            {"label": "Forecast Confidence", "value": avg_confidence, "format": "percent"},
            {"label": "Available Energy", "value": total_available_energy, "format": "number", "suffix": " MWh"},
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
        hours_back = st.selectbox("Time Range", [6, 12, 24, 48], index=2, format_func=lambda x: f"Last {x} hours")

    colors = get_plotly_colors()

    # Load filtered data
    forecasts_df = load_forecasts(selected_site, hours_back)
    constraints_df = load_constraints(selected_site)

    # Row 1: Time-to-Empty/Full Gauges
    st.subheader("Current Energy Status")

    if not forecast_summary.empty:
        cols = st.columns(len(forecast_summary))
        for i, (_, row) in enumerate(forecast_summary.iterrows()):
            with cols[i]:
                st.markdown(f"**{row['site_id']}**")

                # Time to empty gauge
                tte = row["time_to_empty_min"] if pd.notna(row["time_to_empty_min"]) else 999
                color = "green" if tte > 120 else ("orange" if tte > 60 else "red")

                fig = go.Figure(go.Indicator(
                    mode="gauge+number",
                    value=min(tte, 240),
                    title={"text": "Time to Empty (min)"},
                    gauge={
                        "axis": {"range": [0, 240]},
                        "bar": {"color": color},
                        "steps": [
                            {"range": [0, 60], "color": "#ffcdd2"},
                            {"range": [60, 120], "color": "#fff9c4"},
                            {"range": [120, 240], "color": "#c8e6c9"},
                        ],
                    },
                ))
                fig.update_layout(height=200, margin=dict(t=50, b=0, l=20, r=20))
                st.plotly_chart(fig, use_container_width=True)

                st.metric("Available Energy", f"{row['available_energy_mwh']:.1f} MWh")
                st.metric("Confidence", f"{row['confidence_pct']:.0f}%")

    # Row 2: Predicted SoC at Horizons
    st.subheader("SoC Forecast by Horizon")

    if not forecasts_df.empty:
        # Get latest forecasts
        latest_ts = forecasts_df["ts"].max()
        latest_forecasts = forecasts_df[forecasts_df["ts"] == latest_ts]

        col1, col2 = st.columns(2)

        with col1:
            # Bar chart of predicted SoC by horizon
            fig = px.bar(
                latest_forecasts,
                x="horizon_min",
                y="predicted_soc_pct",
                color="site_id",
                barmode="group",
                title="Predicted SoC by Horizon",
            )
            fig.update_layout(height=350, xaxis_title="Horizon (minutes)", yaxis_title="Predicted SoC %")
            style_plotly_chart(fig)
            st.plotly_chart(fig, use_container_width=True)

        with col2:
            # Confidence by horizon
            fig = px.line(
                latest_forecasts,
                x="horizon_min",
                y="confidence_pct",
                color="site_id",
                markers=True,
                title="Forecast Confidence by Horizon",
            )
            fig.update_layout(height=350, xaxis_title="Horizon (minutes)", yaxis_title="Confidence %")
            style_plotly_chart(fig)
            st.plotly_chart(fig, use_container_width=True)

    # Row 3: Time Series Forecasts
    st.subheader("Forecast Trends Over Time")

    if not forecasts_df.empty and selected_site:
        site_forecasts = forecasts_df[forecasts_df["site_id"] == selected_site]

        # Create subplot for different horizons
        horizons = site_forecasts["horizon_min"].unique()

        fig = make_subplots(
            rows=2, cols=1,
            shared_xaxes=True,
            subplot_titles=("Predicted SoC by Horizon", "Available Energy"),
            vertical_spacing=0.12,
        )

        for horizon in sorted(horizons):
            horizon_data = site_forecasts[site_forecasts["horizon_min"] == horizon]

            fig.add_trace(
                go.Scatter(
                    x=horizon_data["ts"],
                    y=horizon_data["predicted_soc_pct"],
                    name=f"{horizon}min",
                    mode="lines",
                ),
                row=1, col=1,
            )

        # Available energy (use shortest horizon)
        shortest_horizon = site_forecasts[site_forecasts["horizon_min"] == min(horizons)]
        fig.add_trace(
            go.Scatter(
                x=shortest_horizon["ts"],
                y=shortest_horizon["available_energy_mwh"],
                name="Available Energy",
                fill="tozeroy",
                line=dict(color=ENKA_GREEN),
            ),
            row=2, col=1,
        )

        fig.update_layout(height=500)
        fig.update_yaxes(title_text="SoC %", row=1, col=1)
        fig.update_yaxes(title_text="Energy (MWh)", row=2, col=1)
        style_plotly_chart(fig)
        st.plotly_chart(fig, use_container_width=True)
    elif not selected_site:
        st.info("Select a specific site to view detailed forecast trends.")

    # Row 4: Active Constraints
    st.subheader("Active Power/Energy Constraints")

    if not constraints_df.empty:
        # Constraint summary
        col1, col2 = st.columns(2)

        with col1:
            constraint_counts = constraints_df.groupby("constraint_type").size().reset_index(name="count")
            fig = px.pie(
                constraint_counts,
                values="count",
                names="constraint_type",
                title="Constraints by Type",
            )
            fig.update_layout(height=300)
            style_plotly_chart(fig)
            st.plotly_chart(fig, use_container_width=True)

        with col2:
            severity_counts = constraints_df.groupby("severity").size().reset_index(name="count")
            fig = px.bar(
                severity_counts,
                x="severity",
                y="count",
                color="severity",
                color_discrete_map={
                    "critical": "#d32f2f",
                    "high": "#f57c00",
                    "medium": "#fbc02d",
                    "low": "#4caf50",
                },
                title="Constraints by Severity",
            )
            fig.update_layout(height=300, showlegend=False)
            style_plotly_chart(fig)
            st.plotly_chart(fig, use_container_width=True)

        # Constraints table
        st.dataframe(
            constraints_df[[
                "site_id", "constraint_type", "reason", "limit_value", "severity", "duration_min"
            ]].rename(columns={
                "site_id": "Site",
                "constraint_type": "Type",
                "reason": "Reason",
                "limit_value": "Limit",
                "severity": "Severity",
                "duration_min": "Duration (min)",
            }),
            use_container_width=True,
            height=200,
        )
    else:
        st.success("No active constraints at this time.")

    # Row 5: Forecast Summary Table
    st.subheader("Site Forecast Summary")

    if not forecast_summary.empty:
        display_df = forecast_summary.copy()

        def highlight_tte(val):
            if pd.isna(val):
                return ""
            if val < 60:
                return "background-color: #ffcdd2"
            elif val < 120:
                return "background-color: #fff9c4"
            return ""

        st.dataframe(
            display_df.style.map(highlight_tte, subset=["time_to_empty_min"]).format({
                "time_to_empty_min": "{:.0f}",
                "time_to_full_min": "{:.0f}",
                "predicted_soc_pct": "{:.1f}%",
                "confidence_pct": "{:.0f}%",
                "available_energy_mwh": "{:.2f}",
            }),
            use_container_width=True,
        )

    # Documentation
    with st.expander("Forecasting Methodology"):
        st.markdown("""
        ### Edge Intelligence Forecasting

        The Forecasting Engine provides predictive energy and power availability:

        **Time-to-Empty:**
        - Estimates minutes until battery reaches minimum operational SoC
        - Based on current discharge rate and available energy
        - Critical for service delivery planning

        **Time-to-Full:**
        - Estimates minutes until battery reaches maximum operational SoC
        - Based on current charge rate and remaining capacity
        - Useful for charge scheduling

        **Multi-Horizon Forecasts:**
        - 15 minutes: High confidence, short-term decisions
        - 30 minutes: Grid service commitment window
        - 60 minutes: Dispatch optimization
        - 120 minutes: Trading decisions
        - 240 minutes: Strategic planning

        **Confidence Score:**
        - Decreases with longer horizons
        - Lower at high power (more uncertainty)
        - Factors: load variability, temperature effects

        **Active Constraints:**
        - Thermal: Temperature-based power limits
        - SoC: Near-empty or near-full derating
        - Grid: External grid constraints
        - Cell: Cell-level limitations
        """)

    render_footer()


if __name__ == "__main__":
    main()
