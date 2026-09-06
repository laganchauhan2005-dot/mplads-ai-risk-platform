# MPLADS AI Risk & Anomaly Detection — ML Approach

## 1. Overview

The ML layer of the MPLADS AI Risk & Anomaly Intelligence Platform analyzes sanctioned MPLADS projects and assigns risk signals based on:

1. Cost and financial anomalies
2. Delay and implementation anomalies
3. Duplicate or near-duplicate work descriptions
4. Rule-based compliance/financial inconsistencies
5. A combined project-level risk score

The system is designed as a **decision-support and investigation-prioritization system**.

It does **not** automatically declare a project fraudulent. An anomaly or high-risk score means that the project deserves further review.

---

## 2. Data Used

The current dataset consists of official MPLADS exports for both:

- Lok Sabha
- Rajya Sabha

The following datasets were used:

- Allocated MP limits
- Works recommended
- Works sanctioned
- Works completed
- Expenditure on completed and ongoing works

The datasets were joined using the available project/work identifiers.

After preprocessing and joining the available information, the canonical project dataset contains:

**98,646 sanctioned projects**

The canonical dataset is stored at:

`data/processed/canonical_projects.csv`

The ML output files are stored under:

`data/result/`

---

## 3. Canonical Project Dataset

The raw MPLADS datasets have different structures and field names.

A preprocessing pipeline converts them into a common project-level representation.

Important fields include:

- `project_id`
- `house`
- `state`
- `mp_name`
- `constituency`
- `work_category`
- `work_raw`
- `work_description`
- `recommended_date`
- `sanction_date`
- `sanction_amount`
- `status`
- `recommended_amount`
- `completion_date`
- `completed_amount`
- `total_expenditure`
- `first_expenditure_date`
- `last_expenditure_date`
- `payment_count`
- `vendor_count`
- `is_completed`
- `utilization_ratio`
- `recommendation_to_sanction_days`
- `sanction_to_completion_days`
- `sanction_to_last_expenditure_days`

### Important data interpretation

`is_completed` indicates the presence of a completion record. It should not be interpreted as proof that every project without a completion record is delayed.

Similarly, absence of expenditure data does not by itself indicate fraud or an anomaly.

The ML system therefore combines multiple signals instead of relying on a single missing field.

---

# 4. Cost & Financial Anomaly Detection

## Objective

Identify projects whose financial characteristics are unusual compared with similar MPLADS projects.

A project costing significantly more than comparable projects may deserve investigation, especially when combined with other signals such as unusual expenditure or low utilization.

## Peer Groups

Projects are not compared against one national average.

The primary peer group is:

`house + state + work_category`

For example, a Lok Sabha project in Uttar Pradesh under a particular work category is compared primarily with similar Lok Sabha projects in Uttar Pradesh and the same category.

If a peer group contains too few projects, the system falls back to:

`house + work_category`

This reduces misleading comparisons caused by very different project types or geographical cost structures.

## Features

The cost anomaly detector uses features including:

- Log-transformed sanction amount
- Utilization ratio
- Log-transformed total expenditure
- Log-transformed payment count
- Relative position within the peer group

Log transformation reduces the influence of extremely large monetary values.

## Algorithm

The current prototype uses:

**Isolation Forest**

Configuration:

- 300 estimators
- Contamination: 3%
- Random state: 42

Isolation Forest is an unsupervised anomaly detection algorithm that attempts to isolate observations that are unusual compared with the rest of the data.

## Cost Anomaly Score

The model output is converted into a **0–100 anomaly score**.

A higher score indicates greater financial unusualness relative to comparable projects.

This score is a ranking signal and **not a probability of fraud**.

The detector also generates interpretable reasons such as:

- Cost significantly above peer median
- High robust cost deviation
- High cost percentile
- Expenditure exceeding sanctioned amount

---

# 5. Delay & Implementation Anomaly Detection

## Objective

Identify projects whose implementation timeline appears unusually long compared with historically completed projects.

The system distinguishes between:

- Completed projects, which provide historical duration information
- Ongoing projects, whose current age can be compared against historical project durations

## Historical Baseline

For completed projects, implementation duration is calculated from:

`sanction_date → completion_date`

Historical durations are grouped using:

`house + state + work_category`

If insufficient historical projects are available, the system falls back to:

`house + work_category`

## Ongoing Project Analysis

For projects without a completion record, the system calculates the project's current age using its sanction date and the analysis date.

An ongoing project is not automatically classified as delayed simply because it is incomplete.

The current baseline requires a minimum project age before applying the delay anomaly logic.

