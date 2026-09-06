# MPLADS SIH26102 Frontend

Streamlit frontend built specifically against the supplied FastAPI backend.

## Backend contract used

The frontend consumes:

- GET `/api/mps`
- GET `/api/mps/{mp_id}`
- GET `/api/mps/{mp_id}/projects`
- GET `/api/mps/{mp_id}/summary`
- GET `/api/projects`
- GET `/api/projects/top-risk`
- GET `/api/projects/{project_id}`
- GET `/api/projects/{project_id}/risk-history`
- GET `/api/projects/{project_id}/duplicate-matches`
- GET `/api/analytics/overview`
- GET `/api/analytics/sectors`

## Run on Windows

From the repository root:

```powershell
python -m venv venv
venv\Scripts\python.exe -m pip install -r frontend\requirements.txt
```

Terminal 1:

```powershell
venv\Scripts\python.exe -m uvicorn backend.app.main:app --reload --port 8000
```

Terminal 2:

```powershell
venv\Scripts\python.exe -m streamlit run frontend\Home.py
```

Open the Streamlit URL, normally `http://localhost:8501`.

## API URL

Default:

`http://127.0.0.1:8000/api`

To override:

```powershell
$env:MPLADS_API_BASE_URL="http://127.0.0.1:8000/api"
```

## Important backend limitation

The supplied backend exposes duplicate matches only for a selected project; therefore the Duplicate Candidates page is project-centric.

The backend's project detail, risk-history and duplicate-match routes use `{project_id}` as a path parameter. If a future MPLADS identifier contains `/`, URL routing may require a backend change to a query-parameter endpoint. The frontend has a search fallback for project details, but history/matches still depend on the current backend route.

## ML boundary

The frontend does not train or import ML models. It consumes the risk/anomaly fields returned by FastAPI. This preserves the backend's intended separation between the ML engine and dashboard.
