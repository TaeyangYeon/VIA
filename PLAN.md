# VIA (Vision Intelligence Agent)
## Master Development Plan v3.0

Intel Mac + Ollama + Gemma4 멀티모달 기반 비전 알고리즘 자동 설계 데스크톱 앱.
Argos 실패 분석 기반 전면 재설계. TDD + PCRO 워크플로우. 50 Steps / 8 Phases.

---

# Part 1. 프로젝트 개요

## 1.1 프로젝트 정보

| 항목 | 내용 |
|------|------|
| 개발 환경 | Intel Mac (x86_64) / macOS |
| AI 엔진 | Ollama + Gemma4 (gemma4:e4b) — 로컬, 멀티모달 |
| 백엔드 | FastAPI + Python 3.11 |
| 프론트엔드 | Electron + React + TypeScript + TailwindCSS + Redux Toolkit |
| 비전 라이브러리 | OpenCV + NumPy |
| 테스트 | pytest (백엔드), jest + React Testing Library (프론트엔드) |
| 개발 방식 | TDD + PCRO 프롬프트 → Claude Code 구현 → Taeyang 직접 검증 → Git 커밋 |
| 총 개발 단계 | 50 Steps / 8 Phases |

## 1.2 프로젝트 목적

이미지와 사용자 의도를 분석하여 비전 알고리즘을 자동으로 설계하는 멀티에이전트 AI 데스크톱 앱.
인터넷 없이 완전 독립 실행됨.

**출력물**
- OpenCV 코드 (즉시 실행 가능)
- 한국어 알고리즘 설명
- 테스트 메트릭 (Accuracy / 과검률 / 미검률 / 좌표 오차)
- 개선 제안 (HW 개선 / Edge Learning / Deep Learning 판단 + 근거)

**지원 모드**
- **Inspection Mode**: OK/NG 이미지 이진 분류 알고리즘 설계
- **Align Mode**: X/Y 좌표 산출 알고리즘 설계 (EL/DL 제외, HW 개선만)

## 1.3 Argos 실패 분석 및 VIA 설계 원칙

Argos는 이전에 만들었던 유사 프로젝트로 실패했다. VIA는 그 실패 원인을 구조적으로 해결한다.

| # | Argos 실패 원인 | VIA 해결 방향 |
|---|---------------|--------------|
| 1 | LLM이 알고리즘 카테고리를 단독 결정 → 엉뚱한 기법 선택 | Python 결정 트리가 카테고리 확정, LLM override 불가 |
| 2 | 고정된 검사 템플릿만 사용 (fixture → 패턴 → 검사) | Inspection Plan Agent가 검사 항목을 자유롭게 다단계 설계 |
| 3 | 이미지 처리 파이프라인 고정 (이진화→침식→가우시안 반복) | Block Library + Pipeline Composer로 자유로운 조합 |
| 4 | 처리 품질 판단이 범용 수치뿐 → 검사 목적과 무관한 평가 | Vision Judge Agent가 이미지를 직접 보고 목적 기준 판단 |

### 핵심 설계 원칙 6가지

1. **알고리즘 카테고리 선택** → Python 결정 트리 (LLM 금지)
2. **검사 항목 설계** → Inspection Plan Agent (자유로운 다단계 설계)
3. **이미지 처리 파이프라인** → Block Library + Pipeline Composer + Parameter Searcher
4. **처리 품질 판단** → Vision Judge Agent (Gemma4가 이미지 직접 시각적 판단)
5. **Gemma4 역할** → 시각적 판단 + 코드 조합만 (구조 결정 금지)
6. **사용자 개입** → Agent Directive로 에이전트별 방향성 지시 가능

---

# Part 2. 시스템 설계

## 2.1 아키텍처

```
[Desktop UI: Electron + React + Redux]
              ↓
      [FastAPI Local Server :8000]
              ↓
      [Orchestrator Agent]
              ↓
┌─────────────────────────────────────────┐
│  Spec Agent              ← Directive    │
│  Image Analysis Agent    ← Directive    │
│  Pipeline Composer       ← Directive    │
│  Vision Judge Agent      ← Directive    │
│  Inspection Plan Agent   ← Directive    │
│  Algorithm Coder Agent   ← Directive    │
│  Test Agent              ← Directive    │
│  Evaluation Agent                       │
│  Feedback Controller                    │
│  Decision Agent                         │
└─────────────────────────────────────────┘
              ↓
      [Ollama: Gemma4 e4b 멀티모달]
```

## 2.2 에이전트 구성

| 에이전트 | 역할 | LLM 사용 |
|---------|------|---------|
| Orchestrator | 전체 파이프라인 제어, Retry, 목표 수치 사전 검증 | 보조 |
| Spec Agent | 사용자 텍스트 → 모드/목표/성공기준 추출 | O |
| Image Analysis Agent | 이미지 특성 수치 + 처리 전략 진단 | X (OpenCV) |
| Pipeline Composer | Block Library로 후보 파이프라인 조합 | X (Rule-based) |
| Parameter Searcher | 각 파이프라인 파라미터 자동 탐색 | X (OpenCV) |
| Vision Judge Agent | 원본+처리 이미지 직접 보고 목적 기준 판단 | O (멀티모달) |
| Inspection Plan Agent | 검사 항목 목록/순서/의존성 자유 설계 | O |
| Algorithm Selector | 이미지 진단 수치로 알고리즘 카테고리 확정 | X (결정 트리) |
| Algorithm Coder Agent | 확정 카테고리+파이프라인으로 코드 생성 | O |
| Test Agent | 생성 코드 실행 → 항목별 메트릭 계산 | X (OpenCV) |
| Evaluation Agent | 항목별 실패 원인 분석 + 성공/실패 판정 | X (Rule-based) |
| Feedback Controller | 실패 원인별 재시도 전략 결정 | X (Rule-based) |
| Decision Agent | 최종 판단: Rule-based 유지 / EL / DL | O |

