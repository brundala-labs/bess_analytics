"""
Architecture And Data Flow

Cloud architecture, Medallion data pipeline, and canonical data model documentation.
"""

import sys
from pathlib import Path
import base64

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
    """Generate cloud architecture diagram using Mermaid syntax."""
    return """
```mermaid
flowchart TB
    subgraph Sources["Data Sources"]
        TMEIC["TMEIC Controller<br/>(PCS/Plant Control)"]
        BMS["BMS<br/>(Battery Management System)"]
        EMS["ENKA EMS/SCADA"]
        RTM["RTM / Market<br/>Settlement Provider"]
        CMMS["ENKA CMMS"]
        FINANCE["Contracts And Finance"]
    end

    subgraph Streaming["Streaming Bus"]
        KAFKA["Kafka / Event Hubs /<br/>Kinesis / Pub/Sub"]
    end

    subgraph Cloud["Any Cloud Platform"]
        subgraph Lake["Data Lake (S3/ADLS/GCS)"]
            BRONZE["Bronze Layer<br/>(Raw Events)"]
            SILVER["Silver Layer<br/>(Cleaned/Conformed)"]
            GOLD["Gold Layer<br/>(KPI Tables)"]
        end

        subgraph Compute["Databricks"]
            STREAM["Structured Streaming"]
            DELTA["Delta Lake"]
            UNITY["Unity Catalog<br/>(Governance)"]
        end
    end

    subgraph Serving["Analytics Serving"]
        API["FastAPI<br/>Metrics Service"]
        BI["Streamlit /<br/>Power BI / Tableau"]
    end

    TMEIC --> KAFKA
    BMS --> KAFKA
    EMS --> KAFKA
    RTM --> |Batch| BRONZE
    CMMS --> |Batch| BRONZE
    FINANCE --> |Batch| BRONZE

    KAFKA --> STREAM
    STREAM --> BRONZE
    BRONZE --> DELTA
    DELTA --> SILVER
    SILVER --> DELTA
    DELTA --> GOLD

    GOLD --> API
    API --> BI

    UNITY -.-> BRONZE
    UNITY -.-> SILVER
    UNITY -.-> GOLD
```
"""


def get_medallion_diagram() -> str:
    """Generate Medallion Architecture diagram."""
    return """
```mermaid
flowchart LR
    subgraph Bronze["Bronze Layer (Raw)"]
        B1["telemetry_raw.jsonl<br/>- As-received from sensors<br/>- Minimal parsing<br/>- Append-only"]
        B2["events_raw.jsonl<br/>- Controller events<br/>- Fault codes<br/>- Timestamps as-is"]
        B3["settlement_raw.csv<br/>- Daily settlement files<br/>- Partner data<br/>- Contract terms"]
    end

    subgraph Silver["Silver Layer (Cleaned)"]
        S1["fact_telemetry<br/>- Canonical schema<br/>- Deduplicated<br/>- Time-aligned"]
        S2["fact_events<br/>- Normalized codes<br/>- Duration calculated<br/>- Linked to assets"]
        S3["fact_settlement<br/>- Validated revenues<br/>- Service mapping<br/>- Partner joins"]
        S4["dim_site / dim_asset<br/>- Master data<br/>- Slowly changing"]
    end

    subgraph Gold["Gold Layer (Curated)"]
        G1["agg_telemetry_15min<br/>- Downsampled metrics<br/>- Derived KPIs"]
        G2["agg_site_daily<br/>- Daily rollups<br/>- Availability, DoD"]
        G3["agg_revenue_daily<br/>- Revenue attribution<br/>- Loss analysis"]
        G4["v_sla_compliance<br/>- SLA status<br/>- Penalty exposure"]
    end

    B1 --> S1
    B2 --> S2
    B3 --> S3
    S1 --> G1
    S1 --> G2
    S2 --> G2
    S3 --> G3
    S4 --> G4
```
"""


