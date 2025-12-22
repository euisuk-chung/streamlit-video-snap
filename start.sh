#!/bin/bash

# Start backend (Docker) and frontend (Streamlit) for streamlit-video-snap

echo "Starting backend (Docker)..."
docker-compose up -d

echo "Starting frontend (Streamlit)..."
if [ -d ".venv" ]; then
    .venv/bin/python -m streamlit run app.py
else
    python -m streamlit run app.py
fi
