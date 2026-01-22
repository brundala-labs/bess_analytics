"""
Architecture And Data Flow

Cloud architecture, Medallion data pipeline, and canonical data model documentation.
"""

import sys
from pathlib import Path


import streamlit as st

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from dashboard.components.branding import apply_enka_theme, render_sidebar_branding, render_footer, style_plotly_chart
from dashboard.components.header import get_dashboard_config, render_header
from dashboard.components.kpi_glossary import render_kpi_glossary

st.set_page_config(page_title="Architecture And Data Flow", page_icon="🏗️", layout="wide")

# Apply ENKA branding
apply_enka_theme()
render_sidebar_branding()


DASHBOARD_KEY = "architecture_data_flow"


def get_architecture_diagram() -> str:
    """Generate cloud architecture description."""
    return ""


def get_medallion_diagram() -> str:
    """Generate Medallion Architecture description."""
    return ""


def get_data_model_diagram() -> str:
    """Generate canonical data model description."""
    return ""


def main():
    # Header metadata
    config = {
        "title": "Architecture And Data Flow",
        "personas": ["CEO", "CTO", "Head Of Operations", "Engineering Lead"],
        "decisions": [
            "Approve architecture design",
            "Confirm project scope",
            "Align stakeholders on data sources",
            "Validate integration approach"
        ],
        "data_sources": [
            {"system": "Architecture Documentation", "tables": ["N/A"], "notes": "Static reference page"},
        ],
        "freshness": "Static (reference documentation)",
    }

    kpi_values = {}

    render_header(
        title=config.get("title"),
        personas=config.get("personas", []),
        decisions=config.get("decisions", []),
        data_sources=config.get("data_sources", []),
        freshness=config.get("freshness", ""),
        kpis=[],
    )

    st.divider()

    # Section 1: Cloud Architecture
    st.header("☁️ Cloud Streaming Architecture")
    st.markdown("""
    The BESS Analytics platform uses a cloud-native streaming architecture built on Databricks
    with Delta Lake for reliable, scalable data processing.

    **Key Components:**
    - **Streaming Bus**: Kafka / Event Hubs / Kinesis / Pub/Sub for real-time telemetry ingestion
    - **Data Lake**: Cloud object storage (S3/ADLS/GCS) organized in Medallion layers
    - **Compute**: Databricks Structured Streaming for continuous data processing
    - **Governance**: Unity Catalog for data cataloging and access control
    - **Serving**: FastAPI metrics service + Streamlit dashboards
    """)

    st.divider()

    # Section 2: Medallion Architecture
    st.header("🏅 Medallion Architecture")
    st.markdown("""
    Data flows through three progressively refined layers:

    | Layer | Purpose | Characteristics |
    |-------|---------|-----------------|
    | **Bronze** | Raw ingestion | As-received, append-only, minimal parsing |
    | **Silver** | Cleaned & conformed | Canonical schema, deduplicated, validated |
    | **Gold** | Analytics-ready | KPI tables, rollups, dashboard views |
    """)

    # Bronze/Silver/Gold table mapping
    with st.expander("📋 Table Mapping Details"):
        col1, col2, col3 = st.columns(3)

        with col1:
            st.markdown("**Bronze (Raw)**")
            st.markdown("""
- telemetry/ (JSONL per site/hour)
- events/ (JSONL daily)
- settlement/ (CSV monthly)
            """)

        with col2:
            st.markdown("**Silver (Cleaned)**")
            st.markdown("""
- fact_telemetry
- fact_dispatch
- fact_events
- fact_settlement
- fact_maintenance
- fact_data_quality
- dim_site, dim_asset
- dim_service, dim_partner, dim_sla
            """)

        with col3:
            st.markdown("**Gold (Curated)**")
            st.markdown("""
- agg_telemetry_15min
- agg_site_daily
- agg_site_monthly
- agg_events_daily
- agg_revenue_daily
            """)

    st.divider()

    # Section 3: Canonical Data Model
    st.header("📊 Canonical Data Model")
    st.markdown("""
    The canonical BESS data model follows a star schema design with:
    - **Dimensions**: Site, Asset, Service, Partner, SLA
    - **Facts**: Telemetry, Dispatch, Events, Settlement, Maintenance
    - **Derived KPIs**: Availability, RTE, DoD, Lost Revenue, etc.
    """)

    st.divider()

    # Section 4: Data Sources
    st.header("📡 Upstream Data Sources")

    sources = [
        {
            "name": "TMEIC Controller (PCS/Plant Control)",
            "type": "Streaming",
            "frequency": "1-minute",
            "tags": ["p_kw", "q_kvar", "v_pu", "f_hz", "controller_status", "inverter_efficiency_pct"],
        },
        {
            "name": "BMS (Battery Management System)",
            "type": "Streaming",
            "frequency": "1-minute",
            "tags": ["soc_pct", "soh_pct", "temp_c_avg", "temp_c_max", "voltage_v", "current_a", "cycle_count"],
        },
        {
            "name": "ENKA EMS/SCADA",
            "type": "Streaming",
            "frequency": "1-minute",
            "tags": ["command_kw", "setpoint_kw", "dispatch_mode"],
        },
        {
            "name": "RTM / Market Settlement Provider",
            "type": "Batch",
            "frequency": "Daily",
            "tags": ["revenue_gbp", "energy_mwh", "avg_price_gbp_per_mwh"],
        },
        {
            "name": "ENKA CMMS",
            "type": "Batch",
            "frequency": "On-event",
            "tags": ["ticket_id", "issue_category", "resolution", "cost_gbp"],
        },
        {
            "name": "Contracts And Finance",
            "type": "Batch",
            "frequency": "On-change",
            "tags": ["partner_id", "revenue_share_pct", "sla_threshold", "penalty_rate"],
        },
    ]

    cols = st.columns(3)
    for idx, source in enumerate(sources):
        with cols[idx % 3]:
            with st.container(border=True):
                st.markdown(f"**{source['name']}**")
                st.caption(f"Type: {source['type']} | Frequency: {source['frequency']}")
                st.markdown(f"Tags: `{', '.join(source['tags'][:4])}`{'...' if len(source['tags']) > 4 else ''}")

    st.divider()

    # Section 5: KPI Glossary (subset for architecture page)
    render_kpi_glossary(
        kpi_keys=["soc_pct", "soh_pct", "availability_pct", "rte_pct", "lost_revenue_gbp"],
        title="Key KPI Definitions",
        expanded=False
    )


if __name__ == "__main__":
    main()
