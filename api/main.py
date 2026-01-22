"""
BESS Analytics - FastAPI Backend

Provides REST API endpoints for dashboard metrics and drilldowns.
"""

from datetime import date, datetime
from pathlib import Path
from typing import Any, Optional

import duckdb
import pandas as pd
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger
from pydantic import BaseModel

# Initialize app
app = FastAPI(
    title="BESS Analytics API",
    description="API for Battery Energy Storage System telemetry and analytics",
    version="1.0.0",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Database path
DATA_DIR = Path(__file__).parent.parent / "data"
DB_PATH = DATA_DIR / "bess_analytics.duckdb"


def get_db() -> duckdb.DuckDBPyConnection:
    """Get database connection."""
    return duckdb.connect(str(DB_PATH), read_only=True)


# ============== Response Models ==============

class SiteInfo(BaseModel):
    site_id: str
    name: str
    country: str
    bess_mw: float
    bess_mwh: float
    vendor_controller: str


class PortfolioMetrics(BaseModel):
    total_sites: int
    total_mw: float
    total_mwh: float
    revenue_mtd: float
    avg_availability_pct: float
    active_faults: int
    avg_soh_pct: float
    sites_below_target: int


class SiteMetrics(BaseModel):
    site_id: str
    name: str
    current_power_kw: Optional[float]
    current_soc_pct: Optional[float]
    current_soh_pct: Optional[float]
    availability_pct: Optional[float]
    revenue_mtd: float
    active_events: int


class EventRecord(BaseModel):
    event_id: str
    site_id: str
    asset_id: str
    start_ts: datetime
    end_ts: Optional[datetime]
    severity: str
    event_type: str
    code: str
    description: str


class RevenueLossRecord(BaseModel):
    date: date
    site_id: str
    site_name: str
    forecast_revenue: float
    actual_revenue: float
    revenue_gap: float
    loss_category: str


class SLAReport(BaseModel):
    sla_id: str
    site_id: str
    site_name: str
    metric_name: str
    threshold: float
    actual_value: Optional[float]
    status: str
    penalty_exposure: float


# ============== API Endpoints ==============

@app.get("/")
def root():
    """API root endpoint."""
    return {"message": "BESS Analytics API", "version": "1.0.0"}


@app.get("/health")
def health_check():
    """Health check endpoint."""
    try:
        conn = get_db()
        conn.execute("SELECT 1").fetchone()
        conn.close()
        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}


# ============== Sites ==============

@app.get("/sites", response_model=list[SiteInfo])
def get_sites():
    """Get all sites."""
    conn = get_db()
    df = conn.execute("""
        SELECT site_id, name, country, bess_mw, bess_mwh, vendor_controller
        FROM dim_site
    """).df()
    conn.close()
    return df.to_dict(orient="records")


@app.get("/sites/{site_id}")
def get_site(site_id: str):
    """Get site details with latest telemetry."""
    conn = get_db()
    result = conn.execute("""
        SELECT * FROM v_site_latest_telemetry
        WHERE site_id = ?
    """, [site_id]).df()
    conn.close()

    if result.empty:
        raise HTTPException(status_code=404, detail="Site not found")

    return result.iloc[0].to_dict()


# ============== Portfolio Metrics ==============

