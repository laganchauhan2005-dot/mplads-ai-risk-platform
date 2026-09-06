from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..database import get_db
from ..live_ml import upsert_and_predict
from ..models import LivePrediction
from datetime import datetime
import json
router=APIRouter(prefix='/predict',tags=['Live Prediction'])
@router.post('')
def predict(payload:dict,db:Session=Depends(get_db)):
    try: return upsert_and_predict(db,payload)
    except Exception as e: db.rollback(); raise HTTPException(400,str(e))
@router.post('/batch')
def batch(payload:dict,db:Session=Depends(get_db)):
    records=payload.get('records') if isinstance(payload,dict) else None
    if not isinstance(records,list) or not records: raise HTTPException(400,'records must be a non-empty list')
    out=[]
    for r in records:
        try: out.append(upsert_and_predict(db,r))
        except Exception as e: db.rollback(); out.append({'project_id':r.get('project_id'),'error':str(e)})
    return {'count':len(out),'results':out}
@router.get('/history')
def history(limit:int=50,db:Session=Depends(get_db)):
    rows=db.query(LivePrediction).order_by(LivePrediction.id.desc()).limit(min(limit,200)).all()
    return [{'id':x.id,'project_id':x.project_id,'predicted_at':x.predicted_at,'risk_score':x.risk_score,'risk_level':x.risk_level,'was_update':bool(x.was_update),'risk_reasons':x.risk_reasons} for x in rows]
