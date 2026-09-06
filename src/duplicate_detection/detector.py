from pathlib import Path
import re
import numpy as np
import pandas as pd

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.neighbors import NearestNeighbors


# =========================================================
# PATHS
# =========================================================

INPUT = Path("data/processed/canonical_projects.csv")
OUT = Path("data/result/duplicate_candidates.csv")

df = pd.read_csv(INPUT, low_memory=False)

print("Total projects:", len(df))


# =========================================================
# TEXT NORMALIZATION
# =========================================================

def normalize_text(text):
    if pd.isna(text):
        return ""

    text = str(text).lower()

    # Remove punctuation
    text = re.sub(r"[^a-z0-9\s]", " ", text)

    # Normalize whitespace
    text = re.sub(r"\s+", " ", text).strip()

    return text


df["duplicate_text"] = (
    df["work_raw"].fillna("").astype(str)
    + " "
    + df["work_description"].fillna("").astype(str)
)

df["duplicate_text"] = df["duplicate_text"].apply(normalize_text)

working = df[df["duplicate_text"].str.len() >= 15].copy()

print("Projects with usable text:", len(working))


# =========================================================
# BLOCKING
#
# Compare projects within:
# House + State + Work Category
#
# This avoids comparing every project with every other
# project.
# =========================================================

working["block"] = (
    working["house"].fillna("").astype(str)
    + "||"
    + working["state"].fillna("").astype(str)
    + "||"
    + working["work_category"].fillna("").astype(str)
)


# =========================================================
# TF-IDF
# =========================================================

vectorizer = TfidfVectorizer(
    ngram_range=(1, 2),
    min_df=2,
    max_features=100000,
    sublinear_tf=True
)

tfidf = vectorizer.fit_transform(working["duplicate_text"])

print("TF-IDF matrix:", tfidf.shape)


# =========================================================
# DUPLICATE SEARCH
# =========================================================

results = []

# Similarity threshold
# Anything below this is not interesting enough for review.
MIN_SIMILARITY = 0.85

# Maximum number of neighbours examined per project.
# Keeps computation manageable.
N_NEIGHBORS = 15


for block_name, block_df in working.groupby("block"):

    block_indices = block_df.index.to_numpy()

    if len(block_indices) < 2:
        continue

    positions = [
        working.index.get_loc(idx)
        for idx in block_indices
    ]

    block_matrix = tfidf[positions]

    # Number of neighbours cannot exceed block size
    k = min(N_NEIGHBORS + 1, len(block_indices))

    nn = NearestNeighbors(
        n_neighbors=k,
        metric="cosine",
        algorithm="brute"
    )

    nn.fit(block_matrix)

    distances, neighbours = nn.kneighbors(block_matrix)

    for i in range(len(block_indices)):

        idx_a = block_indices[i]
        a = working.loc[idx_a]

        for j in range(1, k):

            neighbour_position = neighbours[i][j]
            idx_b = block_indices[neighbour_position]

            # Prevent duplicate A-B / B-A pairs
            if idx_a >= idx_b:
                continue

            b = working.loc[idx_b]

            similarity = 1 - distances[i][j]

            if similarity < MIN_SIMILARITY:
                continue

            # =================================================
            # CONTEXTUAL EVIDENCE
            # =================================================

            same_mp = (
                str(a["mp_name"]).strip().lower()
                == str(b["mp_name"]).strip().lower()
            )

            same_constituency = (
                str(a["constituency"]).strip().lower()
                == str(b["constituency"]).strip().lower()
            )

            amount_a = a["sanction_amount"]
            amount_b = b["sanction_amount"]

            if pd.notna(amount_a) and pd.notna(amount_b):

                max_amount = max(amount_a, amount_b)

                if max_amount > 0:
                    amount_ratio = (
                        min(amount_a, amount_b) / max_amount
                    )
                else:
                    amount_ratio = np.nan

            else:
                amount_ratio = np.nan


            # =================================================
            # DUPLICATE SCORE
            #
            # Text similarity is the PRIMARY signal.
            # Context only provides a modest adjustment.
            # =================================================

            score = similarity * 100

            supporting_evidence = 0

            if same_mp:
                supporting_evidence += 2

            if same_constituency:
                supporting_evidence += 2

            if pd.notna(amount_ratio) and amount_ratio >= 0.8:
                supporting_evidence += 1

            score = min(score + supporting_evidence, 100)


            # =================================================
            # CLASSIFICATION
            # =================================================

            if similarity >= 0.95:
                duplicate_type = "VERY_STRONG"

            elif similarity >= 0.90:
                duplicate_type = "STRONG"

            else:
                duplicate_type = "POTENTIAL"


            # =================================================
            # EXPLANATION
            # =================================================

            reasons = [
                f"Text similarity {similarity:.2f}"
            ]

            if same_mp:
                reasons.append("Same MP")

            if same_constituency:
                reasons.append("Same constituency")

            if pd.notna(amount_ratio) and amount_ratio >= 0.8:
                reasons.append("Similar sanctioned amount")


            results.append({
                "project_id": a["project_id"],
                "matched_project_id": b["project_id"],
                "house": a["house"],
                "state": a["state"],
                "work_category": a["work_category"],

                "text_similarity": round(similarity, 4),
                "duplicate_score": round(score, 2),
                "duplicate_type": duplicate_type,

                "same_mp": int(same_mp),
                "same_constituency": int(same_constituency),

                "amount_ratio": (
                    round(amount_ratio, 3)
                    if pd.notna(amount_ratio)
                    else np.nan
                ),

                "duplicate_reasons": " | ".join(reasons)
            })


# =========================================================
# SAVE RESULTS
# =========================================================

result_df = pd.DataFrame(results)

if len(result_df) > 0:

    result_df = (
        result_df
        .sort_values(
            ["duplicate_score", "text_similarity"],
            ascending=False
        )
        .drop_duplicates(
            subset=["project_id", "matched_project_id"]
        )
    )

result_df.to_csv(OUT, index=False)


# =========================================================
# SUMMARY
# =========================================================

print()
print("========================================")
print("DUPLICATE DETECTION COMPLETE")
print("========================================")

print("Candidate pairs:", len(result_df))

if len(result_df) > 0:

    print(
        "Very strong:",
        (result_df["duplicate_type"] == "VERY_STRONG").sum()
    )

    print(
        "Strong:",
        (result_df["duplicate_type"] == "STRONG").sum()
    )

    print(
        "Potential:",
        (result_df["duplicate_type"] == "POTENTIAL").sum()
    )

    print()
    print("Top 20 candidates:")

    print(
        result_df.head(20).to_string(index=False)
    )

print()
print("Saved:", OUT)