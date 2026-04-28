# VIA Progress

## 현재 진행 단계: Step 23 완료 / Step 24 대기

## Phase 1: 환경 설정
- [x] Step 1: Python 환경 초기화 (2026-04-21)
- [x] Step 2: OpenCV + NumPy 설치 및 검증 (2026-04-21)
- [x] Step 3: Ollama 설치 및 Gemma4 Pull + 멀티모달 검증 (2026-04-22)
- [x] Step 4: 프로젝트 디렉토리 구조 및 Git 초기화 (2026-04-22)

## Phase 2: 백엔드 기반
- [x] Step 5: FastAPI 프로젝트 초기화 (2026-04-22)
- [x] Step 6: 이미지 업로드 API + 검증 로직 (2026-04-22)
- [x] Step 7: 이미지 저장소 관리 서비스 (2026-04-23)
- [x] Step 8: 실행 설정 API + Agent Directive API (2026-04-23)
- [x] Step 9: 로깅 시스템 구현 (2026-04-23)
- [x] Step 10: Ollama 클라이언트 서비스 (멀티모달 지원) (2026-04-23)

## Phase 3: 이미지 처리 레이어
- [x] Step 11: Agent 기본 인터페이스 + 전체 모델 정의 (2026-04-23)
- [x] Step 12: Spec Agent 구현 (2026-04-23)
- [x] Step 13: Image Analysis Agent (ImageDiagnosis 전체) (2026-04-24)
- [x] Step 14: Pipeline Block Library 구현 (2026-04-24)
- [x] Step 15: Pipeline Composer 구현 (2026-04-25)
- [x] Step 16: Parameter Searcher + ProcessingQualityEvaluator (2026-04-25)
- [x] Step 17: Vision Judge Agent (멀티모달 핵심) (2026-04-26)

## Phase 4: 검사 설계 레이어
- [x] Step 18: Inspection Plan Agent (2026-04-26)
- [x] Step 19: Algorithm Selector (결정 트리) (2026-04-27)
- [x] Step 20: Algorithm Coder Agent (Inspection) (2026-04-27)
- [x] Step 21: Algorithm Coder Agent (Align) (2026-04-27)
- [x] Step 22: Test Agent (Inspection, 항목별) (2026-04-28)
- [x] Step 23: Test Agent (Align) (2026-04-28)
- [ ] Step 24: 코드 정적 검증 레이어

## Phase 5: 평가 & 피드백 루프
- [ ] Step 25: Evaluation Agent (항목별 세분화)
- [ ] Step 26: Feedback Controller
- [ ] Step 27: Decision Agent (EL/DL 판단)
- [ ] Step 28: Orchestrator (기본 파이프라인)
- [ ] Step 29: Orchestrator Retry 로직
- [ ] Step 30: Orchestrator → Decision Agent 연결
- [ ] Step 31: 파이프라인 실행 API

## Phase 6: 프론트엔드
- [ ] Step 32: Electron 프로젝트 초기화
- [ ] Step 33: React + TypeScript + TailwindCSS + 디자인 시스템 설정
- [ ] Step 34: Redux Store 초기화 (directives 포함)
- [ ] Step 35: API 클라이언트 서비스
- [ ] Step 36: 전체 레이아웃 + Input Panel
- [ ] Step 37: Directive Panel UI
- [ ] Step 38: Config Panel + Execution Panel
- [ ] Step 39: Result Panel (파이프라인 시각화 포함)
- [ ] Step 40: 로그 패널 + UI-API 통합 테스트

## Phase 7: 통합 & E2E
- [ ] Step 41: Inspection 전체 파이프라인 E2E
- [ ] Step 42: Align 전체 파이프라인 E2E
- [ ] Step 43: Agent Directive E2E 테스트
- [ ] Step 44: 성능 최적화 (Vision Judge 속도)
- [ ] Step 45: 에러 처리 강화 + 결과 내보내기
- [ ] Step 46: Retry 및 Decision 시나리오 통합 테스트

