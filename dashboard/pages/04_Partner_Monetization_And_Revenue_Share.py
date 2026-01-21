"""
ENKA Partner Monetization & Revenue Share

Partner payout tracking, SLA performance, and revenue share calculations.
"""

import sys
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from dashboard.components.branding import apply_enka_theme, render_sidebar_branding, render_footer, style_plotly_chart
from dashboard.components.header import get_dashboard_config, render_header
from db.loader import get_connection

st.set_page_config(page_title="Partner Monetization", page_icon="💰", layout="wide")

# Apply ENKA branding
apply_enka_theme()
render_sidebar_branding()


DASHBOARD_KEY = "enka_partner_monetization"


@st.cache_data(ttl=300)
def load_partner_data():
    """Load partner revenue share data."""
    conn = get_connection()

    partners = conn.execute("""
        SELECT
            p.partner_id,
            p.name as partner_name,
            p.site_id,
            s.name as site_name,
            p.revenue_share_pct
        FROM dim_partner p
        JOIN dim_site s ON p.site_id = s.site_id
    """).df()

    revenue = conn.execute("""
        SELECT
            partner_id,
            partner_name,
            site_id,
            SUM(gross_revenue) as gross_revenue,
            SUM(partner_share) as partner_share
        FROM v_partner_revenue
        WHERE date >= DATE_TRUNC('month', (SELECT MAX(date) FROM fact_settlement))
        GROUP BY partner_id, partner_name, site_id
    """).df()

    # Monthly trend
    monthly_revenue = conn.execute("""
        SELECT
            partner_id,
            partner_name,
            DATE_TRUNC('day', date) as date,
            SUM(gross_revenue) as gross_revenue,
            SUM(partner_share) as partner_share
        FROM v_partner_revenue
        GROUP BY partner_id, partner_name, DATE_TRUNC('day', date)
        ORDER BY date
    """).df()

    # SLA compliance
    sla_compliance = conn.execute("""
        SELECT
            site_id,
            site_name,
            metric_name,
            threshold,
            actual_value,
            status,
            penalty_rate_per_hour
        FROM v_sla_compliance
    """).df()

    conn.close()
    return partners, revenue, monthly_revenue, sla_compliance


def main():
    partners, revenue, monthly_revenue, sla_compliance = load_partner_data()

    # Calculate KPI values
    total_gross = revenue["gross_revenue"].sum() if not revenue.empty else 0
    total_share = revenue["partner_share"].sum() if not revenue.empty else 0
    compliance_rate = (sla_compliance["status"] == "COMPLIANT").mean() * 100 if not sla_compliance.empty else 0
    breaches = (sla_compliance["status"] == "BREACH").sum() if not sla_compliance.empty else 0

    kpi_values = {
        "partner_revenue_share_mtd": total_share,
        "sla_compliance_pct": compliance_rate,
        "pending_disputes": 2,  # Mock
        "partner_count": len(partners),
        "avg_revenue_share_pct": partners["revenue_share_pct"].mean() if not partners.empty else 0,
        "ytd_partner_payouts": total_share * 3,  # Estimate
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

    # Revenue share by partner
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Partner Revenue Share MTD")
        if not revenue.empty:
            fig = px.bar(
                revenue,
                x="partner_name",
                y=["gross_revenue", "partner_share"],
                barmode="group",
                title="Gross Revenue vs Partner Share (£)",
            )
            fig.update_layout(height=350)
            st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.subheader("Revenue Share Distribution")
        if not partners.empty:
            fig = px.pie(
                partners,
                values="revenue_share_pct",
                names="partner_name",
                title="Revenue Share % by Partner",
            )
            fig.update_layout(height=350)
            st.plotly_chart(fig, use_container_width=True)

    # Revenue trend
    st.subheader("Daily Partner Revenue Trend")
    if not monthly_revenue.empty:
        fig = px.line(
            monthly_revenue,
            x="date",
            y="partner_share",
            color="partner_name",
            title="Daily Partner Share (£)",
        )
        fig.update_layout(height=300)
        st.plotly_chart(fig, use_container_width=True)

    # SLA Compliance
    st.subheader("SLA Compliance Status")

    col1, col2 = st.columns([2, 1])

    with col1:
        if not sla_compliance.empty:
            # Color code by status
            sla_display = sla_compliance.copy()
            sla_display["status_color"] = sla_display["status"].map({
                "COMPLIANT": "🟢",
                "BREACH": "🔴"
            })

            st.dataframe(
                sla_display[[
                    "site_name", "metric_name", "threshold", "actual_value", "status_color"
                ]].rename(columns={
                    "site_name": "Site",
                    "metric_name": "Metric",
                    "threshold": "Threshold",
                    "actual_value": "Actual",
                    "status_color": "Status"
                }),
                use_container_width=True,
                height=250,
            )

    with col2:
        st.metric("Compliance Rate", f"{compliance_rate:.1f}%")
        st.metric("Active Breaches", int(breaches))

        if breaches > 0:
            penalty_exposure = sla_compliance[
                sla_compliance["status"] == "BREACH"
            ]["penalty_rate_per_hour"].sum() * 24
            st.metric("Penalty Exposure (Daily)", f"£{penalty_exposure:,.0f}")

    # Partner details table
    st.subheader("Partner Details")
    if not partners.empty:
        st.dataframe(
            partners[[
                "partner_name", "site_name", "revenue_share_pct"
            ]].rename(columns={
                "partner_name": "Partner",
                "site_name": "Site",
                "revenue_share_pct": "Revenue Share %"
            }),
            use_container_width=True,
        )


if __name__ == "__main__":
    main()
