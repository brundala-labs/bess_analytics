"""
BESS Analytics - Unit Tests

Tests for data generation, database operations, and metric calculations.
"""

import sys
from datetime import datetime, timedelta
from pathlib import Path

import pytest
import pandas as pd
import numpy as np

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))


class TestDataGeneration:
    """Tests for data generation module."""

    def test_generate_dim_site(self):
        """Test site dimension generation."""
        from data_gen.generate import generate_dim_site

        sites = generate_dim_site()

        assert len(sites) == 3
        assert "site_id" in sites.columns
        assert "vendor_controller" in sites.columns
        assert set(sites["vendor_controller"].unique()) == {"TMEIC", "OtherPCS"}

    def test_generate_dim_asset(self):
        """Test asset dimension generation."""
        from data_gen.generate import generate_dim_site, generate_dim_asset

        sites = generate_dim_site()
        assets = generate_dim_asset(sites)

        # Each site should have: 1 controller + 2 inverters + 4 battery racks = 7
        assert len(assets) == 3 * 7
        assert set(assets["asset_type"].unique()) == {"controller", "inverter", "battery_rack"}

    def test_generate_dim_service(self):
        """Test service dimension generation."""
        from data_gen.generate import generate_dim_service

        services = generate_dim_service()

        assert len(services) == 4
        assert "arbitrage" in services["name"].values
        assert "frequency_response" in services["name"].values

    def test_generate_dim_partner(self):
        """Test partner dimension generation."""
        from data_gen.generate import generate_dim_site, generate_dim_partner

        sites = generate_dim_site()
        partners = generate_dim_partner(sites)

        assert len(partners) == 3  # One partner per site
        assert all(partners["revenue_share_pct"] > 0)
        assert all(partners["revenue_share_pct"] <= 100)

    def test_generate_dim_sla(self):
        """Test SLA dimension generation."""
        from data_gen.generate import generate_dim_site, generate_dim_sla

        sites = generate_dim_site()
        slas = generate_dim_sla(sites)

        # 3 SLA types per site
        assert len(slas) == 3 * 3
        assert all(slas["threshold"] > 0)
        assert all(slas["penalty_rate_per_hour"] > 0)

    def test_generate_price_curve(self):
        """Test price curve generation."""
        from data_gen.generate import generate_price_curve

        prices = generate_price_curve(7)  # 7 days

        assert len(prices) == 7 * 24  # Hourly prices
        assert all(prices >= 0)  # No negative prices
        assert np.mean(prices) > 0

    def test_generate_projects_pipeline(self):
        """Test pipeline data generation."""
        from data_gen.generate import generate_projects_pipeline

        pipeline = generate_projects_pipeline()

        assert len(pipeline) >= 4
        assert "project_id" in pipeline.columns
        assert "mw_capacity" in pipeline.columns
        assert all(pipeline["completion_pct"] >= 0)
        assert all(pipeline["completion_pct"] <= 100)


class TestDashboardComponents:
    """Tests for dashboard components."""

    def test_load_catalog(self):
        """Test dashboard catalog loading."""
        from dashboard.components.header import load_catalog

        catalog = load_catalog()

        assert "dashboards" in catalog
        assert "upstream_systems" in catalog
        assert len(catalog["dashboards"]) == 14

    def test_get_dashboard_config(self):
        """Test getting specific dashboard config."""
        from dashboard.components.header import get_dashboard_config

        config = get_dashboard_config("enka_portfolio_executive")

        assert config["title"] == "Portfolio Executive Cockpit"
        assert "personas" in config
        assert "decisions" in config
        assert "data_sources" in config
        assert "freshness" in config
        assert "kpis" in config

    def test_format_kpi_value_currency(self):
        """Test KPI value formatting for currency."""
        from dashboard.components.header import format_kpi_value

        assert format_kpi_value(1500000, "currency") == "£1.5M"
        assert format_kpi_value(150000, "currency") == "£150.0K"
        assert format_kpi_value(150, "currency") == "£150"

    def test_format_kpi_value_percent(self):
        """Test KPI value formatting for percentage."""
        from dashboard.components.header import format_kpi_value

        assert format_kpi_value(95.5, "percent") == "95.5%"
        assert format_kpi_value(100, "percent") == "100.0%"

    def test_format_kpi_value_integer(self):
        """Test KPI value formatting for integers."""
        from dashboard.components.header import format_kpi_value

        assert format_kpi_value(1500, "integer") == "1,500"
        assert format_kpi_value(0, "integer") == "0"

    def test_format_kpi_value_none(self):
        """Test KPI value formatting for None."""
        from dashboard.components.header import format_kpi_value

        assert format_kpi_value(None, "currency") == "N/A"
        assert format_kpi_value(None, "percent") == "N/A"


