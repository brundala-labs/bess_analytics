"""
BESS Analytics - Synthetic Data Generator

Generates realistic BESS telemetry, events, and financial data for demo purposes.
- 30 days of 1-minute telemetry
- 3 sites with 2 vendors (TMEIC, OtherPCS)
- Realistic patterns: daily price cycles, faults, comms drops, degradation
"""

import json
import os
import random
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from loguru import logger

# Configuration
NUM_DAYS = 30
MINUTES_PER_DAY = 1440
NUM_SITES = 3
VENDORS = ["TMEIC", "OtherPCS"]
DATA_DIR = Path(__file__).parent.parent / "data"
BRONZE_DIR = DATA_DIR / "bronze"
SILVER_DIR = DATA_DIR / "silver"
GOLD_DIR = DATA_DIR / "gold"

# Seed for reproducibility
np.random.seed(42)
random.seed(42)


def generate_dim_site() -> pd.DataFrame:
    """Generate site dimension table."""
    sites = [
        {
            "site_id": "SITE001",
            "name": "Cotswold Energy Park",
            "country": "UK",
            "grid_connection_mw": 100.0,
            "bess_mw": 50.0,
            "bess_mwh": 100.0,
            "cod_date": "2023-06-15",
            "vendor_controller": "TMEIC",
            "latitude": 51.8,
            "longitude": -1.7,
        },
        {
            "site_id": "SITE002",
            "name": "Thames Gateway Storage",
            "country": "UK",
            "grid_connection_mw": 75.0,
            "bess_mw": 40.0,
            "bess_mwh": 80.0,
            "cod_date": "2023-09-01",
            "vendor_controller": "TMEIC",
            "latitude": 51.5,
            "longitude": 0.2,
        },
        {
            "site_id": "SITE003",
            "name": "Yorkshire Wind-Storage",
            "country": "UK",
            "grid_connection_mw": 60.0,
            "bess_mw": 30.0,
            "bess_mwh": 60.0,
            "cod_date": "2024-01-10",
            "vendor_controller": "OtherPCS",
            "latitude": 53.9,
            "longitude": -1.1,
        },
    ]
    return pd.DataFrame(sites)


def generate_dim_asset(sites_df: pd.DataFrame) -> pd.DataFrame:
    """Generate asset dimension table."""
    assets = []
    asset_id = 1

    for _, site in sites_df.iterrows():
        # Controller
        assets.append({
            "asset_id": f"ASSET{asset_id:04d}",
            "site_id": site["site_id"],
            "asset_type": "controller",
            "make": site["vendor_controller"],
            "model": f"{site['vendor_controller']}-PCS-500" if site["vendor_controller"] == "TMEIC" else "OtherPCS-Controller-X1",
        })
        asset_id += 1

        # Inverters (2 per site)
        for inv_num in range(1, 3):
            assets.append({
                "asset_id": f"ASSET{asset_id:04d}",
                "site_id": site["site_id"],
                "asset_type": "inverter",
                "make": site["vendor_controller"],
                "model": f"{site['vendor_controller']}-INV-250",
            })
            asset_id += 1

        # Battery racks (4 per site)
        for rack_num in range(1, 5):
            assets.append({
                "asset_id": f"ASSET{asset_id:04d}",
                "site_id": site["site_id"],
                "asset_type": "battery_rack",
                "make": "CATL" if random.random() > 0.5 else "BYD",
                "model": "LFP-280Ah" if random.random() > 0.5 else "LFP-302Ah",
            })
            asset_id += 1

    return pd.DataFrame(assets)


def generate_dim_service() -> pd.DataFrame:
    """Generate service dimension table."""
    services = [
        {"service_id": "SVC001", "name": "arbitrage", "market": "GB Wholesale"},
        {"service_id": "SVC002", "name": "frequency_response", "market": "GB FFR"},
        {"service_id": "SVC003", "name": "reserve", "market": "GB STOR"},
        {"service_id": "SVC004", "name": "capacity", "market": "GB Capacity Market"},
    ]
    return pd.DataFrame(services)


def generate_dim_partner(sites_df: pd.DataFrame) -> pd.DataFrame:
    """Generate partner dimension table."""
    partners = [
        {
            "partner_id": "PARTNER001",
            "site_id": "SITE001",
            "name": "Cotswold Renewables Ltd",
            "revenue_share_pct": 15.0,
        },
        {
            "partner_id": "PARTNER002",
            "site_id": "SITE002",
            "name": "Thames Energy Investments",
            "revenue_share_pct": 12.0,
        },
        {
            "partner_id": "PARTNER003",
            "site_id": "SITE003",
            "name": "Yorkshire Green Power",
            "revenue_share_pct": 18.0,
        },
    ]
    return pd.DataFrame(partners)


