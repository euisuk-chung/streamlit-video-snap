# Changelog

All notable changes to the **Streamlit Video Snap** project will be documented in this file.

---

## [0.5.0] - 2026-02-16

### Fixed
- **Transcript 429 에러 해결**: YouTube 자막 요청 시 `urllib`로 직접 다운로드하던 방식을 `youtube-transcript-api` 라이브러리로 교체하여 YouTube rate limit(429 Too Many Requests) 문제 해결
- **Docker healthcheck 실패 수정**: `python:3.11-slim` 이미지에 `curl`이 없어서 healthcheck가 1,844회 연속 실패하던 문제를 Python `urllib`로 대체하여 해결
- **Docker config.yaml 마운트 오류 수정**: Docker Desktop Windows에서 파일 bind mount가 디렉토리로 인식되는 버그를 Dockerfile `COPY`로 우회

### Changed
- `docker-compose.yml`에서 deprecated된 `version` 속성 제거
- config.yaml을 볼륨 마운트 대신 Docker 이미지에 포함

---

## [0.4.0] - 2026-02-16

### Added
- **Windows 자동 시작 지원**: PC 부팅 시 Streamlit 프론트엔드 자동 실행
  - `start-streamlit.bat`: Windows 부팅 시 Streamlit 서버 자동 시작
  - `create-shortcut.ps1`: 시작 프로그램 폴더에 바로가기 생성 스크립트

### Changed
- `app.py`에서 API URL을 하드코딩 대신 환경변수(`API_URL`)로 변경하여 LAN 접속 지원
- `start.sh`에 LAN IP 자동 감지 및 Windows 호환성 추가

---

## [0.3.0] - 2026-01-15

### Added
- **LLM AI 요약 기능**: YouTube 영상의 자막/오디오를 AI로 요약
  - 3가지 요약 모드: Transcript / Audio (Whisper) / Audio (Multimodal)
  - 3개 LLM 프로바이더 지원: OpenAI (GPT-4o), Anthropic (Claude), Google (Gemini)
  - 한국어/영어 요약 출력 언어 선택
  - 요약 진행률 실시간 추적 (`/api/summarize/progress`)
- `config.yaml`: LLM 프로바이더 설정 및 요약 프롬프트 관리
- `llm_service.py`: LLM 프로바이더 추상화 서비스 레이어
- `.env.sample`: API 키 설정 예시 파일

---

## [0.2.0] - 2025-12-22

### Added
- **오디오 스트리밍 및 다운로드**: YouTube 영상의 오디오 재생 및 다운로드 기능
  - 오디오 다운로드 진행률 실시간 추적
  - 오디오 플레이어 UI 개선

### Changed
- Backend API에 오디오 관련 엔드포인트 추가 (`/api/audio/stream`, `/api/audio/download`)
- Dockerfile에 `ffmpeg` 의존성 추가 (오디오 변환용)

---

## [0.1.0] - 2025-12-16

### Added
- **Transcript(자막) 추출 기능**: YouTube 영상의 자막을 타임스탬프 포함하여 추출
  - 수동 자막 > 자동 자막 우선순위 지원
  - 한국어 > 영어 > 기타 언어 우선순위
  - `.txt` / `.srt` 형식 다운로드

---

## [0.0.1] - 2025-11-24

### Added
- **프로젝트 초기 구축**
  - Streamlit 기반 프론트엔드 (`app.py`)
  - yt-dlp 기반 백엔드 API 서버 (`ytdlp-server/`)
  - Docker Compose를 통한 백엔드 컨테이너화
  - YouTube 영상 정보 조회 (`/api/info`)
  - 영상 스냅샷(썸네일) 조회 기능
