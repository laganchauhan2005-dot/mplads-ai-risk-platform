import pandas as pd
import plotly.express as px
import streamlit as st

from services.api import APIError, top_risk
from styles import inject_css

inject_css()
st.markdown('<div class="hero"><div class="hero-kicker">Prioritization</div><h1>Top Risk Projects</h1><p>Highest-priority projects for human review based on the current risk signals.</p></div>', unsafe_allow_html=True)
st.caption("Highest-risk projects returned by the backend. These are investigation priorities, not proof of fraud.")

limit = st.slider("Projects to show", min_value=5, max_value=100, value=20, step=5, key="top_risk_limit")
try:
    data = top_risk(limit)
except APIError as e:
    st.error(str(e)); st.stop()

if not data:
    st.info("No high-risk projects were returned.")
    st.stop()

df = pd.DataFrame(data)
a,b,c = st.columns(3)
a.metric("Returned", len(df))
b.metric("Highest score", f"{df['risk_score'].max():.1f}" if "risk_score" in df else "—")
c.metric("Average score", f"{df['risk_score'].mean():.1f}" if "risk_score" in df else "—")

cols = [c for c in ["project_id","project_name","mp_name","state","sector","work_status","risk_score","risk_level","risk_reasons"] if c in df.columns]
st.dataframe(df[cols], use_container_width=True, hide_index=True)

fig = px.bar(df.sort_values("risk_score"), x="risk_score", y="project_id", orientation="h", text="risk_score")
fig.update_layout(height=520, margin=dict(l=10,r=10,t=20,b=10))
st.plotly_chart(fig, use_container_width=True)
