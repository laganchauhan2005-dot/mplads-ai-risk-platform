from __future__ import annotations

import os
from typing import Any
from urllib.parse import quote

import requests
import streamlit as st

API_BASE_URL = os.getenv(
    "MPLADS_API_BASE_URL",
    "http://127.0.0.1:8000/api",
).rstrip("/")

class APIError(RuntimeError):
    pass

def _request(path: str, params: dict[str, Any] | None = None) -> Any:
    url = f"{API_BASE_URL}/{path.lstrip('/')}"
    try:
        response = requests.get(url, params=params, timeout=30)
    except requests.RequestException as exc:
        raise APIError(
            f"Could not connect to the FastAPI backend at {API_BASE_URL}. "
            "Start the backend and try again."
        ) from exc

    if not response.ok:
        detail = response.text[:500]
        try:
            payload = response.json()
            detail = payload.get("detail", detail)
        except Exception:
            pass
        raise APIError(f"Backend returned HTTP {response.status_code}: {detail}")

    try:
        return response.json()
    except ValueError as exc:
        raise APIError("Backend returned an invalid JSON response.") from exc

def health() -> dict:
    base = API_BASE_URL.rsplit("/api", 1)[0]
    try:
        r = requests.get(f"{base}/health", timeout=5)
        return r.json() if r.ok else {"status": "error"}
    except requests.RequestException:
        return {"status": "offline"}

@st.cache_data(ttl=30, show_spinner=False)
def overview() -> dict:
    return _request("/analytics/overview")

@st.cache_data(ttl=60, show_spinner=False)
def sectors() -> list[dict]:
    return _request("/analytics/sectors")

@st.cache_data(ttl=30, show_spinner=False)
def list_mps(search: str | None = None, state: str | None = None, limit: int = 100) -> list[dict]:
    params = {"limit": limit}
    if search:
        params["search"] = search
    if state:
        params["state"] = state
    return _request("/mps", params)

@st.cache_data(ttl=30, show_spinner=False)
def mp_profile(mp_id: str) -> dict:
    return _request(f"/mps/{quote(mp_id, safe='')}")

@st.cache_data(ttl=30, show_spinner=False)
def mp_projects(
    mp_id: str,
    risk_level: str | None = None,
    sector: str | None = None,
    status: str | None = None,
    limit: int = 500,
) -> list[dict]:
    params = {"limit": limit}
    if risk_level:
        params["risk_level"] = risk_level
    if sector:
        params["sector"] = sector
    if status:
        params["status"] = status
    return _request(f"/mps/{quote(mp_id, safe='')}/projects", params)

@st.cache_data(ttl=30, show_spinner=False)
def mp_summary(mp_id: str) -> dict:
    return _request(f"/mps/{quote(mp_id, safe='')}/summary")

@st.cache_data(ttl=30, show_spinner=False)
def projects(
    search: str | None = None,
    risk_level: str | None = None,
    risk_levels: list[str] | None = None,
    sector: str | None = None,
    state: str | None = None,
    status: str | None = None,
    limit: int = 500,
    offset: int = 0,
    min_risk_score: float | None = None,
) -> list[dict]:
    params = {"limit": limit, "offset": offset}
    if search:
        params["search"] = search
    if risk_levels:
        # requests encodes repeated query parameters as risk_levels=HIGH&risk_levels=MEDIUM...
        params["risk_levels"] = risk_levels
    elif risk_level:
        params["risk_level"] = risk_level
    if sector:
        params["sector"] = sector
    if state:
        params["state"] = state
    if status:
        params["status"] = status
    if min_risk_score is not None:
        params["min_risk_score"] = min_risk_score
    return _request("/projects", params)

@st.cache_data(ttl=30, show_spinner=False)
def project_stats(
    risk_levels: list[str] | None = None,
    min_risk_score: float | None = None,
    sector: str | None = None,
    state: str | None = None,
    status: str | None = None,
) -> dict:
    params: dict[str, Any] = {}
    if risk_levels:
        params["risk_levels"] = risk_levels
    if min_risk_score is not None:
        params["min_risk_score"] = min_risk_score
    if sector:
        params["sector"] = sector
    if state:
        params["state"] = state
    if status:
        params["status"] = status
    return _request("/projects/stats", params)

@st.cache_data(ttl=30, show_spinner=False)
def project_count(
    risk_levels: list[str] | None = None,
    min_risk_score: float | None = None,
    sector: str | None = None,
    state: str | None = None,
    status: str | None = None,
) -> int:
    params: dict[str, Any] = {}
    if risk_levels:
        params["risk_levels"] = risk_levels
    if min_risk_score is not None:
        params["min_risk_score"] = min_risk_score
    if sector:
        params["sector"] = sector
    if state:
        params["state"] = state
    if status:
        params["status"] = status
    return int(_request("/projects/count", params).get("count", 0))

@st.cache_data(ttl=300, show_spinner=False)
def project_options() -> dict:
    return _request("/projects/options")

@st.cache_data(ttl=30, show_spinner=False)
def top_risk(limit: int = 20) -> list[dict]:
    return _request("/projects/top-risk", {"limit": limit})

@st.cache_data(ttl=30, show_spinner=False)
def project(project_id: str) -> dict:
    # Fast path for IDs without slash characters.
    encoded = quote(project_id, safe="")
    try:
        return _request(f"/projects/{encoded}")
    except APIError:
        # The backend's detail route is a path parameter. If a future MPLADS
        # identifier contains '/', use the list/search endpoint as a safe fallback.
        matches = projects(search=project_id, limit=50)
        for item in matches:
            if item.get("project_id") == project_id:
                return item
        raise

@st.cache_data(ttl=30, show_spinner=False)
def risk_history(project_id: str) -> list[dict]:
    return _request(f"/projects/{quote(project_id, safe='')}/risk-history")

@st.cache_data(ttl=30, show_spinner=False)
def duplicate_matches(project_id: str) -> list[dict]:
    return _request(f"/projects/{quote(project_id, safe='')}/duplicate-matches")


def live_predict(payload: dict) -> dict:
    return _post_request('/predict', payload)

def live_predict_batch(records: list[dict]) -> dict:
    return _post_request('/predict/batch', {'records': records})

def live_prediction_history(limit: int=50) -> list[dict]:
    return _request('/predict/history', {'limit': limit})

def _post_request(path: str, payload: dict) -> Any:
    url=f"{API_BASE_URL}/{path.lstrip('/')}"
    try: response=requests.post(url,json=payload,timeout=180)
    except requests.RequestException as exc: raise APIError(f"Could not connect to FastAPI backend at {API_BASE_URL}.") from exc
    if not response.ok:
        try: detail=response.json().get('detail',response.text[:500])
        except Exception: detail=response.text[:500]
        raise APIError(f"Backend returned HTTP {response.status_code}: {detail}")
    return response.json()
