"""
Proposal Executive Summary

One-page proposal for BESS Analytics platform with objectives, scope, and roadmap.
"""

import sys
from pathlib import Path


import streamlit as st

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from dashboard.components.branding import apply_enka_theme, render_sidebar_branding, render_footer, style_plotly_chart
from dashboard.components.header import get_dashboard_config, render_header
from dashboard.components.kpi_glossary import render_kpi_glossary

st.set_page_config(page_title="Proposal Executive Summary", page_icon="📋", layout="wide")

# Apply ENKA branding
apply_enka_theme()
render_sidebar_branding()


DASHBOARD_KEY = "proposal_executive_summary"


def generate_html_export() -> str:
    """Generate HTML export of the proposal."""
    return """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>BESS Analytics - Proposal Executive Summary</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            max-width: 900px;
            margin: 0 auto;
            padding: 40px;
            background: white;
            color: #333;
            line-height: 1.6;
        }
        .header {
            text-align: center;
            border-bottom: 3px solid #1e3a5f;
            padding-bottom: 20px;
            margin-bottom: 30px;
        }
        .header h1 { color: #1e3a5f; margin: 0; font-size: 28px; }
        .header p { color: #666; margin: 10px 0 0 0; }
        h2 {
            color: #1e3a5f;
            border-left: 4px solid #2d5a87;
            padding-left: 15px;
            margin-top: 30px;
        }
        .objectives {
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 15px;
            margin: 20px 0;
        }
        .objective {
            background: #f8f9fa;
            padding: 15px;
            border-radius: 8px;
            border-left: 4px solid #28a745;
        }
        .objective h4 { margin: 0 0 8px 0; color: #1e3a5f; }
        .scope-table {
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
        }
        .scope-table th, .scope-table td {
            border: 1px solid #ddd;
            padding: 12px;
            text-align: left;
        }
        .scope-table th { background: #1e3a5f; color: white; }
        .scope-table tr:nth-child(even) { background: #f8f9fa; }
        .in-scope { color: #28a745; font-weight: bold; }
        .out-scope { color: #dc3545; font-weight: bold; }
        .roadmap {
            display: flex;
            gap: 15px;
            margin: 20px 0;
        }
        .phase {
            flex: 1;
            background: linear-gradient(135deg, #f8f9fa, #e9ecef);
            padding: 20px;
            border-radius: 8px;
            border-top: 4px solid #2d5a87;
        }
        .phase h4 { margin: 0 0 10px 0; color: #1e3a5f; }
        .risks {
            background: #fff3cd;
            padding: 20px;
            border-radius: 8px;
            border-left: 4px solid #ffc107;
        }
        .footer {
            margin-top: 40px;
            padding-top: 20px;
            border-top: 1px solid #ddd;
            text-align: center;
            color: #666;
            font-size: 12px;
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>BESS Analytics Platform</h1>
        <p>Proposal Executive Summary | ENKA Energy Storage Analytics</p>
    </div>

    <h2>Problem Statement</h2>
    <p>
        ENKA operates a growing fleet of Battery Energy Storage Systems (BESS) across multiple sites
        with different controller vendors. Current challenges include:
    </p>
    <ul>
        <li>Fragmented visibility across TMEIC controllers, BMS systems, and EMS/SCADA</li>
        <li>Revenue leakage due to unattributed dispatch failures and data gaps</li>
        <li>Reactive maintenance leading to extended downtime and warranty disputes</li>
        <li>Manual reconciliation of settlement data with operational performance</li>
        <li>Limited insight into partner revenue sharing and SLA compliance</li>
    </ul>

    <h2>Objectives</h2>
    <div class="objectives">
        <div class="objective">
            <h4>🎯 Availability Maximization</h4>
            <p>Achieve >98% availability through predictive monitoring and rapid fault resolution</p>
        </div>
        <div class="objective">
            <h4>💰 Revenue Assurance</h4>
            <p>Attribute and minimize revenue losses from faults, comms gaps, and dispatch deviations</p>
        </div>
        <div class="objective">
            <h4>🔋 Lifecycle Protection</h4>
            <p>Monitor battery health, prevent warranty excursions, plan augmentation timing</p>
        </div>
        <div class="objective">
            <h4>📋 Claims Readiness</h4>
            <p>Generate evidence packs for SLA disputes and warranty claims with full lineage</p>
        </div>
    </div>

    <h2>Scope</h2>
    <table class="scope-table">
        <tr>
            <th>Category</th>
            <th>In Scope</th>
            <th>Out Of Scope</th>
        </tr>
        <tr>
            <td>Data Sources</td>
            <td class="in-scope">TMEIC Controller, BMS, EMS/SCADA, RTM Settlement, CMMS, Contracts</td>
            <td class="out-scope">External market research, Cornwall Insight, fleet benchmarking (external)</td>
        </tr>
        <tr>
            <td>Analytics</td>
            <td class="in-scope">KPI dashboards, loss attribution, SLA tracking, vendor comparison (internal)</td>
            <td class="out-scope">Price forecasting, market optimization, trading signals</td>
        </tr>
        <tr>
            <td>Sites</td>
            <td class="in-scope">All ENKA-operated BESS sites (TMEIC + other controllers)</td>
            <td class="out-scope">Third-party managed sites, development projects pre-COD</td>
        </tr>
    </table>

    <h2>MVP Deliverables</h2>
    <ul>
        <li><strong>Overview Pack:</strong> Architecture And Data Flow, Proposal Executive Summary</li>
        <li><strong>ENKA Pack:</strong> Portfolio Executive Cockpit, Partner Monetization, RTM Settlement, Lifecycle Planning, Pipeline Tracking</li>
        <li><strong>TMEIC Pack:</strong> Real Time Ops, Controller Health, Faults Timeline, Grid Compliance, Historian Explorer</li>
        <li><strong>Combined Pack:</strong> Revenue Loss Attribution, Dispatch Vs Stress, SLA Evidence, Vendor Benchmarking</li>
    </ul>

    <h2>Roadmap</h2>
    <div class="roadmap">
        <div class="phase">
            <h4>Phase 1: Foundation (0-3 months)</h4>
            <ul>
                <li>Data pipeline setup (Medallion architecture)</li>
                <li>Core KPI dashboards</li>
                <li>Historical data backfill</li>
                <li>User training</li>
            </ul>
        </div>
        <div class="phase">
            <h4>Phase 2: Optimization (3-9 months)</h4>
            <ul>
                <li>Predictive analytics</li>
                <li>Automated alerting</li>
                <li>SLA automation</li>
                <li>Mobile access</li>
            </ul>
        </div>
        <div class="phase">
            <h4>Phase 3: Scale (9-18 months)</h4>
            <ul>
                <li>ML-based anomaly detection</li>
                <li>Cross-vendor optimization</li>
                <li>API for partners</li>
                <li>New site onboarding automation</li>
            </ul>
        </div>
    </div>

    <h2>Risks And Mitigations</h2>
    <div class="risks">
        <ul>
            <li><strong>Data Quality:</strong> Incomplete or inconsistent telemetry → Implement data quality scoring, gap detection, and source validation</li>
            <li><strong>Time Synchronization:</strong> Clock drift between systems → NTP enforcement, drift detection, time alignment in Silver layer</li>
            <li><strong>Vendor Integration:</strong> TMEIC API limitations → Direct database access, file-based fallback, protocol adapters</li>
            <li><strong>Change Management:</strong> User adoption resistance → Phased rollout, champion users, training program</li>
        </ul>
    </div>

    <h2>Team Roles And Assumptions</h2>
    <ul>
        <li><strong>Data Engineer:</strong> Pipeline development, ETL, data quality</li>
        <li><strong>Analytics Engineer:</strong> KPI logic, dashboard development, testing</li>
        <li><strong>Product Owner:</strong> Requirements, prioritization, stakeholder management</li>
        <li><strong>ENKA SME:</strong> Domain expertise, validation, acceptance testing</li>
    </ul>
    <p><em>Assumes: Access to source systems granted, historical data available for 30+ days, stakeholder availability for weekly reviews.</em></p>

    <div class="footer">
        <p>BESS Analytics Platform | Confidential - ENKA Internal Use Only</p>
        <p>Data sources: ENKA internal systems only (no external market research)</p>
    </div>
</body>
</html>
"""


