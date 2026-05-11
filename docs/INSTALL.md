# VIA 설치 가이드

이 문서는 VIA (Vision Intelligence Agent)를 처음 설치하고 실행하는 방법을 단계별로 설명합니다.

---

## 목차

- [사전 요구 사항](#사전-요구-사항)
- [설치 단계](#설치-단계)
- [개발 모드로 실행](#개발-모드로-실행)
- [패키징된 앱 실행](#패키징된-앱-실행)
- [설치 확인](#설치-확인)
- [환경 변수 설정](#환경-변수-설정)

---

## 사전 요구 사항

| 소프트웨어 | 버전 | 용도 |
|-----------|------|------|
| macOS | Intel Mac (x86_64) 또는 Apple Silicon | 운영체제 |
| pyenv | 최신 | Python 버전 관리 |
| Python | 3.11.15 | 백엔드 런타임 |
| Node.js | 18 이상 | 프론트엔드 빌드 |
| npm | 9 이상 | 패키지 관리 |
| Ollama | 최신 | 로컬 AI 엔진 |
| gemma4:e4b | — | 멀티모달 AI 모델 (~3.3GB) |

> **Apple Silicon (M1/M2/M3) 사용자**: 기본 동작은 동일합니다. 단, Ollama가 ARM 최적화 버전을 사용하므로 추론 속도가 더 빠릅니다.

---

## 설치 단계

### 1. Homebrew 설치 (미설치 시)

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

### 2. pyenv 설치 및 Python 3.11 설정

```bash
# pyenv 설치
brew install pyenv

# 쉘 프로파일 설정 (~/.zshrc)
echo 'export PYENV_ROOT="$HOME/.pyenv"' >> ~/.zshrc
echo 'export PATH="$PYENV_ROOT/bin:$PATH"' >> ~/.zshrc
echo 'eval "$(pyenv init -)"' >> ~/.zshrc
source ~/.zshrc

# Python 3.11.15 설치 (약 2-3분 소요)
pyenv install 3.11.15
```

### 3. Node.js 설치

```bash
# Homebrew로 설치 (권장)
brew install node

# 버전 확인
node --version  # v18.x.x 이상
npm --version   # 9.x.x 이상
```

### 4. Ollama 설치

```bash
# Homebrew로 설치
brew install ollama

# 또는 공식 설치 스크립트
curl -fsSL https://ollama.com/install.sh | sh
```

### 5. 저장소 클론

```bash
git clone <repository-url>
cd VIA
```

### 6. Python 가상환경 생성

```bash
# 프로젝트 디렉토리에서 Python 3.11.15 지정
pyenv local 3.11.15

# 가상환경 생성
python -m venv .venv

# 가상환경 활성화
source .venv/bin/activate

# pip 업그레이드
pip install --upgrade pip

# Python 버전 확인
python --version  # Python 3.11.15
```

### 7. Python 의존성 설치

```bash
pip install -r requirements.txt
```

주요 설치 패키지:
- `fastapi` — API 서버
- `uvicorn` — ASGI 서버
- `opencv-python-headless==4.13.0.92` — 컴퓨터 비전
- `numpy==2.4.4` — 수치 연산
- `httpx==0.28.1` — Ollama HTTP 클라이언트
- `structlog` — 구조화 로깅
- `pydantic` / `pydantic-settings` — 데이터 검증
- `anyio` — 비동기 지원
- `pytest` — 테스트 프레임워크

### 8. 프론트엔드 의존성 설치

```bash
cd frontend
npm install
cd ..
```

> `npm install` 실행 시 deprecated 경고가 출력될 수 있습니다. electron-builder의 간접 의존성으로 인한 것이며 동작에 영향 없습니다.

### 9. Gemma4:e4b 모델 Pull

```bash
# Ollama 서버 시작
ollama serve &

# Gemma4:e4b 모델 Pull (약 3.3GB, 최초 1회만 필요)
ollama pull gemma4:e4b

# 모델 확인
ollama list
# 출력에 gemma4:e4b 가 있어야 합니다
```

> **중요**: 모델명은 반드시 `gemma4:e4b`입니다. `gemma3:4b`가 아닙니다.

### 10. 환경 변수 파일 생성

```bash
cp .env.example .env
```

기본값으로 로컬 개발 환경이 설정되어 있습니다. 필요 시 `.env` 파일을 편집하세요.

---

## 개발 모드로 실행

개발 모드에서는 백엔드와 프론트엔드를 별도 터미널에서 실행합니다.

### 터미널 1: 백엔드 서버

```bash
# 가상환경 활성화
source .venv/bin/activate

# FastAPI 서버 시작 (핫 리로드 포함)
uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```

서버 시작 로그:
```
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
INFO:     Started reloader process
```

### 터미널 2: Electron 앱

```bash
cd frontend

# Vite dev server + Electron 동시 실행
npm run dev
```

> 개발 모드에서는 Vite가 React 코드를 핫 리로드합니다. Electron 창은 자동으로 뜹니다.

### Ollama 확인

```bash
# Ollama가 실행 중인지 확인
ollama list

# 실행 중이지 않으면
ollama serve &
```

---

## 패키징된 앱 실행

패키징된 앱은 Electron이 백엔드를 자동으로 시작합니다. 별도 터미널 없이 앱만 실행하면 됩니다.

### macOS DMG 빌드 및 설치

```bash
cd frontend

# macOS DMG 빌드 (Intel Mac 타겟)
npm run build
npx electron-builder --mac --x64 --dir  # 디렉토리 빌드 (빠름, 설치 불필요)

# 또는 DMG 생성
npx electron-builder --mac --x64
```

빌드 출력:
- `release/mac/VIA.app` — 앱 번들
- `release/VIA-*.dmg` — 설치 이미지

```bash
# 앱 실행 (빌드 후)
open release/mac/VIA.app
```

### Windows NSIS 빌드

Windows에서 실행 (또는 Wine 환경):

```bash
cd frontend
npx electron-builder --win --x64
```

빌드 출력:
- `release/VIA-Setup-*.exe` — NSIS 설치 파일

### 패키징된 앱 동작 방식

앱 시작 시 자동으로:
1. FastAPI 백엔드 서버 실행 (포트 8000)
2. Ollama 상태 확인
3. gemma4:e4b 모델 가용 여부 확인
4. 미설치 시 설치 안내 다이얼로그 표시

포트 8000이 이미 사용 중이면 기존 서버를 그대로 사용합니다 (재시작 없음).

---

## 설치 확인

모든 설치가 완료되면 다음 명령으로 동작을 확인하세요.

### 백엔드 헬스 체크

```bash
curl http://localhost:8000/api/health
```

예상 응답:
```json
{"status": "ok", "engine_mode": "local", "ollama_url": "http://localhost:11434"}
```

### 백엔드 테스트 실행

```bash
source .venv/bin/activate

# 비통합 테스트 전체 (Ollama 불필요)
python -m pytest tests/ -m "not integration and not e2e" -q

# 예상 출력
# 1755 passed in X.XXs
```

### 프론트엔드 테스트 실행

```bash
cd frontend
npx vitest run --reporter=dot

# 예상 출력
# 394 tests passed
```

### Ollama 연결 확인 (선택)

```bash
curl http://localhost:11434/api/tags
# gemma4:e4b 가 models 목록에 있어야 합니다
```

---

## 환경 변수 설정

`.env` 파일로 동작을 커스터마이즈할 수 있습니다.

```bash
cp .env.example .env
```

주요 변수:

| 변수 | 기본값 | 설명 |
|------|--------|------|
| `VIA_HOST` | `0.0.0.0` | 백엔드 바인딩 주소 |
| `VIA_PORT` | `8000` | 백엔드 포트 |
| `VIA_DEBUG` | `false` | 디버그 모드 (uvicorn 리로드) |
| `VIA_UPLOAD_DIR` | `uploads` | 이미지 업로드 디렉토리 |
| `VIA_LOG_LEVEL` | `INFO` | 로그 레벨 |
| `VIA_ENGINE_MODE` | `local` | AI 엔진 모드 (`local` / `colab`) |
| `VIA_COLAB_URL` | _(없음)_ | Colab 터널 URL |
| `VIA_OLLAMA_URL` | `http://localhost:11434` | Ollama 서버 URL (E2E 테스트용) |

> Colab 연결 방법은 [docs/COLAB_GUIDE.md](COLAB_GUIDE.md)를 참고하세요.
