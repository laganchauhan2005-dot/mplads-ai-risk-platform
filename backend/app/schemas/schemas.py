from datetime import date
from typing import Optional
from pydantic import BaseModel, ConfigDict

class ORMBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)

class MPOut(ORMBase):
    mp_id: str; mp_name: str; state: Optional[str]=None; constituency: Optional[str]=None
    mp_type: Optional[str]=None; parliamentary_term: Optional[int]=None; annual_entitlement_demo: Optional[int]=None

class ProjectOut(BaseModel):
    project_id: str; mp_id: Optional[str]=None; mp_name: Optional[str]=None; state: Optional[str]=None; constituency: Optional[str]=None
    district: Optional[str]=None; block: Optional[str]=None; village: Optional[str]=None; sector: Optional[str]=None; sub_sector: Optional[str]=None
    project_name: Optional[str]=None; recommended_amount: Optional[float]=None; sanctioned_amount: Optional[float]=None
    funds_released: Optional[float]=None; expenditure: Optional[float]=None; unspent_balance: Optional[float]=None
    start_date: Optional[str]=None; expected_completion_date: Optional[str]=None; reported_progress_pct: Optional[float]=None; progress_pct: Optional[float]=None; delay_days: Optional[int]=None; is_delayed: Optional[int]=None; expected_completion_date: Optional[str]=None
    work_status: Optional[str]=None
    cost_anomaly_score: Optional[float]=None; progress_anomaly_score: Optional[float]=None; delay_risk_score: Optional[float]=None
    duplicate_similarity_score: Optional[float]=None; risk_score: Optional[float]=None; risk_level: Optional[str]=None
    risk_reasons: Optional[str]=None; risk_last_updated: Optional[str]=None

class RiskEventOut(BaseModel):
    risk_event_id: str; project_id: str; mp_id: Optional[str]=None; detected_on: Optional[str]=None
    risk_score: Optional[float]=None; risk_level: Optional[str]=None; risk_reason: Optional[str]=None; review_status: Optional[str]=None

class MPProfileOut(MPOut):
    total_projects: int
    high_risk_projects: int
    average_risk_score: float
    sanctioned_amount: float
    expenditure: float

class MPSummaryOut(BaseModel):
    mp_id: str; project_count: int; high_risk_projects: int; medium_risk_projects: int
    delayed_projects: int; completed_projects: int; sanctioned_amount: float; funds_released: Optional[float]=None
    expenditure: float; unspent_balance: float; utilization_pct: float

class OverviewOut(BaseModel):
    projects: int; mps: int; high_risk: int; medium_risk: int; low_risk: int; delayed_stalled: int
    sanctioned_amount: float; expenditure: float; utilization_pct: float

class SectorAnalyticsOut(BaseModel):
    sector: Optional[str]=None; projects: int; avg_risk: float; high_risk_projects: int
    sanctioned_amount: float; expenditure: float; utilization_pct: float

class DuplicateMatchOut(BaseModel):
    duplicate_match_id: str; project_id: str; matched_project_id: str
    text_similarity: Optional[float]=None; location_match: Optional[int]=None; sector_match: Optional[int]=None
    time_overlap: Optional[int]=None; amount_similarity: Optional[float]=None; duplicate_risk_score: Optional[float]=None
    match_status: Optional[str]=None
    alert_level: Optional[str]=None; reason: Optional[str]=None
