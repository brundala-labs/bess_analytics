"""
ENKA Branding Component

Provides consistent ENKA Energy Transition branding across all dashboard pages.
Brand colors sourced from https://enka-energy.com/
"""

from pathlib import Path
import base64

import streamlit as st


# ENKA Brand Colors
ENKA_GREEN = "#81d742"
ENKA_DARK = "#111111"
ENKA_WHITE = "#ffffff"
ENKA_GRAY = "#32373c"
ENKA_LIGHT_GRAY = "#f0f2f6"
ENKA_ACCENT_GREEN = "#238238"


def get_logo_base64(logo_type: str = "green") -> str:
    """Get base64 encoded logo for embedding in HTML."""
    assets_dir = Path(__file__).parent.parent / "assets"

    if logo_type == "white":
        logo_path = assets_dir / "enka_logo_white.png"
    else:
        logo_path = assets_dir / "enka_logo_green.png"

    if logo_path.exists():
        with open(logo_path, "rb") as f:
            return base64.b64encode(f.read()).decode()
    return ""


def render_enka_logo(width: int = 150, location: str = "sidebar"):
    """
    Render ENKA logo in the specified location.

    Args:
        width: Logo width in pixels
        location: "sidebar" or "main"
    """
    assets_dir = Path(__file__).parent.parent / "assets"
    logo_path = assets_dir / "enka_logo_green.png"

    if logo_path.exists():
        if location == "sidebar":
            st.sidebar.image(str(logo_path), width=width)
        else:
            st.image(str(logo_path), width=width)


def apply_enka_theme():
    """
    Apply ENKA branded CSS styling to the Streamlit app.
    Call this at the start of each page.
    """
    st.markdown(f"""
    <style>
        /* ENKA Brand Colors */
        :root {{
            --enka-green: {ENKA_GREEN};
            --enka-dark: {ENKA_DARK};
            --enka-white: {ENKA_WHITE};
            --enka-gray: {ENKA_GRAY};
            --enka-light-gray: {ENKA_LIGHT_GRAY};
        }}

        /* Sidebar styling - light theme */
        [data-testid="stSidebarNav"] a:hover {{
            color: {ENKA_GREEN} !important;
            background-color: rgba(129, 215, 66, 0.1);
        }}

        [data-testid="stSidebarNav"] a[aria-selected="true"] {{
            background-color: rgba(129, 215, 66, 0.2);
            color: {ENKA_GREEN} !important;
            font-weight: 600;
        }}

        /* Header styling */
        .main-header {{
            font-size: 2.5rem;
            font-weight: bold;
            color: {ENKA_DARK};
            margin-bottom: 1rem;
        }}

        /* Green accent for headers */
        h1, h2, h3, h4 {{
            color: {ENKA_ACCENT_GREEN} !important;
        }}

        /* Primary buttons */
        .stButton > button {{
            background-color: {ENKA_GREEN};
            color: {ENKA_DARK};
            border: none;
            font-weight: 600;
        }}

        .stButton > button:hover {{
            background-color: {ENKA_ACCENT_GREEN};
            color: {ENKA_WHITE};
        }}

        /* Metrics styling */
        [data-testid="stMetricValue"] {{
            color: {ENKA_DARK};
        }}

        [data-testid="stMetricDelta"] svg {{
            stroke: {ENKA_GREEN};
        }}

        /* Tab styling */
        .stTabs [data-baseweb="tab-list"] {{
            gap: 8px;
        }}

        .stTabs [data-baseweb="tab"] {{
            background-color: {ENKA_LIGHT_GRAY};
            border-radius: 4px;
            padding: 8px 16px;
        }}

        .stTabs [aria-selected="true"] {{
            background-color: {ENKA_GREEN} !important;
            color: {ENKA_DARK} !important;
        }}

        /* Expander styling */
        .streamlit-expanderHeader {{
            background-color: {ENKA_LIGHT_GRAY};
            border-radius: 4px;
        }}

        /* Info/Warning/Success boxes */
        .stAlert {{
            border-radius: 4px;
        }}

        /* Success messages use ENKA green */
        [data-testid="stNotification"][data-baseweb="notification"] {{
            background-color: rgba(129, 215, 66, 0.1);
        }}

        /* Divider */
        hr {{
            border-color: {ENKA_LIGHT_GRAY};
        }}

        /* Card-like containers */
        .dashboard-card {{
            background-color: {ENKA_LIGHT_GRAY};
            border-radius: 10px;
            padding: 1rem;
            margin: 0.5rem 0;
            border-left: 4px solid {ENKA_GREEN};
        }}

        /* Pack header styling */
        .pack-header {{
            font-size: 1.5rem;
            font-weight: bold;
            color: {ENKA_GREEN};
            margin-top: 1.5rem;
            margin-bottom: 0.5rem;
        }}

        /* Link styling */
        a {{
            color: {ENKA_GREEN};
        }}

        a:hover {{
            color: {ENKA_ACCENT_GREEN};
        }}

        /* Footer styling */
        .footer {{
            text-align: center;
            padding: 1rem;
            color: {ENKA_GRAY};
            font-size: 0.85rem;
        }}

        /* KPI highlight */
        .metric-highlight {{
            font-size: 2rem;
            font-weight: bold;
            color: {ENKA_GREEN};
        }}

        /* Plotly chart color overrides via CSS */
        .js-plotly-plot .plotly .modebar {{
            background-color: transparent !important;
        }}
    </style>
    """, unsafe_allow_html=True)


