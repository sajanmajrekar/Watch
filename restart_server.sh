#!/bin/bash
lsof -ti:5001 | xargs kill -9 2>/dev/null
source venv/bin/activate
python app.py &
