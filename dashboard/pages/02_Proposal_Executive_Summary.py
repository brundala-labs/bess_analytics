"""
Proposal Executive Summary

One-page proposal for BESS Analytics platform with objectives, scope, and roadmap.
"""

import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from dashboard.components.branding import apply_enka_theme, render_sidebar_branding, render_footer

st.set_page_config(page_title="Proposal Executive Summary", page_icon="📋", layout="wide")

apply_enka_theme()
render_sidebar_branding()


def main():
    st.title("📋 Proposal Executive Summary")
    st.caption("BESS Analytics Platform - Objectives, scope, and roadmap")

    # Problem Statement
    st.header("🎯 Problem Statement")
    st.markdown("""
    ENKA operates a growing fleet of Battery Energy Storage Systems (BESS) across multiple sites
    with different controller vendors. Current challenges include:
    - **Fragmented visibility** across TMEIC controllers, BMS systems, and EMS/SCADA
    - **Revenue leakage** due to unattributed dispatch failures and data gaps
    - **Reactive maintenance** leading to extended downtime and warranty disputes
    - **Manual reconciliation** of settlement data with operational performance
    - **Limited insight** into partner revenue sharing and SLA compliance
    """)

    # Objectives
    st.header("🎯 Objectives")
    col1, col2 = st.columns(2)
    with col1:
        with st.container(border=True):
            st.markdown("**⬆️ Availability Maximization**")
            st.markdown("Achieve >98% availability through real-time monitoring and rapid fault resolution")
        with st.container(border=True):
            st.markdown("**🔋 Lifecycle Protection**")
            st.markdown("Monitor SoH degradation, prevent warranty excursions, plan augmentation timing")
    with col2:
        with st.container(border=True):
            st.markdown("**💰 Revenue Assurance**")
            st.markdown("Attribute losses to root causes, track dispatch adherence, identify comms gaps")
        with st.container(border=True):
            st.markdown("**📋 Claims Readiness**")
            st.markdown("Generate evidence packs for SLA disputes, warranty claims, partner reconciliation")

    # Scope
    st.header("📐 Scope")
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**✅ In Scope**")
        st.success("""
        - TMEIC Controller, BMS, EMS/SCADA
        - RTM Settlement, CMMS, Contracts
        - KPI dashboards, loss attribution
        - SLA tracking, vendor comparison
        """)
    with col2:
        st.markdown("**❌ Out Of Scope**")
        st.error("""
        - External market research
        - Price forecasting, trading signals
        - Third-party managed sites
        - External fleet benchmarking
        """)

    # MVP Deliverables
    st.header("📦 MVP Deliverables")
    deliverables = {
        "Overview": ["Architecture", "Proposal"],
        "ENKA (5)": ["Portfolio Cockpit", "Partner Monetization", "RTM Settlement", "Lifecycle Planning", "Pipeline"],
        "TMEIC (5)": ["Real Time Ops", "Controller Health", "Faults Timeline", "Grid Compliance", "Historian"],
        "Combined (4)": ["Revenue Loss", "Dispatch vs Stress", "SLA Evidence", "Benchmarking"],
    }
    cols = st.columns(4)
    for idx, (pack, pages) in enumerate(deliverables.items()):
        with cols[idx]:
            with st.container(border=True):
                st.markdown(f"**{pack}**")
                for page in pages:
                    st.caption(f"• {page}")

    # Roadmap
    st.header("🗺️ Roadmap")
    col1, col2, col3 = st.columns(3)
    with col1:
        with st.container(border=True):
            st.markdown("**Phase 1: Foundation**")
            st.caption("0-3 months")
            st.markdown("Data pipeline, Core dashboards, Backfill, Training")
            st.progress(100)
    with col2:
        with st.container(border=True):
            st.markdown("**Phase 2: Optimization**")
            st.caption("3-9 months")
            st.markdown("Predictive analytics, Alerting, SLA automation, Mobile")
            st.progress(0)
    with col3:
        with st.container(border=True):
            st.markdown("**Phase 3: Scale**")
            st.caption("9-18 months")
            st.markdown("ML anomaly detection, Partner API, Site automation")
            st.progress(0)

    # Risks
    st.header("⚠️ Risks And Mitigations")
    risks = [
        ("Data Quality", "Incomplete telemetry", "Data quality scoring, gap detection"),
        ("Time Sync", "Clock drift between systems", "NTP enforcement, time alignment"),
        ("Vendor Integration", "TMEIC API limitations", "Direct DB access, file fallback"),
        ("Change Management", "User adoption resistance", "Phased rollout, training"),
    ]
    cols = st.columns(2)
    for idx, (risk, desc, mitigation) in enumerate(risks):
        with cols[idx % 2]:
            with st.container(border=True):
                st.markdown(f"**{risk}**: {desc}")
                st.caption(f"→ {mitigation}")

    render_footer()


main()
