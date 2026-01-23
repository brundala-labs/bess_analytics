"""
ENKA BESS Analytics - Architecture And Data Flow

Main entry point - Cloud architecture, Medallion data pipeline, and canonical data model.
"""

import sys
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components

sys.path.insert(0, str(Path(__file__).parent.parent))

from dashboard.components.branding import apply_enka_theme, render_sidebar_branding, render_footer, ENKA_GREEN

st.set_page_config(initial_sidebar_state="expanded", page_title="BESS Analytics Platform", page_icon="⚡", layout="wide")

apply_enka_theme()
render_sidebar_branding()

# Add Google Material Icons with custom styling
st.markdown("""
<link href="https://fonts.googleapis.com/icon?family=Material+Icons" rel="stylesheet">
<style>
.material-icons {
    vertical-align: middle;
    margin-right: 10px;
    font-size: 32px;
}
h1 .material-icons { font-size: 32px; }
h2 .material-icons { font-size: 28px; }
h1 { font-size: 2rem !important; }
h2 { font-size: 1.6rem !important; font-weight: 600; margin-top: 2rem; }
</style>
""", unsafe_allow_html=True)


def render_mermaid(mermaid_code: str, height: int = 400):
    """Render a Mermaid diagram with ENKA styling."""
    html = f"""
    <script src="https://cdn.jsdelivr.net/npm/mermaid/dist/mermaid.min.js"></script>
    <style>
        .mermaid {{
            display: flex;
            justify-content: center;
            padding: 30px;
            background: linear-gradient(135deg, #ffffff 0%, #f8f9fa 100%);
            border-radius: 16px;
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
        }}
        .mermaid svg {{
            max-width: 100%;
        }}
    </style>
    <div class="mermaid">
    {mermaid_code}
    </div>
    <script>
        mermaid.initialize({{
            startOnLoad: true,
            theme: 'base',
            securityLevel: 'loose',
            themeVariables: {{
                primaryColor: '#81d742',
                primaryTextColor: '#111111',
                primaryBorderColor: '#238238',
                lineColor: '#555555',
                secondaryColor: '#e8f5e9',
                tertiaryColor: '#f0f2f6',
                background: '#ffffff',
                mainBkg: '#ffffff',
                nodeBorder: '#238238',
                clusterBkg: 'transparent',
                clusterBorder: 'transparent',
                titleColor: '#111111',
                edgeLabelBackground: '#ffffff',
                fontSize: '18px',
                fontFamily: 'system-ui, -apple-system, sans-serif'
            }},
            flowchart: {{
                curve: 'basis',
                padding: 25,
                nodeSpacing: 60,
                rankSpacing: 100,
                htmlLabels: true,
                defaultRenderer: 'dagre-wrapper',
                useMaxWidth: true
            }}
        }});
    </script>
    """
    components.html(html, height=height, scrolling=False)


st.markdown('<h1><span class="material-icons">architecture</span> BESS Analytics Platform</h1>', unsafe_allow_html=True)
st.caption("AWS cloud architecture, Medallion data pipeline, and canonical data model")

# Section 1: Cloud Streaming Architecture
st.markdown('<h2><span class="material-icons">cloud</span> Cloud Streaming Architecture</h2>', unsafe_allow_html=True)
st.markdown("End-to-end data flow from sensors to analytics dashboards using cloud-native components.")

cloud_diagram = """
flowchart TB
    TMEIC["🔌 <b>TMEIC Controller</b><br/>Power & Grid Data"]
    BMS["🔋 <b>BMS</b><br/>Battery Health"]
    EMS["📡 <b>ENKA EMS</b><br/>Control Events"]
    RTM["💰 <b>RTM Settlement</b><br/>Revenue Data"]
    CMMS["🔧 <b>CMMS</b><br/>Maintenance"]

    BRONZE["🥉 <b>Bronze Layer</b><br/>Raw Data"]
    SILVER["🥈 <b>Silver Layer</b><br/>Cleaned & Validated"]
    GOLD["🥇 <b>Gold Layer</b><br/>Curated KPIs"]

    SIGNAL["📡 <b>Signal Correction</b><br/>SoC / SoE / SoP"]
    FORECAST["🔮 <b>Forecasting</b><br/>Time-to-Empty/Full"]
    BALANCE["⚖️ <b>Balancing</b><br/>Imbalance Detection"]
    INSIGHTS["💡 <b>Insights</b><br/>Auto Findings"]

    API["🚀 <b>FastAPI</b><br/>REST Endpoints"]
    BI["📊 <b>Streamlit</b><br/>18 Dashboards"]

    TMEIC --> BRONZE
    BMS --> BRONZE
    EMS --> BRONZE
    RTM --> BRONZE
    CMMS --> BRONZE

    BRONZE --> SILVER
    SILVER --> GOLD

    SILVER --> SIGNAL
    SILVER --> BALANCE
    SIGNAL --> FORECAST
    SIGNAL --> INSIGHTS
    BALANCE --> INSIGHTS
    FORECAST --> GOLD
    INSIGHTS --> GOLD

    GOLD --> API
    API --> BI
"""
render_mermaid(cloud_diagram, height=1100)