def generate_dim_sla(sites_df: pd.DataFrame) -> pd.DataFrame:
    """Generate SLA dimension table."""
    slas = []
    sla_id = 1

    sla_definitions = [
        {"metric_name": "availability_pct", "threshold": 95.0, "penalty_rate_per_hour": 500.0},
        {"metric_name": "response_time_sec", "threshold": 1.0, "penalty_rate_per_hour": 200.0},
        {"metric_name": "comms_uptime_pct", "threshold": 99.0, "penalty_rate_per_hour": 100.0},
    ]

    for _, site in sites_df.iterrows():
        for sla_def in sla_definitions:
            slas.append({
                "sla_id": f"SLA{sla_id:04d}",
                "site_id": site["site_id"],
                **sla_def,
            })
            sla_id += 1

    return pd.DataFrame(slas)


def generate_price_curve(num_days: int) -> np.ndarray:
    """Generate realistic UK wholesale price curve (£/MWh)."""
    hours = num_days * 24
    prices = np.zeros(hours)

    for day in range(num_days):
        base_price = 50 + np.random.normal(0, 10)  # Daily base variation

        for hour in range(24):
            idx = day * 24 + hour

            # Peak pricing patterns
            if 16 <= hour <= 20:  # Evening peak
                prices[idx] = base_price * 1.8 + np.random.normal(0, 15)
            elif 6 <= hour <= 9:  # Morning peak
                prices[idx] = base_price * 1.3 + np.random.normal(0, 8)
            elif 0 <= hour <= 5:  # Night trough
                prices[idx] = base_price * 0.6 + np.random.normal(0, 5)
            else:
                prices[idx] = base_price + np.random.normal(0, 8)

            # Occasional price spikes
            if random.random() < 0.02:
                prices[idx] *= random.uniform(1.5, 3.0)

    return np.maximum(prices, 0)  # No negative prices for simplicity


