"""Step 46: Agent Directive E2E Tests.

Verifies that Agent Directives influence (or correctly do NOT influence) agent behavior.
- Prompt-building agents: directive text included in prompt (no markers)
- PipelineComposer: 'Blob' keyword sorts morphology pipelines first (no markers)
- Rule-based agents: directive logged but does NOT change output (no markers)
- Orchestrator _distribute_directives: routes fields to each agent (no markers, mock-based)
- Ollama-dependent agents: structural output verified with real Gemma4 (integration+e2e markers)
"""
from __future__ import annotations

import asyncio
import copy
import os
from pathlib import Path
from typing import Optional
from unittest.mock import MagicMock

import cv2
import httpx
import numpy as np
import pytest

from agents.algorithm_coder_align import AlgorithmCoderAlign
from agents.algorithm_coder_inspection import AlgorithmCoderInspection
from agents.algorithm_selector import AlgorithmSelector
from agents.code_validator import CodeValidator
from agents.decision_agent import DecisionAgent
from agents.evaluation_agent import EvaluationAgent
from agents.feedback_controller import FeedbackController
from agents.image_analysis_agent import ImageAnalysisAgent
from agents.inspection_plan_agent import InspectionPlanAgent
from agents.models import (
    AgentDirectives,
    AlgorithmCategory,
    DefectScale,
    EvaluationResult,
    FailureReason,
    IlluminationType,
    ImageDiagnosis,
    InspectionMode,
    InspectionPlan,
    ItemTestResult,
    JudgementResult,
    NoiseFrequency,
    ProcessingPipeline,
    SpecResult,
    TestMetrics,
)
from agents.orchestrator import Orchestrator
from agents.parameter_searcher import ParameterSearcher
from agents.pipeline_blocks import block_library
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
    """OllamaClient tuned for Intel Mac slow first-inference."""
    return OllamaClient(
        base_url=OLLAMA_BASE_URL,
        model=_MODEL,
        health_timeout=300.0,
        generate_timeout=600.0,
        max_retries=2,
    )


@pytest.fixture(autouse=True)
def reset_singleton_client():
    """Reset the singleton ollama_client's cached HTTP client before each test.

    anyio creates a new event loop per test; an AsyncClient from a prior loop
    is unusable in the new one, so we null it out to force lazy re-creation.
    """
    from backend.services.ollama_client import ollama_client as _singleton
    _singleton._client = None
    yield
    _singleton._client = None


@pytest.fixture(scope="session")
def sample_images() -> dict[str, np.ndarray]:
    """Load OK_1 and NG_1 synthetic sample images."""
    images: dict[str, np.ndarray] = {}
    for name in ["OK_1", "NG_1"]:
        path = _FIXTURES_DIR / f"{name}.png"
        img = cv2.imread(str(path), cv2.IMREAD_GRAYSCALE)
        assert img is not None, f"Failed to load {path}"
        images[name] = img
    return images


# ── Helpers ───────────────────────────────────────────────────────────────────

def make_diagnosis(**overrides) -> ImageDiagnosis:
    defaults = dict(
        contrast=0.5,
        noise_level=0.1,
        edge_density=0.2,
        lighting_uniformity=0.9,
        illumination_type=IlluminationType.uniform,
        noise_frequency=NoiseFrequency.low_freq,
        reflection_level=0.05,
        texture_complexity=0.2,
        surface_type="plastic",
        defect_scale=DefectScale.macro,
        blob_feasibility=0.7,
        blob_count_estimate=5,
        blob_size_variance=0.1,
        color_discriminability=0.3,
        dominant_channel_ratio=0.4,
        structural_regularity=0.6,
        pattern_repetition=0.1,
        background_uniformity=0.8,
        optimal_color_space="gray",
        threshold_candidate=128.0,
        edge_sharpness=100.0,
    )
    defaults.update(overrides)
    return ImageDiagnosis(**defaults)


def _has_morphology(pipeline: ProcessingPipeline) -> bool:
    return any(
        block_library.get_block(b.name).category == "morphology"
        for b in pipeline.blocks
    )


def create_real_orchestrator(ollama_client: Optional[OllamaClient] = None) -> Orchestrator:
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


