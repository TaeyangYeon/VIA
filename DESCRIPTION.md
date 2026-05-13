# VIA (Vision Intelligence Agent) — 기술 문서

> **설치 방법은 [README.md](README.md)를 참조하세요.**  
> 이 문서는 VIA의 모든 기능, 기술 선택 근거, 비전 알고리즘 원리를 망라하는 정식 기술 레퍼런스입니다.

---

## 목차

1. [프로젝트 개요](#1-프로젝트-개요)
2. [기술 선택과 근거](#2-기술-선택과-근거)
3. [시스템 아키텍처 상세](#3-시스템-아키텍처-상세)
4. [에이전트 상세 설명](#4-에이전트-상세-설명)
5. [컴퓨터 비전 기술 해설](#5-컴퓨터-비전-기술-해설)
6. [검사 모드 상세](#6-검사-모드-상세)
7. [피드백 루프와 자동 개선](#7-피드백-루프와-자동-개선)
8. [Colab 통합](#8-colab-통합)
9. [UI/UX 설계 철학](#9-uiux-설계-철학)
10. [테스트 전략](#10-테스트-전략)
11. [한계와 향후 발전 방향](#11-한계와-향후-발전-방향)

---

## 1. 프로젝트 개요

### 1.1 VIA가 해결하는 문제

산업 비전 검사 시스템을 구축하려면 전통적으로 두 가지 전문성이 동시에 필요하다. 하나는 OpenCV·이미지 처리에 대한 깊은 이해이고, 다른 하나는 검사 대상 제품의 도메인 지식이다. 공장 현장의 품질 관리 엔지니어는 "표면 스크래치를 찾아야 한다"는 목적은 알지만, 어떤 전처리 블록 조합이 최적인지, 임계값은 얼마로 설정해야 하는지 알지 못한다. 반대로 비전 엔지니어는 기술은 있지만 각 공정의 세부 검사 항목을 파악하는 데 시간이 걸린다.

VIA는 이 간극을 없앤다. 사용자가 **자연어로 목적을 입력하고 이미지를 업로드**하면, 멀티에이전트 AI 시스템이 이미지를 분석하고, 전처리 파이프라인을 구성하고, OpenCV 코드를 생성하고, 자체 테스트까지 수행한다. 결과물은 즉시 실행 가능한 Python 코드와 함께 한국어 설명, 성능 메트릭이 제공된다.

### 1.2 전통적 도구와의 차이

| 항목 | 전통적 비전 도구 | VIA |
|------|----------------|-----|
| 알고리즘 설계 | 엔지니어 수동 설계 | AI가 자동 설계 |
| 파라미터 튜닝 | 시행착오 반복 | 자동 탐색 + 피드백 루프 |
| 이미지 품질 평가 | 주관적 시각 확인 | Gemma4 멀티모달 객관 평가 |
| 결과물 | 알고리즘만 | 코드 + 설명 + 메트릭 JSON |
| 실행 환경 | 클라우드 의존 | 완전 오프라인 (로컬 AI) |
| 개선 방식 | 수동 재시도 | 실패 원인 분류 후 자동 재시도 |

### 1.3 핵심 기능 요약

- **Inspection Mode**: 이미지를 OK/NG로 이진 분류하는 알고리즘 자동 설계
- **Align Mode**: 대상 물체의 X/Y 좌표를 산출하는 정렬 알고리즘 자동 설계
- **Agent Directive**: 에이전트별 방향성을 사용자가 직접 지시하는 세밀한 제어
- **Vision Judge**: Gemma4:e4b가 처리 결과 이미지를 눈으로 보고 목적 기준으로 평가
- **Decision Agent**: 반복 실패 시 Rule-based 유지 / Edge Learning / Deep Learning 자동 추천
- **Local / Colab 전환**: Intel Mac 로컬 완전 오프라인 또는 Google Colab GPU 원격 실행
- **결과 내보내기**: OpenCV 코드 + 한국어 설명 + 성능 메트릭 JSON

---

## 2. 기술 선택과 근거

### 2.1 AI 엔진: Ollama + Gemma4:e4b

**선택 근거**: 산업 현장에서 인터넷 연결 없이 민감한 제품 이미지를 외부 클라우드로 전송하는 것은 보안상 허용되지 않는 경우가 많다. Ollama는 로컬 GPU/CPU에서 LLM을 실행하는 표준 런타임이며, Gemma4:e4b는 Google DeepMind의 멀티모달 모델로 4비트 양자화된 약 3.3GB 크기로 Intel Mac에서도 실행 가능하다.

**대안 대비 장점**:
- OpenAI GPT-4V, Claude Vision 등 클라우드 API 대비: 완전 오프라인, 데이터 외부 전송 없음, API 비용 없음
- LLaVA 등 다른 로컬 멀티모달 모델 대비: Gemma4는 코드 생성 품질과 한국어 이해도가 우수

**모델 선택 세부사항**:
- `gemma4:e4b`: 로컬 기본 모델 (Intel Mac, 약 3.3GB)
- `gemma4:27b`: Colab GPU 환경에서 사용 가능한 고성능 버전

### 2.2 백엔드: FastAPI + Python 3.11

**선택 근거**: OpenCV, NumPy 등 비전 라이브러리의 생태계는 Python이 압도적이다. FastAPI는 Python 기반 웹 프레임워크 중 async/await 지원이 가장 자연스럽고, Pydantic을 통한 자동 타입 검증, 자동 OpenAPI 문서 생성이 개발 속도를 높인다.

**대안 대비 장점**:
- Flask 대비: async 지원 없음, 타입 힌트 통합 약함
- Django 대비: 불필요한 ORM·어드민·세션 기능 없음, 경량
- FastAPI: 비동기 LLM 호출(여러 파이프라인 후보 병렬 평가)에 최적

**Python 3.11 선택**: 3.10 대비 예외 처리 성능 향상, 3.12의 asyncio 변경사항을 피해 안정적인 버전 선택.

### 2.3 프론트엔드: Electron + React + TypeScript

**선택 근거**: 비전 검사 앱은 데스크톱 앱이어야 한다. 대용량 이미지 파일을 로컬에서 직접 읽고, 파이프라인 실행 결과를 로컬 파일시스템에 저장하며, Ollama 로컬 서버와 직접 통신해야 하기 때문이다.

- **Electron**: Web 기술(React)로 네이티브 데스크톱 앱 구축. macOS DMG 패키징 지원.
- **React 18**: 컴포넌트 기반 UI, 풍부한 생태계. Redux Toolkit과 자연스러운 통합.
- **TypeScript**: 에이전트 응답 데이터 구조가 복잡하므로 컴파일 타임 타입 안전성 필수.

**대안 대비 장점**:
- 웹 앱 (Next.js 등) 대비: 로컬 파일 시스템 접근, 네이티브 OS 통합, 오프라인 동작
- Tauri 대비: React 생태계 그대로 활용, Rust 추가 학습 불필요

### 2.4 비전 라이브러리: OpenCV

**선택 근거**: OpenCV는 산업 비전 검사의 표준이다. 생성된 알고리즘 코드는 최종적으로 실제 생산 라인 PC에 배포되며, 해당 환경에서 OpenCV가 이미 설치된 경우가 대부분이다. 상용 라이브러리(Halcon, VisionPro 등) 대비 무료이며 소스 코드가 공개되어 있다.

### 2.5 상태 관리: Redux Toolkit

**선택 근거**: VIA UI는 6개 패널이 독립적으로 작동하면서도 실행 상태, 로그, 결과를 공유해야 한다. Redux Toolkit은 불변 상태 관리의 표준이며, Immer 통합으로 복잡한 중첩 상태도 간결하게 업데이트할 수 있다.

### 2.6 개발 방법론: TDD + PCRO

**TDD (Test-Driven Development)**: 모든 에이전트 로직은 테스트 먼저 작성 → Red → Green → Refactor 순서로 개발되었다. 비동기 에이전트, LLM 응답 파싱, OpenCV 처리 등 버그가 잠재하기 쉬운 코드에서 TDD는 회귀 방지에 핵심적이다.

**PCRO (Plan-Code-Review-Output)**: 복잡한 기능 구현 전 PLAN.md에 스펙을 작성하고, Claude Code가 이를 기반으로 구현한 후, 3-Gate 검증(pytest 전체 GREEN + vitest 전체 GREEN + 수동 UI 확인)을 통과해야 커밋한다.

---

## 3. 시스템 아키텍처 상세

### 3.1 레이어 구조

```
┌─────────────────────────────────────────────────────────────────┐
│  Electron Shell (main.js, preload.js)                           │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │  React + Redux UI (frontend/src/)                       │    │
│  │  InputPanel │ DirectivePanel │ ConfigPanel              │    │
│  │  ExecutionPanel │ ResultPanel │ LogPanel                │    │
│  └──────────────────────┬──────────────────────────────────┘    │
└─────────────────────────┼───────────────────────────────────────┘
                          │ HTTP (axios) :8000
┌─────────────────────────▼───────────────────────────────────────┐
│  FastAPI Server (backend/main.py :8000)                         │
│  ├── /api/images        이미지 업로드·저장                       │
│  ├── /api/pipeline/run  파이프라인 실행 진입점                   │
│  ├── /api/engine        AI 엔진 설정 (local/colab 전환)         │
│  └── /api/export        결과 내보내기 (코드 + 메트릭 JSON)      │
└─────────────────────────┬───────────────────────────────────────┘
                          │ Python function calls
┌─────────────────────────▼───────────────────────────────────────┐
│  Orchestrator Agent (agents/orchestrator.py)                    │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  멀티에이전트 시스템 (15개 에이전트)                      │   │
│  │  spec → image_analysis → pipeline_composer               │   │
│  │  → parameter_searcher → vision_judge                     │   │
│  │  → inspection_plan → algorithm_selector                  │   │
│  │  → algorithm_coder → code_validator → test → evaluation  │   │
│  │  └─→ feedback_controller → [retry] → decision_agent      │   │
│  └──────────────────────────────────────────────────────────┘   │
└─────────────────────────┬───────────────────────────────────────┘
                          │ HTTP (httpx) 
         ┌────────────────┴───────────────┐
         ▼                                ▼
[Local: localhost:11434]        [Colab: cloudflared tunnel]
  Ollama + gemma4:e4b             Ollama + gemma4:e4b/27b
```

### 3.2 데이터 흐름 상세

```
사용자 입력
  purpose_text: str          "PCB 납땜 불량 검사"
  images: list[np.ndarray]   OK 이미지 2장 + NG 이미지 2장
  directives: AgentDirectives  에이전트별 방향성 (옵션)
  config: { max_iteration: 5, mode: "inspection" }
       │
       ▼
[Orchestrator.execute()]
       │
       ├─▶ [SpecAgent] ─────────────────────────────────────────▶ SpecResult
       │     LLM 호출: purpose_text → mode, goal, success_criteria
       │     { accuracy: 0.95, fp_rate: 0.05, fn_rate: 0.05 }
       │
       ├─▶ [ImageAnalysisAgent] ────────────────────────────────▶ ImageDiagnosis
       │     OpenCV only: 21개 수치 계산
       │     (1회만 실행, 재시도에서 재사용)
       │
       ├─▶ [PipelineComposer] ──────────────────────────────────▶ list[ProcessingPipeline]
       │     Rule-based: 진단 수치로 5가지 후보 파이프라인 조합
       │
       ├─▶ FOR each candidate:
       │     [ParameterSearcher] ──────────────────────────────▶ ProcessingPipeline (파라미터 최적화)
       │     [VisionJudgeAgent] ───────────────────────────────▶ JudgementResult
       │       Gemma4 멀티모달: 원본+처리 이미지 → visibility/separability/measurability
       │
       ├─▶ [InspectionPlanAgent] ───────────────────────────────▶ InspectionPlan
       │     LLM: 검사 항목·순서·의존성 자유 설계 (inspection 모드만)
       │
       ├─▶ [AlgorithmSelector] ─────────────────────────────────▶ AlgorithmCategory
       │     Rule-based 결정 트리: BLOB/COLOR_FILTER/EDGE_DETECTION/TEMPLATE_MATCHING
       │
       ├─▶ [AlgorithmCoder (Inspection|Align)] ─────────────────▶ AlgorithmResult
       │     LLM: category + pipeline + plan → OpenCV Python 코드
       │
       ├─▶ [CodeValidator] ─────────────────────────────────────▶ ValidationResult
       │     AST parse: 문법 오류 사전 차단
       │
       ├─▶ [TestAgent (Inspection|Align)] ─────────────────────▶ list[ItemTestResult]
       │     OpenCV 실행: 실제 테스트 이미지로 메트릭 계산
       │
       ├─▶ [EvaluationAgent] ───────────────────────────────────▶ EvaluationResult
       │     Rule-based: 실패 원인 6종 분류
       │
       └─▶ 실패 시 → [FeedbackController] → 재시도 전략 결정
                 → max_iteration 초과 시 → [DecisionAgent]
                   Rule-based / Edge Learning / Deep Learning 추천
```

### 3.3 재시도 스테이지 제어

Orchestrator는 `_STAGE_ORDER` 매핑으로 부분 재시작을 지원한다. `image_analysis`는 항상 제외(1회 실행 고정)되며, 나머지 스테이지는 번호로 순서가 정해진다:

| 스테이지 | 순서 번호 |
|---------|---------|
| `pipeline_composer` | 1 |
| `parameter_searcher` | 2 |
| `inspection_plan` | 3 |
| `algorithm_selector` | 4 |
| `algorithm_coder` | 5 |

FeedbackController가 `target_agent = "parameter_searcher"`를 반환하면, 스테이지 2부터 재시작하여 이전 후보 파이프라인 목록은 재사용한다. 이를 통해 불필요한 LLM 호출을 최소화한다.

---

## 4. 에이전트 상세 설명

### 4.1 BaseAgent

**파일**: `agents/base_agent.py`  
**역할**: 모든 에이전트의 추상 기반 클래스

모든 VIA 에이전트는 `BaseAgent`를 상속한다. 핵심 인터페이스는 세 가지다:

- `execute(**kwargs)`: 추상 메서드. 에이전트별로 시그니처가 다르므로 `**kwargs`로 선언
- `set_directive(str)` / `get_directive()`: Agent Directive 텍스트를 읽고 설정
- `_log(level, message, details)`: `structlog` 기반 구조화 로그 출력

```python
class BaseAgent(ABC):
    def __init__(self, name: str, directive: Optional[str] = None) -> None: ...
    @abstractmethod
    async def execute(self, **kwargs) -> dict: ...
    def set_directive(self, directive: str) -> None: ...
    def get_directive(self) -> Optional[str]: ...
    def _log(self, level: str, message: str, details: Optional[dict] = None) -> None: ...
```

### 4.2 Orchestrator

**파일**: `agents/orchestrator.py`  
**LLM 사용**: 보조 (직접 LLM 호출 없음, 하위 에이전트 통해 간접 사용)  
**역할**: 전체 파이프라인의 제어 흐름 관리

Orchestrator의 주요 책임:
1. **지시 배포** (`_distribute_directives`): `AgentDirectives` 객체를 받아 각 에이전트에 directive를 설정
2. **목표 수치 사전 검증** (`_validate_goals`): 극단적 목표값 감지 (accuracy > 0.99, fp_rate < 0.001 등) 후 경고 생성
3. **최적 파이프라인 선택** (`_select_best_pipeline`): 후보 파이프라인들을 VisionJudge로 평가, 평균 점수(visibility + separability + measurability) / 3 최고 선택
4. **재시도 루프**: FeedbackController → 재시작 스테이지 결정 → `_run_from_stage` 반복
5. **Decision Agent 트리거**: `max_iteration` 초과 시 DecisionAgent 호출

**입력**: `purpose_text`, `analysis_images`, `test_images`, `directives`, `config`  
**출력**: `spec_result`, `diagnosis`, `best_pipeline`, `judge_result`, `inspection_plan`, `algorithm_category`, `algorithm_result`, `code_validation`, `test_results`, `evaluation_result`, `warnings`, `iteration_history`, `decision_result`

### 4.3 SpecAgent

**파일**: `agents/spec_agent.py`  
**LLM 사용**: ✓  
**역할**: 사용자 자연어 텍스트를 구조화된 검사 사양으로 변환

사용자가 "PCB 납땜 불량을 검사하고 싶다. 정확도 95% 이상, FP 5% 이하"라고 입력하면, Gemma4가 이를 파싱하여 `SpecResult`를 반환한다.

**출력 (`SpecResult`)**:
- `mode`: `InspectionMode.inspection` 또는 `InspectionMode.align`
- `goal`: 목적 요약 문자열
- `success_criteria`: `{ "accuracy": 0.95, "fp_rate": 0.05, "fn_rate": 0.05 }` 형태의 딕셔너리

### 4.4 ImageAnalysisAgent

**파일**: `agents/image_analysis_agent.py`  
**LLM 사용**: ✗ (순수 OpenCV)  
**역할**: 이미지에서 21개 진단 수치를 계산하여 `ImageDiagnosis` 반환

모든 계산이 OpenCV와 NumPy로 수행되므로 LLM 없이도 실행 가능하며, 항상 결정론적이다. 파이프라인 재시도 시 재실행하지 않는다. 상세한 계산 방식은 [5.1절](#51-imagediagnosis-21개-필드-상세)에서 설명한다.

### 4.5 PipelineComposer

**파일**: `agents/pipeline_composer.py`  
**LLM 사용**: ✗ (Rule-based)  
**역할**: ImageDiagnosis 기반으로 5가지 후보 처리 파이프라인 조합

각 파이프라인은 `ProcessingPipeline` 객체로, `PipelineBlock` 목록을 담는다. 5가지 전략:

| 전략 이름 | 설명 | 적합한 경우 |
|---------|-----|-----------|
| `적극적_노이즈제거_파이프라인` | 색상변환 + 노이즈제거(2개) + 이진화 + 형태학 | 노이즈가 많은 이미지 |
| `적응형_임계값_파이프라인` | 노이즈제거 + 적응형 이진화 + 형태학 | 조명 불균일 이미지 |
| `엣지_검출_파이프라인` | 색상변환 + 노이즈제거 + 엣지 검출 | 경계선 기반 검사 |
| `최소_전처리_파이프라인` | 이진화만 | 이미 깨끗한 이미지 |
| `형태학적_정제_파이프라인` | 색상변환 + 노이즈제거 + Otsu + 형태학(2개) | Blob 검출 위주 |

Agent Directive에 "Blob", "blob", "블롭" 키워드가 포함되면 형태학 블록을 포함한 파이프라인을 우선순위 상위로 정렬한다.

### 4.6 ParameterSearcher

**파일**: `agents/parameter_searcher.py`  
**LLM 사용**: ✗ (OpenCV)  
**역할**: 파이프라인 각 블록의 파라미터를 자동 탐색하여 최적 조합 반환

Block Library에 각 블록의 파라미터 후보 목록이 정의되어 있다. 예를 들어 `gaussian_mid`는 `sigma: [1.0, 1.5, 2.0]`의 후보를 가진다. ParameterSearcher는 이 후보 중 이미지 처리 품질 점수가 가장 높은 조합을 선택한다.

### 4.7 VisionJudgeAgent

**파일**: `agents/vision_judge_agent.py`  
**LLM 사용**: ✓ (멀티모달, Gemma4)  
**역할**: 원본 이미지와 처리 후 이미지를 Gemma4에 전송, 목적 기준 3가지 점수 평가

VisionJudge는 VIA에서 가장 독특한 에이전트다. 숫자 메트릭만으로 판단하는 것이 아니라, AI가 실제로 이미지를 "보고" 평가한다.

**평가 기준 (`JudgementResult`)**:
- `visibility_score` (0~1): 처리 후 결함/대상이 얼마나 잘 보이는가
- `separability_score` (0~1): OK와 NG를 얼마나 잘 구분할 수 있는가
- `measurability_score` (0~1): 좌표나 크기를 얼마나 정확히 측정할 수 있는가
- `problems`: 발견된 문제점 목록
- `next_suggestion`: 개선 방향 제안

**구현 상세**:
- 이미지는 최대 512×512로 다운샘플링 후 base64 PNG로 인코딩
- SHA-256 기반 캐시 (최대 50개 항목, LRU 방식) — 동일한 이미지+목적 조합 재평가 방지
- 2회 재시도 포함 파싱 로직 (JSON 펜스 제거 → json.loads)
- Intel Mac 첫 번째 멀티모달 호출은 모델 로딩으로 2분 이상 소요 가능 → `timeout=120.0`초 설정

### 4.8 InspectionPlanAgent

**파일**: `agents/inspection_plan_agent.py`  
**LLM 사용**: ✓  
**역할**: 검사 항목, 순서, 항목 간 의존성을 LLM으로 자유롭게 설계

Inspection 모드에서만 실행된다. "납땜 검사"라면 LLM이 "① 납땜 영역 존재 확인 → ② 납땜 크기 측정 → ③ 납땜 형상 이상 여부" 같은 체계적 검사 계획을 생성한다.

**출력 (`InspectionPlan`)**:
- `items`: `InspectionItem` 목록
  - `id`, `name`, `purpose`, `method` (AlgorithmCategory), `depends_on`, `safety_role`, `success_criteria`
- `mode`: `InspectionMode`

### 4.9 AlgorithmSelector

**파일**: `agents/algorithm_selector.py`  
**LLM 사용**: ✗ (결정 트리)  
**역할**: ImageDiagnosis 수치를 입력받아 최적 알고리즘 카테고리 결정

완전한 규칙 기반으로 동작하며, 결정론적이다. 결정 트리 로직은 [5.3절](#53-알고리즘-카테고리-결정-트리)에서 상세 설명한다.

### 4.10 AlgorithmCoder (Inspection / Align)

**파일**: `agents/algorithm_coder_inspection.py`, `agents/algorithm_coder_align.py`  
**LLM 사용**: ✓  
**역할**: 선택된 알고리즘 카테고리 + 최적 파이프라인 + 검사 계획을 바탕으로 실행 가능한 OpenCV Python 코드 생성

두 Coder는 별도 파일이지만 동일한 `BaseAgent`를 상속한다. Inspection Coder는 검사 항목별로 독립적인 함수를 생성하고, Align Coder는 X/Y 좌표를 반환하는 단일 함수를 생성한다.

**출력 (`AlgorithmResult`)**:
- `code`: Python 소스 코드 (즉시 `exec` 가능)
- `explanation`: 한국어 알고리즘 설명
- `category`: `AlgorithmCategory`
- `pipeline`: 사용된 `ProcessingPipeline`

### 4.11 CodeValidator

**파일**: `agents/code_validator.py`  
**LLM 사용**: ✗  
**역할**: `ast.parse()`로 생성 코드의 문법 오류를 사전 차단

TestAgent가 실행하기 전에 문법 오류가 있는 코드를 조기에 탐지한다. 유효하지 않으면 `is_valid=False`를 반환하고 `EvaluationResult`에 `algorithm_runtime_error` 원인으로 기록된다.

### 4.12 TestAgent (Inspection / Align)

**파일**: `agents/test_agent_inspection.py`, `agents/test_agent_align.py`  
**LLM 사용**: ✗ (OpenCV)  
**역할**: 생성된 코드를 실제 테스트 이미지에 실행하여 메트릭 계산

**TestAgentInspection** 출력 (`ItemTestResult` per item):
- `accuracy`: 정확도 (TP+TN / 전체)
- `fp_rate`: 오경보율 (FP / 실제 OK)
- `fn_rate`: 미검출율 (FN / 실제 NG)

**TestAgentAlign** 출력 (`ItemTestResult` per image):
- `coord_error`: 실제 좌표와 예측 좌표의 픽셀 오차 (유클리드 거리)
- `success_rate`: 오차 허용 범위 내 성공 비율

### 4.13 EvaluationAgent

**파일**: `agents/evaluation_agent.py`  
**LLM 사용**: ✗ (Rule-based)  
**역할**: 항목별 테스트 결과를 분석하여 6종 실패 원인 분류 및 전체 통과/실패 판정

상세한 실패 원인 분류 로직은 [7.1절](#71-실패-원인-6종-분류)에서 설명한다.

### 4.14 FeedbackController

**파일**: `agents/feedback_controller.py`  
**LLM 사용**: ✗ (Rule-based)  
**역할**: 실패 원인을 받아 재시도 전략 (어느 에이전트로 돌아갈지) 결정

연속 동일 실패 2회 이상 시 상위 원인으로 에스컬레이션하는 로직을 포함한다. 상세 내용은 [7.2절](#72-피드백-루프와-에스컬레이션)에서 설명한다.

### 4.15 DecisionAgent

**파일**: `agents/decision_agent.py`  
**LLM 사용**: ✓ (최종 추천 문구 생성)  
**역할**: `max_iteration` 초과 후 최종 방향 결정: Rule-based 유지 / Edge Learning 전환 / Deep Learning 전환

상세 결정 로직은 [7.3절](#73-decision-agent-결정-로직)에서 설명한다.

---

## 5. 컴퓨터 비전 기술 해설

### 5.1 ImageDiagnosis 21개 필드 상세

`ImageDiagnosis`는 VIA 비전 파이프라인의 핵심 데이터 구조다. 단 한 장의 이미지에서 21개 수치를 계산하여, 이후 모든 Rule-based 의사결정의 근거가 된다.

---

#### `contrast` (대비, float 0~1)

**계산**: 그레이스케일 이미지의 픽셀 밝기 표준편차 / 255

```python
contrast = std(gray.astype(float32)) / 255.0
```

**의미**: 이미지 내 밝은 부분과 어두운 부분의 차이. 대비가 높으면 결함이 배경과 명확히 구분된다. 동전(밝음)이 검은 컨베이어(어두움) 위에 있으면 대비가 높다. 흰 종이 위 연한 연필 자국은 대비가 낮다.

**사용**: AlgorithmSelector에서 `contrast > 0.4` → BLOB 카테고리 선택 조건

---

#### `noise_level` (노이즈 수준, float 0~1)

**계산**: 원본에서 5×5 가우시안 블러를 뺀 차이 이미지의 표준편차 / 50

```python
blurred = GaussianBlur(gray, (5,5), 0)
diff = gray - blurred
noise_level = std(diff) / 50.0
```

**의미**: 가우시안 블러는 저주파 신호(실제 구조)만 남기므로, 원본에서 뺀 것은 고주파 잡음이다. 카메라 센서 노이즈, 조명 깜박임, 진동으로 인한 흔들림 등이 노이즈로 측정된다.

**사용**:
- `noise_level < 0.2` → `gaussian_fine` 블록 선택
- `0.2 ≤ noise_level ≤ 0.5` → `gaussian_mid` 블록 선택
- `noise_level > 0.3` → `median` 블록 선택
- `noise_level > 0.6` → `nlmeans` 블록 선택 (강한 노이즈 제거)
- `noise_level > 0.2` → `erosion`, `opening` 형태학 블록 선택

---

#### `edge_density` (엣지 밀도, float 0~1)

**계산**: Canny 엣지 검출 (threshold1=50, threshold2=150) 후 엣지 픽셀 수 / 전체 픽셀 수

```python
edges = Canny(gray, 50, 150)
edge_density = count_nonzero(edges) / (height * width)
```

**의미**: 이미지에 경계선이 얼마나 많은가. PCB 기판은 회로 패턴으로 엣지가 매우 많다. 민무늬 금속 표면은 엣지가 적다. 엣지 밀도가 높을수록 구조적으로 복잡한 대상이다.

**사용**:
- `edge_density > 0.3 and structural_regularity > 0.5` → EDGE_DETECTION 카테고리
- `edge_density > 0.1` → `laplacian` 블록 선택

---

#### `lighting_uniformity` (조명 균일도, float 0~1)

**계산**: 이미지를 4×4 격자(16개 셀)로 분할, 각 셀의 평균 밝기를 구한 후 변동계수(CV)로 균일도 계산

```python
cv = std(cell_means) / mean(cell_means)
lighting_uniformity = 1.0 - cv   # 높을수록 균일
```

**의미**: 1에 가까울수록 조명이 고르게 분포. 현장에서 링 조명을 사용하면 균일도가 높고, 자연광이나 측면 조명은 그림자가 생겨 균일도가 낮다.

**사용**: `illumination_type` 계산의 전제 조건 (`uniformity > 0.85` → `uniform`)

---

#### `illumination_type` (조명 유형, `IlluminationType` enum)

**값**: `uniform` / `gradient` / `spot` / `uneven`

**계산 로직**:
1. `lighting_uniformity > 0.85` → `uniform`
2. 중앙 1/3 영역의 평균 밝기가 전체 평균보다 1.5배 이상 밝거나 0.67배 미만 → `spot`
3. 열 방향 또는 행 방향 평균의 표준편차 > 30 → `gradient`
4. 나머지 → `uneven`

**의미**:
- `uniform`: 링 조명, 백라이트 — 모든 방향에서 균등하게 조명
- `gradient`: 단방향 조명 — 한쪽이 밝고 반대쪽이 어두운 그라디언트
- `spot`: 스폿 조명 — 중앙만 밝고 주변이 어두운 집중 조명
- `uneven`: 불규칙 조명 — 위 패턴 외의 불균일 조명

**사용**:
- `uneven` → `clahe` 블록 선택 (국소 대비 향상)
- `gradient` 또는 `uneven` → `adaptive_mean`, `adaptive_gauss` 블록 선택

---

#### `noise_frequency` (노이즈 주파수 특성, `NoiseFrequency` enum)

**값**: `high_freq` / `low_freq`

**계산**: 2D 고속 푸리에 변환(FFT)으로 주파수 도메인 분석

```python
f = np.fft.fft2(gray)
magnitude = |fftshift(f)|
# 중앙(저주파) vs 외곽(고주파) 에너지 비교
r_low = min(height, width) // 8  # 저주파 반경
if high_energy > low_energy:
    return NoiseFrequency.high_freq
```

**비전 전문가가 아닌 독자를 위한 설명**:  
모든 이미지는 다양한 주파수의 패턴 합성으로 볼 수 있다. FFT는 마치 음악을 음표로 분해하는 것처럼, 이미지를 "저주파 패턴(완만한 밝기 변화)"과 "고주파 패턴(급격한 밝기 변화, 세밀한 텍스처)"으로 분해한다. 카메라 센서 노이즈는 주로 고주파이며, 조명 불균일은 저주파다.

**사용**: 파이프라인 선택 시 노이즈 제거 전략의 참고 정보

---

#### `reflection_level` (반사 수준, float 0~1)

**계산**: 밝기값 250 이상인 픽셀 비율

```python
reflection_level = count(gray >= 250) / total_pixels
```

**의미**: 금속, 유리 표면에서 조명이 강하게 반사되면 픽셀값이 포화(255 근처)된다. 반사 수준이 높으면 해당 영역에서 텍스처 정보가 손실된다. 광택 금속 부품 검사에서 중요한 지표.

**사용**:
- `reflection_level > 0.4` → `bilateral` 필터 선택 (엣지 보존하며 노이즈 제거)
- `surface_type` 분류에 사용 (glass: reflection > 0.3)

---

#### `texture_complexity` (텍스처 복잡도, float 0~1)

**계산**: Laplacian 분산 / 5000

```python
lap = Laplacian(gray, CV_64F)
texture_complexity = var(lap) / 5000.0
```

**의미**: Laplacian은 이미지의 2차 미분으로, 텍스처가 복잡할수록 값이 크다. 직물, PCB, 목재처럼 세밀한 패턴이 있는 표면은 텍스처 복잡도가 높다. 흰 플라스틱 표면은 낮다.

**사용**:
- DecisionAgent: `texture_complexity >= 0.5` → Deep Learning 권장
- `surface_type` 분류에 사용 (fabric: texture > 0.4)

---

#### `surface_type` (표면 유형, str)

**값**: `"glass"` / `"metal"` / `"pcb"` / `"fabric"` / `"plastic"` / `"unknown"`

**계산 규칙**:
```python
if reflection > 0.3 and texture < 0.3:    → "glass"
if reflection > 0.2 and texture < 0.5:    → "metal"
if edge_density > 0.2 and texture > 0.3:  → "pcb"
if texture > 0.4 and reflection < 0.1:    → "fabric"
if texture < 0.2 and reflection < 0.2:    → "plastic"
else:                                      → "unknown"
```

**사용**:
- `surface_type == "metal"` → `lab_l` 블록 선택 (L*a*b* 밝기 채널이 금속에 유리)
- `optimal_color_space` 계산에 사용

---

#### `defect_scale` (결함 규모, `DefectScale` enum)

**값**: `macro` / `micro` / `texture`

**계산 규칙**:
```python
if blob_count > 10 or blob_size_var > 0.5:  → DefectScale.micro
if blob_count > 0 and blob_size_var < 0.3:   → DefectScale.macro
if edge_density > 0.1:                        → DefectScale.texture
else:                                          → DefectScale.macro
```

**의미**:
- `macro`: 육안으로 보이는 큰 결함 — 균열, 파손, 큰 이물질
- `micro`: 미세한 결함들 — 핀홀, 미세 스크래치, 소형 파티클
- `texture`: 텍스처 레벨의 결함 — 도장 벗겨짐, 표면 거칠기 변화

**사용**:
- DecisionAgent: `micro + low texture` → Edge Learning 권장
- `defect_scale == micro` → `tophat`, `blackhat` 블록 선택 (미세 밝은/어두운 결함 강조)

---

#### `blob_feasibility` (블롭 탐지 가능성, float 0~1)

**계산**: Otsu 이진화 후 최소 면적(전체의 0.1%) 이상 윤곽선 수를 기반으로 계산

```python
# valid contours: area >= image_size * 0.001
count = len(valid_contours)
feasibility = min(count, 20) / 20.0 * 0.5 + 0.5  # 0.1~1.0 범위
```

**의미**: 이미지에서 의미 있는 블롭(독립된 덩어리)이 얼마나 탐지될 수 있는가. 볼트, 납땜, 부품처럼 배경과 구분되는 객체가 명확히 있으면 높다.

**사용**:
- `blob_feasibility > 0.6 and contrast > 0.4` → BLOB 카테고리 선택 (AlgorithmSelector)
- `blob_feasibility > 0.3` → `dilation`, `closing` 블록 선택

---

#### `blob_count_estimate` (블롭 추정 수, int)

**계산**: Otsu 이진화 후 최소 면적 이상 윤곽선의 개수

**의미**: 이미지에서 탐지 가능한 독립 객체의 예상 수. 회로 기판 위 부품들, 트레이 위 제품들의 개수 추정.

---

#### `blob_size_variance` (블롭 크기 분산, float 0~1)

**계산**: 블롭 면적들의 분산 / (이미지크기²)

**의미**: 블롭 크기가 균일한가 다양한가. 균일하면 분산이 낮다. 결함처럼 크기가 제각각이면 분산이 높다.

---

#### `color_discriminability` (색상 판별력, float 0~1)

**계산 (컬러 이미지)**: BGR 3채널 평균값 중 최대-최소 / 255  
**계산 (그레이스케일)**: Otsu 경계로 이진 분할 후 클래스 간 분산 / 전체 분산

```python
# 컬러
max_sep = max(ch_means) - min(ch_means)
color_discriminability = max_sep / 255.0

# 그레이스케일 (피셔 판별 기준)
between_var = w0 * w1 * (mu0 - mu1)^2
color_discriminability = between_var / total_var
```

**의미**: 색상으로 결함과 정상을 얼마나 잘 구분할 수 있는가. 빨간 오류 마킹 vs 흰 배경은 색상 판별력이 매우 높다. 흑백 이미지에서 두 클래스의 밝기 차이가 클수록 높다.

**사용**:
- `color_discriminability > 0.5` → COLOR_FILTER 카테고리 선택 (AlgorithmSelector)
- `color_discriminability > 0.5` → `hsv_s` 블록 선택 (채도 채널 활용)
- `color_discriminability < 0.3` → `grayscale` 블록 선택

---

#### `dominant_channel_ratio` (지배 채널 비율, float 0~1)

**계산**: 3채널 평균 중 최대값 / 3채널 평균의 합

**의미**: 특정 색상 채널이 얼마나 지배적인가. 1/3 (≈0.333)에 가까우면 세 채널이 균형 잡혀 있고, 1에 가까우면 한 채널이 압도적으로 강하다. 빨간 부품 이미지에서 R 채널 비율이 높다.

---

#### `structural_regularity` (구조적 규칙성, float 0~1)

**계산**: 이미지를 격자로 분할하여 각 패치를 16×16으로 리사이즈 후 Pearson 상관계수 평균

```python
base_patch = regions[0]
correlations = [|corr(base_patch, r)| for r in regions[1:]]
structural_regularity = mean(correlations)
```

**의미**: 이미지 각 부분의 구조가 얼마나 반복적·규칙적인가. 직조 패턴, 격자 패턴, 타일은 규칙성이 높다. 자연 물체나 결함은 불규칙하다.

**사용**:
- `structural_regularity > 0.5` → EDGE_DETECTION 카테고리 선택 조건 일부
- `structural_regularity > 0.5` → `sobel` 블록 선택

---

#### `pattern_repetition` (패턴 반복성, float 0~1)

**계산**: 이미지를 세로로 1/4, 1/3, 1/2 이동(roll) 후 자기상관 계수 최대값

```python
shifts = [h//4, h//3, h//2]
max_corr = max(|corr(norm, roll(norm, shift, axis=0))| for shift in shifts)
```

**의미**: 이미지가 주기적으로 반복되는 패턴을 가지는가. 그물망, 직물 위빙, 반복 격자 구조는 반복성이 높다. 반복 패턴이 있는 대상은 템플릿 매칭이 효과적이다.

**사용**:
- `pattern_repetition > 0.7` → TEMPLATE_MATCHING 카테고리 선택 (AlgorithmSelector)

---

#### `background_uniformity` (배경 균일도, float 0~1)

**계산**: 밝기 히스토그램의 최빈값(배경 추정) ±20 범위 픽셀들의 변동계수

```python
mode_val = argmax(histogram)
bg_pixels = gray[(gray >= mode_val-20) & (gray <= mode_val+20)]
cv = std(bg_pixels) / mean(bg_pixels)
background_uniformity = 1.0 - cv * 2
```

**의미**: 배경이 얼마나 균일한가. 배경이 균일하면 대상(결함)을 쉽게 분리할 수 있다. 배경이 복잡하면 오경보(FP)가 증가한다.

---

#### `optimal_color_space` (최적 색상 공간, str)

**값**: `"gray"` / `"hsv_s"` / `"lab_l"` / `"rgb"`

**결정 규칙**:
```python
if not is_color:                      → "gray"
if color_discriminability > 0.3:      → "hsv_s"
if surface_type in ("metal", "glass"):→ "lab_l"
else:                                  → "rgb"
```

**의미**: 이 이미지를 처리하기에 가장 적합한 색상 공간 추천. 
- `gray`: 색상 정보 없음, 그레이스케일로 처리
- `hsv_s`: 색상 차이가 명확할 때 채도(Saturation) 채널 활용
- `lab_l`: 금속·유리 표면에서 인간 시각 기준 밝기(Lightness) 채널이 효과적
- `rgb`: 특별한 색상 변환 없이 표준 RGB 처리

---

#### `threshold_candidate` (이진화 임계값 후보, float)

**계산**: Otsu 알고리즘이 자동 계산한 최적 이진화 임계값 (0~255)

**의미**: 픽셀을 "밝음(전경)"과 "어두움(배경)"으로 나누는 경계값. Otsu는 두 클래스의 분산을 최소화(클래스 내 분산)하고 클래스 간 분산을 최대화하는 값을 자동으로 찾는다. 동전(밝음)과 검은 배경을 분리하는 자동 임계값 계산과 같다.

---

#### `edge_sharpness` (엣지 선명도, float)

**계산**: Laplacian 분산값 (정규화 없음, 0~∞)

```python
lap = Laplacian(gray, CV_64F)
edge_sharpness = var(lap)  # 클수록 선명
```

**의미**: 이미지의 엣지(경계)가 얼마나 선명한가. 포커스가 맞으면 높고, 흔들리거나 초점이 안 맞으면 낮다. `texture_complexity`와 같은 계산이지만 정규화를 하지 않아 절댓값으로 사용된다.

---

### 5.2 Pipeline Block Library 21개 블록 상세

Block Library는 VIA의 전처리 레고 세트다. 각 블록은 이미지를 받아 처리된 이미지를 반환하며, `matches(diagnosis)` 조건이 참인 블록만 해당 이미지에 선택된다.

#### 색상 공간 변환 (color_space 카테고리)

| 블록 | 선택 조건 | 설명 |
|------|---------|------|
| `grayscale` | `color_discriminability < 0.3` | BGR → 그레이스케일. 색상 정보가 별로 없을 때 연산 단순화 |
| `hsv_s` | `color_discriminability > 0.5` | BGR → HSV, Saturation(채도) 채널만 추출. 색상 차이가 뚜렷할 때 색조 변화에 강건 |
| `lab_l` | `surface_type == "metal"` | BGR → L*a*b*, Lightness 채널 추출. 금속 표면 밝기 분석에 최적 |

**실제 적용 예**: 빨간 불량 마킹 vs 흰 배경 → `color_discriminability` 높음 → `hsv_s` 선택 → 채도 차이로 마킹 강조

#### 노이즈 제거 (noise_reduction 카테고리)

| 블록 | 선택 조건 | 파라미터 후보 | 설명 |
|------|---------|------------|------|
| `gaussian_fine` | `noise_level < 0.2` | sigma: [0.3, 0.5, 0.8] | 미세한 노이즈만 제거하는 부드러운 가우시안 블러 |
| `gaussian_mid` | `0.2 ≤ noise_level ≤ 0.5` | sigma: [1.0, 1.5, 2.0] | 중간 노이즈 제거. 가장 일반적인 전처리 |
| `bilateral` | `reflection_level > 0.4` | d: [5,9], sigmaColor: [25,50,75] | 엣지 보존 블러. 반사가 있는 금속/유리에서 경계선 유지하며 노이즈 제거 |
| `median` | `noise_level > 0.3` | k: [3, 5, 7] | 소금-후추 노이즈(점 형태 잡음)에 특히 효과적 |
| `nlmeans` | `noise_level > 0.6` | h: [3, 6, 10] | Non-Local Means. 이미지 구조를 최대한 보존하는 고품질 노이즈 제거. 연산 비용 높음 |
| `clahe` | `illumination_type == uneven` | clip: [1.0, 2.0, 4.0] | Contrast Limited Adaptive Histogram Equalization. 불균일 조명 이미지에서 로컬 대비 향상 |

**기초 개념 설명**:
- **가우시안 블러**: 각 픽셀을 주변 픽셀의 가중 평균으로 대체. sigma가 클수록 더 많이 흐려짐
- **bilateral 필터**: 가우시안이 경계선을 흐리게 만드는 단점 보완. 색상이 비슷한 주변 픽셀만 평균에 포함
- **median 필터**: 평균 대신 중앙값 사용. 극단적인 노이즈 픽셀의 영향을 원천 차단
- **CLAHE**: 히스토그램 평탄화를 전체 이미지가 아닌 작은 격자 구역별로 적용. 어두운 구석도 밝게 보정

#### 이진화 임계값 (threshold 카테고리)

| 블록 | 선택 조건 | 파라미터 후보 | 설명 |
|------|---------|------------|------|
| `otsu` | `contrast > 0.15` | 없음 (자동) | 밝기 히스토그램의 두 봉우리 사이 최적 경계 자동 탐색 |
| `adaptive_mean` | `illumination_type in (gradient, uneven)` | blockSize: [11, 21, 31] | 지역별 평균으로 이진화. 조명 불균일에 강건 |
| `adaptive_gauss` | `illumination_type in (gradient, uneven)` | blockSize: [11, 21, 31] | 지역별 가우시안 가중 평균으로 이진화 |

**Otsu 이진화 직관적 설명**:  
밝기 히스토그램에 두 봉우리가 있다고 상상하자 (배경=밝음, 결함=어두움). 두 봉우리 사이의 골짜기에 경계선을 그으면 가장 잘 분리된다. Otsu는 이 골짜기를 수학적으로 자동 찾는다. 마치 동전과 검은 테이블보를 찍은 사진에서 "밝은 건 동전, 어두운 건 배경"으로 나누는 최적 기준을 자동 계산하는 것이다.

**Adaptive 이진화**: 조명이 불균일하면 이미지 전체에 하나의 임계값을 적용하면 한쪽은 배경이 잘 분리되어도 다른 쪽은 그림자 때문에 실패한다. Adaptive 이진화는 이미지를 작은 블록으로 나눠 각 블록마다 지역 임계값을 계산한다.

#### 형태학적 연산 (morphology 카테고리)

| 블록 | 선택 조건 | 파라미터 후보 | 설명 |
|------|---------|------------|------|
| `erosion` | `noise_level > 0.2` | k: [3,5], iterations: [1,2,3] | 침식. 밝은 영역 축소. 노이즈 점 제거 |
| `dilation` | `blob_feasibility > 0.3` | k: [3,5], iterations: [1,2,3] | 팽창. 밝은 영역 확대. 끊긴 영역 연결 |
| `opening` | `noise_level > 0.2` | k: [3,5] | 침식 후 팽창 (erosion → dilation). 소음 점 제거하며 형상 유지 |
| `closing` | `blob_feasibility > 0.3` | k: [3,5] | 팽창 후 침식 (dilation → erosion). 작은 구멍 메우기 |
| `tophat` | `defect_scale == micro` | k: [3,5,7] | 원본 - opening. 배경보다 밝은 미세 결함 강조 |
| `blackhat` | `defect_scale == micro and contrast > 0.2` | k: [3,5,7] | closing - 원본. 배경보다 어두운 미세 결함 강조 |

**형태학 연산 직관적 설명**:  
이진화된 흑백 이미지에서 흰 픽셀을 "물질", 검은 픽셀을 "공간"이라 생각하자.
- **침식(Erosion)**: 작은 물질 덩어리를 녹여 없앤다. 노이즈로 생긴 작은 점 제거에 유용
- **팽창(Dilation)**: 물질을 부풀린다. 실금처럼 얇게 끊긴 결함을 연결하는 데 유용
- **Opening** (= 침식→팽창): 물질 형태를 유지하면서 작은 잡음을 제거. 스크래치 주변 노이즈 정리
- **Closing** (= 팽창→침식): 구멍 뚫린 영역을 메운다. 불완전하게 탐지된 결함 영역 완성
- **Top-hat**: 원본에서 Opening 결과를 빼면, 원본에는 있지만 Opening 후 사라진 것들, 즉 배경보다 밝은 미세 특징만 남는다
- **Black-hat**: Closing에서 원본을 빼면, 배경보다 어두운 미세 특징만 남는다

#### 엣지 검출 (edge 카테고리)

| 블록 | 선택 조건 | 파라미터 후보 | 설명 |
|------|---------|------------|------|
| `canny` | 항상 (무조건 매칭) | t1: [30,50,100], t2: [100,150,200] | 2단계 임계값 기반 엣지 검출의 표준 |
| `sobel` | `structural_regularity > 0.5` | ksize: [3,5] | X·Y 방향 1차 미분의 크기. 규칙적 구조에서 방향성 엣지 강조 |
| `laplacian` | `edge_density > 0.1` | ksize: [1,3,5] | 2차 미분. 엣지 방향에 무관하게 경계선 탐지 |

**Canny 엣지 검출 직관적 설명**:  
경계선은 밝기가 급격히 변하는 곳이다. Canny는 네 단계로 동작한다: ① 가우시안 블러로 노이즈 제거 → ② 기울기(Sobel) 계산으로 경계 후보 탐지 → ③ 최대값 억제(Non-Maximum Suppression)로 경계를 1픽셀 선으로 가늘게 만들기 → ④ 이중 임계값(`t1`, `t2`)으로 약한 엣지는 강한 엣지와 연결된 것만 유지. `t1 < t2`이며, 두 값 사이가 "가능한 엣지" 구간이다.

### 5.3 알고리즘 카테고리 결정 트리

AlgorithmSelector는 ImageDiagnosis의 4개 수치를 이용한 단순하지만 효과적인 결정 트리로 알고리즘 카테고리를 결정한다.

```
                          ┌─────────────────────────────────┐
                          │  ImageDiagnosis 수치 입력        │
                          └────────────────┬────────────────┘
                                           │
              contrast > 0.4              ▼
              AND blob_feasibility > 0.6?
              ┌──────────────────────────────────────┐
              │YES                                   │NO
              ▼                                      ▼
          ★ BLOB                    color_discriminability > 0.5?
    (명확한 블롭 분리)           ┌──────────────────────────────┐
                                 │YES                           │NO
                                 ▼                              ▼
                          ★ COLOR_FILTER           edge_density > 0.3 AND
                        (색상 기반 필터링)          structural_regularity > 0.5?
                                              ┌──────────────────────────────┐
                                              │YES                           │NO
                                              ▼                              ▼
                                    ★ EDGE_DETECTION         pattern_repetition > 0.7?
                                   (경계선 기반 검출)      ┌──────────────────────────┐
                                                           │YES                       │NO
                                                           ▼                          ▼
                                               ★ TEMPLATE_MATCHING          ★ BLOB (default)
                                              (반복 패턴 매칭)              (기본값)
```

**각 카테고리의 실제 적용 사례**:

| 카테고리 | 적합한 검사 | 부적합한 검사 |
|---------|-----------|------------|
| **BLOB** | 볼트 개수, 납땜 존재 여부, 이물질 탐지 | 도장 불량, 텍스처 결함 |
| **COLOR_FILTER** | 빨간 마킹 확인, 변색 감지, 색상 분류 | 형상 기반 검사 |
| **EDGE_DETECTION** | 치수 측정, 균열 탐지, PCB 패턴 확인 | 색상 기반 검사 |
| **TEMPLATE_MATCHING** | 인쇄 품질, 라벨 위치 확인, 바코드 영역 | 비정형 결함 |

---

## 6. 검사 모드 상세

### 6.1 Inspection Mode

**목적**: 이미지를 OK(정상) 또는 NG(불량)로 이진 분류

**파이프라인 특이점**:
- `InspectionPlanAgent`가 실행되어 검사 항목을 LLM으로 설계
- `AlgorithmSelector`로 카테고리 결정
- `AlgorithmCoderInspection`이 항목별 OpenCV 코드 생성
- `TestAgentInspection`이 OK/NG 이미지로 메트릭 계산

**성공 기준 (`TestMetrics`)**:
- `accuracy`: 전체 정확도 (TP+TN / 전체 테스트 이미지 수)
- `fp_rate`: 오경보율 — 정상 이미지를 불량으로 잘못 판정하는 비율
- `fn_rate`: 미검출율 — 불량 이미지를 정상으로 놓치는 비율

**산업 현장에서의 의미**: FP가 높으면 정상 제품이 폐기되어 생산성 손실. FN이 높으면 불량 제품이 출하되어 품질 문제. 제품에 따라 어떤 오류를 더 허용할지 트레이드오프가 있으며, SpecAgent가 사용자 의도를 파악해 성공 기준에 반영한다.

**출력 결과**:
- 생성된 OpenCV Python 코드 (함수 형태, 즉시 실행 가능)
- 한국어 알고리즘 설명
- 항목별 `accuracy`, `fp_rate`, `fn_rate`
- Vision Judge `visibility_score`, `separability_score`, `measurability_score`

### 6.2 Align Mode

**목적**: 이미지에서 대상 물체의 X/Y 픽셀 좌표 산출

**파이프라인 특이점**:
- `InspectionPlanAgent` 건너뜀 (정렬 모드에서는 불필요)
- `AlgorithmSelector` 건너뜀 (항상 위치 기반 알고리즘)
- `AlgorithmCoderAlign`이 단일 좌표 반환 함수 생성
- `TestAgentAlign`이 정답 좌표와 비교

**성공 기준 (`TestMetrics`)**:
- `coord_error`: 예측 좌표와 실제 좌표의 유클리드 거리 (픽셀)
- `success_rate`: `coord_error < 허용 오차` 이미지 비율

**DecisionAgent의 Align 처리**: 반복 실패 시 DecisionAgent는 Align 모드에서 항상 `rule_based`를 반환하며, "하드웨어 및 광학 장비 개선이 필요합니다"는 메시지를 출력한다. 소프트웨어 알고리즘 한계가 아닌 카메라·조명 물리적 문제임을 명시한다.

---

## 7. 피드백 루프와 자동 개선

### 7.1 실패 원인 6종 분류

`EvaluationAgent`는 테스트 결과를 분석하여 6가지 `FailureReason` 중 하나를 판정한다.

| FailureReason | 한국어 | 의미 | 우선순위 |
|-------------|-------|------|---------|
| `algorithm_runtime_error` | 알고리즘 런타임 오류 | 코드 실행 중 예외 발생 | 1 (최고) |
| `spec_issue` | 사양 문제 | 모든 항목이 실패 → 목적 추출 자체가 잘못됨 | 2 |
| `inspection_plan_issue` | 검사 계획 구조 문제 | 의존 관계 있는 항목들이 연쇄 실패 | 3 |
| `pipeline_bad_fit` | 파이프라인 부적합 | VisionJudge 점수 모두 0.4 미만 | 4 |
| `algorithm_wrong_category` | 알고리즘 카테고리 오류 | 정확도 < 0.5, FP > 0.3, FN > 0.3 동시 | 5 |
| `pipeline_bad_params` | 파이프라인 파라미터 부적합 | 위 어느 것도 아닌 일반 실패 | 6 (최저) |

**복수 원인 처리**: 여러 원인이 동시에 감지되면 우선순위가 가장 높은 원인이 선택된다. 예를 들어 `algorithm_runtime_error`와 `pipeline_bad_fit`이 같이 발생하면 `algorithm_runtime_error`가 최종 원인이 된다.

**특별 조건**:
- 모든 항목 실패(`fail_count == total`) → `spec_issue` 추가
- 3개 이상 실패 + 의존성 연쇄 실패 패턴 → `inspection_plan_issue` 추가

### 7.2 피드백 루프와 에스컬레이션

`FeedbackController`는 실패 원인을 받아 어느 에이전트로 되돌아가야 하는지 결정한다.

**기본 매핑 (`_MAPPING`)**:

| 실패 원인 | 재시작 대상 | 동작 |
|---------|-----------|-----|
| `pipeline_bad_fit` | `pipeline_composer` | 파이프라인 재구성 |
| `pipeline_bad_params` | `parameter_searcher` | 파라미터 재탐색 |
| `algorithm_wrong_category` | `algorithm_selector` | 카테고리 재선택 (미래 확장) |
| `algorithm_runtime_error` | `algorithm_coder` | 코드 재생성 |
| `inspection_plan_issue` | `inspection_plan` | 검사 계획 재설계 |
| `spec_issue` | `spec_agent` | 사양 재추출 |

**에스컬레이션 로직 (`_ESCALATION`)**:

동일한 실패 원인이 **연속 2회** 발생하면, 더 상위 원인으로 에스컬레이션한다:

```
pipeline_bad_params → (2회 연속) → pipeline_bad_fit
pipeline_bad_fit    → (2회 연속) → spec_issue
algorithm_runtime_error → (2회 연속) → algorithm_wrong_category
algorithm_wrong_category → (2회 연속) → inspection_plan_issue
```

**에스컬레이션의 의미**: 파라미터를 아무리 바꿔도 개선이 없다면, 파라미터 문제가 아니라 파이프라인 구조 자체가 잘못된 것이다. 두 번 더 파이프라인을 바꿔도 안 되면, 애초에 사용자 목적 파악이 틀렸을 수 있다.

### 7.3 Decision Agent 결정 로직

`max_iteration` 횟수를 소진한 후 최종적으로 어떤 방향으로 가야 할지 판단한다.

**결정 규칙 (순서대로 평가)**:

```
1. mode == "align"
   → rule_based (소프트웨어 한계, 하드웨어 개선 필요)

2. judge_avg >= 0.6 (VisionJudge 점수 평균이 충분히 높음)
   → rule_based (파라미터 조정 여지 남음)

3. defect_scale == "micro" AND texture_complexity < 0.3
   → edge_learning (미세하고 일관된 패턴 → EL에 적합)

4. defect_scale == "texture" OR texture_complexity >= 0.5
   → deep_learning (복잡한 텍스처 결함 → DL 필요)

5. iteration_count >= 3 AND best_accuracy < 0.5
   → deep_learning (규칙 기반 근본적 한계)

6. iteration_count >= 3 AND best_accuracy < 0.7
   → edge_learning (중간 성능 → EL로 개선 가능)

7. 기본값
   → edge_learning (불명확할 때 Edge Learning 우선 권장)
```

**결정 유형 설명**:

| DecisionType | 의미 | 권장 조건 |
|-------------|-----|---------|
| `rule_based` | 현재 규칙 기반 방식 유지 | VisionJudge 점수 양호 또는 Align 모드 |
| `edge_learning` | 소수 레이블 이미지로 학습하는 방식 (anomaly detection, few-shot) | 미세·일관 결함, 중간 정확도 |
| `deep_learning` | CNN 등 대규모 학습 | 복잡한 텍스처, 낮은 정확도, 다양한 결함 형태 |
| `hw_improvement` | 하드웨어 개선 (현재 미사용) | 예약 타입 |

---

## 8. Colab 통합

### 8.1 왜 Colab 지원이 필요한가

Intel Mac은 내장 GPU가 없어 Gemma4:e4b를 CPU로만 실행한다. 첫 번째 멀티모달 호출은 모델 로딩까지 포함해 2~3분이 걸린다. Google Colab의 T4 GPU를 사용하면 응답 속도가 약 5~10배 빨라진다. 또한 고성능 버전인 `gemma4:27b`(약 16GB)는 Colab GPU 없이는 실용적으로 실행하기 어렵다.

### 8.2 구조: cloudflared 터널

Colab 노트북은 외부에서 직접 접근할 수 없다. VIA는 Cloudflare Tunnel(cloudflared)을 통해 `localhost:11434`(Ollama)를 공개 URL(`https://*.trycloudflare.com`)로 노출한다.

```
[VIA 로컬 앱]
    │
    │ HTTP 요청
    ▼
[https://*.trycloudflare.com]  ← cloudflared가 생성한 임시 URL
    │
    │ 암호화 터널
    ▼
[Google Colab - nohup ollama serve]
    │
    ▼
[gemma4:e4b 또는 gemma4:27b 추론]
```

### 8.3 ColabNotebookGenerator

**파일**: `backend/services/colab_notebook_generator.py`  
VIA는 Colab 설정 노트북을 프로그래밍 방식으로 생성한다. 지원 모델은 `gemma4:e4b`와 `gemma4:27b`로 화이트리스트 방식으로 제한된다.

생성되는 노트북 셀 순서:
1. **Markdown**: 제목 및 사전 요구사항 (GPU 런타임 활성화 안내)
2. **Code**: Ollama 설치 (`apt-get` + 공식 설치 스크립트)
3. **Code**: Ollama 서버 시작 + 준비 완료 대기 (30초 폴링)
4. **Code**: 모델 Pull (`ollama pull gemma4:e4b`)
5. **Code**: cloudflared 설치 및 터널 시작 + URL 추출
6. **Markdown**: 다음 단계 안내 (VIA Engine Settings에 URL 붙여넣기)

### 8.4 콜드 스타트 주의사항

Colab에서 Ollama 서버와 모델이 처음 로딩되는 데 30~90초가 걸린다. 첫 번째 파이프라인 실행 전 반드시 **워밍업 요청**을 보내야 한다. 자세한 내용은 [docs/COLAB_GUIDE.md](docs/COLAB_GUIDE.md) 참조.

### 8.5 OllamaClient 동적 전환

**파일**: `backend/services/ollama_client.py`  
`OllamaClient`는 `base_url`을 런타임에 교체하는 싱글턴이다. Local 모드(`http://localhost:11434`)와 Colab 모드(사용자가 입력한 cloudflared URL)를 `/api/engine` API 호출 한 번으로 전환한다. 앱 재시작이 필요 없다.

---

## 9. UI/UX 설계 철학

### 9.1 다크 테마 전용

VIA는 다크 테마만 지원한다. 이는 미적 선호가 아닌 실용적 이유에서다:

1. **산업 현장 가시성**: 공장 라인 주변의 강한 조명 환경에서 밝은 화면은 눈의 피로를 증가시킨다
2. **이미지 색상 판단**: 검사 이미지의 색상과 밝기를 정확히 인지하려면 중립적인 어두운 배경이 필요하다
3. **집중도**: 결과 패널의 이미지와 코드에 시선이 집중되게 한다

**색상 시스템**:
- 최심층 배경: `#0a0a0a`
- 패널 배경: `#111111`
- 카드/요소: `#1a1a1a`
- 유리형 오버레이: `bg-white/5 backdrop-blur-sm border border-white/10`

### 9.2 글래스모피즘 (Glass Morphism)

반투명 배경(`bg-white/5`)과 블러(`backdrop-blur-sm`), 밝은 테두리(`border border-white/10`)를 결합하는 디자인 패턴. 깊이감 있는 UI 레이어를 만들되 복잡해 보이지 않게 한다. TailwindCSS 유틸리티 클래스로 구현하여 일관성을 유지한다.

### 9.3 6패널 레이아웃

| 패널 | 위치 | 역할 |
|------|------|------|
| **Input Panel** | 좌측 상단 | 목적 텍스트 입력 + 이미지 업로드 |
| **Directive Panel** | 좌측 중간 | 8개 에이전트별 방향성 지시 (아코디언 UI) |
| **Config Panel** | 좌측 하단 | 모드 선택 (Inspection/Align), 반복 횟수 설정 |
| **Engine Panel** | 우측 상단 | Local/Colab 전환, Colab URL 입력 |
| **Execution Panel** | 우측 중간 | 파이프라인 실행 버튼 + 진행 상태 표시 |
| **Result Panel** | 우측 하단 | 생성 코드 + 메트릭 + 파이프라인 시각화 |
| **Log Panel** | 하단 전체 | 실시간 에이전트 실행 로그 (structlog 기반) |

### 9.4 Agent Directive 시스템

사용자가 각 에이전트에 자연어 지시를 입력할 수 있는 고급 기능이다. 예를 들어:
- SpecAgent Directive: "정확도보다 미검출율(FN)을 최소화하는 방향으로 해석해주세요"
- PipelineComposer Directive: "Blob 위주로 파이프라인을 구성해주세요"
- VisionJudge Directive: "납땜 형상의 균일성을 최우선으로 평가해주세요"

`AgentDirectives` 데이터클래스는 8개 필드를 가진다: `orchestrator`, `spec`, `image_analysis`, `pipeline_composer`, `vision_judge`, `inspection_plan`, `algorithm_coder`, `test`.

### 9.5 인터랙션 일관성

모든 인터랙티브 요소에 `transition-all duration-150`을 적용하여 150ms의 일관된 전환 효과를 제공한다. 아이콘은 모두 `lucide-react` 라이브러리를 사용한다.

---

## 10. 테스트 전략

### 10.1 TDD 사이클

VIA의 모든 기능은 테스트 먼저 작성하는 원칙으로 개발되었다:

```
1. 실패하는 테스트 작성 (Red)
   - 에이전트 인터페이스 정의
   - 예상 입출력 타입 명세
   - 경계값·엣지 케이스 포함

2. 최소한의 구현 (Green)
   - 테스트를 통과하는 가장 간단한 코드
   - 중복·설계 문제 무시

3. 리팩터링 (Refactor)
   - 테스트가 그린인 상태 유지하며 코드 품질 개선
```

### 10.2 테스트 레이어

**백엔드 테스트 (pytest + anyio)**:

| 레이어 | 대상 | 특징 |
|--------|-----|------|
| 단위 테스트 | 각 에이전트 메서드 | Mock 없음, 실제 OpenCV 실행 |
| 통합 테스트 | 에이전트 간 데이터 흐름 | `@pytest.mark.integration` |
| E2E 테스트 | 전체 파이프라인 | `@pytest.mark.e2e`, 실제 Gemma4 필요 |

**비통합 테스트 실행** (Ollama 불필요):
```bash
python -m pytest tests/ -m "not integration and not e2e" -q
```

**프론트엔드 테스트 (vitest + React Testing Library)**:
- Redux slice 단위 테스트
- 컴포넌트 렌더링 및 인터랙션 테스트
- API 서비스 모킹 테스트

### 10.3 3-Gate 검증 (커밋 전)

Taeyang이 직접 수행하는 검증 게이트:

```
Gate 1: python -m pytest tests/ -m "not integration and not e2e" -q
        → 백엔드 비통합 테스트 전체 GREEN (1755개 이상)

Gate 2: cd frontend && npx vitest run --reporter=dot
        → 프론트엔드 테스트 전체 GREEN (394개 이상)

Gate 3: 앱 실행 후 골든 패스 수동 UI 확인
        → 이미지 업로드 → 파이프라인 실행 → 결과 확인
```

모든 게이트를 통과한 후에만 `git commit`을 수행한다.

### 10.4 테스트 피라미드와 커버리지

```
        /\
       /E2E\          소수 (Gemma4 필요)
      /──────\
     / 통합   \        중간 (에이전트 간 흐름)
    /──────────\
   /   단위    \      다수 (각 메서드, OpenCV 연산)
  /────────────\
```

LLM을 사용하는 에이전트(SpecAgent, InspectionPlanAgent 등)는 단위 테스트에서 Ollama를 모킹하고, E2E 테스트에서만 실제 Gemma4를 사용한다. LLM 응답의 비결정성으로 인해 E2E 테스트에서 `test_results=[]`가 반환될 수 있으며, 이는 정상 동작이다.

---

## 11. 한계와 향후 발전 방향

### 11.1 현재 한계

**이미지 입력**:
- 단일 이미지 분석 (ImageAnalysisAgent는 첫 번째 이미지만 처리)
- 테스트용 OK/NG 이미지는 수동으로 준비해야 함
- 비디오 스트리밍 지원 없음

**AI 모델**:
- Gemma4:e4b의 코드 생성 품질이 비결정적 — 동일 입력에도 실행마다 다른 코드 생성 가능
- Intel Mac CPU 환경에서 멀티모달 첫 호출 2~3분 소요
- 한국어 이해도가 영어 대비 낮을 수 있어 한국어 directive에서 품질 저하 가능

**알고리즘 범위**:
- 현재 4가지 카테고리 (BLOB, COLOR_FILTER, EDGE_DETECTION, TEMPLATE_MATCHING)
- 딥러닝 기반 검사 코드는 생성하지 않음 (Decision Agent가 추천만 함)
- 3D 비전, 깊이 정보, 스테레오 비전 미지원

**파이프라인**:
- 최대 `max_iteration`(기본 5회) 재시도 후 수동 개입 필요
- 파이프라인 블록은 21개로 고정 (동적 추가 불가)

### 11.2 향후 발전 방향

**단기 개선 (품질)**:
- 다중 이미지 동시 분석으로 더 강건한 `ImageDiagnosis` 계산
- 파라미터 탐색 알고리즘 고도화 (베이지안 최적화, 그리드 서치)
- Vision Judge 캐시 영속화 (앱 재시작 후에도 캐시 유지)

**중기 기능 확장**:
- 새로운 파이프라인 블록 추가 인터페이스 (플러그인 아키텍처)
- 생성된 알고리즘 코드의 버전 관리 및 히스토리
- 여러 검사 레시피를 저장하고 재사용하는 레시피 시스템
- Windows 지원 (현재 Intel Mac 검증)

**장기 발전 방향**:
- Edge Learning 코드 자동 생성 (anomaly detection 스켈레톤 코드)
- 실시간 카메라 스트림 연결 및 인라인 검사
- OPC UA / Modbus 등 PLC 통신 인터페이스
- 더 큰 로컬 모델 지원 (Llama 4, Mistral 등)
- 분산 멀티 카메라 검사 시스템

---

## 부록 A: 데이터 모델 전체 레퍼런스

### 주요 Enum

```python
class InspectionMode(str, Enum):
    inspection = "inspection"   # OK/NG 이진 분류
    align = "align"             # X/Y 좌표 산출

class AlgorithmCategory(str, Enum):
    BLOB = "BLOB"
    COLOR_FILTER = "COLOR_FILTER"
    EDGE_DETECTION = "EDGE_DETECTION"
    TEMPLATE_MATCHING = "TEMPLATE_MATCHING"

class FailureReason(str, Enum):
    pipeline_bad_fit = "pipeline_bad_fit"
    pipeline_bad_params = "pipeline_bad_params"
    algorithm_wrong_category = "algorithm_wrong_category"
    algorithm_runtime_error = "algorithm_runtime_error"
    inspection_plan_issue = "inspection_plan_issue"
    spec_issue = "spec_issue"

class DecisionType(str, Enum):
    rule_based = "rule_based"
    edge_learning = "edge_learning"
    deep_learning = "deep_learning"
    hw_improvement = "hw_improvement"

class DefectScale(str, Enum):
    macro = "macro"     # 육안 식별 가능한 큰 결함
    micro = "micro"     # 미세한 결함
    texture = "texture" # 텍스처 수준의 결함

class IlluminationType(str, Enum):
    uniform = "uniform"     # 균일 조명
    gradient = "gradient"   # 그라디언트 조명
    spot = "spot"           # 스폿 조명
    uneven = "uneven"       # 불규칙 조명

class NoiseFrequency(str, Enum):
    high_freq = "high_freq"  # 고주파 노이즈 (센서, 잡음)
    low_freq = "low_freq"    # 저주파 노이즈 (조명 변화)
```

### 주요 Dataclass

```python
@dataclass
class ImageDiagnosis:           # 이미지 진단 결과 (21개 필드)
    contrast: float             # 대비 [0,1]
    noise_level: float          # 노이즈 수준 [0,1]
    edge_density: float         # 엣지 밀도 [0,1]
    lighting_uniformity: float  # 조명 균일도 [0,1]
    illumination_type: IlluminationType
    noise_frequency: NoiseFrequency
    reflection_level: float     # 반사 수준 [0,1]
    texture_complexity: float   # 텍스처 복잡도 [0,1]
    surface_type: str           # 표면 유형 (glass/metal/pcb/fabric/plastic/unknown)
    defect_scale: DefectScale
    blob_feasibility: float     # 블롭 탐지 가능성 [0,1]
    blob_count_estimate: int    # 블롭 추정 수
    blob_size_variance: float   # 블롭 크기 분산 [0,1]
    color_discriminability: float  # 색상 판별력 [0,1]
    dominant_channel_ratio: float  # 지배 채널 비율 [0,1]
    structural_regularity: float   # 구조적 규칙성 [0,1]
    pattern_repetition: float      # 패턴 반복성 [0,1]
    background_uniformity: float   # 배경 균일도 [0,1]
    optimal_color_space: str       # 최적 색상 공간 (gray/hsv_s/lab_l/rgb)
    threshold_candidate: float     # Otsu 임계값 후보 [0,255]
    edge_sharpness: float          # 엣지 선명도 (비정규화)

@dataclass
class JudgementResult:              # Vision Judge 평가 결과
    visibility_score: float         # 가시성 점수 [0,1]
    separability_score: float       # 분리성 점수 [0,1]
    measurability_score: float      # 측정 가능성 점수 [0,1]
    problems: list[str]             # 발견된 문제점 목록
    next_suggestion: str            # 개선 방향 제안

@dataclass
class AgentDirectives:              # 에이전트별 방향성 지시
    orchestrator: Optional[str]
    spec: Optional[str]
    image_analysis: Optional[str]
    pipeline_composer: Optional[str]
    vision_judge: Optional[str]
    inspection_plan: Optional[str]
    algorithm_coder: Optional[str]
    test: Optional[str]
```

---

## 부록 B: 파이프라인 블록 매핑 요약

| 블록명 | 카테고리 | 선택 조건 요약 |
|--------|---------|-------------|
| `grayscale` | color_space | color_discriminability < 0.3 |
| `hsv_s` | color_space | color_discriminability > 0.5 |
| `lab_l` | color_space | surface_type == "metal" |
| `gaussian_fine` | noise_reduction | noise_level < 0.2 |
| `gaussian_mid` | noise_reduction | 0.2 ≤ noise_level ≤ 0.5 |
| `bilateral` | noise_reduction | reflection_level > 0.4 |
| `median` | noise_reduction | noise_level > 0.3 |
| `nlmeans` | noise_reduction | noise_level > 0.6 |
| `clahe` | noise_reduction | illumination_type == uneven |
| `otsu` | threshold | contrast > 0.15 |
| `adaptive_mean` | threshold | illumination_type in (gradient, uneven) |
| `adaptive_gauss` | threshold | illumination_type in (gradient, uneven) |
| `erosion` | morphology | noise_level > 0.2 |
| `dilation` | morphology | blob_feasibility > 0.3 |
| `opening` | morphology | noise_level > 0.2 |
| `closing` | morphology | blob_feasibility > 0.3 |
| `tophat` | morphology | defect_scale == micro |
| `blackhat` | morphology | defect_scale == micro AND contrast > 0.2 |
| `canny` | edge | 항상 (무조건 매칭) |
| `sobel` | edge | structural_regularity > 0.5 |
| `laplacian` | edge | edge_density > 0.1 |

---

*Copyright © 2026 TaeyangYeon. All rights reserved.*
