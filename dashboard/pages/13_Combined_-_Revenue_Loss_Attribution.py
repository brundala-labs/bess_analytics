"""
Combined Revenue Loss Attribution

Analyze revenue gaps and attribute losses to root causes.
"""

import sys
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from dashboard.components.header import get_dashboard_config, render_header, render_filter_bar
from dashboard.components.kpi_glossary import render_kpi_glossary
from db.loader import get_connection

st.set_page_config(page_title="Revenue Loss Attribution", page_icon="💸", layout="wide")

DASHBOARD_KEY = "combined_revenue_loss"


@st.cache_data(ttl=300)
def load_revenue_data():
    """Load revenue loss attribution data."""
    conn = get_connection()

    # Revenue vs forecast with attribution
    loss_data = conn.execute("""
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
        ORDER BY date DESC
    """).df()

    # Daily summary
    daily_summary = conn.execute("""
        SELECT
            date,
            SUM(forecast_revenue) as total_forecast,
            SUM(actual_revenue) as total_actual,
            SUM(revenue_gap) as total_gap
        FROM v_revenue_loss_attribution
        GROUP BY date
        ORDER BY date
    """).df()

    # Event-based losses
    event_losses = conn.execute("""
        SELECT
            e.site_id,
            s.name as site_name,
            e.event_type,
            COUNT(*) as event_count,
            SUM(EXTRACT(EPOCH FROM (e.end_ts - e.start_ts)) / 3600) as total_hours,
            SUM(EXTRACT(EPOCH FROM (e.end_ts - e.start_ts)) / 3600) * 50 as estimated_loss  -- Assume £50/hr/site
        FROM fact_events e
        JOIN dim_site s ON e.site_id = s.site_id
        WHERE e.event_type IN ('fault', 'trip', 'comms_drop')
        GROUP BY e.site_id, s.name, e.event_type
    """).df()

    sites = conn.execute("SELECT site_id, name FROM dim_site").df().to_dict(orient="records")

    conn.close()
    return loss_data, daily_summary, event_losses, sites


def categorize_loss(row):
    """Categorize loss by root cause."""
    if row["fault_minutes"] + row["trip_minutes"] > 60:
        return "Faults/Trips"
    elif row["data_completeness"] < 95:
        return "Data Gaps"
    elif row["revenue_gap"] > row["forecast_revenue"] * 0.1:
        return "Market Conditions"
    else:
        return "Other"