def _assert_valid_inspection_result(result: dict) -> None:
    expected_keys = {
        "spec_result", "diagnosis", "best_pipeline", "judge_result",
        "inspection_plan", "algorithm_category", "algorithm_result",
        "code_validation", "test_results", "evaluation_result",
        "warnings", "iteration_history", "decision_result",
    }
    assert set(result.keys()) == expected_keys
    assert isinstance(result["spec_result"], SpecResult)
    assert isinstance(result["diagnosis"], ImageDiagnosis)
    assert isinstance(result["best_pipeline"], ProcessingPipeline)
    assert isinstance(result["judge_result"], JudgementResult)
    assert isinstance(result["inspection_plan"], InspectionPlan)
    assert len(result["inspection_plan"].items) >= 1
    assert isinstance(result["algorithm_category"], AlgorithmCategory)
    assert isinstance(result["evaluation_result"], EvaluationResult)
    assert isinstance(result["evaluation_result"].overall_passed, bool)


# ── 1. Prompt builder tests (no markers) ─────────────────────────────────────

class TestPromptBuilders:
    def test_spec_prompt_includes_directive(self):
        from agents.prompts.spec_prompt import build_spec_prompt
        prompt = build_spec_prompt("원형 검출", directive="정확도 우선")
        assert "정확도 우선" in prompt

    def test_spec_prompt_omits_directive_section_when_none(self):
        from agents.prompts.spec_prompt import build_spec_prompt
        prompt = build_spec_prompt("원형 검출")
        assert "Additional directive" not in prompt

    def test_inspection_plan_prompt_includes_directive(self):
        from agents.prompts.inspection_plan_prompt import build_inspection_plan_prompt
        prompt = build_inspection_plan_prompt(
            "원형 검출", "surface=plastic, contrast=0.50", directive="BLOB 우선"
        )
        assert "BLOB 우선" in prompt

    def test_inspection_plan_prompt_omits_directive_section_when_none(self):
        from agents.prompts.inspection_plan_prompt import build_inspection_plan_prompt
        prompt = build_inspection_plan_prompt("원형 검출", "surface=plastic")
        assert "Additional directive" not in prompt

    def test_vision_judge_prompt_includes_directive(self):
        from agents.prompts.vision_judge_prompt import build_vision_judge_prompt
        prompt = build_vision_judge_prompt("원형 검출", "test_pipeline", directive="엣지 집중 평가")
        assert "엣지 집중 평가" in prompt

    def test_vision_judge_prompt_omits_directive_section_when_none(self):
        from agents.prompts.vision_judge_prompt import build_vision_judge_prompt
        prompt = build_vision_judge_prompt("원형 검출", "test_pipeline")
        assert "Additional guidance" not in prompt


# ── 2. PipelineComposer directive tests (no markers) ─────────────────────────

class TestPipelineComposerDirective:
    def test_blob_directive_sorts_morphology_pipelines_first(self):
        pc = PipelineComposer()
        pc.set_directive("Blob")
        pipelines = pc.execute(make_diagnosis())

        morph_flags = [_has_morphology(p) for p in pipelines]
        first_non_morph = next((i for i, f in enumerate(morph_flags) if not f), len(morph_flags))
        assert all(morph_flags[:first_non_morph]), (
            f"'Blob' directive must sort morphology pipelines first. "
            f"Pipelines: {[p.name for p in pipelines]}"
        )

    def test_korean_blob_directive_sorts_morphology_pipelines_first(self):
        pc = PipelineComposer()
        pc.set_directive("블롭")
        pipelines = pc.execute(make_diagnosis())

        morph_flags = [_has_morphology(p) for p in pipelines]
        first_non_morph = next((i for i, f in enumerate(morph_flags) if not f), len(morph_flags))
        assert all(morph_flags[:first_non_morph]), (
            f"'블롭' directive must sort morphology pipelines first. "
            f"Pipelines: {[p.name for p in pipelines]}"
        )

    def test_lowercase_blob_directive_sorts_morphology_pipelines_first(self):
        pc = PipelineComposer()
        pc.set_directive("blob detection 사용")
        pipelines = pc.execute(make_diagnosis())

        morph_flags = [_has_morphology(p) for p in pipelines]
        first_non_morph = next((i for i, f in enumerate(morph_flags) if not f), len(morph_flags))
        assert all(morph_flags[:first_non_morph])

    def test_no_directive_returns_default_ordering(self):
        pc = PipelineComposer()
        pipelines = pc.execute(make_diagnosis())

        assert len(pipelines) == 5
        assert pipelines[0].name == "적극적_노이즈제거_파이프라인"

    def test_custom_directive_without_blob_keyword_does_not_crash(self):
        pc = PipelineComposer()
        pc.set_directive("엣지 검출 우선")
        pipelines = pc.execute(make_diagnosis())

        assert isinstance(pipelines, list)
        assert len(pipelines) >= 1

    def test_blob_directive_preserves_pipeline_count(self):
        diagnosis = make_diagnosis()
        pc_no_dir = PipelineComposer()
        pc_blob = PipelineComposer()
        pc_blob.set_directive("Blob")

        assert len(pc_no_dir.execute(diagnosis)) == len(pc_blob.execute(diagnosis))


