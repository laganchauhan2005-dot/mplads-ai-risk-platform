from pathlib import Path
import pandas as pd, numpy as np
from sklearn.ensemble import IsolationForest

INPUT=Path('data/processed/canonical_projects.csv')
OUT=Path('data/result/cost_anomaly_results_v2.csv')
df=pd.read_csv(INPUT,low_memory=False,parse_dates=['recommended_date','sanction_date','completion_date','first_expenditure_date','last_expenditure_date'])

# Peer groups: same House + State + Work Category. For tiny groups, fall back to House + Work Category.
primary=['house','state','work_category']
fallback=['house','work_category']
pg=df.groupby(primary)['sanction_amount'].agg(peer_n='count',peer_median='median',peer_q1=lambda x:x.quantile(.25),peer_q3=lambda x:x.quantile(.75)).reset_index()
df=df.merge(pg,on=primary,how='left')
fg=df.groupby(fallback)['sanction_amount'].agg(fb_median='median',fb_q1=lambda x:x.quantile(.25),fb_q3=lambda x:x.quantile(.75),fb_n='count').reset_index()
df=df.merge(fg,on=fallback,how='left')
small=df.peer_n<20
df.loc[small,'peer_median']=df.loc[small,'fb_median']; df.loc[small,'peer_q1']=df.loc[small,'fb_q1']; df.loc[small,'peer_q3']=df.loc[small,'fb_q3']; df.loc[small,'peer_n']=df.loc[small,'fb_n']
df['iqr']=(df.peer_q3-df.peer_q1)
df['cost_vs_peer_median']=df.sanction_amount/df.peer_median
df['robust_cost_z']=(df.sanction_amount-df.peer_median)/(df.iqr/1.349).replace(0,np.nan)

df['overspend_flag']=((df.total_expenditure>df.sanction_amount)&df.total_expenditure.notna()&df.sanction_amount.notna()).astype(int)

# Unsupervised financial detector. No labels are assumed.
X=pd.DataFrame({
 'log_sanction_amount':np.log1p(df.sanction_amount.clip(lower=0)),
 'utilization_ratio':df.utilization_ratio.clip(-1,3),
 'log_total_expenditure':np.log1p(df.total_expenditure.clip(lower=0)),
 'payment_count':np.log1p(df.payment_count.fillna(0)),
})
X=X.replace([np.inf,-np.inf],np.nan)
X=X.fillna(X.median(numeric_only=True))
model=IsolationForest(n_estimators=300,contamination=0.03,random_state=42,n_jobs=-1)
model.fit(X)
raw=-model.score_samples(X)
df['cost_if_raw_score']=raw
df['cost_anomaly_score']=df.cost_if_raw_score.rank(pct=True).mul(100).round(2)

def reason(r):
    rr=[]
    if pd.notna(r.cost_vs_peer_median) and r.cost_vs_peer_median>=2: rr.append(f"Sanction amount is {r.cost_vs_peer_median:.1f}x the comparable-project median")
    if pd.notna(r.robust_cost_z) and r.robust_cost_z>=3: rr.append('Sanction amount is a strong upper-tail outlier within its peer group')
    if r.overspend_flag: rr.append('Aggregated expenditure exceeds sanctioned amount')
    if r.cost_anomaly_score>=97: rr.append('Financial pattern is in the highest 3% of unsupervised anomaly scores')
    return ' | '.join(rr)
df['cost_reasons']=df.apply(reason,axis=1)
df['cost_risk_level']=pd.cut(df.cost_anomaly_score,bins=[-1,70,90,97,100],labels=['LOW','MEDIUM','HIGH','CRITICAL']).astype(str)
cols=['project_id','house','mp_name','state','constituency','work_category','work_description','status','sanction_amount','recommended_amount','total_expenditure','utilization_ratio','payment_count','vendor_count','peer_n','peer_median','peer_q1','peer_q3','cost_vs_peer_median','robust_cost_z','cost_anomaly_score','cost_risk_level','overspend_flag','cost_reasons']
df[cols].to_csv(OUT,index=False)
print('rows',len(df)); print('high+', (df.cost_anomaly_score>=90).sum()); print('critical', (df.cost_anomaly_score>=97).sum()); print('overspend',df.overspend_flag.sum())
print(df.nlargest(15,'cost_anomaly_score')[['project_id','house','state','work_category','sanction_amount','total_expenditure','utilization_ratio','cost_vs_peer_median','cost_anomaly_score','cost_reasons']].to_string(index=False))
