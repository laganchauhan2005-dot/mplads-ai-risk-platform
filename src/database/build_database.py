"""
Build the MPLADS SQLite database from processed ML outputs.

Run from the repository root:

    python src/database/build_database.py

Expected input files:

    data/processed/canonical_projects.csv
    data/result/project_risk_results.csv
    data/result/duplicate_alerts.csv

The script creates:

    database/mplads.db
"""

from pathlib import Path
import sqlite3
import hashlib
import sys

import pandas as pd


# ============================================================
# PATHS
# ============================================================

ROOT = Path(__file__).resolve().parents[2]

CANONICAL_FILE = ROOT / "data" / "processed" / "canonical_projects.csv"
RISK_FILE = ROOT / "data" / "result" / "project_risk_results.csv"
DUPLICATE_FILE = ROOT / "data" / "result" / "duplicate_alerts.csv"

DATABASE_DIR = ROOT / "database"
DATABASE_FILE = DATABASE_DIR / "mplads.db"


# ============================================================
# HELPERS
# ============================================================

def check_file(path: Path, required: bool = True):
    """Check whether an input file exists."""
    if path.exists():
        print(f"[OK] {path.relative_to(ROOT)}")
        return True

    if required:
        print(f"[ERROR] Missing required file: {path}")
        return False

    print(f"[WARNING] Optional file not found: {path}")
    return False


def clean_column_names(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize column names."""
    df = df.copy()

    df.columns = (
        df.columns
        .astype(str)
        .str.strip()
        .str.lower()
        .str.replace(" ", "_", regex=False)
    )

    return df


def find_column(df: pd.DataFrame, *names):
    """
    Find a column using several possible names.

    Returns None if no matching column exists.
    """
    columns = {str(c).lower().strip(): c for c in df.columns}

    for name in names:
        key = name.lower().strip()

        if key in columns:
            return columns[key]

    return None


def safe_value(value):
    """Convert pandas values into SQLite-safe values."""
    if pd.isna(value):
        return None

    # Convert numpy scalar types to native Python types.
    if hasattr(value, "item"):
        try:
            return value.item()
        except Exception:
            pass

    return value


def make_mp_id(row):
    """
    Create a stable identifier for an MP.

    We use house + MP name + state + constituency/elected-nominated
    because the same MP name may potentially appear in different contexts.
    """

    house = str(row.get("house") or "").strip().upper()
    mp_name = str(row.get("mp_name") or "").strip().upper()
    state = str(row.get("state") or "").strip().upper()
    constituency = str(row.get("constituency") or "").strip().upper()

    raw = f"{house}|{mp_name}|{state}|{constituency}"

    return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:16]


def convert_bool(value):
    """Convert common boolean representations to 0/1."""
    if pd.isna(value):
        return None

    if isinstance(value, bool):
        return int(value)

    text = str(value).strip().lower()

    if text in {"true", "1", "yes", "y"}:
        return 1

    if text in {"false", "0", "no", "n"}:
        return 0

    return None


# ============================================================
# DATABASE SCHEMA
# ============================================================

SCHEMA = """

PRAGMA foreign_keys = ON;


-- ==========================================================
-- MPs
-- ==========================================================

CREATE TABLE IF NOT EXISTS mps (
    mp_id TEXT PRIMARY KEY,
    mp_name TEXT NOT NULL,
    house TEXT,
    state TEXT,
    constituency TEXT,
    allocated_amount REAL
);


-- ==========================================================
-- Projects
-- ==========================================================

CREATE TABLE IF NOT EXISTS projects (
    project_id TEXT PRIMARY KEY,

    mp_id TEXT,

    house TEXT,
    state TEXT,
    mp_name TEXT,
    constituency TEXT,

    work_category TEXT,
    work_raw TEXT,
    work_description TEXT,

    recommended_date TEXT,
    sanction_date TEXT,
    sanction_amount REAL,

    status TEXT,
    recommended_amount REAL,

    completion_date TEXT,
    completed_amount REAL,

    total_expenditure REAL,
    first_expenditure_date TEXT,
    last_expenditure_date TEXT,

    payment_count INTEGER,
    vendor_count INTEGER,

    is_completed INTEGER,

    utilization_ratio REAL,

    recommendation_to_sanction_days REAL,
    sanction_to_completion_days REAL,
    sanction_to_last_expenditure_days REAL,

    FOREIGN KEY (mp_id) REFERENCES mps(mp_id)
);


-- ==========================================================
-- Risk Assessments
-- ==========================================================
CREATE TABLE IF NOT EXISTS risk_assessments (
    project_id TEXT PRIMARY KEY,

    cost_anomaly_score REAL,
    cost_risk_level TEXT,
    overspend_flag INTEGER,
    cost_reasons TEXT,

    delay_anomaly_score REAL,

    duplicate_risk_score REAL,
    duplicate_match_count INTEGER,
    duplicate_high_count INTEGER,
    duplicate_medium_count INTEGER,
    duplicate_low_count INTEGER,
    duplicate_max_similarity REAL,
    strongest_duplicate_match TEXT,
    duplicate_reason TEXT,

    overall_risk_score REAL,
    risk_level TEXT,
    risk_reasons TEXT,

    assessment_date TEXT,

    FOREIGN KEY (project_id) REFERENCES projects(project_id)
);

-- ==========================================================
-- Duplicate Alerts
-- ==========================================================

CREATE TABLE IF NOT EXISTS duplicate_alerts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,

    project_id TEXT NOT NULL,
    matched_project_id TEXT NOT NULL,

    similarity REAL,
    alert_score REAL,
    alert_level TEXT,

    same_mp INTEGER,
    same_constituency INTEGER,
    similar_amount INTEGER,

    reason TEXT,

    FOREIGN KEY (project_id) REFERENCES projects(project_id),
    FOREIGN KEY (matched_project_id) REFERENCES projects(project_id)
);


