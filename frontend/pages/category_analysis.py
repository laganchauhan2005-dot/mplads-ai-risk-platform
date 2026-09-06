import pandas as pd
import plotly.express as px
import streamlit as st

from services.api import APIError, sectors
from styles import inject_css

inject_css()
st.markdown('<div class="hero"><div class="hero-kicker">Portfolio intelligence</div><h1>Category Analysis</h1><p>Compare project volume, financial utilization and risk concentration across sectors.</p></div>', unsafe_allow_html=True)
st.caption("Sector-level workload, financial utilization and risk concentration.")

try:
    data = sectors()
except APIError as e:
    st.error(str(e)); st.stop()

df = pd.DataFrame(data)
if df.empty:
    st.info("No sector analytics returned.")
    st.stop()

df["sanctioned_cr"] = df["sanctioned_amount"]/1e7
df["expenditure_cr"] = df["expenditure"]/1e7

sector = st.selectbox("Focus sector", ["All"] + sorted(df["sector"].fillna("Unknown").astype(str).unique().tolist()))
view = df if sector == "All" else df[df["sector"].fillna("Unknown") == sector]

a,b,c,d = st.columns(4)
a.metric("Sectors", len(df))
b.metric("Projects", int(view["projects"].sum()))
c.metric("High Risk", int(view["high_risk_projects"].sum()))
d.metric("Avg Risk", f"{view['avg_risk'].mean():.1f}")

left,right = st.columns(2)
with left:
    fig = px.bar(view.sort_values("projects"), x="projects", y="sector", orientation="h", text="projects")
    fig.update_layout(height=450, margin=dict(l=10,r=10,t=20,b=10))
    st.plotly_chart(fig, use_container_width=True)
with right:
    fig = px.scatter(view, x="utilization_pct", y="avg_risk", size="projects", hover_name="sector", text="sector")
    fig.update_layout(height=450, margin=dict(l=10,r=10,t=20,b=10))
    st.plotly_chart(fig, use_container_width=True)

cols = ["sector","projects","avg_risk","high_risk_projects","sanctioned_cr","expenditure_cr","utilization_pct"]
st.dataframe(view[cols], use_container_width=True, hide_index=True)
