# BESS Analytics Dashboard

A comprehensive Battery Energy Storage System (BESS) telemetry analytics platform demonstrating dashboards for:
- **ENKA** - Asset Owner/Operator dashboards
- **TMEIC** - Controller/PCS dashboards
- **Combined** - Revenue & SLA tied to controller performance
- **Edge Intelligence** - Advanced signal correction, forecasting, and insights

## Features

- 18 interactive dashboards across 4 dashboard packs
- **Edge Intelligence Engine** - Signal correction, forecasting, balancing, and automated insights
- Synthetic but realistic data generation (30 days, 1-minute resolution, 3 sites, 2 vendors)
- Local DuckDB analytics database
- FastAPI backend with RESTful endpoints
- Streamlit frontend with drill-through capabilities
- Standardized dashboard header component with personas, decisions, data sources, and KPIs

## Architecture

```
bess_analytics/
├── data_gen/          # Synthetic data generation
│   └── generate.py
├── db/                # DuckDB database management
│   └── loader.py
├── api/               # FastAPI backend
│   └── main.py
├── edge/              # Edge Intelligence engines
│   ├── __init__.py
│   ├── signal_correction.py   # SoC/SoE/SoP correction with trust scores
│   ├── forecasting.py         # Time-to-empty/full predictions
│   ├── balancing.py           # Rack imbalance detection
│   └── insights.py            # Automated findings generation
├── dashboard/         # Streamlit frontend
│   ├── Home.py
│   ├── components/
│   │   ├── header.py
│   │   ├── branding.py
│   │   └── kpi_glossary.py
│   └── pages/         # 18 dashboard pages
├── data/              # Generated Parquet files & DuckDB
├── tests/             # Unit tests
├── dashboard_catalog.yaml  # Dashboard metadata
└── requirements.txt
```

