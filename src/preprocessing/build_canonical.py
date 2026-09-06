from pathlib import Path
import pandas as pd, numpy as np, re
from sklearn.ensemble import IsolationForest
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.neighbors import NearestNeighbors

BASE=Path('/mnt/data')

def money(s):
    return pd.to_numeric(s.astype(str).str.replace(',','',regex=False).str.replace('₹','',regex=False).str.replace('nan','',regex=False).str.strip(), errors='coerce')

def wid(x):
    if pd.isna(x): return pd.NA
    m=re.search(r'(WS/\s*MP\d+/\d{4}-\d{4}/\d+)',str(x),re.I)
    return re.sub(r'\s+','',m.group(1)).upper() if m else pd.NA

def load(house):
    tag='Lok Sabha' if house=='Lok Sabha' else 'Rajya Sabha'
    san=pd.read_csv(BASE / (f'Works Sanctioned {tag}' + ('(1)' if house=='Lok Sabha' else '') + '.csv'), low_memory=False)
    rec=pd.read_csv(BASE/f'Works Recommended {tag}.csv',low_memory=False)
    comp=pd.read_csv(BASE/f'Works Completed {tag}.csv',low_memory=False)
    exp=pd.read_csv(BASE/f'Expenditure on Completed and On-going Works as on Date {tag}.csv',low_memory=False)
    san=san[san['Work Status'].notna() & ~san['Work Status'].astype(str).str.contains('Grand Total',case=False,na=False)].copy()
    san['project_id']=san['Work'].map(wid)
    san['sanction_amount']=money(san['Sanction Amount ( ₹ )'])
    san['recommended_date']=pd.to_datetime(san['Recommended date'],dayfirst=True,errors='coerce')
    san['sanction_date']=pd.to_datetime(san['Sanction Date'],dayfirst=True,errors='coerce')
    san=san.dropna(subset=['project_id']).drop_duplicates('project_id')
    rec['project_id']=rec['WORK'].map(wid); rec['recommended_amount']=money(rec['RECOMMENDED AMOUNT   ( ₹ )']); rec['rec_date']=pd.to_datetime(rec['Recommended date'],dayfirst=True,errors='coerce')
    rec=rec.dropna(subset=['project_id']).sort_values('rec_date').drop_duplicates('project_id',keep='last')
    comp['project_id']=comp['Work'].map(wid); comp['completion_date']=pd.to_datetime(comp['Completion Date'],dayfirst=True,errors='coerce'); comp['completed_amount']=money(comp['Amount Disbursed ( ₹ )'])
    comp=comp.dropna(subset=['project_id']).groupby('project_id').agg(completion_date=('completion_date','max'),completed_amount=('completed_amount','sum')).reset_index()
    exp['project_id']=exp['Work ID'].map(wid); exp['expenditure_date']=pd.to_datetime(exp['Expenditure Date'],dayfirst=True,errors='coerce'); exp['expenditure_amount']=money(exp['Fund Disbursed Amount ( ₹ )'])
    exp=exp.dropna(subset=['project_id'])
    expagg=exp.groupby('project_id').agg(total_expenditure=('expenditure_amount','sum'),first_expenditure_date=('expenditure_date','min'),last_expenditure_date=('expenditure_date','max'),payment_count=('expenditure_amount','size'),vendor_count=('Vendor Name','nunique')).reset_index()
    out=san[['project_id','State','IDA',"Hon'ble Members of Parliament"] + (["Constituency"] if 'Constituency' in san else []) + (["Elected/Nominated"] if 'Elected/Nominated' in san else []) + ['Work category','Work','Work description','recommended_date','sanction_date','sanction_amount','Work Status']].copy()
    out=out.rename(columns={'State':'state','IDA':'ida',"Hon'ble Members of Parliament":'mp_name','Constituency':'constituency','Elected/Nominated':'elected_nominated','Work category':'work_category','Work':'work_raw','Work description':'work_description','Work Status':'status'})
    out=out.merge(rec[['project_id','recommended_amount','rec_date']],on='project_id',how='left'); out['recommended_date']=out['recommended_date'].fillna(out['rec_date']); out.drop(columns=['rec_date'],inplace=True)
    out=out.merge(comp,on='project_id',how='left').merge(expagg,on='project_id',how='left')
    out['house']=house; out['is_completed']=out['completion_date'].notna().astype(int)
    out['utilization_ratio']=out['total_expenditure']/out['sanction_amount']
    out.loc[out['sanction_amount']<=0,'utilization_ratio']=np.nan
    out['recommendation_to_sanction_days']=(out['sanction_date']-out['recommended_date']).dt.days
    out['sanction_to_completion_days']=(out['completion_date']-out['sanction_date']).dt.days
    out['sanction_to_last_expenditure_days']=(out['last_expenditure_date']-out['sanction_date']).dt.days
    return out

