from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import or_, func
from sqlalchemy.orm import Session
from ..database import get_db
from ..models import Project, RiskAssessment, RiskHistory, DuplicateAlert
from ..schemas import ProjectOut, RiskEventOut, DuplicateMatchOut

router = APIRouter(prefix="/projects", tags=["Projects"])


def project_dict(p: Project, r: RiskAssessment | None) -> dict:
    sanctioned = p.sanction_amount
    expenditure = p.total_expenditure
    unspent = max((sanctioned or 0) - (expenditure or 0), 0) if sanctioned is not None else None
    return {
        "project_id": p.project_id,
        "mp_id": p.mp_id,
        "mp_name": p.mp_name,
        "state": p.state,
        "constituency": p.constituency,
        "district": None,
        "block": None,
        "village": None,
        "sector": p.work_category,
        "sub_sector": None,
        "project_name": p.work_description or p.work_raw,
        "recommended_amount": p.recommended_amount,
        "sanctioned_amount": sanctioned,
        "funds_released": None,
        "expenditure": expenditure,
        "unspent_balance": unspent,
        "start_date": p.recommended_date,
        "expected_completion_date": None,
        "reported_progress_pct": p.progress_pct,
        "progress_pct": p.progress_pct,
        "delay_days": p.delay_days,
        "is_delayed": p.is_delayed,
        "expected_completion_date": p.expected_completion_date,
        "work_status": p.status,
        "cost_anomaly_score": r.cost_anomaly_score if r else None,
        "progress_anomaly_score": None,
        "delay_risk_score": r.delay_anomaly_score if r else None,
        "duplicate_similarity_score": r.duplicate_max_similarity if r else None,
        "risk_score": r.overall_risk_score if r else None,
        "risk_level": r.risk_level if r else None,
        "risk_reasons": r.risk_reasons if r else None,
        "risk_last_updated": r.assessment_date if r else None,
    }


def joined_query(db: Session):
    return db.query(Project, RiskAssessment).outerjoin(
        RiskAssessment, RiskAssessment.project_id == Project.project_id
    )


@router.get("", response_model=list[ProjectOut])
def list_projects(
    search: str | None = None,
    risk_level: str | None = None,
    risk_levels: list[str] | None = Query(None),
    sector: str | None = None,
    state: str | None = None,
    status: str | None = None,
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    min_risk_score: float | None = Query(None, ge=0, le=100),
    db: Session = Depends(get_db),
):
    q = joined_query(db)
    if search:
        t = f"%{search.strip()}%"
        q = q.filter(or_(
            Project.project_id.ilike(t), Project.work_description.ilike(t),
            Project.work_raw.ilike(t), Project.mp_name.ilike(t), Project.constituency.ilike(t)
        ))
    if risk_levels:
        normalized = [x.upper() for x in risk_levels if x]
        if normalized:
            q = q.filter(RiskAssessment.risk_level.in_(normalized))
    elif risk_level:
        q = q.filter(RiskAssessment.risk_level == risk_level.upper())
    if min_risk_score is not None:
        q = q.filter(RiskAssessment.overall_risk_score >= min_risk_score)
    if sector:
        q = q.filter(Project.work_category == sector)
    if state:
        q = q.filter(Project.state == state)
    if status:
        q = q.filter(Project.status == status)
    rows = q.order_by(RiskAssessment.overall_risk_score.desc(), Project.project_id).offset(offset).limit(limit).all()
    return [project_dict(p, r) for p, r in rows]



@router.get("/stats")
def project_stats(
    search: str | None = None,
    risk_level: str | None = None,
    risk_levels: list[str] | None = Query(None),
    min_risk_score: float | None = Query(None, ge=0, le=100),
    sector: str | None = None,
    state: str | None = None,
    status: str | None = None,
    db: Session = Depends(get_db),
):
    q = joined_query(db)
    if search:
        t = f"%{search.strip()}%"
        q = q.filter(or_(Project.project_id.ilike(t), Project.work_description.ilike(t), Project.work_raw.ilike(t), Project.mp_name.ilike(t), Project.constituency.ilike(t)))
    if risk_levels:
        normalized = [x.upper() for x in risk_levels if x]
        if normalized:
            q = q.filter(RiskAssessment.risk_level.in_(normalized))
    elif risk_level:
        q = q.filter(RiskAssessment.risk_level == risk_level.upper())
    if min_risk_score is not None:
        q = q.filter(RiskAssessment.overall_risk_score >= min_risk_score)
    if sector:
        q = q.filter(Project.work_category == sector)
    if state:
        q = q.filter(Project.state == state)
    if status:
        q = q.filter(Project.status == status)
    total, avg = q.with_entities(func.count(Project.project_id), func.avg(RiskAssessment.overall_risk_score)).one()
    high_critical = q.filter(RiskAssessment.risk_level.in_(["HIGH", "CRITICAL"])).with_entities(func.count(Project.project_id)).scalar() or 0
    partial = q.filter(Project.status.ilike("%partially%completed%")).with_entities(func.count(Project.project_id)).scalar() or 0
    return {"count": total or 0, "average_risk": round(float(avg or 0), 2), "high_critical": int(high_critical), "partially_completed": int(partial)}

