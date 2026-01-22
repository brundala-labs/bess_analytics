"""
BESS Analytics - DuckDB Database Loader

Loads Parquet files into DuckDB and creates analytical views.
"""

from pathlib import Path
from typing import Optional

import duckdb
from loguru import logger

DATA_DIR = Path(__file__).parent.parent / "data"
GOLD_DIR = DATA_DIR / "gold"
DB_PATH = DATA_DIR / "bess_analytics.duckdb"


def get_connection(db_path: Optional[Path] = None) -> duckdb.DuckDBPyConnection:
    """Get DuckDB connection."""
    path = db_path or DB_PATH
    return duckdb.connect(str(path))


def load_data(conn: Optional[duckdb.DuckDBPyConnection] = None) -> duckdb.DuckDBPyConnection:
    """Load all Parquet files into DuckDB tables."""
    if conn is None:
        conn = get_connection()

    logger.info("Loading data into DuckDB...")

    # Load dimension tables
    tables = [
        "dim_site",
        "dim_asset",
        "dim_service",
        "dim_partner",
        "dim_sla",
        "fact_telemetry",
        "fact_dispatch",
        "fact_events",
        "fact_settlement",
        "fact_maintenance",
        "fact_data_quality",
        "forecast_revenue",
        "projects_pipeline",
        # Edge Intelligence tables
        "fact_corrected_signals",
        "fact_constraints",
        "fact_cell_telemetry",
        "fact_imbalance",
        "fact_balancing_actions",
        "fact_forecasts",
        "fact_insights_findings",
    ]

    for table in tables:
        parquet_path = DATA_DIR / f"{table}.parquet"
        if parquet_path.exists():
            conn.execute(f"""
                CREATE OR REPLACE TABLE {table} AS
                SELECT * FROM read_parquet('{parquet_path}')
            """)
            count = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            logger.info(f"  Loaded {table}: {count:,} rows")
        else:
            logger.warning(f"  Missing: {parquet_path}")

    # Load Gold layer aggregate tables (if they exist)
    gold_tables = [
        "agg_telemetry_15min",
        "agg_site_daily",
        "agg_site_monthly",
        "agg_revenue_daily",
        "agg_events_daily",
    ]

    for table in gold_tables:
        parquet_path = GOLD_DIR / f"{table}.parquet"
        if parquet_path.exists():
            conn.execute(f"""
                CREATE OR REPLACE TABLE {table} AS
                SELECT * FROM read_parquet('{parquet_path}')
            """)
            count = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            logger.info(f"  Loaded Gold/{table}: {count:,} rows")

    # Create analytical views
    create_views(conn)

    logger.info("Database loading complete!")
    return conn