ls=load('Lok Sabha'); rs=load('Rajya Sabha'); df=pd.concat([ls,rs],ignore_index=True)
# clean text
for c in ['state','mp_name','ida','work_category','work_description','status','constituency']:
    if c in df: df[c]=df[c].astype('string').str.strip()
df.to_csv(BASE/'mplads_ml/canonical_projects_rebuilt.csv',index=False)
print('canonical',df.shape)
print(df.groupby('house').size())
print('duplicate ids',df.project_id.duplicated().sum())
print('missing sanction',df.sanction_amount.isna().sum())
print('completion',df.is_completed.sum())
print('expenditure',df.total_expenditure.notna().sum())
print('exp>sanction',((df.total_expenditure>df.sanction_amount)&df.total_expenditure.notna()).sum())
print('status',df.status.value_counts(dropna=False).to_string())

# cost features: peer group = house + work category + state; use median and IQR, with fallback house+category
peer=['house','state','work_category']
g=df.groupby(peer)['sanction_amount'].agg(peer_median='median',peer_q1=lambda x:x.quantile(.25),peer_q3=lambda x:x.quantile(.75),peer_n='count').reset_index()
df=df.merge(g,on=peer,how='left')
df['iqr']=df.peer_q3-df.peer_q1
df['cost_vs_peer_median']=df.sanction_amount/df.peer_median
df['robust_cost_z']=(df.sanction_amount-df.peer_median)/(df.iqr/1.349).replace(0,np.nan)
# clip for IF and impute with peer medians
feat=df[['sanction_amount','utilization_ratio','recommendation_to_sanction_days']].copy()
feat['sanction_amount']=feat['sanction_amount'].fillna(feat['sanction_amount'].median())
feat['utilization_ratio']=feat['utilization_ratio'].clip(-2,3).fillna(feat['utilization_ratio'].median())
feat['recommendation_to_sanction_days']=feat['recommendation_to_sanction_days'].clip(-30,1500).fillna(feat['recommendation_to_sanction_days'].median())
# log amount stabilizes scale
feat['log_sanction_amount']=np.log1p(feat['sanction_amount'])
model=IsolationForest(n_estimators=300,contamination=0.03,random_state=42,n_jobs=-1)
model.fit(feat[['log_sanction_amount','utilization_ratio','recommendation_to_sanction_days']])
df['cost_if_raw_score']=-model.score_samples(feat[['log_sanction_amount','utilization_ratio','recommendation_to_sanction_days']])
# normalize 0-100 percentile; not probability
rank=df['cost_if_raw_score'].rank(pct=True)
df['cost_anomaly_score']=(rank*100).round(2)
# rule signal for overspend
overspend=(df.total_expenditure>df.sanction_amount) & df.total_expenditure.notna() & df.sanction_amount.notna()
df['overspend_flag']=overspend.astype(int)
# reasons
reasons=[]
for _,r in df.iterrows():
    rr=[]
    if pd.notna(r.cost_vs_peer_median) and r.cost_vs_peer_median>=2: rr.append(f"Sanction amount is {r.cost_vs_peer_median:.1f}x the peer-group median")
    if pd.notna(r.robust_cost_z) and r.robust_cost_z>=3: rr.append('Sanction amount is a strong upper-tail peer-group outlier')
    if r.overspend_flag: rr.append('Aggregated expenditure exceeds sanctioned amount')
    if r.cost_anomaly_score>=97: rr.append('High financial anomaly score from unsupervised detector')
    reasons.append(' | '.join(rr))
df['cost_reasons']=reasons
outcols=['project_id','house','mp_name','state','constituency','work_category','work_description','sanction_amount','recommended_amount','total_expenditure','utilization_ratio','peer_median','cost_vs_peer_median','robust_cost_z','cost_anomaly_score','overspend_flag','cost_reasons']
df[outcols].to_csv(BASE/'mplads_ml/cost_anomaly_results.csv',index=False)
# Save ML-ready dataset
mlcols=['project_id','house','mp_name','state','constituency','work_category','work_description','status','recommended_date','sanction_date','sanction_amount','recommended_amount','total_expenditure','first_expenditure_date','last_expenditure_date','payment_count','vendor_count','completion_date','completed_amount','is_completed','utilization_ratio','recommendation_to_sanction_days','sanction_to_completion_days','sanction_to_last_expenditure_days','peer_median','peer_q1','peer_q3','cost_vs_peer_median','robust_cost_z','cost_anomaly_score','overspend_flag','cost_reasons']
df[mlcols].to_csv(BASE/'mplads_ml/ml_ready_projects.csv',index=False)
print('cost high>=97', (df.cost_anomaly_score>=97).sum(), 'overspend',overspend.sum())