@app.get("/metrics/portfolio", response_model=PortfolioMetrics)
def get_portfolio_metrics(
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
):
    """Get portfolio-level metrics."""
    conn = get_db()

    # Sites summary
    sites = conn.execute("SELECT COUNT(*) as cnt, SUM(bess_mw) as mw, SUM(bess_mwh) as mwh FROM dim_site").fetchone()

    # Revenue MTD
    revenue_query = """
        SELECT COALESCE(SUM(revenue_gbp), 0) as revenue
        FROM fact_settlement
        WHERE date >= DATE_TRUNC('month', (SELECT MAX(date) FROM fact_settlement))
    """
    revenue = conn.execute(revenue_query).fetchone()[0]

    # Average availability
    availability = conn.execute("""
        SELECT AVG(availability_pct)
        FROM v_site_availability
        WHERE date >= (SELECT MAX(date) FROM v_site_availability) - INTERVAL '7 days'
    """).fetchone()[0] or 0

    # Active faults
    active_faults = conn.execute("""
        SELECT COUNT(*)
        FROM fact_events
        WHERE event_type IN ('fault', 'trip')
        AND end_ts > (SELECT MAX(ts) FROM fact_telemetry) - INTERVAL '1 hour'
    """).fetchone()[0]

    # Average SOH
    avg_soh = conn.execute("""
        SELECT AVG(avg_soh)
        FROM v_battery_health
        WHERE date = (SELECT MAX(date) FROM v_battery_health)
    """).fetchone()[0] or 0

    # Sites below availability target (95%)
    below_target = conn.execute("""
        SELECT COUNT(DISTINCT site_id)
        FROM v_site_availability
        WHERE date >= (SELECT MAX(date) FROM v_site_availability) - INTERVAL '7 days'
        GROUP BY site_id
        HAVING AVG(availability_pct) < 95
    """).fetchone()
    below_target_count = below_target[0] if below_target else 0

    conn.close()

    return PortfolioMetrics(
        total_sites=sites[0],
        total_mw=sites[1] or 0,
        total_mwh=sites[2] or 0,
        revenue_mtd=revenue,
        avg_availability_pct=availability,
        active_faults=active_faults,
        avg_soh_pct=avg_soh,
        sites_below_target=below_target_count,
    )


@app.get("/metrics/site/{site_id}", response_model=SiteMetrics)
def get_site_metrics(site_id: str):
    """Get site-level metrics."""
    conn = get_db()

    # Site info
    site = conn.execute("SELECT site_id, name FROM dim_site WHERE site_id = ?", [site_id]).fetchone()
    if not site:
        conn.close()
        raise HTTPException(status_code=404, detail="Site not found")

    # Latest telemetry
    latest = conn.execute("""
        SELECT
            MAX(CASE WHEN tag = 'p_kw' THEN value END) as power,
            MAX(CASE WHEN tag = 'soc_pct' THEN value END) as soc,
            MAX(CASE WHEN tag = 'soh_pct' THEN value END) as soh
        FROM (
            SELECT tag, value
            FROM fact_telemetry
            WHERE site_id = ?
            ORDER BY ts DESC
            LIMIT 100
        )
    """, [site_id]).fetchone()

    # Availability (last 7 days)
    avail = conn.execute("""
        SELECT AVG(availability_pct)
        FROM v_site_availability
        WHERE site_id = ?
        AND date >= (SELECT MAX(date) FROM v_site_availability) - INTERVAL '7 days'
    """, [site_id]).fetchone()[0]

    # Revenue MTD
    revenue = conn.execute("""
        SELECT COALESCE(SUM(revenue_gbp), 0)
        FROM fact_settlement
        WHERE site_id = ?
        AND date >= DATE_TRUNC('month', (SELECT MAX(date) FROM fact_settlement))
    """, [site_id]).fetchone()[0]

    # Active events
    active_events = conn.execute("""
        SELECT COUNT(*)
        FROM fact_events
        WHERE site_id = ?
        AND (end_ts > (SELECT MAX(ts) FROM fact_telemetry) OR end_ts IS NULL)
    """, [site_id]).fetchone()[0]

    conn.close()

    return SiteMetrics(
        site_id=site[0],
        name=site[1],
        current_power_kw=latest[0],
        current_soc_pct=latest[1],
        current_soh_pct=latest[2],
        availability_pct=avail,
        revenue_mtd=revenue,
        active_events=active_events,
    )


# ============== Revenue ==============