# ── 3. AlgorithmSelector directive independence tests (no markers) ────────────

class TestAlgorithmSelectorDirectiveIndependence:
    def test_directive_does_not_change_blob_selection(self):
        diagnosis = make_diagnosis(contrast=0.5, blob_feasibility=0.7)
        selector = AlgorithmSelector()

        result_no_dir = selector.execute(diagnosis)
        assert result_no_dir == AlgorithmCategory.BLOB

        selector.set_directive("강제로 EDGE_DETECTION 사용")
        result_with_dir = selector.execute(diagnosis)
        assert result_with_dir == AlgorithmCategory.BLOB

    def test_directive_does_not_change_color_filter_selection(self):
        diagnosis = make_diagnosis(
            contrast=0.2, blob_feasibility=0.3, color_discriminability=0.7
        )
        selector = AlgorithmSelector()

        result_no_dir = selector.execute(diagnosis)
        assert result_no_dir == AlgorithmCategory.COLOR_FILTER

        selector.set_directive("BLOB 사용 지시")
        result_with_dir = selector.execute(diagnosis)
        assert result_with_dir == AlgorithmCategory.COLOR_FILTER

    def test_multiple_directives_do_not_change_decision_tree_output(self):
        # Fallback case: no condition matches → default BLOB
        diagnosis = make_diagnosis(
            contrast=0.1,
            blob_feasibility=0.1,
            color_discriminability=0.1,
            edge_density=0.0,
            structural_regularity=0.1,
            pattern_repetition=0.1,
        )
        selector = AlgorithmSelector()
        baseline = selector.execute(diagnosis)

        for directive in ["EDGE_DETECTION", "BLOB", "COLOR_FILTER", "TEMPLATE_MATCHING"]:
            selector.set_directive(directive)
            result = selector.execute(diagnosis)
            assert result == baseline, (
                f"Directive '{directive}' must not change AlgorithmSelector output. "
                f"Expected {baseline}, got {result}"
            )


# ── 4. FeedbackController directive tests (no markers) ───────────────────────

class TestFeedbackControllerDirective:
    @staticmethod
    def _make_eval_result(reason: FailureReason) -> EvaluationResult:
        return EvaluationResult(
            overall_passed=False,
            failure_reason=reason,
            failed_items=[1],
            analysis="테스트",
        )

    def test_directive_does_not_affect_feedback_mapping(self):
        eval_result = self._make_eval_result(FailureReason.pipeline_bad_params)

        fc1 = FeedbackController()
        action1 = fc1.execute(eval_result)

        fc2 = FeedbackController(directive="특수 지시사항 — 파이프라인 재구성")
        action2 = fc2.execute(eval_result)

        assert action1.target_agent == action2.target_agent
        assert action1.reason == action2.reason

    def test_directive_is_stored(self):
        fc = FeedbackController()
        assert fc.get_directive() is None
        fc.set_directive("새로운 지시")
        assert fc.get_directive() == "새로운 지시"

    def test_all_failure_reasons_unaffected_by_directive(self):
        for reason in FailureReason:
            eval_result = self._make_eval_result(reason)

            fc_no_dir = FeedbackController()
            fc_with_dir = FeedbackController(directive="임의 지시")

            action_no_dir = fc_no_dir.execute(eval_result)
            action_with_dir = fc_with_dir.execute(eval_result)

            assert action_no_dir.target_agent == action_with_dir.target_agent, (
                f"FailureReason.{reason.value}: target mismatch with directive"
            )
            assert action_no_dir.reason == action_with_dir.reason, (
                f"FailureReason.{reason.value}: reason mismatch with directive"
            )


# ── 5. EvaluationAgent directive tests (no markers) ──────────────────────────