-- ==========================================================
-- Risk History
-- ==========================================================

CREATE TABLE IF NOT EXISTS risk_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,

    project_id TEXT NOT NULL,

    assessment_date TEXT,

    cost_score REAL,
    delay_score REAL,
    duplicate_score REAL,

    overall_score REAL,
    risk_level TEXT,

    risk_reasons TEXT,

    FOREIGN KEY (project_id) REFERENCES projects(project_id)
);


-- ==========================================================
-- INDEXES
-- ==========================================================

CREATE INDEX IF NOT EXISTS idx_projects_mp
ON projects(mp_id);

CREATE INDEX IF NOT EXISTS idx_projects_house
ON projects(house);

CREATE INDEX IF NOT EXISTS idx_projects_state
ON projects(state);

CREATE INDEX IF NOT EXISTS idx_projects_category
ON projects(work_category);

CREATE INDEX IF NOT EXISTS idx_projects_risk_join
ON projects(project_id);

CREATE INDEX IF NOT EXISTS idx_risk_level
ON risk_assessments(risk_level);

CREATE INDEX IF NOT EXISTS idx_risk_score
ON risk_assessments(overall_risk_score DESC);

CREATE INDEX IF NOT EXISTS idx_risk_project
ON risk_assessments(project_id);

CREATE INDEX IF NOT EXISTS idx_duplicate_project
ON duplicate_alerts(project_id);

CREATE INDEX IF NOT EXISTS idx_duplicate_match
ON duplicate_alerts(matched_project_id);

CREATE INDEX IF NOT EXISTS idx_duplicate_level
ON duplicate_alerts(alert_level);

CREATE INDEX IF NOT EXISTS idx_history_project
ON risk_history(project_id);

CREATE INDEX IF NOT EXISTS idx_history_date
ON risk_history(assessment_date);


-- ==========================================================
-- Useful backend views
-- ==========================================================

CREATE VIEW IF NOT EXISTS project_risk_view AS
SELECT
    p.project_id,
    p.house,
    p.state,
    p.mp_name,
    p.constituency,
    p.work_category,
    p.work_description,
    p.status,
    p.sanction_date,
    p.sanction_amount,
    p.total_expenditure,
    p.utilization_ratio,

    r.cost_anomaly_score,
    r.delay_anomaly_score,
    r.duplicate_risk_score,
    r.overall_risk_score,
    r.risk_level,
    r.risk_reasons,
    r.duplicate_match_count,
    r.duplicate_max_similarity

FROM projects p

LEFT JOIN risk_assessments r
    ON p.project_id = r.project_id;


CREATE VIEW IF NOT EXISTS high_risk_projects AS
SELECT *
FROM project_risk_view
WHERE risk_level IN ('HIGH', 'CRITICAL')
ORDER BY overall_risk_score DESC;