def create_views(conn: duckdb.DuckDBPyConnection):
    """Create analytical views for dashboards."""
    logger.info("Creating analytical views...")

    # View: Site summary with latest telemetry
    conn.execute("""
        CREATE OR REPLACE VIEW v_site_latest_telemetry AS
        WITH latest AS (
            SELECT
                site_id,
                tag,
                value,
                ROW_NUMBER() OVER (PARTITION BY site_id, tag ORDER BY ts DESC) as rn
            FROM fact_telemetry
        )
        SELECT
            s.*,
            MAX(CASE WHEN l.tag = 'p_kw' THEN l.value END) as latest_power_kw,
            MAX(CASE WHEN l.tag = 'soc_pct' THEN l.value END) as latest_soc_pct,
            MAX(CASE WHEN l.tag = 'soh_pct' THEN l.value END) as latest_soh_pct,
            MAX(CASE WHEN l.tag = 'controller_status' THEN l.value END) as controller_status
        FROM dim_site s
        LEFT JOIN latest l ON s.site_id = l.site_id AND l.rn = 1
        GROUP BY s.site_id, s.name, s.country, s.grid_connection_mw, s.bess_mw,
                 s.bess_mwh, s.cod_date, s.vendor_controller, s.latitude, s.longitude
    """)

    # View: Daily revenue by site
    conn.execute("""
        CREATE OR REPLACE VIEW v_daily_revenue AS
        SELECT
            date,
            site_id,
            SUM(revenue_gbp) as total_revenue_gbp,
            SUM(energy_mwh) as total_energy_mwh,
            AVG(avg_price_gbp_per_mwh) as avg_price
        FROM fact_settlement
        GROUP BY date, site_id
    """)

    # View: Revenue with forecast comparison
    conn.execute("""
        CREATE OR REPLACE VIEW v_revenue_vs_forecast AS
        SELECT
            r.date,
            r.site_id,
            r.total_revenue_gbp as actual_revenue,
            f.forecast_revenue_gbp as forecast_revenue,
            f.forecast_revenue_gbp - r.total_revenue_gbp as revenue_gap
        FROM v_daily_revenue r
        LEFT JOIN forecast_revenue f ON r.date = f.date AND r.site_id = f.site_id
    """)

    # View: Site availability (based on controller status)
    conn.execute("""
        CREATE OR REPLACE VIEW v_site_availability AS
        WITH hourly_status AS (
            SELECT
                site_id,
                DATE_TRUNC('hour', ts) as hour,
                AVG(CASE WHEN tag = 'controller_status' THEN value ELSE NULL END) as avg_status
            FROM fact_telemetry
            GROUP BY site_id, DATE_TRUNC('hour', ts)
        )
        SELECT
            site_id,
            DATE_TRUNC('day', hour) as date,
            AVG(avg_status) * 100 as availability_pct,
            COUNT(*) as hours_measured
        FROM hourly_status
        GROUP BY site_id, DATE_TRUNC('day', hour)
    """)

    # View: Event summary by site and type
    conn.execute("""
        CREATE OR REPLACE VIEW v_event_summary AS
        SELECT
            site_id,
            event_type,
            severity,
            COUNT(*) as event_count,
            AVG(EXTRACT(EPOCH FROM (end_ts - start_ts)) / 60) as avg_duration_minutes,
            SUM(EXTRACT(EPOCH FROM (end_ts - start_ts)) / 60) as total_downtime_minutes
        FROM fact_events
        GROUP BY site_id, event_type, severity
    """)

    # View: Active events (not yet ended)
    conn.execute("""
        CREATE OR REPLACE VIEW v_active_events AS
        SELECT *
        FROM fact_events
        WHERE end_ts > (SELECT MAX(start_ts) FROM fact_events) OR end_ts IS NULL
    """)

    # View: Partner revenue share calculation
    conn.execute("""
        CREATE OR REPLACE VIEW v_partner_revenue AS
        SELECT
            p.partner_id,
            p.name as partner_name,
            p.site_id,
            s.name as site_name,
            p.revenue_share_pct,
            r.date,
            r.total_revenue_gbp as gross_revenue,
            r.total_revenue_gbp * (p.revenue_share_pct / 100) as partner_share
        FROM dim_partner p
        JOIN dim_site s ON p.site_id = s.site_id
        JOIN v_daily_revenue r ON p.site_id = r.site_id
    """)

    # View: Dispatch compliance
    conn.execute("""
        CREATE OR REPLACE VIEW v_dispatch_compliance AS
        SELECT
            site_id,
            DATE_TRUNC('day', ts) as date,
            COUNT(*) as dispatch_count,
            AVG(CASE
                WHEN command_kw = 0 THEN 100
                ELSE LEAST(100, (actual_kw / NULLIF(command_kw, 0)) * 100)
            END) as compliance_pct,
            SUM(ABS(command_kw - actual_kw)) / 1000 as total_deviation_mw
        FROM fact_dispatch
        GROUP BY site_id, DATE_TRUNC('day', ts)
    """)

    # View: Battery health trends
    conn.execute("""
        CREATE OR REPLACE VIEW v_battery_health AS
        SELECT
            site_id,
            DATE_TRUNC('day', ts) as date,
            AVG(CASE WHEN tag = 'soh_pct' THEN value END) as avg_soh,
            AVG(CASE WHEN tag = 'soc_pct' THEN value END) as avg_soc,
            AVG(CASE WHEN tag = 'temp_c_avg' THEN value END) as avg_temp,
            MAX(CASE WHEN tag = 'temp_c_max' THEN value END) as max_temp,
            MAX(CASE WHEN tag = 'cycle_count' THEN value END) as cycle_count
        FROM fact_telemetry
        WHERE tag IN ('soh_pct', 'soc_pct', 'temp_c_avg', 'temp_c_max', 'cycle_count')
        GROUP BY site_id, DATE_TRUNC('day', ts)
    """)

    # View: Data quality trends
    conn.execute("""
        CREATE OR REPLACE VIEW v_data_quality_daily AS
        SELECT
            site_id,
            DATE_TRUNC('day', ts_hour) as date,
            AVG(completeness_pct) as avg_completeness,
            MIN(completeness_pct) as min_completeness,
            SUM(missing_tags_count) as total_missing_tags
        FROM fact_data_quality
        GROUP BY site_id, DATE_TRUNC('day', ts_hour)
    """)

    # View: Vendor benchmarking
    conn.execute("""
        CREATE OR REPLACE VIEW v_vendor_benchmark AS
        SELECT
            s.vendor_controller as vendor,
            COUNT(DISTINCT s.site_id) as site_count,
            SUM(s.bess_mw) as total_mw,
            AVG(bh.avg_soh) as avg_soh,
            AVG(a.availability_pct) as avg_availability
        FROM dim_site s
        LEFT JOIN v_battery_health bh ON s.site_id = bh.site_id
        LEFT JOIN v_site_availability a ON s.site_id = a.site_id
        GROUP BY s.vendor_controller
    """)

    # View: Revenue loss attribution
    conn.execute("""
        CREATE OR REPLACE VIEW v_revenue_loss_attribution AS
        SELECT
            rvf.date,
            rvf.site_id,
            s.name as site_name,
            rvf.forecast_revenue,
            rvf.actual_revenue,
            rvf.revenue_gap,
            COALESCE(es.fault_downtime, 0) as fault_minutes,
            COALESCE(es.trip_downtime, 0) as trip_minutes,
            COALESCE(dq.avg_completeness, 100) as data_completeness
        FROM v_revenue_vs_forecast rvf
        JOIN dim_site s ON rvf.site_id = s.site_id
        LEFT JOIN (
            SELECT
                site_id,
                DATE_TRUNC('day', start_ts) as date,
                SUM(CASE WHEN event_type = 'fault'
                    THEN EXTRACT(EPOCH FROM (end_ts - start_ts)) / 60 ELSE 0 END) as fault_downtime,
                SUM(CASE WHEN event_type = 'trip'
                    THEN EXTRACT(EPOCH FROM (end_ts - start_ts)) / 60 ELSE 0 END) as trip_downtime
            FROM fact_events
            GROUP BY site_id, DATE_TRUNC('day', start_ts)
        ) es ON rvf.site_id = es.site_id AND rvf.date = es.date
        LEFT JOIN v_data_quality_daily dq ON rvf.site_id = dq.site_id AND rvf.date = dq.date
    """)

    # View: Response time from telemetry (comms_latency_ms -> seconds)
    conn.execute("""
        CREATE OR REPLACE VIEW v_response_time AS
        SELECT
            site_id,
            AVG(value) / 1000.0 as avg_response_sec
        FROM fact_telemetry
        WHERE tag = 'comms_latency_ms'
        GROUP BY site_id
    """)

    # View: SLA compliance
    conn.execute("""
        CREATE OR REPLACE VIEW v_sla_compliance AS
        SELECT
            sla.sla_id,
            sla.site_id,
            s.name as site_name,
            sla.metric_name,
            sla.threshold,
            sla.penalty_rate_per_hour,
            CASE sla.metric_name
                WHEN 'availability_pct' THEN AVG(a.availability_pct)
                WHEN 'comms_uptime_pct' THEN AVG(dq.avg_completeness)
                WHEN 'response_time_sec' THEN AVG(rt.avg_response_sec)
                ELSE NULL
            END as actual_value,
            CASE
                WHEN sla.metric_name = 'availability_pct'
                    AND AVG(a.availability_pct) < sla.threshold THEN 'BREACH'
                WHEN sla.metric_name = 'comms_uptime_pct'
                    AND AVG(dq.avg_completeness) < sla.threshold THEN 'BREACH'
                WHEN sla.metric_name = 'response_time_sec'
                    AND AVG(rt.avg_response_sec) > sla.threshold THEN 'BREACH'
                ELSE 'COMPLIANT'
            END as status
        FROM dim_sla sla
        JOIN dim_site s ON sla.site_id = s.site_id
        LEFT JOIN v_site_availability a ON sla.site_id = a.site_id
        LEFT JOIN v_data_quality_daily dq ON sla.site_id = dq.site_id
        LEFT JOIN v_response_time rt ON sla.site_id = rt.site_id
        GROUP BY sla.sla_id, sla.site_id, s.name, sla.metric_name, sla.threshold, sla.penalty_rate_per_hour
    """)

    # ============== Edge Intelligence Views ==============

    # View: Latest corrected signals per site
    conn.execute("""
        CREATE OR REPLACE VIEW v_latest_corrected_signals AS
        SELECT DISTINCT ON (site_id)
            site_id, ts, soc_pct_raw, soc_pct_corrected, soe_mwh_corrected,
            sop_charge_kw, sop_discharge_kw, hsl_soc_pct, lsl_soc_pct,
            signal_trust_score, drift_detected, correction_applied
        FROM fact_corrected_signals
        ORDER BY site_id, ts DESC
    """)

    # View: Active constraints
    conn.execute("""
        CREATE OR REPLACE VIEW v_active_constraints AS
        SELECT *
        FROM fact_constraints
        WHERE ts >= (SELECT MAX(ts) FROM fact_constraints) - INTERVAL '1 hour'
        ORDER BY
            CASE severity WHEN 'critical' THEN 1 WHEN 'high' THEN 2 WHEN 'medium' THEN 3 ELSE 4 END,
            ts DESC
    """)

    # View: Imbalance summary by rack
    conn.execute("""
        CREATE OR REPLACE VIEW v_imbalance_summary AS
        SELECT
            site_id,
            rack_id,
            AVG(imbalance_score) as avg_imbalance_score,
            MAX(imbalance_score) as max_imbalance_score,
            AVG(max_cell_delta_mv) as avg_voltage_delta_mv,
            AVG(max_temp_delta_c) as avg_temp_delta_c,
            COUNT(CASE WHEN severity = 'critical' THEN 1 END) as critical_count,
            COUNT(CASE WHEN severity = 'high' THEN 1 END) as high_count
        FROM fact_imbalance
        WHERE ts >= (SELECT MAX(ts) FROM fact_imbalance) - INTERVAL '7 days'
        GROUP BY site_id, rack_id
    """)

    # View: Pending balancing actions
    conn.execute("""
        CREATE OR REPLACE VIEW v_pending_balancing_actions AS
        SELECT *
        FROM fact_balancing_actions
        WHERE status = 'pending'
        ORDER BY
            CASE priority WHEN 'urgent' THEN 1 WHEN 'high' THEN 2 WHEN 'medium' THEN 3 ELSE 4 END,
            ts DESC
    """)

    # View: Latest forecast summary per site
    conn.execute("""
        CREATE OR REPLACE VIEW v_forecast_summary AS
        WITH latest AS (
            SELECT
                site_id,
                MAX(ts) as latest_ts
            FROM fact_forecasts
            GROUP BY site_id
        )
        SELECT
            f.site_id,
            f.ts,
            f.horizon_min,
            f.predicted_soc_pct,
            f.time_to_empty_min,
            f.time_to_full_min,
            f.confidence_pct,
            f.available_energy_mwh
        FROM fact_forecasts f
        JOIN latest l ON f.site_id = l.site_id AND f.ts = l.latest_ts
        WHERE f.horizon_min = 60
    """)

    # View: Active insights (unresolved)
    conn.execute("""
        CREATE OR REPLACE VIEW v_active_insights AS
        SELECT *
        FROM fact_insights_findings
        WHERE resolved = false
        ORDER BY
            CASE severity WHEN 'critical' THEN 1 WHEN 'alert' THEN 2 WHEN 'warning' THEN 3 ELSE 4 END,
            estimated_value_gbp DESC
    """)

    # View: Insights summary by category and severity
    conn.execute("""
        CREATE OR REPLACE VIEW v_insights_summary AS
        SELECT
            site_id,
            severity,
            category,
            COUNT(*) as finding_count,
            SUM(estimated_value_gbp) as total_value_impact
        FROM fact_insights_findings
        WHERE resolved = false
        GROUP BY site_id, severity, category
    """)

    # View: Site signal health overview
    conn.execute("""
        CREATE OR REPLACE VIEW v_site_signal_health AS
        SELECT
            site_id,
            AVG(signal_trust_score) as avg_trust_score,
            SUM(CASE WHEN drift_detected THEN 1 ELSE 0 END) as drift_count,
            SUM(CASE WHEN correction_applied THEN 1 ELSE 0 END) as correction_count,
            AVG(ABS(soc_pct_corrected - soc_pct_raw)) as avg_soc_error
        FROM fact_corrected_signals
        WHERE ts >= (SELECT MAX(ts) FROM fact_corrected_signals) - INTERVAL '24 hours'
        GROUP BY site_id
    """)

    logger.info("Views created successfully (including Edge Intelligence views)")


def init_database() -> duckdb.DuckDBPyConnection:
    """Initialize database and load all data."""
    conn = get_connection()
    load_data(conn)
    return conn


if __name__ == "__main__":
    init_database()
