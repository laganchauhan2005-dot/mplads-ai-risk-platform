from pathlib import Path
import pandas as pd
import numpy as np


# =========================================================
# PATHS
# =========================================================

COST_FILE = Path("data/result/cost_anomaly_results_v2.csv")
DELAY_FILE = Path("data/result/delay_baseline_results.csv")
DUPLICATE_FILE = Path("data/result/duplicate_alerts.csv")

OUT = Path("data/result/project_risk_results.csv")


# =========================================================
# LOAD DATA
# =========================================================

print("Loading ML results...")

cost = pd.read_csv(COST_FILE, low_memory=False)
delay = pd.read_csv(DELAY_FILE, low_memory=False)
duplicate = pd.read_csv(DUPLICATE_FILE, low_memory=False)

print("Cost rows:", len(cost))
print("Delay rows:", len(delay))
print("Duplicate alerts:", len(duplicate))


# =========================================================
# BASE PROJECT TABLE
#
# Cost results contain one row per project.
# =========================================================

risk = cost[
    [
        "project_id",
        "house",
        "mp_name",
        "state",
        "constituency",
        "work_category",
        "work_description",
        "status",
        "sanction_amount",
        "total_expenditure",
        "utilization_ratio",
    ]
].copy()


# =========================================================
# COST SIGNAL
# =========================================================

cost_signal = cost[
    [
        "project_id",
        "cost_anomaly_score",
        "cost_risk_level",
        "overspend_flag",
        "cost_reasons",
    ]
].copy()

risk = risk.merge(
    cost_signal,
    on="project_id",
    how="left"
)


# =========================================================
# DELAY SIGNAL
#
# Column names can vary slightly depending on the
# baseline detector version, so we identify the
# important score/reason columns.
# =========================================================

delay_columns = delay.columns.tolist()

delay_score_col = None

for candidate in [
    "delay_anomaly_score",
    "delay_score",
    "anomaly_score",
]:
    if candidate in delay_columns:
        delay_score_col = candidate
        break


if delay_score_col is None:

    raise ValueError(
        "Could not find delay anomaly score column. "
        f"Available columns: {delay_columns}"
    )


delay_keep = ["project_id", delay_score_col]

for col in [
    "delay_risk_level",
    "delay_flag",
    "delay_reasons",
    "delay_reason",
]:
    if col in delay_columns:
        delay_keep.append(col)


delay_signal = delay[delay_keep].copy()

delay_signal = delay_signal.rename(
    columns={
        delay_score_col: "delay_anomaly_score"
    }
)


risk = risk.merge(
    delay_signal,
    on="project_id",
    how="left"
)


# =========================================================
# DUPLICATE SIGNAL
#
# Duplicate data is pairwise:
#
# Project A <-> Project B
#
# We aggregate it into ONE project-level signal.
# =========================================================