class TestEvaluationAgentDirective:
    @staticmethod
    def _make_test_results(passed: bool) -> list[ItemTestResult]:
        return [ItemTestResult(
            item_id=1,
            item_name="원형 검출",
            passed=passed,
            metrics=TestMetrics(
                accuracy=0.9 if passed else 0.3,
                fp_rate=0.05 if passed else 0.4,
                fn_rate=0.05 if passed else 0.4,
            ),
        )]

    def test_directive_does_not_affect_pass_evaluation(self):
        test_results = self._make_test_results(passed=True)

        ea1 = EvaluationAgent()
        result1 = ea1.execute(test_results)

        ea2 = EvaluationAgent(directive="다른 방식으로 평가")
        result2 = ea2.execute(test_results)

        assert result1.overall_passed == result2.overall_passed
        assert result1.failure_reason == result2.failure_reason

    def test_directive_does_not_affect_fail_evaluation(self):
        test_results = self._make_test_results(passed=False)

        ea1 = EvaluationAgent()
        result1 = ea1.execute(test_results)

        ea2 = EvaluationAgent(directive="엄격한 평가 기준 적용")
        result2 = ea2.execute(test_results)

        assert result1.overall_passed == result2.overall_passed
        assert result1.failure_reason == result2.failure_reason

    def test_directive_is_stored(self):
        ea = EvaluationAgent(directive="검사 지시")
        assert ea.get_directive() == "검사 지시"


# ── 6. ImageAnalysisAgent directive tests (no markers) ───────────────────────

class TestImageAnalysisAgentDirective:
    @staticmethod
    def _make_test_image() -> np.ndarray:
        img = np.ones((100, 100), dtype=np.uint8) * 200
        img[30:70, 30:70] = 50
        return img

    def test_directive_does_not_change_computation_results(self):
        image = self._make_test_image()

        ia1 = ImageAnalysisAgent()
        diag1 = ia1.execute(image)

        ia2 = ImageAnalysisAgent(directive="엣지 집중 분석")
        diag2 = ia2.execute(image)

        assert diag1.contrast == diag2.contrast
        assert diag1.noise_level == diag2.noise_level
        assert diag1.edge_density == diag2.edge_density
        assert diag1.blob_feasibility == diag2.blob_feasibility
        assert diag1.surface_type == diag2.surface_type

    def test_directive_is_stored(self):
        ia = ImageAnalysisAgent(directive="색상 분석 집중")
        assert ia.get_directive() == "색상 분석 집중"

    def test_none_directive_does_not_crash(self):
        image = self._make_test_image()
        ia = ImageAnalysisAgent(directive=None)
        diag = ia.execute(image)
        assert isinstance(diag, ImageDiagnosis)


# ── 7. ParameterSearcher directive tests (no markers) ────────────────────────

class TestParameterSearcherDirective:
    def test_directive_does_not_change_search_results(self):
        image = np.ones((100, 100), dtype=np.uint8) * 200
        image[30:70, 30:70] = 50

        pc = PipelineComposer()
        pipelines = pc.execute(make_diagnosis())
        minimal = next(p for p in pipelines if p.name == "최소_전처리_파이프라인")

        pipeline1 = copy.deepcopy(minimal)
        pipeline2 = copy.deepcopy(minimal)

        ps1 = ParameterSearcher()
        result1 = ps1.execute(pipeline1, image)

        ps2 = ParameterSearcher(directive="다른 최적화 전략 사용")
        result2 = ps2.execute(pipeline2, image)

        assert result1.score == result2.score, (
            f"ParameterSearcher score must be deterministic regardless of directive. "
            f"Without: {result1.score}, with: {result2.score}"
        )

    def test_directive_is_stored(self):
        ps = ParameterSearcher(directive="최적화 지시")
        assert ps.get_directive() == "최적화 지시"


# ── 8. Orchestrator _distribute_directives tests (no markers, mock-based) ─────