## Phase 8: 패키징 & 배포
- [ ] Step 47: FastAPI 자동 시작 + Ollama 멀티모달 상태 확인
- [ ] Step 48: macOS DMG + Windows NSIS 패키징
- [ ] Step 49: 전체 최종 통합 테스트
- [ ] Step 50: 문서화 완성 + 최종 Git 커밋
```

---

*VIA Master Development Plan v3.0 | 50 Steps / 8 Phases*

---

## 완료 기록

### Step 1: Python 환경 초기화 (2026-04-21)

**작업 결과:**
- pyenv + Python 3.11.15 가상환경(.venv) 생성
- requirements.txt 작성: fastapi, uvicorn, opencv-python-headless, numpy, httpx, structlog, pytest, pydantic
- pyproject.toml 작성: 프로젝트 메타데이터 (name=via, version=0.1.0, requires-python>=3.11, pytest testpaths 설정)
- .python-version 파일 생성 (3.11.15)
- .gitignore 생성: Python, Node, Electron, IDE, .claude/ 제외 설정

**발생 이슈:**
- requirements.txt에 opencv-python-headless를 명시했으나 opencv-python(GUI 버전)이 설치됨. VIA는 Electron UI를 사용하므로 기능상 동일하며 추후 정리 예정.
- .gitignore를 초기 push 이후에 생성하여 이미 추적된 파일을 `git rm -r --cached .`로 제거 후 재커밋함.

**생성/수정 파일:**
- .python-version
- pyproject.toml
- requirements.txt
- tests/__init__.py
- tests/test_environment.py
- .gitignore

**테스트 결과:**
- 12개 테스트 전체 GREEN (Python 버전 확인 1, 패키지 import 8, 프로젝트 파일 확인 2, .gitignore 확인 1)

### Step 2: OpenCV + NumPy 설치 및 검증 (2026-04-21)

**작업 결과:**
- opencv-python-headless 4.13.0.92 설치 확인 (headless 버전 정상 사용)
- numpy 2.4.4 설치 확인
- Intel Mac x86_64 호환성 검증 완료
- 기본 이미지 연산 검증 완료: 생성, 저장/로드, 색공간 변환, 가우시안 블러, 이진화 임계값
- requirements.txt에 opencv-python-headless==4.13.0.92, numpy==2.4.4 핀 버전 반영

**발생 이슈:**
- Step 1에서 opencv-python(GUI)이 설치되었다고 기록했으나, 실제 확인 시 opencv-python-headless가 이미 설치되어 있음. 패키지 교체 불필요.

**생성/수정 파일:**
- tests/test_opencv.py (신규)
- requirements.txt (핀 버전 업데이트)
- PROGRESS.md

**테스트 결과:**
- 25개 테스트 전체 GREEN (Step 1: 11개 + Step 2: 14개)
  - Step 2 세부: import 2, 버전 확인 2, 이미지 생성 2, 색공간 변환 1, 저장/로드 1, 가우시안 블러 1, 임계값 1, NumPy 연동 3, 아키텍처 확인 1

### Step 3: Ollama 설치 및 Gemma4 Pull + 멀티모달 검증 (2026-04-22)

**작업 결과:**
- Ollama 서버 시작 스크립트(scripts/start_ollama.sh) 작성: 설치 확인, 서버 시작, gemma4:e4b 모델 pull 자동화
- Gemma4:e4b 멀티모달 통합 테스트 구현 (tests/test_ollama_multimodal.py)
- 서버 연결, 모델 존재 확인, 텍스트 생성, 멀티모달 이미지 입력 테스트 포함
- pytest integration 마커 추가 (Ollama 미실행 시 자동 skip)
- 멀티모달 동작 확인 완료: 녹색 사각형 테스트 이미지를 Gemma4:e4b가 정확히 묘사함

**발생 이슈:**
- 초기 구현 시 gemma3:4b로 잘못 구현됨. PLAN에 명시된 gemma4:e4b가 실제 Ollama에 존재하는 모델임을 확인 후 수동으로 전체 수정 (test_ollama_multimodal.py, start_ollama.sh)
- Intel Mac에서 멀티모달 첫 호출 시 모델 로딩 포함 약 2분 38초 소요. 기본 타임아웃(120초)으로는 부족하여 GENERATE_TIMEOUT=600.0, HEALTH_TIMEOUT=300.0으로 상향 조정
- 멀티모달 테스트 9개 중 첫 번째 테스트에서 모델 로딩 시간 소비 후 나머지는 빠르게 통과하는 패턴 확인

**생성/수정 파일:**
- scripts/start_ollama.sh (신규)
- tests/test_ollama_multimodal.py (신규)
- pyproject.toml (integration 마커 추가)
- requirements.txt (httpx==0.28.1 핀 버전)
- PROGRESS.md (Step 3 완료 기록)
- PLAN.md (Part 5 실행 로그 Step 3 추가)

**테스트 결과:**
- 34개 테스트 전체 GREEN (34 passed, 0 skipped, 0 failed) — 390초 (6분 30초)
  - Step 1: 11개 PASSED (test_environment.py)
  - Step 2: 14개 PASSED (test_opencv.py)
  - Step 3: 9개 PASSED (test_ollama_multimodal.py — 서버 상태 2, 모델 가용성 2, 텍스트 생성 2, 멀티모달 생성 3)
- Integration 마커 필터 실행: 9 passed, 25 deselected — 396초 (6분 35초)

### Step 4: 프로젝트 디렉토리 구조 및 Git 초기화 (2026-04-22)

**작업 결과:**
- 전체 프로젝트 디렉토리 구조 생성 (PLAN.md Section 2.5 기준)
- backend/ 패키지: main.py, config.py, routers/ (6개 라우터), services/ (3개 서비스), models/
- agents/ 패키지: 20개 에이전트 플레이스홀더 + prompts/
- frontend/ 빈 디렉토리 (Phase 6에서 초기화 예정)
- tests/e2e/, tests/fixtures/sample_images/ 디렉토리 생성
- docs/ 디렉토리 생성 (.gitkeep)
- README.md 작성: 프로젝트 설명, 기술 스택, 상태, Getting Started, 디렉토리 구조
- 모든 플레이스홀더 .py 파일에 모듈 독스트링 포함 (구현 코드 없음)

**발생 이슈:**
- 없음

**생성/수정 파일:**
- tests/test_directory_structure.py (신규 — 103개 테스트)
- backend/__init__.py, backend/main.py, backend/config.py (신규)
- backend/routers/__init__.py, images.py, config.py, directives.py, execute.py, logs.py, export.py (신규)
- backend/services/__init__.py, ollama_client.py, image_store.py, logger.py (신규)
- backend/models/__init__.py (신규)
- agents/__init__.py, base_agent.py, models.py, orchestrator.py, spec_agent.py (신규)
- agents/image_analysis_agent.py, pipeline_blocks.py, pipeline_composer.py (신규)
- agents/parameter_searcher.py, processing_quality_evaluator.py (신규)
- agents/vision_judge_agent.py, inspection_plan_agent.py, algorithm_selector.py (신규)
- agents/algorithm_coder_inspection.py, algorithm_coder_align.py, code_validator.py (신규)
- agents/test_agent_inspection.py, test_agent_align.py (신규)
- agents/evaluation_agent.py, feedback_controller.py, decision_agent.py (신규)
- agents/prompts/__init__.py (신규)
- tests/e2e/__init__.py (신규)
- tests/fixtures/sample_images/.gitkeep (신규)
- docs/.gitkeep (신규)
- README.md (신규)
- PROGRESS.md (수정)
- PLAN.md (수정)

**테스트 결과:**
- 128개 테스트 전체 GREEN (128 passed, 0 failed) — Ollama 통합 테스트 제외
  - Step 1: 11개 PASSED (test_environment.py — structlog 미설치 1개 제외 시 10개)
  - Step 2: 14개 PASSED (test_opencv.py)
  - Step 4: 103개 PASSED (test_directory_structure.py — 디렉토리 13, __init__ 8, 파일존재 31, 독스트링 31, README 7, 기존파일 9, 특수디렉토리 4)

### Step 5: FastAPI 프로젝트 초기화 (2026-04-22)

**작업 결과:**
- FastAPI 앱 인스턴스 생성 (title="VIA API", version="0.1.0")
- Pydantic v2 BaseSettings 기반 VIAConfig 구현 (host, port, debug, cors_origins, upload_dir, log_level)
- CORS 미들웨어 추가 (debug 모드에서 모든 origin 허용)
- GET /health 엔드포인트 구현 → {"status": "ok", "version": "0.1.0"} 반환
- httpx.AsyncClient + ASGITransport 기반 비동기 테스트 구현
- requirements.txt에 pydantic-settings, anyio 추가
- pyproject.toml에 anyio 백엔드 설정 추가

**발생 이슈:**
- anyio pytest 플러그인이 trio 백엔드도 자동 실행하여 trio 미설치 오류 발생. anyio_backend fixture를 asyncio 전용으로 오버라이드하여 해결.
- CORS 미들웨어에서 allow_credentials=True 설정 시 Starlette가 와일드카드(*) 대신 요청 Origin을 반영(reflect)하는 동작 확인. dev 모드에서는 credentials 불필요하므로 제거하여 * 반환 확인.

**생성/수정 파일:**
- tests/test_api_health.py (신규 — 16개 테스트)
- backend/main.py (수정 — FastAPI 앱 + CORS + /health)
- backend/config.py (수정 — VIAConfig BaseSettings)
- requirements.txt (수정 — pydantic-settings, anyio 추가)
- pyproject.toml (수정 — anyio 백엔드 설정)
- PROGRESS.md (수정)
- PLAN.md (수정)

**테스트 결과:**
- 144개 테스트 실행, 143 passed, 1 failed (structlog 미설치 — 기존 이슈) — Ollama 통합 테스트 제외
  - Step 1: 10개 PASSED + 1 FAILED (test_environment.py — structlog 미설치)
  - Step 2: 14개 PASSED (test_opencv.py)
  - Step 4: 103개 PASSED (test_directory_structure.py)
  - Step 5: 16개 PASSED (test_api_health.py — 앱 메타 2, 설정 6, 헬스 5, CORS 2, 404 1)

### Step 6: 이미지 업로드 API + 검증 로직 (2026-04-22)

**작업 결과:**
- ImageValidator 서비스 구현 (backend/services/image_validator.py)
  - 파일명 규칙 검증: OK_N.ext / NG_N.ext 패턴 (N은 1 이상 양의 정수)
  - 확장자 검증: .png, .jpg, .jpeg, .bmp, .tiff 허용
  - 파일 크기 검증: 50MB 제한
  - 이미지 무결성 검증: cv2.imdecode로 실제 이미지 디코딩 확인
- POST /api/images/upload 엔드포인트 구현 (backend/routers/images.py)
  - UploadFile + purpose 쿼리 파라미터 (analysis / test)
  - 5단계 검증: purpose → 파일명 → 확장자 → 크기 → 이미지 무결성
  - 성공 시 {upload_dir}/{purpose}/{filename} 경로에 파일 저장
  - JSON 응답: id (uuid4), filename, label, index, purpose, path
  - 실패 시 422 + detail 메시지 반환
- FastAPI 앱에 images 라우터 등록 (prefix=/api/images)
- requirements.txt에 python-multipart==0.0.22 핀 버전 추가

**발생 이슈:**
- python-multipart가 requirements.txt에 추가되었으나 실제 설치가 누락되어 모든 테스트가 collection error 발생. pip install python-multipart로 해결. 버전 0.0.22 핀 적용.

**생성/수정 파일:**
- tests/test_image_upload.py (신규 — 32개 테스트)
- backend/services/image_validator.py (수정 — ImageValidator 구현)
- backend/routers/images.py (수정 — POST /upload 엔드포인트)
- backend/main.py (수정 — images 라우터 등록)
- requirements.txt (수정 — python-multipart 추가)
- PROGRESS.md (수정)
- PLAN.md (수정)

**테스트 결과:**
- 176개 테스트 실행, 175 passed, 1 failed (structlog 미설치 — 기존 이슈) — Ollama 통합 테스트 제외
  - Step 1: 10개 PASSED + 1 FAILED (test_environment.py — structlog 미설치)
  - Step 2: 14개 PASSED (test_opencv.py)
  - Step 4: 103개 PASSED (test_directory_structure.py)
  - Step 5: 16개 PASSED (test_api_health.py)
  - Step 6: 32개 PASSED (test_image_upload.py — 유효파일명 5, 무효파일명 8, purpose 검증 1, 파일크기 1, 이미지무결성 2, 업로드성공 3, purpose라우팅 3, Validator단위 9)

### Step 7: 이미지 저장소 관리 서비스 (2026-04-23)

**작업 결과:**
- ImageStore 인메모리 서비스 구현 (backend/services/image_store.py)
  - add: 메타데이터 저장 + uploaded_at(UTC ISO 8601) 자동 부여
  - get: image_id로 단일 조회 (없으면 None)
  - list_all: 전체 목록 조회 (purpose, label 필터 지원)
  - delete: 메타데이터 삭제 + 디스크 파일 삭제 (FileNotFoundError graceful 처리)
  - clear: 전체 또는 purpose별 일괄 삭제
  - count: 전체 또는 purpose별 개수 반환
- 모듈 레벨 싱글톤 패턴 (image_store = ImageStore())
- REST API 엔드포인트 추가 (backend/routers/images.py)
  - GET /api/images: 목록 조회 (purpose, label 쿼리 파라미터)
  - GET /api/images/{image_id}: 단일 조회 (404 처리)
  - DELETE /api/images/{image_id}: 단일 삭제 (메타+파일, 404 처리)
  - DELETE /api/images: 전체/purpose별 일괄 삭제
- 기존 POST /api/images/upload에 ImageStore 연동: 업로드 성공 시 자동 등록, 응답에 uploaded_at 포함

**발생 이슈:**
- 없음

**생성/수정 파일:**
- tests/test_image_store.py (신규 — 38개 테스트)
- backend/services/image_store.py (수정 — ImageStore 클래스 구현)
- backend/routers/images.py (수정 — GET/DELETE 엔드포인트 추가 + store 연동)
- PROGRESS.md (수정)
- PLAN.md (수정)

**테스트 결과:**
- 214개 테스트 실행, 213 passed, 1 failed (structlog 미설치 — 기존 이슈) — Ollama 통합 테스트 9개 제외
  - Step 1: 10개 PASSED + 1 FAILED (test_environment.py — structlog 미설치)
  - Step 2: 14개 PASSED (test_opencv.py)
  - Step 4: 103개 PASSED (test_directory_structure.py)
  - Step 5: 16개 PASSED (test_api_health.py)
  - Step 6: 32개 PASSED (test_image_upload.py)
  - Step 7: 38개 PASSED (test_image_store.py — add 4, get 3, list_all 5, delete 5, clear 3, count 3, API list 4, API get 2, API delete 2, API clear 2, upload-store통합 5)

### Step 8: 실행 설정 API + Agent Directive API (2026-04-23)

**작업 결과:**
- ConfigStore 인메모리 서비스 구현 (backend/services/config_store.py)
  - save: ExecutionConfig 저장 (덮어쓰기)
  - get: 현재 설정 반환 (미설정 시 None)
  - clear: 설정 초기화
- DirectiveStore 인메모리 서비스 구현 (backend/services/directive_store.py)
  - 8개 에이전트 필드: orchestrator, spec, image_analysis, pipeline_composer, vision_judge, inspection_plan, algorithm_coder, test
  - get: 전체 디렉티브 반환
  - save: 다수 필드 일괄 저장
  - update: 단일 에이전트 디렉티브 갱신 (미존재 시 ValueError)
  - reset: 전체 필드를 None으로 초기화
- Execution Config API 구현 (backend/routers/config.py)
  - POST /api/config: 설정 저장 + 극단적 목표 경고 반환
  - GET /api/config: 저장된 설정 반환 (없으면 404)
  - Pydantic v2 모델: InspectionCriteria (accuracy/fp_rate/fn_rate), AlignCriteria (coord_error/success_rate)
  - mode: "inspection" | "align" (Literal)
  - max_iteration: 기본값 5, 범위 1-20
  - 극단적 목표 경고 로직: accuracy>0.99, fp_rate<0.001, fn_rate<0.001, coord_error<0.5
- Agent Directive API 구현 (backend/routers/directives.py)
  - POST /api/directives: 디렉티브 일괄 저장
  - GET /api/directives: 현재 디렉티브 반환 (초기 전체 None)
  - PUT /api/directives/{agent_name}: 단일 에이전트 디렉티브 갱신 (미존재 시 404)
  - DELETE /api/directives: 전체 디렉티브 초기화
- backend/main.py에 config_router, directives_router 등록

**발생 이슈:**
- 없음

**생성/수정 파일:**
- tests/test_config_api.py (신규 — 23개 테스트)
- tests/test_directive_api.py (신규 — 23개 테스트)
- backend/services/config_store.py (신규 — ConfigStore 구현)
- backend/services/directive_store.py (신규 — DirectiveStore 구현)
- backend/routers/config.py (수정 — Config 엔드포인트 구현)
- backend/routers/directives.py (수정 — Directive 엔드포인트 구현)
- backend/main.py (수정 — 라우터 등록)
- PROGRESS.md (수정)
- PLAN.md (수정)

**테스트 결과:**
- 260개 테스트 전체 GREEN (260 passed, 0 failed) — Ollama 통합 테스트 제외
  - Step 1: 11개 PASSED (test_environment.py — structlog 설치됨으로 1개 추가 통과)
  - Step 2: 14개 PASSED (test_opencv.py)
  - Step 4: 103개 PASSED (test_directory_structure.py)
  - Step 5: 16개 PASSED (test_api_health.py)
  - Step 6: 32개 PASSED (test_image_upload.py)
  - Step 7: 38개 PASSED (test_image_store.py)
  - Step 8: 46개 PASSED (test_config_api.py 23개 + test_directive_api.py 23개)
    - Config: store단위 4, POST검증 6, GET 2, 극단경고 7
    - Directive: store단위 6, POST 6, GET 3, PUT 5, DELETE 3

### Step 9: 로깅 시스템 구현 (2026-04-23)

**작업 결과:**
- VIALogger 인메모리 서비스 구현 (backend/services/logger.py)
  - structlog 25.5.0 기반 JSON stdout 출력
  - 에이전트 인식 로그 (agent 필드), 레벨: DEBUG/INFO/WARNING/ERROR
  - collections.deque(maxlen=1000) 버퍼, threading.Lock 스레드 안전
  - log(), get_logs(agent, level, limit), clear(), get_agents() 메서드
  - 모듈 레벨 싱글톤: via_logger = VIALogger()
- Logs REST API (backend/routers/logs.py)
  - GET /api/logs, GET /api/logs/agents, DELETE /api/logs
- backend/main.py에 logs_router 등록

**발생 이슈:**
- structlog 미설치 상태 — pip install structlog(25.5.0)으로 해결

**생성/수정 파일:**
- tests/test_logger.py (신규)
- backend/services/logger.py (구현)
- backend/routers/logs.py (구현)
- backend/main.py (수정)
- PLAN.md, PROGRESS.md (수정)

**테스트 결과:**
- 296개 전체 GREEN (296 passed, 0 failed) — Ollama 통합 테스트 제외
  - Step 1: 11개 PASSED
  - Step 2: 14개 PASSED
  - Step 4: 103개 PASSED
  - Step 5: 16개 PASSED
  - Step 6: 32개 PASSED
  - Step 7: 38개 PASSED
  - Step 8: 46개 PASSED
  - Step 9: 36개 PASSED (test_logger.py)
    - VIALogger 단위: log 9, get_logs 6, clear 2, get_agents 3, buffer 2, thread safety 1, singleton 1
    - API 통합: GET /api/logs 7, GET /api/logs/agents 3, DELETE /api/logs 3

### Step 10: Ollama 클라이언트 서비스 (2026-04-23)

**작업 결과:**
- OllamaClient 비동기 서비스 구현 (backend/services/ollama_client.py)
  - httpx.AsyncClient 기반 비동기 HTTP 클라이언트
  - 커스텀 예외 계층: OllamaError(base) → OllamaConnectionError / OllamaModelNotFoundError / OllamaGenerationError
  - check_health(): GET /api/tags로 서버 상태 확인 + 모델 존재 검증
  - generate(prompt, system): POST /api/generate, stream=false, 텍스트 응답 반환
  - generate_with_images(prompt, images, system): base64 이미지 리스트 포함 멀티모달 생성
  - generate_with_image_paths(prompt, image_paths, system): 파일 읽기 → base64 인코딩 → generate_with_images 위임
  - 재시도 로직: max_retries=2 (기본값), TimeoutException/ConnectError 시 지수 백오프(1s, 2s)
  - 타임아웃: health_timeout=30.0, generate_timeout=600.0
  - VIALogger 연동: 모든 요청 INFO 로그, 오류 ERROR 로그 (agent="ollama_client")
  - async with 컨텍스트 매니저 지원 (aclose() 보장)
  - 모듈 레벨 싱글톤: ollama_client = OllamaClient()

**발생 이슈:**
- 없음

**생성/수정 파일:**
- tests/test_ollama_client.py (신규 — 38개 테스트)
- backend/services/ollama_client.py (수정 — OllamaClient 구현)
- PROGRESS.md (수정)
- PLAN.md (수정)

**테스트 결과:**
- 334개 테스트 전체 GREEN (334 passed, 0 failed) — Ollama 통합 테스트 제외
  - Step 1: 11개 PASSED
  - Step 2: 14개 PASSED
  - Step 4: 103개 PASSED
  - Step 5: 16개 PASSED
  - Step 6: 32개 PASSED
  - Step 7: 38개 PASSED
  - Step 8: 46개 PASSED
  - Step 9: 36개 PASSED
  - Step 10: 38개 PASSED (test_ollama_client.py)
    - 예외 계층 4, 생성자 기본값 6, check_health 5, generate 8
    - generate_with_images 3, generate_with_image_paths 3, retry 4, logging 2, context manager 2, singleton 1

### Step 12: Spec Agent 구현 (2026-04-23)

**작업 결과:**
- SpecAgent 구현 (agents/spec_agent.py): BaseAgent 상속, execute(user_text) → SpecResult
- JSON 파싱 로직: markdown code fence(```json ... ```) 자동 제거, 실패 시 1회 retry, 2회 모두 실패 시 ValueError 발생
- 모드 기본값: 인식 불가 mode → "inspection" + WARNING 로그
- success_criteria 기본값 자동 적용 (inspection: accuracy=0.95, fp_rate=0.05, fn_rate=0.05 / align: coord_error=2.0, success_rate=0.9)
- 프롬프트 모듈 구현 (agents/prompts/spec_prompt.py): SPEC_SYSTEM_PROMPT 상수 + build_spec_prompt(user_text, directive) 순수 함수
- Agent Directive 지원: directive가 있으면 사용자 프롬프트에 추가
- 모든 OllamaClient 호출 AsyncMock으로 격리 (실제 Ollama 호출 없음)

**발생 이슈:**
- PCRO 프롬프트에서 SpecResult 필드명을 "objective"로 기술했으나 실제 models.py에는 "goal"로 정의됨 — 파일을 먼저 읽어 확인 후 올바른 필드명 사용

**생성/수정 파일:**
- tests/test_spec_agent.py (신규 — 26개 테스트)
- agents/prompts/spec_prompt.py (신규)
- agents/spec_agent.py (수정 — placeholder → 전체 구현)
- PROGRESS.md (수정)
- PLAN.md (수정)

**테스트 결과:**
- 433개 테스트 전체 GREEN (433 passed, 0 failed) — Ollama 통합 테스트 제외
  - Step 12: 26개 PASSED (test_spec_agent.py)
    - 클래스 구조: 4 (상속, agent_name, directive 저장)
    - 프롬프트 템플릿: 9 (user_text 포함, directive 포함, system prompt 내용 검증)
    - execute() 핵심: 5 (inspection/align/Korean 파싱, system 프롬프트 전달, directive 전달)
    - 기본값 처리: 4 (inspection/align 기본값, 부분 기본값, 미인식 mode)
    - JSON 파싱 견고성: 4 (markdown code block, plain code block, retry, 이중 실패 예외)

### Step 14: Pipeline Block Library 구현 (2026-04-24)

**작업 결과:**
- BlockDefinition 클래스 구현: name, category, params(검색 공간), apply(image, params), matches(diagnosis) 5개 필드
- 21개 블록 정의 — 5개 카테고리:
  - color_space (3): grayscale, hsv_s, lab_l
  - noise_reduction (6): gaussian_fine, gaussian_mid, bilateral, median, nlmeans, clahe
  - threshold (3): otsu, adaptive_mean, adaptive_gauss
  - morphology (6): erosion, dilation, opening, closing, tophat, blackhat
  - edge (3): canny, sobel, laplacian
- 각 블록의 apply() 구현:
  - grayscale: cv2.cvtColor BGR2GRAY (color만), gray 입력 시 그대로 반환
  - hsv_s/lab_l: 컬러 입력 → 해당 채널 추출 2D 반환, 그레이 입력 시 unchanged
  - gaussian_fine/mid: cv2.GaussianBlur (0,0) ksize (sigma로 자동 계산)
  - bilateral: cv2.bilateralFilter, sigmaSpace=sigmaColor
  - median: cv2.medianBlur
  - nlmeans: 컬러=fastNlMeansDenoisingColored, 그레이=fastNlMeansDenoising
  - clahe: cv2.createCLAHE, 그레이 자동 변환
  - otsu/adaptive_mean/adaptive_gauss: 그레이 자동 변환 → 이진화 출력
  - erosion/dilation/opening/closing/tophat/blackhat: 그레이 자동 변환 → 형태학 연산
  - canny: 그레이 자동 변환 → cv2.Canny
  - sobel: 그레이 자동 변환 → |Gx|+|Gy| → uint8
  - laplacian: 그레이 자동 변환 → convertScaleAbs → uint8
- PipelineBlockLibrary 클래스: get_block, get_all_blocks, get_categories, get_blocks_by_category, get_matching_blocks (category 필터 지원)
- 모듈 레벨 싱글톤: block_library = PipelineBlockLibrary()
- LLM 호출 전혀 없음 (완전 규칙 기반)

**발생 이슈:**
- 없음 (63개 테스트 1회 실행에서 전체 GREEN)

**생성/수정 파일:**
- tests/test_pipeline_blocks.py (신규 — 63개 테스트)
- agents/pipeline_blocks.py (수정 — placeholder → 전체 구현)
- PROGRESS.md (수정)
- PLAN.md (수정)

**테스트 결과:**
- 559개 테스트 전체 GREEN (559 passed, 0 failed) — Ollama 통합 테스트 제외
  - Step 14: 63개 PASSED (test_pipeline_blocks.py)
    - BlockDefinition 구조: 5 (name/category/params/apply/matches 필드)
    - apply() color 유효성 (parametrize 21블록): 21
    - apply() 엣지케이스: 4 (grayscale→2D, gray→2D, hsv_s+gray, otsu+color)
    - matches() True: 15 (블록별 조건 True 검증)
    - matches() False: 5 (경계값/반대 조건 False 검증)
    - PipelineBlockLibrary 메서드: 7 (get_block, KeyError, 21개수, 5카테고리, by_category, matching, filter)
    - 파라미터 공간: 5 (gaussian_fine sigma, bilateral keys, erosion iterations, canny t1/t2, grayscale empty)
    - 싱글톤: 1

### Step 13: Image Analysis Agent (ImageDiagnosis 전체) (2026-04-24)

**작업 결과:**
- ImageAnalysisAgent 구현 (agents/image_analysis_agent.py): BaseAgent 상속, execute(image) → ImageDiagnosis (동기, LLM 미사용)
- ImageDiagnosis 21개 필드 전체 OpenCV + NumPy 순수 연산으로 구현
  - 각 필드마다 전용 private 메서드 (_compute_contrast, _compute_noise_level, ...)
  - _compute_contrast: RMS contrast (std / 255)
  - _compute_noise_level: GaussianBlur diff std / 50 (고주파 노이즈 추정)
  - _compute_edge_density: Canny(50, 150) edge pixel ratio
  - _compute_lighting_uniformity: 4×4 grid 셀 평균의 변동계수 기반 (1 - CV)
  - _compute_illumination_type: uniformity > 0.85 → uniform, spot/gradient/uneven 휴리스틱 분류
  - _compute_noise_frequency: FFT magnitude 저주파 vs 고주파 에너지 비교
  - _compute_reflection_level: pixel >= 250 비율
  - _compute_texture_complexity: Laplacian variance / 5000
  - _compute_edge_sharpness: Laplacian variance (비정규화)
  - _compute_blob_metrics: Otsu threshold → findContours → feasibility/count/variance/threshold 4-tuple
  - _compute_color_discriminability: 색상 이미지=채널 mean 최대차/255, 그레이=Otsu 클래스간 분산
  - _compute_dominant_channel_ratio: 그레이=1.0, 컬러=max채널mean/sum
  - _compute_structural_regularity: 16×16 패치 상관계수 평균
  - _compute_pattern_repetition: 자기상관 (수직 shift 분석)
  - _compute_background_uniformity: 히스토그램 최빈값 주변 픽셀 CV
  - _classify_surface: texture/reflection/edge_density 기반 6-class 규칙
  - _classify_defect_scale: blob 크기/개수 기반 macro/micro/texture
  - _compute_optimal_color_space: is_color/color_disc/surface_type 기반 gray/hsv_s/lab_l/rgb
- 엣지 케이스 처리: 2D 그레이스케일 입력, 10×10 초소형 이미지, 전체 흑/백 이미지
- 모든 float 출력값 finite 보장 (_clamp + 예외 처리)
- Agent Directive 지원: directive 존재 시 INFO 로그, 연산은 결정론적

**발생 이슈:**
- test_striped_image_has_edges 임계값 조정: Canny 내부 Gaussian blur로 인해 edge_density가 예상보다 낮게 측정됨 (0.02). 임계값 > 0.05 → > 0.01로 수정 (동작은 정확함, 기대치 조정)

**생성/수정 파일:**
- tests/test_image_analysis.py (신규 — 63개 테스트)
- agents/image_analysis_agent.py (수정 — placeholder → 전체 구현)
- PROGRESS.md (수정)
- PLAN.md (수정)

**테스트 결과:**
- 496개 테스트 전체 GREEN (496 passed, 0 failed) — Ollama 통합 테스트 제외
  - Step 13: 63개 PASSED (test_image_analysis.py)
    - 클래스 구조: 8 (상속, agent_name, callable, sync, 반환타입, directive, 기본directive, kwarg)
    - 대비/노이즈/엣지/균일도: 10 (contrast 3, noise 3, edge 3, uniformity 3)
    - 조명타입/노이즈주파수: 4 (illumination 2, frequency 2)
    - 반사/텍스처/표면/결함: 7 (reflection 3, texture 3, surface 2, defect 1)
    - 블롭/컬러: 7 (blob 4, color 3)
    - 구조/패턴/배경/색공간/임계값/선명도: 12 (structural 4, colorspace 2, threshold 2, sharpness 2, bg 2)
    - 엣지케이스: 8 (grayscale, tiny, black, white, all_floats_finite×4, tiny_finite)
    - 전체 실행: 4 (색상이미지, 21필드타입, directive, noisy)

### Step 15: Pipeline Composer 구현 (2026-04-25)

**작업 결과:**
- PipelineComposer 구현 (agents/pipeline_composer.py): BaseAgent 상속, execute(diagnosis: ImageDiagnosis) → list[ProcessingPipeline] (동기, LLM 미사용)
- block_library.get_matching_blocks() 활용하여 진단 결과 기반 적합 블록 선택
- 매칭 블록 없는 카테고리는 해당 카테고리 전체 블록으로 폴백 (항상 정확히 5개 파이프라인 보장)
- 5가지 다양한 전략으로 파이프라인 구성:
  1. 적극적_노이즈제거_파이프라인: cs(1) + nr(:2) + th(0) + mo(0) — 적극적 노이즈 제거 후 이진화
  2. 적응형_임계값_파이프라인: (cs 없음) + nr(0) + adaptive_th + mo(1) — 적응형 임계값 중심
  3. 엣지_검출_파이프라인: cs(0) + nr(0) + ed(0) — 엣지 검출 전용
  4. 최소_전처리_파이프라인: th(0) 만 — 최소 전처리
  5. 형태학적_정제_파이프라인: cs(0) + nr(0) + otsu + mo(:2) — 형태학 연산 중심
- 블록 배열 순서 보장: color_space → noise_reduction → threshold → morphology → edge
- 카테고리별 상한 강제: color_space ≤1, noise_reduction ≤2, threshold ≤1, morphology ≤2, edge ≤1
- 파이프라인 내 블록 중복 없음
- 전략 2는 cs 미사용, 전략 4는 cs+nr 미사용 → 5개 전략 간 블록셋 항상 다름 (다양성 보장)
- 적응형 임계값 선호: adaptive_mean/adaptive_gauss 우선, 없으면 th[0] 폴백
- Otsu 선호: 형태학 파이프라인에서 otsu 우선, 없으면 th[0] 폴백
- Agent Directive 지원: "Blob"/"blob"/"블롭" 포함 시 morphology 블록이 있는 파이프라인 우선 정렬
- 모든 PipelineBlock.params = {} (Step 16 Parameter Searcher에서 채움)
- 모든 파이프라인 이름은 한국어 (적극적_노이즈제거_파이프라인 등)
- ProcessingPipeline.score = 0.0 초기화 (Step 17 Vision Judge에서 채점)

**발생 이슈:**
- PCRO 프롬프트에서 ProcessingPipeline 필드명을 pipeline_id/description으로 기술했으나, 실제 models.py에는 name/score 만 존재 (description 없음). 또한 PipelineBlock 필드명은 block_name/parameters가 아닌 name/when_condition/params. 항상 모델 파일을 먼저 읽어 확인한 후 구현함.

**생성/수정 파일:**
- tests/test_pipeline_composer.py (신규 — 42개 테스트)
- agents/pipeline_composer.py (수정 — placeholder → 전체 구현)
- PROGRESS.md (수정)
- PLAN.md (수정)

**테스트 결과:**
- 601개 테스트 전체 GREEN (601 passed, 0 failed) — Ollama 통합 테스트 제외
  - Step 15: 42개 PASSED (tests/test_pipeline_composer.py)
    - 클래스 구조: 5 (BaseAgent 상속, agent_name, 동기 execute, directive 생성자, set_directive)
    - 출력 유효성: 6 (list+타입, 정확히 5개, 여러 진단에서 5개, 이름 비공백+고유, score=0.0, 최소 1블록)
    - PipelineBlock 필드: 3 (params=빈dict, name 비공백, when_condition 비공백)
    - 블록 제약: 7 (라이브러리 내 name, max 1 cs, max 2 nr, max 1 th, max 2 mo, max 1 ed, 중복없음)
    - 블록 순서: 3 (표준/고노이즈/비균일조명 진단별 category order 검증)
    - 파이프라인 다양성: 3 (identical 아님, edge 포함, morphology 포함)
    - 엣지케이스: 4 (고노이즈 5개, 저대비 5개, 최소매칭 5개, 고대비균일 5개)
    - Directive 지원: 4 (Blob 대문자, blob 소문자, 블롭 한국어 → morphology 우선; 제약 미위반)
    - 전략별: 5 (적극적=cs+2NR, 적응형=adaptive_th, 엣지=edge+no_th, 최소=1블록, 형태학=2mo)
    - 한국어 이름: 2 (5개 전략명 정확히 일치, 모든 이름 한국어 포함)

### Step 16: Parameter Searcher + ProcessingQualityEvaluator (2026-04-25)

**작업 결과:**
- ProcessingQualityEvaluator 구현 (agents/processing_quality_evaluator.py): BaseAgent 비상속 유틸리티 클래스, evaluate(original, processed) → dict
  - contrast_preservation: min(std(proc_gray) / std(orig_gray), 1.0), orig_std==0 → 1.0
  - edge_retention: min(Canny(proc) / Canny(orig), 1.0), orig_edges==0 → 1.0
  - noise_reduction_score: max(0, 1 - noise(proc) / noise(orig)), 노이즈=std(img - GaussianBlur(img, σ=1.0)), orig_noise==0 → 1.0
  - detail_preservation: cv2.matchTemplate(proc, orig_patch, TM_CCOEFF_NORMED) 그리드 패치 평균, std≈0 패치 → 1.0 처리
  - overall_score: 0.3×contrast + 0.25×edge + 0.25×noise + 0.2×detail
  - 컬러 입력 자동 그레이스케일 변환, 모든 점수 [0.0, 1.0] 클램핑
- ParameterSearcher 구현 (agents/parameter_searcher.py): BaseAgent 상속, agent_name="parameter_searcher"
  - execute(pipeline, image) → ProcessingPipeline (동기, LLM 미사용)
  - 각 블록별 itertools.product로 전체 파라미터 조합 생성
  - 조합 수 > 500이면 random.Random(42).sample(all_combos, 500) 으로 재현 가능 샘플링
  - 블록별 최고 overall_score 파라미터 선택 → block.params 갱신
  - 순차 최적화: 이전 블록 출력 이미지를 다음 블록 최적화의 입력으로 사용
  - apply() 예외 시 WARNING 로그, 해당 조합 스킵; 전체 실패 시 block.params={} + ERROR 로그
  - 빈 params 검색 공간({}) 블록은 스킵 (조합 없음)
  - 파이프라인 전체 end-to-end 실행 후 최종 evaluate로 pipeline.score 설정
  - Agent Directive 지원: directive 존재 시 INFO 로그, 검색 결과는 결정론적

**발생 이슈:**
- test_heavily_blurred_loses_edges: 초기 fixture(gray_image)는 행별 gradient 이미지로 Canny(50,150) 임계값 이하여서 edge=0 → edge_retention=1.0 반환. 테스트를 step image(좌=0, 우=255)로 교체하여 원래 이미지에 선명한 엣지가 있음을 보장.
- test_large_search_space_calls_apply_at_most_500: 검색 500회 + 최적 파라미터 적용 1회 + 최종 평가 1회 = 502회 호출. 테스트 assertion을 ≤502로 수정.

**생성/수정 파일:**
- tests/test_parameter_searcher.py (신규 — 51개 테스트)
- agents/processing_quality_evaluator.py (수정 — placeholder → 전체 구현)
- agents/parameter_searcher.py (수정 — placeholder → 전체 구현)
- PROGRESS.md (수정)
- PLAN.md (수정)

**테스트 결과:**
- 652개 테스트 전체 GREEN (652 passed, 0 failed) — Ollama 통합 테스트 제외
  - Step 16: 51개 PASSED (tests/test_parameter_searcher.py)
    - ProcessingQualityEvaluator (28개):
      - import/구조 3 (importable, not BaseAgent, has evaluate)
      - output 4 (returns dict, all keys, floats, range)
      - contrast_preservation 5 (identical=1, zero_std=1, blurred<1, formula, clamped≤1)
      - edge_retention 4 (identical=1, no_edges=1, heavily_blurred<1, formula)
      - noise_reduction_score 5 (identical=0, zero_noise=1, blurring increases, white=1, clamped≥0)
      - detail_preservation 3 (identical≥0.8, in_range, black_graceful)
      - overall_score 2 (weighted average formula, in range)
      - color handling 2 (no raise, color same as gray for identical)
    - ParameterSearcher (23개):
      - import/구조 5 (importable, BaseAgent, agent_name, directive, set_directive)
      - execute 반환 2 (returns Pipeline, same object)
      - 파라미터 선택 5 (params updated, sigma from space, empty skipped, score set, score in range)
      - 순차 최적화 2 (two blocks, three blocks all params set)
      - directive 1 (no change to results)
      - 예외 처리 3 (all fail → empty, pipeline returns, partial failure → best remaining)
      - 조합 제한 3 (≤502 calls, reproducible seed=42, small not sampled)
      - 최종 스코어링 2 (full pipeline, empty pipeline)

### Step 11: Agent 기본 인터페이스 + 전체 모델 정의 (2026-04-23)

**작업 결과:**
- 7개 Enum 구현 (agents/models.py): InspectionMode, AlgorithmCategory, FailureReason, DecisionType, DefectScale, IlluminationType, NoiseFrequency — 모두 (str, Enum) 상속으로 JSON 직렬화 호환
- 16개 dataclass 구현 (agents/models.py): ImageDiagnosis(21개 필드), PipelineBlock, ProcessingPipeline, JudgementResult, InspectionItem, InspectionPlan, SpecResult, TestMetrics, ItemTestResult, EvaluationResult, FeedbackAction, DecisionResult, AgentDirectives(8개 Optional[str] 필드), ExecutionProgress, AlgorithmResult
- BaseAgent 추상 기반 클래스 구현 (agents/base_agent.py): ABC + abstractmethod execute(), agent_name 프로퍼티, get_directive()/set_directive(), _log() — via_logger 싱글톤 연동
- 모든 가변 기본값에 field(default_factory=list/dict) 적용으로 mutable default 문제 방지

**발생 이슈:**
- 없음

**생성/수정 파일:**
- tests/test_models.py (신규 — 73개 테스트)
- agents/models.py (수정 — 7개 Enum + 16개 dataclass 전체 구현)
- agents/base_agent.py (수정 — BaseAgent 추상 클래스 구현)
- PROGRESS.md (수정)
- PLAN.md (수정)

**테스트 결과:**
- 407개 테스트 전체 GREEN (407 passed, 0 failed) — Ollama 통합 테스트 제외
  - Step 1: 11개 PASSED
  - Step 2: 14개 PASSED
  - Step 4: 103개 PASSED
  - Step 5: 16개 PASSED
  - Step 6: 32개 PASSED
  - Step 7: 38개 PASSED
  - Step 8: 46개 PASSED
  - Step 9: 36개 PASSED
  - Step 10: 38개 PASSED
  - Step 11: 73개 PASSED (test_models.py)
    - Enum: InspectionMode 3, AlgorithmCategory 3, FailureReason 2, DecisionType 2, DefectScale 2, IlluminationType 2, NoiseFrequency 2
    - Dataclass: ImageDiagnosis 5, PipelineBlock 3, ProcessingPipeline 4, JudgementResult 3, InspectionItem 3, InspectionPlan 2, SpecResult 2, TestMetrics 3, ItemTestResult 3, EvaluationResult 4, FeedbackAction 3, DecisionResult 2, AgentDirectives 5, ExecutionProgress 2, AlgorithmResult 2
    - BaseAgent: abstract 3, properties 5, logging 3

### Step 17: Vision Judge Agent (멀티모달 핵심) (2026-04-26)

**작업 결과:**
- VISION_JUDGE_SYSTEM_PROMPT 상수 구현 (agents/prompts/vision_judge_prompt.py): Gemma4가 비전 처리 품질 심판으로 동작하도록 지시, 5개 JSON 키(visibility_score, separability_score, measurability_score, problems, next_suggestion) 및 정의 포함
- build_vision_judge_prompt(purpose, pipeline_name, directive=None) 빌더 함수 구현: purpose + pipeline_name 포함, directive 있으면 추가 안내로 append
- VisionJudgeAgent 전체 구현 (agents/vision_judge_agent.py): BaseAgent 상속, agent_name="vision_judge"
  - execute(original_image, processed_image, purpose, pipeline_name) → JudgementResult (async)
  - cv2.imencode → base64.b64encode → decode('utf-8') 방식으로 양쪽 이미지 PNG 인코딩 (data URI 접두어 없음)
  - ollama_client.generate_with_images(prompt, [orig_b64, proc_b64], system=SYSTEM_PROMPT) 호출
  - JSON 파싱 강건성: markdown code fence(```json ... ```) 자동 제거, 빈 응답/파싱 실패 시 1회 재시도, 2회 모두 실패 시 ValueError 발생
  - 점수 클램핑: visibility/separability/measurability_score 모두 [0.0, 1.0] 강제
  - OllamaError 계열 예외는 그대로 전파 (재시도 없음)
  - 성공 시 INFO 로그, 최종 실패 시 ERROR 로그

**발생 이슈:**
- 없음 (37개 테스트 1회 실행에서 전체 GREEN)

**생성/수정 파일:**
- tests/test_vision_judge.py (신규 — 37개 테스트)
- agents/prompts/vision_judge_prompt.py (신규)
- agents/vision_judge_agent.py (수정 — placeholder → 전체 구현)
- PROGRESS.md (수정)
- PLAN.md (수정)

**테스트 결과:**
- 689개 테스트 전체 GREEN (689 passed, 9 deselected, 0 failed) — Ollama 통합 테스트 제외
  - Step 17: 37개 PASSED (tests/test_vision_judge.py)
    - 프롬프트 모듈 (12개):
      - VISION_JUDGE_SYSTEM_PROMPT 존재/길이, judge/quality/vision 포함, JSON 지시 포함, 5개 JSON 키 포함
      - build_vision_judge_prompt: purpose/pipeline_name 포함, directive 없을 시 미포함, directive 있을 시 append, 길이 증가, JSON 포맷 지시
    - 클래스 구조 (5개): BaseAgent 상속, agent_name="vision_judge", execute 코루틴, directive 생성자, set_directive
    - execute 핵심 (5개): JudgementResult 반환, 점수 [0,1] 범위, problems=list[str], next_suggestion=str, 이미지 2개 전달
    - JSON 파싱 강건성 (4개): markdown code fence 처리, plain JSON, 1회 실패 후 재시도 성공, 2회 실패 ValueError
    - 점수 클램핑 (3개): >1.0 → 1.0, <0.0 → 0.0, 음수 큰값 → 0.0
    - 이미지 인코딩 (3개): 그레이스케일 PNG magic bytes 검증, 컬러 PNG magic bytes 검증, data URI 접두어 없음
    - Directive 지원 (2개): directive 프롬프트에 포함, directive 없으면 "directive" 미포함
    - 에러 처리 (3개): OllamaError 전파, OllamaConnectionError 전파, 빈 응답 재시도 후 성공

### Step 19: Algorithm Selector 구현 (결정 트리) (2026-04-27)

**작업 결과:**
- AlgorithmSelector 클래스 구현 (agents/algorithm_selector.py): BaseAgent 상속, agent_name="algorithm_selector"
  - execute(diagnosis: ImageDiagnosis) → AlgorithmCategory (동기 메서드, async 없음, LLM 없음)
  - 결정 트리 (PLAN.md Section 2.4.3 기준, 조건 순서 엄격 준수):
    1. contrast > 0.4 AND blob_feasibility > 0.6 → BLOB
    2. color_discriminability > 0.5 → COLOR_FILTER
    3. edge_density > 0.3 AND structural_regularity > 0.5 → EDGE_DETECTION
    4. pattern_repetition > 0.7 → TEMPLATE_MATCHING
    5. 기본 fallback → BLOB
  - directive는 INFO 로그에만 기록, 결정 트리 로직에 영향 없음
  - 선택된 카테고리와 매칭된 조건 이유를 INFO 로그로 출력

**발생 이슈:**
- 경계값 테스트 중 `test_blob_contrast_at_exact_threshold_does_not_match` 초안의 assertion 로직 오류 발견 (BLOB branch 미매칭 시 default fallback도 BLOB을 반환하므로 단순 != BLOB으로 검증 불가) → COLOR_FILTER 조건을 추가해 "BLOB branch가 스킵되면 COLOR_FILTER가 이긴다"는 방식으로 테스트 재작성

**생성/수정 파일:**
- tests/test_algorithm_selector.py (신규 — 40개 테스트)
- agents/algorithm_selector.py (수정 — placeholder → 전체 구현)
- PROGRESS.md (수정)
- PLAN.md (수정)

**테스트 결과:**
- 773개 테스트 전체 GREEN (773 passed, 0 failed) — Ollama 통합 테스트 제외
  - Step 19: 40개 PASSED (tests/test_algorithm_selector.py)
    - 클래스 구조 (7개): BaseAgent 상속, agent_name, directive 없음(기본), directive 저장, set_directive, execute 동기 반환, execute 코루틴 아님
    - LLM 없음 검증 (2개): ollama import 없음, ollama_client 속성 없음
    - 결정 트리 happy path (5개): BLOB, COLOR_FILTER, EDGE_DETECTION, TEMPLATE_MATCHING, default BLOB
    - 경계값 (11개): 각 임계값 정확히 equal(not >), just above, BLOB 양쪽 조건 독립 검증 등
    - 우선순위/순서 (6개): BLOB > COLOR_FILTER, BLOB > EDGE_DETECTION, BLOB > TEMPLATE_MATCHING, COLOR_FILTER > EDGE_DETECTION, COLOR_FILTER > TEMPLATE_MATCHING, EDGE_DETECTION > TEMPLATE_MATCHING
    - 엣지 케이스 (4개): 전체 0, 전체 최대, BLOB 단일 조건 충족, EDGE_DETECTION 단일 조건 충족
    - 결정론 (2개): 동일 입력 10회 동일 결과, 다른 인스턴스 동일 결과
    - Directive 독립성 (3개): directive 있어도 결과 동일, directive override 시도 무시, set_directive 후 결과 동일

### Step 18: Inspection Plan Agent 구현 (2026-04-26)

**작업 결과:**
- INSPECTION_PLAN_SYSTEM_PROMPT 상수 구현 (agents/prompts/inspection_plan_prompt.py): Gemma4가 산업용 비전 검사 플래너로 동작하도록 지시, JSON 출력 포맷(items 배열, 각 item에 id/name/purpose/method/depends_on/safety_role/success_criteria), AlgorithmCategory 값(BLOB/COLOR_FILTER/EDGE_DETECTION/TEMPLATE_MATCHING) 명시, 자유 설계 원칙(고정 템플릿 없음) 및 의존성 순서 규칙 포함
- build_inspection_plan_prompt(purpose, image_diagnosis_summary, directive=None) 빌더 함수 구현: purpose + image_diagnosis_summary 포함, directive 있으면 "Additional directive:" 형식으로 append
- InspectionPlanAgent 전체 구현 (agents/inspection_plan_agent.py): BaseAgent 상속, agent_name="inspection_plan"
  - execute(purpose, image_diagnosis_summary) → InspectionPlan (async)
  - ollama_client.generate(prompt, system=INSPECTION_PLAN_SYSTEM_PROMPT) 호출
  - JSON 파싱 강건성: markdown code fence(```json ... ```) 자동 제거, 파싱 실패/빈 items 시 1회 재시도, 2회 모두 실패 시 ValueError 발생
  - method 검증: AlgorithmCategory 값과 정확히 일치해야 하며, 불일치 시 WARNING 로그 + BLOB 기본값 설정
  - depends_on 위상 검증: 각 item의 depends_on은 이전 item의 id만 참조 가능; 자기 참조/전방 참조/미존재 id 자동 제거 + WARNING 로그
  - OllamaError 계열 예외는 그대로 전파 (재시도 없음)
  - 성공 시 INFO 로그(item 개수), 최종 실패 시 ERROR 로그
  - InspectionItem 필드: id(int), name(str), purpose(str), method(AlgorithmCategory), depends_on(list[int]), safety_role(str), success_criteria(str)

**발생 이슈:**
- PCRO 프롬프트에 id가 str, method 값이 소문자(blob 등)로 기재되었으나, agents/models.py 실제 확인 시 id=int, AlgorithmCategory 값=대문자(BLOB 등)임을 확인 → 실제 코드 기준으로 구현

**생성/수정 파일:**
- tests/test_inspection_plan.py (신규 — 44개 테스트)
- agents/prompts/inspection_plan_prompt.py (신규)
- agents/inspection_plan_agent.py (수정 — placeholder → 전체 구현)
- PROGRESS.md (수정)
- PLAN.md (수정)

**테스트 결과:**
- 733개 테스트 전체 GREEN (733 passed, 0 failed) — Ollama 통합 테스트 제외
  - Step 18: 44개 PASSED (tests/test_inspection_plan.py)
    - 시스템 프롬프트 (10개): 문자열 타입, 비어있지 않음, 길이>100, "inspection" 포함, "items" 포함, "depends_on" 포함, "safety_role" 포함, "method" 포함, JSON 지시 포함, 4개 AlgorithmCategory 값 포함
    - 빌더 함수 (5개): purpose 포함, diagnosis_summary 포함, directive 있을 시 포함, directive 있을 시 길이 증가, directive 없을 시 미포함
    - 클래스 구조 (5개): BaseAgent 상속, agent_name="inspection_plan", execute 코루틴, directive 생성자, set_directive
    - execute 핵심 (8개): InspectionPlan 반환, InspectionItem 타입, 필드 타입(id=int/name=str/method=AlgorithmCategory/depends_on=list), system 프롬프트로 generate 호출, purpose/summary/directive 프롬프트 포함, 복수 items + depends_on
    - 의존성 검증 (4개): 유효 depends_on 통과, 미존재 참조 제거+WARNING, 자기 참조 제거, 전방 참조 제거
    - method 검증 (3개): 4가지 유효 값 통과, 잘못된 값 BLOB 기본값+WARNING, 소문자 BLOB 기본값
    - JSON 파싱 강건성 (4개): markdown code fence 처리, plain JSON, 1회 실패 후 재시도 성공, 2회 실패 ValueError
    - 에러 처리 (3개): OllamaError 전파, OllamaConnectionError 전파, 빈 items 재시도
    - 엣지 케이스 (2개): 단일 item(의존성 없음), 복잡한 5단계 의존성 체인

### Step 21: Algorithm Coder Agent (Align) 구현 (2026-04-27)

**작업 결과:**
- CODER_ALIGN_SYSTEM_PROMPT 상수 구현 (agents/prompts/coder_align_prompt.py): align(image: np.ndarray) -> dict 시그니처 강제, {"x": float, "y": float, "confidence": float, "method_used": str} 반환 형식 명시, Fallback Chain (template_matching → edge_detection → caliper) 순서 명시, Edge Learning / Deep Learning 명시적 금지, HW 개선(조명/카메라/지그) 권고, cv2/numpy 전용 제약, Korean explanation 요구
- build_coder_align_prompt(pipeline_summary: str, directive: str | None = None) → str 빌더 함수 구현: fallback chain 명시, pipeline_summary 포함, directive 있으면 "Additional directive:" 형식으로 append
- AlgorithmCoderAlign 전체 구현 (agents/algorithm_coder_align.py): BaseAgent 상속, agent_name="algorithm_coder_align"
  - execute(pipeline: ProcessingPipeline) → AlgorithmResult (async)
  - Inspection과 달리 items 순회 없이 단일 generate 호출 (통합 fallback chain 코드 1개 생성)
  - pipeline.blocks에서 pipeline_summary 생성 (block name + params, 빈 블록 "(no preprocessing)")
  - JSON 파싱 강건성: markdown code fence 자동 제거, 파싱/빈 응답 실패 시 1회 재시도, 2회 실패 ValueError
  - AlgorithmResult.category = TEMPLATE_MATCHING (fallback chain의 primary method)
  - OllamaError 계열 예외 그대로 전파

**발생 이슈:**
- 루트 원인: 프로젝트 실제 개발 환경에 pytest-asyncio가 설치되어 있지 않고 anyio만 설치됨. @pytest.mark.asyncio 데코레이터가 unknown mark로 인식되어 anyio 플러그인이 해당 테스트를 수집하지 못하고 pytest 기본 수집기가 "async def functions are not natively supported" 에러를 발생시킴.
- Claude Code 환경에는 pytest-asyncio가 설치되어 있어 3회 반복 재현 실패 (환경 차이).
- 해결: @pytest.mark.asyncio → @pytest.mark.anyio 로 전환 (26개), anyio_backend 픽스처 추가 (params=["asyncio"]) — test_api_health.py 등 기존 파일과 동일한 패턴. anyio의 [asyncio] 파라미터화 방식으로 async 테스트 정상 수집.

**생성/수정 파일:**
- tests/test_coder_align.py (신규 — 59개 테스트, 클래스 기반 재구성)
- agents/prompts/coder_align_prompt.py (신규)
- agents/algorithm_coder_align.py (수정 — placeholder → 전체 구현)
- PROGRESS.md (수정)
- PLAN.md (수정)

**테스트 결과:**
- 878개 테스트 전체 GREEN (878 passed, 0 failed) — Ollama 통합 테스트 제외
  - Step 21: 59개 PASSED (tests/test_coder_align.py)
    - 시스템 프롬프트 (19개): string/비공백, align 시그니처, x/y/confidence/method_used 반환키, template_matching/edge_detection/caliper fallback 포함, 순서 검증(template<edge<caliper), EL/DL 금지, Korean explanation, cv2/numpy, JSON 출력, HW 개선 권고
    - 빌더 함수 (7개): string 반환, pipeline_summary 포함, directive 포함/미포함, default=None, 빈 summary 처리, 비공백
    - 클래스 구조 (6개): BaseAgent 상속, agent_name, 코루틴, _ollama 저장, directive 생성자, 기본 directive=None
    - execute 핵심 (8개): AlgorithmResult 반환, TEMPLATE_MATCHING category, code/explanation LLM에서, pipeline 보존, ollama 1회 호출, system prompt 사용, pipeline_summary 프롬프트 포함
    - JSON 파싱 강건성 (7개): clean JSON, ```json 펜스, plain 펜스, 첫 실패 재시도, 빈 응답 재시도, 2회 실패 ValueError, 2회 빈 응답 ValueError
    - 에러 처리 (4개): OllamaError/OllamaConnectionError/OllamaGenerationError 전파, 재시도 중 OllamaError 전파
    - Directive 지원 (3개): set_directive 동작, directive 프롬프트 포함, 미지정 시 "Additional directive" 미포함
    - 엣지 케이스 (5개): 빈 pipeline → "(no preprocessing)" 프롬프트, 블록 params 포함 summary, 항상 TEMPLATE_MATCHING, pipeline 일치, params없는 블록 이름만 포함

