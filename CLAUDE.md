# CLAUDE.md - Project Guidelines for Claude Code

## Project Overview

YouTube 영상 도구 모음 (Streamlit 프론트엔드 + Docker 백엔드 API).
썸네일 다운로드, 오디오 추출, 자막 추출, AI 요약 기능을 제공한다.

## Architecture

```
app.py (Streamlit Frontend, port 8501)
    ↓ HTTP requests
ytdlp-server/app.py (Flask API, Docker, port 8080)
    ├── yt-dlp: 영상 정보, 오디오 추출
    ├── youtube-transcript-api: 자막 추출
    ├── llm_service.py: AI 요약 (OpenAI / Anthropic / Google)
    └── config.yaml: LLM 설정 및 프롬프트
```

## Key Files

| 파일 | 역할 |
|------|------|
| `app.py` | Streamlit 메인 앱 (UI + API 호출) |
| `ytdlp-server/app.py` | Flask 백엔드 API 서버 |
| `ytdlp-server/llm_service.py` | LLM 프로바이더 추상화 서비스 |
| `ytdlp-server/Dockerfile` | 백엔드 Docker 이미지 정의 |
| `ytdlp-server/docker-compose.yml` | Docker Compose 설정 |
| `ytdlp-server/config.yaml` | LLM 설정 (Docker 이미지에 COPY됨) |
| `config.yaml` | LLM 설정 원본 (프로젝트 루트) |
| `start-streamlit.bat` | Windows 부팅 시 Streamlit 자동 시작 |
| `CHANGELOG.md` | 버전별 변경 이력 |

## Development Rules

### CHANGELOG 관리 (필수)
- **코드 변경 시 반드시 `CHANGELOG.md`를 업데이트**할 것
- 기존 형식(버전, 날짜, Added/Changed/Fixed 카테고리)을 따를 것
- 버전 번호는 semver 기반: 기능 추가 시 minor, 버그 수정 시 patch
- 최신 변경이 파일 상단에 위치

### Docker 관련
- 백엔드 변경 시 `docker compose up -d --build`로 재빌드 필요
- `config.yaml` 변경 시 `ytdlp-server/config.yaml`에도 복사 후 Docker 재빌드
- Docker Desktop Windows에서 파일 bind mount 버그가 있음 → 볼륨 마운트 대신 `COPY` 사용
- healthcheck는 `python urllib` 사용 (`curl` 미설치)
- 베이스 이미지: `python:3.11-slim` + `ffmpeg`

### API 서버
- 자막 추출: `youtube-transcript-api` 사용 (yt-dlp의 urllib 방식은 YouTube 429 에러 발생)
- 영상 정보/오디오: `yt-dlp` 사용
- AI 요약: `llm_service.py`의 프로바이더 패턴 (OpenAI, Anthropic, Google)
- API 키는 환경변수로 전달 (`OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `GOOGLE_API_KEY`)

### Frontend
- Streamlit 앱은 `uv run streamlit run app.py`로 실행
- API URL은 환경변수 `API_URL`로 설정 (기본값: `http://localhost:8080`)
- LAN 접속 시 호스트 PC의 IP:8501로 접근

### Commit Convention
- 커밋 메시지는 영어, 첫 줄은 imperative mood ("Fix ...", "Add ...")
- 본문에 변경 이유를 포함
- Co-Authored-By 태그 포함

## Auto-Start (Windows)

- **Docker 백엔드**: Docker Desktop 자동 시작 + `restart: unless-stopped`
- **Streamlit 프론트엔드**: `start-streamlit.bat` → Windows 시작 프로그램 폴더 바로가기

## Common Commands

```bash
# 백엔드 시작/재빌드
cd ytdlp-server && docker compose up -d --build

# 프론트엔드 시작
uv run streamlit run app.py

# 로그 확인
docker compose -f ytdlp-server/docker-compose.yml logs --tail=20

# 헬스체크
curl http://localhost:8080/health
```
