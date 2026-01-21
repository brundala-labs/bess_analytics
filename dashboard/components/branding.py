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
        h1, h2, h3 {{
            color: {ENKA_DARK};
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


def render_sidebar_branding():
    """Render ENKA branding in sidebar (minimal version without logo)."""
    # Simple tagline only - no logo
    pass  # Logo removed per user request


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
