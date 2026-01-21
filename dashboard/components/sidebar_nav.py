"""
Custom Sidebar Navigation with Expandable Sections

Provides collapsible dashboard categories in the sidebar.
"""

import streamlit as st


def render_sidebar_nav():
    """Render custom sidebar navigation with expandable sections."""

    # Dashboard structure
    dashboards = {
        "ENKA": [
            ("Portfolio Executive Cockpit", "03_Portfolio_Executive_Cockpit"),
            ("Partner Monetization And Revenue Share", "04_Partner_Monetization_And_Revenue_Share"),
            ("RTM Settlement Reconciliation", "05_RTM_Settlement_Reconciliation"),
            ("Lifecycle And Augmentation Planning", "06_Lifecycle_And_Augmentation_Planning"),
            ("Development Pipeline Tracking", "07_Development_Pipeline_Tracking"),
        ],
        "TMEIC": [
            ("PCS Controller Real Time Operations", "08_PCS_Controller_Real_Time_Operations"),
            ("Controller Health And Communications", "09_Controller_Health_And_Communications"),
            ("Faults And Trips Timeline", "10_Faults_And_Trips_Timeline"),
            ("Grid Performance And Compliance", "11_Grid_Performance_And_Compliance"),
            ("Historian Explorer", "12_Historian_Explorer"),
        ],
        "Combined": [
            ("Revenue Loss Attribution", "13_Revenue_Loss_Attribution"),
            ("Dispatch Versus Asset Stress", "14_Dispatch_Versus_Asset_Stress"),
            ("SLA And Warranty Evidence Pack", "15_SLA_And_Warranty_Evidence_Pack"),
            ("Portfolio Benchmarking By Vendor And Site", "16_Portfolio_Benchmarking_By_Vendor_And_Site"),
        ],
    }

    reference_docs = [
        ("Architecture And Data Flow", "01_Architecture_And_Data_Flow"),
        ("Proposal Executive Summary", "02_Proposal_Executive_Summary"),
    ]

    st.sidebar.markdown("## Dashboards")

    # Render each category as expander
    for category, pages in dashboards.items():
        with st.sidebar.expander(f"**{category}** ({len(pages)})", expanded=False):
            for title, page_key in pages:
                # Create a link-like button
                if st.button(f"📊 {title}", key=f"nav_{page_key}", use_container_width=True):
                    st.switch_page(f"pages/{page_key}.py")

    # Reference documents section
    st.sidebar.markdown("---")
    st.sidebar.markdown("## Reference")
    for title, page_key in reference_docs:
        if st.sidebar.button(f"📄 {title}", key=f"nav_{page_key}", use_container_width=True):
            st.switch_page(f"pages/{page_key}.py")


def hide_default_nav():
    """Hide the default Streamlit multipage navigation."""
    st.markdown("""
    <style>
        [data-testid="stSidebarNav"] {
            display: none;
        }
    </style>
    """, unsafe_allow_html=True)