@app.get("/metrics/revenue")
def get_revenue_metrics(
    site_id: Optional[str] = Query(None),
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    group_by: str = Query("day", regex="^(day|week|month)$"),
):
    """Get revenue metrics with optional filtering."""
    conn = get_db()

    date_trunc = {
        "day": "DATE_TRUNC('day', date)",
        "week": "DATE_TRUNC('week', date)",
        "month": "DATE_TRUNC('month', date)",
    }[group_by]

    query = f"""
        SELECT
            {date_trunc} as period,
            site_id,
            SUM(revenue_gbp) as revenue,
            SUM(energy_mwh) as energy_mwh,
            AVG(avg_price_gbp_per_mwh) as avg_price
        FROM fact_settlement
        WHERE 1=1
    """
    params = []

    if site_id:
        query += " AND site_id = ?"
        params.append(site_id)
    if start_date:
        query += " AND date >= ?"
        params.append(start_date)
    if end_date:
        query += " AND date <= ?"
        params.append(end_date)

    query += f" GROUP BY {date_trunc}, site_id ORDER BY period"

    df = conn.execute(query, params).df()
    conn.close()

    return df.to_dict(orient="records")


@app.get("/metrics/revenue_loss")
def get_revenue_loss(
    site_id: Optional[str] = Query(None),
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
):
    """Get revenue loss attribution."""
    conn = get_db()

    query = """
        SELECT
            date,
            site_id,
            site_name,
            forecast_revenue,
            actual_revenue,
            revenue_gap,
            fault_minutes,
            trip_minutes,
            data_completeness
        FROM v_revenue_loss_attribution
        WHERE 1=1
    """
    params = []

    if site_id:
        query += " AND site_id = ?"
        params.append(site_id)
    if start_date:
        query += " AND date >= ?"
        params.append(start_date)
    if end_date:
        query += " AND date <= ?"
        params.append(end_date)

    query += " ORDER BY date DESC"

    df = conn.execute(query, params).df()
    conn.close()

    # Categorize losses
    records = []
    for _, row in df.iterrows():
        loss_category = "Other"
        if row["fault_minutes"] > 30:
            loss_category = "Faults/Trips"
        elif row["data_completeness"] < 95:
            loss_category = "Data Gaps"
        elif row["revenue_gap"] > 0:
            loss_category = "Market Conditions"

        records.append({
            "date": row["date"],
            "site_id": row["site_id"],
            "site_name": row["site_name"],
            "forecast_revenue": row["forecast_revenue"],
            "actual_revenue": row["actual_revenue"],
            "revenue_gap": row["revenue_gap"],
            "loss_category": loss_category,
        })

    return records


# ============== Events ==============

@app.get("/metrics/events")
def get_events(
    site_id: Optional[str] = Query(None),
    event_type: Optional[str] = Query(None),
    severity: Optional[str] = Query(None),
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    limit: int = Query(100, le=1000),
):
    """Get event records with filtering."""
    conn = get_db()

    query = """
        SELECT
            event_id, site_id, asset_id,
            start_ts, end_ts, severity, event_type, code, description
        FROM fact_events
        WHERE 1=1
    """
    params = []

    if site_id:
        query += " AND site_id = ?"
        params.append(site_id)
    if event_type:
        query += " AND event_type = ?"
        params.append(event_type)
    if severity:
        query += " AND severity = ?"
        params.append(severity)
    if start_date:
        query += " AND start_ts >= ?"
        params.append(datetime.combine(start_date, datetime.min.time()))
    if end_date:
        query += " AND start_ts <= ?"
        params.append(datetime.combine(end_date, datetime.max.time()))

    query += f" ORDER BY start_ts DESC LIMIT {limit}"

    df = conn.execute(query, params).df()
    conn.close()

    return df.to_dict(orient="records")


