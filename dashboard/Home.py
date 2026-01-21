"""
BESS Analytics - Home Page

Main entry point for the Streamlit dashboard application.
ENKA Energy Transition branded.
"""

import sys
from pathlib import Path

import streamlit as st

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from dashboard.components.header import load_catalog
from dashboard.components.branding import (
    apply_enka_theme,
    render_sidebar_branding,
    render_footer,
    ENKA_GREEN,
    ENKA_DARK,
)

# Page configuration
st.set_page_config(
    page_title="ENKA BESS Analytics",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Apply ENKA branding
apply_enka_theme()
render_sidebar_branding()


def main():
    # Header with ENKA branding
    st.markdown(
        f'<h1 style="color: {ENKA_DARK};">⚡ ENKA BESS Analytics</h1>',
        unsafe_allow_html=True
    )

    st.markdown(f"""
    <p style="font-size: 1.1rem; color: {ENKA_DARK};">
    Welcome to the <span style="color: {ENKA_GREEN}; font-weight: bold;">ENKA Energy Transition</span>
    Battery Energy Storage System (BESS) Analytics Platform.
    </p>
    """, unsafe_allow_html=True)

    st.markdown("""
    This platform provides telemetry analytics dashboards for:

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
                    if kpi_labels:
                        st.code(", ".join(kpi_labels), language=None)
                    else:
                        st.caption("Reference page - no live KPIs")

                    # Navigation hint
                    page_file = config.get("page_file", "")
                    st.caption(f"Navigate to: {page_file}")

    # System info
    st.markdown("---")
    st.subheader("System Information")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("**Data Sources**")
        st.markdown("""
        - **TMEIC Controller** - PCS/Plant Control telemetry
        - **BMS** - Battery Management System data
        - **ENKA EMS/SCADA** - Events and dispatch
        - **RTM Settlement** - Market settlement data
        - **ENKA CMMS** - Maintenance records
        - **Contracts & Finance** - Partner and SLA data
        """)

    with col2:
        st.markdown("**Data Architecture**")
        st.markdown("""
        - **Bronze Layer**: Raw JSONL micro-batches
        - **Silver Layer**: Cleaned Parquet tables
        - **Gold Layer**: Aggregate rollups
        """)

        st.markdown("**Technology Stack**")
        st.markdown("""
        - Database: DuckDB
        - Dashboard: Streamlit + Plotly
        - API: FastAPI
        """)

    # Footer
    render_footer()


if __name__ == "__main__":
    main()
