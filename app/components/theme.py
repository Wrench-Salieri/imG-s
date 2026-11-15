import streamlit as st

TEAL = st.get_option("theme.primaryColor") or "#3DD6C6"
TEXT = st.get_option("theme.textColor") or "#E6EAF2"
AMBER = "#F5B14C"
RED = "#E8708A"
MUTED = "#9AA6BF"
DESIGN_IMAGE_HEIGHT = 300
MISSION_IMAGE_HEIGHT = 230
SWEEP_CHART_HEIGHT = 300

def style_figure(fig, height=360):
    """The dark, transparent look shared by every chart."""
    fig.update_layout(
        height=height,
        margin=dict(l=10, r=10, t=30, b=10),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font_color=TEXT,
        legend=dict(orientation="h", y=-0.2),
    )
    return fig

def apply_compact_css():
    st.markdown(
        """
        <style>
        [data-testid="stMainBlockContainer"], .block-container {padding-top: 3rem; padding-bottom: 0.5rem;}
        [data-testid="stSidebarUserContent"] {padding-top: 1rem;}
        [data-testid="stVerticalBlock"] {gap: 0.6rem;}
        [data-testid="stMetricValue"] {font-size: 1.5rem;}
        [data-testid="stMetricLabel"] p {font-size: 0.8rem;}
        [data-testid="stMetricDelta"] {font-size: 0.7rem;}
        [data-testid="stAlert"] {padding: 0.35rem 0.75rem;}
        [data-testid="stTabs"] button {padding-top: 0.25rem; padding-bottom: 0.25rem;}
        [data-testid="stSidebarHeader"] {height: 2rem; padding-top: 0.25rem; padding-bottom: 0;}
        [data-testid="stSidebarUserContent"] {padding-top: 0 !important; margin-top: -1rem;}
        [data-testid="stHeaderActionElements"] {display: none;}
        </style>
        """,
        unsafe_allow_html=True,
    )