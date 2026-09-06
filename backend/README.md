# MPLADS AI Risk Intelligence Backend

The backend is a FastAPI API layer over the **ML team's final MPLADS SQLite database**. The database contains project records, MP records, risk assessments, risk history snapshots, and duplicate alerts.

## Final database

Place the approved SQLite file at:

```text
backend/mplads_dev.db
```

The default SQLite path is resolved relative to the `backend` folder, so starting FastAPI from the project root will still open the correct database.

The final database currently contains approximately:

- MPs: 714
- Projects: 98,646
- Risk assessments: 98,646
- Risk history records: 98,646
- Duplicate alerts: 94,892
- HIGH + CRITICAL projects: 8,220

The database file is intentionally ignored by Git (`*.db`). Do **not** commit the 100+ MB database to the Git repository. Share it separately with teammates or use a controlled data distribution process.

## Setup

From the project root on Windows:

```powershell
venv\Scripts\python.exe backend\check_data.py
venv\Scripts\python.exe -m uvicorn backend.app.main:app --reload --port 8000
```

Then start Streamlit from the project root in another terminal:

```powershell
venv\Scripts\python.exe -m streamlit run frontend\Home.py
```

## API

- `GET /api/mps?search=&state=` — MP listing/search
- `GET /api/mps/{mp_id}` — MP profile
- `GET /api/mps/{mp_id}/projects` — MP projects
- `GET /api/mps/{mp_id}/summary` — MP summary
- `GET /api/projects` — project list/search/filter
- `GET /api/projects/{project_id}` — project details
- `GET /api/projects/top-risk` — true Top-N by overall risk score
- `GET /api/projects/{project_id}/risk-history` — risk history/snapshots
- `GET /api/projects/{project_id}/duplicate-matches` — potential duplicate candidates
- `GET /api/analytics/overview` — overview analytics
- `GET /api/analytics/sectors` — category analytics

Project IDs may contain `/`; the detail/history/duplicate endpoints therefore use a path converter.

## ML boundary

The FastAPI layer does not train or infer models. It consumes the ML team's final fields from `risk_assessments` and exposes them through the stable frontend API contract.

Risk levels and explanations are supplied by the ML database. The application should describe these as **risk indicators / potential anomalies / investigation priority**, not as proof of fraud.

## Important field mapping

The final ML database uses these source fields:

- `work_category` -> API `sector`
- `work_description` / `work_raw` -> API `project_name`
- `sanction_amount` -> API `sanctioned_amount`
- `total_expenditure` -> API `expenditure`
- `status` -> API `work_status`
- `delay_anomaly_score` -> API `delay_risk_score`
- `duplicate_max_similarity` -> API `duplicate_similarity_score`
- `overall_risk_score` -> API `risk_score`
- `assessment_date` -> API `risk_last_updated`

The final database does not contain district/block/village, funds-released, or expected-completion fields, so those API fields are returned as unavailable rather than fabricated.

## Legacy CSV importer

`backend/import_data.py` is retained only as a guard against accidentally running the old development seed workflow. **Do not run it against the final database.**


### Live prediction
POST /api/predict and POST /api/predict/batch run the current live ML adapter. If project_id exists, the project is updated before the prediction is stored.