@app.get("/metrics/event_summary")
def get_event_summary(
    site_id: Optional[str] = Query(None),
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
):
    """Get event summary statistics."""
    conn = get_db()

    query = """
        SELECT
            site_id,
            event_type,
            severity,
            COUNT(*) as count,
            AVG(EXTRACT(EPOCH FROM (end_ts - start_ts)) / 60) as avg_duration_min
        FROM fact_events
        WHERE 1=1
    """
    params = []

    if site_id:
        query += " AND site_id = ?"
        params.append(site_id)
    if start_date:
        query += " AND start_ts >= ?"
        params.append(datetime.combine(start_date, datetime.min.time()))
    if end_date:
        query += " AND start_ts <= ?"
        params.append(datetime.combine(end_date, datetime.max.time()))

    query += " GROUP BY site_id, event_type, severity ORDER BY count DESC"

    df = conn.execute(query, params).df()
    conn.close()

    return df.to_dict(orient="records")


# ============== SLA ==============

@app.get("/metrics/sla_report")
def get_sla_report(site_id: Optional[str] = Query(None)):
    """Get SLA compliance report."""
    conn = get_db()

    query = """
        SELECT
            sla_id,
            site_id,
            site_name,
            metric_name,
            threshold,
            actual_value,
            status,
            CASE
                WHEN status = 'BREACH' THEN penalty_rate_per_hour * 24
                ELSE 0
            END as penalty_exposure
        FROM v_sla_compliance
        WHERE 1=1
    """
    params = []

    if site_id:
        query += " AND site_id = ?"
        params.append(site_id)

    df = conn.execute(query, params).df()
    conn.close()

    return df.to_dict(orient="records")


# ============== Telemetry ==============

@app.get("/metrics/telemetry")
def get_telemetry(
    site_id: str = Query(...),
    tags: str = Query(..., description="Comma-separated tag names"),
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    resolution: str = Query("1min", regex="^(1min|5min|15min|1hour|1day)$"),
):
    """Get telemetry data for specified tags."""
    conn = get_db()

    tag_list = [t.strip() for t in tags.split(",")]
    tag_placeholders = ",".join(["?" for _ in tag_list])

    # Resolution mapping
    resolutions = {
        "1min": "ts",
        "5min": "DATE_TRUNC('minute', ts) - INTERVAL '1 minute' * (EXTRACT(MINUTE FROM ts)::INT % 5)",
        "15min": "DATE_TRUNC('minute', ts) - INTERVAL '1 minute' * (EXTRACT(MINUTE FROM ts)::INT % 15)",
        "1hour": "DATE_TRUNC('hour', ts)",
        "1day": "DATE_TRUNC('day', ts)",
    }
    time_bucket = resolutions[resolution]

    query = f"""
        SELECT
            {time_bucket} as ts,
            tag,
            AVG(value) as value
        FROM fact_telemetry
        WHERE site_id = ?
        AND tag IN ({tag_placeholders})
    """
    params = [site_id] + tag_list

    if start_date:
        query += " AND ts >= ?"
        params.append(datetime.combine(start_date, datetime.min.time()))
    if end_date:
        query += " AND ts <= ?"
        params.append(datetime.combine(end_date, datetime.max.time()))

    query += f" GROUP BY {time_bucket}, tag ORDER BY ts"

    df = conn.execute(query, params).df()
    conn.close()

    # Pivot to wide format
    if not df.empty:
        df_pivot = df.pivot(index="ts", columns="tag", values="value").reset_index()
        return df_pivot.to_dict(orient="records")

    return []


@app.get("/metrics/data_quality")
def get_data_quality(
    site_id: Optional[str] = Query(None),
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
):
    """Get data quality metrics."""
    conn = get_db()

    query = """
        SELECT
            site_id,
            date,
            avg_completeness,
            min_completeness,
            total_missing_tags
        FROM v_data_quality_daily
        WHERE 1=1
    """
    params = []

    if site_id:
        query += " AND site_id = ?"
        params.append(site_id)
    if start_date:
        query += " AND date >= ?"
        params.append(start_date)
    if end_date:
        query += " AND date <= ?"
        params.append(end_date)

    query += " ORDER BY date DESC"

    df = conn.execute(query, params).df()
    conn.close()

    return df.to_dict(orient="records")


# ============== Battery Health ==============