col1, col2 = st.columns(2)
with col1:
    st.markdown("**Key Components:**")
    st.markdown("""
- **Cloud**: AWS
- **Data Lake**: S3 (Medallion layers)
- **Compute**: AWS Databricks
    """)
with col2:
    st.markdown("**&nbsp;**")
    st.markdown("""
- **Storage**: Delta Lake
- **Governance**: Unity Catalog
- **Analytics**: FastAPI + Streamlit
    """)

# Section 2: Medallion Architecture
st.markdown('<h2><span class="material-icons">layers</span> Medallion Architecture</h2>', unsafe_allow_html=True)
st.markdown("Data flows through three progressively refined layers:")

medallion_diagram = """
flowchart LR
    B1["🥉 <b>telemetry_raw</b>"]
    B2["🥉 <b>events_raw</b>"]
    B3["🥉 <b>settlement_raw</b>"]

    S1["🥈 <b>fact_telemetry</b>"]
    S2["🥈 <b>fact_events</b>"]
    S3["🥈 <b>fact_settlement</b>"]
    S4["🥈 <b>dimensions</b>"]

    E1["🧠 <b>corrected_signals</b>"]
    E2["🧠 <b>forecasts</b>"]
    E3["🧠 <b>imbalance</b>"]
    E4["🧠 <b>insights</b>"]

    G1["🥇 <b>agg_15min</b>"]
    G2["🥇 <b>agg_daily</b>"]
    G3["🥇 <b>v_signal_health</b>"]

    B1 --> S1
    B2 --> S2
    B3 --> S3
    S1 --> E1
    S1 --> E3
    E1 --> E2
    E1 --> E4
    E3 --> E4
    S1 --> G1
    S1 --> G2
    E1 --> G3
"""
render_mermaid(medallion_diagram, height=550)

col1, col2, col3, col4 = st.columns(4)
with col1:
    with st.container(border=True):
        st.markdown("**Bronze (Raw)**")
        st.caption("As-received, append-only")
        st.markdown("telemetry/, events/, settlement/")
with col2:
    with st.container(border=True):
        st.markdown("**Silver (Cleaned)**")
        st.caption("Canonical schema, validated")
        st.markdown("fact_*, dim_*")
with col3:
    with st.container(border=True):
        st.markdown("**Edge Intelligence**")
        st.caption("ML-enhanced signals")
        st.markdown("corrected_signals, forecasts, insights")
with col4:
    with st.container(border=True):
        st.markdown("**Gold (Curated)**")
        st.caption("KPI tables, rollups")
        st.markdown("agg_*, v_*")

# Section 3: Canonical Data Model
st.markdown('<h2><span class="material-icons">schema</span> Canonical Data Model</h2>', unsafe_allow_html=True)

data_model_diagram = """
erDiagram
    dim_site ||--o{ fact_telemetry : has
    dim_site ||--o{ fact_events : has
    dim_site ||--o{ fact_settlement : has
    dim_site ||--o{ fact_corrected_signals : has
    dim_site ||--o{ fact_forecasts : has
    dim_site ||--o{ fact_insights_findings : has
    dim_asset ||--o{ fact_telemetry : has
    dim_asset ||--o{ fact_imbalance : has
    dim_partner ||--o{ fact_settlement : has
    dim_service ||--o{ fact_settlement : has
    dim_sla ||--o{ dim_site : governs

    dim_site {
        string site_id PK
        string name
        float capacity_mw
        string region
    }
    dim_asset {
        string asset_id PK
        string site_id FK
        string asset_type
        string vendor
    }
    fact_telemetry {
        datetime ts
        string site_id FK
        float soc_pct
        float p_kw
    }
    fact_corrected_signals {
        datetime ts
        string site_id FK
        float soc_corrected
        float trust_score
    }
    fact_forecasts {
        datetime ts
        string site_id FK
        int horizon_min
        float time_to_empty
    }
    fact_insights_findings {
        string finding_id PK
        string site_id FK
        string severity
        float value_gbp
    }
"""
render_mermaid(data_model_diagram, height=400)