## System Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              BESS Analytics Platform                              │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                   │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐                   │
│  │  TMEIC PCS      │  │  BMS            │  │  ENKA EMS       │                   │
│  │  Controller     │  │  Battery Mgmt   │  │  SCADA          │                   │
│  └────────┬────────┘  └────────┬────────┘  └────────┬────────┘                   │
│           │                    │                    │                             │
│           └────────────────────┼────────────────────┘                             │
│                                ▼                                                  │
│  ┌─────────────────────────────────────────────────────────────────────────────┐ │
│  │                         Data Generation Layer                                │ │
│  │  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐        │ │
│  │  │ Telemetry    │ │ Events       │ │ Settlements  │ │ Edge Intel   │        │ │
│  │  │ Generator    │ │ Generator    │ │ Generator    │ │ Generator    │        │ │
│  │  └──────────────┘ └──────────────┘ └──────────────┘ └──────────────┘        │ │
│  └─────────────────────────────────────────────────────────────────────────────┘ │
│                                ▼                                                  │
│  ┌─────────────────────────────────────────────────────────────────────────────┐ │
│  │                         Edge Intelligence Layer                              │ │
│  │  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐        │ │
│  │  │ Signal       │ │ Forecasting  │ │ Balancing    │ │ Insights     │        │ │
│  │  │ Correction   │ │ Engine       │ │ Engine       │ │ Engine       │        │ │
│  │  │ ─────────────│ │ ─────────────│ │ ─────────────│ │ ─────────────│        │ │
│  │  │ • SoC Fix    │ │ • Time2Empty │ │ • Imbalance  │ │ • Auto Find  │        │ │
│  │  │ • SoE Calc   │ │ • Time2Full  │ │ • Cell Delta │ │ • Value Est  │        │ │
│  │  │ • SoP Limits │ │ • Multi-Hrzn │ │ • Actions    │ │ • Priority   │        │ │
│  │  │ • HSL/LSL    │ │ • Confidence │ │ • Recovery   │ │ • Recommend  │        │ │
│  │  │ • Trust Score│ │              │ │              │ │              │        │ │
│  │  └──────────────┘ └──────────────┘ └──────────────┘ └──────────────┘        │ │
│  └─────────────────────────────────────────────────────────────────────────────┘ │
│                                ▼                                                  │
│  ┌─────────────────────────────────────────────────────────────────────────────┐ │
│  │                         Storage Layer (DuckDB)                               │ │
│  │  ┌────────────┐  ┌────────────┐  ┌────────────┐  ┌────────────┐             │ │
│  │  │ Dimensions │  │ Facts      │  │ Edge Intel │  │ Gold Aggs  │             │ │
│  │  │ • dim_site │  │ • telemetry│  │ • signals  │  │ • 15min    │             │ │
│  │  │ • dim_asset│  │ • dispatch │  │ • forecasts│  │ • daily    │             │ │
│  │  │ • dim_sla  │  │ • events   │  │ • imbalance│  │ • monthly  │             │ │
│  │  │            │  │ • settle   │  │ • insights │  │            │             │ │
│  │  └────────────┘  └────────────┘  └────────────┘  └────────────┘             │ │
│  └─────────────────────────────────────────────────────────────────────────────┘ │
│                                ▼                                                  │
│  ┌─────────────────────────────────────────────────────────────────────────────┐ │
│  │                         API Layer (FastAPI)                                  │ │
│  │  /sites  /metrics  /edge/signals  /edge/forecasts  /edge/insights           │ │
│  └─────────────────────────────────────────────────────────────────────────────┘ │
│                                ▼                                                  │
│  ┌─────────────────────────────────────────────────────────────────────────────┐ │
│  │                         Dashboard Layer (Streamlit)                          │ │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────────┐             │ │
│  │  │ ENKA     │  │ TMEIC    │  │ Combined │  │ Edge Intelligence│             │ │
│  │  │ (5 pages)│  │ (5 pages)│  │ (4 pages)│  │ (4 pages)        │             │ │
│  │  └──────────┘  └──────────┘  └──────────┘  └──────────────────┘             │ │
│  └─────────────────────────────────────────────────────────────────────────────┘ │
│                                                                                   │
└─────────────────────────────────────────────────────────────────────────────────┘
```

## Data Flow Diagram

```
                                    DATA FLOW
                                    ─────────

    ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
    │   BMS Raw   │     │ TMEIC PCS   │     │  Market     │
    │   Signals   │     │  Telemetry  │     │  Prices     │
    └──────┬──────┘     └──────┬──────┘     └──────┬──────┘
           │                   │                   │
           ▼                   ▼                   ▼
    ┌────────────────────────────────────────────────────┐
    │              fact_telemetry (2M+ rows)             │
    │    p_kw, soc_pct, soh_pct, temp_c, voltage_v       │
    └────────────────────────────────────────────────────┘
           │
           ├──────────────────────────────────────────────┐
           │                                              │
           ▼                                              ▼
    ┌────────────────────┐                    ┌────────────────────┐
    │  Signal Correction │                    │  Cell Telemetry    │
    │      Engine        │                    │  (Rack Level)      │
    └─────────┬──────────┘                    └─────────┬──────────┘
              │                                         │
              ▼                                         ▼
    ┌────────────────────┐                    ┌────────────────────┐
    │ fact_corrected_    │                    │   Balancing        │
    │ signals            │                    │   Engine           │
    │ ─────────────────  │                    └─────────┬──────────┘
    │ • soc_corrected    │                              │
    │ • soe_mwh          │                              ▼
    │ • sop_charge/dis   │                    ┌────────────────────┐
    │ • hsl/lsl limits   │                    │ fact_imbalance     │
    │ • trust_score      │                    │ fact_balancing_    │
    └─────────┬──────────┘                    │ actions            │
              │                               └────────────────────┘
              │
              ├────────────────────┐
              │                    │
              ▼                    ▼
    ┌────────────────────┐  ┌────────────────────┐
    │  Forecasting       │  │  Insights          │
    │  Engine            │  │  Engine            │
    └─────────┬──────────┘  └─────────┬──────────┘
              │                       │
              ▼                       ▼
    ┌────────────────────┐  ┌────────────────────┐
    │ fact_forecasts     │  │ fact_insights_     │
    │ ─────────────────  │  │ findings           │
    │ • predicted_soc    │  │ ─────────────────  │
    │ • time_to_empty    │  │ • category         │
    │ • time_to_full     │  │ • severity         │
    │ • available_energy │  │ • value_impact     │
    │ • confidence       │  │ • recommendation   │
    └────────────────────┘  └────────────────────┘
              │                       │
              └───────────┬───────────┘
                          │
                          ▼
              ┌────────────────────────┐
              │   Dashboard Views      │
              │   API Endpoints        │
              └────────────────────────┘
