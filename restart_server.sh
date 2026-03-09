#!/bin/bash
lsof -ti:5000 | xargs kill -9 2>/dev/null
source venv/bin/activate
python app.py &