@app.get("/metrics/battery_health")
def get_battery_health(
    site_id: Optional[str] = Query(None),
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
):
    """Get battery health metrics."""
    conn = get_db()

    query = """
        SELECT
            site_id,
            date,
            avg_soh,
            avg_soc,
            avg_temp,
            max_temp,
            cycle_count
        FROM v_battery_health
        WHERE 1=1
    """
    params = []

    if site_id:
        query += " AND site_id = ?"
        params.append(site_id)
    if start_date:
        query += " AND date >= ?"
        params.append(start_date)
    if end_date:
        query += " AND date <= ?"
        params.append(end_date)

    query += " ORDER BY date"

    df = conn.execute(query, params).df()
    conn.close()

    return df.to_dict(orient="records")


# ============== Dispatch ==============

@app.get("/metrics/dispatch")
def get_dispatch_metrics(
    site_id: Optional[str] = Query(None),
    service_id: Optional[str] = Query(None),
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
):
    """Get dispatch data."""
    conn = get_db()

    query = """
        SELECT
            DATE_TRUNC('hour', ts) as hour,
            site_id,
            service_id,
            AVG(command_kw) as avg_command_kw,
            AVG(actual_kw) as avg_actual_kw,
            COUNT(*) as dispatch_count
        FROM fact_dispatch
        WHERE 1=1
    """
    params = []

    if site_id:
        query += " AND site_id = ?"
        params.append(site_id)
    if service_id:
        query += " AND service_id = ?"
        params.append(service_id)
    if start_date:
        query += " AND ts >= ?"
        params.append(datetime.combine(start_date, datetime.min.time()))
    if end_date:
        query += " AND ts <= ?"
        params.append(datetime.combine(end_date, datetime.max.time()))

    query += " GROUP BY DATE_TRUNC('hour', ts), site_id, service_id ORDER BY hour"

    df = conn.execute(query, params).df()
    conn.close()

    return df.to_dict(orient="records")


@app.get("/metrics/dispatch_compliance")
def get_dispatch_compliance(
    site_id: Optional[str] = Query(None),
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
):
    """Get dispatch compliance metrics."""
    conn = get_db()

    query = """
        SELECT
            site_id,
            date,
            dispatch_count,
            compliance_pct,
            total_deviation_mw
        FROM v_dispatch_compliance
        WHERE 1=1
    """
    params = []

    if site_id:
        query += " AND site_id = ?"
        params.append(site_id)
    if start_date:
        query += " AND date >= ?"
        params.append(start_date)
    if end_date:
        query += " AND date <= ?"
        params.append(end_date)

    query += " ORDER BY date DESC"

    df = conn.execute(query, params).df()
    conn.close()

    return df.to_dict(orient="records")


# ============== Partners ==============

@app.get("/metrics/partner_revenue")
def get_partner_revenue(
    partner_id: Optional[str] = Query(None),
    site_id: Optional[str] = Query(None),
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
):
    """Get partner revenue share data."""
    conn = get_db()

    query = """
        SELECT
            partner_id,
            partner_name,
            site_id,
            site_name,
            revenue_share_pct,
            date,
            gross_revenue,
            partner_share
        FROM v_partner_revenue
        WHERE 1=1
    """
    params = []

    if partner_id:
        query += " AND partner_id = ?"
        params.append(partner_id)
    if site_id:
        query += " AND site_id = ?"
        params.append(site_id)
    if start_date:
        query += " AND date >= ?"
        params.append(start_date)
    if end_date:
        query += " AND date <= ?"
        params.append(end_date)

    query += " ORDER BY date DESC"

    df = conn.execute(query, params).df()
    conn.close()

    return df.to_dict(orient="records")


# ============== Vendor Benchmarking ==============

