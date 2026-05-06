"""Step 45: E2E Integration Tests — Align Full Pipeline.

All integration tests marked @pytest.mark.integration and @pytest.mark.e2e.
Async tests use @pytest.mark.anyio (NOT asyncio).
Tests requiring Ollama are skipped automatically when Ollama / gemma4:e4b is unavailable.
"""
from __future__ import annotations

import ast
import asyncio
import os
import time
from pathlib import Path

import cv2
import httpx
import numpy as np
import pytest

from agents.algorithm_coder_align import AlgorithmCoderAlign
from agents.algorithm_coder_inspection import AlgorithmCoderInspection
from agents.algorithm_selector import AlgorithmSelector
from agents.code_validator import CodeValidator, ValidationResult
from agents.decision_agent import DecisionAgent
from agents.evaluation_agent import EvaluationAgent
from agents.feedback_controller import FeedbackController
from agents.image_analysis_agent import ImageAnalysisAgent
from agents.inspection_plan_agent import InspectionPlanAgent
from agents.models import (
    AlgorithmCategory,
    AlgorithmResult,
    DecisionResult,
    DecisionType,
    EvaluationResult,
    ImageDiagnosis,
    InspectionMode,
    ItemTestResult,
    JudgementResult,
    ProcessingPipeline,
    SpecResult,
)
from agents.orchestrator import Orchestrator
from agents.parameter_searcher import ParameterSearcher
from agents.pipeline_composer import PipelineComposer
from agents.spec_agent import SpecAgent
from agents.test_agent_align import TestAgentAlign
from agents.test_agent_inspection import TestAgentInspection
from agents.vision_judge_agent import VisionJudgeAgent
from backend.services.ollama_client import OllamaClient

_FIXTURES_DIR = Path(__file__).parent.parent / "fixtures" / "sample_images"
OLLAMA_BASE_URL = os.environ.get("VIA_OLLAMA_URL", "http://localhost:11434")
_MODEL = "gemma4:e4b"
_ALIGN_PURPOSE = (
    "마크 정렬 검사: 이미지에서 밝은 원형 마크의 중심 좌표를 검출하고, "
    "align(image) 형식으로 x, y, confidence, method_used를 반환하는 알고리즘을 설계하라."
)

_ALIGN_IMAGE_FILENAMES = [
    "X_320.0_Y_240.0_1.png",
    "X_160.0_Y_120.0_2.png",
    "X_480.0_Y_360.0_3.png",
    "X_250.5_Y_200.5_4.png",
]


# ── anyio backend ─────────────────────────────────────────────────────────────

@pytest.fixture(params=["asyncio"])
def anyio_backend(request):
    return request.param


# ── Session fixtures ──────────────────────────────────────────────────────────

@pytest.fixture(scope="session")
def check_ollama_available():
    """Skip dependent tests if Ollama / gemma4:e4b is not reachable."""
    from backend.services.ollama_client import ollama_client as _singleton

    print(f"\n[E2E] Using Ollama at: {OLLAMA_BASE_URL}")
    asyncio.run(_singleton.set_base_url(OLLAMA_BASE_URL))
    try:
        resp = httpx.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=10.0)
        if resp.status_code != 200:
            pytest.skip("Ollama not running")
        models = resp.json().get("models", [])
        if not any(m["name"].startswith(_MODEL) for m in models):
            pytest.skip(f"{_MODEL} not available in Ollama")
    except Exception as exc:
        pytest.skip(f"Ollama not reachable: {exc}")

    print(f"\n[E2E] Warming up {_MODEL} (cold-start GPU load, up to 600s)...")
    try:
        warmup = httpx.post(
            f"{OLLAMA_BASE_URL}/api/generate",
            json={"model": _MODEL, "prompt": "Say OK", "stream": False},
            timeout=600.0,
        )
        print(f"[E2E] Warmup complete: status={warmup.status_code}")
    except Exception as exc:
        print(f"[E2E] Warmup failed (non-fatal): {exc}")

    return True


@pytest.fixture
def real_ollama_client() -> OllamaClient:
    """OllamaClient tuned for Intel Mac slow first-inference (function-scoped for loop safety)."""
    return OllamaClient(
        base_url=OLLAMA_BASE_URL,
        model=_MODEL,
        health_timeout=300.0,
        generate_timeout=600.0,
        max_retries=2,
    )


