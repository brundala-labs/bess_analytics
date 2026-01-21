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

    # Load catalog
    catalog = load_catalog()
    dashboards = catalog.get("dashboards", {})

    # Quick stats
    st.markdown("---")
    col1, col2, col3, col4 = st.columns(4)

    enka_count = sum(1 for d in dashboards.values() if d.get("pack") == "ENKA")
    tmeic_count = sum(1 for d in dashboards.values() if d.get("pack") == "TMEIC")
    combined_count = sum(1 for d in dashboards.values() if d.get("pack") == "Combined")

    with col1:
        st.metric("Total Dashboards", len(dashboards))
    with col2:
        st.metric("ENKA", enka_count)
    with col3:
        st.metric("TMEIC", tmeic_count)
    with col4:
        st.metric("Combined", combined_count)

    st.markdown("---")

    # Dashboard catalog
    st.subheader("Dashboards")

    # Organize by pack
    packs = {"ENKA": [], "TMEIC": [], "Combined": [], "Overview": []}
    for key, config in dashboards.items():
        pack = config.get("pack", "Other")
        if pack in packs:
            packs[pack].append((key, config))

    # Render each pack as expandable section
    for pack_name in ["ENKA", "TMEIC", "Combined"]:
        pack_dashboards = packs.get(pack_name, [])

        with st.expander(f"**{pack_name}** ({len(pack_dashboards)} dashboards)", expanded=False):
            if pack_name == "ENKA":
                st.caption("Asset Owner/Operator dashboards for portfolio management, revenue, and lifecycle planning.")
            elif pack_name == "TMEIC":
                st.caption("Controller/PCS dashboards for real-time operations, health monitoring, and grid compliance.")
            else:
                st.caption("Combined dashboards bridging asset performance with commercial outcomes.")

            for key, config in pack_dashboards:
                col1, col2 = st.columns([3, 1])
                with col1:
                    st.markdown(f"**{config.get('title', key)}**")
                    personas = config.get("personas", [])
                    if personas:
                        st.caption(f"For: {', '.join(personas[:3])}")
                with col2:
                    page_file = config.get("page_file", "")
                    st.caption(f"📄 {page_file.split('_', 1)[1].replace('.py', '').replace('_', ' ')}")
                st.markdown("---")

    # Overview section (Architecture & Proposal)
    overview_dashboards = packs.get("Overview", [])
    if overview_dashboards:
        st.markdown("---")
        st.subheader("Reference Documents")
        cols = st.columns(len(overview_dashboards))
        for idx, (key, config) in enumerate(overview_dashboards):
            with cols[idx]:
                st.markdown(f"**{config.get('title', key)}**")
                st.caption(config.get('decisions', [''])[0] if config.get('decisions') else '')

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
        """)

    with col2:
        st.markdown("**Data Architecture**")
        st.markdown("""
        - **Bronze Layer**: Raw JSONL micro-batches
        - **Silver Layer**: Cleaned Parquet tables
        - **Gold Layer**: Aggregate rollups
        """)

    # Footer
    render_footer()


if __name__ == "__main__":
    main()
