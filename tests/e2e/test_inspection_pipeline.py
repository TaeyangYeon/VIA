"""Step 44: E2E Integration Tests — Inspection Full Pipeline.

All tests marked @pytest.mark.integration and @pytest.mark.e2e.
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
    EvaluationResult,
    ImageDiagnosis,
    InspectionPlan,
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
_PURPOSE = (
    "원형 검출 검사: 이미지에서 원형 객체의 존재 여부를 판별하고, "
    "OK(정상 원형 존재)/NG(원형 결함 또는 부재)를 분류하는 알고리즘을 설계하라."
)


# ── anyio backend ─────────────────────────────────────────────────────────────

@pytest.fixture(params=["asyncio"])
def anyio_backend(request):
    return request.param


# ── Session fixtures ──────────────────────────────────────────────────────────

@pytest.fixture(scope="session")
def check_ollama_available():
    """Skip dependent tests if Ollama / gemma4:e4b is not reachable.

    Reads VIA_OLLAMA_URL env var (default: localhost:11434) and configures
    the module-level singleton ollama_client so all agents point to the same URL.
    """
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
    """Reset the module-level ollama_client singleton's cached HTTP client before each test.

    anyio creates a new event loop per test. An httpx.AsyncClient created in a previous
    event loop is not usable in a new one, so we null it out before each test so it gets
    re-created lazily in the current event loop.
    """
    from backend.services.ollama_client import ollama_client as _singleton
    _singleton._client = None
    yield
    _singleton._client = None


@pytest.fixture(scope="session")
def sample_images() -> dict[str, np.ndarray]:
    """Load all 6 synthetic sample images."""
    names = ["OK_1", "OK_2", "OK_3", "NG_1", "NG_2", "NG_3"]
    images: dict[str, np.ndarray] = {}
    for name in names:
        path = _FIXTURES_DIR / f"{name}.png"
        img = cv2.imread(str(path), cv2.IMREAD_GRAYSCALE)
        assert img is not None, f"Failed to load {path}"
        images[name] = img
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


# ── Test 5 (no Ollama) ────────────────────────────────────────────────────────

class TestSampleImagesValid:
    def test_sample_images_are_valid(self, sample_images: dict[str, np.ndarray]) -> None:
        """Verify all 6 synthetic images have correct shape, dtype, and naming."""
        expected_names = {"OK_1", "OK_2", "OK_3", "NG_1", "NG_2", "NG_3"}
        assert set(sample_images.keys()) == expected_names

        for name, img in sample_images.items():
            assert isinstance(img, np.ndarray), f"{name}: not ndarray"
            assert img.dtype == np.uint8, f"{name}: dtype={img.dtype}"
            assert img.ndim in (2, 3), f"{name}: ndim={img.ndim}"
            h, w = img.shape[:2]
            assert (h, w) == (480, 640), f"{name}: shape=({h},{w})"

        # OK images should have a dark blob (circle) — mean should be < 255
        for name in ["OK_1", "OK_2", "OK_3"]:
            assert sample_images[name].mean() < 254.0, f"{name}: no dark region found"

        # NG_1 is blank — mean should be ~255
        assert sample_images["NG_1"].mean() > 254.0, "NG_1: should be blank"


# ── Integration / E2E tests ───────────────────────────────────────────────────

@pytest.mark.integration
@pytest.mark.e2e
class TestE2EInspectionPipeline:

    @pytest.mark.anyio
    async def test_full_inspection_pipeline_executes(
        self,
        check_ollama_available,
        sample_images: dict[str, np.ndarray],
        real_ollama_client: OllamaClient,
    ) -> None:
        """Run the full Inspection pipeline (max_iteration=1) via Orchestrator.execute()."""
        orchestrator = create_real_orchestrator(real_ollama_client)

        analysis_images = [sample_images["OK_1"], sample_images["NG_1"]]
        test_images = [
            (sample_images["OK_1"], "OK_1.png"),
            (sample_images["OK_2"], "OK_2.png"),
            (sample_images["NG_1"], "NG_1.png"),
            (sample_images["NG_2"], "NG_2.png"),
        ]

        t0 = time.monotonic()
        result = await orchestrator.execute(
            purpose_text=_PURPOSE,
            analysis_images=analysis_images,
            test_images=test_images,
            config={"mode": "inspection", "max_iteration": 1},
        )
        elapsed = time.monotonic() - t0
        print(f"\n[orchestrator] full pipeline elapsed: {elapsed:.1f}s")

        # ── key presence ──
        expected_keys = {
            "spec_result", "diagnosis", "best_pipeline", "judge_result",
            "inspection_plan", "algorithm_category", "algorithm_result",
            "code_validation", "test_results", "evaluation_result",
            "warnings", "iteration_history", "decision_result",
        }
        assert set(result.keys()) == expected_keys

        # ── spec_result ──
        spec: SpecResult = result["spec_result"]
        log_agent_output("spec_agent", spec)
        assert isinstance(spec, SpecResult)
        assert spec.mode.value == "inspection"

        # ── diagnosis ──
        diag: ImageDiagnosis = result["diagnosis"]
        log_agent_output("image_analysis", diag)
        assert isinstance(diag, ImageDiagnosis)
        assert isinstance(diag.contrast, float)
        assert isinstance(diag.noise_level, float)
        assert isinstance(diag.surface_type, str)

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

        # ── inspection_plan ──
        plan: InspectionPlan = result["inspection_plan"]
        log_agent_output("inspection_plan", plan)
        assert isinstance(plan, InspectionPlan)
        assert len(plan.items) >= 1

        # ── algorithm_category ──
        cat: AlgorithmCategory = result["algorithm_category"]
        log_agent_output("algorithm_selector", cat)
        assert isinstance(cat, AlgorithmCategory)
        assert cat in list(AlgorithmCategory)

        # ── algorithm_result ──
        algo: AlgorithmResult = result["algorithm_result"]
        log_agent_output("algorithm_coder", algo)
        assert isinstance(algo, AlgorithmResult)
        assert len(algo.code.strip()) > 0
        assert len(algo.explanation.strip()) > 0

        # ── code_validation ──
        val: ValidationResult = result["code_validation"]
        log_agent_output("code_validator", val)
        assert isinstance(val, ValidationResult)
        assert isinstance(val.is_valid, bool)

        # ── test_results ──
        test_results: list[ItemTestResult] = result["test_results"]
        log_agent_output("test_agent", test_results)
        assert isinstance(test_results, list)
        assert len(test_results) >= 1
        for tr in test_results:
            assert isinstance(tr, ItemTestResult)
            assert isinstance(tr.passed, bool)

        # ── evaluation_result ──
        eval_result: EvaluationResult = result["evaluation_result"]
        log_agent_output("evaluation_agent", eval_result)
        assert isinstance(eval_result, EvaluationResult)
        assert isinstance(eval_result.overall_passed, bool)

        # ── decision_result (None or DecisionResult with max_iter=1) ──
        dr = result["decision_result"]
        assert dr is None or isinstance(dr, DecisionResult)
        log_agent_output("decision_agent", dr)

    @pytest.mark.anyio
    async def test_individual_agent_outputs_are_consistent(
        self,
        check_ollama_available,
        sample_images: dict[str, np.ndarray],
        real_ollama_client: OllamaClient,
    ) -> None:
        """Step through each agent individually and verify type/range consistency."""
        image = sample_images["OK_1"]
        timings: dict[str, float] = {}

        # 1. SpecAgent
        t0 = time.monotonic()
        spec_agent = SpecAgent()
        spec = await spec_agent.execute(_PURPOSE)
        timings["spec"] = time.monotonic() - t0
        log_agent_output("spec_agent", spec)
        assert isinstance(spec, SpecResult)
        assert spec.mode.value == "inspection"
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
        assert 0.0 <= diagnosis.blob_feasibility <= 1.0
        assert 0.0 <= diagnosis.background_uniformity <= 1.0
        assert diagnosis.blob_count_estimate >= 0

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
            purpose=_PURPOSE,
            pipeline_name=optimized.name,
        )
        timings["vision_judge"] = time.monotonic() - t0
        log_agent_output("vision_judge", judge)
        assert isinstance(judge, JudgementResult)
        assert 0.0 <= judge.visibility_score <= 1.0
        assert 0.0 <= judge.separability_score <= 1.0
        assert 0.0 <= judge.measurability_score <= 1.0

        # 6. InspectionPlanAgent
        t0 = time.monotonic()
        ip_agent = InspectionPlanAgent()
        summary = f"surface={diagnosis.surface_type}, contrast={diagnosis.contrast:.2f}"
        plan = await ip_agent.execute(purpose=_PURPOSE, image_diagnosis_summary=summary)
        timings["inspection_plan"] = time.monotonic() - t0
        log_agent_output("inspection_plan", plan)
        assert isinstance(plan, InspectionPlan)
        assert len(plan.items) >= 1

        # 7. AlgorithmSelector
        t0 = time.monotonic()
        as_agent = AlgorithmSelector()
        category = as_agent.execute(diagnosis)
        timings["algorithm_selector"] = time.monotonic() - t0
        log_agent_output("algorithm_selector", category)
        assert isinstance(category, AlgorithmCategory)

        # 8. AlgorithmCoderInspection
        t0 = time.monotonic()
        coder = AlgorithmCoderInspection(ollama_client=real_ollama_client)
        algo = await coder.execute(category=category, pipeline=optimized, plan=plan)
        timings["algorithm_coder"] = time.monotonic() - t0
        log_agent_output("algorithm_coder", algo)
        assert isinstance(algo, AlgorithmResult)
        assert len(algo.code.strip()) > 0

        # 9. CodeValidator
        t0 = time.monotonic()
        cv_agent = CodeValidator()
        validation = cv_agent.validate(algo.code, "inspection")
        timings["code_validator"] = time.monotonic() - t0
        log_agent_output("code_validator", validation)
        assert isinstance(validation, ValidationResult)
        # If invalid, log errors for debugging
        if not validation.is_valid:
            print(f"  [WARN] CodeValidator errors: {validation.errors}")

        # 10. TestAgentInspection
        test_imgs = [
            (sample_images["OK_1"], "OK_1.png"),
            (sample_images["NG_1"], "NG_1.png"),
        ]
        t0 = time.monotonic()
        ta_agent = TestAgentInspection()
        test_results = ta_agent.execute(code=algo.code, plan=plan, test_images=test_imgs)
        timings["test_agent"] = time.monotonic() - t0
        log_agent_output("test_agent", test_results)
        assert isinstance(test_results, list)
        for tr in test_results:
            assert isinstance(tr, ItemTestResult)

        # 11. EvaluationAgent
        t0 = time.monotonic()
        ea_agent = EvaluationAgent()
        eval_result = ea_agent.execute(
            test_results=test_results,
            judge_result=judge,
            plan=plan,
            mode="inspection",
        )
        timings["evaluation_agent"] = time.monotonic() - t0
        log_agent_output("evaluation_agent", eval_result)
        assert isinstance(eval_result, EvaluationResult)

        # Print timing summary
        print("\n[timings]")
        for agent, t in timings.items():
            print(f"  {agent}: {t:.2f}s")

    @pytest.mark.anyio
    async def test_vision_judge_differentiates_good_and_bad_processing(
        self,
        check_ollama_available,
        sample_images: dict[str, np.ndarray],
    ) -> None:
        """VisionJudgeAgent should score good processing higher than destructive blur."""
        original = sample_images["OK_1"]

        # Good processing: Otsu threshold — preserves circle structure
        _, good_processed = cv2.threshold(original, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

        # Bad processing: extreme blur — destroys circle boundary
        bad_processed = cv2.GaussianBlur(original, (99, 99), 50)

        vj = VisionJudgeAgent()

        for attempt in range(3):
            good_judge = await vj.execute(
                original_image=original,
                processed_image=good_processed,
                purpose=_PURPOSE,
                pipeline_name="otsu_threshold",
            )
            bad_judge = await vj.execute(
                original_image=original,
                processed_image=bad_processed,
                purpose=_PURPOSE,
                pipeline_name="extreme_blur",
            )
            log_agent_output("judge_good", good_judge)
            log_agent_output("judge_bad", bad_judge)

            good_avg = (
                good_judge.visibility_score
                + good_judge.separability_score
                + good_judge.measurability_score
            ) / 3.0
            bad_avg = (
                bad_judge.visibility_score
                + bad_judge.separability_score
                + bad_judge.measurability_score
            ) / 3.0

            print(f"\n[attempt {attempt+1}] good_avg={good_avg:.3f}, bad_avg={bad_avg:.3f}")

            # At least one score dimension should rank good higher
            good_better = (
                good_judge.visibility_score > bad_judge.visibility_score
                or good_judge.separability_score > bad_judge.separability_score
                or good_judge.measurability_score > bad_judge.measurability_score
            )
            if good_better:
                break
            if attempt < 2:
                print("  [retry] good not ranked higher — retrying")

        assert good_better, (
            f"Expected good processing to score higher on at least one dimension. "
            f"good=({good_judge.visibility_score:.2f}, {good_judge.separability_score:.2f}, "
            f"{good_judge.measurability_score:.2f}), "
            f"bad=({bad_judge.visibility_score:.2f}, {bad_judge.separability_score:.2f}, "
            f"{bad_judge.measurability_score:.2f})"
        )

    @pytest.mark.anyio
    async def test_pipeline_produces_executable_code(
        self,
        check_ollama_available,
        sample_images: dict[str, np.ndarray],
        real_ollama_client: OllamaClient,
    ) -> None:
        """Generated algorithm code must be syntactically valid and executable."""
        # Run agents up to code generation
        image = sample_images["OK_1"]
        ia_agent = ImageAnalysisAgent()
        diagnosis = ia_agent.execute(image)

        pc_agent = PipelineComposer()
        candidates = pc_agent.execute(diagnosis)

        ps_agent = ParameterSearcher()
        optimized = ps_agent.execute(candidates[0], image)

        ip_agent = InspectionPlanAgent()
        summary = f"surface={diagnosis.surface_type}, contrast={diagnosis.contrast:.2f}"
        plan = await ip_agent.execute(purpose=_PURPOSE, image_diagnosis_summary=summary)

        as_agent = AlgorithmSelector()
        category = as_agent.execute(diagnosis)

        coder = AlgorithmCoderInspection(ollama_client=real_ollama_client)

        for attempt in range(3):
            algo = await coder.execute(category=category, pipeline=optimized, plan=plan)
            code = algo.code
            log_agent_output("algorithm_coder (code)", code[:300])

            # 1. ast.parse() — syntax check
            try:
                tree = ast.parse(code)
            except SyntaxError as exc:
                if attempt < 2:
                    print(f"  [retry] SyntaxError on attempt {attempt+1}: {exc}")
                    continue
                raise AssertionError(f"Generated code has SyntaxError: {exc}") from exc

            # 2. CodeValidator
            cv_agent = CodeValidator()
            validation = cv_agent.validate(code, "inspection")
            assert isinstance(validation, ValidationResult)
            if not validation.is_valid:
                print(f"  [WARN] CodeValidator: {validation.errors}")

            # 3. exec() — runtime check
            func_names = [
                node.name
                for node in ast.walk(tree)
                if isinstance(node, ast.FunctionDef)
                and node.name.startswith("inspect")
            ]
            assert len(func_names) >= 1, (
                f"No 'inspect*' function found in generated code. "
                f"Functions: {[n.name for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]}"
            )

            namespace: dict = {"np": np, "cv2": cv2, "numpy": np}
            try:
                exec(code, namespace)  # noqa: S102
            except Exception as exc:
                if attempt < 2:
                    print(f"  [retry] exec() failed on attempt {attempt+1}: {exc}")
                    continue
                raise AssertionError(f"exec() failed: {exc}") from exc

            # 4. Call the first inspect* function
            func = namespace[func_names[0]]
            test_img = sample_images["OK_1"]
            try:
                call_result = func(test_img)
            except Exception as exc:
                if attempt < 2:
                    print(f"  [retry] function call failed on attempt {attempt+1}: {exc}")
                    continue
                raise AssertionError(f"inspect function call failed: {exc}") from exc

            print(f"\n[exec result] {func_names[0]}(OK_1) → {call_result}")
            assert isinstance(call_result, dict), (
                f"Expected dict, got {type(call_result).__name__}: {call_result}"
            )
            assert "result" in call_result, (
                f"Expected 'result' key in return dict. Got: {list(call_result.keys())}"
            )
            assert call_result["result"] in ("OK", "NG"), (
                f"Expected 'OK' or 'NG', got: {call_result['result']!r}"
            )
            break
