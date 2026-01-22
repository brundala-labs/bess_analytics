"""
Architecture And Data Flow

Cloud architecture, Medallion data pipeline, and canonical data model documentation.
"""

import sys
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from dashboard.components.branding import apply_enka_theme, render_sidebar_branding, render_footer, ENKA_GREEN

st.set_page_config(page_title="Architecture And Data Flow", page_icon="🏗️", layout="wide")

apply_enka_theme()
render_sidebar_branding()


def render_mermaid(mermaid_code: str, height: int = 400):
    """Render a Mermaid diagram."""
    html = f"""
    <script src="https://cdn.jsdelivr.net/npm/mermaid/dist/mermaid.min.js"></script>
    <div class="mermaid" style="display: flex; justify-content: center;">
    {mermaid_code}
    </div>
    <script>
        mermaid.initialize({{ startOnLoad: true, theme: 'default' }});
    </script>
    """
    components.html(html, height=height)


def main():
    st.title("🏗️ Architecture And Data Flow")
    st.caption("Cloud architecture, Medallion data pipeline, and canonical data model")

    # Section 1: Cloud Streaming Architecture
    st.header("☁️ Cloud Streaming Architecture")
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
    """
    render_mermaid(cloud_diagram, height=500)

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**Key Components:**")
        st.markdown("""
- **Streaming Bus**: Kafka / Event Hubs / Kinesis / Pub/Sub
- **Data Lake**: S3 / ADLS / GCS (Medallion layers)
- **Compute**: Databricks Structured Streaming
        """)
    with col2:
        st.markdown("**&nbsp;**")
        st.markdown("""
- **Governance**: Unity Catalog
- **API**: FastAPI metrics service
- **Dashboards**: Streamlit
        """)

    # Section 2: Medallion Architecture
    st.header("🏅 Medallion Architecture")
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
    render_mermaid(medallion_diagram, height=300)

    col1, col2, col3 = st.columns(3)
    with col1:
        with st.container(border=True):
            st.markdown(f"**Bronze (Raw)**")
            st.caption("As-received, append-only")
            st.markdown("telemetry/, events/, settlement/")
    with col2:
        with st.container(border=True):
            st.markdown(f"**Silver (Cleaned)**")
            st.caption("Canonical schema, validated")
            st.markdown("fact_*, dim_*")
    with col3:
        with st.container(border=True):
            st.markdown(f"**Gold (Curated)**")
            st.caption("KPI tables, rollups")
            st.markdown("agg_*, v_*")

    # Section 3: Canonical Data Model
    st.header("📊 Canonical Data Model")

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
    render_mermaid(data_model_diagram, height=400)

    st.markdown("""
    **Star Schema Design:**
    - **Dimensions**: Site, Asset, Service, Partner, SLA
    - **Facts**: Telemetry, Dispatch, Events, Settlement, Maintenance
    - **Derived KPIs**: Availability, RTE, DoD, Lost Revenue
    """)

    # Section 4: Data Sources
    st.header("📡 Upstream Data Sources")

    sources = [
        ("TMEIC Controller", "Streaming", "1-min", "p_kw, q_kvar, v_pu, f_hz"),
        ("BMS", "Streaming", "1-min", "soc_pct, soh_pct, temp_c"),
        ("ENKA EMS/SCADA", "Streaming", "1-min", "command_kw, setpoint_kw"),
        ("RTM Settlement", "Batch", "Daily", "revenue_gbp, energy_mwh"),
        ("ENKA CMMS", "Batch", "On-event", "ticket_id, resolution"),
        ("Contracts & Finance", "Batch", "On-change", "revenue_share_pct"),
    ]

    cols = st.columns(3)
    for idx, (name, stype, freq, tags) in enumerate(sources):
        with cols[idx % 3]:
            with st.container(border=True):
                st.markdown(f"**{name}**")
                st.caption(f"{stype} | {freq}")
                st.code(tags, language=None)

    render_footer()


main()
