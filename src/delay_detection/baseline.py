from pathlib import Path
import pandas as pd, numpy as np
from sklearn.ensemble import IsolationForest
BASE=Path('data/processed')
df=pd.read_csv(BASE/'canonical_projects.csv',low_memory=False,parse_dates=['recommended_date','sanction_date','completion_date','first_expenditure_date','last_expenditure_date'])
ASOF=pd.Timestamp('2026-09-04')
# Historical completed duration peer baseline
p=['house','state','work_category']
completed=df[df.completion_date.notna() & df.sanction_date.notna()].copy()
completed['duration_days']=(completed.completion_date-completed.sanction_date).dt.days
completed=completed[completed.duration_days>=0]
stats=completed.groupby(p)['duration_days'].agg(peer_duration_median='median',peer_duration_q1=lambda x:x.quantile(.25),peer_duration_q3=lambda x:x.quantile(.75),peer_duration_n='count').reset_index()
df=df.merge(stats,on=p,how='left')
# fallback house+category
fb=['house','work_category']
f=completed.groupby(fb)['duration_days'].agg(fb_duration_median='median',fb_duration_q1=lambda x:x.quantile(.25),fb_duration_q3=lambda x:x.quantile(.75),fb_duration_n='count').reset_index()
df=df.merge(f,on=fb,how='left')
small=(df.peer_duration_n<20)|df.peer_duration_n.isna()
for a,b in [('peer_duration_median','fb_duration_median'),('peer_duration_q1','fb_duration_q1'),('peer_duration_q3','fb_duration_q3'),('peer_duration_n','fb_duration_n')]: df.loc[small,a]=df.loc[small,b]
df['project_age_days']=np.where(df.sanction_date.notna(),(df.completion_date.fillna(ASOF)-df.sanction_date).dt.days,np.nan)
df['duration_vs_peer_median']=df['project_age_days']/df['peer_duration_median']
iqr=df.peer_duration_q3-df.peer_duration_q1
df['delay_robust_z']=(df.project_age_days-df.peer_duration_median)/(iqr/1.349).replace(0,np.nan)
# Completed: compare actual duration. Ongoing: compare current age, but only flag with minimum age 180 days.
completed_flag=df.is_completed.eq(1)
completed_rule=completed_flag & df.delay_robust_z.ge(3) & df.peer_duration_n.ge(20)
ongoing_rule=(~completed_flag) & df.project_age_days.ge(180) & df.peer_duration_median.notna() & (df.project_age_days.ge(df.peer_duration_median*1.75))
# IF only on delay-related numeric features; this is a baseline, not ground-truth fraud/delay probability.
X=pd.DataFrame({'age_log':np.log1p(df.project_age_days.clip(lower=0)),'ratio':df.duration_vs_peer_median.clip(lower=0,upper=10),'days_since_last_exp':((ASOF-df.last_expenditure_date).dt.days).clip(lower=0)})
X=X.replace([np.inf,-np.inf],np.nan).fillna(X.median(numeric_only=True))
model=IsolationForest(n_estimators=250,contamination=0.05,random_state=42,n_jobs=-1).fit(X)
df['delay_if_raw_score']=-model.score_samples(X)
df['delay_anomaly_score']=df.delay_if_raw_score.rank(pct=True).mul(100).round(2)
df['delay_rule_flag']=(completed_rule|ongoing_rule).astype(int)
# conservative combined baseline score: prioritize peer-rule and IF percentile
# This is not a calibrated probability.
df['delay_score']=(0.65*df.delay_anomaly_score+35*df.delay_rule_flag).clip(0,100).round(2)
def reason(r):
 rr=[]
 if r.delay_rule_flag:
  if r.is_completed: rr.append('Completed duration is unusually long relative to comparable completed projects')
  else: rr.append('Ongoing project age is substantially above the comparable-project duration baseline')
 if pd.notna(r.duration_vs_peer_median) and r.duration_vs_peer_median>=2: rr.append(f'Project age/duration is {r.duration_vs_peer_median:.1f}x the peer median')
 if r.delay_anomaly_score>=95: rr.append('Delay-related pattern is in the highest 5% of unsupervised anomaly scores')
 return ' | '.join(rr)
df['delay_reasons']=df.apply(reason,axis=1)
out=['project_id','house','mp_name','state','constituency','work_category','status','sanction_date','completion_date','is_completed','project_age_days','peer_duration_n','peer_duration_median','peer_duration_q1','peer_duration_q3','duration_vs_peer_median','delay_robust_z','delay_anomaly_score','delay_rule_flag','delay_score','delay_reasons']
df[out].to_csv(BASE/'delay_baseline_results.csv',index=False)
print('rows',len(df),'rule flags',df.delay_rule_flag.sum(),'score>=90',(df.delay_score>=90).sum(),'score>=95',(df.delay_score>=95).sum())
print(df.nlargest(20,'delay_score')[['project_id','house','state','work_category','status','project_age_days','peer_duration_median','duration_vs_peer_median','delay_anomaly_score','delay_rule_flag','delay_score','delay_reasons']].to_string(index=False))