st.markdown("""
**Star Schema Design:**
- **Dimensions**: Site, Asset, Service, Partner, SLA
- **Core Facts**: Telemetry, Dispatch, Events, Settlement, Maintenance
- **Edge Intelligence Facts**: Corrected Signals, Forecasts, Imbalance, Insights
- **Derived KPIs**: Availability, RTE, DoD, Lost Revenue, Trust Score, Value-at-Risk
""")

# Section 4: Edge Intelligence
st.markdown('<h2><span class="material-icons">psychology</span> Edge Intelligence Layer</h2>', unsafe_allow_html=True)
st.markdown("Advanced battery analytics with signal correction, forecasting, and automated insights.")

edge_diagram = """
flowchart LR
    RAW["📥 <b>BMS Raw SoC</b>"]
    CELL["📥 <b>Cell Voltages</b>"]
    TEMP["📥 <b>Temperatures</b>"]

    SOC["📡 <b>SoC Correction</b>"]
    SOE["📡 <b>SoE Calculation</b>"]
    TRUST["📡 <b>Trust Score</b>"]

    TTE["🔮 <b>Time-to-Empty</b>"]
    TTF["🔮 <b>Time-to-Full</b>"]

    IMBAL["⚖️ <b>Imbalance Score</b>"]
    ACTION["⚖️ <b>Action Queue</b>"]

    FIND["💡 <b>Findings</b>"]
    VALUE["💡 <b>Value Impact</b>"]

    RAW --> SOC
    CELL --> SOC
    CELL --> TRUST
    SOC --> SOE
    SOC --> TRUST

    SOE --> TTE
    SOE --> TTF

    CELL --> IMBAL
    TEMP --> IMBAL
    IMBAL --> ACTION

    TRUST --> FIND
    IMBAL --> FIND
    TTE --> FIND
    FIND --> VALUE
"""
render_mermaid(edge_diagram, height=350)

col1, col2, col3, col4 = st.columns(4)
with col1:
    with st.container(border=True):
        st.markdown("**📡 Signal Correction**")
        st.caption("Corrects BMS SoC using cell analysis")
        st.markdown("• SoC/SoE/SoP\n• HSL/LSL bands\n• Trust Score 0-100")
with col2:
    with st.container(border=True):
        st.markdown("**🔮 Forecasting**")
        st.caption("Predicts energy availability")
        st.markdown("• Time-to-Empty/Full\n• 5 horizons\n• Confidence %")
with col3:
    with st.container(border=True):
        st.markdown("**⚖️ Balancing**")
        st.caption("Detects rack imbalances")
        st.markdown("• Imbalance Score\n• Cell deltas\n• Action queue")
with col4:
    with st.container(border=True):
        st.markdown("**💡 Insights**")
        st.caption("Automated findings")
        st.markdown("• 5 categories\n• Value impact £\n• Recommendations")

# Section 5: Data Sources
st.markdown('<h2><span class="material-icons">sensors</span> Upstream Data Sources</h2>', unsafe_allow_html=True)

sources = [
    ("TMEIC Controller", "S3 Streaming", "1-min", "p_kw, q_kvar, v_pu, f_hz"),
    ("BMS", "S3 Streaming", "1-min", "soc_pct, soh_pct, temp_c"),
    ("ENKA EMS/SCADA", "S3 Streaming", "1-min", "command_kw, setpoint_kw"),
    ("RTM Settlement", "S3 Batch", "Daily", "revenue_gbp, energy_mwh"),
    ("ENKA CMMS", "S3 Batch", "On-event", "ticket_id, resolution"),
    ("Contracts & Finance", "S3 Batch", "On-change", "revenue_share_pct"),
]

cols = st.columns(3)
for idx, (name, stype, freq, tags) in enumerate(sources):
    with cols[idx % 3]:
        with st.container(border=True):
            st.markdown(f"**{name}**")
            st.caption(f"{stype} | {freq}")
            st.code(tags, language=None)

render_footer()