## 2.3 실행 파이프라인

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
성공 → 결과 출력
실패 → Feedback Controller → Retry
  max_iteration 초과 → Decision Agent (Rule-based 유지 / EL / DL)
```

### Failure Reason 세분화

| failure_reason | Feedback 전략 |
|---------------|--------------|
| pipeline_bad_fit | Pipeline Composer 재조합 |
| pipeline_bad_params | Parameter Searcher 재탐색 |
| algorithm_wrong_category | Algorithm Selector 재판단 |
| algorithm_runtime_error | Algorithm Coder 재생성 |
| inspection_plan_issue | Inspection Plan 재설계 |
| spec_issue | Spec Agent 재실행 |

## 2.4 핵심 컴포넌트

### 2.4.1 ImageDiagnosis

Image Analysis Agent가 OpenCV로 계산하는 이미지 진단 수치. LLM 미사용.

```python
@dataclass
class ImageDiagnosis:
    contrast: float
    noise_level: float
    edge_density: float
    lighting_uniformity: float
    illumination_type: str        # "uniform" / "gradient" / "spot" / "uneven"
    noise_frequency: str          # "high_freq" / "low_freq" (FFT 기반)
    reflection_level: float
    texture_complexity: float
    surface_type: str
    defect_scale: str             # "macro" / "micro" / "texture"
    blob_feasibility: float
    blob_count_estimate: int
    blob_size_variance: float
    color_discriminability: float
    dominant_channel_ratio: float
    structural_regularity: float
    pattern_repetition: float
    background_uniformity: float
    optimal_color_space: str
    threshold_candidate: float
    edge_sharpness: float
```

### 2.4.2 Pipeline Block Library

처리 블록과 조건 매칭 규칙. Pipeline Composer가 ImageDiagnosis를 보고 조합.

```python
PIPELINE_BLOCKS = {
    # 색공간
    "grayscale":      Block(when="color_discriminability < 0.3"),
    "hsv_s":          Block(when="color_discriminability > 0.5"),
    "lab_l":          Block(when="surface_type == 'metal'"),

    # 노이즈 제거
    "gaussian_fine":  Block(params={"sigma": [0.3, 0.5, 0.8]}, when="noise_level < 0.2"),
    "gaussian_mid":   Block(params={"sigma": [1.0, 1.5, 2.0]}, when="noise_level 0.2~0.5"),
    "bilateral":      Block(params={"d": [5,9], "sc": [25,50,75]}, when="reflection_level > 0.4"),
    "median":         Block(params={"k": [3,5,7]}, when="salt_pepper_noise"),
    "nlmeans":        Block(params={"h": [3,6,10]}, when="noise_level > 0.6"),
    "clahe":          Block(params={"clip": [1.0,2.0,4.0]}, when="illumination_type == 'uneven'"),

    # 임계값
    "otsu":           Block(when="bimodal_histogram"),
    "adaptive_mean":  Block(params={"blockSize": [11,21,31]}, when="illumination_gradient"),
    "adaptive_gauss": Block(params={"blockSize": [11,21,31]}, when="illumination_gradient"),

    # 모폴로지
    "erosion":        Block(params={"k": [3,5], "iter": [1,2,3]}, when="noise_small_objects"),
    "dilation":       Block(params={"k": [3,5], "iter": [1,2,3]}, when="fill_small_gaps"),
    "opening":        Block(when="remove_small_noise"),
    "closing":        Block(when="fill_holes"),
    "tophat":         Block(when="defect_scale == 'micro'"),
    "blackhat":       Block(when="dark_defects_on_bright"),

    # 엣지
    "canny":          Block(params={"t1": [30,50,100], "t2": [100,150,200]}),
    "sobel":          Block(when="directional_edges"),
    "laplacian":      Block(when="isotropic_edges"),
}
```

### 2.4.3 Algorithm Selector (결정 트리)

LLM이 알고리즘 카테고리를 단독 결정하지 않음. Python 결정 트리가 확정하며 override 불가.

```python
def select_algorithm_category(diagnosis: ImageDiagnosis) -> AlgorithmCategory:
    if diagnosis.contrast > 0.4 and diagnosis.blob_feasibility > 0.6:
        return BLOB
    if diagnosis.color_discriminability > 0.5:
        return COLOR_FILTER
    if diagnosis.edge_density > 0.3 and diagnosis.structural_regularity > 0.5:
        return EDGE_DETECTION
    if diagnosis.pattern_repetition > 0.7:
        return TEMPLATE_MATCHING
    return BLOB
