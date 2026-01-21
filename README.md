# BESS Analytics Dashboard

A comprehensive Battery Energy Storage System (BESS) telemetry analytics platform demonstrating dashboards for:
- **ENKA** - Asset Owner/Operator dashboards
- **TMEIC** - Controller/PCS dashboards
- **Combined** - Revenue & SLA tied to controller performance

## Features

- 14 interactive dashboards across 3 dashboard packs
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
├── dashboard/         # Streamlit frontend
│   ├── Home.py
│   ├── components/
│   │   └── header.py
│   └── pages/         # 14 dashboard pages
├── data/              # Generated Parquet files & DuckDB
├── tests/             # Unit tests
├── dashboard_catalog.yaml  # Dashboard metadata
└── requirements.txt
```

## Data Model

### Dimensions
- `dim_site` - Site information (location, capacity, vendor)
- `dim_asset` - Assets (controllers, inverters, battery racks)
- `dim_service` - Market services (arbitrage, FFR, reserve, capacity)
- `dim_partner` - Revenue share partners
- `dim_sla` - SLA definitions and thresholds

### Facts
- `fact_telemetry` - 1-minute time series (power, SOC, SOH, temperature, comms)
- `fact_dispatch` - Dispatch commands and actuals
- `fact_events` - Faults, trips, comms drops, maintenance
- `fact_settlement` - Daily market settlements
- `fact_maintenance` - Maintenance tickets
- `fact_data_quality` - Hourly data completeness metrics
- `forecast_revenue` - Revenue forecasts for loss attribution
- `projects_pipeline` - Development pipeline (mock)

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
1. **Portfolio Executive Cockpit** - CEO/CFO portfolio overview
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

## License

This is a demo project for educational and evaluation purposes.