@pytest.fixture(autouse=True)
def reset_singleton_client():
    """Reset module-level ollama_client singleton before each test for anyio event loop safety."""
    from backend.services.ollama_client import ollama_client as _singleton
    _singleton._client = None
    yield
    _singleton._client = None


@pytest.fixture(scope="session")
def align_images() -> dict[str, np.ndarray]:
    """Load all 4 synthetic align images keyed by filename."""
    images: dict[str, np.ndarray] = {}
    for fname in _ALIGN_IMAGE_FILENAMES:
        path = _FIXTURES_DIR / fname
        img = cv2.imread(str(path), cv2.IMREAD_GRAYSCALE)
        assert img is not None, f"Failed to load {path}"
        images[fname] = img
    return images


# ── Helpers ───────────────────────────────────────────────────────────────────

def create_real_orchestrator(ollama_client: OllamaClient | None = None) -> Orchestrator:
    """Instantiate all 15 agents + Orchestrator with real OllamaClient."""
    return Orchestrator(
        spec_agent=SpecAgent(),
        image_analysis_agent=ImageAnalysisAgent(),
        pipeline_composer=PipelineComposer(),
        parameter_searcher=ParameterSearcher(),
        vision_judge_agent=VisionJudgeAgent(),
        inspection_plan_agent=InspectionPlanAgent(),
        algorithm_selector=AlgorithmSelector(),
        algorithm_coder_inspection=AlgorithmCoderInspection(ollama_client=ollama_client),
        algorithm_coder_align=AlgorithmCoderAlign(ollama_client=ollama_client),
        code_validator=CodeValidator(),
        test_agent_inspection=TestAgentInspection(),
        test_agent_align=TestAgentAlign(),
        evaluation_agent=EvaluationAgent(),
        feedback_controller=FeedbackController(),
        decision_agent=DecisionAgent(),
    )


def log_agent_output(agent_name: str, output: object) -> None:
    print(f"\n[{agent_name}] {type(output).__name__}: {output}")


# ── Test 1 (no Ollama) ────────────────────────────────────────────────────────

class TestAlignImagesValid:
    def test_align_images_are_valid(self, align_images: dict[str, np.ndarray]) -> None:
        """Verify all 4 align synthetic images have correct shape, dtype, and bright features."""
        assert set(align_images.keys()) == set(_ALIGN_IMAGE_FILENAMES)

        for fname, img in align_images.items():
            assert isinstance(img, np.ndarray), f"{fname}: not ndarray"
            assert img.dtype == np.uint8, f"{fname}: dtype={img.dtype}"
            assert img.ndim in (2, 3), f"{fname}: ndim={img.ndim}"
            h, w = img.shape[:2]
            assert (h, w) == (480, 640), f"{fname}: shape=({h},{w})"
            # Each align image must have a bright alignment target (value >= 200)
            assert img.max() >= 200, f"{fname}: no bright alignment feature found"
            # Background must be mostly dark — mean < 100
            assert img.mean() < 100.0, (
                f"{fname}: expected dark background, mean={img.mean():.1f}"
            )


# ── Integration / E2E tests ───────────────────────────────────────────────────

