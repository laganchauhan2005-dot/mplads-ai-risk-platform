import pandas as pd
import plotly.express as px
import streamlit as st

from services.api import APIError, list_mps, mp_profile, mp_projects, mp_summary
from styles import inject_css, risk_class

inject_css()
st.markdown('<div class="hero"><div class="hero-kicker">MP intelligence</div><h1>MP Search & Profile</h1><p>Search an MP and review portfolio exposure, project risk and financial position.</p></div>', unsafe_allow_html=True)

search = st.text_input("Search MP", placeholder="e.g. MP name, constituency or MP ID")
try:
    mps = list_mps(search=search or None, limit=100)
except APIError as e:
    st.error(str(e)); st.stop()

if not mps:
    st.info("No MPs matched your search.")
    st.stop()

options = {f"{m['mp_name']} | {m['constituency'] or 'Constituency not listed'} | {m['state'] or 'State not listed'}": m["mp_id"] for m in mps}
label = st.selectbox("Select MP", list(options))
mp_id = options[label]

try:
    profile = mp_profile(mp_id)
    summary = mp_summary(mp_id)
    projects = mp_projects(mp_id, limit=500)
except APIError as e:
    st.error(str(e)); st.stop()

a,b,c,d,e = st.columns(5)
a.metric("Projects", f"{profile['total_projects']:,}")
b.metric("High Risk", f"{profile['high_risk_projects']:,}")
c.metric("Average Risk", f"{profile['average_risk_score']:.1f}")
d.metric("Sanctioned", f"₹{profile['sanctioned_amount']/1e7:.2f} Cr")
e.metric("Expenditure", f"₹{profile['expenditure']/1e7:.2f} Cr")

st.markdown(f"### {profile['mp_name']}")
st.write(f"**MP ID:** {profile['mp_id']}  |  **Constituency:** {profile.get('constituency') or '—'}  |  **State:** {profile.get('state') or '—'}")
st.write(f"**MP Type:** {profile.get('mp_type') or '—'}  |  **Parliamentary term:** {profile.get('parliamentary_term') or '—'}")

tab1, tab2, tab3 = st.tabs(["Overview", "Projects", "Financials"])
with tab1:
    x,y,z = st.columns(3)
    x.metric("Medium Risk", summary["medium_risk_projects"])
    y.metric("Delayed / Stalled", summary["delayed_projects"])
    z.metric("Completed", summary["completed_projects"])
    util = summary["utilization_pct"]
    st.progress(min(max(util/100,0),1), text=f"Utilization: {util:.1f}%")

with tab2:
    if projects:
        pdf = pd.DataFrame(projects)
        risk_filter = st.multiselect("Risk level", ["CRITICAL","HIGH","MEDIUM","LOW"], default=["CRITICAL","HIGH","MEDIUM","LOW"])
        sector_options = sorted([x for x in pdf["sector"].dropna().unique()]) if "sector" in pdf else []
        sector = st.selectbox("Sector", ["All"] + sector_options)
        filtered = pdf[pdf["risk_level"].isin(risk_filter)]
        if sector != "All": filtered = filtered[filtered["sector"] == sector]
        cols = ["project_id","project_name","district","sector","work_status","sanctioned_amount","expenditure","reported_progress_pct","risk_score","risk_level"]
        cols = [c for c in cols if c in filtered.columns]
        st.dataframe(filtered[cols], use_container_width=True, hide_index=True)
    else:
        st.info("No projects returned.")

with tab3:
    fin = pd.DataFrame({
        "Metric":["Sanctioned","Funds released","Expenditure","Unspent balance"],
        "Amount":[summary["sanctioned_amount"],summary["funds_released"],summary["expenditure"],summary["unspent_balance"]]
    })
    fin["Amount (₹ Cr)"] = fin["Amount"]/1e7
    st.dataframe(fin[["Metric","Amount (₹ Cr)"]], use_container_width=True, hide_index=True)
    fig = px.bar(fin, x="Metric", y="Amount (₹ Cr)", text="Amount (₹ Cr)")
    fig.update_layout(height=330, margin=dict(l=10,r=10,t=20,b=10))
    st.plotly_chart(fig, use_container_width=True)
