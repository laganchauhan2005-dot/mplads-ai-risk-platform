import pandas as pd
import streamlit as st

from services.api import APIError, live_predict, live_predict_batch, live_prediction_history
from styles import inject_css

inject_css()

st.markdown(
    '<div class="hero"><div class="hero-kicker">Live ML inference</div>'
    '<h1>Live Prediction</h1>'
    '<p>Enter a new project or upload a CSV. Uploaded columns are detected automatically and sent to the backend for live ML inference. Existing Project IDs are updated.</p></div>',
    unsafe_allow_html=True,
)
st.warning(
    "Risk scores are investigation-priority signals, not proof or probability of fraud. "
    "Current inference uses the project's unsupervised prototype models."
)

mode = st.radio("Input mode", ["Manual project", "CSV upload"], horizontal=True)

if mode == "Manual project":
    with st.form("manual"):
        c1, c2, c3 = st.columns(3)
        pid = c1.text_input("Project ID *")
        mp_id = c2.text_input("MP ID")
        mp_name = c3.text_input("MP name")
        state = c1.text_input("State")
        constituency = c2.text_input("Constituency")
        category = c3.text_input("Work category", value="Roads")
        title = st.text_input(
            "Project description / work",
            value="Construction and improvement of community road with drainage",
        )
        c1, c2, c3, c4 = st.columns(4)
        sanction = c1.number_input("Sanction amount", min_value=0.0, value=2500000.0, step=100000.0)
        expenditure = c2.number_input("Total expenditure", min_value=0.0, value=1200000.0, step=50000.0)
        progress = c3.slider("Progress %", 0.0, 100.0, 48.0)
        delay = c4.number_input("Delay days", min_value=0, max_value=3000, value=0)
        status = st.selectbox(
            "Status",
            [
                "Sanction",
                "Physical Inspection",
                "Vendor Identification",
                "Work partially Completed",
                "Delayed",
                "Stalled",
                "Work Completed",
            ],
        )
        submitted = st.form_submit_button("Run Live ML Prediction", type="primary")

    if submitted:
        if not pid.strip():
            st.error("Project ID is required.")
            st.stop()
        payload = {
            "project_id": pid.strip(),
            "mp_id": mp_id,
            "mp_name": mp_name,
            "state": state,
            "constituency": constituency,
            "work_category": category,
            "work_description": title,
            "work_raw": title,
            "sanction_amount": sanction,
            "recommended_amount": sanction,
            "total_expenditure": expenditure,
            "utilization_ratio": (expenditure / sanction if sanction else 0),
            "progress_pct": progress,
            "delay_days": delay,
            "is_delayed": int(delay > 0),
            "status": status,
        }
        try:
            result = live_predict(payload)
        except APIError as e:
            st.error(str(e))
            st.stop()
        st.success(
            "Existing project updated and re-predicted."
            if result.get("was_update")
            else "New project stored and predicted."
        )
        a, b = st.columns(2)
        a.metric("Risk score", f"{result['risk_score']:.1f}/100")
        b.metric("Risk level", result["risk_level"])
        a, b, c = st.columns(3)
        a.metric("Cost anomaly", result["cost_anomaly_score"])
        b.metric("Delay risk", result["delay_risk_score"])
        c.metric("Duplicate similarity", result["duplicate_similarity_score"])
        st.subheader("Why this score?")
        st.write(result["risk_reasons"])
        if result.get("strongest_match"):
            st.info(f"Closest existing project: {result['strongest_match']}")