The prototype currently uses a minimum age of approximately:

**180 days**

This avoids treating recently sanctioned projects as suspicious merely because they have not yet been completed.

## Features

Delay detection considers:

- Project age
- Historical peer completion duration
- Ratio of current age to peer duration
- Days since last expenditure where available

## Algorithm

The current prototype combines:

- Historical peer-duration baselines
- Rule-based delay signals
- Isolation Forest anomaly detection

The resulting score is normalized to:

**0–100**

A higher score indicates that the project's timeline is unusually long compared with comparable historical projects.

---

# 6. Duplicate / Near-Duplicate Work Detection

## Objective

Identify projects that may represent duplicate or highly similar works.

The system does not assume that similar descriptions are fraudulent.

MPLADS can legitimately contain repeated types of work, such as construction of similar infrastructure in different locations.

Therefore, text similarity is treated as a **candidate-generation and investigation signal**.

## Text Processing

The system combines:

- `work_raw`
- `work_description`

The text is normalized before comparison.

## Baseline NLP Method

The current prototype uses:

**TF-IDF + cosine similarity**

TF-IDF represents important words and phrases numerically.

Cosine similarity measures how similar two project descriptions are.

The current TF-IDF configuration uses:

- Unigrams and bigrams
- Minimum document frequency of 2
- Maximum 100,000 features
- Sublinear term frequency

## Candidate Search

Projects are initially blocked by:

`house + state + work_category`

This prevents unnecessary comparison between unrelated project groups.

For each project, nearest-neighbor search is used to identify highly similar descriptions.

The current candidate threshold is approximately:

**0.85 cosine similarity**

## Contextual Evidence

Text similarity alone is insufficient.

The duplicate alert system also considers contextual information such as:

- Same MP
- Same constituency
- Similar sanctioned amount
- Same house
- Same state
- Same work category

The stronger the combination of textual and contextual evidence, the higher the investigation priority.

## Alert Levels

The current prototype classifies candidate pairs into:

- HIGH
- MEDIUM
- LOW

These are **duplicate-risk alerts**, not confirmed duplicate-work findings.

A human reviewer should verify whether two similar projects actually refer to the same work.

---

# 7. Rule-Based Checks

Machine learning is supplemented with deterministic validation rules.

These checks are useful because some inconsistencies can be identified without statistical modeling.

Examples include:

- Recommendation occurring after sanction
- Completion occurring before sanction
- Expenditure occurring before sanction
- Non-positive sanctioned amount
- Expenditure exceeding sanctioned amount
- Completed amount exceeding sanctioned amount
- Missing or invalid project identifiers

Rule-based checks provide transparent evidence that can be shown directly to reviewers.

---

# 8. Project-Level Risk Engine

The individual detectors produce separate signals.

These are combined into a project-level risk score.

Current prototype components:

- Cost anomaly score
- Delay anomaly score
- Duplicate-risk score

The current prototype uses:

```text
Overall Risk Score =
    0.40 × Cost Anomaly Score
  + 0.35 × Delay Anomaly Score
  + 0.25 × Duplicate Risk Score
The resulting score is constrained to:

0–100

These weights are prototype weights intended for the hackathon demonstration.

They should be calibrated using validation data and reviewer feedback before being treated as production policy.

9. Risk Levels

The current prototype maps the overall score to four levels:

Score	Risk Level
0–49	LOW
50–69	MEDIUM
70–84	HIGH
85–100	CRITICAL

The purpose of these levels is to prioritize projects for investigation.

A CRITICAL project should therefore be interpreted as:

A project with multiple or unusually strong anomaly signals that should receive high investigation priority.

It should not be interpreted as:

A project proven to be fraudulent.

10. Explainability

The system stores the reasons contributing to each project's risk score.

Examples include:

Cost approximately 2× the peer median
Cost in the top 3% of the relevant peer group
Project age significantly above historical peer duration
Highly similar work description found
Similar project found for the same MP
Similar sanctioned amount
Expenditure inconsistency detected

The dashboard should expose these reasons to the reviewer instead of showing only a numerical score.

The objective is to answer:

"Why was this project flagged?"

rather than simply:

"Was this project flagged?"

11. Current ML Outputs

The current pipeline produces the following files:

Cost anomalies

data/result/cost_anomaly_results_v2.csv

Contains project-level financial anomaly results.

Delay anomalies

data/result/delay_baseline_results.csv

Contains project-level implementation/delay signals.

Duplicate candidates

data/result/duplicate_candidates.csv

Contains pairs of projects with high textual similarity.

Duplicate alerts

data/result/duplicate_alerts.csv

Contains contextualized duplicate-risk alerts.

Final project risk

data/result/project_risk_results.csv

Contains the combined project-level risk assessment.

This final file is the primary ML output that can be consumed by the backend.

12. Current Pipeline Results

The current pipeline successfully processes:

98,646 sanctioned projects

The final risk output contains one row per sanctioned project.

Current prototype risk distribution:

Risk Level	Projects
LOW	60,545
MEDIUM	29,881
HIGH	6,365
CRITICAL	1,855

These numbers represent the current prototype configuration and should not be interpreted as the actual prevalence of fraud or malpractice in MPLADS.

13. ML Pipeline

The overall processing flow is:

Official MPLADS Data
        ↓
Data Cleaning & Validation
        ↓
Canonical Project Dataset
        ↓
Feature Engineering
        ↓
 ┌───────────────┬────────────────┬──────────────────┐
 ↓               ↓                ↓
Cost Detector   Delay Detector   Duplicate Detector
 ↓               ↓                ↓
 └───────────────┴────────────────┘
                 ↓
          Rule-Based Checks
                 ↓
          Risk Aggregation
                 ↓
       Project Risk Assessment
                 ↓
       Explainability / Evidence
                 ↓
          Backend Database
                 ↓
        Dashboard & Review UI
14. Human-in-the-Loop Design

The platform is designed for human investigation rather than fully automated enforcement.

The system should use terminology such as:

Potential anomaly
Elevated risk
Investigation priority
Duplicate candidate
Financial inconsistency

It should avoid automatically displaying:

Confirmed fraud
Fraudulent MP
Fraudulent project

unless such a conclusion is independently established through an appropriate investigation process.

Human reviewers should be able to:

Open a flagged project
View the anomaly reasons
Compare it with peer projects
Inspect similar project candidates
Review financial and timeline information
Mark the alert for further review
Record a resolution or reviewer note

15. Evaluation Strategy
Because the current dataset does not provide confirmed fraud labels, traditional supervised accuracy cannot be directly used for every detector.
The evaluation strategy therefore focuses on anomaly usefulness and reviewer validation.

Duplicate Detection:
  Create a manually reviewed sample of duplicate candidates and measure:
     -Precision
     -Recall where ground truth can be established
     -False-positive rate
     -Reviewer agreement

Cost Anomaly Detection:
Evaluate whether highly ranked projects are genuinely unusual compared with appropriate peer groups.
  Metrics can include:
   -Precision@K
   -Reviewer agreement
   -Peer-relative cost deviation

Delay Detection:
  Evaluate flagged projects against:
    -Historical completion outcomes
    -Known long-duration projects
    -Reviewer assessment

Risk Engine
  Evaluate:
   -Usefulness of Top-10 / Top-25 / Top-50 risk queues
   -Number of meaningful signals per high-risk project
   -Reviewer agreement
   -Explainability and understandability

16. Limitations

The current ML system has several important limitations.

No confirmed fraud labels:
The current data does not provide a reliable project-level label indicating confirmed fraud.
Therefore, the system is primarily an unsupervised anomaly and risk-ranking system.

Similar descriptions can be legitimate:
Two projects with nearly identical descriptions may represent genuinely different works.
Therefore, duplicate alerts require human verification.

Risk score is not fraud probability:
A score of 90 does not mean a 90% probability of fraud.
It means that the project has a high level of anomaly/risk according to the current scoring framework.

Prototype weights:
The 40/35/25 risk weights are initial prototype choices.
They should eventually be calibrated using historical outcomes and reviewer feedback.

Data availability:
Some useful signals, such as detailed physical progress, location coordinates, or richer payment-level information, may not be consistently available in the current exports.

Future versions can incorporate additional verified data sources when available.

17. Future Improvements

Potential future improvements include:

Sentence-transformer embeddings for stronger semantic duplicate detection
Geospatial duplicate detection using project coordinates
More sophisticated expected-cost models
Robust statistical peer-group modeling
Supervised fraud/anomaly classification if verified historical labels become available
Temporal anomaly detection
Graph-based analysis of MPs, vendors, agencies and projects
Vendor concentration analysis
Payment-pattern anomaly detection
Predictive early-warning models
Automated model calibration using reviewer feedback
Historical risk-score tracking
Model monitoring and drift detection

18. Design Principle

The central principle of the ML system is:

Detect unusual patterns, explain why they are unusual, and help humans decide what deserves investigation.

The system is therefore designed to prioritize transparency, peer-relative comparison, explainability, and human review over unsupported claims of fraud.