def get_data_model_diagram() -> str:
    """Generate canonical data model diagram."""
    return """
```mermaid
erDiagram
    dim_site {
        string site_id PK
        string name
        string country
        float grid_connection_mw
        float bess_mw
        float bess_mwh
        date cod_date
        string vendor_controller
    }

    dim_asset {
        string asset_id PK
        string site_id FK
        string asset_type
        string make
        string model
    }

    dim_service {
        string service_id PK
        string name
        string market
    }

    dim_partner {
        string partner_id PK
        string site_id FK
        string name
        float revenue_share_pct
    }

    dim_sla {
        string sla_id PK
        string site_id FK
        string metric_name
        float threshold
        float penalty_rate_per_hour
    }

    fact_telemetry {
        timestamp ts
        string site_id FK
        string asset_id FK
        string tag
        float value
    }

    fact_dispatch {
        timestamp ts
        string site_id FK
        string service_id FK
        float command_kw
        float actual_kw
    }

    fact_events {
        string event_id PK
        string site_id FK
        string asset_id FK
        timestamp start_ts
        timestamp end_ts
        string severity
        string event_type
        string code
        string description
    }

    fact_settlement {
        date date
        string site_id FK
        string service_id FK
        float revenue_gbp
        float energy_mwh
        float avg_price_gbp_per_mwh
    }

    fact_maintenance {
        string ticket_id PK
        string site_id FK
        string asset_id FK
        timestamp opened_ts
        timestamp closed_ts
        string issue_category
        string resolution
        float cost_gbp
    }

    dim_site ||--o{ dim_asset : contains
    dim_site ||--o{ dim_partner : has
    dim_site ||--o{ dim_sla : governed_by
    dim_site ||--o{ fact_telemetry : generates
    dim_site ||--o{ fact_dispatch : receives
    dim_site ||--o{ fact_events : logs
    dim_site ||--o{ fact_settlement : earns
    dim_asset ||--o{ fact_telemetry : reports
    dim_asset ||--o{ fact_events : triggers
    dim_service ||--o{ fact_dispatch : commands
    dim_service ||--o{ fact_settlement : revenues
```
"""


