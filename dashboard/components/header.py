"""
BESS Analytics - Dashboard Header Component

Reusable header component that displays:
- Personas
- Decisions
- Data Sources
- Data Freshness
- KPI Tiles
"""

from pathlib import Path
from typing import Any, Optional

import streamlit as st
import yaml


def load_catalog() -> dict:
    """Load the dashboard catalog YAML file."""
    catalog_path = Path(__file__).parent.parent / "dashboard_catalog.yaml"
    with open(catalog_path, "r") as f:
        return yaml.safe_load(f)


def get_dashboard_config(dashboard_key: str) -> dict:
    """Get configuration for a specific dashboard."""
    catalog = load_catalog()
    return catalog.get("dashboards", {}).get(dashboard_key, {})


def format_kpi_value(value: Any, format_type: str) -> str:
    """Format KPI value based on its type."""
    if value is None:
        return "N/A"

    if format_type == "currency":
        if abs(value) >= 1_000_000:
            return f"£{value/1_000_000:.1f}M"
        elif abs(value) >= 1_000:
            return f"£{value/1_000:.1f}K"
        else:
            return f"£{value:.0f}"
    elif format_type == "percent":
        return f"{value:.1f}%"
    elif format_type == "integer":
        return f"{int(value):,}"
    elif format_type == "number":
        if abs(value) >= 1_000_000:
            return f"{value/1_000_000:.1f}M"
        elif abs(value) >= 1_000:
            return f"{value/1_000:.1f}K"
        else:
            return f"{value:.1f}"
    elif format_type == "mwh":
        return f"{value:,.0f} MWh"
    elif format_type == "mw":
        return f"{value:,.0f} MW"
    elif format_type == "text":
        return str(value)
    else:
        return str(value)


def render_header(
    title: str,
    personas: list[str],
    decisions: list[str],
    data_sources: list[dict],
    freshness: str,
    kpis: list[dict],
    show_info_expanded: bool = False,
):
    """
    Render a standardized dashboard header with metadata and KPIs.

    Parameters:
    -----------
    title : str
        Dashboard title
    personas : list[str]
        List of user personas who use this dashboard
    decisions : list[str]
        List of decisions made using this dashboard
    data_sources : list[dict]
        List of data sources with keys: system, tables, notes
    freshness : str
        Expected data update frequency
    kpis : list[dict]
        List of KPIs with keys: label, value, delta (optional), format
    show_info_expanded : bool
        Whether to show the info expander as expanded by default
    """

    # Title
    st.title(title)

    # Info section in an expander
    with st.expander("Dashboard Info", expanded=show_info_expanded):
        col1, col2 = st.columns(2)

        with col1:
            # Personas
            st.markdown("**Personas**")
            persona_tags = " ".join([f"`{p}`" for p in personas])
            st.markdown(persona_tags)

            # Data Freshness
            st.markdown("**Data Freshness**")
            st.info(freshness)

        with col2:
            # Key Decisions
            st.markdown("**Key Decisions**")
            for decision in decisions[:4]:  # Limit to 4
                st.markdown(f"- {decision}")

        # Data Sources - Show system names prominently
        st.markdown("**Data Sources**")

        # Display all source systems as tags
        system_names = [source.get("system", "Unknown") for source in data_sources]
        system_tags = " ".join([f"`{name}`" for name in system_names])
        st.markdown(system_tags)

        # Show details in a more compact format
        st.markdown("")  # Spacer
        for source in data_sources:
            system_name = source.get("system", "Unknown")
            notes = source.get("notes", "")
            if notes:
                st.caption(f"**{system_name}**: {notes}")

    # KPI Tiles
    st.markdown("---")
    render_kpi_tiles(kpis)
    st.markdown("---")


def render_kpi_tiles(kpis: list[dict], columns: int = None):
    """
    Render KPI metric tiles.

    Parameters:
    -----------
    kpis : list[dict]
        List of KPIs with keys: label, value, delta (optional), format
    columns : int
        Number of columns (default: len(kpis) up to 6)
    """
    if not kpis:
        return

    num_cols = columns or min(len(kpis), 6)
    cols = st.columns(num_cols)

    for idx, kpi in enumerate(kpis):
        with cols[idx % num_cols]:
            label = kpi.get("label", "Metric")
            value = kpi.get("value")
            delta = kpi.get("delta")
            format_type = kpi.get("format", "number")

            formatted_value = format_kpi_value(value, format_type)

            # Handle delta formatting
            delta_str = None
            if delta is not None:
                if format_type == "currency":
                    delta_str = f"£{abs(delta):.0f}" if delta >= 0 else f"-£{abs(delta):.0f}"
                elif format_type == "percent":
                    delta_str = f"{delta:+.1f}%"
                else:
                    delta_str = f"{delta:+.1f}"

            st.metric(
                label=label,
                value=formatted_value,
                delta=delta_str,
            )


