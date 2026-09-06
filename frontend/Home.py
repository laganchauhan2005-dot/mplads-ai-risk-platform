
import streamlit as st
from styles import inject_css

st.set_page_config(
    page_title="MPLADS AI Risk Intelligence",
    page_icon=None,
    layout="wide",
    initial_sidebar_state="expanded",
)
inject_css()

pg = st.navigation({
    "HOME": [st.Page("pages/home.py", title="Home")],
    "INTELLIGENCE": [
        st.Page("pages/mp_search.py", title="MP Search"),
        st.Page("pages/project_investigation.py", title="Project Investigation"),
        st.Page("pages/top_risk.py", title="Top Risk Projects"),
        st.Page("pages/category_analysis.py", title="Category Analysis"),
        st.Page("pages/duplicate_candidates.py", title="Duplicate Candidates"),
        st.Page("pages/risk_explorer.py", title="Risk Explorer"),
        st.Page("pages/live_prediction.py", title="Live Prediction"),
    ],
})

pg.run()
