import pandas as pd
import plotly.express as px
import streamlit as st

from services.api import APIError, project_options, project_stats, projects
from styles import inject_css

inject_css()
st.markdown('<div class="hero"><div class="hero-kicker">Risk analytics</div><h1>Risk Explorer</h1><p>Filter and investigate projects using the risk signals exposed by the backend.</p></div>', unsafe_allow_html=True)
st.caption("Filter projects by risk level, state, sector and work status.")

try:
    opts = project_options()
except APIError as e:
    st.error(str(e)); st.stop()

with st.sidebar:
    st.markdown("### Filters")
    min_risk = st.slider("Minimum risk score", 0, 100, 70)
    risk_levels = st.multiselect("Risk level", ["CRITICAL","HIGH","MEDIUM","LOW"], default=["CRITICAL","HIGH","MEDIUM","LOW"])
    state = st.selectbox("State", ["All"] + opts.get("states", []))
    sector = st.selectbox("Sector", ["All"] + opts.get("sectors", []))
    status = st.selectbox("Work status", ["All"] + opts.get("statuses", []))
    page_size = st.select_slider("Rows per page", options=[25,50,100,250,500], value=100)

state_value = None if state == "All" else state
sector_value = None if sector == "All" else sector
status_value = None if status == "All" else status

try:
    stats = project_stats(
        risk_levels=risk_levels if risk_levels else [],
        min_risk_score=min_risk,
        sector=sector_value,
        state=state_value,
        status=status_value,
    )
    total = stats["count"]
    page_count = max(1, (total + page_size - 1) // page_size)
    page = st.number_input("Page", min_value=1, max_value=page_count, value=1, step=1)
    offset = (page - 1) * page_size
    data = projects(
        risk_levels=risk_levels if risk_levels else [],
        min_risk_score=min_risk,
        sector=sector_value,
        state=state_value,
        status=status_value,
        limit=page_size,
        offset=offset,
    )
except APIError as e:
    st.error(str(e)); st.stop()

df = pd.DataFrame(data)

a,b,c,d = st.columns(4)
a.metric("Matching projects", f"{total:,}")
b.metric("High / Critical", f"{stats['high_critical']:,}")
c.metric("Average risk", f"{stats['average_risk']:.1f}")
d.metric("Partially completed", f"{stats['partially_completed']:,}")

if df.empty:
    st.info("No projects matched the current filters.")
    st.stop()

cols = [c for c in ["project_id","project_name","mp_name","state","sector","work_status","risk_score","risk_level","risk_reasons"] if c in df.columns]
st.dataframe(df[cols], use_container_width=True, hide_index=True)
st.caption(f"Showing {offset + 1:,}–{offset + len(df):,} of {total:,} matching projects")

fig = px.histogram(df, x="risk_score", nbins=20)
fig.update_layout(height=320, margin=dict(l=10,r=10,t=20,b=10))
st.plotly_chart(fig, use_container_width=True)