"""


# ============================================================
# LOAD CANONICAL PROJECTS
# ============================================================

def load_projects():

    print("\n" + "=" * 60)
    print("LOADING CANONICAL PROJECTS")
    print("=" * 60)

    df = pd.read_csv(CANONICAL_FILE, low_memory=False)

    df = clean_column_names(df)

    print(f"Rows loaded: {len(df):,}")
    print(f"Columns: {len(df.columns)}")

    project_col = find_column(df, "project_id")

    if project_col is None:
        raise ValueError("canonical_projects.csv has no project_id column.")

    # Remove invalid IDs.
    df[project_col] = df[project_col].astype(str).str.strip()

    df = df[
        df[project_col].notna()
        & (df[project_col] != "")
        & (df[project_col].str.lower() != "nan")
    ].copy()

    # Remove duplicate project IDs if any.
    before = len(df)

    df = df.drop_duplicates(
        subset=[project_col],
        keep="first"
    )

    removed = before - len(df)

    if removed:
        print(f"Removed duplicate project IDs: {removed:,}")

    print(f"Final project rows: {len(df):,}")

    return df


# ============================================================
# LOAD RISK RESULTS
# ============================================================

def load_risk_results():

    print("\n" + "=" * 60)
    print("LOADING RISK RESULTS")
    print("=" * 60)

    if not RISK_FILE.exists():
        print("[WARNING] Risk results file not found.")
        return pd.DataFrame()

    df = pd.read_csv(RISK_FILE, low_memory=False)

    df = clean_column_names(df)

    print(f"Risk rows loaded: {len(df):,}")

    project_col = find_column(df, "project_id")

    if project_col is None:
        raise ValueError(
            "project_risk_results.csv has no project_id column."
        )

    df[project_col] = df[project_col].astype(str).str.strip()

    return df


# ============================================================
# LOAD DUPLICATE ALERTS
# ============================================================

def load_duplicate_alerts():

    print("\n" + "=" * 60)
    print("LOADING DUPLICATE ALERTS")
    print("=" * 60)

    if not DUPLICATE_FILE.exists():
        print("[WARNING] Duplicate alerts file not found.")
        return pd.DataFrame()

    df = pd.read_csv(DUPLICATE_FILE, low_memory=False)

    df = clean_column_names(df)

    print(f"Duplicate alert rows: {len(df):,}")

    return df


# ============================================================
# INSERT MPs
# ============================================================

def insert_mps(conn, projects):

    print("\n" + "=" * 60)
    print("BUILDING MP TABLE")
    print("=" * 60)

    records = {}

    for _, row in projects.iterrows():

        mp_name = safe_value(row.get("mp_name"))
        house = safe_value(row.get("house"))
        state = safe_value(row.get("state"))
        constituency = safe_value(row.get("constituency"))

        if not mp_name:
            continue

        mp_id = make_mp_id(row)

        key = mp_id

        if key not in records:

            records[key] = (
                mp_id,
                mp_name,
                house,
                state,
                constituency,
                None
            )

    conn.executemany(
        """
        INSERT OR REPLACE INTO mps
        (
            mp_id,
            mp_name,
            house,
            state,
            constituency,
            allocated_amount
        )
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        list(records.values())
    )

    print(f"MP records created: {len(records):,}")


# ============================================================
# INSERT PROJECTS
# ============================================================