@app.get("/metrics/vendor_benchmark")
def get_vendor_benchmark():
    """Get vendor benchmarking metrics."""
    conn = get_db()

    df = conn.execute("""
        SELECT
            s.vendor_controller as vendor,
            COUNT(DISTINCT s.site_id) as site_count,
            SUM(s.bess_mw) as total_mw,
            AVG(bh.avg_soh) as avg_soh,
            AVG(a.availability_pct) as avg_availability,
            COUNT(DISTINCT e.event_id) / NULLIF(COUNT(DISTINCT s.site_id), 0) as faults_per_site
        FROM dim_site s
        LEFT JOIN v_battery_health bh ON s.site_id = bh.site_id
            AND bh.date = (SELECT MAX(date) FROM v_battery_health)
        LEFT JOIN v_site_availability a ON s.site_id = a.site_id
            AND a.date >= (SELECT MAX(date) FROM v_site_availability) - INTERVAL '7 days'
        LEFT JOIN fact_events e ON s.site_id = e.site_id
            AND e.event_type IN ('fault', 'trip')
        GROUP BY s.vendor_controller
    """).df()
    conn.close()

    return df.to_dict(orient="records")


# ============== Pipeline ==============

@app.get("/metrics/pipeline")
def get_pipeline():
    """Get project pipeline data."""
    conn = get_db()

    df = conn.execute("SELECT * FROM projects_pipeline ORDER BY expected_cod").df()
    conn.close()

    return df.to_dict(orient="records")


# ============== Maintenance ==============

@app.get("/metrics/maintenance")
def get_maintenance(
    site_id: Optional[str] = Query(None),
    status: Optional[str] = Query(None, regex="^(open|closed)$"),
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
):
    """Get maintenance ticket data."""
    conn = get_db()

    query = """
        SELECT
            ticket_id,
            site_id,
            asset_id,
            opened_ts,
            closed_ts,
            issue_category,
            resolution,
            cost_gbp
        FROM fact_maintenance
        WHERE 1=1
    """
    params = []

    if site_id:
        query += " AND site_id = ?"
        params.append(site_id)
    if status == "open":
        query += " AND closed_ts IS NULL"
    elif status == "closed":
        query += " AND closed_ts IS NOT NULL"
    if start_date:
        query += " AND opened_ts >= ?"
        params.append(datetime.combine(start_date, datetime.min.time()))
    if end_date:
        query += " AND opened_ts <= ?"
        params.append(datetime.combine(end_date, datetime.max.time()))

    query += " ORDER BY opened_ts DESC"

    df = conn.execute(query, params).df()
    conn.close()

    return df.to_dict(orient="records")


# ============== Grid Code ==============

@app.get("/metrics/grid_code")
def get_grid_code_metrics(
    site_id: Optional[str] = Query(None),
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
):
    """Get grid code compliance metrics."""
    conn = get_db()

    query = """
        WITH power_data AS (
            SELECT
                site_id,
                ts,
                value as power_kw,
                LAG(value) OVER (PARTITION BY site_id ORDER BY ts) as prev_power_kw
            FROM fact_telemetry
            WHERE tag = 'p_kw'
        ),
        ramp_rates AS (
            SELECT
                site_id,
                DATE_TRUNC('day', ts) as date,
                MAX(ABS(power_kw - prev_power_kw)) as max_ramp_kw_per_min,
                AVG(ABS(power_kw - prev_power_kw)) as avg_ramp_kw_per_min
            FROM power_data
            WHERE prev_power_kw IS NOT NULL
    """
    params = []

    if site_id:
        query += " AND site_id = ?"
        params.append(site_id)

    query += """
            GROUP BY site_id, DATE_TRUNC('day', ts)
        ),
        voltage_data AS (
            SELECT
                site_id,
                DATE_TRUNC('day', ts) as date,
                COUNT(CASE WHEN value < 0.95 OR value > 1.05 THEN 1 END) as voltage_excursions
            FROM fact_telemetry
            WHERE tag = 'v_pu'
    """

    if site_id:
        query += " AND site_id = ?"
        params.append(site_id)

    query += """
            GROUP BY site_id, DATE_TRUNC('day', ts)
        )
        SELECT
            r.site_id,
            r.date,
            r.max_ramp_kw_per_min,
            r.avg_ramp_kw_per_min,
            COALESCE(v.voltage_excursions, 0) as voltage_excursions
        FROM ramp_rates r
        LEFT JOIN voltage_data v ON r.site_id = v.site_id AND r.date = v.date
        ORDER BY r.date DESC
    """

    df = conn.execute(query, params).df()
    conn.close()

    return df.to_dict(orient="records")