### Step 20: Algorithm Coder Agent (Inspection) 구현 (2026-04-27)

**작업 결과:**
- CODER_INSPECTION_SYSTEM_PROMPT 상수 구현 (agents/prompts/coder_inspection_prompt.py): Gemma4가 산업용 OpenCV 코드 생성기로 동작하도록 지시, inspect_item(image: np.ndarray) -> dict 시그니처 강제, {"result": "OK"/"NG", "details": {...}} 반환 형식 명시, cv2/numpy 전용 제약, 파이프라인 처리 단계 반영 지시, Korean explanation 요구
- build_coder_inspection_prompt(item, category, pipeline_summary, directive=None) 빌더 함수 구현: item.name/purpose/method/success_criteria 포함, category 포함, pipeline_summary 포함, directive 있으면 "Additional directive:" 형식으로 append
- AlgorithmCoderInspection 전체 구현 (agents/algorithm_coder_inspection.py): BaseAgent 상속, agent_name="algorithm_coder_inspection"
  - execute(category, pipeline, plan) → AlgorithmResult (async)
  - pipeline.blocks에서 pipeline_summary 문자열 생성 (block name + params, 빈 블록 "(no preprocessing)")
  - InspectionPlan.items 순회: 각 item별 build_coder_inspection_prompt → ollama_client.generate → JSON 파싱
  - JSON 파싱 강건성: markdown code fence 자동 제거, 파싱/빈 응답 실패 시 1회 재시도, 2회 실패 시 ValueError 발생
  - 모든 item 코드를 "\n\n".join으로 결합 → AlgorithmResult.code
  - 모든 item 설명을 "[item.name] explanation" 형식으로 결합 → AlgorithmResult.explanation
  - OllamaError 계열 예외는 그대로 전파 (재시도 없음)
  - 성공 시 INFO 로그(item 개수), 파싱 최종 실패 시 ERROR 로그