```

## Data Model

### Dimensions
- `dim_site` - Site information (location, capacity, vendor)
- `dim_asset` - Assets (controllers, inverters, battery racks)
- `dim_service` - Market services (arbitrage, FFR, reserve, capacity)
- `dim_partner` - Revenue share partners
- `dim_sla` - SLA definitions and thresholds

### Core Facts
- `fact_telemetry` - 1-minute time series (power, SOC, SOH, temperature, comms)
- `fact_dispatch` - Dispatch commands and actuals
- `fact_events` - Faults, trips, comms drops, maintenance
- `fact_settlement` - Daily market settlements
- `fact_maintenance` - Maintenance tickets
- `fact_data_quality` - Hourly data completeness metrics
- `forecast_revenue` - Revenue forecasts for loss attribution
- `projects_pipeline` - Development pipeline (mock)

### Edge Intelligence Facts
- `fact_corrected_signals` - Corrected SoC/SoE/SoP with trust scores and HSL/LSL limits
- `fact_constraints` - Active power/energy constraints with severity
- `fact_cell_telemetry` - Cell-level voltage and temperature data
- `fact_imbalance` - Rack imbalance scores and cell deltas
- `fact_balancing_actions` - Recommended balancing actions with priority
- `fact_forecasts` - Multi-horizon energy/power availability predictions
- `fact_insights_findings` - Automated findings with value impact estimation

### Telemetry Tags

**Controller Tags:**
- `p_kw`, `q_kvar`, `v_pu`, `f_hz`
- `controller_status`, `comms_latency_ms`, `comms_drop_rate`
- `inverter_efficiency_pct`, `cooling_status`

**Battery Tags:**
- `soc_pct`, `soh_pct`, `temp_c_avg`, `temp_c_max`
- `voltage_v`, `current_a`, `cycle_count`

## Upstream Systems (Mocked)

| System | Description |
|--------|-------------|
| TMEIC Controller (PCS/Plant Control) | Primary telemetry and event source |
| BMS (Battery Management System) | Battery-level telemetry |
| ENKA EMS/SCADA | Dispatch commands and site status |
| RTM / Market Settlement Provider | Settlement and price data |
| ENKA CMMS | Maintenance tickets |
| Contracts & Finance | Partner agreements and SLA terms |

## Dashboard Catalog

### ENKA Dashboards
1. **Portfolio Executive Cockpit** - CEO/CFO portfolio overview (includes Signal Trust Score)
2. **Partner Monetization & Revenue Share** - Partner payouts and SLA
3. **RTM/Market Settlement Reconciliation** - Settlement verification
4. **Lifecycle & Augmentation Planning** - Battery health and planning
5. **Development Pipeline & Deployment Tracking** - Project status

### TMEIC Dashboards
6. **PCS/Controller Real-time Ops** - Live monitoring
7. **Controller Health & Comms** - Communication health
8. **Faults/Trips Timeline** - Event tracking and MTTR
9. **Grid Code Performance** - Compliance metrics
10. **Historian Explorer** - Data exploration and export

### Combined Dashboards
11. **Revenue Loss Attribution** - Loss root cause analysis
12. **Dispatch vs Asset Stress** - Degradation vs revenue tradeoff
13. **SLA & Warranty Evidence Pack** - Compliance documentation
14. **Portfolio Benchmarking by Vendor** - Vendor comparison

### Edge Intelligence Dashboards
15. **Signal Fidelity & SCADA Replacement** - Corrected signals, trust scores, raw vs corrected SoC, HSL/LSL bands
16. **Predictive Energy & Power Availability** - Time-to-empty/full forecasts, multi-horizon predictions, constraints
17. **Balancing & Imbalance Optimization** - Rack imbalance detection, cell deltas, balancing action queue
18. **Insights Report & Recommendations** - Automated findings, value-at-risk, prioritized recommendations

## Quick Start

### Prerequisites
- Python 3.11+
- pip

### Installation

```bash
# Clone or navigate to the project directory
cd bess_analytics