@router.get("/count")
def count_projects(
    search: str | None = None,
    risk_level: str | None = None,
    risk_levels: list[str] | None = Query(None),
    min_risk_score: float | None = Query(None, ge=0, le=100),
    sector: str | None = None,
    state: str | None = None,
    status: str | None = None,
    db: Session = Depends(get_db),
):
    q = joined_query(db)
    if search:
        t = f"%{search.strip()}%"
        q = q.filter(or_(
            Project.project_id.ilike(t), Project.work_description.ilike(t),
            Project.work_raw.ilike(t), Project.mp_name.ilike(t), Project.constituency.ilike(t)
        ))
    if risk_levels:
        normalized = [x.upper() for x in risk_levels if x]
        if normalized:
            q = q.filter(RiskAssessment.risk_level.in_(normalized))
    elif risk_level:
        q = q.filter(RiskAssessment.risk_level == risk_level.upper())
    if min_risk_score is not None:
        q = q.filter(RiskAssessment.overall_risk_score >= min_risk_score)
    if sector:
        q = q.filter(Project.work_category == sector)
    if state:
        q = q.filter(Project.state == state)
    if status:
        q = q.filter(Project.status == status)
    return {"count": q.with_entities(func.count(Project.project_id)).scalar() or 0}

@router.get("/options")
def project_options(db: Session = Depends(get_db)):
    states = [x[0] for x in db.query(Project.state).filter(Project.state.isnot(None)).distinct().order_by(Project.state).all()]
    sectors = [x[0] for x in db.query(Project.work_category).filter(Project.work_category.isnot(None)).distinct().order_by(Project.work_category).all()]
    statuses = [x[0] for x in db.query(Project.status).filter(Project.status.isnot(None)).distinct().order_by(Project.status).all()]
    return {"states": states, "sectors": sectors, "statuses": statuses}

@router.get("/top-risk", response_model=list[ProjectOut])
def top_risk(limit: int = Query(10, ge=1, le=100), db: Session = Depends(get_db)):
    rows = joined_query(db).order_by(RiskAssessment.overall_risk_score.desc(), Project.project_id).limit(limit).all()
    return [project_dict(p, r) for p, r in rows]


@router.get("/{project_id:path}/risk-history", response_model=list[RiskEventOut])
def project_risk_history(project_id: str, db: Session = Depends(get_db)):
    if not db.get(Project, project_id):
        raise HTTPException(404, "Project not found")
    rows = db.query(RiskHistory).filter(RiskHistory.project_id == project_id).order_by(RiskHistory.assessment_date.desc(), RiskHistory.id.desc()).all()
    return [{
        "risk_event_id": str(x.id), "project_id": x.project_id, "mp_id": None,
        "detected_on": x.assessment_date, "risk_score": x.overall_score,
        "risk_level": x.risk_level, "risk_reason": x.risk_reasons,
        "review_status": None,
    } for x in rows]


@router.get("/{project_id:path}/duplicate-matches", response_model=list[DuplicateMatchOut])
def duplicate_matches(project_id: str, db: Session = Depends(get_db)):
    if not db.get(Project, project_id):
        raise HTTPException(404, "Project not found")
    rows = db.query(DuplicateAlert).filter(
        (DuplicateAlert.project_id == project_id) | (DuplicateAlert.matched_project_id == project_id)
    ).order_by(DuplicateAlert.alert_score.desc(), DuplicateAlert.similarity.desc()).all()
    return [{
        "duplicate_match_id": str(x.id),
        "project_id": x.project_id,
        "matched_project_id": x.matched_project_id,
        "text_similarity": x.similarity,
        "location_match": x.same_constituency,
        "sector_match": None,
        "time_overlap": None,
        "amount_similarity": 1.0 if x.similar_amount else 0.0 if x.similar_amount is not None else None,
        "duplicate_risk_score": x.alert_score,
        "match_status": x.alert_level,
        "alert_level": x.alert_level,
        "reason": x.reason,
    } for x in rows]

@router.get("/{project_id:path}", response_model=ProjectOut)
def get_project(project_id: str, db: Session = Depends(get_db)):
    row = joined_query(db).filter(Project.project_id == project_id).first()
    if not row:
        raise HTTPException(404, "Project not found")
    return project_dict(*row)