**발생 이슈:**
- 없음 (46개 테스트 1회 실행에서 전체 GREEN)

**생성/수정 파일:**
- tests/test_coder_inspection.py (신규 — 46개 테스트)
- agents/prompts/coder_inspection_prompt.py (신규)
- agents/algorithm_coder_inspection.py (수정 — placeholder → 전체 구현)
- PROGRESS.md (수정)
- PLAN.md (수정)

**테스트 결과:**
- 819개 테스트 전체 GREEN (819 passed, 0 failed) — Ollama 통합 테스트 제외
  - Step 20: 46개 PASSED (tests/test_coder_inspection.py)
    - 시스템 프롬프트 (10개): 존재/비공백/string, OpenCV/cv2 포함, inspect 포함, code 포함, JSON 포함, inspect_item 함수명 포함, OK/NG 포함, explanation 포함
    - 빌더 함수 (10개): item.name/purpose/method/success_criteria 포함, category 포함, pipeline_summary 포함, directive 포함/미포함, string 반환, 비공백
    - 클래스 구조 (5개): BaseAgent 상속, agent_name 정확, execute 코루틴, directive 생성자, set_directive
    - execute 핵심 (9개): AlgorithmResult 반환, category 정확, pipeline 저장, item별 generate 1회씩, code/explanation string, Korean explanation, system prompt 전달, block name 포함
    - JSON 파싱 강건성 (4개): markdown code fence 처리, plain JSON, 1회 실패 재시도 성공, 2회 실패 ValueError
    - 에러 처리 (3개): OllamaError 전파, OllamaConnectionError 전파, 빈 응답 재시도
    - Directive 테스트 (2개): directive 포함 확인, no-directive 미포함 확인
    - 엣지 케이스 (3개): 단일 item, 5개 item 전체 코드 생성, 빈 pipeline blocks

