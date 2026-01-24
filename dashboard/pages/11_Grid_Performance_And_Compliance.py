"""
TMEIC Grid Code Performance

Grid compliance monitoring, ramp rate validation, and frequency response.
"""

import sys
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
import numpy as np

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from dashboard.components.branding import apply_enka_theme, render_sidebar_branding, render_footer, style_plotly_chart
from dashboard.components.header import get_dashboard_config, render_header, render_filter_bar
from db.loader import get_connection

st.set_page_config(initial_sidebar_state="expanded", page_title="Grid Code Performance", page_icon="📈", layout="wide")

# Apply ENKA branding
apply_enka_theme()
render_sidebar_branding("11_Grid_Performance_And_Compliance")


DASHBOARD_KEY = "tmeic_grid_code"


@st.cache_data(ttl=300)
def load_grid_data():
    """Load grid code related telemetry."""
    conn = get_connection()

    # Power data with ramp calculation
    power_data = conn.execute("""
        SELECT
            t.ts,
            t.site_id,
            s.name as site_name,
            t.value as power_kw
        FROM fact_telemetry t
        JOIN dim_site s ON t.site_id = s.site_id
        WHERE t.tag = 'p_kw'
        ORDER BY t.site_id, t.ts
    """).df()

    # Voltage data
    voltage_data = conn.execute("""
        SELECT
            t.ts,
            t.site_id,
            s.name as site_name,
            t.value as voltage_pu
        FROM fact_telemetry t
        JOIN dim_site s ON t.site_id = s.site_id
        WHERE t.tag = 'v_pu'
        ORDER BY t.ts
    """).df()

    # Frequency data
    frequency_data = conn.execute("""
        SELECT
            t.ts,
            t.site_id,
            s.name as site_name,
            t.value as frequency_hz
        FROM fact_telemetry t
        JOIN dim_site s ON t.site_id = s.site_id
        WHERE t.tag = 'f_hz'
        ORDER BY t.ts
    """).df()

    # Reactive power
    reactive_data = conn.execute("""
        SELECT
            t.ts,
            t.site_id,
            s.name as site_name,
            t.value as q_kvar
        FROM fact_telemetry t
        JOIN dim_site s ON t.site_id = s.site_id
        WHERE t.tag = 'q_kvar'
        ORDER BY t.ts
    """).df()

    # Dispatch compliance
    dispatch = conn.execute("""
        SELECT
            site_id,
            date,
            dispatch_count,
            compliance_pct,
            total_deviation_mw
        FROM v_dispatch_compliance
        ORDER BY date
    """).df()

    sites = conn.execute("SELECT site_id, name, bess_mw FROM dim_site").df()

    conn.close()
    return power_data, voltage_data, frequency_data, reactive_data, dispatch, sites


def calculate_ramp_rates(power_df: pd.DataFrame) -> pd.DataFrame:
    """Calculate ramp rates from power data."""
    result = []

    for site_id in power_df["site_id"].unique():
        site_power = power_df[power_df["site_id"] == site_id].sort_values("ts")
        if len(site_power) < 2:
            continue

        site_power = site_power.copy()
        site_power["prev_power"] = site_power["power_kw"].shift(1)
        site_power["ramp_kw_per_min"] = abs(site_power["power_kw"] - site_power["prev_power"])
        site_power = site_power.dropna()

        result.append(site_power)

    return pd.concat(result, ignore_index=True) if result else pd.DataFrame()