def main():
    # Header metadata
    config = {
        "title": "Proposal Executive Summary",
        "personas": ["CEO", "CFO", "Partner Stakeholders", "Board Members"],
        "decisions": [
            "Approve project scope and budget",
            "Align on objectives and success criteria",
            "Confirm data source access",
            "Approve roadmap and timeline"
        ],
        "data_sources": [
            {"system": "Proposal Documentation", "tables": ["N/A"], "notes": "Static reference page"},
        ],
        "freshness": "Static (proposal document)",
    }

    render_header(
        title=config.get("title"),
        personas=config.get("personas", []),
        decisions=config.get("decisions", []),
        data_sources=config.get("data_sources", []),
        freshness=config.get("freshness", ""),
        kpis=[],
    )

    st.divider()

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

    st.divider()

    # Objectives
    st.header("🎯 Objectives")

    col1, col2 = st.columns(2)

    with col1:
        with st.container(border=True):
            st.markdown("### ⬆️ Availability Maximization")
            st.markdown("""
            Achieve **>98% availability** through:
            - Real-time fault monitoring
            - Predictive maintenance alerts
            - Rapid issue resolution workflows
            """)

        with st.container(border=True):
            st.markdown("### 🔋 Lifecycle Protection")
            st.markdown("""
            Protect battery assets via:
            - SoH degradation tracking
            - Warranty excursion monitoring
            - Augmentation timing optimization
            """)

    with col2:
        with st.container(border=True):
            st.markdown("### 💰 Revenue Assurance")
            st.markdown("""
            Minimize revenue losses by:
            - Attributing losses to root causes
            - Tracking dispatch adherence
            - Identifying comms gaps impact
            """)

        with st.container(border=True):
            st.markdown("### 📋 Claims Readiness")
            st.markdown("""
            Generate evidence packs for:
            - SLA breach disputes
            - Warranty claims
            - Partner reconciliation
            """)

    st.divider()

    # Scope
    st.header("📐 Scope")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### ✅ In Scope")
        st.markdown("""
        **Data Sources:**
        - TMEIC Controller (PCS/Plant Control)
        - BMS (Battery Management System)
        - ENKA EMS/SCADA
        - RTM / Market Settlement Provider
        - ENKA CMMS
        - Contracts And Finance

        **Analytics:**
        - KPI dashboards (portfolio to asset level)
        - Revenue loss attribution
        - SLA compliance tracking
        - Internal vendor comparison
        """)

    with col2:
        st.markdown("### ❌ Out Of Scope")
        st.error("""
        **Explicitly Excluded:**
        - External market research
        - Cornwall Insight datasets
        - External fleet benchmarking
        - Price forecasting models
        - Trading signal generation
        - Third-party managed sites
        """)

    st.divider()

    # MVP Deliverables
    st.header("📦 MVP Deliverables")

    deliverables = {
        "Overview Pack": [
            "Architecture And Data Flow",
            "Proposal Executive Summary"
        ],
        "ENKA Pack": [
            "Portfolio Executive Cockpit",
            "Partner Monetization And Revenue Share",
            "RTM Settlement Reconciliation",
            "Lifecycle And Augmentation Planning",
            "Development Pipeline Tracking"
        ],
        "TMEIC Pack": [
            "PCS Controller Real Time Operations",
            "Controller Health And Communications",
            "Faults And Trips Timeline",
            "Grid Performance And Compliance",
            "Historian Explorer"
        ],
        "Combined Pack": [
            "Revenue Loss Attribution",
            "Dispatch Versus Asset Stress",
            "SLA And Warranty Evidence Pack",
            "Portfolio Benchmarking By Vendor And Site"
        ]
    }

    cols = st.columns(4)
    for idx, (pack, pages) in enumerate(deliverables.items()):
        with cols[idx]:
            with st.container(border=True):
                st.markdown(f"**{pack}**")
                for page in pages:
                    st.markdown(f"- {page}")

    st.divider()

    # Roadmap
    st.header("🗺️ Roadmap")

    col1, col2, col3 = st.columns(3)

    with col1:
        with st.container(border=True):
            st.markdown("### Phase 1: Foundation")
            st.caption("0-3 months")
            st.markdown("""
            - Data pipeline setup (Medallion)
            - Core KPI dashboards
            - Historical data backfill
            - User training
            - Pilot with 1 site
            """)
            st.progress(100, text="MVP Complete")

    with col2:
        with st.container(border=True):
            st.markdown("### Phase 2: Optimization")
            st.caption("3-9 months")
            st.markdown("""
            - Predictive analytics
            - Automated alerting
            - SLA automation
            - Mobile access
            - All sites onboarded
            """)
            st.progress(0, text="Planned")

    with col3:
        with st.container(border=True):
            st.markdown("### Phase 3: Scale")
            st.caption("9-18 months")
            st.markdown("""
            - ML anomaly detection
            - Cross-vendor optimization
            - Partner API access
            - New site automation
            - Advanced forecasting
            """)
            st.progress(0, text="Future")

    st.divider()

    # Team Roles
    st.header("👥 Team Roles And Assumptions")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### Team Roles")
        st.markdown("""
        | Role | Responsibilities |
        |------|-----------------|
        | **Data Engineer** | Pipeline development, ETL, data quality |
        | **Analytics Engineer** | KPI logic, dashboards, testing |
        | **Product Owner** | Requirements, prioritization |
        | **ENKA SME** | Domain expertise, validation |
        """)

    with col2:
        st.markdown("### Key Assumptions")
        st.info("""
        - Access to all source systems granted
        - Historical data available (30+ days)
        - Stakeholder availability for weekly reviews
        - No major schema changes during MVP
        - Network connectivity to all sites
        """)

    st.divider()

    # Risks
    st.header("⚠️ Risks And Mitigations")

    risks = [
        {
            "risk": "Data Quality",
            "description": "Incomplete or inconsistent telemetry from sites",
            "mitigation": "Implement data quality scoring, gap detection, source validation"
        },
        {
            "risk": "Time Synchronization",
            "description": "Clock drift between controllers, BMS, and EMS",
            "mitigation": "NTP enforcement, drift detection, time alignment in Silver layer"
        },
        {
            "risk": "Vendor Integration",
            "description": "TMEIC API limitations or access restrictions",
            "mitigation": "Direct database access, file-based fallback, protocol adapters"
        },
        {
            "risk": "Change Management",
            "description": "User adoption resistance or training gaps",
            "mitigation": "Phased rollout, champion users, comprehensive training"
        },
    ]

    for risk in risks:
        with st.container(border=True):
            col1, col2 = st.columns([1, 2])
            with col1:
                st.warning(f"**{risk['risk']}**")
                st.caption(risk['description'])
            with col2:
                st.success(f"**Mitigation:** {risk['mitigation']}")

    st.divider()

    # KPI Glossary
    render_kpi_glossary(
        kpi_keys=["availability_pct", "lost_revenue_gbp", "soh_pct", "sla_breaches_count"],
        title="Key KPI Definitions",
        expanded=False
    )


if __name__ == "__main__":
    main()
