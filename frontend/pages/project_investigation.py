import pandas as pd
import plotly.express as px
import streamlit as st

from services.api import APIError, projects, project, risk_history, duplicate_matches
from styles import inject_css, risk_class

inject_css()
st.markdown('<div class="hero"><div class="hero-kicker">Case review</div><h1>Project Investigation</h1><p>Inspect the evidence signals behind an individual MPLADS project.</p></div>', unsafe_allow_html=True)

query = st.text_input("Find project", placeholder="Project ID, project name, MP, or district")
try:
    candidates = projects(search=query or None, limit=100)
except APIError as e:
    st.error(str(e)); st.stop()

if not candidates:
    st.info("No matching projects. Enter a project ID or project name.")
    st.stop()

options = {f"{p['project_id']} | {p.get('project_name') or 'Unnamed project'}": p["project_id"] for p in candidates}
choice = st.selectbox("Select project", list(options))
project_id = options[choice]

try:
    p = project(project_id)
except APIError as e:
    st.error(str(e)); st.stop()

risk_level = (p.get("risk_level") or "UNKNOWN").upper()
st.markdown(f"### {p.get('project_name') or p['project_id']}")
st.write(f"**Project ID:** `{p['project_id']}`")
st.write(f"**MP:** {p.get('mp_name') or '—'} | **State:** {p.get('state') or '—'} | **District:** {p.get('district') or '—'}")

a,b,c,d = st.columns(4)
a.metric("Risk Score", f"{p.get('risk_score',0):.1f}" if p.get("risk_score") is not None else "—")
b.metric("Risk Level", risk_level)
c.metric("Progress", f"{p.get('reported_progress_pct',0):.1f}%" if p.get("reported_progress_pct") is not None else "—")
util = (p.get("expenditure") or 0)/(p.get("sanctioned_amount") or 1)*100 if p.get("sanctioned_amount") else 0
d.metric("Expenditure / Sanctioned", f"{util:.1f}%")

tab1,tab2,tab3,tab4 = st.tabs(["Project Details","Risk Signals","Risk History","Duplicate Matches"])

with tab1:
    d1,d2 = st.columns(2)
    with d1:
        st.markdown("**Location**")
        st.write(f"Sector: {p.get('sector') or '—'}")
        st.write(f"Sub-sector: {p.get('sub_sector') or '—'}")
        st.write(f"Block: {p.get('block') or '—'}")
        st.write(f"Village: {p.get('village') or '—'}")
        st.write(f"Work status: {p.get('work_status') or '—'}")
    with d2:
        st.markdown("**Financials**")
        for label,key in [("Recommended","recommended_amount"),("Sanctioned","sanctioned_amount"),("Funds released","funds_released"),("Expenditure","expenditure"),("Unspent balance","unspent_balance")]:
            st.write(f"{label}: ₹{(p.get(key) or 0):,}")
        st.markdown("**Timeline**")
        st.write(f"Start: {p.get('start_date') or '—'}")
        st.write(f"Expected completion: {p.get('expected_completion_date') or '—'}")

with tab2:
    signals = {
        "Cost anomaly": p.get("cost_anomaly_score"),
        "Progress anomaly": p.get("progress_anomaly_score"),
        "Delay risk": p.get("delay_risk_score"),
        "Duplicate similarity": p.get("duplicate_similarity_score"),
    }
    sdf = pd.DataFrame([{"Signal":k,"Score":v or 0} for k,v in signals.items()])
    fig = px.bar(sdf, x="Score", y="Signal", orientation="h", text="Score")
    fig.update_layout(height=320, margin=dict(l=10,r=10,t=20,b=10), xaxis_range=[0,100])
    st.plotly_chart(fig, use_container_width=True)
    st.markdown("**Risk reasons**")
    reasons = p.get("risk_reasons")
    if reasons:
        for r in str(reasons).replace("|",";").split(";"):
            if r.strip(): st.write(f"- {r.strip()}")
    else:
        st.info("No risk reason text is currently stored.")

with tab3:
    try:
        hist = risk_history(project_id)
        if hist:
            hdf = pd.DataFrame(hist).sort_values("detected_on")
            if "detected_on" in hdf and "risk_score" in hdf:
                fig = px.line(hdf, x="detected_on", y="risk_score", markers=True)
                fig.update_layout(height=330, margin=dict(l=10,r=10,t=20,b=10))
                st.plotly_chart(fig, use_container_width=True)
            cols = [c for c in ["detected_on","risk_score","risk_level","risk_reason","review_status"] if c in hdf.columns]
            st.dataframe(hdf[cols], use_container_width=True, hide_index=True)
        else:
            st.info("No risk-history records returned.")
    except APIError as e:
        st.warning(f"Risk history is unavailable for this project through the current backend contract: {e}")

with tab4:
    try:
        matches = duplicate_matches(project_id)
        if matches:
            mdf = pd.DataFrame(matches)
            cols = [c for c in ["duplicate_match_id","project_id","matched_project_id","text_similarity","location_match","sector_match","time_overlap","amount_similarity","duplicate_risk_score","match_status"] if c in mdf.columns]
            st.dataframe(mdf[cols], use_container_width=True, hide_index=True)
        else:
            st.info("No duplicate-match records returned.")
    except APIError as e:
        st.warning(f"Duplicate matches are unavailable through the current backend contract: {e}")