def main():
    loss_data, daily_summary, event_losses, sites = load_revenue_data()

    # Add loss category
    loss_data["loss_category"] = loss_data.apply(categorize_loss, axis=1)

    # Calculate KPIs
    # MTD losses
    if not loss_data.empty:
        mtd_data = loss_data[loss_data["date"] >= loss_data["date"].max().replace(day=1)]
        total_loss = mtd_data["revenue_gap"].sum()
        loss_from_faults = mtd_data[mtd_data["loss_category"] == "Faults/Trips"]["revenue_gap"].sum()
        loss_from_curtailment = mtd_data[mtd_data["loss_category"] == "Market Conditions"]["revenue_gap"].sum()
        loss_from_gaps = mtd_data[mtd_data["loss_category"] == "Data Gaps"]["revenue_gap"].sum()

        recovery_rate = (mtd_data["actual_revenue"].sum() / mtd_data["forecast_revenue"].sum()) * 100 if mtd_data["forecast_revenue"].sum() > 0 else 100
        top_loss_site = mtd_data.groupby("site_name")["revenue_gap"].sum().idxmax() if not mtd_data.empty else "N/A"
    else:
        total_loss = 0
        loss_from_faults = 0
        loss_from_curtailment = 0
        loss_from_gaps = 0
        recovery_rate = 100
        top_loss_site = "N/A"

    kpi_values = {
        "revenue_loss_mtd": total_loss,
        "loss_from_faults": loss_from_faults,
        "loss_from_curtailment": loss_from_curtailment,
        "loss_from_data_gaps": loss_from_gaps,
        "revenue_recovery_rate": recovery_rate,
        "top_loss_site": top_loss_site,
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

    # Filters
    filters = render_filter_bar(show_site=True, show_date_range=True, sites=sites)

    # Filter data
    filtered = loss_data.copy()
    if filters.get("site_id"):
        filtered = filtered[filtered["site_id"] == filters["site_id"]]

    # Revenue gap trend
    st.subheader("Revenue Gap Trend")

    if not daily_summary.empty:
        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=daily_summary["date"],
            y=daily_summary["total_forecast"],
            name="Forecast",
            marker_color="lightblue"
        ))
        fig.add_trace(go.Bar(
            x=daily_summary["date"],
            y=daily_summary["total_actual"],
            name="Actual",
            marker_color="darkblue"
        ))
        fig.add_trace(go.Scatter(
            x=daily_summary["date"],
            y=daily_summary["total_gap"],
            name="Gap",
            mode="lines+markers",
            line=dict(color="red"),
            yaxis="y2"
        ))
        fig.update_layout(
            height=350,
            barmode="overlay",
            yaxis2=dict(
                title="Revenue Gap (£)",
                overlaying="y",
                side="right"
            ),
            title="Daily Forecast vs Actual Revenue"
        )
        st.plotly_chart(fig, use_container_width=True)

    # Loss attribution
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Loss Attribution (MTD)")
        if not filtered.empty:
            category_totals = filtered.groupby("loss_category")["revenue_gap"].sum().reset_index()
            category_totals = category_totals[category_totals["revenue_gap"] > 0]

            if not category_totals.empty:
                fig = px.pie(
                    category_totals,
                    values="revenue_gap",
                    names="loss_category",
                    color="loss_category",
                    color_discrete_map={
                        "Faults/Trips": "#d32f2f",
                        "Data Gaps": "#ff9800",
                        "Market Conditions": "#2196f3",
                        "Other": "#9e9e9e"
                    },
                    title="Revenue Loss by Category"
                )
                fig.update_layout(height=300)
                st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.subheader("Loss by Site")
        if not filtered.empty:
            site_totals = filtered.groupby("site_name")["revenue_gap"].sum().reset_index()
            site_totals = site_totals.sort_values("revenue_gap", ascending=False)

            fig = px.bar(
                site_totals,
                x="site_name",
                y="revenue_gap",
                color="revenue_gap",
                color_continuous_scale="Reds",
                title="Total Revenue Gap by Site"
            )
            fig.update_layout(height=300)
            st.plotly_chart(fig, use_container_width=True)

    # Event-based losses
    st.subheader("Event-Based Loss Analysis")

    if not event_losses.empty:
        col1, col2 = st.columns(2)

        with col1:
            fig = px.bar(
                event_losses.groupby("event_type")["estimated_loss"].sum().reset_index(),
                x="event_type",
                y="estimated_loss",
                color="event_type",
                title="Estimated Loss by Event Type (£)"
            )
            fig.update_layout(height=280)
            st.plotly_chart(fig, use_container_width=True)

        with col2:
            fig = px.bar(
                event_losses.groupby("site_name")["total_hours"].sum().reset_index(),
                x="site_name",
                y="total_hours",
                color="total_hours",
                color_continuous_scale="Reds",
                title="Total Downtime Hours by Site"
            )
            fig.update_layout(height=280)
            st.plotly_chart(fig, use_container_width=True)

    # Detailed loss table
    st.subheader("Daily Loss Details")

    if not filtered.empty:
        display = filtered[[
            "date", "site_name", "forecast_revenue", "actual_revenue",
            "revenue_gap", "loss_category", "fault_minutes", "data_completeness"
        ]].head(50).copy()

        def highlight_loss(row):
            if row["Category"] == "Faults/Trips":
                return ["background-color: #ffcdd2"] * len(row)
            elif row["Category"] == "Data Gaps":
                return ["background-color: #ffe0b2"] * len(row)
            return [""] * len(row)

        display_renamed = display.rename(columns={
            "date": "Date",
            "site_name": "Site",
            "forecast_revenue": "Forecast (£)",
            "actual_revenue": "Actual (£)",
            "revenue_gap": "Gap (£)",
            "loss_category": "Category",
            "fault_minutes": "Fault Min",
            "data_completeness": "Data %"
        })

        st.dataframe(
            display_renamed.style.apply(highlight_loss, axis=1).format({
                "Forecast (£)": "£{:,.0f}",
                "Actual (£)": "£{:,.0f}",
                "Gap (£)": "£{:,.0f}",
                "Fault Min": "{:.0f}",
                "Data %": "{:.1f}%"
            }),
            use_container_width=True,
            height=350,
        )

    # Action recommendations
    st.subheader("Recommended Actions")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown("**Faults/Trips**")
        if loss_from_faults > 0:
            st.warning(f"£{loss_from_faults:,.0f} lost to equipment failures")
            st.markdown("- Review fault codes for patterns")
            st.markdown("- Schedule preventive maintenance")
            st.markdown("- Consider vendor escalation")
        else:
            st.success("No significant fault-related losses")

    with col2:
        st.markdown("**Data Gaps**")
        if loss_from_gaps > 0:
            st.warning(f"£{loss_from_gaps:,.0f} lost to data issues")
            st.markdown("- Check communication links")
            st.markdown("- Verify SCADA configuration")
            st.markdown("- Improve data validation")
        else:
            st.success("No significant data-related losses")

    with col3:
        st.markdown("**Market/Curtailment**")
        if loss_from_curtailment > 0:
            st.info(f"£{loss_from_curtailment:,.0f} due to market conditions")
            st.markdown("- Review trading strategy")
            st.markdown("- Analyze price forecasts")
            st.markdown("- Consider hedging options")
        else:
            st.success("Market performance on target")

    # KPI Glossary
    st.divider()
    render_kpi_glossary(
        kpi_keys=["lost_revenue_gbp", "availability_pct", "dispatch_adherence_pct", "comms_health"],
        title="KPI Definitions And Sources"
    )


if __name__ == "__main__":
    main()