else:
    file = st.file_uploader("Upload project CSV", type=["csv"])

    # Canonical field -> common header aliases. Matching is case-insensitive and
    # ignores spaces, punctuation, underscores and brackets.
    aliases = {
        "project_id": ["project_id", "Project ID", "projectid", "id", "work_id"],
        "mp_id": ["mp_id", "MP ID", "mpid", "member_id"],
        "mp_name": ["mp_name", "MP Name", "mpname", "member_name", "member of parliament"],
        "state": ["state", "State", "state_name"],
        "constituency": ["constituency", "Constituency", "parliamentary_constituency", "pc_name"],
        "work_category": ["work_category", "Work Category", "category", "sector", "work sector", "sub_sector"],
        "work_description": ["work_description", "Work Description", "project_name", "project title", "work", "description", "work title"],
        "sanction_amount": ["sanction_amount", "Sanction Amount", "sanctioned_amount", "sanctioned amount", "sanction_amount_inr"],
        "total_expenditure": ["total_expenditure", "Total Expenditure", "expenditure", "total expenditure", "expenditure_total", "amount_spent"],
        "progress_pct": ["progress_pct", "Progress %", "progress", "reported_progress_pct", "reported progress", "physical_progress", "physical progress pct"],
        "delay_days": ["delay_days", "Delay Days", "delay", "days_delayed", "delay days"],
        "status": ["status", "Status", "work_status", "work status", "project_status"],
    }

    def normalize_header(value):
        """Normalize a CSV header so common naming variations match automatically."""
        return "".join(ch for ch in str(value).strip().lower() if ch.isalnum())

    def auto_detect_columns(columns):
        normalized = {}
        for col in columns:
            normalized.setdefault(normalize_header(col), []).append(col)

        detected = {}
        for target, names in aliases.items():
            candidates = []
            for name in names:
                candidates.extend(normalized.get(normalize_header(name), []))
            # Preserve CSV order and remove duplicates.
            seen = set()
            candidates = [c for c in candidates if not (c in seen or seen.add(c))]
            detected[target] = candidates[0] if candidates else None
        return detected

    def clean_value(value):
        if pd.isna(value):
            return None
        if hasattr(value, "item"):
            value = value.item()
        return value

    if file:
        try:
            df = pd.read_csv(file)
        except Exception as e:
            st.error(f"Could not read CSV: {e}")
            st.stop()

        st.write(f"**{len(df):,} rows loaded**")
        st.dataframe(df.head(10), use_container_width=True, hide_index=True)

        detected = auto_detect_columns(df.columns)
        required = ["project_id", "sanction_amount", "total_expenditure"]
        missing_required = [field for field in required if not detected.get(field)]

        # No manual selectboxes: show exactly what the system detected.
        st.subheader("Automatic column detection")
        detection_rows = []
        for target, source in detected.items():
            detection_rows.append(
                {"Model field": target, "Detected CSV column": source or "Not found"}
            )
        st.dataframe(pd.DataFrame(detection_rows), use_container_width=True, hide_index=True)

        if missing_required:
            st.error(
                "Automatic detection could not find the required column(s): "
                + ", ".join(missing_required)
                + ". Rename those CSV headers to standard names such as "
                "project_id, sanction_amount and total_expenditure and upload again."
            )
        else:
            if st.button("Run ML on CSV", type="primary"):
                records = []
                for _, row in df.iterrows():
                    record = {}
                    for target, source in detected.items():
                        if source is not None:
                            value = clean_value(row[source])
                            if value is not None:
                                record[target] = value
                    records.append(record)

                try:
                    result = live_predict_batch(records)
                except APIError as e:
                    st.error(str(e))
                    st.stop()

                out = pd.DataFrame(result["results"])
                error_count = int(out["error"].notna().sum()) if "error" in out.columns else 0
                success_count = len(out) - error_count
                st.success(
                    f"Processed {len(out):,} rows: {success_count:,} successful, "
                    f"{error_count:,} with errors. Existing Project IDs were updated."
                )
                st.dataframe(out, use_container_width=True, hide_index=True)
                st.download_button(
                    "Download predictions CSV",
                    out.to_csv(index=False).encode("utf-8"),
                    file_name="live_predictions.csv",
                    mime="text/csv",
                )

st.divider()
st.subheader("Recent live predictions")
try:
    history = live_prediction_history(25)
    st.dataframe(pd.DataFrame(history), use_container_width=True, hide_index=True)
except APIError:
    pass