# ============== Edge Intelligence ==============

@app.get("/edge/corrected_signals")
def get_corrected_signals(
    site_id: Optional[str] = Query(None),
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    limit: int = Query(1000, le=10000),
):
    """Get corrected signal data with trust scores."""
    conn = get_db()

    query = """
        SELECT
            site_id, ts, soc_pct_raw, soc_pct_corrected, soe_mwh_corrected,
            sop_charge_kw, sop_discharge_kw, hsl_soc_pct, lsl_soc_pct,
            signal_trust_score, drift_detected, correction_applied
        FROM fact_corrected_signals
        WHERE 1=1
    """
    params = []

    if site_id:
        query += " AND site_id = ?"
        params.append(site_id)
    if start_date:
        query += " AND ts >= ?"
        params.append(datetime.combine(start_date, datetime.min.time()))
    if end_date:
        query += " AND ts <= ?"
        params.append(datetime.combine(end_date, datetime.max.time()))

    query += f" ORDER BY ts DESC LIMIT {limit}"

    df = conn.execute(query, params).df()
    conn.close()

    return df.to_dict(orient="records")


@app.get("/edge/latest_signals")
def get_latest_corrected_signals(site_id: Optional[str] = Query(None)):
    """Get latest corrected signals per site."""
    conn = get_db()

    query = "SELECT * FROM v_latest_corrected_signals"
    params = []

    if site_id:
        query = "SELECT * FROM v_latest_corrected_signals WHERE site_id = ?"
        params.append(site_id)

    df = conn.execute(query, params).df()
    conn.close()

    return df.to_dict(orient="records")


@app.get("/edge/signal_health")
def get_signal_health(site_id: Optional[str] = Query(None)):
    """Get signal health summary per site."""
    conn = get_db()

    query = "SELECT * FROM v_site_signal_health"
    params = []

    if site_id:
        query = "SELECT * FROM v_site_signal_health WHERE site_id = ?"
        params.append(site_id)

    df = conn.execute(query, params).df()
    conn.close()

    return df.to_dict(orient="records")


@app.get("/edge/constraints")
def get_constraints(
    site_id: Optional[str] = Query(None),
    constraint_type: Optional[str] = Query(None),
    limit: int = Query(500, le=5000),
):
    """Get power/energy constraint records."""
    conn = get_db()

    query = """
        SELECT site_id, ts, constraint_type, reason, limit_value, duration_min, severity
        FROM fact_constraints
        WHERE 1=1
    """
    params = []

    if site_id:
        query += " AND site_id = ?"
        params.append(site_id)
    if constraint_type:
        query += " AND constraint_type = ?"
        params.append(constraint_type)

    query += f" ORDER BY ts DESC LIMIT {limit}"

    df = conn.execute(query, params).df()
    conn.close()

    return df.to_dict(orient="records")


@app.get("/edge/forecasts")
def get_forecasts(
    site_id: Optional[str] = Query(None),
    horizon_min: Optional[int] = Query(None),
    limit: int = Query(1000, le=10000),
):
    """Get energy/power availability forecasts."""
    conn = get_db()

    query = """
        SELECT site_id, ts, horizon_min, predicted_soc_pct,
               time_to_empty_min, time_to_full_min, confidence_pct, available_energy_mwh
        FROM fact_forecasts
        WHERE 1=1
    """
    params = []

    if site_id:
        query += " AND site_id = ?"
        params.append(site_id)
    if horizon_min:
        query += " AND horizon_min = ?"
        params.append(horizon_min)

    query += f" ORDER BY ts DESC, horizon_min LIMIT {limit}"

    df = conn.execute(query, params).df()
    conn.close()

    return df.to_dict(orient="records")


