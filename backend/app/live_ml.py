from __future__ import annotations
import json, re
from datetime import datetime
import numpy as np, pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sqlalchemy.orm import Session
from .models import Project, RiskAssessment, RiskHistory, LivePrediction

class LiveMLPredictor:
    """Online inference adapter using the project's existing unsupervised ML approach."""
    def __init__(self, db: Session):
        self.db=db
        rows=db.query(Project).all()
        self.df=pd.DataFrame([{
            'project_id':p.project_id,'house':p.house,'state':p.state,'work_category':p.work_category,
            'work_raw':p.work_raw,'work_description':p.work_description,'sanction_amount':p.sanction_amount,
            'total_expenditure':p.total_expenditure,'payment_count':p.payment_count,'utilization_ratio':p.utilization_ratio,
            'progress_pct':p.progress_pct,'delay_days':p.delay_days,'is_delayed':p.is_delayed,
            'status':p.status,'sanction_date':p.sanction_date,'expected_completion_date':p.expected_completion_date,
            'last_expenditure_date':p.last_expenditure_date
        } for p in rows])
        if self.df.empty: raise ValueError('No projects available for ML reference data.')
        X=pd.DataFrame({
            'log_sanction_amount':np.log1p(pd.to_numeric(self.df.sanction_amount,errors='coerce').clip(lower=0)),
            'utilization_ratio':pd.to_numeric(self.df.utilization_ratio,errors='coerce').clip(-1,3),
            'log_total_expenditure':np.log1p(pd.to_numeric(self.df.total_expenditure,errors='coerce').clip(lower=0)),
            'payment_count':np.log1p(pd.to_numeric(self.df.payment_count,errors='coerce').fillna(0)),
        }).replace([np.inf,-np.inf],np.nan)
        X=X.fillna(X.median(numeric_only=True)).fillna(0)
        self.cost_model=IsolationForest(n_estimators=300,contamination=0.03,random_state=42,n_jobs=-1).fit(X)
        raw=-self.cost_model.score_samples(X); self.cost_ref=np.sort(raw)
        D=pd.DataFrame({
            'progress_gap':(100-pd.to_numeric(self.df.progress_pct,errors='coerce').fillna(0)).clip(0,100),
            'delay_days':pd.to_numeric(self.df.delay_days,errors='coerce').fillna(0).clip(0,2000),
            'utilization_ratio':pd.to_numeric(self.df.utilization_ratio,errors='coerce').fillna(0).clip(-1,3),
        }).replace([np.inf,-np.inf],np.nan).fillna(0)
        self.delay_model=IsolationForest(n_estimators=250,contamination=0.05,random_state=42,n_jobs=-1).fit(D)
        draw=-self.delay_model.score_samples(D); self.delay_ref=np.sort(draw)
        texts=(self.df.work_raw.fillna('')+' '+self.df.work_description.fillna('')).map(self.norm).tolist()
        self.vectorizer=TfidfVectorizer(max_features=60000,ngram_range=(1,2),min_df=2)
        self.matrix=self.vectorizer.fit_transform(texts)
    @staticmethod
    def norm(x): return re.sub(r'\s+',' ',re.sub(r'[^a-z0-9 ]',' ',str(x).lower())).strip()
    @staticmethod
    def pct_rank(arr,x):
        return float(np.searchsorted(arr,x,side='right')/max(1,len(arr))*100)
    def predict(self, payload):
        p=dict(payload)
        sanction=float(p.get('sanction_amount') or p.get('sanctioned_amount') or 0)
        exp=float(p.get('total_expenditure') or p.get('expenditure') or 0)
        pay=float(p.get('payment_count') or p.get('expenditure_txn_count') or 0)
        util=p.get('utilization_ratio')
        if util is None: util=(exp/sanction) if sanction else 0
        progress=float(p.get('progress_pct') if p.get('progress_pct') is not None else p.get('reported_progress_pct') or 0)
        delay=float(p.get('delay_days') or 0)
        X=pd.DataFrame([{'log_sanction_amount':np.log1p(max(0,sanction)),'utilization_ratio':np.clip(util,-1,3),'log_total_expenditure':np.log1p(max(0,exp)),'payment_count':np.log1p(max(0,pay))}])
        raw=float(-self.cost_model.score_samples(X)[0]); cost=self.pct_rank(self.cost_ref,raw)
        D=pd.DataFrame([{'progress_gap':np.clip(100-progress,0,100),'delay_days':np.clip(delay,0,2000),'utilization_ratio':np.clip(util,-1,3)}])
        draw=float(-self.delay_model.score_samples(D)[0]); delay_score=self.pct_rank(self.delay_ref,draw)
        text=self.norm((p.get('work_raw') or p.get('work') or '')+' '+(p.get('work_description') or p.get('project_name') or ''))
        sim=0.0; match=''
        if text:
            v=self.vectorizer.transform([text]); sims=cosine_similarity(v,self.matrix,dense_output=False).toarray().ravel(); idx=int(np.argmax(sims)); sim=float(sims[idx]*100); match=str(self.df.iloc[idx].project_id)
        reasons=[]
        if cost>=90: reasons.append(f'Cost anomaly signal is elevated ({cost:.1f}/100)')
        if delay_score>=90: reasons.append(f'Progress/delay signal is elevated ({delay_score:.1f}/100)')
        if progress<35 and (util or 0)>=0.60: reasons.append('Expenditure utilization is high relative to reported progress')
        if sim>=80: reasons.append(f'Potentially similar project found ({match}, similarity {sim:.1f}%)')
        if exp>sanction>0: reasons.append('Expenditure exceeds sanctioned amount')
        if not reasons: reasons.append('No major anomaly signal detected by the current prototype models')
        overall=float(np.clip(.40*cost+.35*delay_score+.25*sim,0,100))
        level='CRITICAL' if overall>=85 else 'HIGH' if overall>=70 else 'MEDIUM' if overall>=50 else 'LOW'
        return {'risk_score':round(overall,2),'risk_level':level,'cost_anomaly_score':round(cost,2),'delay_risk_score':round(delay_score,2),'duplicate_similarity_score':round(sim,2),'strongest_match':match,'risk_reasons':' | '.join(reasons),'progress_pct':round(progress,2),'delay_days':int(delay)}