class TestCatalogCompleteness:
    """Tests for dashboard catalog completeness."""

    def test_all_dashboards_have_required_fields(self):
        """Test that all dashboards have required metadata."""
        from dashboard.components.header import load_catalog

        catalog = load_catalog()
        required_fields = ["title", "pack", "personas", "decisions", "data_sources", "freshness", "kpis"]

        for key, config in catalog["dashboards"].items():
            for field in required_fields:
                assert field in config, f"Dashboard {key} missing field: {field}"

    def test_all_dashboards_have_personas(self):
        """Test that all dashboards have at least one persona."""
        from dashboard.components.header import load_catalog

        catalog = load_catalog()

        for key, config in catalog["dashboards"].items():
            assert len(config["personas"]) > 0, f"Dashboard {key} has no personas"

    def test_all_dashboards_have_decisions(self):
        """Test that all dashboards have at least one decision."""
        from dashboard.components.header import load_catalog

        catalog = load_catalog()

        for key, config in catalog["dashboards"].items():
            assert len(config["decisions"]) > 0, f"Dashboard {key} has no decisions"

    def test_all_dashboards_have_data_sources(self):
        """Test that all dashboards have at least one data source."""
        from dashboard.components.header import load_catalog

        catalog = load_catalog()

        for key, config in catalog["dashboards"].items():
            assert len(config["data_sources"]) > 0, f"Dashboard {key} has no data sources"

    def test_all_dashboards_have_kpis(self):
        """Test that all dashboards have KPIs."""
        from dashboard.components.header import load_catalog

        catalog = load_catalog()

        for key, config in catalog["dashboards"].items():
            assert len(config["kpis"]) >= 4, f"Dashboard {key} has fewer than 4 KPIs"

    def test_dashboard_packs(self):
        """Test that dashboards are correctly assigned to packs."""
        from dashboard.components.header import load_catalog

        catalog = load_catalog()
        packs = {"ENKA": 0, "TMEIC": 0, "Combined": 0}

        for key, config in catalog["dashboards"].items():
            pack = config.get("pack")
            assert pack in packs, f"Dashboard {key} has invalid pack: {pack}"
            packs[pack] += 1

        assert packs["ENKA"] == 5
        assert packs["TMEIC"] == 5
        assert packs["Combined"] == 4


class TestDataSourceMapping:
    """Tests for data source to table mapping."""

    def test_data_sources_have_tables(self):
        """Test that data sources specify tables."""
        from dashboard.components.header import load_catalog

        catalog = load_catalog()

        for key, config in catalog["dashboards"].items():
            for source in config["data_sources"]:
                assert "system" in source, f"Dashboard {key} data source missing system"
                assert "tables" in source, f"Dashboard {key} data source missing tables"
                assert len(source["tables"]) > 0, f"Dashboard {key} data source has empty tables"

    def test_valid_table_names(self):
        """Test that referenced tables exist in schema."""
        from dashboard.components.header import load_catalog

        catalog = load_catalog()

        valid_tables = {
            "dim_site", "dim_asset", "dim_service", "dim_partner", "dim_sla",
            "fact_telemetry", "fact_dispatch", "fact_events", "fact_settlement",
            "fact_maintenance", "fact_data_quality", "forecast_revenue",
            "projects_pipeline", "v_site_latest_telemetry", "v_daily_revenue",
            "v_revenue_vs_forecast", "v_site_availability", "v_event_summary",
            "v_partner_revenue", "v_dispatch_compliance", "v_battery_health",
            "v_data_quality_daily", "v_vendor_benchmark", "v_revenue_loss_attribution",
            "v_sla_compliance"
        }

        for key, config in catalog["dashboards"].items():
            for source in config["data_sources"]:
                for table in source["tables"]:
                    assert table in valid_tables, f"Dashboard {key} references invalid table: {table}"


class TestKPIDefinitions:
    """Tests for KPI definitions."""

    def test_kpis_have_required_fields(self):
        """Test that KPIs have label, metric, and format."""
        from dashboard.components.header import load_catalog

        catalog = load_catalog()

        for key, config in catalog["dashboards"].items():
            for kpi in config["kpis"]:
                assert "label" in kpi, f"Dashboard {key} KPI missing label"
                assert "metric" in kpi, f"Dashboard {key} KPI missing metric"
                assert "format" in kpi, f"Dashboard {key} KPI missing format"

    def test_valid_kpi_formats(self):
        """Test that KPI formats are valid."""
        from dashboard.components.header import load_catalog

        catalog = load_catalog()
        valid_formats = {"currency", "percent", "integer", "number", "text"}

        for key, config in catalog["dashboards"].items():
            for kpi in config["kpis"]:
                assert kpi["format"] in valid_formats, f"Dashboard {key} KPI has invalid format: {kpi['format']}"


class TestMetricCalculations:
    """Tests for metric calculation logic."""

    def test_degradation_rate_calculation(self):
        """Test degradation rate calculation."""
        # Create sample health data
        dates = pd.date_range(start="2024-02-15", end="2024-03-15", freq="D")
        health_data = pd.DataFrame({
            "site_id": ["SITE001"] * len(dates),
            "site_name": ["Test Site"] * len(dates),
            "date": dates,
            "avg_soh": np.linspace(98, 95, len(dates))  # Linear degradation
        })

        # Calculate degradation rate
        soh_start = health_data.head(7)["avg_soh"].mean()
        soh_end = health_data.tail(7)["avg_soh"].mean()
        days = (health_data["date"].max() - health_data["date"].min()).days
        monthly_rate = ((soh_start - soh_end) / days) * 30

        assert monthly_rate > 0  # Should show degradation
        assert monthly_rate < 5  # Reasonable rate

    def test_availability_calculation(self):
        """Test availability calculation from status."""
        # 95 minutes online, 5 minutes offline = 95% availability
        statuses = [1.0] * 95 + [0.0] * 5
        availability = sum(statuses) / len(statuses) * 100

        assert availability == 95.0

    def test_revenue_per_cycle_calculation(self):
        """Test revenue per cycle calculation."""
        daily_revenue = 5000  # £5000 per day
        daily_energy_mwh = 100  # 100 MWh discharged
        capacity_mwh = 100  # 100 MWh battery

        daily_cycles = daily_energy_mwh / capacity_mwh
        revenue_per_cycle = daily_revenue / daily_cycles

        assert revenue_per_cycle == 5000.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