def main():
    power_data, voltage_data, frequency_data, reactive_data, dispatch, sites_df = load_grid_data()
    sites = sites_df.to_dict(orient="records")

    # Calculate ramp rates
    ramp_data = calculate_ramp_rates(power_data)

    # Calculate KPIs
    # Ramp compliance (assuming 10MW/min limit for 50MW site = 20%/min)
    if not ramp_data.empty:
        ramp_data_merged = ramp_data.merge(sites_df[["site_id", "bess_mw"]], on="site_id")
        ramp_data_merged["ramp_pct_per_min"] = ramp_data_merged["ramp_kw_per_min"] / (ramp_data_merged["bess_mw"] * 1000) * 100
        ramp_violations = (ramp_data_merged["ramp_pct_per_min"] > 20).sum()
        total_ramps = len(ramp_data_merged)
        ramp_compliance = ((total_ramps - ramp_violations) / total_ramps) * 100 if total_ramps > 0 else 100
    else:
        ramp_compliance = 100

    # Frequency response (simulated - time to reach setpoint)
    avg_freq_response = 0.8  # seconds (mock)

    # Voltage excursions
    if not voltage_data.empty:
        voltage_excursions = ((voltage_data["voltage_pu"] < 0.95) | (voltage_data["voltage_pu"] > 1.05)).sum()
    else:
        voltage_excursions = 0

    # Power factor
    if not power_data.empty and not reactive_data.empty:
        merged = power_data.merge(reactive_data[["ts", "site_id", "q_kvar"]], on=["ts", "site_id"], how="inner")
        merged["apparent_power"] = np.sqrt(merged["power_kw"]**2 + merged["q_kvar"]**2)
        merged["power_factor"] = merged["power_kw"] / merged["apparent_power"].replace(0, np.nan)
        avg_pf = merged["power_factor"].mean()
    else:
        avg_pf = 1.0

    # Grid code score (weighted average)
    grid_code_score = (ramp_compliance * 0.4 + (100 - min(voltage_excursions, 100)) * 0.3 +
                       dispatch["compliance_pct"].mean() * 0.3) if not dispatch.empty else ramp_compliance

    # Non-compliance events
    non_compliance = int(ramp_violations if not ramp_data.empty else 0) + int(voltage_excursions)

    # Dispatch adherence from view
    dispatch_adherence = dispatch["compliance_pct"].mean() if not dispatch.empty else 100

    # Frequency response score (0-100)
    freq_response_score = min(100, (1 / max(avg_freq_response, 0.1)) * 100)

    # Voltage compliance (percentage within limits)
    if not voltage_data.empty:
        voltage_in_range = ((voltage_data["voltage_pu"] >= 0.95) & (voltage_data["voltage_pu"] <= 1.05)).sum()
        voltage_compliance = (voltage_in_range / len(voltage_data)) * 100
    else:
        voltage_compliance = 100

    kpi_values = {
        "dispatch_adherence_pct": dispatch_adherence,
        "frequency_response_score": freq_response_score,
        "voltage_compliance_pct": voltage_compliance,
        "ramp_rate_compliance_pct": ramp_compliance,
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
    filtered_power = power_data.copy()
    filtered_voltage = voltage_data.copy()
    filtered_frequency = frequency_data.copy()

    if filters.get("site_id"):
        filtered_power = filtered_power[filtered_power["site_id"] == filters["site_id"]]
        filtered_voltage = filtered_voltage[filtered_voltage["site_id"] == filters["site_id"]]
        filtered_frequency = filtered_frequency[filtered_frequency["site_id"] == filters["site_id"]]

    # Power and ramp rate
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Power Output Profile")
        if not filtered_power.empty:
            # Sample for performance
            sampled = filtered_power.groupby([
                pd.Grouper(key="ts", freq="15min"),
                "site_name"
            ])["power_kw"].mean().reset_index()

            fig = px.line(
                sampled,
                x="ts",
                y="power_kw",
                color="site_name",
                title="Power (kW) - 15min Resolution"
            )
            fig.add_hline(y=0, line_dash="dash", line_color="gray")
            fig.update_layout(height=300)
            st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.subheader("Ramp Rate Distribution")
        if not ramp_data.empty:
            fig = px.histogram(
                ramp_data[ramp_data["site_id"].isin(filtered_power["site_id"].unique())] if filters.get("site_id") else ramp_data,
                x="ramp_kw_per_min",
                nbins=50,
                title="Ramp Rate Distribution (kW/min)"
            )
            fig.add_vline(x=10000, line_dash="dash", line_color="red", annotation_text="Limit")
            fig.update_layout(height=300)
            st.plotly_chart(fig, use_container_width=True)

    # Voltage and frequency
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Voltage Profile")
        if not filtered_voltage.empty:
            sampled = filtered_voltage.groupby([
                pd.Grouper(key="ts", freq="15min"),
                "site_name"
            ])["voltage_pu"].mean().reset_index()

            fig = px.line(
                sampled,
                x="ts",
                y="voltage_pu",
                color="site_name",
                title="Voltage (p.u.)"
            )
            fig.add_hline(y=0.95, line_dash="dash", line_color="red", annotation_text="Low Limit")
            fig.add_hline(y=1.05, line_dash="dash", line_color="red", annotation_text="High Limit")
            fig.add_hline(y=1.0, line_dash="dash", line_color="green")
            fig.update_layout(height=280)
            st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.subheader("Frequency Profile")
        if not filtered_frequency.empty:
            sampled = filtered_frequency.groupby([
                pd.Grouper(key="ts", freq="15min"),
                "site_name"
            ])["frequency_hz"].mean().reset_index()

            fig = px.line(
                sampled,
                x="ts",
                y="frequency_hz",
                color="site_name",
                title="Grid Frequency (Hz)"
            )
            fig.add_hline(y=49.8, line_dash="dash", line_color="orange", annotation_text="FFR Trigger")
            fig.add_hline(y=50.0, line_dash="dash", line_color="green")
            fig.add_hline(y=50.2, line_dash="dash", line_color="orange")
            fig.update_layout(height=280)
            st.plotly_chart(fig, use_container_width=True)

    # Dispatch compliance
    st.subheader("Dispatch Compliance Trend")

    if not dispatch.empty:
        fig = px.line(
            dispatch.groupby("date")["compliance_pct"].mean().reset_index(),
            x="date",
            y="compliance_pct",
            title="Average Dispatch Compliance %"
        )
        fig.add_hline(y=95, line_dash="dash", line_color="red", annotation_text="Target 95%")
        fig.update_layout(height=280)
        st.plotly_chart(fig, use_container_width=True)

    # Compliance summary table
    st.subheader("Site Compliance Summary")

    if not dispatch.empty:
        summary = dispatch.groupby("site_id").agg({
            "compliance_pct": "mean",
            "total_deviation_mw": "sum",
            "dispatch_count": "sum"
        }).reset_index()

        summary = summary.merge(sites_df[["site_id", "name"]], on="site_id")

        summary["status"] = summary["compliance_pct"].apply(
            lambda x: "🟢 Compliant" if x >= 95 else ("🟡 Marginal" if x >= 90 else "🔴 Non-Compliant")
        )

        st.dataframe(
            summary[[
                "name", "compliance_pct", "total_deviation_mw", "dispatch_count", "status"
            ]].rename(columns={
                "name": "Site",
                "compliance_pct": "Compliance %",
                "total_deviation_mw": "Total Deviation (MW)",
                "dispatch_count": "Dispatch Count",
                "status": "Status"
            }).style.format({
                "Compliance %": "{:.1f}%",
                "Total Deviation (MW)": "{:.1f}",
            }),
            use_container_width=True,
        )


if __name__ == "__main__":
    main()