if len(duplicate) > 0:

    duplicate["duplicate_alert_score"] = pd.to_numeric(
        duplicate["duplicate_alert_score"],
        errors="coerce"
    )

    duplicate["text_similarity"] = pd.to_numeric(
        duplicate["text_similarity"],
        errors="coerce"
    )

    duplicate["same_mp"] = pd.to_numeric(
        duplicate["same_mp"],
        errors="coerce"
    ).fillna(0)

    duplicate["same_constituency"] = pd.to_numeric(
        duplicate["same_constituency"],
        errors="coerce"
    ).fillna(0)

    # -----------------------------------------------------
    # Convert each pair into both project directions.
    # If A matches B, both A and B should receive
    # duplicate evidence.
    # -----------------------------------------------------

    forward = duplicate[
        [
            "project_id",
            "matched_project_id",
            "duplicate_alert_score",
            "text_similarity",
            "duplicate_alert_level",
            "alert_reason",
        ]
    ].copy()

    forward = forward.rename(
        columns={
            "matched_project_id": "matched_project",
        }
    )


    reverse = duplicate[
        [
            "matched_project_id",
            "project_id",
            "duplicate_alert_score",
            "text_similarity",
            "duplicate_alert_level",
            "alert_reason",
        ]
    ].copy()

    reverse = reverse.rename(
        columns={
            "matched_project_id": "project_id",
            "project_id": "matched_project",
        }
    )


    duplicate_project_pairs = pd.concat(
        [forward, reverse],
        ignore_index=True
    )


    # -----------------------------------------------------
    # Aggregate pairwise results per project
    # -----------------------------------------------------

    duplicate_project = (
        duplicate_project_pairs
        .groupby("project_id")
        .agg(
            duplicate_match_count=(
                "matched_project",
                "count"
            ),

            duplicate_max_score=(
                "duplicate_alert_score",
                "max"
            ),

            duplicate_max_similarity=(
                "text_similarity",
                "max"
            ),

            duplicate_high_count=(
                "duplicate_alert_level",
                lambda x: (x == "HIGH").sum()
            ),

            duplicate_medium_count=(
                "duplicate_alert_level",
                lambda x: (x == "MEDIUM").sum()
            ),

            duplicate_low_count=(
                "duplicate_alert_level",
                lambda x: (x == "LOW").sum()
            ),
        )
        .reset_index()
    )


    # -----------------------------------------------------
    # Keep strongest duplicate explanation
    # -----------------------------------------------------

    strongest = (
        duplicate_project_pairs
        .sort_values(
            ["project_id", "duplicate_alert_score"],
            ascending=[True, False]
        )
        .drop_duplicates("project_id")
    )

    strongest = strongest[
        [
            "project_id",
            "matched_project",
            "alert_reason",
        ]
    ].rename(
        columns={
            "matched_project":
                "strongest_duplicate_match",
            "alert_reason":
                "duplicate_reason",
        }
    )


    duplicate_project = duplicate_project.merge(
        strongest,
        on="project_id",
        how="left"
    )


else:

    duplicate_project = pd.DataFrame(
        columns=[
            "project_id",
            "duplicate_match_count",
            "duplicate_max_score",
            "duplicate_max_similarity",
            "duplicate_high_count",
            "duplicate_medium_count",
            "duplicate_low_count",
            "strongest_duplicate_match",
            "duplicate_reason",
        ]
    )


risk = risk.merge(
    duplicate_project,
    on="project_id",
    how="left"
)


# =========================================================
# FILL MISSING SIGNALS
# =========================================================

for col in [
    "cost_anomaly_score",
    "delay_anomaly_score",
    "duplicate_max_score",
]:
    if col in risk.columns:
        risk[col] = pd.to_numeric(
            risk[col],
            errors="coerce"
        ).fillna(0)


for col in [
    "duplicate_match_count",
    "duplicate_high_count",
    "duplicate_medium_count",
    "duplicate_low_count",
]:
    if col in risk.columns:
        risk[col] = (
            pd.to_numeric(
                risk[col],
                errors="coerce"
            )
            .fillna(0)
            .astype(int)
        )


# =========================================================
# DUPLICATE PROJECT-LEVEL SCORE
#
# The strongest pair is the main signal.
#
# Multiple matches add a small additional signal,
# but cannot overwhelm the overall score.
# =========================================================

risk["duplicate_risk_score"] = (
    risk["duplicate_max_score"]
    .fillna(0)
)


# =========================================================
# RISK ENGINE
#
# We use weighted signals:
#
# Cost      = 40%
# Delay     = 35%
# Duplicate = 25%
#
# These are initial prototype weights, NOT calibrated
# fraud probabilities.
# =========================================================

risk["overall_risk_score"] = (
    0.40 * risk["cost_anomaly_score"]
    + 0.35 * risk["delay_anomaly_score"]
    + 0.25 * risk["duplicate_risk_score"]
)


risk["overall_risk_score"] = (
    risk["overall_risk_score"]
    .clip(0, 100)
    .round(2)
)


# =========================================================
# RISK LEVEL
# =========================================================

risk["overall_risk_level"] = pd.cut(
    risk["overall_risk_score"],
    bins=[-1, 49, 69, 84, 100],
    labels=[
        "LOW",
        "MEDIUM",
        "HIGH",
        "CRITICAL"
    ]
).astype(str)


