from pathlib import Path
import pandas as pd


# =========================================================
# PATHS
# =========================================================

INPUT = Path("data/result/duplicate_candidates.csv")
OUT = Path("data/result/duplicate_alerts.csv")


# =========================================================
# LOAD
# =========================================================

df = pd.read_csv(INPUT, low_memory=False)

print("Candidate pairs loaded:", len(df))


# =========================================================
# REQUIRED COLUMNS
# =========================================================

required = [
    "project_id",
    "matched_project_id",
    "house",
    "state",
    "work_category",
    "text_similarity",
    "same_mp",
    "same_constituency",
    "amount_ratio",
]

missing = [c for c in required if c not in df.columns]

if missing:
    raise ValueError(f"Missing columns: {missing}")


# =========================================================
# CLEAN VALUES
# =========================================================

df["text_similarity"] = pd.to_numeric(
    df["text_similarity"],
    errors="coerce"
)

df["same_mp"] = pd.to_numeric(
    df["same_mp"],
    errors="coerce"
).fillna(0).astype(int)

df["same_constituency"] = pd.to_numeric(
    df["same_constituency"],
    errors="coerce"
).fillna(0).astype(int)

df["amount_ratio"] = pd.to_numeric(
    df["amount_ratio"],
    errors="coerce"
)

df["similar_amount"] = (
    df["amount_ratio"].notna()
    & (df["amount_ratio"] >= 0.80)
)


# =========================================================
# CONTEXTUAL EVIDENCE
# =========================================================

df["context_count"] = (
    df["same_mp"]
    + df["same_constituency"]
    + df["similar_amount"].astype(int)
)


# =========================================================
# ALERT CLASSIFICATION
#
# IMPORTANT:
# These are investigation priorities,
# NOT confirmed fraud.
# =========================================================

def classify(row):

    sim = row["text_similarity"]
    context = row["context_count"]

    # -----------------------------------------------
    # HIGH PRIORITY
    # -----------------------------------------------

    if (
        sim >= 0.98
        and row["same_mp"] == 1
        and row["similar_amount"]
    ):
        return "HIGH"

    if (
        sim >= 0.995
        and row["same_constituency"] == 1
        and row["similar_amount"]
    ):
        return "HIGH"


    # -----------------------------------------------
    # MEDIUM PRIORITY
    # -----------------------------------------------

    if sim >= 0.95 and context >= 1:
        return "MEDIUM"


    # -----------------------------------------------
    # LOW PRIORITY
    # -----------------------------------------------

    if sim >= 0.90 and context >= 1:
        return "LOW"


    # -----------------------------------------------
    # NOT AN ALERT
    # -----------------------------------------------

    return "NONE"


df["duplicate_alert_level"] = df.apply(
    classify,
    axis=1
)


# =========================================================
# KEEP ONLY ACTIONABLE ALERTS
# =========================================================

alerts = df[
    df["duplicate_alert_level"] != "NONE"
].copy()


# =========================================================
# SCORE
#
# Score represents investigation priority,
# NOT probability of fraud.
# =========================================================

def score(row):

    sim = row["text_similarity"]

    # Text similarity is dominant.
    score = sim * 100

    # Small contextual support.
    if row["same_mp"] == 1:
        score += 1

    if row["same_constituency"] == 1:
        score += 1

    if row["similar_amount"]:
        score += 1

    return min(round(score, 2), 100)


alerts["duplicate_alert_score"] = alerts.apply(
    score,
    axis=1
)


# =========================================================
# DUPLICATE TYPE
# =========================================================

alerts["duplicate_type"] = alerts[
    "duplicate_alert_level"
].map({
    "HIGH": "HIGH_PRIORITY_DUPLICATE_CANDIDATE",
    "MEDIUM": "POTENTIAL_DUPLICATE",
    "LOW": "SIMILAR_WORK"
})


# =========================================================
# EXPLANATION
# =========================================================

def explanation(row):

    reasons = []

    sim = row["text_similarity"]

    if sim >= 0.98:
        reasons.append(
            f"Very high text similarity ({sim:.2f})"
        )

    elif sim >= 0.95:
        reasons.append(
            f"High text similarity ({sim:.2f})"
        )

    else:
        reasons.append(
            f"Text similarity ({sim:.2f})"
        )

    if row["same_mp"] == 1:
        reasons.append("Same MP")

    if row["same_constituency"] == 1:
        reasons.append("Same constituency")

    if row["similar_amount"]:
        reasons.append(
            f"Similar sanctioned amount "
            f"(ratio {row['amount_ratio']:.2f})"
        )

    return " | ".join(reasons)


alerts["alert_reason"] = alerts.apply(
    explanation,
    axis=1
)


# =========================================================
# OUTPUT COLUMNS
# =========================================================

output_columns = [
    "project_id",
    "matched_project_id",
    "house",
    "state",
    "work_category",
    "text_similarity",
    "duplicate_alert_score",
    "duplicate_alert_level",
    "duplicate_type",
    "same_mp",
    "same_constituency",
    "similar_amount",
    "amount_ratio",
    "context_count",
    "alert_reason",
]

alerts = alerts[output_columns]


# =========================================================
# SORT
# =========================================================

priority = {
    "HIGH": 3,
    "MEDIUM": 2,
    "LOW": 1
}

alerts["_priority"] = (
    alerts["duplicate_alert_level"]
    .map(priority)
    .fillna(0)
)

alerts = (
    alerts
    .sort_values(
        ["_priority", "duplicate_alert_score"],
        ascending=False
    )
    .drop(columns="_priority")
)


# =========================================================
# SAVE
# =========================================================

alerts.to_csv(
    OUT,
    index=False
)


# =========================================================
# SUMMARY
# =========================================================

print()
print("========================================")
print("DUPLICATE ALERT FILTER COMPLETE")
print("========================================")

print("Candidate pairs:", len(df))
print("Actionable alerts:", len(alerts))

print(
    "HIGH:",
    (alerts["duplicate_alert_level"] == "HIGH").sum()
)

print(
    "MEDIUM:",
    (alerts["duplicate_alert_level"] == "MEDIUM").sum()
)

print(
    "LOW:",
    (alerts["duplicate_alert_level"] == "LOW").sum()
)

print()

if len(alerts) > 0:
    print("Top 20 alerts:")
    print(
        alerts.head(20).to_string(index=False)
    )

print()
print("Saved:", OUT)