# Create virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Generate Data

```bash
# Generate synthetic data (30 days, 3 sites)
python -m data_gen.generate
```

This creates Parquet files in `data/` and takes ~1-2 minutes.

### Load Database

```bash
# Initialize DuckDB and create views
python -m db.loader
```

### Run API Server

```bash
# Start FastAPI backend on port 8000
uvicorn api.main:app --reload
```

API docs available at: http://localhost:8000/docs

### Run Dashboard

```bash
# Start Streamlit dashboard
streamlit run dashboard/Home.py
```

Dashboard available at: http://localhost:8501

## API Endpoints

### Core Endpoints
| Endpoint | Description |
|----------|-------------|
| `GET /sites` | List all sites |
| `GET /sites/{site_id}` | Site details with latest telemetry |
| `GET /metrics/portfolio` | Portfolio-level KPIs |
| `GET /metrics/site/{site_id}` | Site-level metrics |
| `GET /metrics/revenue` | Revenue by site/service/period |
| `GET /metrics/revenue_loss` | Loss attribution |
| `GET /metrics/events` | Event records with filters |
| `GET /metrics/sla_report` | SLA compliance status |
| `GET /metrics/telemetry` | Telemetry data export |
| `GET /metrics/data_quality` | Data completeness metrics |
| `GET /metrics/battery_health` | SOH/SOC trends |
| `GET /metrics/dispatch` | Dispatch commands |
| `GET /metrics/vendor_benchmark` | Vendor comparison |
| `GET /metrics/pipeline` | Project pipeline |

### Edge Intelligence Endpoints
| Endpoint | Description |
|----------|-------------|
| `GET /edge/corrected_signals` | Corrected signals with filters |
| `GET /edge/latest_signals` | Latest corrected signal per site |
| `GET /edge/signal_health` | Signal health summary by site |
| `GET /edge/constraints` | Active power/energy constraints |
| `GET /edge/forecasts` | Energy/power forecasts |
| `GET /edge/imbalance` | Rack imbalance data |
| `GET /edge/balancing_actions` | Recommended balancing actions |
| `GET /edge/insights` | Automated findings |
| `GET /edge/value_at_risk` | Total value at risk summary |

## Dashboard Header Component

Every dashboard uses the standardized header component:

```python
from dashboard.components.header import render_header

render_header(
    title="Dashboard Title",
    personas=["CEO", "CFO", "Asset Manager"],
    decisions=[
        "Allocate capex for augmentation",
        "Prioritize underperforming sites"
    ],
    data_sources=[
        {"system": "TMEIC Controller", "tables": ["fact_telemetry"], "notes": "Real-time power data"}
    ],
    freshness="Daily for financial; 1-5 min for operational",
    kpis=[
        {"label": "Revenue MTD", "value": 125000, "format": "currency"},
        {"label": "Availability", "value": 96.5, "format": "percent"}
    ]
)
```