def generate_html_export() -> str:
    """Generate HTML export of the architecture page."""
    html_content = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>BESS Analytics - Architecture And Data Flow</title>
    <script src="https://cdn.jsdelivr.net/npm/mermaid/dist/mermaid.min.js"></script>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            background: #f5f5f5;
        }}
        .header {{
            background: linear-gradient(135deg, #1e3a5f, #2d5a87);
            color: white;
            padding: 30px;
            border-radius: 10px;
            margin-bottom: 30px;
        }}
        .header h1 {{ margin: 0 0 10px 0; }}
        .header p {{ margin: 0; opacity: 0.9; }}
        .section {{
            background: white;
            padding: 25px;
            border-radius: 10px;
            margin-bottom: 20px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .section h2 {{
            color: #1e3a5f;
            border-bottom: 2px solid #e0e0e0;
            padding-bottom: 10px;
        }}
        .mermaid {{
            display: flex;
            justify-content: center;
            margin: 20px 0;
        }}
        .metadata {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin-top: 15px;
        }}
        .meta-card {{
            background: #f8f9fa;
            padding: 15px;
            border-radius: 8px;
            border-left: 4px solid #2d5a87;
        }}
        .meta-card h4 {{ margin: 0 0 8px 0; color: #1e3a5f; }}
        .meta-card ul {{ margin: 0; padding-left: 20px; }}
        .footer {{
            text-align: center;
            color: #666;
            margin-top: 30px;
            padding: 20px;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>🏗️ Architecture And Data Flow</h1>
        <p>BESS Analytics Platform - Cloud Architecture with Databricks and Medallion Pipeline</p>
    </div>

    <div class="section">
        <h2>Personas</h2>
        <div class="metadata">
            <div class="meta-card">
                <h4>Target Users</h4>
                <ul>
                    <li>CEO</li>
                    <li>CTO</li>
                    <li>Head Of Operations</li>
                    <li>Engineering Lead</li>
                </ul>
            </div>
            <div class="meta-card">
                <h4>Primary Decisions</h4>
                <ul>
                    <li>Approve architecture design</li>
                    <li>Confirm project scope</li>
                    <li>Align stakeholders</li>
                    <li>Validate data sources</li>
                </ul>
            </div>
        </div>
    </div>

    <div class="section">
        <h2>Cloud Streaming Architecture</h2>
        <p>End-to-end data flow from sensors to analytics dashboards using cloud-native components.</p>
        <div class="mermaid">
flowchart TB
    subgraph Sources["Data Sources"]
        TMEIC["TMEIC Controller"]
        BMS["BMS"]
        EMS["ENKA EMS/SCADA"]
        RTM["RTM Settlement"]
        CMMS["ENKA CMMS"]
        FINANCE["Contracts And Finance"]
    end
    subgraph Streaming["Streaming Bus"]
        KAFKA["Kafka / Event Hubs / Kinesis / Pub/Sub"]
    end
    subgraph Cloud["Any Cloud Platform"]
        subgraph Lake["Data Lake"]
            BRONZE["Bronze"]
            SILVER["Silver"]
            GOLD["Gold"]
        end
        subgraph Compute["Databricks"]
            STREAM["Structured Streaming"]
            DELTA["Delta Lake"]
        end
    end
    subgraph Serving["Analytics"]
        API["FastAPI"]
        BI["Streamlit / BI Tools"]
    end
    TMEIC --> KAFKA
    BMS --> KAFKA
    EMS --> KAFKA
    RTM --> BRONZE
    CMMS --> BRONZE
    FINANCE --> BRONZE
    KAFKA --> STREAM
    STREAM --> BRONZE
    BRONZE --> SILVER
    SILVER --> GOLD
    GOLD --> API
    API --> BI
        </div>
    </div>

    <div class="section">
        <h2>Medallion Architecture</h2>
        <p>Three-layer data pipeline ensuring quality, governance, and analytics-ready datasets.</p>
        <div class="mermaid">
flowchart LR
    subgraph Bronze["Bronze - Raw"]
        B1["telemetry_raw"]
        B2["events_raw"]
        B3["settlement_raw"]
    end
    subgraph Silver["Silver - Cleaned"]
        S1["fact_telemetry"]
        S2["fact_events"]
        S3["fact_settlement"]
        S4["dimensions"]
    end
    subgraph Gold["Gold - Curated"]
        G1["agg_telemetry_15min"]
        G2["agg_site_daily"]
        G3["agg_revenue_daily"]
        G4["v_sla_compliance"]
    end
    B1 --> S1
    B2 --> S2
    B3 --> S3
    S1 --> G1
    S1 --> G2
    S2 --> G2
    S3 --> G3
        </div>
    </div>

    <div class="section">
        <h2>Data Sources</h2>
        <div class="metadata">
            <div class="meta-card">
                <h4>TMEIC Controller (PCS/Plant Control)</h4>
                <p>Real-time telemetry: power, voltage, frequency, controller status</p>
            </div>
            <div class="meta-card">
                <h4>BMS (Battery Management System)</h4>
                <p>Battery metrics: SoC, SoH, temperature, voltage, current</p>
            </div>
            <div class="meta-card">
                <h4>ENKA EMS/SCADA</h4>
                <p>Dispatch commands, setpoints, alarms</p>
            </div>
            <div class="meta-card">
                <h4>RTM / Market Settlement</h4>
                <p>Daily settlement, revenue, energy volumes</p>
            </div>
            <div class="meta-card">
                <h4>ENKA CMMS</h4>
                <p>Maintenance tickets, work orders, costs</p>
            </div>
            <div class="meta-card">
                <h4>Contracts And Finance</h4>
                <p>Partner agreements, SLA terms, revenue share</p>
            </div>
        </div>
    </div>

    <div class="footer">
        <p>Generated by BESS Analytics Platform | Internal Use Only</p>
        <p>Data sources: ENKA internal systems only (no external market research)</p>
    </div>

    <script>
        mermaid.initialize({{ startOnLoad: true, theme: 'default' }});
    </script>
</body>
</html>
"""
    return html_content


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

    # Export button
    col1, col2, col3 = st.columns([1, 1, 4])
    with col1:
        html_content = generate_html_export()
        b64 = base64.b64encode(html_content.encode()).decode()
        href = f'<a href="data:text/html;base64,{b64}" download="architecture_and_data_flow.html">📥 Export To HTML</a>'
        st.markdown(href, unsafe_allow_html=True)

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

    st.markdown(get_architecture_diagram())

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

    st.markdown(get_medallion_diagram())

    # Bronze/Silver/Gold table mapping
    with st.expander("📋 Table Mapping Details"):
        col1, col2, col3 = st.columns(3)

        with col1:
            st.markdown("**Bronze (Raw)**")
            st.code("""
/data/bronze/
├── telemetry/
│   ├── site001_2024031512.jsonl
│   └── site002_2024031512.jsonl
├── events/
│   └── events_raw.jsonl
└── settlement/
    └── settlement_2024.csv
            """)

        with col2:
            st.markdown("**Silver (Cleaned)**")
            st.code("""
fact_telemetry
fact_dispatch
fact_events
fact_settlement
fact_maintenance
fact_data_quality
dim_site
dim_asset
dim_service
dim_partner
dim_sla
            """)

        with col3:
            st.markdown("**Gold (Curated)**")
            st.code("""
agg_telemetry_15min
agg_site_daily
agg_site_monthly
agg_events_daily
agg_revenue_daily
v_battery_health
v_site_availability
v_sla_compliance
v_dispatch_compliance
v_revenue_loss_attribution
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

    st.markdown(get_data_model_diagram())

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
