import streamlit as st

TEAL = st.get_option("theme.primaryColor") or "#3DD6C6"
TEXT = st.get_option("theme.textColor") or "#E6EAF2"
AMBER = "#F5B14C"
RED = "#E8708A"
MUTED = "#9AA6BF"

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