def render_sidebar_branding(current_page=None):
    """Render top navigation menu instead of sidebar for full-width layout.

    Args:
        current_page: The current page file name (e.g., "03_Portfolio_Executive_Cockpit")
    """
    # Hide sidebar completely and style for full-width professional look
    st.markdown(f"""
    <style>
        /* Hide default sidebar completely */
        [data-testid="stSidebar"] {{
            display: none !important;
        }}
        [data-testid="stSidebarNav"] {{
            display: none !important;
        }}
        section[data-testid="stSidebar"] {{
            display: none !important;
        }}
        button[kind="header"] {{
            display: none !important;
        }}

        /* Expand main content to full width */
        .main .block-container {{
            padding-left: 2rem !important;
            padding-right: 2rem !important;
            padding-top: 0 !important;
            margin-top: -4rem !important;
            max-width: 100% !important;
            background: #f8f9fa !important;
        }}

        /* Top navigation styling - professional dark bar */
        .nav-container {{
            background: linear-gradient(180deg, {ENKA_DARK} 0%, #1a1a1a 100%);
            margin: 0 -2rem 1.5rem -2rem;
            padding: 0.8rem 2rem;
            border-bottom: 4px solid {ENKA_GREEN};
            box-shadow: 0 4px 15px rgba(0,0,0,0.2);
        }}

        /* Style selectbox for dark background */
        .nav-select div[data-baseweb="select"] > div {{
            background-color: rgba(255,255,255,0.1) !important;
            border: 2px solid {ENKA_GRAY} !important;
            border-radius: 8px !important;
            transition: all 0.2s ease !important;
        }}

        .nav-select div[data-baseweb="select"] > div:hover {{
            border-color: {ENKA_GREEN} !important;
            box-shadow: 0 0 8px rgba(129, 215, 66, 0.3) !important;
        }}

        .nav-select .stSelectbox label {{
            color: {ENKA_WHITE} !important;
            font-weight: 600 !important;
            font-size: 0.85rem !important;
        }}

        .nav-select [data-baseweb="select"] span {{
            color: {ENKA_WHITE} !important;
        }}

        /* Highlight selected report dropdown with green background */
        .nav-select-active div[data-baseweb="select"] > div {{
            background-color: {ENKA_GREEN} !important;
            border: 2px solid {ENKA_GREEN} !important;
        }}

        .nav-select-active [data-baseweb="select"] span {{
            color: {ENKA_DARK} !important;
            font-weight: 700 !important;
        }}

        /* Home/Architecture button - professional gradient */
        .nav-home button {{
            background: linear-gradient(135deg, {ENKA_GREEN} 0%, {ENKA_ACCENT_GREEN} 100%) !important;
            color: {ENKA_WHITE} !important;
            border: none !important;
            font-weight: 700 !important;
            padding: 0.7rem 1.8rem !important;
            white-space: nowrap !important;
            min-width: fit-content !important;
            border-radius: 8px !important;
            box-shadow: 0 4px 12px rgba(129, 215, 66, 0.35) !important;
            transition: all 0.25s ease !important;
            text-transform: none !important;
        }}

        .nav-home button:hover {{
            background: linear-gradient(135deg, {ENKA_ACCENT_GREEN} 0%, #1a6b1a 100%) !important;
            color: {ENKA_WHITE} !important;
            box-shadow: 0 6px 20px rgba(129, 215, 66, 0.5) !important;
            transform: translateY(-2px) !important;
        }}

        .nav-home button p {{
            white-space: nowrap !important;
        }}

        /* Professional dividers */
        hr {{
            border: none !important;
            height: 2px !important;
            background: linear-gradient(90deg, {ENKA_GREEN}, #e0e0e0, {ENKA_GREEN}) !important;
            margin: 1.5rem 0 !important;
            border-radius: 1px !important;
        }}

        /* Dashboard info expander styling */
        .streamlit-expanderHeader {{
            background: {ENKA_WHITE} !important;
            border: 1px solid #e0e0e0 !important;
            border-radius: 8px !important;
            font-weight: 600 !important;
        }}

        /* Subheader styling */
        h2, h3 {{
            border-bottom: 2px solid {ENKA_GREEN} !important;
            padding-bottom: 0.5rem !important;
            margin-bottom: 1rem !important;
        }}

        /* Chart containers */
        [data-testid="stVerticalBlock"] > div:has(.js-plotly-plot) {{
            background: {ENKA_WHITE};
            border-radius: 10px;
            padding: 1rem;
            box-shadow: 0 2px 8px rgba(0,0,0,0.06);
            border: 1px solid #eaeaea;
            margin-bottom: 1rem;
        }}

        /* Dataframe styling */
        [data-testid="stDataFrame"] {{
            border-radius: 10px !important;
            overflow: hidden !important;
            box-shadow: 0 2px 8px rgba(0,0,0,0.06) !important;
            border: 1px solid #eaeaea !important;
        }}
    </style>
    """, unsafe_allow_html=True)

    # Dashboard structure - separate lists for each pack
    enka_dashboards = [
        ("ENKA Reports", None),
        ("Portfolio Cockpit", "03_Portfolio_Executive_Cockpit"),
        ("Partner Monetization", "04_Partner_Monetization_And_Revenue_Share"),
        ("RTM Settlement", "05_RTM_Settlement_Reconciliation"),
        ("Lifecycle Planning", "06_Lifecycle_And_Augmentation_Planning"),
        ("Dev Pipeline", "07_Development_Pipeline_Tracking"),
    ]

    tmeic_dashboards = [
        ("TMEIC Reports", None),
        ("PCS Real Time", "08_PCS_Controller_Real_Time_Operations"),
        ("Controller Health", "09_Controller_Health_And_Communications"),
        ("Faults & Trips", "10_Faults_And_Trips_Timeline"),
        ("Grid Performance", "11_Grid_Performance_And_Compliance"),
        ("Historian", "12_Historian_Explorer"),
    ]

    combined_dashboards = [
        ("Combined Reports", None),
        ("Revenue Loss", "13_Revenue_Loss_Attribution"),
        ("Dispatch vs Stress", "14_Dispatch_Versus_Asset_Stress"),
        ("SLA & Warranty", "15_SLA_And_Warranty_Evidence_Pack"),
        ("Benchmarking", "16_Portfolio_Benchmarking_By_Vendor_And_Site"),
    ]

    edge_dashboards = [
        ("Edge Intelligence", None),
        ("Signal Fidelity", "17_Signal_Fidelity_And_SCADA_Replacement"),
        ("Energy Forecasts", "18_Predictive_Energy_And_Power_Availability"),
        ("Balancing", "19_Balancing_And_Imbalance_Optimization"),
        ("Insights Report", "20_Insights_Report_And_Recommendations"),
    ]

    # Brand title above the navigation bar - professional header with borders
    st.markdown(f'''
        <div style="
            background: linear-gradient(180deg, {ENKA_WHITE} 0%, #f8f9fa 100%);
            margin: -6rem -2rem 0 -2rem;
            padding: 1.2rem 2rem 1rem 2rem;
            text-align: center;
            border-bottom: 1px solid #e0e0e0;
            box-shadow: 0 2px 4px rgba(0,0,0,0.03);
        ">
            <span style="
                color: {ENKA_DARK};
                font-size: 2.2rem;
                font-weight: 800;
                letter-spacing: -0.02em;
            ">
                <span style="color: {ENKA_GREEN};">⚡</span> BESS Analytics Platform
            </span>
        </div>
    ''', unsafe_allow_html=True)

    # Helper to find index of current page in a dashboard list
    def get_current_index(dashboards, page_name):
        if page_name:
            for i, (label, page) in enumerate(dashboards):
                if page == page_name:
                    return i
        return 0

    # Top navigation bar (below the title)
    st.markdown('<div class="nav-container">', unsafe_allow_html=True)

    nav_cols = st.columns([2, 2, 2, 2, 2])

    with nav_cols[0]:
        with st.container():
            st.markdown('<div class="nav-home">', unsafe_allow_html=True)
            if st.button("⚡ Architecture", key="nav_home_btn", use_container_width=True):
                st.switch_page("Home.py")
            st.markdown('</div>', unsafe_allow_html=True)

    # ENKA Pack dropdown
    with nav_cols[1]:
        with st.container():
            enka_options = [d[0] for d in enka_dashboards]
            enka_page_map = {d[0]: d[1] for d in enka_dashboards}
            enka_index = get_current_index(enka_dashboards, current_page)
            enka_class = "nav-select-active" if enka_index > 0 else "nav-select"

            st.markdown(f'<div class="{enka_class}">', unsafe_allow_html=True)
            enka_selected = st.selectbox(
                "ENKA Pack",
                enka_options,
                index=enka_index,
                key="nav_enka_select",
                label_visibility="collapsed"
            )

            if enka_selected and enka_page_map.get(enka_selected) and enka_page_map.get(enka_selected) != current_page:
                st.switch_page(f"pages/{enka_page_map[enka_selected]}.py")
            st.markdown('</div>', unsafe_allow_html=True)

    # TMEIC Pack dropdown
    with nav_cols[2]:
        with st.container():
            tmeic_options = [d[0] for d in tmeic_dashboards]
            tmeic_page_map = {d[0]: d[1] for d in tmeic_dashboards}
            tmeic_index = get_current_index(tmeic_dashboards, current_page)
            tmeic_class = "nav-select-active" if tmeic_index > 0 else "nav-select"

            st.markdown(f'<div class="{tmeic_class}">', unsafe_allow_html=True)
            tmeic_selected = st.selectbox(
                "TMEIC Pack",
                tmeic_options,
                index=tmeic_index,
                key="nav_tmeic_select",
                label_visibility="collapsed"
            )

            if tmeic_selected and tmeic_page_map.get(tmeic_selected) and tmeic_page_map.get(tmeic_selected) != current_page:
                st.switch_page(f"pages/{tmeic_page_map[tmeic_selected]}.py")
            st.markdown('</div>', unsafe_allow_html=True)

    # Combined Pack dropdown
    with nav_cols[3]:
        with st.container():
            combined_options = [d[0] for d in combined_dashboards]
            combined_page_map = {d[0]: d[1] for d in combined_dashboards}
            combined_index = get_current_index(combined_dashboards, current_page)
            combined_class = "nav-select-active" if combined_index > 0 else "nav-select"

            st.markdown(f'<div class="{combined_class}">', unsafe_allow_html=True)
            combined_selected = st.selectbox(
                "Combined Pack",
                combined_options,
                index=combined_index,
                key="nav_combined_select",
                label_visibility="collapsed"
            )

            if combined_selected and combined_page_map.get(combined_selected) and combined_page_map.get(combined_selected) != current_page:
                st.switch_page(f"pages/{combined_page_map[combined_selected]}.py")
            st.markdown('</div>', unsafe_allow_html=True)

    # Edge Intelligence dropdown
    with nav_cols[4]:
        with st.container():
            edge_options = [d[0] for d in edge_dashboards]
            edge_page_map = {d[0]: d[1] for d in edge_dashboards}
            edge_index = get_current_index(edge_dashboards, current_page)
            edge_class = "nav-select-active" if edge_index > 0 else "nav-select"

            st.markdown(f'<div class="{edge_class}">', unsafe_allow_html=True)
            edge_selected = st.selectbox(
                "Edge Intelligence",
                edge_options,
                index=edge_index,
                key="nav_edge_select",
                label_visibility="collapsed"
            )

            if edge_selected and edge_page_map.get(edge_selected) and edge_page_map.get(edge_selected) != current_page:
                st.switch_page(f"pages/{edge_page_map[edge_selected]}.py")
            st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('</div>', unsafe_allow_html=True)


