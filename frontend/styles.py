
import streamlit as st

def inject_css():
    st.markdown("""
    <style>
    /* ---------- App shell ---------- */
    .stApp {
        background: #0b0f14;
    }
    .block-container {
        max-width: 1480px;
        padding-top: 1.5rem;
        padding-bottom: 3rem;
    }

    /* ---------- Sidebar ---------- */
    [data-testid="stSidebar"] {
        background: #0a0e13;
        border-right: 1px solid #202832;
    }
    [data-testid="stSidebar"] .block-container {
        padding: 1.25rem 1rem;
    }
    .side-section {
        color: #687585;
        font-size: .68rem;
        font-weight: 800;
        letter-spacing: .12em;
        margin: 18px 4px 7px;
    }

    /* ---------- Hero ---------- */
    .hero {
        position: relative;
        overflow: hidden;
        padding: 30px 32px;
        border: 1px solid #27313d;
        border-radius: 16px;
        background:
            radial-gradient(circle at 88% 20%, rgba(91,141,239,.10), transparent 28%),
            linear-gradient(135deg,#111720,#0d1218);
        margin-bottom: 22px;
    }
    .hero-kicker {
        color: #6f9ff5;
        font-size: .72rem;
        font-weight: 800;
        letter-spacing: .14em;
        text-transform: uppercase;
        margin-bottom: 10px;
    }
    .hero h1 {
        margin: 0;
        font-size: 2.25rem;
        line-height: 1.1;
        letter-spacing: -.025em;
    }
    .hero p {
        margin: 10px 0 0;
        color: #9ba7b7;
        font-size: .98rem;
    }

    /* ---------- Section headers ---------- */
    .section-title {
        display: flex;
        align-items: center;
        gap: 10px;
        font-size: 1.12rem;
        font-weight: 750;
        margin: 26px 0 11px;
    }
    .section-title::before {
        content: "";
        width: 3px;
        height: 18px;
        background: #5b8def;
        border-radius: 4px;
    }
    .section-caption {
        color: #7e8998;
        font-size: .78rem;
        margin-top: -5px;
        margin-bottom: 12px;
    }

    /* ---------- Metric cards ---------- */
    [data-testid="stMetric"] {
        background: #121821;
        border: 1px solid #27313d;
        border-radius: 12px;
        padding: 15px 17px;
        min-height: 104px;
    }
    [data-testid="stMetricLabel"] {
        color: #8793a3 !important;
        font-size: .75rem !important;
    }
    [data-testid="stMetricValue"] {
        color: #f2f5f8 !important;
        font-weight: 750 !important;
        font-size: 1.55rem !important;
    }

    /* ---------- Controls ---------- */
    .stTextInput input, .stSelectbox div[data-baseweb="select"] > div,
    .stMultiSelect div[data-baseweb="select"] > div {
        background: #121821 !important;
        border-color: #2a3441 !important;
        border-radius: 9px !important;
    }
    .stSlider [data-baseweb="slider"] {
        margin-top: 6px;
    }

    /* ---------- Tables ---------- */
    div[data-testid="stDataFrame"] {
        border: 1px solid #27313d;
        border-radius: 11px;
        overflow: hidden;
    }

    /* ---------- Buttons / links ---------- */
    .stButton button {
        border-radius: 8px;
        border: 1px solid #2d3947;
        background: #151c25;
    }
    .stButton button:hover {
        border-color: #5b8def;
    }

    /* ---------- Info cards ---------- */
    .notice {
        padding: 12px 14px;
        border-radius: 10px;
        background: #111821;
        border: 1px solid #27313d;
        color: #9da8b7;
        font-size: .82rem;
    }
    .risk-high, .risk-critical {color:#ff7b7b; font-weight:750;}
    .risk-medium {color:#f2c75c; font-weight:750;}
    .risk-low {color:#69d39a; font-weight:750;}

    /* ---------- Hide Streamlit chrome ---------- */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    </style>
    """, unsafe_allow_html=True)

def risk_class(level: str | None) -> str:
    return {
        "CRITICAL": "risk-critical",
        "HIGH": "risk-high",
        "MEDIUM": "risk-medium",
        "LOW": "risk-low",
    }.get((level or "").upper(), "muted")
