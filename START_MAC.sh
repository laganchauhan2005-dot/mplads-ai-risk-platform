#!/bin/bash
cd "$(dirname "$0")"
if [ ! -x venv/bin/python ]; then python3 -m venv venv; fi
"$PWD/venv/bin/python" -m pip install -r backend/requirements.txt
"$PWD/venv/bin/python" -m pip install -r frontend/requirements.txt
osascript -e 'tell application "Terminal" to do script "cd '"'"'"$PWD"'"'"'; source venv/bin/activate; python -m uvicorn backend.app.main:app --reload --port 8000"'
osascript -e 'tell application "Terminal" to do script "cd '"'"'"$PWD"'"'"'; source venv/bin/activate; python -m streamlit run frontend/Home.py"'