```

### 2.4.4 Vision Judge Agent (멀티모달 핵심)

Gemma4 멀티모달로 원본 이미지 + 처리된 이미지를 직접 보고 검사 목적 기준으로 판단.
Argos가 못 했던 "검사 목적에 맞게 잘 보이는지" 판단을 담당.

**출력**: visibility_score / separability_score / measurability_score / problems / next_suggestion

### 2.4.5 Inspection Plan Agent

고정 템플릿 없이 검사 목적에 맞는 항목을 자유롭게 설계.
각 항목: id / name / purpose / method / depends_on / safety_role / success_criteria

**타공 검사 예시**:
```
항목 0: 구멍 후보 검출 (BLOB)          - 기초 검출
항목 1: 구멍 간 거리 검사 (GEOMETRIC)  - 오인식 방지  ← depends_on: [0]
항목 2: 구멍 크기 검사 (BLOB)          - 주 검사      ← depends_on: [1]
항목 3: 진원도 검사 (BLOB)             - 품질 검사    ← depends_on: [1]
항목 4: 구멍 개수 검사 (COUNT)         - 누락 검출    ← depends_on: [1,2,3]
```

### 2.4.6 Agent Directive

각 에이전트마다 사용자가 방향성 입력 가능. 입력 없으면 에이전트 자체 판단으로 진행.

```python
@dataclass
class AgentDirectives:
    orchestrator: str      # "과검 0.1% 이하를 반드시 달성해"
    spec: str
    image_analysis: str    # "반사광은 무시하고 구멍 경계에 집중"
    pipeline_composer: str # "Blob 방식 파이프라인 우선 시도"
    vision_judge: str
    inspection_plan: str   # "오인식 방지 항목을 반드시 포함해"
    algorithm_coder: str
    test: str              # "과검보다 미검을 더 엄격하게 평가"
```

### 2.4.7 Decision Agent (EL/DL 판단)

max_iteration 초과 시 최종 판단. 목표 수치(과검/미검률) 달성 불가 여부를 핵심 근거로 사용.

| 판단 | 조건 |
|------|------|
| Rule-based 유지 | Judge 점수가 임계값 근처 도달, 파라미터 탐색 여지 있음 |
| Edge Learning | 불량이 미세하고 일관된 패턴, 수십~수백장 수준 데이터 |
| Deep Learning | 불량 형태 다양/불규칙, 수천장 이상 필요 |

Align 모드는 EL/DL 없음. HW 개선만 반환.

## 2.5 디렉토리 구조

```
via/
├── backend/
│   ├── main.py
│   ├── config.py
│   ├── routers/           # images, config, directives, execute, logs, export
│   ├── services/          # ollama_client, image_store, logger
│   └── models/
├── agents/
│   ├── base_agent.py
│   ├── models.py
│   ├── orchestrator.py
│   ├── spec_agent.py
│   ├── image_analysis_agent.py
│   ├── pipeline_blocks.py
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
│   └── prompts/
├── frontend/
│   ├── main.js
│   ├── src/
│   │   ├── store/
│   │   ├── styles/
│   │   ├── services/
│   │   └── components/panels/
│   └── package.json
├── tests/
├── scripts/
├── docs/
├── VIA_MASTER_PLAN.md
├── progress.md
└── README.md
```

## 2.6 Redux Store 구조

```typescript
{
  project: { name, created_at },
  images: { analysis: [...], test: [...] },
  config: {
    mode: 'align' | 'inspection',
    max_iteration: number,
    success_criteria: { accuracy?, fp_rate?, fn_rate?, coord_error? }
  },
  directives: {
    orchestrator, spec, image_analysis, pipeline_composer,
    vision_judge, inspection_plan, algorithm_coder, test
  },
  execution: {
    status: 'idle' | 'running' | 'success' | 'failed',
    execution_id, current_agent, current_iteration,
    goal_validation, progress
  },
  result: {
    summary, pipeline, inspection_plan,
    algorithm_code, algorithm_explanation,
    metrics, item_results, improvement_suggestions,
    decision, decision_reason
  },
  logs: [{ timestamp, agent, level, message }]
}
```

---

# Part 3. 개발 규칙

## 3.1 워크플로우

```
1. VIA_MASTER_PLAN.md + progress.md 첨부
2. "STEP N 진행해줘" 요청
3. Claude가 해당 Step 내용을 보고 아래 3가지를 생성:
   ① PCRO 형식의 Claude Code 프롬프트 (영어)
   ② 직접 검증 방법 (3-Gate)
   ③ Git 커밋 메시지
4. Claude Code에 프롬프트 입력 → TDD 방식으로 구현
5. Taeyang이 직접 3-Gate 검증 수행
6. 검증 완료 후 Taeyang이 직접 Git 커밋
7. progress.md Step N 완료 표기 ([ ] → [x])
```

**원칙**
- Claude Code는 Git 커밋하지 않음
- 커밋은 Taeyang이 3-Gate 검증 완료 후 직접 수행
- 하나의 Step = 하나의 커밋

## 3.2 TDD 규칙

Claude Code가 구현한 코드가 실제로 동작하는지 테스트 결과로만 확인 가능하다.
따라서 모든 구현은 테스트 주도 방식을 따른다.

**사이클**: Red (실패하는 테스트) → Green (최소 구현) → Blue (리팩토링)

**규칙**
1. 테스트 파일을 구현 파일보다 먼저 작성
2. Claude Code는 테스트 실행 결과를 확인하면서 구현
3. 모든 테스트 GREEN 확인 후 다음 기능 진행
4. 테스트 파일이 해당 기능의 스펙 역할
5. 백엔드는 pytest, 프론트엔드는 jest + React Testing Library

**PCRO Output Format 고정 순서**
```
Step 1. Write test file first
Step 2. Run tests → confirm ALL FAIL (Red)
Step 3. Implement the feature
Step 4. Run tests → confirm ALL PASS (Green)
Step 5. Refactor if needed, confirm still GREEN
```

## 3.3 PCRO 프롬프트 규칙

"STEP N 진행해줘" 요청 시 Claude가 생성하는 프롬프트 형식.

```
## Persona
You are a [구체적인 전문가 역할].

