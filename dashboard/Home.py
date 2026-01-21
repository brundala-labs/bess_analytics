"""
BESS Analytics - Home Page

Main entry point for the Streamlit dashboard application.
"""

import sys
from pathlib import Path

import streamlit as st

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from dashboard.components.header import load_catalog

# Page configuration
st.set_page_config(
    page_title="BESS Analytics",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        margin-bottom: 1rem;
    }
    .dashboard-card {
        background-color: #f0f2f6;
        border-radius: 10px;
        padding: 1rem;
        margin: 0.5rem 0;
    }
    .pack-header {
        font-size: 1.5rem;
        font-weight: bold;
        margin-top: 1.5rem;
        margin-bottom: 0.5rem;
    }
    .metric-highlight {
        font-size: 2rem;
        font-weight: bold;
        color: #2e7d32;
    }
</style>
""", unsafe_allow_html=True)


def main():
    # Header
    st.markdown('<p class="main-header">⚡ BESS Analytics Dashboard</p>', unsafe_allow_html=True)

    st.markdown("""
    Welcome to the Battery Energy Storage System (BESS) Analytics Platform.
    This demo showcases telemetry analytics dashboards for:

    - **ENKA** - Asset Owner/Operator Dashboards
    - **TMEIC** - Controller/PCS Dashboards
    - **Combined** - Revenue & SLA tied to Controller Performance
    """)

    # Load catalog
    catalog = load_catalog()
    dashboards = catalog.get("dashboards", {})

    # Quick stats
    st.markdown("---")
    col1, col2, col3, col4, col5 = st.columns(5)

    with col1:
        st.metric("Total Dashboards", len(dashboards))
    with col2:
        overview_count = sum(1 for d in dashboards.values() if d.get("pack") == "Overview")
        st.metric("Overview", overview_count)
    with col3:
        enka_count = sum(1 for d in dashboards.values() if d.get("pack") == "ENKA")
        st.metric("ENKA Dashboards", enka_count)
    with col4:
        tmeic_count = sum(1 for d in dashboards.values() if d.get("pack") == "TMEIC")
        st.metric("TMEIC Dashboards", tmeic_count)
    with col5:
        combined_count = sum(1 for d in dashboards.values() if d.get("pack") == "Combined")
        st.metric("Combined Dashboards", combined_count)

    st.markdown("---")

    # Dashboard catalog by pack
    st.subheader("Dashboard Catalog")

    # Organize by pack
    packs = {"Overview": [], "ENKA": [], "TMEIC": [], "Combined": []}
    for key, config in dashboards.items():
        pack = config.get("pack", "Other")
        if pack in packs:
            packs[pack].append((key, config))

    # Render each pack
    tabs = st.tabs(["Overview", "ENKA", "TMEIC", "Combined"])

    for tab, (pack_name, pack_dashboards) in zip(tabs, packs.items()):
        with tab:
            st.markdown(f"### {pack_name} Dashboard Pack")

            if pack_name == "Overview":
                st.info("System architecture, data flow documentation, and proposal executive summary.")
            elif pack_name == "ENKA":
                st.info("Asset Owner/Operator dashboards focused on portfolio management, revenue, and lifecycle planning.")
            elif pack_name == "TMEIC":
                st.info("Controller/PCS dashboards for real-time operations, health monitoring, and grid compliance.")
            else:
                st.info("Combined dashboards bridging asset performance with commercial outcomes.")

            for key, config in pack_dashboards:
                with st.expander(f"📊 {config.get('title', key)}", expanded=False):
                    col1, col2 = st.columns([2, 1])

                    with col1:
                        # Personas
                        st.markdown("**Personas:**")
                        personas = config.get("personas", [])
                        st.markdown(" | ".join([f"`{p}`" for p in personas]))

                        # Decisions
                        st.markdown("**Key Decisions:**")
                        for decision in config.get("decisions", [])[:3]:
                            st.markdown(f"- {decision}")

                    with col2:
                        # Data Sources
                        st.markdown("**Data Sources:**")
                        for source in config.get("data_sources", [])[:3]:
                            st.markdown(f"- {source.get('system', 'Unknown')}")

                        # Freshness
                        st.markdown("**Freshness:**")
                        st.caption(config.get("freshness", "Unknown"))

                    # KPIs preview
                    st.markdown("**KPIs:**")
                    kpi_labels = [k.get("label") for k in config.get("kpis", [])]
                    st.code(", ".join(kpi_labels), language=None)

                    # Navigation hint
                    route = config.get("route", "")
                    st.caption(f"Navigate to: pages/{route}")

    # System info
    st.markdown("---")
    st.subheader("System Information")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("**Upstream Systems (Mocked)**")
        systems = catalog.get("upstream_systems", {})
        for sys_key, sys_info in systems.items():
            st.markdown(f"- **{sys_info.get('name')}**: {sys_info.get('description')}")

    with col2:
        st.markdown("**Data Model**")
        st.markdown("""
        - **Dimensions**: dim_site, dim_asset, dim_service, dim_partner, dim_sla
        - **Facts**: fact_telemetry, fact_dispatch, fact_events, fact_settlement, fact_maintenance, fact_data_quality
        - **Forecast**: forecast_revenue
        - **Pipeline**: projects_pipeline
        """)

        st.markdown("**Technology Stack**")
        st.markdown("""
        - Database: DuckDB
        - API: FastAPI
        - Frontend: Streamlit
        - Charts: Plotly
        """)

    # Footer
    st.markdown("---")
    st.caption("BESS Analytics Demo | Use sidebar to navigate to specific dashboards")


if __name__ == "__main__":
    main()