class TestOrchestratorDistributeDirectives:
    def _create_mock_orchestrator(self) -> tuple[Orchestrator, dict[str, MagicMock]]:
        mocks: dict[str, MagicMock] = {k: MagicMock() for k in [
            "spec", "image_analysis", "pipeline_composer", "parameter_searcher",
            "vision_judge", "inspection_plan", "algorithm_selector",
            "algo_coder_inspection", "algo_coder_align",
            "code_validator", "test_agent_inspection", "test_agent_align",
            "evaluation_agent",
        ]}
        orch = Orchestrator(
            spec_agent=mocks["spec"],
            image_analysis_agent=mocks["image_analysis"],
            pipeline_composer=mocks["pipeline_composer"],
            parameter_searcher=mocks["parameter_searcher"],
            vision_judge_agent=mocks["vision_judge"],
            inspection_plan_agent=mocks["inspection_plan"],
            algorithm_selector=mocks["algorithm_selector"],
            algorithm_coder_inspection=mocks["algo_coder_inspection"],
            algorithm_coder_align=mocks["algo_coder_align"],
            code_validator=mocks["code_validator"],
            test_agent_inspection=mocks["test_agent_inspection"],
            test_agent_align=mocks["test_agent_align"],
            evaluation_agent=mocks["evaluation_agent"],
        )
        return orch, mocks

    def test_distribute_directives_routes_all_fields(self):
        orch, mocks = self._create_mock_orchestrator()

        directives = AgentDirectives(
            spec="사양 지시",
            image_analysis="이미지 분석 지시",
            pipeline_composer="Blob",
            vision_judge="시각 판단 지시",
            inspection_plan="검사 계획 지시",
            algorithm_coder="알고리즘 코더 지시",
            test="테스트 지시",
        )
        orch._distribute_directives(directives)

        mocks["spec"].set_directive.assert_called_once_with("사양 지시")
        mocks["image_analysis"].set_directive.assert_called_once_with("이미지 분석 지시")
        mocks["pipeline_composer"].set_directive.assert_called_once_with("Blob")
        mocks["vision_judge"].set_directive.assert_called_once_with("시각 판단 지시")
        mocks["inspection_plan"].set_directive.assert_called_once_with("검사 계획 지시")
        mocks["algo_coder_inspection"].set_directive.assert_called_once_with("알고리즘 코더 지시")
        mocks["algo_coder_align"].set_directive.assert_called_once_with("알고리즘 코더 지시")
        mocks["test_agent_inspection"].set_directive.assert_called_once_with("테스트 지시")
        mocks["test_agent_align"].set_directive.assert_called_once_with("테스트 지시")

    def test_distribute_directives_skips_none_fields(self):
        orch, mocks = self._create_mock_orchestrator()

        directives = AgentDirectives(spec="사양만", image_analysis=None, pipeline_composer=None)
        orch._distribute_directives(directives)

        mocks["spec"].set_directive.assert_called_once_with("사양만")
        mocks["image_analysis"].set_directive.assert_not_called()
        mocks["pipeline_composer"].set_directive.assert_not_called()

    def test_distribute_directives_none_does_nothing(self):
        orch, mocks = self._create_mock_orchestrator()
        orch._distribute_directives(None)

        for mock in mocks.values():
            mock.set_directive.assert_not_called()

    def test_algorithm_coder_directive_goes_to_both_coders(self):
        orch, mocks = self._create_mock_orchestrator()

        orch._distribute_directives(AgentDirectives(algorithm_coder="코더 지시"))

        mocks["algo_coder_inspection"].set_directive.assert_called_once_with("코더 지시")
        mocks["algo_coder_align"].set_directive.assert_called_once_with("코더 지시")

    def test_test_directive_goes_to_both_test_agents(self):
        orch, mocks = self._create_mock_orchestrator()

        orch._distribute_directives(AgentDirectives(test="테스트 지시"))

        mocks["test_agent_inspection"].set_directive.assert_called_once_with("테스트 지시")
        mocks["test_agent_align"].set_directive.assert_called_once_with("테스트 지시")


# ── 9. SpecAgent with directive (integration + e2e) ───────────────────────────

@pytest.mark.integration
@pytest.mark.e2e
class TestSpecAgentWithDirective:
    @pytest.mark.anyio
    async def test_spec_agent_with_directive_returns_valid_result(
        self, check_ollama_available
    ) -> None:
        agent = SpecAgent(directive="정확도를 최대한 높이는 방향으로 분석")
        result = await agent.execute(_PURPOSE)

        assert isinstance(result, SpecResult)
        assert isinstance(result.mode, InspectionMode)
        assert len(result.goal) > 0
        assert isinstance(result.success_criteria, dict)

    @pytest.mark.anyio
    async def test_spec_agent_without_directive_returns_valid_result(
        self, check_ollama_available
    ) -> None:
        agent = SpecAgent()
        result = await agent.execute(_PURPOSE)

        assert isinstance(result, SpecResult)
        assert isinstance(result.mode, InspectionMode)
        assert len(result.goal) > 0


# ── 10. VisionJudgeAgent with directive (integration + e2e) ──────────────────