## Configuration

Dashboard metadata is stored in `dashboard_catalog.yaml`. Each dashboard defines:
- Title and pack (ENKA/TMEIC/Combined)
- Personas and decisions
- Data sources with tables
- Data freshness
- KPI definitions

## Generated Data Characteristics

### Sites
| Site | Vendor | Capacity | Characteristics |
|------|--------|----------|-----------------|
| Cotswold Energy Park | TMEIC | 50MW/100MWh | Baseline performance |
| Thames Gateway Storage | TMEIC | 40MW/80MWh | Higher comms issues |
| Yorkshire Wind-Storage | OtherPCS | 30MW/60MWh | Faster degradation, repeated faults |

### Data Patterns
- Daily price cycles (evening peak, night trough)
- Realistic charge/discharge behavior
- Occasional faults (few per month)
- Comms drops (random, site-specific rates)
- Gradual SOH degradation

### Edge Intelligence Data
- **Corrected Signals**: 25,920 records (1-min resolution, 3 sites, 30 days)
- **Forecasts**: 10,800 records (5 horizons × 3 sites × hourly)
- **Imbalance**: 34,560 rack-level readings
- **Insights**: ~30 automated findings with value impact

## Development

### Running Tests

```bash
pytest tests/
```

### Code Structure

- **data_gen/generate.py** - Synthetic data generators
- **db/loader.py** - DuckDB loading and view creation
- **api/main.py** - FastAPI endpoints
- **dashboard/components/header.py** - Reusable header component
- **dashboard/pages/*.py** - Individual dashboard pages

## Assumptions & Limitations

1. **Synthetic Data**: All data is generated and may not reflect real-world distributions
2. **Single Instance**: Designed for local single-user demo
3. **No Authentication**: No user authentication implemented
4. **Fixed Date Range**: Data is generated for a fixed 30-day period ending 2024-03-15
5. **Simplified Settlements**: Market settlement logic is simplified
6. **Mock Pipeline**: Project pipeline data is static

## Technology Stack

- **Database**: DuckDB (embedded analytical database)
- **API**: FastAPI (Python web framework)
- **Frontend**: Streamlit (Python dashboard framework)
- **Charts**: Plotly (interactive visualizations)
- **Data**: Pandas, PyArrow, NumPy

## Edge Intelligence

The Edge Intelligence module provides advanced battery analytics capabilities:

### Signal Correction Engine
Corrects BMS-reported State of Charge using cell-level analysis:
- **SoC Correction**: Compares BMS SoC with cell voltage-derived estimates
- **SoE (State of Energy)**: Usable energy in MWh within safety limits
- **SoP (State of Power)**: Real-time charge/discharge limits
- **HSL/LSL Bands**: Temperature-adjusted high/low safety limits
- **Trust Score (0-100)**: Confidence in corrected values

### Forecasting Engine
Predicts energy availability at multiple time horizons:
- **Time-to-Empty**: Minutes until minimum operational SoC
- **Time-to-Full**: Minutes until maximum operational SoC
- **Multi-Horizon**: 15, 30, 60, 120, 240 minute forecasts
- **Confidence Scores**: Decreasing with longer horizons

### Balancing Engine
Detects and prioritizes cell/rack imbalances:
- **Imbalance Score (0-100)**: Combined voltage and temperature delta analysis
- **Cell Delta Detection**: Voltage >50mV warning, >100mV critical
- **Temperature Delta**: >5°C warning, >10°C critical
- **Action Queue**: Prioritized balancing recommendations with recovery estimates

### Insights Engine
Generates automated findings with value impact:
- **Categories**: signal_quality, energy_availability, power_constraints, cell_imbalance, thermal
- **Severity Levels**: critical, alert, warning, info
- **Value Estimation**: Potential revenue impact in GBP
- **Recommendations**: Actionable next steps

## License

This is a demo project for educational and evaluation purposes.
