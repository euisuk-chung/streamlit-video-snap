@echo off
REM YouTube Tools - Streamlit Frontend Auto-Start Script
REM This script starts the Streamlit frontend server

cd /d "d:\Repo\streamlit-video-snap"

REM Get local IP address for LAN access
for /f "tokens=2 delims=:" %%a in ('ipconfig ^| findstr /c:"IPv4"') do (
    for /f "tokens=1" %%b in ("%%a") do set LOCAL_IP=%%b
)

REM Set API URL for LAN access (use local IP instead of localhost)
set API_URL=http://%LOCAL_IP%:8080

REM Start Streamlit in minimized window (accessible from other devices on LAN)
start /min "" cmd /c "uv run streamlit run app.py"
