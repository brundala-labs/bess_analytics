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

st.set_page_config(page_title="ENKA BESS Analytics", page_icon="⚡", layout="wide")

apply_enka_theme()
render_sidebar_branding()

# Add Google Material Icons
st.markdown("""
<link href="https://fonts.googleapis.com/icon?family=Material+Icons" rel="stylesheet">
<style>
.material-icons { vertical-align: middle; margin-right: 8px; }
</style>
""", unsafe_allow_html=True)


def render_mermaid(mermaid_code: str, height: int = 400):
    """Render a Mermaid diagram."""
    html = f"""
    <script src="https://cdn.jsdelivr.net/npm/mermaid/dist/mermaid.min.js"></script>
    <div class="mermaid" style="display: flex; justify-content: center; padding: 10px;">
    {mermaid_code}
    </div>
    <script>
        mermaid.initialize({{ startOnLoad: true, theme: 'default', securityLevel: 'loose' }});
    </script>
    """
    components.html(html, height=height, scrolling=False)


st.markdown('<h1><span class="material-icons">architecture</span> Architecture And Data Flow</h1>', unsafe_allow_html=True)
st.caption("Cloud architecture, Medallion data pipeline, and canonical data model")

# Section 1: Cloud Streaming Architecture
st.markdown('<h2><span class="material-icons">cloud</span> Cloud Streaming Architecture</h2>', unsafe_allow_html=True)
st.markdown("End-to-end data flow from sensors to analytics dashboards using cloud-native components.")

cloud_diagram = """
flowchart TB
    subgraph Sources["Data Sources"]
        TMEIC["TMEIC Controller"]
        BMS["BMS"]
        EMS["ENKA EMS/SCADA"]
        RTM["RTM Settlement"]
        CMMS["ENKA CMMS"]
        FINANCE["Contracts & Finance"]
    end
    subgraph Storage["AWS S3 Data Lake"]
        subgraph Lake["Medallion Architecture"]
            BRONZE["Bronze Layer"]
            SILVER["Silver Layer"]
            GOLD["Gold Layer"]
        end
    end
    subgraph Compute["Databricks"]
        STREAM["Structured Streaming"]
        DELTA["Delta Lake"]
    end
    subgraph Serving["Analytics"]
        API["FastAPI"]
        BI["Streamlit Dashboards"]
    end
    TMEIC -->|Telemetry| BRONZE
    BMS -->|Telemetry| BRONZE
    EMS -->|Events| BRONZE
    RTM -->|Batch| BRONZE
    CMMS -->|Batch| BRONZE
    FINANCE -->|Batch| BRONZE
    BRONZE --> STREAM
    STREAM --> SILVER
    SILVER --> GOLD
    GOLD --> API
    API --> BI
"""
render_mermaid(cloud_diagram, height=1120)

st.markdown("")
col1, col2 = st.columns(2)
with col1:
    st.markdown("**Key Components:**")
    st.markdown("""
- **Data Lake**: AWS S3 (Medallion layers)
- **Compute**: Databricks Structured Streaming
- **Storage Format**: Delta Lake
    """)
with col2:
    st.markdown("**&nbsp;**")
    st.markdown("""
- **Governance**: Unity Catalog
- **API**: FastAPI metrics service
- **Dashboards**: Streamlit
    """)

# Section 2: Medallion Architecture
st.markdown('<h2><span class="material-icons">layers</span> Medallion Architecture</h2>', unsafe_allow_html=True)
st.markdown("Data flows through three progressively refined layers:")

medallion_diagram = """
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
    end
    B1 --> S1
    B2 --> S2
    B3 --> S3
    S1 --> G1
    S1 --> G2
    S2 --> G2
    S3 --> G3
"""
render_mermaid(medallion_diagram, height=550)

st.markdown("")
col1, col2, col3 = st.columns(3)
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
    dim_asset ||--o{ fact_telemetry : has
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
    fact_settlement {
        date date
        string site_id FK
        float revenue_gbp
        float energy_mwh
    }
"""
render_mermaid(data_model_diagram, height=600)

st.markdown("")
st.markdown("""
**Star Schema Design:**
- **Dimensions**: Site, Asset, Service, Partner, SLA
- **Facts**: Telemetry, Dispatch, Events, Settlement, Maintenance
- **Derived KPIs**: Availability, RTE, DoD, Lost Revenue
""")

# Section 4: Data Sources
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