@app.get("/edge/imbalance")
def get_imbalance(
    site_id: Optional[str] = Query(None),
    severity: Optional[str] = Query(None),
    limit: int = Query(1000, le=10000),
):
    """Get rack imbalance detection records."""
    conn = get_db()

    query = """
        SELECT site_id, rack_id, ts, imbalance_score, severity, max_cell_delta_mv, max_temp_delta_c
        FROM fact_imbalance
        WHERE 1=1
    """
    params = []

    if site_id:
        query += " AND site_id = ?"
        params.append(site_id)
    if severity:
        query += " AND severity = ?"
        params.append(severity)

    query += f" ORDER BY ts DESC LIMIT {limit}"

    df = conn.execute(query, params).df()
    conn.close()

    return df.to_dict(orient="records")


@app.get("/edge/balancing_actions")
def get_balancing_actions(
    site_id: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    priority: Optional[str] = Query(None),
    limit: int = Query(500, le=5000),
):
    """Get balancing action recommendations."""
    conn = get_db()

    query = """
        SELECT action_id, site_id, rack_id, ts, action_type, priority,
               estimated_duration_min, estimated_recovery_mwh, status
        FROM fact_balancing_actions
        WHERE 1=1
    """
    params = []

    if site_id:
        query += " AND site_id = ?"
        params.append(site_id)
    if status:
        query += " AND status = ?"
        params.append(status)
    if priority:
        query += " AND priority = ?"
        params.append(priority)

    query += f" ORDER BY ts DESC LIMIT {limit}"

    df = conn.execute(query, params).df()
    conn.close()

    return df.to_dict(orient="records")


@app.get("/edge/insights")
def get_insights(
    site_id: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    severity: Optional[str] = Query(None),
    resolved: Optional[bool] = Query(None),
    limit: int = Query(500, le=5000),
):
    """Get automated insights and findings."""
    conn = get_db()

    query = """
        SELECT finding_id, ts, site_id, category, severity, title,
               description, recommendation, estimated_value_gbp,
               confidence, acknowledged, resolved
        FROM fact_insights_findings
        WHERE 1=1
    """
    params = []

    if site_id:
        query += " AND site_id = ?"
        params.append(site_id)
    if category:
        query += " AND category = ?"
        params.append(category)
    if severity:
        query += " AND severity = ?"
        params.append(severity)
    if resolved is not None:
        query += " AND resolved = ?"
        params.append(resolved)

    query += """
        ORDER BY
            CASE severity WHEN 'critical' THEN 1 WHEN 'alert' THEN 2 WHEN 'warning' THEN 3 ELSE 4 END,
            ts DESC
    """
    query += f" LIMIT {limit}"

    df = conn.execute(query, params).df()
    conn.close()

    return df.to_dict(orient="records")


@app.get("/edge/value_at_risk")
def get_value_at_risk(site_id: Optional[str] = Query(None)):
    """Get total value at risk from unresolved insights."""
    conn = get_db()

    query = """
        SELECT
            site_id,
            SUM(estimated_value_gbp) as total_value_at_risk,
            COUNT(*) as unresolved_count,
            COUNT(CASE WHEN severity = 'critical' THEN 1 END) as critical_count,
            COUNT(CASE WHEN severity = 'alert' THEN 1 END) as alert_count
        FROM fact_insights_findings
        WHERE resolved = false
    """
    params = []

    if site_id:
        query += " AND site_id = ?"
        params.append(site_id)

    query += " GROUP BY site_id"

    df = conn.execute(query, params).df()

    # Portfolio total
    total = conn.execute("""
        SELECT SUM(estimated_value_gbp) as total, COUNT(*) as count
        FROM fact_insights_findings WHERE resolved = false
    """).fetchone()
    conn.close()

    return {
        "by_site": df.to_dict(orient="records"),
        "portfolio": {"total_value_at_risk": total[0] or 0, "total_unresolved": total[1] or 0}
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
