#!/bin/bash

# Start backend (Docker) and frontend (Streamlit) for streamlit-video-snap

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Get local IP address for LAN access
LOCAL_IP=$(hostname -I 2>/dev/null | awk '{print $1}' || ipconfig 2>/dev/null | grep -oP 'IPv4.*: \K[\d.]+' | head -1)
export API_URL="http://${LOCAL_IP}:8080"

echo "Starting backend (Docker)..."
docker-compose -f ytdlp-server/docker-compose.yml up -d

echo "Starting frontend (Streamlit)..."
echo "API URL: $API_URL"
echo "Access from other devices: http://${LOCAL_IP}:8501"

if [ -d ".venv/Scripts" ]; then
    # Windows
    .venv/Scripts/python.exe -m streamlit run app.py
elif [ -d ".venv/bin" ]; then
    # Linux/Mac
    .venv/bin/python -m streamlit run app.py
else
    python -m streamlit run app.py
fi