@pytest.mark.integration
@pytest.mark.e2e
class TestVisionJudgeAgentWithDirective:
    @pytest.mark.anyio
    async def test_vision_judge_with_directive_returns_valid_result(
        self,
        check_ollama_available,
        sample_images: dict[str, np.ndarray],
    ) -> None:
        image = sample_images["OK_1"]
        agent = VisionJudgeAgent(directive="엣지 명확도를 중점으로 평가")
        result = await agent.execute(
            original_image=image,
            processed_image=image,
            purpose=_PURPOSE,
            pipeline_name="test_pipeline",
        )

        assert isinstance(result, JudgementResult)
        assert 0.0 <= result.visibility_score <= 1.0
        assert 0.0 <= result.separability_score <= 1.0
        assert 0.0 <= result.measurability_score <= 1.0
        assert isinstance(result.problems, list)
        assert isinstance(result.next_suggestion, str)

    @pytest.mark.anyio
    async def test_vision_judge_without_directive_returns_valid_result(
        self,
        check_ollama_available,
        sample_images: dict[str, np.ndarray],
    ) -> None:
        image = sample_images["OK_1"]
        agent = VisionJudgeAgent()
        result = await agent.execute(
            original_image=image,
            processed_image=image,
            purpose=_PURPOSE,
            pipeline_name="test_pipeline",
        )

        assert isinstance(result, JudgementResult)
        assert 0.0 <= result.visibility_score <= 1.0


# ── 11. InspectionPlanAgent with directive (integration + e2e) ────────────────

@pytest.mark.integration
@pytest.mark.e2e
class TestInspectionPlanAgentWithDirective:
    @pytest.mark.anyio
    async def test_inspection_plan_with_directive_returns_valid_result(
        self, check_ollama_available
    ) -> None:
        agent = InspectionPlanAgent(directive="BLOB 검출 위주로 계획 수립")
        result = await agent.execute(
            purpose=_PURPOSE,
            image_diagnosis_summary="surface=plastic, contrast=0.50",
        )

        assert isinstance(result, InspectionPlan)
        assert len(result.items) >= 1
        for item in result.items:
            assert item.id >= 1
            assert len(item.name) > 0
            assert item.method in list(AlgorithmCategory)

    @pytest.mark.anyio
    async def test_inspection_plan_without_directive_returns_valid_result(
        self, check_ollama_available
    ) -> None:
        agent = InspectionPlanAgent()
        result = await agent.execute(
            purpose=_PURPOSE,
            image_diagnosis_summary="surface=plastic, contrast=0.50",
        )

        assert isinstance(result, InspectionPlan)
        assert len(result.items) >= 1


# ── 12. Full Orchestrator with directives vs without (integration + e2e) ─────

@pytest.mark.integration
@pytest.mark.e2e
class TestOrchestratorWithDirectives:
    @pytest.mark.anyio
    async def test_orchestrator_executes_without_directives(
        self,
        check_ollama_available,
        sample_images: dict[str, np.ndarray],
        real_ollama_client: OllamaClient,
    ) -> None:
        orch = create_real_orchestrator(real_ollama_client)
        analysis_images = [sample_images["OK_1"]]
        test_images = [
            (sample_images["OK_1"], "OK_1.png"),
            (sample_images["NG_1"], "NG_1.png"),
        ]

        result = await orch.execute(
            purpose_text=_PURPOSE,
            analysis_images=analysis_images,
            test_images=test_images,
            config={"max_iteration": 1},
        )

        _assert_valid_inspection_result(result)

    @pytest.mark.anyio
    async def test_orchestrator_executes_with_directives(
        self,
        check_ollama_available,
        sample_images: dict[str, np.ndarray],
        real_ollama_client: OllamaClient,
    ) -> None:
        directives = AgentDirectives(
            spec="검사 목표에 집중하여 정확한 사양 추출",
            pipeline_composer="Blob",
            inspection_plan="Blob 검출 위주로 검사 항목 설계",
        )

        orch = create_real_orchestrator(real_ollama_client)
        analysis_images = [sample_images["OK_1"]]
        test_images = [
            (sample_images["OK_1"], "OK_1.png"),
            (sample_images["NG_1"], "NG_1.png"),
        ]

        result = await orch.execute(
            purpose_text=_PURPOSE,
            analysis_images=analysis_images,
            test_images=test_images,
            directives=directives,
            config={"max_iteration": 1},
        )

        _assert_valid_inspection_result(result)