@pytest.mark.integration
@pytest.mark.e2e
class TestE2EAlignPipeline:

    @pytest.mark.anyio
    async def test_full_align_pipeline_executes(
        self,
        check_ollama_available,
        align_images: dict[str, np.ndarray],
        real_ollama_client: OllamaClient,
    ) -> None:
        """Run the full Align pipeline (max_iteration=1) via Orchestrator.execute()."""
        orchestrator = create_real_orchestrator(real_ollama_client)

        analysis_images = [align_images["X_320.0_Y_240.0_1.png"]]
        test_images = [(align_images[fname], fname) for fname in _ALIGN_IMAGE_FILENAMES]

        t0 = time.monotonic()
        result = await orchestrator.execute(
            purpose_text=_ALIGN_PURPOSE,
            analysis_images=analysis_images,
            test_images=test_images,
            config={"max_iteration": 1},
        )
        elapsed = time.monotonic() - t0
        print(f"\n[orchestrator] full align pipeline elapsed: {elapsed:.1f}s")

        # ── key presence ──
        expected_keys = {
            "spec_result", "diagnosis", "best_pipeline", "judge_result",
            "inspection_plan", "algorithm_category", "algorithm_result",
            "code_validation", "test_results", "evaluation_result",
            "warnings", "iteration_history", "decision_result",
        }
        assert set(result.keys()) == expected_keys

        # ── spec_result: align mode ──
        spec: SpecResult = result["spec_result"]
        log_agent_output("spec_agent", spec)
        assert isinstance(spec, SpecResult)
        assert spec.mode.value == "align"

        # ── diagnosis ──
        diag: ImageDiagnosis = result["diagnosis"]
        log_agent_output("image_analysis", diag)
        assert isinstance(diag, ImageDiagnosis)
        assert isinstance(diag.contrast, float)
        assert isinstance(diag.noise_level, float)

        # ── best_pipeline ──
        pipeline: ProcessingPipeline = result["best_pipeline"]
        log_agent_output("pipeline", pipeline)
        assert isinstance(pipeline, ProcessingPipeline)
        assert len(pipeline.blocks) >= 1

        # ── judge_result ──
        judge: JudgementResult = result["judge_result"]
        log_agent_output("vision_judge", judge)
        assert isinstance(judge, JudgementResult)
        assert 0.0 <= judge.visibility_score <= 1.0
        assert 0.0 <= judge.separability_score <= 1.0
        assert 0.0 <= judge.measurability_score <= 1.0

        # ── align mode: inspection_plan and algorithm_category not computed ──
        assert result["inspection_plan"] is None
        assert result["algorithm_category"] is None

        # ── algorithm_result: TEMPLATE_MATCHING category, align code ──
        algo: AlgorithmResult = result["algorithm_result"]
        log_agent_output("algorithm_coder_align", algo)
        assert isinstance(algo, AlgorithmResult)
        assert len(algo.code.strip()) > 0
        assert len(algo.explanation.strip()) > 0
        assert algo.category == AlgorithmCategory.TEMPLATE_MATCHING

        # ── code_validation ──
        val: ValidationResult = result["code_validation"]
        log_agent_output("code_validator", val)
        assert isinstance(val, ValidationResult)
        assert isinstance(val.is_valid, bool)

        # ── test_results: align-specific metrics (coord_error, success_rate) ──
        test_results: list[ItemTestResult] = result["test_results"]
        log_agent_output("test_agent_align", test_results)
        assert isinstance(test_results, list)
        assert len(test_results) >= 1
        for tr in test_results:
            assert isinstance(tr, ItemTestResult)
            assert isinstance(tr.passed, bool)
            assert tr.metrics.coord_error is not None
            assert tr.metrics.success_rate is not None

        # ── evaluation_result ──
        eval_result: EvaluationResult = result["evaluation_result"]
        log_agent_output("evaluation_agent", eval_result)
        assert isinstance(eval_result, EvaluationResult)
        assert isinstance(eval_result.overall_passed, bool)

        # ── decision_result: align always RULE_BASED when triggered ──
        dr = result["decision_result"]
        log_agent_output("decision_agent", dr)
        assert dr is None or isinstance(dr, DecisionResult)
        if dr is not None:
            assert dr.decision == DecisionType.rule_based, (
                f"Align mode DecisionAgent must return RULE_BASED, got {dr.decision}"
            )

    @pytest.mark.anyio
    async def test_individual_align_agent_outputs(
        self,
        check_ollama_available,
        align_images: dict[str, np.ndarray],
        real_ollama_client: OllamaClient,
    ) -> None:
        """Step through each Align-mode agent individually and verify type/range consistency."""
        image = align_images["X_320.0_Y_240.0_1.png"]
        timings: dict[str, float] = {}

        # 1. SpecAgent
        t0 = time.monotonic()
        spec_agent = SpecAgent()
        spec = await spec_agent.execute(_ALIGN_PURPOSE)
        timings["spec"] = time.monotonic() - t0
        log_agent_output("spec_agent", spec)
        assert isinstance(spec, SpecResult)
        assert spec.mode.value == "align"
        assert len(spec.goal) > 0

        # 2. ImageAnalysisAgent
        t0 = time.monotonic()
        ia_agent = ImageAnalysisAgent()
        diagnosis = ia_agent.execute(image)
        timings["image_analysis"] = time.monotonic() - t0
        log_agent_output("image_analysis", diagnosis)
        assert isinstance(diagnosis, ImageDiagnosis)
        assert 0.0 <= diagnosis.contrast <= 1.0
        assert 0.0 <= diagnosis.noise_level <= 1.0
        assert 0.0 <= diagnosis.edge_density <= 1.0
        assert 0.0 <= diagnosis.lighting_uniformity <= 1.0

        # 3. PipelineComposer
        t0 = time.monotonic()
        pc_agent = PipelineComposer()
        candidates = pc_agent.execute(diagnosis)
        timings["pipeline_composer"] = time.monotonic() - t0
        log_agent_output("pipeline_composer", candidates)
        assert isinstance(candidates, list)
        assert len(candidates) >= 1
        for p in candidates:
            assert isinstance(p, ProcessingPipeline)

        # 4. ParameterSearcher
        t0 = time.monotonic()
        ps_agent = ParameterSearcher()
        optimized = ps_agent.execute(candidates[0], image)
        timings["parameter_searcher"] = time.monotonic() - t0
        log_agent_output("parameter_searcher", optimized)
        assert isinstance(optimized, ProcessingPipeline)

        # 5. VisionJudgeAgent
        t0 = time.monotonic()
        vj_agent = VisionJudgeAgent()
        judge = await vj_agent.execute(
            original_image=image,
            processed_image=image,
            purpose=_ALIGN_PURPOSE,
            pipeline_name=optimized.name,
        )
        timings["vision_judge"] = time.monotonic() - t0
        log_agent_output("vision_judge", judge)
        assert isinstance(judge, JudgementResult)
        assert 0.0 <= judge.visibility_score <= 1.0
        assert 0.0 <= judge.separability_score <= 1.0
        assert 0.0 <= judge.measurability_score <= 1.0

        # 6. AlgorithmCoderAlign (no InspectionPlan / AlgorithmSelector in align mode)
        t0 = time.monotonic()
        coder = AlgorithmCoderAlign(ollama_client=real_ollama_client)
        algo = await coder.execute(pipeline=optimized)
        timings["algorithm_coder_align"] = time.monotonic() - t0
        log_agent_output("algorithm_coder_align", algo)
        assert isinstance(algo, AlgorithmResult)
        assert len(algo.code.strip()) > 0
        assert algo.category == AlgorithmCategory.TEMPLATE_MATCHING

        # 7. CodeValidator — align mode checks for align(image) function
        t0 = time.monotonic()
        cv_agent = CodeValidator()
        validation = cv_agent.validate(algo.code, "align")
        timings["code_validator"] = time.monotonic() - t0
        log_agent_output("code_validator", validation)
        assert isinstance(validation, ValidationResult)
        if not validation.is_valid:
            print(f"  [WARN] CodeValidator errors: {validation.errors}")

        # 8. TestAgentAlign — filenames encode GT coordinates
        test_imgs = [
            (align_images["X_320.0_Y_240.0_1.png"], "X_320.0_Y_240.0_1.png"),
            (align_images["X_160.0_Y_120.0_2.png"], "X_160.0_Y_120.0_2.png"),
        ]
        t0 = time.monotonic()
        ta_agent = TestAgentAlign()
        test_results = ta_agent.execute(code=algo.code, test_images=test_imgs)
        timings["test_agent_align"] = time.monotonic() - t0
        log_agent_output("test_agent_align", test_results)
        assert isinstance(test_results, list)
        assert len(test_results) >= 1
        for tr in test_results:
            assert isinstance(tr, ItemTestResult)
            assert tr.item_name == "align"
            assert tr.metrics.coord_error is not None
            assert tr.metrics.success_rate is not None

        # 9. EvaluationAgent — align mode (no plan argument)
        t0 = time.monotonic()
        ea_agent = EvaluationAgent()
        eval_result = ea_agent.execute(
            test_results=test_results,
            judge_result=judge,
            mode="align",
        )
        timings["evaluation_agent"] = time.monotonic() - t0
        log_agent_output("evaluation_agent", eval_result)
        assert isinstance(eval_result, EvaluationResult)
        assert isinstance(eval_result.overall_passed, bool)

        print("\n[timings]")
        for agent, t in timings.items():
            print(f"  {agent}: {t:.2f}s")

    @pytest.mark.anyio
    async def test_align_code_has_valid_signature(
        self,
        check_ollama_available,
        align_images: dict[str, np.ndarray],
        real_ollama_client: OllamaClient,
    ) -> None:
        """Generated align code must have align(image) returning dict with x, y, confidence, method_used."""
        image = align_images["X_320.0_Y_240.0_1.png"]
        ia_agent = ImageAnalysisAgent()
        diagnosis = ia_agent.execute(image)
        pc_agent = PipelineComposer()
        candidates = pc_agent.execute(diagnosis)
        ps_agent = ParameterSearcher()
        optimized = ps_agent.execute(candidates[0], image)

        coder = AlgorithmCoderAlign(ollama_client=real_ollama_client)

        for attempt in range(3):
            algo = await coder.execute(pipeline=optimized)
            code = algo.code
            log_agent_output("algorithm_coder_align (code)", code[:300])

            # 1. Syntax check
            try:
                tree = ast.parse(code)
            except SyntaxError as exc:
                if attempt < 2:
                    print(f"  [retry] SyntaxError on attempt {attempt+1}: {exc}")
                    continue
                raise AssertionError(f"Generated align code has SyntaxError: {exc}") from exc

            # 2. CodeValidator align mode
            cv_agent = CodeValidator()
            validation = cv_agent.validate(code, "align")
            assert isinstance(validation, ValidationResult)

            # 3. find align(image) function
            align_fns = [
                node for node in ast.walk(tree)
                if isinstance(node, ast.FunctionDef) and node.name == "align"
            ]
            assert len(align_fns) >= 1, (
                "No 'align' function in generated code. "
                f"Functions: {[n.name for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]}"
            )

            # 4. exec and call align(image)
            namespace: dict = {"np": np, "cv2": cv2, "numpy": np}
            try:
                exec(code, namespace)  # noqa: S102
            except Exception as exc:
                if attempt < 2:
                    print(f"  [retry] exec() failed on attempt {attempt+1}: {exc}")
                    continue
                raise AssertionError(f"exec() failed: {exc}") from exc

            align_fn = namespace.get("align")
            assert callable(align_fn), "align is not callable after exec"

            try:
                call_result = align_fn(image)
            except Exception as exc:
                if attempt < 2:
                    print(f"  [retry] align() call failed on attempt {attempt+1}: {exc}")
                    continue
                raise AssertionError(f"align() call failed: {exc}") from exc

            print(f"\n[exec result] align(X_320.0_Y_240.0_1) → {call_result}")
            assert isinstance(call_result, dict), (
                f"Expected dict, got {type(call_result).__name__}: {call_result}"
            )
            required_keys = {"x", "y", "confidence", "method_used"}
            assert required_keys.issubset(call_result.keys()), (
                f"Missing keys: {required_keys - set(call_result.keys())}. "
                f"Got: {list(call_result.keys())}"
            )
            assert isinstance(float(call_result["x"]), float), "x must be numeric"
            assert isinstance(float(call_result["y"]), float), "y must be numeric"
            break


