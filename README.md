# YouTube Tools

A local Streamlit application that provides YouTube video tools: thumbnail downloader and audio extractor.

## Features

- 📸 **Thumbnail Downloader**
  - Download high-quality thumbnails (up to 1920x1080)
  - Multiple quality options (Max, High, Medium, Standard)
  - Direct download links for each quality

- 🎵 **Audio Extractor**
  - Extract audio from YouTube videos
  - Play audio directly in the browser
  - Display video metadata (title, duration, views, etc.)
  - Download audio files

- 🐳 **Docker-based Backend**
  - yt-dlp API server running in Docker
  - Easy setup and deployment

- 💻 **Simple Streamlit UI**
  - Clean tabbed interface
  - Real-time API status check

## Architecture

- **Frontend**: Streamlit web application
- **Backend**: Flask API server running yt-dlp in Docker
- **Audio Extraction**: yt-dlp with ffmpeg

## Setup

### Prerequisites

- Python 3.8+
- [uv](https://docs.astral.sh/uv/) (recommended) or pip
- Docker and Docker Compose
- Git

### Installation

1. Clone the repository:
```bash
git clone <your-repo-url>
cd streamlit-video-snap
```

2. Install Python dependencies:

**Using uv (recommended):**
```bash
uv sync
```

**Using pip:**
```bash
pip install -r requirements.txt
```

3. Start the yt-dlp Docker server:
```bash
cd ytdlp-server
docker-compose up -d
cd ..
```

4. Verify the API server is running:
```bash
curl http://localhost:8080/health
```

You should see: `{"service":"yt-dlp-api","status":"ok"}`

### Running the Application

**Using uv (recommended):**
```bash
uv run streamlit run app.py
```

**Using pip:**
```bash
streamlit run app.py
```

Then open your browser to: `http://localhost:8501`

## Usage

### Thumbnail Downloader

1. Switch to the "📸 Thumbnail Downloader" tab
2. Enter a YouTube video URL
3. Click "Get Thumbnail"
4. View thumbnails in multiple qualities
5. Click download links to save thumbnails

### Audio Extractor

1. Switch to the "🎵 Audio Extractor" tab
2. Enter a YouTube video URL
3. Click "Extract Audio"
4. View video information and metadata
5. Play the audio directly in your browser
6. Download the audio file if needed

## API Endpoints

The yt-dlp server provides the following endpoints:

- `GET /health` - Health check
- `POST /api/info` - Get video metadata
- `POST /api/audio` - Extract audio information and URL

## Auto-Start on Windows Boot

PC 부팅 시 자동으로 서버들이 실행되도록 설정할 수 있습니다.

### 현재 상태

| 서버 | 자동 실행 | 설명 |
|------|-----------|------|
| Backend (Docker) | O | `restart: unless-stopped` 설정됨 |
| Frontend (Streamlit) | O | Windows 시작 프로그램에 등록됨 |

### 자동 실행 구조

- **Backend**: Docker Desktop이 부팅 시 자동 시작되면, `unless-stopped` 정책으로 컨테이너도 자동 시작
- **Frontend**: `start-streamlit.bat` 파일이 Windows 시작 프로그램에 등록되어 자동 실행

### 자동 실행 관리

#### 시작 프로그램 등록 (최초 설정 시)
```powershell
powershell -ExecutionPolicy Bypass -File create-shortcut.ps1
```

#### 시작 프로그램 해제
Windows 시작 프로그램 폴더에서 바로가기 삭제:
```powershell
Remove-Item "$env:APPDATA\Microsoft\Windows\Start Menu\Programs\Startup\YouTube-Tools-Streamlit.lnk"
```

또는 `Win + R` → `shell:startup` → `YouTube-Tools-Streamlit.lnk` 삭제

#### 시작 프로그램 폴더 열기
```
Win + R → shell:startup
```

### 관련 파일

| 파일 | 설명 |
|------|------|
| `start-streamlit.bat` | Streamlit 실행 배치 파일 |
| `create-shortcut.ps1` | 시작 프로그램 등록 스크립트 |

## Troubleshooting

### API Server Not Running

If the sidebar shows "API Server is not running":

```bash
cd ytdlp-server
docker-compose up -d
docker-compose logs
```

### Docker Container Issues

Check container status:
```bash
docker ps
docker logs ytdlp-server
```

Restart the container:
```bash
cd ytdlp-server
docker-compose restart
```

### Audio Playback Issues

Some audio formats may not play directly in the browser. Try downloading the audio file instead using the provided link.

## Development

### Project Structure

```
streamlit-video-snap/
├── app.py                  # Main Streamlit application
├── pyproject.toml         # Project configuration and dependencies (uv)
├── requirements.txt        # Python dependencies (pip)
├── .python-version        # Python version specification
├── README.md              # This file
└── ytdlp-server/          # Docker-based yt-dlp API
    ├── app.py             # Flask API server
    ├── Dockerfile         # Docker image definition
    └── docker-compose.yml # Docker compose configuration
```

### Stopping the Application

1. Stop Streamlit: Press `Ctrl+C` in the terminal

2. Stop Docker container:
```bash
cd ytdlp-server
docker-compose down
```

## License

MIT

## Notes

- This is a local-only application (not deployed to cloud)
- Audio extraction may take a few seconds depending on the video
- Some videos may be blocked due to geographic restrictions or copyright
- The extracted audio URL is temporary and expires after some time
