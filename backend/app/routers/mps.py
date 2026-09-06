from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import or_, func, case
from sqlalchemy.orm import Session
from ..database import get_db
from ..models import MP, Project, RiskAssessment
from ..schemas import MPOut, ProjectOut, MPProfileOut, MPSummaryOut
from .projects import project_dict

router = APIRouter(prefix="/mps", tags=["MPs"])


def mp_out(mp: MP) -> dict:
    return {"mp_id": mp.mp_id, "mp_name": mp.mp_name, "state": mp.state, "constituency": mp.constituency,
            "mp_type": mp.house, "parliamentary_term": None, "annual_entitlement_demo": mp.allocated_amount}

@router.get("", response_model=list[MPOut])
def list_mps(search: str | None = Query(None), state: str | None = None, limit: int = Query(100, ge=1, le=500), db: Session = Depends(get_db)):
    q = db.query(MP)
    if search:
        term = f"%{search.strip()}%"
        q = q.filter(or_(MP.mp_id.ilike(term), MP.mp_name.ilike(term), MP.state.ilike(term), MP.constituency.ilike(term)))
    if state:
        q = q.filter(MP.state.ilike(state.strip()))
    return [mp_out(x) for x in q.order_by(MP.mp_name).limit(limit).all()]

@router.get("/{mp_id}", response_model=MPProfileOut)
def get_mp(mp_id: str, db: Session = Depends(get_db)):
    mp = db.get(MP, mp_id)
    if not mp: raise HTTPException(404, "MP not found")
    stats = db.query(
        func.count(Project.project_id),
        func.sum(case((RiskAssessment.risk_level.in_(["HIGH", "CRITICAL"]), 1), else_=0)),
        func.avg(RiskAssessment.overall_risk_score),
        func.coalesce(func.sum(Project.sanction_amount), 0),
        func.coalesce(func.sum(Project.total_expenditure), 0)
    ).outerjoin(RiskAssessment, RiskAssessment.project_id == Project.project_id).filter(Project.mp_id == mp_id).one()
    return {**mp_out(mp), "total_projects": stats[0] or 0, "high_risk_projects": int(stats[1] or 0),
            "average_risk_score": round(float(stats[2] or 0), 2), "sanctioned_amount": float(stats[3] or 0), "expenditure": float(stats[4] or 0)}

@router.get("/{mp_id}/projects", response_model=list[ProjectOut])
def get_mp_projects(mp_id: str, risk_level: str | None=None, sector: str | None=None, status: str | None=None, limit: int=Query(100,ge=1,le=500), db: Session=Depends(get_db)):
    if not db.get(MP, mp_id): raise HTTPException(404, "MP not found")
    q = db.query(Project, RiskAssessment).outerjoin(RiskAssessment, RiskAssessment.project_id == Project.project_id).filter(Project.mp_id == mp_id)
    if risk_level: q=q.filter(RiskAssessment.risk_level==risk_level.upper())
    if sector: q=q.filter(Project.work_category==sector)
    if status: q=q.filter(Project.status==status)
    return [project_dict(p, r) for p, r in q.order_by(RiskAssessment.overall_risk_score.desc()).limit(limit).all()]

@router.get("/{mp_id}/summary", response_model=MPSummaryOut)
def mp_summary(mp_id: str, db: Session = Depends(get_db)):
    if not db.get(MP, mp_id): raise HTTPException(404, "MP not found")
    rows = db.query(Project, RiskAssessment).outerjoin(RiskAssessment, RiskAssessment.project_id == Project.project_id).filter(Project.mp_id == mp_id).all()
    sanctioned=sum(p.sanction_amount or 0 for p,_ in rows); expenditure=sum(p.total_expenditure or 0 for p,_ in rows)
    return {"mp_id":mp_id,"project_count":len(rows),
            "high_risk_projects":sum((r.risk_level in ["HIGH","CRITICAL"]) if r else False for _,r in rows),
            "medium_risk_projects":sum((r.risk_level=="MEDIUM") if r else False for _,r in rows),
            "delayed_projects":0,
            "completed_projects":sum(p.is_completed==1 for p,_ in rows),
            "sanctioned_amount":sanctioned,"funds_released":None,
            "expenditure":expenditure,"unspent_balance":max(0,sanctioned-expenditure),
            "utilization_pct":round(expenditure/sanctioned*100,2) if sanctioned else 0}