def upsert_and_predict(db,payload):
    pid=str(payload.get('project_id') or '').strip()
    if not pid: raise ValueError('project_id is required for prediction and upsert.')
    existing=db.get(Project,pid); was_update=1 if existing else 0
    fields={'mp_id','house','state','mp_name','constituency','work_category','work_raw','work_description','recommended_date','sanction_date','sanction_amount','status','recommended_amount','completion_date','completed_amount','total_expenditure','first_expenditure_date','last_expenditure_date','payment_count','vendor_count','is_completed','utilization_ratio','recommendation_to_sanction_days','sanction_to_completion_days','sanction_to_last_expenditure_days','progress_pct','delay_days','is_delayed','expected_completion_date'}
    if existing is None: existing=Project(project_id=pid); db.add(existing)
    for k in fields:
        if k in payload and payload[k] is not None:
            try: setattr(existing,k,payload[k])
            except Exception: pass
    pred=LiveMLPredictor(db); result=pred.predict(payload)
    ra=db.get(RiskAssessment,pid)
    if ra is None: ra=RiskAssessment(project_id=pid); db.add(ra)
    ra.cost_anomaly_score=result['cost_anomaly_score']; ra.cost_risk_level='CRITICAL' if result['cost_anomaly_score']>=97 else 'HIGH' if result['cost_anomaly_score']>=90 else 'MEDIUM' if result['cost_anomaly_score']>=70 else 'LOW'
    ra.delay_anomaly_score=result['delay_risk_score']; ra.duplicate_max_similarity=result['duplicate_similarity_score']; ra.duplicate_risk_score=result['duplicate_similarity_score']; ra.overall_risk_score=result['risk_score']; ra.risk_level=result['risk_level']; ra.risk_reasons=result['risk_reasons']; ra.assessment_date=datetime.utcnow().isoformat()
    hist=RiskHistory(project_id=pid,assessment_date=datetime.utcnow().isoformat(),cost_score=result['cost_anomaly_score'],delay_score=result['delay_risk_score'],duplicate_score=result['duplicate_similarity_score'],overall_score=result['risk_score'],risk_level=result['risk_level'],risk_reasons=result['risk_reasons']); db.add(hist)
    lp=LivePrediction(project_id=pid,predicted_at=datetime.utcnow().isoformat(),risk_score=result['risk_score'],risk_level=result['risk_level'],cost_anomaly_score=result['cost_anomaly_score'],delay_risk_score=result['delay_risk_score'],duplicate_similarity_score=result['duplicate_similarity_score'],risk_reasons=result['risk_reasons'],input_payload=json.dumps(payload,default=str),was_update=was_update); db.add(lp)
    db.commit(); db.refresh(existing)
    result.update({'project_id':pid,'was_update':bool(was_update),'strongest_match':result.get('strongest_match','')})
    return result
