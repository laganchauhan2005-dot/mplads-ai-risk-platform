
import pandas as pd
import plotly.express as px
import streamlit as st

from services.api import APIError, overview, sectors, top_risk
from styles import inject_css

inject_css()

st.markdown(
    '<div class="hero">'
    '<div class="hero-kicker">SIH26102 · Command Center</div>'
    '<h1>MPLADS AI Risk Intelligence Platform</h1>'
    '<p>Prioritize projects for human investigation using financial, progress, delay and similarity risk signals.</p>'
    '</div>',
    unsafe_allow_html=True,
)

try:
    o = overview()
    sec = sectors()
    risk = top_risk(10)
except APIError as e:
    st.error(str(e))
    st.stop()

st.markdown('<div class="section-title">Portfolio snapshot</div>', unsafe_allow_html=True)
cols = st.columns(5)
for col, label, value in [
    (cols[0], "Projects", f"{o['projects']:,}"),
    (cols[1], "MPs", f"{o['mps']:,}"),
    (cols[2], "High risk", f"{o['high_risk']:,}"),
    (cols[3], "Delayed / stalled", f"{o['delayed_stalled']:,}"),
    (cols[4], "Utilization", f"{o['utilization_pct']:.1f}%"),
]:
    col.metric(label, value)

st.markdown('<div class="section-title">Financial position</div>', unsafe_allow_html=True)
f = st.columns(3)
f[0].metric("Sanctioned amount", f"₹{o['sanctioned_amount']/1e7:.2f} Cr")
f[1].metric("Expenditure", f"₹{o['expenditure']/1e7:.2f} Cr")
f[2].metric("Low-risk projects", f"{o['low_risk']:,}")

left, right = st.columns(2)
with left:
    st.markdown('<div class="section-title">Risk distribution</div>', unsafe_allow_html=True)
    rdf = pd.DataFrame({
        "Risk level": ["HIGH", "MEDIUM", "LOW"],
        "Projects": [o["high_risk"], o["medium_risk"], o["low_risk"]],
    })
    fig = px.bar(rdf, x="Risk level", y="Projects", text="Projects")
    fig.update_layout(
        height=350, margin=dict(l=10,r=10,t=15,b=10),
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
    )
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

with right:
    st.markdown('<div class="section-title">Projects by sector</div>', unsafe_allow_html=True)
    sdf = pd.DataFrame(sec)
    if not sdf.empty:
        sdf = sdf.head(8).sort_values("projects")
        fig = px.bar(sdf, x="projects", y="sector", orientation="h", text="projects")
        fig.update_layout(
            height=350, margin=dict(l=10,r=10,t=15,b=10),
            plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
            yaxis_title="",
        )
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

st.markdown('<div class="section-title">Investigation queue</div>', unsafe_allow_html=True)
st.markdown('<div class="section-caption">Highest-risk projects returned by the backend. Risk is an investigation-priority signal, not proof of fraud.</div>', unsafe_allow_html=True)
if risk:
    rdf = pd.DataFrame(risk)
    cols = [c for c in [
        "project_id","project_name","mp_name","state","sector",
        "risk_score","risk_level","risk_reasons"
    ] if c in rdf.columns]
    st.dataframe(rdf[cols], use_container_width=True, hide_index=True)
else:
    st.info("No high-risk projects were returned.")
