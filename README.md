# VIA (Vision Intelligence Agent)

이미지와 사용자 의도를 분석하여 비전 검사 알고리즘을 자동으로 설계하는 **멀티에이전트 AI 데스크톱 앱**.  
Intel Mac에서 Ollama + Gemma4:e4b 멀티모달 AI로 완전 오프라인 실행. Google Colab GPU 원격 연결도 지원.

> **현황**: 전체 53 Steps / 8 Phases 완료 (Phase 1~8) · 백엔드 비통합 테스트 1755개 GREEN · 프론트엔드 394개 GREEN

---

## 목차

- [주요 기능](#주요-기능)
- [아키텍처 개요](#아키텍처-개요)
- [기술 스택](#기술-스택)
- [Getting Started (빠른 시작)](#getting-started-빠른-시작)
- [개발 워크플로우](#개발-워크플로우)
- [프로젝트 구조](#프로젝트-구조)
- [테스트](#테스트)
- [UI 미리보기](#ui-미리보기)
- [문제 해결](#문제-해결)
- [라이선스](#라이선스)

---

## 주요 기능

| 기능 | 설명 |
|------|------|
| **Inspection Mode** | OK/NG 이미지 이진 분류 알고리즘 자동 설계 |
| **Align Mode** | X/Y 좌표 산출 알고리즘 자동 설계 |
| **Agent Directive** | 에이전트별 방향성 지시 입력 (상세 제어) |
| **Vision Judge** | Gemma4:e4b가 처리 이미지를 직접 보고 목적 기준으로 판단 |
| **Decision Agent** | Rule-based 유지 / Edge Learning / Deep Learning 자동 추천 |
| **Local / Colab 전환** | Ollama 로컬 실행 또는 Google Colab GPU 원격 실행 |
| **결과 내보내기** | OpenCV 코드 + 한국어 설명 + 성능 메트릭 JSON 내보내기 |

---

## 아키텍처 개요

```
[Electron + React + Redux UI]
          ↓
  [FastAPI Server :8000]
          ↓
  [Orchestrator Agent]
          ↓
┌─────────────────────────────────────────────┐
│  Spec Agent              ← Directive        │
│  Image Analysis Agent    ← Directive        │
│  Pipeline Composer       ← Directive        │
│  Vision Judge Agent      ← Directive (멀티모달) │
│  Inspection Plan Agent   ← Directive        │
│  Algorithm Coder Agent   ← Directive        │
│  Test Agent              ← Directive        │
│  Evaluation Agent                           │
│  Feedback Controller                        │
│  Decision Agent                             │
└─────────────────────────────────────────────┘
          ↓
  [OllamaClient (base_url 동적 전환)]
   ┌───────┴────────┐
[Local Mode]   [Colab Mode]
localhost:11434  cloudflared 터널 URL
gemma4:e4b       gemma4:e4b 또는 gemma4:27b
```

### 실행 파이프라인

```
사용자 입력 (목적 텍스트 + 이미지 + Agent Directives)
  ↓
[목표 수치 사전 검증]
  ↓
Spec Agent → Image Analysis Agent → Pipeline Composer
  ↓
FOR 각 후보 파이프라인:
  Parameter Searcher → ProcessingQualityEvaluator → Vision Judge Agent
  ↓
최고 점수 파이프라인 확정
  ↓
Inspection Plan Agent → Algorithm Selector → Algorithm Coder Agent
  ↓
[코드 정적 검증 (ast.parse)]
  ↓
Test Agent → Evaluation Agent
  ↓
성공 → 결과 출력 (OpenCV 코드 + 메트릭 + 개선 제안)
실패 → Feedback Controller → Retry
  max_iteration 초과 → Decision Agent (Rule-based / EL / DL)
```

### 에이전트 목록 (15개)

| 에이전트 | 역할 | LLM 사용 |
|---------|------|---------|
| Orchestrator | 파이프라인 제어, Retry, 목표 수치 검증 | 보조 |
| Spec Agent | 사용자 텍스트 → 모드/목표/성공기준 추출 | ✓ |
| Image Analysis Agent | 이미지 특성 수치 + 처리 전략 진단 | ✗ (OpenCV) |
| Pipeline Composer | Block Library로 후보 파이프라인 조합 | ✗ (Rule-based) |
| Parameter Searcher | 파이프라인 파라미터 자동 탐색 | ✗ (OpenCV) |
| Vision Judge Agent | 처리 이미지 직접 보고 목적 기준 판단 | ✓ (멀티모달) |
| Inspection Plan Agent | 검사 항목/순서/의존성 자유 설계 | ✓ |
| Algorithm Selector | 이미지 진단 수치로 알고리즘 카테고리 확정 | ✗ (결정 트리) |
| Algorithm Coder (Inspection) | Inspection 알고리즘 OpenCV 코드 생성 | ✓ |
| Algorithm Coder (Align) | Align 알고리즘 OpenCV 코드 생성 | ✓ |
| Code Validator | 생성 코드 정적 검증 (ast.parse) | ✗ |
| Test Agent (Inspection) | 코드 실행 → 항목별 메트릭 계산 | ✗ (OpenCV) |
| Test Agent (Align) | 코드 실행 → 좌표 오차 계산 | ✗ (OpenCV) |
| Evaluation Agent | 항목별 실패 원인 분석 + 성공/실패 판정 | ✗ (Rule-based) |
| Feedback Controller | 실패 원인별 재시도 전략 결정 | ✗ (Rule-based) |
| Decision Agent | 최종 판단: Rule-based / EL / DL | ✓ |

---

## 기술 스택

| 레이어 | 기술 | 버전 |
|-------|------|------|
| 백엔드 | Python + FastAPI + Uvicorn | Python 3.11.15, FastAPI latest |
| 비전 | OpenCV + NumPy | 4.13.0.92 / 2.4.4 |
| HTTP 클라이언트 | httpx | 0.28.1 |
| 로깅 | structlog | latest |
| 프론트엔드 | Electron + React + TypeScript | Electron 35, React 18 |
| UI 스타일 | TailwindCSS | 3.4.19 |
| 상태 관리 | Redux Toolkit | latest |
| 빌드 | Vite | 8.0.10 |
| AI 엔진 | Ollama + Gemma4:e4b | 로컬 또는 Colab |
| 백엔드 테스트 | pytest + anyio | 1755+ 비통합 테스트 |
| 프론트엔드 테스트 | vitest + React Testing Library | 394+ 테스트 |

---

## Getting Started (빠른 시작)

### 사전 요구 사항

- **macOS** (Intel Mac x86_64 검증 완료)
- **pyenv** + **Python 3.11.15**
- **Node.js 18+** + npm
- **Ollama** 설치 및 실행 중
- **gemma4:e4b** 모델 Pull 완료

### 1단계: 저장소 클론

```bash
git clone <repository-url>
cd VIA
```

### 2단계: Python 환경 설정

```bash
# Python 3.11.15 설치 (pyenv 사용)
pyenv install 3.11.15
pyenv local 3.11.15

# 가상환경 생성 및 활성화
python -m venv .venv
source .venv/bin/activate

# 의존성 설치
pip install -r requirements.txt
```

### 3단계: 프론트엔드 의존성 설치

```bash
cd frontend
npm install
cd ..
```

> `npm install` 실행 시 electron-builder 관련 deprecated 경고가 출력될 수 있습니다. 동작에 영향 없습니다.

### 4단계: Ollama + Gemma4:e4b 설정

```bash
# Ollama 시작 및 모델 Pull
./scripts/start_ollama.sh
```

또는 수동으로:

```bash
# Ollama 서버 시작 (백그라운드)
ollama serve &

# Gemma4:e4b 모델 Pull (약 3.3GB, 최초 1회)
ollama pull gemma4:e4b
```

> **중요**: 모델명은 `gemma4:e4b`입니다. `gemma3:4b`가 아닙니다.

### 5단계: 환경 변수 설정

```bash
cp .env.example .env
# 필요 시 .env 편집
```

### 6단계: 앱 실행

**개발 모드 (백엔드 + 프론트엔드 동시 실행):**

```bash
# 터미널 1: 백엔드 서버 시작
source .venv/bin/activate
uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload

# 터미널 2: Electron 앱 시작
cd frontend
npm run dev
```

**Electron 앱 단독 실행 (백엔드 자동 시작 모드):**

```bash
cd frontend
npm start
```

> Electron 앱은 시작 시 백엔드 서버를 자동으로 실행합니다. 이미 포트 8000이 사용 중이면 기존 서버를 그대로 사용합니다.

### 설치 확인

```bash
# 백엔드 헬스 체크
curl http://localhost:8000/api/health

# 응답 예시
# {"status": "ok", "engine_mode": "local", "ollama_url": "http://localhost:11434"}
```

---

## 개발 워크플로우

VIA는 **TDD + PCRO** 방식으로 개발되었습니다.

### TDD (Test-Driven Development)

모든 기능은 테스트 먼저 작성 → Red → Green → Refactor 순서로 개발합니다.

```bash
# 새 기능 개발 시
# 1. 테스트 먼저 작성 (tests/ 또는 frontend/src/__tests__/)
# 2. 실패 확인 (Red)
# 3. 구현 (Green)
# 4. 리팩터링
```

### PCRO (Plan-Code-Review-Output)

복잡한 기능은 PLAN.md에 스펙 작성 후 Claude Code로 구현합니다.

### 3-Gate 검증 (커밋 전 Taeyang 직접 수행)

1. `python -m pytest tests/ -m "not integration and not e2e" -q` → 전체 GREEN
2. `cd frontend && npx vitest run --reporter=dot` → 전체 GREEN
3. 앱 실행 후 골든 패스 UI 수동 확인

---

## 프로젝트 구조

```
VIA/
├── backend/                  # FastAPI 서버
│   ├── main.py               # 앱 진입점
│   ├── config.py             # 설정 (환경 변수)
│   ├── routers/              # API 라우터
│   │   ├── images.py         # 이미지 업로드 API
│   │   ├── pipeline.py       # 파이프라인 실행 API
│   │   ├── engine_config.py  # AI 엔진 설정 API
│   │   └── export.py         # 결과 내보내기 API
│   ├── services/             # 비즈니스 로직
│   │   ├── image_store.py    # 이미지 저장소
│   │   ├── ollama_client.py  # Ollama HTTP 클라이언트
│   │   └── logging.py        # structlog 설정
│   └── models/               # Pydantic 데이터 모델
├── agents/                   # 멀티에이전트 시스템 (15개)
│   ├── base_agent.py         # 에이전트 기본 인터페이스
│   ├── models.py             # 공유 데이터 모델
│   ├── orchestrator.py       # 파이프라인 오케스트레이터
│   ├── spec_agent.py
│   ├── image_analysis_agent.py
│   ├── pipeline_blocks.py    # Block Library
│   ├── pipeline_composer.py
│   ├── parameter_searcher.py
│   ├── processing_quality_evaluator.py
│   ├── vision_judge_agent.py
│   ├── inspection_plan_agent.py
│   ├── algorithm_selector.py
│   ├── algorithm_coder_inspection.py
│   ├── algorithm_coder_align.py
│   ├── code_validator.py
│   ├── test_agent_inspection.py
│   ├── test_agent_align.py
│   ├── evaluation_agent.py
│   ├── feedback_controller.py
│   ├── decision_agent.py
│   └── prompts/              # LLM 프롬프트 템플릿
├── frontend/                 # Electron + React UI
│   ├── main.js               # Electron main process
│   ├── preload.js            # IPC bridge
│   ├── src/
│   │   ├── App.tsx           # 루트 컴포넌트
│   │   ├── components/       # UI 컴포넌트
│   │   │   └── panels/       # InputPanel, DirectivePanel, ConfigPanel, ExecutionPanel, ResultPanel, LogPanel
│   │   ├── store/            # Redux slices
│   │   └── services/         # API 클라이언트
│   ├── electron-builder.yml  # 패키징 설정
│   └── package.json
├── tests/                    # 테스트 스위트
│   ├── e2e/                  # E2E 통합 테스트 (Gemma4 필요)
│   └── fixtures/             # 테스트 이미지 (OK/NG + Align)
├── scripts/
│   └── start_ollama.sh       # Ollama 시작 스크립트
├── docs/
│   ├── INSTALL.md            # 상세 설치 가이드
│   └── COLAB_GUIDE.md        # Colab 연결 가이드
├── release/                  # 패키징 출력물 (DMG 등)
├── requirements.txt
├── pyproject.toml
├── .env.example
├── PLAN.md                   # 마스터 개발 계획 (53 Steps)
└── PROGRESS.md               # 진행 현황 + 완료 기록
```

---

## 테스트

### 백엔드 테스트 (pytest)

```bash
source .venv/bin/activate

# 비통합 테스트 전체 실행 (Ollama 불필요, 1755개)
python -m pytest tests/ -m "not integration and not e2e" -q

# 특정 모듈 테스트
python -m pytest tests/test_orchestrator.py -v

# 커버리지 포함
python -m pytest tests/ -m "not integration and not e2e" --cov=agents --cov=backend
```

### 프론트엔드 테스트 (vitest)

```bash
cd frontend

# 전체 실행 (394개)
npx vitest run --reporter=dot

# 워치 모드
npx vitest
```

### E2E 통합 테스트 (Gemma4 필요)

E2E 테스트는 실제 Gemma4 모델이 필요합니다. Colab URL 환경에서 실행하세요.

```bash
# Colab 연결 후
VIA_OLLAMA_URL=<Colab_터널_URL> python -m pytest tests/e2e/test_final_integration.py -m "integration and e2e" -v
```

> Scenario 1/2에서 `test_results=[]`가 반환될 수 있습니다. Gemma4 코드 생성 품질의 비결정성으로 인한 정상 동작입니다.

---

## UI 미리보기

> 스크린샷은 추후 추가 예정입니다.

**주요 패널 구성:**

- **Input Panel**: 목적 텍스트 입력 + 이미지 업로드
- **Directive Panel**: 8개 에이전트별 방향성 지시 (아코디언)
- **Config Panel**: 모드 선택 (Inspection/Align), 반복 횟수 설정
- **Engine Panel**: Local/Colab 전환, Colab 터널 URL 입력
- **Execution Panel**: 파이프라인 실행 버튼 + 진행 상태
- **Result Panel**: 생성 코드 + 메트릭 차트 + 파이프라인 시각화
- **Log Panel**: 실시간 에이전트 실행 로그

---

## 문제 해결

### Intel Mac에서 첫 번째 멀티모달 호출 타임아웃

**증상**: Vision Judge Agent 호출 시 타임아웃 오류 발생  
**원인**: Intel Mac에서 Gemma4:e4b 모델 첫 로딩 시 약 2분 30초 이상 소요  
**해결**: 코드에 `GENERATE_TIMEOUT=600.0` (600초)로 설정되어 있습니다. 첫 번째 멀티모달 요청은 오래 기다리는 것이 정상입니다.

---

### 모델 이름 오류: `gemma3:4b` vs `gemma4:e4b`

**증상**: `model "gemma3:4b" not found` 오류  
**원인**: 모델명 혼동  
**해결**: 반드시 `gemma4:e4b`를 사용하세요. `ollama pull gemma4:e4b`로 Pull하세요.

```bash
# 설치된 모델 확인
ollama list
# gemma4:e4b 가 목록에 있어야 합니다
```

---

### Colab 터널 콜드 스타트 — 첫 번째 요청 실패

**증상**: Colab URL 연결 후 첫 번째 파이프라인 실행 시 실패  
**원인**: Colab에서 Ollama + Gemma4 모델 최초 로딩 지연 (30~90초)  
**해결**: 연결 직후 반드시 **워밍업 요청**을 먼저 보내세요.

자세한 내용은 [docs/COLAB_GUIDE.md](docs/COLAB_GUIDE.md) 참고.

---

### `npm install` 실행 시 deprecated 경고

**증상**: `npm warn deprecated` 메시지 다수 출력  
**원인**: electron-builder의 간접 의존성 일부가 최신 npm 기준에서 deprecated  
**해결**: 무시해도 됩니다. 앱 동작에 영향 없습니다.

---

### 포트 8000 이미 사용 중

**증상**: `uvicorn` 시작 시 `address already in use` 오류  
**원인**: 이미 백엔드 서버가 실행 중  
**해결**: Electron 앱 개발 모드에서는 기존 서버를 그대로 사용합니다. 별도로 uvicorn을 시작할 필요 없습니다. 수동으로 종료하려면:

```bash
lsof -ti:8000 | xargs kill -9
```

---

### Python venv 없음 / Python 버전 오류

**증상**: `python: command not found` 또는 `Python 3.x.x is not available`  
**원인**: pyenv 미설치 또는 Python 3.11이 없음  
**해결**:

```bash
# Homebrew로 pyenv 설치
brew install pyenv

# 쉘 프로파일에 추가 (~/.zshrc 또는 ~/.bash_profile)
echo 'export PYENV_ROOT="$HOME/.pyenv"' >> ~/.zshrc
echo 'export PATH="$PYENV_ROOT/bin:$PATH"' >> ~/.zshrc
echo 'eval "$(pyenv init -)"' >> ~/.zshrc
source ~/.zshrc

# Python 3.11.15 설치
pyenv install 3.11.15
```

자세한 내용은 [docs/INSTALL.md](docs/INSTALL.md) 참고.

---

## 라이선스

Copyright © 2026 TaeyangYeon. All rights reserved.