def render_footer():
    """Render ENKA branded footer."""
    st.markdown("---")
    st.markdown(
        f"""<div class="footer">
        <span style="color: {ENKA_GREEN};">ENKA Energy Transition</span> |
        BESS Analytics Platform |
        <a href="https://enka-energy.com/" target="_blank" style="color: {ENKA_GREEN};">enka-energy.com</a>
        </div>""",
        unsafe_allow_html=True
    )


def get_plotly_colors():
    """
    Get ENKA-branded color palette for Plotly charts.

    Returns:
        dict with color sequences and individual colors
    """
    return {
        "primary": ENKA_GREEN,
        "secondary": ENKA_DARK,
        "accent": ENKA_ACCENT_GREEN,
        "sequence": [
            ENKA_GREEN,       # Primary green
            "#2ecc71",        # Emerald
            "#3498db",        # Blue
            "#9b59b6",        # Purple
            "#f39c12",        # Orange
            "#e74c3c",        # Red
            "#1abc9c",        # Teal
            "#34495e",        # Dark gray
        ],
        "positive": ENKA_GREEN,
        "negative": "#e74c3c",
        "neutral": ENKA_GRAY,
    }


def style_plotly_chart(fig):
    """
    Apply ENKA branding to a Plotly figure.

    Args:
        fig: Plotly figure object

    Returns:
        Updated figure with ENKA styling
    """
    fig.update_layout(
        font_family="sans-serif",
        font_color=ENKA_DARK,
        title_font_color=ENKA_DARK,
        legend_title_font_color=ENKA_DARK,
        paper_bgcolor="white",
        plot_bgcolor="white",
        colorway=get_plotly_colors()["sequence"],
    )

    # Update axes
    fig.update_xaxes(
        gridcolor=ENKA_LIGHT_GRAY,
        linecolor=ENKA_GRAY,
    )
    fig.update_yaxes(
        gridcolor=ENKA_LIGHT_GRAY,
        linecolor=ENKA_GRAY,
    )

    return fig
