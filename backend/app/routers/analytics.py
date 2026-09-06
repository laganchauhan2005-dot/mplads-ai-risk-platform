from fastapi import APIRouter, Depends
from sqlalchemy import func, case
from sqlalchemy.orm import Session
from ..database import get_db
from ..models import Project, MP, RiskAssessment
from ..schemas import OverviewOut, SectorAnalyticsOut
router=APIRouter(prefix="/analytics",tags=["Analytics"])

@router.get("/overview",response_model=OverviewOut)
def overview(db:Session=Depends(get_db)):
    total=db.query(Project).count(); mps=db.query(MP).count()
    high=db.query(RiskAssessment).filter(RiskAssessment.risk_level.in_(["HIGH","CRITICAL"])).count()
    medium=db.query(RiskAssessment).filter(RiskAssessment.risk_level=="MEDIUM").count()
    low=db.query(RiskAssessment).filter(RiskAssessment.risk_level=="LOW").count()
    sanctioned=float(db.query(func.coalesce(func.sum(Project.sanction_amount),0)).scalar() or 0)
    expenditure=float(db.query(func.coalesce(func.sum(Project.total_expenditure),0)).scalar() or 0)
    return {"projects":total,"mps":mps,"high_risk":high,"medium_risk":medium,"low_risk":low,"delayed_stalled": db.query(Project).filter(Project.is_delayed==1).count(),
            "sanctioned_amount":sanctioned,"expenditure":expenditure,"utilization_pct":round(expenditure/sanctioned*100,2) if sanctioned else 0}

@router.get("/sectors",response_model=list[SectorAnalyticsOut])
def sectors(db:Session=Depends(get_db)):
    rows=db.query(Project.work_category,func.count(Project.project_id),func.avg(RiskAssessment.overall_risk_score),
        func.sum(case((RiskAssessment.risk_level.in_(["HIGH","CRITICAL"]),1),else_=0)),
        func.coalesce(func.sum(Project.sanction_amount),0),func.coalesce(func.sum(Project.total_expenditure),0)
    ).outerjoin(RiskAssessment,RiskAssessment.project_id==Project.project_id).group_by(Project.work_category).order_by(func.count(Project.project_id).desc()).all()
    out=[]
    for s,count,avg,high,sanctioned,expenditure in rows:
        sanctioned=float(sanctioned or 0); expenditure=float(expenditure or 0)
        out.append({"sector":s,"projects":count,"avg_risk":round(float(avg or 0),2),"high_risk_projects":int(high or 0),
                    "sanctioned_amount":sanctioned,"expenditure":expenditure,"utilization_pct":round(expenditure/sanctioned*100,2) if sanctioned else 0})
    return out
