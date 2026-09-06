"""Legacy seed entrypoint.

The project now uses the ML team's final SQLite database directly. Do not run the
old CSV seeding workflow against the final schema. Replace/update backend/mplads_dev.db
with the approved final database instead.
"""

raise SystemExit(
    "This repository uses the final ML database. Do not run backend/import_data.py; "
    "place the approved mplads_dev.db in backend/ instead."
)
