@echo off
cd /d "%~dp0"
if not exist venv\Scripts\python.exe python -m venv venv
start "MPLADS Backend" cmd /k "venv\Scripts\python.exe -m pip install -r backend\requirements.txt && venv\Scripts\python.exe -m uvicorn backend.app.main:app --reload --port 8000"
start "MPLADS Frontend" cmd /k "venv\Scripts\python.exe -m pip install -r frontend\requirements.txt && venv\Scripts\python.exe -m streamlit run frontend\Home.py"