# ── Non-Ollama unit tests ─────────────────────────────────────────────────────

class TestAlignDecisionAgent:
    def test_decision_agent_returns_rule_based_for_align(self) -> None:
        """DecisionAgent must always return RULE_BASED (never EL/DL) for Align mode."""
        agent = DecisionAgent()

        for iteration_history in [
            [],
            [{"iteration": 1}],
            [{"iteration": i} for i in range(5)],
        ]:
            result = agent.execute(
                iteration_history=iteration_history,
                mode="align",
                judge_result=None,
                image_diagnosis=None,
            )
            log_agent_output("decision_agent", result)
            assert isinstance(result, DecisionResult)
            assert result.decision == DecisionType.rule_based, (
                f"Align mode must return rule_based, got {result.decision} "
                f"with {len(iteration_history)} iterations"
            )
            assert "하드웨어" in result.reason or "정렬" in result.reason, (
                f"Align RULE_BASED reason should mention hardware/alignment: {result.reason}"
            )


class TestAlignCodeValidator:
    def test_code_validator_rejects_missing_align_function(self) -> None:
        """CodeValidator rejects code without valid align(image) function."""
        cv_agent = CodeValidator()

        # Wrong function name
        bad_name = "import cv2\nimport numpy as np\ndef detect(image):\n    return {'x': 0.0}"
        result = cv_agent.validate(bad_name, "align")
        assert not result.is_valid
        assert any("align" in e for e in result.errors)

        # Wrong signature — extra argument
        bad_sig = (
            "import cv2\nimport numpy as np\n"
            "def align(image, threshold):\n    return {'x': 0.0, 'y': 0.0}"
        )
        result2 = cv_agent.validate(bad_sig, "align")
        assert not result2.is_valid

        # Valid align code
        good = (
            "import cv2\nimport numpy as np\n"
            "def align(image):\n"
            "    return {'x': 320.0, 'y': 240.0, 'confidence': 0.9, 'method_used': 'template_matching'}"
        )
        result3 = cv_agent.validate(good, "align")
        assert result3.is_valid, f"Expected valid, errors: {result3.errors}"