def render_filter_bar(
    show_site: bool = True,
    show_date_range: bool = True,
    show_vendor: bool = False,
    show_service: bool = False,
    sites: list[dict] = None,
    vendors: list[str] = None,
    services: list[dict] = None,
) -> dict:
    """
    Render a standardized filter bar.

    Returns:
    --------
    dict with selected filter values
    """
    filters = {}

    cols = st.columns(4)

    if show_site and sites:
        with cols[0]:
            site_options = ["All Sites"] + [s["name"] for s in sites]
            selected_site = st.selectbox("Site", site_options)
            if selected_site != "All Sites":
                site_match = [s for s in sites if s["name"] == selected_site]
                filters["site_id"] = site_match[0]["site_id"] if site_match else None
            else:
                filters["site_id"] = None

    if show_date_range:
        with cols[1]:
            from datetime import date, timedelta
            default_end = date(2024, 3, 15)  # Match generated data
            default_start = default_end - timedelta(days=7)
            date_range = st.date_input(
                "Date Range",
                value=(default_start, default_end),
            )
            if isinstance(date_range, tuple) and len(date_range) == 2:
                filters["start_date"] = date_range[0]
                filters["end_date"] = date_range[1]
            else:
                filters["start_date"] = date_range[0] if date_range else default_start
                filters["end_date"] = default_end

    if show_vendor and vendors:
        with cols[2]:
            vendor_options = ["All Vendors"] + vendors
            selected_vendor = st.selectbox("Vendor", vendor_options)
            filters["vendor"] = None if selected_vendor == "All Vendors" else selected_vendor

    if show_service and services:
        with cols[3]:
            service_options = ["All Services"] + [s["name"] for s in services]
            selected_service = st.selectbox("Service", service_options)
            if selected_service != "All Services":
                service_match = [s for s in services if s["name"] == selected_service]
                filters["service_id"] = service_match[0]["service_id"] if service_match else None
            else:
                filters["service_id"] = None

    return filters


def render_drilldown_table(
    data: list[dict],
    title: str = "Details",
    columns: list[str] = None,
    height: int = 400,
):
    """
    Render a drilldown data table.

    Parameters:
    -----------
    data : list[dict]
        Data to display
    title : str
        Table title
    columns : list[str]
        Columns to display (default: all)
    height : int
        Table height in pixels
    """
    import pandas as pd

    st.subheader(title)

    if not data:
        st.info("No data available")
        return

    df = pd.DataFrame(data)

    if columns:
        df = df[[c for c in columns if c in df.columns]]

    st.dataframe(df, height=height, use_container_width=True)


def create_dashboard_page(
    dashboard_key: str,
    kpi_values: dict,
    render_content_func,
):
    """
    Create a complete dashboard page using the catalog configuration.

    Parameters:
    -----------
    dashboard_key : str
        Key in the dashboard catalog
    kpi_values : dict
        Dictionary mapping KPI metrics to their values
    render_content_func : callable
        Function that renders the main dashboard content
    """
    config = get_dashboard_config(dashboard_key)

    if not config:
        st.error(f"Dashboard configuration not found: {dashboard_key}")
        return

    # Build KPIs with values
    kpis = []
    for kpi_def in config.get("kpis", []):
        metric_name = kpi_def.get("metric")
        kpis.append({
            "label": kpi_def.get("label"),
            "value": kpi_values.get(metric_name),
            "delta": kpi_values.get(f"{metric_name}_delta"),
            "format": kpi_def.get("format", "number"),
        })

    # Render header
    render_header(
        title=config.get("title", "Dashboard"),
        personas=config.get("personas", []),
        decisions=config.get("decisions", []),
        data_sources=config.get("data_sources", []),
        freshness=config.get("freshness", "Unknown"),
        kpis=kpis,
    )

    # Render main content
    render_content_func()
