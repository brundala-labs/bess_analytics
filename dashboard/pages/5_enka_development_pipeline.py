"""
ENKA Development Pipeline & Deployment Tracking

Project pipeline tracking, milestone monitoring, and capacity forecasting.
"""

import sys
from pathlib import Path
from datetime import datetime, date

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from dashboard.components.header import get_dashboard_config, render_header
from db.loader import get_connection

st.set_page_config(page_title="Development Pipeline", page_icon="🏗️", layout="wide")

DASHBOARD_KEY = "enka_development_pipeline"


@st.cache_data(ttl=300)
def load_pipeline_data():
    """Load project pipeline data."""
    conn = get_connection()

    pipeline = conn.execute("SELECT * FROM projects_pipeline").df()

    # Convert expected_cod to datetime
    pipeline["expected_cod"] = pd.to_datetime(pipeline["expected_cod"])

    conn.close()
    return pipeline


def main():
    pipeline = load_pipeline_data()

    # Calculate KPIs
    in_flight = len(pipeline)
    total_mw = pipeline["mw_capacity"].sum()
    on_schedule = (pipeline["status"] == "On Track").sum()
    delayed = (pipeline["status"].isin(["Delayed", "At Risk"])).sum()

    # Next 8 months
    cutoff = datetime.now() + pd.DateOffset(months=8)
    next_8mo = pipeline[pipeline["expected_cod"] <= cutoff]["mw_capacity"].sum()

    # Pipeline value estimate (£2M per MW for BESS)
    pipeline_value = total_mw * 2_000_000

    kpi_values = {
        "projects_in_flight": in_flight,
        "mw_under_development": total_mw,
        "on_schedule_count": int(on_schedule),
        "delayed_projects": int(delayed),
        "next_8month_capacity_mw": next_8mo,
        "pipeline_value_gbp": pipeline_value,
    }

    config = get_dashboard_config(DASHBOARD_KEY)

    kpis = []
    for kpi_def in config.get("kpis", []):
        kpis.append({
            "label": kpi_def.get("label"),
            "value": kpi_values.get(kpi_def.get("metric")),
            "format": kpi_def.get("format", "number"),
        })

    render_header(
        title=config.get("title"),
        personas=config.get("personas", []),
        decisions=config.get("decisions", []),
        data_sources=config.get("data_sources", []),
        freshness=config.get("freshness", ""),
        kpis=kpis,
    )

    # Pipeline overview
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Project Status Distribution")
        status_counts = pipeline.groupby("status").size().reset_index(name="count")
        fig = px.pie(
            status_counts,
            values="count",
            names="status",
            color="status",
            color_discrete_map={
                "On Track": "#4caf50",
                "At Risk": "#ff9800",
                "Delayed": "#f44336"
            },
            title="Projects by Status"
        )
        fig.update_layout(height=300)
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.subheader("Capacity by Stage")
        stage_capacity = pipeline.groupby("stage")["mw_capacity"].sum().reset_index()
        fig = px.bar(
            stage_capacity,
            x="stage",
            y="mw_capacity",
            color="mw_capacity",
            title="MW by Development Stage"
        )
        fig.update_layout(height=300)
        st.plotly_chart(fig, use_container_width=True)

    # Timeline view
    st.subheader("Project Timeline (Expected COD)")

    # Create Gantt-like visualization
    timeline_df = pipeline.copy()
    timeline_df["start"] = datetime.now()
    timeline_df["end"] = timeline_df["expected_cod"]

    fig = px.timeline(
        timeline_df,
        x_start="start",
        x_end="end",
        y="name",
        color="status",
        color_discrete_map={
            "On Track": "#4caf50",
            "At Risk": "#ff9800",
            "Delayed": "#f44336"
        },
        title="Project Timeline to COD"
    )
    fig.update_layout(height=300)
    st.plotly_chart(fig, use_container_width=True)

    # Capacity forecast
    st.subheader("Cumulative Capacity Coming Online")

    capacity_timeline = pipeline.sort_values("expected_cod").copy()
    capacity_timeline["cumulative_mw"] = capacity_timeline["mw_capacity"].cumsum()

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=capacity_timeline["expected_cod"],
        y=capacity_timeline["cumulative_mw"],
        mode="lines+markers",
        name="Cumulative MW",
        fill="tozeroy"
    ))
    fig.update_layout(
        title="Projected Capacity Growth",
        xaxis_title="Expected COD",
        yaxis_title="Cumulative MW",
        height=300
    )
    st.plotly_chart(fig, use_container_width=True)

    # Vendor split
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Capacity by Vendor")
        vendor_capacity = pipeline.groupby("vendor")["mw_capacity"].sum().reset_index()
        fig = px.pie(
            vendor_capacity,
            values="mw_capacity",
            names="vendor",
            title="Pipeline MW by Vendor"
        )
        fig.update_layout(height=280)
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.subheader("Completion Progress")
        fig = px.bar(
            pipeline,
            x="name",
            y="completion_pct",
            color="status",
            color_discrete_map={
                "On Track": "#4caf50",
                "At Risk": "#ff9800",
                "Delayed": "#f44336"
            },
            title="Project Completion %"
        )
        fig.update_layout(height=280)
        st.plotly_chart(fig, use_container_width=True)

    # Project details table
    st.subheader("Project Details")

    display_df = pipeline[[
        "name", "stage", "mw_capacity", "mwh_capacity", "expected_cod", "vendor", "status", "completion_pct"
    ]].copy()

    display_df["expected_cod"] = display_df["expected_cod"].dt.strftime("%Y-%m-%d")

    def color_status(val):
        if val == "On Track":
            return "background-color: #c8e6c9"
        elif val == "At Risk":
            return "background-color: #ffe0b2"
        elif val == "Delayed":
            return "background-color: #ffcdd2"
        return ""

    st.dataframe(
        display_df.rename(columns={
            "name": "Project",
            "stage": "Stage",
            "mw_capacity": "MW",
            "mwh_capacity": "MWh",
            "expected_cod": "Expected COD",
            "vendor": "Vendor",
            "status": "Status",
            "completion_pct": "Complete %"
        }).style.applymap(color_status, subset=["Status"]),
        use_container_width=True,
        height=250,
    )

    # 8-Month deployment view
    st.subheader("8-Month Deployment Outlook")

    next_8_months = pipeline[pipeline["expected_cod"] <= cutoff].sort_values("expected_cod")

    if not next_8_months.empty:
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Projects Due", len(next_8_months))
        with col2:
            st.metric("Total MW", f"{next_8_months['mw_capacity'].sum():.0f}")
        with col3:
            at_risk = next_8_months["status"].isin(["At Risk", "Delayed"]).sum()
            st.metric("At Risk/Delayed", int(at_risk))

        st.dataframe(
            next_8_months[[
                "name", "expected_cod", "mw_capacity", "status", "completion_pct"
            ]].rename(columns={
                "name": "Project",
                "expected_cod": "COD",
                "mw_capacity": "MW",
                "status": "Status",
                "completion_pct": "Complete %"
            }),
            use_container_width=True,
        )
    else:
        st.info("No projects expected within the next 8 months.")


if __name__ == "__main__":
    main()
