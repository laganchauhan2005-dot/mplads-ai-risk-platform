import pandas as pd
import streamlit as st

from services.api import APIError, projects, duplicate_matches
from styles import inject_css

inject_css()
st.markdown('<div class="hero"><div class="hero-kicker">Similarity review</div><h1>Duplicate Candidates</h1><p>Review potential project similarities before human verification.</p></div>', unsafe_allow_html=True)
st.caption("Review potential project similarities. The current backend exposes duplicate matches at project level.")

query = st.text_input("Find a project", placeholder="Project ID, project name, MP or district")
try:
    candidates = projects(search=query or None, limit=100)
except APIError as e:
    st.error(str(e)); st.stop()

if not candidates:
    st.info("No matching projects.")
    st.stop()

options = {f"{p['project_id']} | {p.get('project_name') or 'Unnamed project'}": p["project_id"] for p in candidates}
choice = st.selectbox("Select project to inspect matches", list(options))
pid = options[choice]

try:
    data = duplicate_matches(pid)
except APIError as e:
    st.error(str(e)); st.stop()

if not data:
    st.info("No duplicate-match records returned for this project.")
else:
    df = pd.DataFrame(data)
    a,b,c = st.columns(3)
    a.metric("Candidate matches", len(df))
    if "duplicate_risk_score" in df and df["duplicate_risk_score"].notna().any():
        b.metric("Highest duplicate score", f"{df['duplicate_risk_score'].max():.2f}")
    else:
        b.metric("Highest text similarity", f"{df['text_similarity'].max():.2f}" if "text_similarity" in df else "—")
    c.metric("Same-MP matches", int(df["location_match"].sum()) if "location_match" in df else "—")
    cols = [c for c in ["duplicate_match_id","project_id","matched_project_id","text_similarity","location_match","sector_match","time_overlap","amount_similarity","duplicate_risk_score","match_status"] if c in df.columns]
    st.dataframe(df[cols], use_container_width=True, hide_index=True)

st.markdown(
    '<div class="notice"><b>Review rule:</b> similarity is a screening signal. '
    'A candidate requires human verification before being treated as a duplicate or irregularity.</div>',
    unsafe_allow_html=True,
)