def insert_projects(conn, projects):

    print("\n" + "=" * 60)
    print("BUILDING PROJECT TABLE")
    print("=" * 60)

    records = []

    for _, row in projects.iterrows():

        project_id = safe_value(row.get("project_id"))

        if not project_id:
            continue

        mp_id = make_mp_id(row)

        records.append(
            (
                project_id,
                mp_id,

                safe_value(row.get("house")),
                safe_value(row.get("state")),
                safe_value(row.get("mp_name")),
                safe_value(row.get("constituency")),

                safe_value(row.get("work_category")),
                safe_value(row.get("work_raw")),
                safe_value(row.get("work_description")),

                safe_value(row.get("recommended_date")),
                safe_value(row.get("sanction_date")),
                safe_value(row.get("sanction_amount")),

                safe_value(row.get("status")),
                safe_value(row.get("recommended_amount")),

                safe_value(row.get("completion_date")),
                safe_value(row.get("completed_amount")),

                safe_value(row.get("total_expenditure")),
                safe_value(row.get("first_expenditure_date")),
                safe_value(row.get("last_expenditure_date")),

                safe_value(row.get("payment_count")),
                safe_value(row.get("vendor_count")),

                convert_bool(row.get("is_completed")),

                safe_value(row.get("utilization_ratio")),

                safe_value(
                    row.get("recommendation_to_sanction_days")
                ),

                safe_value(
                    row.get("sanction_to_completion_days")
                ),

                safe_value(
                    row.get("sanction_to_last_expenditure_days")
                ),
            )
        )

    conn.executemany(
        """
        INSERT OR REPLACE INTO projects
        (
            project_id,
            mp_id,

            house,
            state,
            mp_name,
            constituency,

            work_category,
            work_raw,
            work_description,

            recommended_date,
            sanction_date,
            sanction_amount,

            status,
            recommended_amount,

            completion_date,
            completed_amount,

            total_expenditure,
            first_expenditure_date,
            last_expenditure_date,

            payment_count,
            vendor_count,

            is_completed,

            utilization_ratio,

            recommendation_to_sanction_days,
            sanction_to_completion_days,
            sanction_to_last_expenditure_days
        )
        VALUES (
            ?, ?,
            ?, ?, ?, ?,
            ?, ?, ?,
            ?, ?, ?,
            ?, ?,
            ?, ?,
            ?, ?, ?,
            ?, ?,
            ?,
            ?,
            ?, ?, ?
        )
        """,
        records
    )

    print(f"Project records inserted: {len(records):,}")


# ============================================================
# INSERT RISK RESULTS
# ============================================================

