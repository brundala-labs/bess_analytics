"""
KPI Glossary Component

Provides expandable KPI definitions and lineage information for dashboards.
"""

import yaml
from pathlib import Path
from typing import List, Optional

import streamlit as st


def load_kpi_dictionary() -> dict:
    """Load the KPI dictionary from YAML file."""
    dict_path = Path(__file__).parent.parent.parent / "docs" / "kpi_dictionary.yaml"

    if not dict_path.exists():
        return {"kpis": {}}

    with open(dict_path, "r") as f:
        return yaml.safe_load(f)


def render_kpi_glossary(
    kpi_keys: List[str],
    title: str = "KPI Definitions And Sources",
    expanded: bool = False
) -> None:
    """
    Render an expandable KPI glossary section.

    Args:
        kpi_keys: List of KPI keys to display (e.g., ["soc_pct", "soh_pct"])
        title: Title for the expander section
        expanded: Whether to expand by default
    """
    if not kpi_keys:
        return

    kpi_dict = load_kpi_dictionary()
    kpis = kpi_dict.get("kpis", {})

    with st.expander(f"📖 {title}", expanded=expanded):
        # Group KPIs for display
        for key in kpi_keys:
            kpi = kpis.get(key)
            if not kpi:
                continue

            st.markdown(f"### {kpi.get('display_name', key)}")

            col1, col2 = st.columns([2, 1])

            with col1:
                st.markdown(f"**Definition:** {kpi.get('definition', 'N/A')}")
                st.markdown(f"**Units:** `{kpi.get('units', 'N/A')}`")
                st.markdown(f"**Calculation:** `{kpi.get('calculation_demo', 'N/A')}`")

                # Assumptions
                assumptions = kpi.get("assumptions", "")
                if assumptions:
                    st.caption(f"💡 {assumptions}")

            with col2:
                # Lineage information
                lineage = kpi.get("lineage", {})
                tables = lineage.get("tables", [])
                tags = lineage.get("tags", [])

                st.markdown("**Data Lineage:**")
                if tables:
                    st.markdown(f"Tables: `{', '.join(tables)}`")
                if tags:
                    st.markdown(f"Tags: `{', '.join(tags)}`")

                source = kpi.get("source_label", "")
                if source:
                    st.caption(f"📚 {source}")

            st.divider()


def render_kpi_card(
    kpi_key: str,
    value: Optional[float] = None,
    delta: Optional[float] = None,
    show_definition: bool = True
) -> None:
    """
    Render a single KPI metric card with optional definition tooltip.

    Args:
        kpi_key: KPI key from the dictionary
        value: Current value to display
        delta: Change from previous period
        show_definition: Whether to show definition on hover
    """
    kpi_dict = load_kpi_dictionary()
    kpi = kpi_dict.get("kpis", {}).get(kpi_key, {})

    label = kpi.get("display_name", kpi_key)
    units = kpi.get("units", "")
    definition = kpi.get("definition", "")

    # Format value based on units
    if value is not None:
        if units == "%":
            formatted_value = f"{value:.1f}%"
        elif units == "GBP":
            formatted_value = f"£{value:,.0f}"
        elif units == "Hours":
            formatted_value = f"{value:.1f} hrs"
        elif units == "Days":
            formatted_value = f"{value:.1f} days"
        elif units == "Count":
            formatted_value = f"{int(value)}"
        else:
            formatted_value = f"{value:,.2f}"
    else:
        formatted_value = "N/A"

    # Render metric
    if delta is not None:
        st.metric(label=label, value=formatted_value, delta=f"{delta:+.1f}")
    else:
        st.metric(label=label, value=formatted_value)

    # Show definition as caption if enabled
    if show_definition and definition:
        st.caption(definition[:100] + "..." if len(definition) > 100 else definition)


def get_kpi_info(kpi_key: str) -> dict:
    """
    Get full information for a specific KPI.

    Args:
        kpi_key: KPI key from the dictionary

    Returns:
        Dictionary with KPI information or empty dict if not found
    """
    kpi_dict = load_kpi_dictionary()
    return kpi_dict.get("kpis", {}).get(kpi_key, {})


def get_all_kpi_keys() -> List[str]:
    """Get list of all available KPI keys."""
    kpi_dict = load_kpi_dictionary()
    return list(kpi_dict.get("kpis", {}).keys())


def render_mini_glossary(kpi_keys: List[str]) -> None:
    """
    Render a compact inline glossary (useful for headers).

    Args:
        kpi_keys: List of KPI keys to display
    """
    kpi_dict = load_kpi_dictionary()
    kpis = kpi_dict.get("kpis", {})

    glossary_items = []
    for key in kpi_keys:
        kpi = kpis.get(key)
        if kpi:
            name = kpi.get("display_name", key)
            units = kpi.get("units", "")
            glossary_items.append(f"**{name}** ({units})")

    if glossary_items:
        st.caption(" | ".join(glossary_items))