def generate_fact_telemetry(
    sites_df: pd.DataFrame,
    assets_df: pd.DataFrame,
    start_date: datetime,
    num_days: int,
) -> pd.DataFrame:
    """Generate 1-minute telemetry data."""
    logger.info(f"Generating {num_days} days of telemetry data...")

    records = []
    total_minutes = num_days * MINUTES_PER_DAY
    price_curve = generate_price_curve(num_days)

    # Pre-compute site characteristics
    site_characteristics = {
        "SITE001": {"base_efficiency": 0.92, "comms_drop_rate": 0.001, "degradation_rate": 0.0001},
        "SITE002": {"base_efficiency": 0.90, "comms_drop_rate": 0.015, "degradation_rate": 0.0002},  # Higher comms issues
        "SITE003": {"base_efficiency": 0.89, "comms_drop_rate": 0.003, "degradation_rate": 0.0003},  # Faster degradation
    }

    for _, site in sites_df.iterrows():
        site_id = site["site_id"]
        bess_mw = site["bess_mw"]
        bess_mwh = site["bess_mwh"]
        vendor = site["vendor_controller"]
        chars = site_characteristics[site_id]

        # Get assets for this site
        site_assets = assets_df[assets_df["site_id"] == site_id]
        controller_asset = site_assets[site_assets["asset_type"] == "controller"].iloc[0]["asset_id"]
        battery_assets = site_assets[site_assets["asset_type"] == "battery_rack"]["asset_id"].tolist()

        # Initialize state
        soc = 50.0  # Start at 50% SOC
        soh = 98.0 - random.uniform(0, 3)  # Starting SOH
        cycle_count = random.randint(100, 500)

        # Track comms drop periods
        in_comms_drop = False
        comms_drop_end = 0

        for minute in range(total_minutes):
            ts = start_date + timedelta(minutes=minute)
            hour = ts.hour
            price_idx = min(minute // 60, len(price_curve) - 1)
            current_price = price_curve[price_idx]

            # Determine dispatch based on price (simple strategy)
            if current_price > 80:  # Discharge during high prices
                target_power = bess_mw * random.uniform(0.7, 1.0) * 1000  # kW
                soc -= (target_power / (bess_mwh * 1000)) * (1/60) * 100  # SOC decrease per minute
            elif current_price < 30:  # Charge during low prices
                target_power = -bess_mw * random.uniform(0.5, 0.8) * 1000  # Negative = charging
                soc += (abs(target_power) / (bess_mwh * 1000)) * (1/60) * 100 * 0.95  # Charge efficiency
            else:
                target_power = random.uniform(-500, 500)  # Small regulation

            # Apply SOC limits
            soc = np.clip(soc, 5, 95)
            if soc <= 10:
                target_power = max(target_power, 0)  # Stop discharge
            if soc >= 90:
                target_power = min(target_power, 0)  # Stop charge

            # Count cycles
            if abs(target_power) > bess_mw * 500:
                cycle_count += 0.001  # Partial cycle count

            # Degrade SOH slowly
            soh -= chars["degradation_rate"] * (1 + abs(target_power) / (bess_mw * 1000))
            soh = max(soh, 70)

            # Comms drop simulation
            if not in_comms_drop and random.random() < chars["comms_drop_rate"]:
                in_comms_drop = True
                comms_drop_end = minute + random.randint(5, 60)  # 5-60 minute drop

            if minute >= comms_drop_end:
                in_comms_drop = False

            comms_latency = 50 + np.random.exponential(20) if not in_comms_drop else 9999
            comms_drop_rate = 0.0 if not in_comms_drop else 100.0

            # Calculate actual power with efficiency losses
            efficiency = chars["base_efficiency"] - (98 - soh) * 0.002
            actual_power = target_power * efficiency if not in_comms_drop else 0

            # Controller telemetry
            controller_tags = {
                "p_kw": actual_power + np.random.normal(0, 10),
                "q_kvar": actual_power * 0.1 * random.uniform(-1, 1) + np.random.normal(0, 5),
                "v_pu": 1.0 + np.random.normal(0, 0.02),
                "f_hz": 50.0 + np.random.normal(0, 0.05),
                "controller_status": 1.0 if not in_comms_drop else 0.0,
                "comms_latency_ms": comms_latency,
                "comms_drop_rate": comms_drop_rate,
                "inverter_efficiency_pct": efficiency * 100,
                "cooling_status": 1.0,
            }

            for tag, value in controller_tags.items():
                records.append({
                    "ts": ts,
                    "site_id": site_id,
                    "asset_id": controller_asset,
                    "tag": tag,
                    "value": round(value, 3),
                })

            # Battery telemetry (aggregate for simplicity, one record per site)
            battery_tags = {
                "soc_pct": soc + np.random.normal(0, 0.5),
                "soh_pct": soh + np.random.normal(0, 0.1),
                "temp_c_avg": 25 + (abs(actual_power) / (bess_mw * 1000)) * 15 + np.random.normal(0, 2),
                "temp_c_max": 30 + (abs(actual_power) / (bess_mw * 1000)) * 20 + np.random.normal(0, 3),
                "voltage_v": 800 + np.random.normal(0, 5),
                "current_a": actual_power / 800 + np.random.normal(0, 1),
                "cycle_count": cycle_count,
            }

            for tag, value in battery_tags.items():
                records.append({
                    "ts": ts,
                    "site_id": site_id,
                    "asset_id": battery_assets[0],  # Use first battery rack as aggregate
                    "tag": tag,
                    "value": round(value, 3),
                })

            # Log progress every 10000 minutes
            if minute % 10000 == 0 and minute > 0:
                logger.info(f"  Site {site_id}: {minute}/{total_minutes} minutes generated")

    return pd.DataFrame(records)


def generate_fact_dispatch(
    sites_df: pd.DataFrame,
    services_df: pd.DataFrame,
    start_date: datetime,
    num_days: int,
) -> pd.DataFrame:
    """Generate dispatch commands."""
    logger.info("Generating dispatch data...")

    records = []
    price_curve = generate_price_curve(num_days)

    for _, site in sites_df.iterrows():
        site_id = site["site_id"]
        bess_mw = site["bess_mw"]

        for minute in range(num_days * MINUTES_PER_DAY):
            ts = start_date + timedelta(minutes=minute)

            # Only generate dispatch records every 5 minutes
            if minute % 5 != 0:
                continue

            price_idx = min(minute // 60, len(price_curve) - 1)
            current_price = price_curve[price_idx]

            # Select service based on time and price
            if current_price > 80:
                service_id = "SVC001"  # Arbitrage discharge
                command_kw = bess_mw * random.uniform(0.6, 1.0) * 1000
            elif current_price < 30:
                service_id = "SVC001"  # Arbitrage charge
                command_kw = -bess_mw * random.uniform(0.4, 0.7) * 1000
            elif random.random() < 0.1:
                service_id = "SVC002"  # Frequency response
                command_kw = random.uniform(-1000, 1000)
            else:
                service_id = "SVC003"  # Reserve standby
                command_kw = 0

            # Actual may differ from command (efficiency, SOC limits)
            actual_kw = command_kw * random.uniform(0.9, 1.0) if command_kw != 0 else 0

            records.append({
                "ts": ts,
                "site_id": site_id,
                "service_id": service_id,
                "command_kw": round(command_kw, 1),
                "actual_kw": round(actual_kw, 1),
            })

    return pd.DataFrame(records)


def generate_fact_events(
    sites_df: pd.DataFrame,
    assets_df: pd.DataFrame,
    start_date: datetime,
    num_days: int,
) -> pd.DataFrame:
    """Generate fault and event data."""
    logger.info("Generating event data...")

    events = []
    event_id = 1

    event_types = [
        {"type": "fault", "severity": "high", "codes": ["F001-Overcurrent", "F002-Overvoltage", "F003-OverTemp"]},
        {"type": "trip", "severity": "critical", "codes": ["T001-EmergencyStop", "T002-GridFault", "T003-CommsLoss"]},
        {"type": "comms_drop", "severity": "medium", "codes": ["C001-NetworkTimeout", "C002-ProtocolError"]},
        {"type": "maintenance", "severity": "low", "codes": ["M001-ScheduledMaint", "M002-FirmwareUpdate"]},
    ]

    # Site-specific event rates (per day)
    event_rates = {
        "SITE001": {"fault": 0.1, "trip": 0.02, "comms_drop": 0.2, "maintenance": 0.05},
        "SITE002": {"fault": 0.15, "trip": 0.03, "comms_drop": 0.8, "maintenance": 0.05},  # More comms issues
        "SITE003": {"fault": 0.3, "trip": 0.05, "comms_drop": 0.3, "maintenance": 0.1},  # More faults (repeated code)
    }

    for _, site in sites_df.iterrows():
        site_id = site["site_id"]
        rates = event_rates[site_id]

        site_assets = assets_df[assets_df["site_id"] == site_id]

        for day in range(num_days):
            day_start = start_date + timedelta(days=day)

            for event_def in event_types:
                event_type = event_def["type"]
                rate = rates.get(event_type, 0.1)

                # Poisson process for events
                num_events = np.random.poisson(rate)

                for _ in range(num_events):
                    start_ts = day_start + timedelta(minutes=random.randint(0, 1439))
                    duration_minutes = random.randint(5, 120) if event_type != "maintenance" else random.randint(60, 480)
                    end_ts = start_ts + timedelta(minutes=duration_minutes)

                    # Select random asset
                    asset = site_assets.sample(1).iloc[0]

                    # For SITE003, make one fault code repeat more often
                    if site_id == "SITE003" and event_type == "fault" and random.random() < 0.7:
                        code = "F001-Overcurrent"  # Repeated fault
                    else:
                        code = random.choice(event_def["codes"])

                    events.append({
                        "event_id": f"EVT{event_id:06d}",
                        "site_id": site_id,
                        "asset_id": asset["asset_id"],
                        "start_ts": start_ts,
                        "end_ts": end_ts,
                        "severity": event_def["severity"],
                        "event_type": event_type,
                        "code": code,
                        "description": f"{code} on {asset['asset_type']} {asset['asset_id']}",
                    })
                    event_id += 1

    return pd.DataFrame(events)


def generate_fact_settlement(
    sites_df: pd.DataFrame,
    services_df: pd.DataFrame,
    start_date: datetime,
    num_days: int,
) -> pd.DataFrame:
    """Generate daily settlement data."""
    logger.info("Generating settlement data...")

    records = []
    price_curve = generate_price_curve(num_days)

    for _, site in sites_df.iterrows():
        site_id = site["site_id"]
        bess_mw = site["bess_mw"]

        for day in range(num_days):
            date = (start_date + timedelta(days=day)).date()

            # Daily average price
            day_prices = price_curve[day * 24:(day + 1) * 24]
            avg_price = np.mean(day_prices)

            for _, service in services_df.iterrows():
                service_id = service["service_id"]

                # Simulate revenue based on service type
                if service_id == "SVC001":  # Arbitrage
                    energy_mwh = bess_mw * random.uniform(1.5, 2.5)
                    revenue = energy_mwh * avg_price * random.uniform(0.8, 1.2)
                elif service_id == "SVC002":  # FFR
                    energy_mwh = bess_mw * random.uniform(0.1, 0.5)
                    revenue = energy_mwh * 80 * random.uniform(0.9, 1.1)  # FFR premium
                elif service_id == "SVC003":  # Reserve
                    energy_mwh = bess_mw * random.uniform(0.05, 0.2)
                    revenue = bess_mw * 5 * random.uniform(0.9, 1.1)  # Availability payment
                else:  # Capacity
                    energy_mwh = 0
                    revenue = bess_mw * 2 / 30  # Daily capacity payment

                records.append({
                    "date": date,
                    "site_id": site_id,
                    "service_id": service_id,
                    "revenue_gbp": round(revenue, 2),
                    "energy_mwh": round(energy_mwh, 3),
                    "avg_price_gbp_per_mwh": round(avg_price, 2),
                })

    return pd.DataFrame(records)


def generate_fact_maintenance(
    events_df: pd.DataFrame,
    start_date: datetime,
) -> pd.DataFrame:
    """Generate maintenance tickets linked to events."""
    logger.info("Generating maintenance data...")

    records = []
    ticket_id = 1

    # Create tickets for faults and trips
    fault_events = events_df[events_df["event_type"].isin(["fault", "trip"])]

    for _, event in fault_events.iterrows():
        # 80% chance a fault generates a maintenance ticket
        if random.random() < 0.8:
            opened_ts = event["end_ts"]
            resolution_hours = random.randint(1, 72)
            closed_ts = opened_ts + timedelta(hours=resolution_hours) if random.random() < 0.9 else None

            issue_categories = ["Electrical", "Mechanical", "Software", "Thermal", "Communication"]
            resolutions = ["Component replaced", "Firmware updated", "Parameter adjusted", "Cleaned/serviced", "Pending"]

            records.append({
                "ticket_id": f"TKT{ticket_id:06d}",
                "site_id": event["site_id"],
                "asset_id": event["asset_id"],
                "opened_ts": opened_ts,
                "closed_ts": closed_ts,
                "issue_category": random.choice(issue_categories),
                "resolution": "Pending" if closed_ts is None else random.choice(resolutions[:-1]),
                "cost_gbp": round(random.uniform(500, 15000), 2) if closed_ts else 0,
            })
            ticket_id += 1

    return pd.DataFrame(records)


def generate_fact_data_quality(
    sites_df: pd.DataFrame,
    start_date: datetime,
    num_days: int,
) -> pd.DataFrame:
    """Generate hourly data quality metrics."""
    logger.info("Generating data quality metrics...")

    records = []

    # Site-specific quality characteristics
    quality_profiles = {
        "SITE001": {"base_completeness": 99.5, "volatility": 0.5},
        "SITE002": {"base_completeness": 95.0, "volatility": 3.0},  # More gaps
        "SITE003": {"base_completeness": 97.0, "volatility": 2.0},
    }

    for _, site in sites_df.iterrows():
        site_id = site["site_id"]
        profile = quality_profiles[site_id]

        for hour in range(num_days * 24):
            ts_hour = start_date + timedelta(hours=hour)

            completeness = profile["base_completeness"] + np.random.normal(0, profile["volatility"])
            completeness = np.clip(completeness, 80, 100)

            # Occasional major drops
            if random.random() < 0.01:
                completeness = random.uniform(50, 80)

            missing_tags = max(0, int((100 - completeness) / 10))

            records.append({
                "ts_hour": ts_hour,
                "site_id": site_id,
                "completeness_pct": round(completeness, 2),
                "missing_tags_count": missing_tags,
            })

    return pd.DataFrame(records)


def generate_forecast_revenue(
    sites_df: pd.DataFrame,
    start_date: datetime,
    num_days: int,
) -> pd.DataFrame:
    """Generate baseline revenue forecast for loss attribution."""
    logger.info("Generating revenue forecast...")

    records = []

    for _, site in sites_df.iterrows():
        site_id = site["site_id"]
        bess_mw = site["bess_mw"]

        for day in range(num_days):
            date = (start_date + timedelta(days=day)).date()

            # Forecast based on capacity and typical utilization
            forecast_revenue = bess_mw * random.uniform(150, 250)  # £/MW/day

            records.append({
                "date": date,
                "site_id": site_id,
                "forecast_revenue_gbp": round(forecast_revenue, 2),
            })

    return pd.DataFrame(records)


def generate_projects_pipeline() -> pd.DataFrame:
    """Generate development pipeline data."""
    logger.info("Generating project pipeline...")

    projects = [
        {
            "project_id": "PRJ001",
            "name": "Somerset Solar-Storage",
            "stage": "Construction",
            "mw_capacity": 75,
            "mwh_capacity": 150,
            "expected_cod": "2024-08-15",
            "vendor": "TMEIC",
            "status": "On Track",
            "completion_pct": 65,
        },
        {
            "project_id": "PRJ002",
            "name": "Norfolk Grid Services",
            "stage": "Permitting",
            "mw_capacity": 50,
            "mwh_capacity": 100,
            "expected_cod": "2025-02-01",
            "vendor": "OtherPCS",
            "status": "Delayed",
            "completion_pct": 30,
        },
        {
            "project_id": "PRJ003",
            "name": "Scottish Highlands Storage",
            "stage": "Development",
            "mw_capacity": 100,
            "mwh_capacity": 400,
            "expected_cod": "2025-06-01",
            "vendor": "TMEIC",
            "status": "On Track",
            "completion_pct": 15,
        },
        {
            "project_id": "PRJ004",
            "name": "Welsh Valleys BESS",
            "stage": "Procurement",
            "mw_capacity": 40,
            "mwh_capacity": 80,
            "expected_cod": "2024-11-01",
            "vendor": "OtherPCS",
            "status": "At Risk",
            "completion_pct": 45,
        },
        {
            "project_id": "PRJ005",
            "name": "Midlands Industrial Storage",
            "stage": "Construction",
            "mw_capacity": 60,
            "mwh_capacity": 120,
            "expected_cod": "2024-07-01",
            "vendor": "TMEIC",
            "status": "On Track",
            "completion_pct": 80,
        },
    ]

    return pd.DataFrame(projects)


def generate_bronze_layer(telemetry_df: pd.DataFrame, events_df: pd.DataFrame, sites_df: pd.DataFrame):
    """
    Generate Bronze layer data as JSONL micro-batches.

    Simulates streaming ingestion from sensors/controllers.
    """
    BRONZE_DIR.mkdir(parents=True, exist_ok=True)
    telemetry_bronze = BRONZE_DIR / "telemetry"
    events_bronze = BRONZE_DIR / "events"
    telemetry_bronze.mkdir(exist_ok=True)
    events_bronze.mkdir(exist_ok=True)

    logger.info("Generating Bronze layer (raw JSONL micro-batches)...")

    # Sample a subset for bronze layer (to avoid huge files)
    sample_hours = 24  # Generate bronze for last 24 hours only
    latest_ts = telemetry_df["ts"].max()
    bronze_start = latest_ts - timedelta(hours=sample_hours)
    bronze_telemetry = telemetry_df[telemetry_df["ts"] >= bronze_start].copy()

    # Generate telemetry micro-batches (hourly chunks per site)
    for site_id in sites_df["site_id"].unique():
        site_telemetry = bronze_telemetry[bronze_telemetry["site_id"] == site_id].copy()

        if site_telemetry.empty:
            continue

        # Group by hour
        site_telemetry["hour"] = site_telemetry["ts"].dt.floor("H")

        for hour, hour_data in site_telemetry.groupby("hour"):
            # Create JSONL file for this hour
            hour_str = hour.strftime("%Y%m%d%H")
            filename = telemetry_bronze / f"{site_id}_{hour_str}.jsonl"

            # Convert to raw format (as if from sensor)
            records = []
            for _, row in hour_data.iterrows():
                record = {
                    "source": "controller" if row["tag"] in ["p_kw", "q_kvar", "v_pu", "f_hz", "controller_status", "inverter_efficiency_pct"] else "bms",
                    "site": row["site_id"],
                    "asset": row["asset_id"],
                    "timestamp": row["ts"].isoformat(),
                    "tag": row["tag"],
                    "value": float(row["value"]) if pd.notna(row["value"]) else None,
                    "quality": "good" if random.random() > 0.01 else "uncertain",
                    "received_at": (row["ts"] + timedelta(seconds=random.randint(1, 30))).isoformat()
                }
                records.append(json.dumps(record))

            with open(filename, "w") as f:
                f.write("\n".join(records))

    # Generate events bronze (single file per day)
    events_df_copy = events_df.copy()
    events_df_copy["date"] = pd.to_datetime(events_df_copy["start_ts"]).dt.date
    for date, day_events in events_df_copy.groupby("date"):
        date_str = date.strftime("%Y%m%d")
        filename = events_bronze / f"events_{date_str}.jsonl"

        records = []
        for _, row in day_events.iterrows():
            record = {
                "source": "controller",
                "event_id": row["event_id"],
                "site": row["site_id"],
                "asset": row.get("asset_id"),
                "start_ts": row["start_ts"].isoformat() if pd.notna(row["start_ts"]) else None,
                "end_ts": row["end_ts"].isoformat() if pd.notna(row["end_ts"]) else None,
                "severity": row["severity"],
                "type": row["event_type"],
                "code": row["code"],
                "message": row["description"],
                "received_at": datetime.now().isoformat()
            }
            records.append(json.dumps(record))

        with open(filename, "w") as f:
            f.write("\n".join(records))

    logger.info(f"Bronze layer generated in {BRONZE_DIR}")


def generate_gold_layer(sites_df: pd.DataFrame, telemetry_df: pd.DataFrame,
                        settlement_df: pd.DataFrame, events_df: pd.DataFrame):
    """
    Generate Gold layer rollup/aggregate tables.
    """
    GOLD_DIR.mkdir(parents=True, exist_ok=True)

    logger.info("Generating Gold layer (aggregates and rollups)...")

    # 1. agg_telemetry_15min - 15-minute aggregates
    telemetry_15min = telemetry_df.copy()
    telemetry_15min["ts_15min"] = telemetry_15min["ts"].dt.floor("15min")

    agg_telemetry_15min = telemetry_15min.groupby(
        ["ts_15min", "site_id", "tag"]
    ).agg({
        "value": ["mean", "min", "max", "std", "count"]
    }).reset_index()
    agg_telemetry_15min.columns = ["ts_15min", "site_id", "tag", "avg_value", "min_value", "max_value", "std_value", "sample_count"]
    agg_telemetry_15min.to_parquet(GOLD_DIR / "agg_telemetry_15min.parquet", index=False)

    # 2. agg_site_daily - Daily site rollups
    telemetry_daily = telemetry_df.copy()
    telemetry_daily["date"] = telemetry_daily["ts"].dt.date

    # Calculate daily metrics per site
    daily_metrics = []
    for site_id in sites_df["site_id"].unique():
        site_data = telemetry_daily[telemetry_daily["site_id"] == site_id]
        site_info = sites_df[sites_df["site_id"] == site_id].iloc[0]

        for date, day_data in site_data.groupby("date"):
            # Get tag values
            soc_data = day_data[day_data["tag"] == "soc_pct"]["value"]
            soh_data = day_data[day_data["tag"] == "soh_pct"]["value"]
            power_data = day_data[day_data["tag"] == "p_kw"]["value"]
            temp_data = day_data[day_data["tag"] == "temp_c_max"]["value"]

            # Calculate metrics
            dod = soc_data.max() - soc_data.min() if len(soc_data) > 0 else 0
            avg_soh = soh_data.mean() if len(soh_data) > 0 else None
            max_temp = temp_data.max() if len(temp_data) > 0 else None
            energy_charged = (power_data[power_data < 0].abs().sum() / 60) / 1000 if len(power_data) > 0 else 0  # MWh
            energy_discharged = (power_data[power_data > 0].sum() / 60) / 1000 if len(power_data) > 0 else 0  # MWh

            daily_metrics.append({
                "date": date,
                "site_id": site_id,
                "dod_pct": dod,
                "avg_soh_pct": avg_soh,
                "max_temp_c": max_temp,
                "energy_charged_mwh": energy_charged,
                "energy_discharged_mwh": energy_discharged,
                "cycles_equivalent": (energy_charged + energy_discharged) / (2 * site_info["bess_mwh"]) if site_info["bess_mwh"] > 0 else 0
            })

    agg_site_daily = pd.DataFrame(daily_metrics)
    agg_site_daily.to_parquet(GOLD_DIR / "agg_site_daily.parquet", index=False)

    # 3. agg_revenue_daily - Daily revenue by site and service
    agg_revenue_daily = settlement_df.groupby(["date", "site_id", "service_id"]).agg({
        "revenue_gbp": "sum",
        "energy_mwh": "sum"
    }).reset_index()
    agg_revenue_daily["revenue_per_mwh"] = agg_revenue_daily["revenue_gbp"] / agg_revenue_daily["energy_mwh"].replace(0, np.nan)
    agg_revenue_daily.to_parquet(GOLD_DIR / "agg_revenue_daily.parquet", index=False)

    # 4. agg_events_daily - Daily event counts by site and type
    events_daily = events_df.copy()
    events_daily["date"] = pd.to_datetime(events_daily["start_ts"]).dt.date

    agg_events_daily = events_daily.groupby(["date", "site_id", "event_type", "severity"]).agg({
        "event_id": "count"
    }).reset_index()
    agg_events_daily.columns = ["date", "site_id", "event_type", "severity", "event_count"]
    agg_events_daily.to_parquet(GOLD_DIR / "agg_events_daily.parquet", index=False)

    # 5. agg_site_monthly - Monthly aggregates
    agg_site_monthly = agg_site_daily.copy()
    agg_site_monthly["month"] = pd.to_datetime(agg_site_monthly["date"]).dt.to_period("M")

    agg_site_monthly = agg_site_monthly.groupby(["month", "site_id"]).agg({
        "dod_pct": "mean",
        "avg_soh_pct": "mean",
        "max_temp_c": "max",
        "energy_charged_mwh": "sum",
        "energy_discharged_mwh": "sum",
        "cycles_equivalent": "sum"
    }).reset_index()
    agg_site_monthly["month"] = agg_site_monthly["month"].astype(str)
    agg_site_monthly.to_parquet(GOLD_DIR / "agg_site_monthly.parquet", index=False)

    logger.info(f"Gold layer generated in {GOLD_DIR}")
    logger.info(f"  - agg_telemetry_15min: {len(agg_telemetry_15min):,} records")
    logger.info(f"  - agg_site_daily: {len(agg_site_daily):,} records")
    logger.info(f"  - agg_revenue_daily: {len(agg_revenue_daily):,} records")
    logger.info(f"  - agg_events_daily: {len(agg_events_daily):,} records")


def main():
    """Main data generation function."""
    logger.info("Starting BESS Analytics data generation...")

    # Create data directories (Medallion architecture)
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    BRONZE_DIR.mkdir(parents=True, exist_ok=True)
    SILVER_DIR.mkdir(parents=True, exist_ok=True)
    GOLD_DIR.mkdir(parents=True, exist_ok=True)

    # Set start date (30 days ago from "now")
    end_date = datetime(2024, 3, 15)  # Fixed date for reproducibility
    start_date = end_date - timedelta(days=NUM_DAYS)

    logger.info(f"Generating data from {start_date} to {end_date}")

    # Generate dimension tables
    sites_df = generate_dim_site()
    assets_df = generate_dim_asset(sites_df)
    services_df = generate_dim_service()
    partners_df = generate_dim_partner(sites_df)
    slas_df = generate_dim_sla(sites_df)

    # Save dimension tables
    sites_df.to_parquet(DATA_DIR / "dim_site.parquet", index=False)
    assets_df.to_parquet(DATA_DIR / "dim_asset.parquet", index=False)
    services_df.to_parquet(DATA_DIR / "dim_service.parquet", index=False)
    partners_df.to_parquet(DATA_DIR / "dim_partner.parquet", index=False)
    slas_df.to_parquet(DATA_DIR / "dim_sla.parquet", index=False)

    logger.info("Dimension tables generated")

    # Generate fact tables
    telemetry_df = generate_fact_telemetry(sites_df, assets_df, start_date, NUM_DAYS)
    telemetry_df.to_parquet(DATA_DIR / "fact_telemetry.parquet", index=False)
    logger.info(f"Telemetry: {len(telemetry_df):,} records")

    dispatch_df = generate_fact_dispatch(sites_df, services_df, start_date, NUM_DAYS)
    dispatch_df.to_parquet(DATA_DIR / "fact_dispatch.parquet", index=False)
    logger.info(f"Dispatch: {len(dispatch_df):,} records")

    events_df = generate_fact_events(sites_df, assets_df, start_date, NUM_DAYS)
    events_df.to_parquet(DATA_DIR / "fact_events.parquet", index=False)
    logger.info(f"Events: {len(events_df):,} records")

    settlement_df = generate_fact_settlement(sites_df, services_df, start_date, NUM_DAYS)
    settlement_df.to_parquet(DATA_DIR / "fact_settlement.parquet", index=False)
    logger.info(f"Settlement: {len(settlement_df):,} records")

    maintenance_df = generate_fact_maintenance(events_df, start_date)
    maintenance_df.to_parquet(DATA_DIR / "fact_maintenance.parquet", index=False)
    logger.info(f"Maintenance: {len(maintenance_df):,} records")

    data_quality_df = generate_fact_data_quality(sites_df, start_date, NUM_DAYS)
    data_quality_df.to_parquet(DATA_DIR / "fact_data_quality.parquet", index=False)
    logger.info(f"Data Quality: {len(data_quality_df):,} records")

    forecast_df = generate_forecast_revenue(sites_df, start_date, NUM_DAYS)
    forecast_df.to_parquet(DATA_DIR / "forecast_revenue.parquet", index=False)
    logger.info(f"Forecast: {len(forecast_df):,} records")

    pipeline_df = generate_projects_pipeline()
    pipeline_df.to_parquet(DATA_DIR / "projects_pipeline.parquet", index=False)
    logger.info(f"Pipeline: {len(pipeline_df):,} records")

    logger.info("Silver layer (core tables) complete!")

    # Generate Bronze layer (raw streaming simulation)
    generate_bronze_layer(telemetry_df, events_df, sites_df)

    # Generate Gold layer (aggregates and rollups)
    generate_gold_layer(sites_df, telemetry_df, settlement_df, events_df)

    logger.info("Data generation complete!")
    logger.info(f"Files saved to: {DATA_DIR}")

    # Print summary
    print("\n=== Data Generation Summary (Medallion Architecture) ===")
    print(f"Period: {start_date.date()} to {end_date.date()}")
    print(f"Sites: {len(sites_df)}")
    print(f"Assets: {len(assets_df)}")
    print(f"\nSilver Layer (Core Tables):")
    print(f"  - Telemetry records: {len(telemetry_df):,}")
    print(f"  - Dispatch records: {len(dispatch_df):,}")
    print(f"  - Events: {len(events_df)}")
    print(f"  - Settlement records: {len(settlement_df)}")
    print(f"  - Maintenance tickets: {len(maintenance_df)}")
    print(f"\nBronze Layer: {BRONZE_DIR}")
    print(f"Gold Layer: {GOLD_DIR}")


if __name__ == "__main__":
    main()