def insert_risk_results(conn, risk_df):

    print("\n" + "=" * 60)
    print("BUILDING RISK ASSESSMENTS")
    print("=" * 60)

    if risk_df.empty:
        print("[WARNING] No risk data to insert.")
        return

    project_col = find_column(
        risk_df,
        "project_id"
    )

    cost_col = find_column(
        risk_df,
        "cost_anomaly_score"
    )

    cost_level_col = find_column(
        risk_df,
        "cost_risk_level"
    )

    overspend_col = find_column(
        risk_df,
        "overspend_flag"
    )

    cost_reasons_col = find_column(
        risk_df,
        "cost_reasons"
    )

    delay_col = find_column(
        risk_df,
        "delay_anomaly_score",
        "delay_score",
        "anomaly_score"
    )

    duplicate_col = find_column(
        risk_df,
        "duplicate_risk_score",
        "duplicate_score"
    )

    duplicate_match_count_col = find_column(
        risk_df,
        "duplicate_match_count",
        "duplicate_count"
    )

    duplicate_high_col = find_column(
        risk_df,
        "duplicate_high_count"
    )

    duplicate_medium_col = find_column(
        risk_df,
        "duplicate_medium_count"
    )

    duplicate_low_col = find_column(
        risk_df,
        "duplicate_low_count"
    )

    duplicate_similarity_col = find_column(
        risk_df,
        "duplicate_max_similarity",
        "max_similarity"
    )

    strongest_duplicate_col = find_column(
        risk_df,
        "strongest_duplicate_match"
    )

    duplicate_reason_col = find_column(
        risk_df,
        "duplicate_reason"
    )

    overall_col = find_column(
        risk_df,
        "overall_risk_score",
        "risk_score",
        "overall_score"
    )

    level_col = find_column(
        risk_df,
        "overall_risk_level",
        "risk_level",
        "risk"
    )

    reasons_col = find_column(
        risk_df,
        "overall_risk_reasons",
        "risk_reasons",
        "reasons",
        "reason"
    )

    if project_col is None:
        raise ValueError(
            "project_risk_results.csv has no project_id column."
        )

    if level_col is None:
        raise ValueError(
            "Could not find overall risk level column."
        )

    if reasons_col is None:
        raise ValueError(
            "Could not find overall risk reasons column."
        )

    assessment_date = pd.Timestamp.now().strftime("%Y-%m-%d")

    records = []

    for _, row in risk_df.iterrows():

        project_id = safe_value(row.get(project_col))

        if not project_id:
            continue

        records.append(
            (
                project_id,

                # Cost
                safe_value(row.get(cost_col))
                if cost_col else None,

                safe_value(row.get(cost_level_col))
                if cost_level_col else None,

                convert_bool(row.get(overspend_col))
                if overspend_col else None,

                safe_value(row.get(cost_reasons_col))
                if cost_reasons_col else None,

                # Delay
                safe_value(row.get(delay_col))
                if delay_col else None,

                # Duplicate
                safe_value(row.get(duplicate_col))
                if duplicate_col else None,

                safe_value(row.get(duplicate_match_count_col))
                if duplicate_match_count_col else None,

                safe_value(row.get(duplicate_high_col))
                if duplicate_high_col else None,

                safe_value(row.get(duplicate_medium_col))
                if duplicate_medium_col else None,

                safe_value(row.get(duplicate_low_col))
                if duplicate_low_col else None,

                safe_value(row.get(duplicate_similarity_col))
                if duplicate_similarity_col else None,

                safe_value(row.get(strongest_duplicate_col))
                if strongest_duplicate_col else None,

                safe_value(row.get(duplicate_reason_col))
                if duplicate_reason_col else None,

                # Overall
                safe_value(row.get(overall_col))
                if overall_col else None,

                safe_value(row.get(level_col)),

                safe_value(row.get(reasons_col)),

                assessment_date,
            )
        )

    conn.executemany(
        """
        INSERT OR REPLACE INTO risk_assessments
        (
            project_id,

            cost_anomaly_score,
            cost_risk_level,
            overspend_flag,
            cost_reasons,

            delay_anomaly_score,

            duplicate_risk_score,
            duplicate_match_count,
            duplicate_high_count,
            duplicate_medium_count,
            duplicate_low_count,
            duplicate_max_similarity,
            strongest_duplicate_match,
            duplicate_reason,

            overall_risk_score,
            risk_level,
            risk_reasons,

            assessment_date
        )
        VALUES (
            ?,

            ?, ?, ?, ?,

            ?,

            ?, ?, ?, ?, ?, ?, ?, ?,

            ?, ?, ?,

            ?
        )
        """,
        records
    )

    # Create initial historical assessment.
    conn.executemany(
        """
        INSERT INTO risk_history
        (
            project_id,
            assessment_date,
            cost_score,
            delay_score,
            duplicate_score,
            overall_score,
            risk_level,
            risk_reasons
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            (
                r[0],   # project_id
                r[17],  # assessment_date
                r[1],   # cost score
                r[5],   # delay score
                r[6],   # duplicate score
                r[14],  # overall score
                r[15],  # risk level
                r[16],  # risk reasons
            )
            for r in records
        ]
    )

    print(
        f"Risk assessments inserted: {len(records):,}"
    )


# ============================================================
# INSERT DUPLICATE ALERTS
# ============================================================

def insert_duplicate_alerts(conn, duplicate_df):

    print("\n" + "=" * 60)
    print("BUILDING DUPLICATE ALERT TABLE")
    print("=" * 60)

    if duplicate_df.empty:
        print("[WARNING] No duplicate alerts to insert.")
        return

    project_col = find_column(
        duplicate_df,
        "project_id",
        "project_id_1"
    )

    matched_col = find_column(
        duplicate_df,
        "matched_project_id",
        "project_id_2",
        "match_project_id"
    )

    similarity_col = find_column(
        duplicate_df,
        "similarity",
        "text_similarity",
        "cosine_similarity"
    )

    score_col = find_column(
        duplicate_df,
        "alert_score",
        "duplicate_score",
        "score"
    )

    level_col = find_column(
        duplicate_df,
        "alert_level",
        "level"
    )

    same_mp_col = find_column(
        duplicate_df,
        "same_mp"
    )

    same_constituency_col = find_column(
        duplicate_df,
        "same_constituency"
    )

    similar_amount_col = find_column(
        duplicate_df,
        "similar_amount"
    )

    reason_col = find_column(
        duplicate_df,
        "reason",
        "alert_reason"
    )

    if project_col is None or matched_col is None:
        print(
            "[WARNING] Could not identify project pair columns."
        )
        print(
            "Available columns:",
            list(duplicate_df.columns)
        )
        return

    records = []

    for _, row in duplicate_df.iterrows():

        project_id = safe_value(row.get(project_col))
        matched_id = safe_value(row.get(matched_col))

        if not project_id or not matched_id:
            continue

        records.append(
            (
                project_id,
                matched_id,

                safe_value(row.get(similarity_col))
                if similarity_col else None,

                safe_value(row.get(score_col))
                if score_col else None,

                safe_value(row.get(level_col))
                if level_col else None,

                convert_bool(row.get(same_mp_col))
                if same_mp_col else None,

                convert_bool(row.get(same_constituency_col))
                if same_constituency_col else None,

                convert_bool(row.get(similar_amount_col))
                if similar_amount_col else None,

                safe_value(row.get(reason_col))
                if reason_col else None,
            )
        )

    conn.executemany(
        """
        INSERT INTO duplicate_alerts
        (
            project_id,
            matched_project_id,
            similarity,
            alert_score,
            alert_level,
            same_mp,
            same_constituency,
            similar_amount,
            reason
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        records
    )

    print(f"Duplicate alerts inserted: {len(records):,}")


# ============================================================
# VERIFICATION
# ============================================================

def verify_database(conn):

    print("\n" + "=" * 60)
    print("DATABASE VERIFICATION")
    print("=" * 60)

    tables = [
        "mps",
        "projects",
        "risk_assessments",
        "duplicate_alerts",
        "risk_history",
    ]

    for table in tables:

        result = conn.execute(
            f"SELECT COUNT(*) FROM {table}"
        ).fetchone()[0]

        print(f"{table:25s}: {result:,}")

    print("\nRisk distribution:")

    rows = conn.execute(
        """
        SELECT
            risk_level,
            COUNT(*) AS project_count
        FROM risk_assessments
        GROUP BY risk_level
        ORDER BY
            CASE risk_level
                WHEN 'CRITICAL' THEN 1
                WHEN 'HIGH' THEN 2
                WHEN 'MEDIUM' THEN 3
                WHEN 'LOW' THEN 4
                ELSE 5
            END
        """
    ).fetchall()

    for level, count in rows:
        print(f"  {str(level):10s}: {count:,}")

    print("\nTop 10 highest-risk projects:")

    rows = conn.execute(
        """
        SELECT
            project_id,
            mp_name,
            state,
            overall_risk_score,
            risk_level
        FROM project_risk_view
        WHERE overall_risk_score IS NOT NULL
        ORDER BY overall_risk_score DESC
        LIMIT 10
        """
    ).fetchall()

    for row in rows:
        print(
            f"  {row[0]} | "
            f"{row[1]} | "
            f"{row[2]} | "
            f"{row[3]:.2f} | "
            f"{row[4]}"
        )

    print("\nTesting high-risk view:")

    count = conn.execute(
        """
        SELECT COUNT(*)
        FROM high_risk_projects
        """
    ).fetchone()[0]

    print(f"  HIGH + CRITICAL projects: {count:,}")


# ============================================================
# MAIN
# ============================================================

def main():

    print("\n")
    print("=" * 60)
    print(" MPLADS AI RISK PLATFORM — DATABASE BUILDER")
    print("=" * 60)

    print("\nChecking input files...\n")

    if not check_file(CANONICAL_FILE):
        sys.exit(1)

    check_file(RISK_FILE, required=False)
    check_file(DUPLICATE_FILE, required=False)

    # Create database directory.
    DATABASE_DIR.mkdir(parents=True, exist_ok=True)

    # Remove existing database so the build is reproducible.
    if DATABASE_FILE.exists():

        print(
            f"\nExisting database found: "
            f"{DATABASE_FILE}"
        )

        print("Rebuilding database from scratch...")

        DATABASE_FILE.unlink()

    # Load source data.
    projects = load_projects()
    risk_results = load_risk_results()
    duplicate_alerts = load_duplicate_alerts()

    # Create SQLite database.
    print("\n" + "=" * 60)
    print("CREATING DATABASE")
    print("=" * 60)

    conn = sqlite3.connect(DATABASE_FILE)

    try:

        # Improve SQLite performance.
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
        conn.execute("PRAGMA foreign_keys=ON;")

        # Create schema.
        conn.executescript(SCHEMA)

        # Insert data.
        insert_mps(conn, projects)
        insert_projects(conn, projects)
        insert_risk_results(conn, risk_results)
        insert_duplicate_alerts(conn, duplicate_alerts)

        conn.commit()

        # Verify everything.
        verify_database(conn)

    except Exception:

        conn.rollback()

        print("\n[ERROR] Database build failed.")
        raise

    finally:
        conn.close()

    print("\n" + "=" * 60)
    print("DATABASE BUILD COMPLETE")
    print("=" * 60)

    print(f"\nDatabase created at:")

    print(
        DATABASE_FILE.relative_to(ROOT)
    )

    print("\nYou are ready for the backend. 🚀")


if __name__ == "__main__":
    main()