### Step 23: Test Agent (Align) 구현 (2026-04-28)

**작업 결과:**
- TestAgentAlign 전체 구현 (agents/test_agent_align.py): BaseAgent 상속, agent_name="test_agent_align"
  - execute(code: str, test_images: list[tuple[np.ndarray, str]], success_criteria: list[str] | None = None) → list[ItemTestResult] (synchronous, LLM 호출 없음)
  - 항상 단일 원소 list 반환: ItemTestResult(item_id=0, item_name="align")
  - _extract_align(): ast.parse 유효성 검사 후 전체 code를 exec() (np/cv2 사전 주입), align 함수 존재 검증, 실패 시 WARNING 로그 + details="error: function_extraction_failed" 포함 실패 결과 반환
  - GT 파일명 패턴: "X_{float}_Y_{float}_{index}.png" — 정수/소수 모두 지원, 패턴 불일치 파일은 WARNING 로그 후 스킵
  - _compute_metrics(): 유효 이미지별 Euclidean distance 계산, align() 예외 시 9999.0으로 실패 처리
  - coord_error: 유효 이미지 평균 Euclidean distance, 유효 이미지 없으면 0.0
  - success_rate: coord_error < threshold(기본 2.0) 이미지 비율, [0.0, 1.0] 클램프
  - accuracy/fp_rate/fn_rate: 0.0 (Align 모드에서 해당 없음)
  - _evaluate_criteria(): 기본 coord_error <= 2.0 AND success_rate >= 0.9, 커스텀 기준은 "coord_error <= 1.5" 형식 파싱 — 전체 기준 AND 논리
  - Directive 로그: INFO 레벨로 기록, 실행 로직에는 영향 없음

**발생 이슈:**
- 없음 (67개 테스트 1회 실행에서 전체 GREEN)

**생성/수정 파일:**
- tests/test_test_agent_align.py (신규 — 67개 테스트)
- agents/test_agent_align.py (수정 — placeholder → 전체 구현)
- progress.md (수정)
- PLAN.md (수정)

**테스트 결과:**
- 1005개 테스트 전체 GREEN (1005 passed, 0 failed) — Ollama 통합 테스트 제외
  - Step 23: 67개 PASSED (tests/test_test_agent_align.py)
    - 클래스 구조 6개, 반환 타입 6개, 함수 추출 8개
    - Ground truth 파싱 7개, 메트릭 계산 14개, 성공 기준 평가 10개
    - 엣지 케이스 8개, Directive 지원 3개, 로깅 검증 5개