## Context
[프로젝트 배경]
[현재까지 구현된 내용 (이전 Step 결과)]
[이번 Step에서 구현해야 할 내용]

## Restriction
- [하지 말아야 할 것들]
- Do NOT commit to git.
(UI Step의 경우 UI 디자인 규칙 추가)

## Output Format
Step 1. Write test file first
Step 2. Run tests → confirm ALL FAIL (Red)
Step 3. Implement the feature
Step 4. Run tests → confirm ALL PASS (Green)
Step 5. Refactor if needed, confirm still GREEN
- [생성해야 할 파일 목록 및 경로]
```

**규칙**
1. 프롬프트는 반드시 영어로 작성
2. Persona는 구체적인 전문가 역할 명시
3. Context에 이전 Step 결과물 명시
4. Restriction에 `Do NOT commit to git` 반드시 포함
5. Output Format에 TDD 순서 반드시 포함
6. UI Step은 Restriction에 UI 디자인 규칙 포함

## 3.4 검증 3-Gate 규칙

매 Step마다 Taeyang이 직접 확인. 3-Gate를 전부 통과해야 다음 Step 진행.

```
Gate 1 — pytest / jest
  터미널에서 직접 실행 → 전체 GREEN 확인

Gate 2 — 코드 리뷰
  구현된 코드를 Claude에게 공유하고 리뷰 요청

Gate 3 — 직접 실행 확인
  터미널 명령어 또는 UI를 직접 실행하여 동작 확인
```

Claude는 Step 내용을 보고 Gate별 구체적인 명령어와 기대 결과를 제공한다.

## 3.5 Git 커밋 규칙

**형식**
```
<type>: <영어 제목>

<한국어 본문>

- 완료 항목 1
- 완료 항목 2
```

**Type**

| type | 용도 |
|------|------|
| feat | 새 기능 추가 |
| fix | 버그 수정 |
| test | 테스트 추가/수정 |
| refactor | 리팩토링 |
| docs | 문서 수정 |
| chore | 빌드/설정 변경 |

## 3.6 UI 디자인 규칙

VIA는 외부 서비스로 공개 가능한 수준의 UI 품질을 목표로 한다.
Phase 6 (Step 32~40)의 모든 UI 구현은 아래 규칙을 따른다.

### 색상 시스템 (Neutral Black/Gray 전용)

```
배경
  최상위:     #0a0a0a  (거의 블랙)
  카드/패널:  #111111  (다크 그레이)
  보조 패널:  #1a1a1a  (미디엄 다크)
  호버/선택:  #222222  (라이트 다크)

경계선
  기본:       #2a2a2a
  강조:       #3a3a3a

텍스트
  주요:       #f5f5f5  (거의 화이트)
  보조:       #a0a0a0  (미디엄 그레이)
  비활성:     #555555  (다크 그레이)

강조색 (단 하나의 포인트 컬러만 사용)
  주요 액션:  #ffffff  (화이트)
  성공:       #4ade80  (그린)
  경고:       #facc15  (옐로우)
  오류:       #f87171  (레드)
  정보:       #60a5fa  (블루, 최소화)
