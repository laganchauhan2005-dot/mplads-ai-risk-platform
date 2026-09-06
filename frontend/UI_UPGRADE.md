
# UI V3 upgrade

This version keeps the existing FastAPI contract and data flow unchanged.

Changes:
- Professional dark intelligence-dashboard visual language
- Cleaner sidebar with visible HOME / INTELLIGENCE navigation
- No emoji page icons
- Consistent hero headers
- Stronger section hierarchy
- Cleaner metric cards
- Improved table and control styling
- More concise investigation-focused copy
- Charts keep their existing backend data sources
- Risk language remains "investigation priority", not a fraud verdict

Run from repository root:

Terminal 1:
`venv\Scripts\python.exe -m uvicorn backend.app.main:app --reload --port 8000`

Terminal 2:
`venv\Scripts\python.exe -m streamlit run frontend\Home.py`