# =========================================================
# HUMAN-READABLE REASONS
# =========================================================

def build_risk_reasons(row):

    reasons = []

    # Cost
    if row["cost_anomaly_score"] >= 90:

        if pd.notna(row.get("cost_reasons")) and row["cost_reasons"]:
            reasons.append(
                "Cost anomaly: "
                + str(row["cost_reasons"])
            )
        else:
            reasons.append(
                f"High cost anomaly score "
                f"({row['cost_anomaly_score']:.1f})"
            )


    # Delay
    if row["delay_anomaly_score"] >= 90:

        delay_reason = None

        if "delay_reasons" in row.index:
            delay_reason = row["delay_reasons"]

        elif "delay_reason" in row.index:
            delay_reason = row["delay_reason"]

        if pd.notna(delay_reason) and str(delay_reason):
            reasons.append(
                "Delay anomaly: "
                + str(delay_reason)
            )
        else:
            reasons.append(
                f"High delay anomaly score "
                f"({row['delay_anomaly_score']:.1f})"
            )


    # Duplicate
    if row["duplicate_risk_score"] >= 90:

        duplicate_reason = row.get(
            "duplicate_reason",
            ""
        )

        match = row.get(
            "strongest_duplicate_match",
            ""
        )

        text = (
            f"Potential duplicate match"
            f" ({match})"
        )

        if pd.notna(duplicate_reason) and duplicate_reason:
            text += ": " + str(duplicate_reason)

        reasons.append(text)


    # Overspend
    if row["overspend_flag"] == 1:
        reasons.append(
            "Expenditure exceeds sanctioned amount"
        )


    if not reasons:
        reasons.append(
            "No major anomaly signal detected"
        )


    return " | ".join(reasons)


risk["overall_risk_reasons"] = risk.apply(
    build_risk_reasons,
    axis=1
)


# =========================================================
# FINAL OUTPUT
# =========================================================

output_columns = [
    "project_id",
    "house",
    "mp_name",
    "state",
    "constituency",
    "work_category",
    "work_description",
    "status",
    "sanction_amount",
    "total_expenditure",
    "utilization_ratio",

    # Cost
    "cost_anomaly_score",
    "cost_risk_level",
    "overspend_flag",
    "cost_reasons",

    # Delay
    "delay_anomaly_score",

    # Duplicate
    "duplicate_risk_score",
    "duplicate_match_count",
    "duplicate_high_count",
    "duplicate_medium_count",
    "duplicate_low_count",
    "duplicate_max_similarity",
    "strongest_duplicate_match",
    "duplicate_reason",

    # Overall
    "overall_risk_score",
    "overall_risk_level",
    "overall_risk_reasons",
]


# Keep only columns that actually exist
output_columns = [
    col for col in output_columns
    if col in risk.columns
]

risk = risk[output_columns]


# =========================================================
# SORT
# =========================================================

risk = risk.sort_values(
    "overall_risk_score",
    ascending=False
)


# =========================================================
# SAVE
# =========================================================

risk.to_csv(
    OUT,
    index=False
)


# =========================================================
# SUMMARY
# =========================================================

print()
print("========================================")
print("RISK ENGINE COMPLETE")
print("========================================")

print("Projects:", len(risk))

print()
print("Risk distribution:")

print(
    risk["overall_risk_level"]
    .value_counts()
    .sort_index()
)

print()

print(
    "CRITICAL:",
    (risk["overall_risk_level"] == "CRITICAL").sum()
)

print(
    "HIGH:",
    (risk["overall_risk_level"] == "HIGH").sum()
)

print(
    "MEDIUM:",
    (risk["overall_risk_level"] == "MEDIUM").sum()
)

print(
    "LOW:",
    (risk["overall_risk_level"] == "LOW").sum()
)

print()
print("Top 20 highest-risk projects:")

print(
    risk.head(20).to_string(index=False)
)

print()
print("Saved:", OUT)