```

**금지**: 파랑/퍼플/그린 계열의 다크 테마 배경 사용 금지.

### 디자인 패턴

- **Glass Morphism**: `bg-white/5 backdrop-blur-sm border border-white/10`
- **Micro Interaction**: 모든 인터랙션에 `transition-all duration-150`
- **Typography**: Inter 또는 시스템 sans-serif, 코드는 JetBrains Mono
- **Spacing**: 8px 그리드 (4, 8, 12, 16, 24, 32, 48px)
- **Icon**: lucide-react 통일

### 컴포넌트 스타일

```
Button Primary    bg-white text-black hover:bg-gray-100
Button Secondary  bg-white/10 text-white hover:bg-white/20 border border-white/20
Button Danger     bg-red-500/20 text-red-400 hover:bg-red-500/30
Card              bg-white/5 border border-white/10 rounded-xl
Input             bg-white/5 border border-white/10 focus:border-white/30
Badge Success     bg-green-500/20 text-green-400
Badge Warning     bg-yellow-500/20 text-yellow-400
Badge Error       bg-red-500/20 text-red-400
```

### UI 품질 기준

- 외부 서비스로 공개해도 부끄럽지 않은 수준
- 모든 인터랙션에 transition 적용
- 빈 상태(Empty State) / 로딩 상태 / 에러 상태 UI 구현 필수

### UI Step PCRO Restriction 템플릿

```
- Use ONLY neutral black/gray dark theme (NO blue/purple/green backgrounds)
- Apply glass morphism for cards: bg-white/5 backdrop-blur border border-white/10
- All interactive elements must have transition-all duration-150
- Use lucide-react for all icons
- Implement empty/loading/error states for every component
- UI quality must be production-ready
- Do NOT commit to git.
```

---

# Part 4. 50단계 개발 계획

## 4.1 Phase 개요

| Phase | 이름 | Steps | 산출물 |
|-------|------|-------|--------|
| 1 | 환경 설정 | 1-4 | Python, Ollama + Gemma4 멀티모달 검증 |
| 2 | 백엔드 기반 | 5-10 | FastAPI, 이미지 API, Directive API, 멀티모달 클라이언트 |
| 3 | 이미지 처리 레이어 | 11-17 | Image Analysis, Block Library, Composer, Vision Judge |
| 4 | 검사 설계 레이어 | 18-24 | Inspection Plan, Algorithm Selector, Coder, Test, 정적검증 |
| 5 | 평가 & 피드백 루프 | 25-31 | Evaluation, Feedback, Decision, Orchestrator |
| 6 | 프론트엔드 | 32-40 | Electron + React UI (UI 디자인 규칙 적용) |
| 7 | 통합 & E2E | 41-46 | E2E 테스트, 최적화 |
| 8 | 패키징 & 배포 | 47-50 | DMG/NSIS 패키징, 배포 준비 |

---

## Phase 1: 환경 설정

### Step 1 — Python 환경 초기화
- **작업 내용**: pyenv + Python 3.11 설치 및 가상환경 구성. requirements.txt 초안
- **생성 파일**: `pyproject.toml`, `requirements.txt`, `.python-version`
- **검증 포인트**: Python 버전 확인, import 동작 확인

### Step 2 — OpenCV + NumPy 설치 및 검증
- **작업 내용**: opencv-python-headless, numpy 설치. Intel Mac x86_64 호환성 검증
- **생성 파일**: `requirements.txt` 업데이트, `tests/test_opencv.py`
- **검증 포인트**: import 확인, 기본 이미지 로드/저장 동작 확인

### Step 3 — Ollama 설치 및 Gemma4 Pull + 멀티모달 검증
- **작업 내용**: Ollama 설치. gemma4:e4b pull. ollama serve 스크립트. 멀티모달 이미지 입력 동작 검증
- **생성 파일**: `scripts/start_ollama.sh`, `tests/test_ollama_multimodal.py`
- **검증 포인트**: 텍스트 응답 확인, 이미지 입력 후 설명 응답 확인

### Step 4 — 프로젝트 디렉토리 구조 및 Git 초기화
- **작업 내용**: 전체 폴더 구조 생성. .gitignore, README.md, progress.md 초기화
- **생성 파일**: 전체 디렉토리, `.gitignore`, `README.md`, `progress.md`
- **검증 포인트**: 디렉토리 구조 확인

---

## Phase 2: 백엔드 기반

### Step 5 — FastAPI 프로젝트 초기화
- **작업 내용**: fastapi, uvicorn 설치. /health 엔드포인트. CORS 미들웨어
- **생성 파일**: `backend/main.py`, `backend/config.py`, `tests/test_api_health.py`
- **검증 포인트**: /health 응답 확인

### Step 6 — 이미지 업로드 API + 검증 로직
- **작업 내용**: POST /api/images/upload. OK_N.png / NG_N.png 검증. Analysis/Test 분류 저장
- **생성 파일**: `backend/routers/images.py`, `backend/services/image_validator.py`, `tests/test_image_upload.py`
- **검증 포인트**: 유효/무효 파일명 처리 확인

### Step 7 — 이미지 저장소 관리 서비스
- **작업 내용**: 메타데이터 관리. GET /api/images, DELETE /api/images/{id}
- **생성 파일**: `backend/services/image_store.py`, `tests/test_image_store.py`
- **검증 포인트**: CRUD 전체 동작 확인

### Step 8 — 실행 설정 API + Agent Directive API
- **작업 내용**: POST /api/config, POST /api/directives. 극단 목표 수치 경고 로직
- **생성 파일**: `backend/routers/config.py`, `backend/routers/directives.py`, `tests/test_config_api.py`
- **검증 포인트**: 설정 저장/조회, 극단 목표 경고 확인

### Step 9 — 로깅 시스템 구현
- **작업 내용**: structlog 기반 에이전트별 로그. GET /api/logs
- **생성 파일**: `backend/services/logger.py`, `backend/routers/logs.py`, `tests/test_logger.py`
- **검증 포인트**: 로그 파일 생성 및 API 조회 확인

### Step 10 — Ollama 클라이언트 서비스 (멀티모달 지원)
- **작업 내용**: httpx 기반 Ollama 래퍼. 이미지 base64 멀티모달 요청. 타임아웃/재시도
- **생성 파일**: `backend/services/ollama_client.py`, `tests/test_ollama_client.py`
- **검증 포인트**: 텍스트 + 이미지 포함 멀티모달 요청 동작 확인

---

## Phase 3: 이미지 처리 레이어

### Step 11 — Agent 기본 인터페이스 + 전체 모델 정의
- **작업 내용**: BaseAgent 추상 클래스. ImageDiagnosis, InspectionPlan, JudgementResult, AgentDirectives, ProcessingPipeline 데이터 클래스
- **생성 파일**: `agents/base_agent.py`, `agents/models.py`, `tests/test_models.py`
- **검증 포인트**: 모든 모델 import 및 인스턴스 생성 확인

### Step 12 — Spec Agent 구현
- **작업 내용**: 사용자 텍스트 → mode/목표/성공기준 추출. Agent Directive 반영
- **생성 파일**: `agents/spec_agent.py`, `agents/prompts/spec_prompt.py`, `tests/test_spec_agent.py`
- **검증 포인트**: 다양한 입력 파싱 결과 확인

### Step 13 — Image Analysis Agent 구현 (ImageDiagnosis 전체)
- **작업 내용**: OpenCV로 ImageDiagnosis 전체 수치 계산. 조명 타입, 노이즈 주파수(FFT), Blob 가능성 등
- **생성 파일**: `agents/image_analysis_agent.py`, `tests/test_image_analysis.py`
- **검증 포인트**: 샘플 이미지로 각 수치 출력 확인

### Step 14 — Pipeline Block Library 구현
- **작업 내용**: 모든 처리 블록 정의. 조건 매칭 로직. 파라미터 탐색 범위
- **생성 파일**: `agents/pipeline_blocks.py`, `tests/test_pipeline_blocks.py`
- **검증 포인트**: ImageDiagnosis 조건별 블록 매칭 결과 확인

### Step 15 — Pipeline Composer 구현
- **작업 내용**: ImageDiagnosis + Block Library → 후보 파이프라인 3~5개 생성. Directive 반영
- **생성 파일**: `agents/pipeline_composer.py`, `tests/test_pipeline_composer.py`
- **검증 포인트**: 후보 파이프라인 생성 확인

### Step 16 — Parameter Searcher + ProcessingQualityEvaluator
- **작업 내용**: 파라미터 자동 탐색. ProcessingQualityEvaluator로 빠른 필터링
- **생성 파일**: `agents/parameter_searcher.py`, `agents/processing_quality_evaluator.py`, `tests/test_parameter_searcher.py`
- **검증 포인트**: 탐색 후 최적 파라미터 출력 확인

### Step 17 — Vision Judge Agent 구현 (멀티모달 핵심)
- **작업 내용**: Gemma4에게 원본+처리 이미지 2장 직접 전달. 가시성/분리도/측정가능성 점수화. 문제점+개선 방향. Directive 반영
- **생성 파일**: `agents/vision_judge_agent.py`, `agents/prompts/vision_judge_prompt.py`, `tests/test_vision_judge.py`
- **검증 포인트**: 좋은 vs 나쁜 처리 판별, 개선 제안 출력 확인

---

## Phase 4: 검사 설계 레이어

### Step 18 — Inspection Plan Agent 구현
- **작업 내용**: 검사 목적 → 자유로운 검사 항목 설계. depends_on, safety_role 포함. 고정 템플릿 없음
- **생성 파일**: `agents/inspection_plan_agent.py`, `agents/prompts/inspection_plan_prompt.py`, `tests/test_inspection_plan.py`
- **검증 포인트**: 다른 목적으로 다른 항목 구성 확인

### Step 19 — Algorithm Selector 구현 (결정 트리)
- **작업 내용**: ImageDiagnosis 수치 기반 Python 결정 트리. LLM override 불가
- **생성 파일**: `agents/algorithm_selector.py`, `tests/test_algorithm_selector.py`
- **검증 포인트**: 다양한 진단 수치로 카테고리 선택 확인

### Step 20 — Algorithm Coder Agent 구현 (Inspection)
- **작업 내용**: 확정 카테고리+파이프라인+검사 항목 → 항목별 OpenCV 코드 생성. 한국어 설명
- **생성 파일**: `agents/algorithm_coder_inspection.py`, `agents/prompts/coder_inspection_prompt.py`, `tests/test_coder_inspection.py`
- **검증 포인트**: 생성 코드 문법 및 실행 가능 여부 확인

### Step 21 — Algorithm Coder Agent 구현 (Align)
- **작업 내용**: Align Fallback 체인 (Template → Edge → Caliper). X/Y 좌표 출력 고정. EL/DL 금지
- **생성 파일**: `agents/algorithm_coder_align.py`, `agents/prompts/coder_align_prompt.py`, `tests/test_coder_align.py`
- **검증 포인트**: Fallback 체인 및 X/Y 좌표 출력 형식 확인

### Step 22 — Test Agent 구현 (Inspection, 항목별)
- **작업 내용**: InspectionPlan 항목별 코드 실행. 항목별 Accuracy/FP/FN. depends_on 순서 준수. Directive 반영
- **생성 파일**: `agents/test_agent_inspection.py`, `tests/test_test_agent_inspection.py`
- **검증 포인트**: 항목별 메트릭 및 의존성 순서 확인

### Step 23 — Test Agent 구현 (Align)
- **작업 내용**: Align 코드 실행. 좌표 오차/성공률 계산
- **생성 파일**: `agents/test_agent_align.py`, `tests/test_test_agent_align.py`
- **검증 포인트**: 좌표 오차 및 성공률 출력 확인

### Step 24 — 코드 정적 검증 레이어
- **작업 내용**: ast.parse() 문법 검증. import 가능 여부. 함수 시그니처 검증
- **생성 파일**: `agents/code_validator.py`, `tests/test_code_validator.py`
- **검증 포인트**: 유효/무효 코드 검증 동작 확인

---

## Phase 5: 평가 & 피드백 루프

### Step 25 — Evaluation Agent 구현 (항목별 세분화)
- **작업 내용**: 항목별 실패 원인 분석. failure_reason 6가지 세분화
- **생성 파일**: `agents/evaluation_agent.py`, `tests/test_evaluation_agent.py`
- **검증 포인트**: 각 failure_reason 경계 케이스 확인

### Step 26 — Feedback Controller 구현
- **작업 내용**: failure_reason별 재시도 전략. Vision Judge 피드백 반영. 실패 컨텍스트 누적
- **생성 파일**: `agents/feedback_controller.py`, `tests/test_feedback_controller.py`
- **검증 포인트**: 전략 선택 및 컨텍스트 누적 확인

### Step 27 — Decision Agent 구현 (EL/DL 판단)
- **작업 내용**: EL/DL/Rule-based 최종 판단. 목표 수치 달성 불가 여부를 핵심 근거로 사용. Align 모드는 HW 개선만
- **생성 파일**: `agents/decision_agent.py`, `tests/test_decision_agent.py`
- **검증 포인트**: 각 판단 시나리오 및 근거 출력 확인

### Step 28 — Orchestrator 구현 (기본 파이프라인)
- **작업 내용**: 전체 파이프라인 순차 실행. 목표 수치 사전 검증. Directive 각 에이전트 전달
- **생성 파일**: `agents/orchestrator.py`, `tests/test_orchestrator_basic.py`
- **검증 포인트**: 에이전트 실행 순서 및 Directive 전달 확인

### Step 29 — Orchestrator Retry 로직
- **작업 내용**: failure_reason별 재시도 분기. max_iteration 제한
- **생성 파일**: `agents/orchestrator.py` 확장, `tests/test_orchestrator_retry.py`
- **검증 포인트**: 각 failure_reason별 재시도 경로 확인

### Step 30 — Orchestrator → Decision Agent 연결
- **작업 내용**: max_iteration 초과 시 Decision Agent 호출. 전체 실행 이력 요약
- **생성 파일**: `agents/orchestrator.py` 확장, `tests/test_orchestrator_decision.py`
- **검증 포인트**: 반복 실패 시 Decision Agent 호출 확인

### Step 31 — 파이프라인 실행 API (POST /api/execute)
- **작업 내용**: POST /api/execute. 비동기 실행. execution_id 발급. 상태 조회/취소
- **생성 파일**: `backend/routers/execute.py`, `backend/services/execution_manager.py`, `tests/test_execute_api.py`
- **검증 포인트**: 비동기 실행 및 상태 폴링 동작 확인

---

## Phase 6: 프론트엔드

> 이 Phase의 모든 Step은 **Part 3.6 UI 디자인 규칙**을 반드시 준수한다.
> PCRO 프롬프트 생성 시 UI Restriction 템플릿이 자동으로 포함된다.

### Step 32 — Electron 프로젝트 초기화
- **작업 내용**: electron, electron-builder 설치. main.js 기본 구조. BrowserWindow 생성
- **생성 파일**: `frontend/main.js`, `frontend/package.json`
- **검증 포인트**: Electron 윈도우 팝업 직접 확인

### Step 33 — React + TypeScript + TailwindCSS + 디자인 시스템 설정
- **작업 내용**: Vite + React + TypeScript. TailwindCSS black/gray 다크 테마. 디자인 토큰 정의. lucide-react 설치
- **생성 파일**: `frontend/src/App.tsx`, `frontend/tailwind.config.js`, `frontend/src/styles/design-tokens.ts`, `frontend/vite.config.ts`
- **검증 포인트**: 다크 배경(#0a0a0a) 렌더링 직접 확인

### Step 34 — Redux Store 초기화 (directives slice 포함)
- **작업 내용**: 7개 slice (project, images, config, directives, execution, result, logs)
- **생성 파일**: `frontend/src/store/index.ts`, `frontend/src/store/slices/*.ts`
- **검증 포인트**: Redux DevTools에서 7개 slice 확인

### Step 35 — API 클라이언트 서비스
- **작업 내용**: axios 인스턴스. 각 API 함수화. Directive API 포함. TypeScript 타입
- **생성 파일**: `frontend/src/services/api.ts`, `frontend/src/services/types.ts`
- **검증 포인트**: 실제 API 호출 동작 확인

### Step 36 — 전체 레이아웃 + Input Panel (이미지 업로드)
- **작업 내용**: Sidebar + Main Workspace. 드래그&드롭 업로드. OK/NG 파일명 검증. 썸네일
- **생성 파일**: `frontend/src/components/Layout.tsx`, `frontend/src/components/panels/InputPanel.tsx`
- **검증 포인트**: 기능 동작 + UI 품질 (글래스모피즘, 트랜지션) 확인

### Step 37 — Directive Panel UI
- **작업 내용**: 각 에이전트 카드마다 선택적 텍스트 입력란. 빈 값 = 자동 판단. 접기/펼치기
- **생성 파일**: `frontend/src/components/panels/DirectivePanel.tsx`
- **검증 포인트**: 8개 에이전트 카드 + UI 품질 확인

### Step 38 — Config Panel + Execution Panel
- **작업 내용**: 모드 토글. 성공 기준 폼. 극단 목표 경고. 실행 시작/중지. 에이전트별 진행 상태
- **생성 파일**: `frontend/src/components/panels/ConfigPanel.tsx`, `frontend/src/components/panels/ExecutionPanel.tsx`
- **검증 포인트**: 기능 동작 + 로딩/에러 상태 UI 확인

### Step 39 — Result Panel (코드 뷰어 + 메트릭 + 파이프라인 시각화)
- **작업 내용**: 코드 신택스 하이라이팅. 파이프라인 블록 흐름도. 항목별 검사 결과. 차트. Decision 강조
- **생성 파일**: `frontend/src/components/panels/ResultPanel.tsx`, `frontend/src/components/MetricsChart.tsx`, `frontend/src/components/PipelineViewer.tsx`
- **검증 포인트**: 기능 동작 + 시각화 완성도 확인

### Step 40 — 로그 패널 + 전체 UI-API 연동 통합 테스트
- **작업 내용**: 에이전트별 색상 구분 로그. 실시간 폴링. E2E 수동 테스트. 전체 UI 디자인 일관성 최종 점검
- **생성 파일**: `frontend/src/components/LogPanel.tsx`, `tests/e2e/test_ui_api_integration.md`
- **검증 포인트**: 전체 흐름 + UI 일관성 확인

---

## Phase 7: 통합 & E2E

### Step 41 — Inspection 전체 파이프라인 E2E 테스트
- **작업 내용**: Vision Judge + Inspection Plan + 항목별 검사 전체 흐름. 실제 Gemma4 멀티모달 호출 포함
- **생성 파일**: `tests/e2e/test_inspection_pipeline.py`, `tests/fixtures/sample_images/`
- **검증 포인트**: 에이전트별 출력 로그 및 최종 결과 확인

### Step 42 — Align 전체 파이프라인 E2E 테스트
- **작업 내용**: Align 모드 전체 흐름. Fallback 체인 동작 확인
- **생성 파일**: `tests/e2e/test_align_pipeline.py`
- **검증 포인트**: Fallback 단계별 진입 로그 및 좌표 출력 확인

### Step 43 — Agent Directive E2E 테스트
- **작업 내용**: Directive 입력 후 동작 변화 확인. 빈 Directive 자동 판단 확인
- **생성 파일**: `tests/e2e/test_directive_e2e.py`
- **검증 포인트**: Directive 있음/없음 시나리오 비교

### Step 44 — 성능 최적화 (Vision Judge 응답 속도)
- **작업 내용**: Vision Judge 이미지 다운샘플링. 캐싱. 타임아웃 튜닝
- **생성 파일**: `agents/vision_judge_agent.py` 최적화, `tests/test_performance.py`
- **검증 포인트**: 응답 시간 측정 및 기준 달성 확인

### Step 45 — 에러 처리 강화 + 결과 내보내기
- **작업 내용**: 에이전트별 예외 처리. UI 에러 표시. 결과 JSON + .py 코드 내보내기
- **생성 파일**: `backend/services/error_handler.py`, `backend/routers/export.py`, `frontend/src/components/ExportButton.tsx`
- **검증 포인트**: 에러 시나리오 및 내보낸 파일 확인

### Step 46 — Retry 및 Decision 시나리오 통합 테스트
- **작업 내용**: 의도적 실패. 목표 수치 미달 → Decision 흐름
- **생성 파일**: `tests/e2e/test_retry_decision.py`
- **검증 포인트**: Retry 경로 및 EL/DL 판단 근거 출력 확인

---

## Phase 8: 패키징 & 배포

### Step 47 — FastAPI 자동 시작 + Ollama 멀티모달 상태 확인
- **작업 내용**: Electron 시작 시 FastAPI 자동 실행. Gemma4 멀티모달 가용 여부 확인. 미설치 안내
- **생성 파일**: `frontend/main.js` 확장, `frontend/src/components/OllamaSetupGuide.tsx`
- **검증 포인트**: 앱 시작 시 서버 자동 실행 및 Ollama 안내 확인

### Step 48 — macOS DMG + Windows NSIS 패키징
- **작업 내용**: electron-builder macOS Intel x86_64 DMG. Windows NSIS
- **생성 파일**: `frontend/electron-builder.yml`, `build/icons/`
- **검증 포인트**: DMG 생성 및 설치 후 앱 실행 확인

### Step 49 — 전체 최종 통합 테스트
- **작업 내용**: 패키징된 앱으로 Inspection/Align/Directive/Decision 전체 시나리오
- **생성 파일**: `tests/e2e/test_final_integration.md`
- **검증 포인트**: 5개 시나리오 전체 실행 확인

### Step 50 — 문서화 완성 + 최종 Git 커밋
- **작업 내용**: README.md 완성. 설치 가이드. progress.md 전체 완료. .env.example
- **생성 파일**: `README.md`, `docs/INSTALL.md`, `progress.md`, `.env.example`
- **검증 포인트**: 문서 내용 및 최종 빌드 확인

---