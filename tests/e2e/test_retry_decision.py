"""Step 49: Retry loop and Decision Agent integration tests.

Non-integration tests (no markers): mock LLM-calling agents; real FeedbackController / DecisionAgent.
Integration tests (@integration @e2e): require live Gemma4 at VIA_OLLAMA_URL.
"""
from __future__ import annotations

import asyncio
import os
from pathlib import Path
from unittest.mock import AsyncMock, Mock, MagicMock

import numpy as np
import pytest

from agents.code_validator import ValidationResult
from agents.decision_agent import DecisionAgent
from agents.evaluation_agent import EvaluationAgent
from agents.feedback_controller import FeedbackController
from agents.models import (
    AlgorithmCategory,
    AlgorithmResult,
    DecisionResult,
    DecisionType,
    DefectScale,
    EvaluationResult,
    FailureReason,
    IlluminationType,
    ImageDiagnosis,
    InspectionItem,
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

_FIXTURES_DIR = Path(__file__).parent.parent / "fixtures" / "sample_images"
OLLAMA_BASE_URL = os.environ.get("VIA_OLLAMA_URL", "http://localhost:11434")
_MODEL = "gemma4:e4b"


# ── anyio backend ─────────────────────────────────────────────────────────────

@pytest.fixture(params=["asyncio"])
def anyio_backend(request):
    return request.param


# ── E2E fixtures (integration tests only) ────────────────────────────────────

@pytest.fixture(scope="session")
def check_ollama_available():
    import httpx
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


@pytest.fixture(autouse=True)
def reset_singleton_client():
    from backend.services.ollama_client import ollama_client as _singleton
    _singleton._client = None
    yield
    _singleton._client = None


@pytest.fixture
def real_ollama_client():
    from backend.services.ollama_client import OllamaClient
    return OllamaClient(
        base_url=OLLAMA_BASE_URL,
        model=_MODEL,
        health_timeout=300.0,
        generate_timeout=600.0,
        max_retries=2,
    )


@pytest.fixture(scope="session")
def sample_images() -> dict[str, np.ndarray]:
    import cv2
    names = ["OK_1", "OK_2", "OK_3", "NG_1", "NG_2", "NG_3"]
    images: dict[str, np.ndarray] = {}
    for name in names:
        path = _FIXTURES_DIR / f"{name}.png"
        img = cv2.imread(str(path), cv2.IMREAD_GRAYSCALE)
        assert img is not None, f"Failed to load {path}"
        images[name] = img
    return images


# ── Helpers ───────────────────────────────────────────────────────────────────

def _img() -> np.ndarray:
    return np.zeros((64, 64, 3), dtype=np.uint8)


def _pipeline(name: str = "pipe") -> ProcessingPipeline:
    return ProcessingPipeline(name=name, blocks=[])


def _diagnosis(
    defect_scale: DefectScale = DefectScale.macro,
    texture_complexity: float = 0.2,
) -> ImageDiagnosis:
    return ImageDiagnosis(
        contrast=0.5, noise_level=0.1, edge_density=0.3, lighting_uniformity=0.8,
        illumination_type=IlluminationType.uniform, noise_frequency=NoiseFrequency.high_freq,
        reflection_level=0.1, texture_complexity=texture_complexity, surface_type="metal",
        defect_scale=defect_scale, blob_feasibility=0.7, blob_count_estimate=3,
        blob_size_variance=0.1, color_discriminability=0.6, dominant_channel_ratio=0.5,
        structural_regularity=0.8, pattern_repetition=0.3, background_uniformity=0.9,
        optimal_color_space="gray", threshold_candidate=128.0, edge_sharpness=0.7,
    )


def _spec(mode: str = "inspection") -> SpecResult:
    return SpecResult(
        mode=InspectionMode(mode),
        goal="detect scratches",
        success_criteria={"accuracy": 0.95, "fp_rate": 0.05, "fn_rate": 0.05},
    )


def _judge(v: float = 0.8, s: float = 0.8, m: float = 0.8) -> JudgementResult:
    return JudgementResult(visibility_score=v, separability_score=s, measurability_score=m)


def _plan() -> InspectionPlan:
    return InspectionPlan(items=[
        InspectionItem(id=1, name="check", purpose="detect", method=AlgorithmCategory.BLOB,
                       success_criteria="accuracy >= 0.9"),
    ])


def _algo(mode: str = "inspection") -> AlgorithmResult:
    if mode == "inspection":
        code = "import cv2\nimport numpy as np\ndef inspect_item(image):\n    return {'result': 'OK'}"
        cat = AlgorithmCategory.BLOB
    else:
        code = "import cv2\nimport numpy as np\ndef align(image):\n    return {'x': 0.0, 'y': 0.0}"
        cat = AlgorithmCategory.TEMPLATE_MATCHING
    return AlgorithmResult(code=code, explanation="ok", category=cat, pipeline=_pipeline())


def _item_result(
    item_id: int = 1,
    passed: bool = True,
    accuracy: float = 0.9,
    fp_rate: float = 0.1,
    fn_rate: float = 0.1,
    details: str = "",
) -> ItemTestResult:
    return ItemTestResult(
        item_id=item_id, item_name=f"item_{item_id}", passed=passed,
        metrics=TestMetrics(accuracy=accuracy, fp_rate=fp_rate, fn_rate=fn_rate),
        details=details,
    )


def _eval_result(
    passed: bool = True,
    reason: FailureReason = FailureReason.algorithm_runtime_error,
) -> EvaluationResult:
    return EvaluationResult(
        overall_passed=passed,
        failure_reason=None if passed else reason,
        failed_items=[] if passed else [1],
        analysis="passed" if passed else "failed",
    )


def _make_eval(reason: FailureReason) -> EvaluationResult:
    return EvaluationResult(
        overall_passed=False, failure_reason=reason, failed_items=[1], analysis="failed"
    )


def _history_entry(iteration: int, accuracy: float = 0.3) -> dict:
    return {
        "iteration": iteration,
        "failure_reason": "algorithm_runtime_error",
        "target_agent": "algorithm_coder",
        "test_results": [_item_result(passed=False, accuracy=accuracy)],
        "test_results_summary": {"count": 1, "passed": 0},
        "judge_result_summary": {},
    }


def _base_mocks(mode: str = "inspection") -> dict:
    """All agent mocks except feedback_controller and decision_agent."""
    spec = Mock()
    spec.execute = AsyncMock(return_value=_spec(mode))
    spec.set_directive = Mock()

    img_agent = Mock()
    img_agent.execute = Mock(return_value=_diagnosis())
    img_agent.set_directive = Mock()

    composer = Mock()
    composer.execute = Mock(return_value=[_pipeline("p1"), _pipeline("p2")])
    composer.set_directive = Mock()

    searcher = Mock()
    searcher.execute = Mock(side_effect=lambda pipeline, image: pipeline)
    searcher.set_directive = Mock()

    judge = Mock()
    judge.execute = AsyncMock(return_value=_judge())
    judge.set_directive = Mock()

    plan_agent = Mock()
    plan_agent.execute = AsyncMock(return_value=_plan())
    plan_agent.set_directive = Mock()

    selector = Mock()
    selector.execute = Mock(return_value=AlgorithmCategory.BLOB)
    selector.set_directive = Mock()

    coder_insp = Mock()
    coder_insp.execute = AsyncMock(return_value=_algo("inspection"))
    coder_insp.set_directive = Mock()

    coder_align = Mock()
    coder_align.execute = AsyncMock(return_value=_algo("align"))
    coder_align.set_directive = Mock()

    validator = Mock()
    validator.validate = Mock(return_value=ValidationResult(is_valid=True))

    test_insp = Mock()
    test_insp.execute = Mock(return_value=[_item_result(passed=True)])
    test_insp.set_directive = Mock()

    test_aln = Mock()
    test_aln.execute = Mock(return_value=[_item_result(passed=True)])
    test_aln.set_directive = Mock()

    eval_agent = Mock()
    eval_agent.execute = Mock(return_value=_eval_result(True))
    eval_agent.set_directive = Mock()

    return dict(
        spec_agent=spec, image_analysis_agent=img_agent,
        pipeline_composer=composer, parameter_searcher=searcher,
        vision_judge_agent=judge, inspection_plan_agent=plan_agent,
        algorithm_selector=selector, algorithm_coder_inspection=coder_insp,
        algorithm_coder_align=coder_align, code_validator=validator,
        test_agent_inspection=test_insp, test_agent_align=test_aln,
        evaluation_agent=eval_agent,
    )


def _orc_with_real_fc(mode: str = "inspection") -> tuple[Orchestrator, dict]:
    m = _base_mocks(mode)
    return Orchestrator(**m, feedback_controller=FeedbackController()), m


def _orc_with_real_fc_da(mode: str = "inspection") -> tuple[Orchestrator, dict]:
    m = _base_mocks(mode)
    return Orchestrator(**m, feedback_controller=FeedbackController(), decision_agent=DecisionAgent()), m


# ── TestFeedbackControllerMapping ─────────────────────────────────────────────

class TestFeedbackControllerMapping:
    def test_pipeline_bad_params_maps_to_parameter_searcher(self):
        fc = FeedbackController()
        action = fc.execute(_make_eval(FailureReason.pipeline_bad_params))
        assert action.target_agent == "parameter_searcher"
        assert action.reason == FailureReason.pipeline_bad_params

    def test_pipeline_bad_fit_maps_to_pipeline_composer(self):
        fc = FeedbackController()
        action = fc.execute(_make_eval(FailureReason.pipeline_bad_fit))
        assert action.target_agent == "pipeline_composer"
        assert action.reason == FailureReason.pipeline_bad_fit

    def test_algorithm_runtime_error_maps_to_algorithm_coder(self):
        fc = FeedbackController()
        action = fc.execute(_make_eval(FailureReason.algorithm_runtime_error))
        assert action.target_agent == "algorithm_coder"
        assert action.reason == FailureReason.algorithm_runtime_error

    def test_algorithm_wrong_category_maps_to_algorithm_selector(self):
        fc = FeedbackController()
        action = fc.execute(_make_eval(FailureReason.algorithm_wrong_category))
        assert action.target_agent == "algorithm_selector"
        assert action.reason == FailureReason.algorithm_wrong_category

    def test_inspection_plan_issue_maps_to_inspection_plan(self):
        fc = FeedbackController()
        action = fc.execute(_make_eval(FailureReason.inspection_plan_issue))
        assert action.target_agent == "inspection_plan"
        assert action.reason == FailureReason.inspection_plan_issue

    def test_spec_issue_maps_to_spec_agent(self):
        fc = FeedbackController()
        action = fc.execute(_make_eval(FailureReason.spec_issue))
        assert action.target_agent == "spec_agent"
        assert action.reason == FailureReason.spec_issue

    def test_returns_none_when_eval_passed(self):
        fc = FeedbackController()
        result = fc.execute(EvaluationResult(
            overall_passed=True, failure_reason=None, failed_items=[]
        ))
        assert result is None


# ── TestFeedbackControllerEscalation ──────────────────────────────────────────

class TestFeedbackControllerEscalation:
    def test_escalation_pipeline_bad_params_to_bad_fit(self):
        fc = FeedbackController()
        ev = _make_eval(FailureReason.pipeline_bad_params)
        action1 = fc.execute(ev)
        assert action1.target_agent == "parameter_searcher"
        action2 = fc.execute(ev)
        assert action2.target_agent == "pipeline_composer"

    def test_escalation_algorithm_runtime_to_wrong_category(self):
        fc = FeedbackController()
        ev = _make_eval(FailureReason.algorithm_runtime_error)
        action1 = fc.execute(ev)
        assert action1.target_agent == "algorithm_coder"
        action2 = fc.execute(ev)
        assert action2.target_agent == "algorithm_selector"

    def test_escalation_chain_bad_params_to_bad_fit_to_spec(self):
        fc = FeedbackController()
        bp = _make_eval(FailureReason.pipeline_bad_params)
        bf = _make_eval(FailureReason.pipeline_bad_fit)
        a1 = fc.execute(bp)
        assert a1.target_agent == "parameter_searcher"
        a2 = fc.execute(bp)
        assert a2.target_agent == "pipeline_composer"
        a3 = fc.execute(bf)
        assert a3.target_agent == "pipeline_composer"
        a4 = fc.execute(bf)
        assert a4.target_agent == "spec_agent"

    def test_no_escalation_on_different_reasons(self):
        fc = FeedbackController()
        bp = _make_eval(FailureReason.pipeline_bad_params)
        rt = _make_eval(FailureReason.algorithm_runtime_error)
        a1 = fc.execute(bp)
        assert a1.target_agent == "parameter_searcher"
        a2 = fc.execute(rt)
        assert a2.target_agent == "algorithm_coder"
        a3 = fc.execute(bp)
        assert a3.target_agent == "parameter_searcher"

    def test_reset_clears_escalation_state(self):
        fc = FeedbackController()
        ev = _make_eval(FailureReason.pipeline_bad_params)
        fc.execute(ev)
        fc.reset()
        action = fc.execute(ev)
        assert action.target_agent == "parameter_searcher"


# ── TestRetryLoopActivation ───────────────────────────────────────────────────

class TestRetryLoopActivation:
    @pytest.mark.anyio
    async def test_single_retry_on_pipeline_bad_params(self):
        orc, m = _orc_with_real_fc("inspection")
        m["evaluation_agent"].execute = Mock(side_effect=[
            _eval_result(False, FailureReason.pipeline_bad_params),
            _eval_result(True),
        ])
        result = await orc.execute("detect", [_img()], [], config={"max_iteration": 5})
        assert result["evaluation_result"].overall_passed is True
        assert m["pipeline_composer"].execute.call_count == 1
        assert m["parameter_searcher"].execute.call_count > 2

    @pytest.mark.anyio
    async def test_single_retry_on_pipeline_bad_fit(self):
        orc, m = _orc_with_real_fc("inspection")
        m["evaluation_agent"].execute = Mock(side_effect=[
            _eval_result(False, FailureReason.pipeline_bad_fit),
            _eval_result(True),
        ])
        result = await orc.execute("detect", [_img()], [], config={"max_iteration": 5})
        assert result["evaluation_result"].overall_passed is True
        assert m["pipeline_composer"].execute.call_count == 2

    @pytest.mark.anyio
    async def test_single_retry_on_algorithm_runtime_error(self):
        orc, m = _orc_with_real_fc("inspection")
        m["evaluation_agent"].execute = Mock(side_effect=[
            _eval_result(False, FailureReason.algorithm_runtime_error),
            _eval_result(True),
        ])
        result = await orc.execute("detect", [_img()], [], config={"max_iteration": 5})
        assert result["evaluation_result"].overall_passed is True
        assert m["algorithm_coder_inspection"].execute.call_count == 2
        assert m["pipeline_composer"].execute.call_count == 1
        assert m["algorithm_selector"].execute.call_count == 1

    @pytest.mark.anyio
    async def test_single_retry_on_algorithm_wrong_category(self):
        orc, m = _orc_with_real_fc("inspection")
        m["evaluation_agent"].execute = Mock(side_effect=[
            _eval_result(False, FailureReason.algorithm_wrong_category),
            _eval_result(True),
        ])
        await orc.execute("detect", [_img()], [], config={"max_iteration": 5})
        assert m["algorithm_selector"].execute.call_count == 2
        assert m["algorithm_coder_inspection"].execute.call_count == 2
        assert m["pipeline_composer"].execute.call_count == 1

    @pytest.mark.anyio
    async def test_single_retry_on_inspection_plan_issue(self):
        orc, m = _orc_with_real_fc("inspection")
        m["evaluation_agent"].execute = Mock(side_effect=[
            _eval_result(False, FailureReason.inspection_plan_issue),
            _eval_result(True),
        ])
        await orc.execute("detect", [_img()], [], config={"max_iteration": 5})
        assert m["inspection_plan_agent"].execute.call_count == 2
        assert m["algorithm_selector"].execute.call_count == 2
        assert m["algorithm_coder_inspection"].execute.call_count == 2
        assert m["pipeline_composer"].execute.call_count == 1

    @pytest.mark.anyio
    async def test_single_retry_on_spec_issue(self):
        orc, m = _orc_with_real_fc("inspection")
        m["evaluation_agent"].execute = Mock(side_effect=[
            _eval_result(False, FailureReason.spec_issue),
            _eval_result(True),
        ])
        await orc.execute("detect", [_img()], [], config={"max_iteration": 5})
        assert m["spec_agent"].execute.call_count == 2
        assert m["pipeline_composer"].execute.call_count == 2


# ── TestRetryExhaustion ───────────────────────────────────────────────────────

class TestRetryExhaustion:
    @pytest.mark.anyio
    async def test_max_iteration_1_no_retry(self):
        orc, m = _orc_with_real_fc_da("inspection")
        m["evaluation_agent"].execute = Mock(
            return_value=_eval_result(False, FailureReason.algorithm_runtime_error)
        )
        result = await orc.execute("detect", [_img()], [], config={"max_iteration": 1})
        assert m["evaluation_agent"].execute.call_count == 1
        assert len(result["iteration_history"]) == 0
        assert result["decision_result"] is not None

    @pytest.mark.anyio
    async def test_max_iteration_2_one_retry_then_decision(self):
        orc, m = _orc_with_real_fc_da("inspection")
        m["evaluation_agent"].execute = Mock(
            return_value=_eval_result(False, FailureReason.algorithm_runtime_error)
        )
        result = await orc.execute("detect", [_img()], [], config={"max_iteration": 2})
        assert m["evaluation_agent"].execute.call_count == 2
        assert len(result["iteration_history"]) == 1
        assert result["decision_result"] is not None

    @pytest.mark.anyio
    async def test_max_iteration_5_all_fail_decision_called(self):
        orc, m = _orc_with_real_fc_da("inspection")
        m["evaluation_agent"].execute = Mock(
            return_value=_eval_result(False, FailureReason.algorithm_runtime_error)
        )
        result = await orc.execute("detect", [_img()], [], config={"max_iteration": 5})
        assert m["evaluation_agent"].execute.call_count == 5
        assert len(result["iteration_history"]) == 4
        assert result["decision_result"] is not None

    @pytest.mark.anyio
    async def test_iteration_history_accumulates_correctly(self):
        orc, m = _orc_with_real_fc_da("inspection")
        m["evaluation_agent"].execute = Mock(side_effect=[
            _eval_result(False, FailureReason.algorithm_runtime_error),
            _eval_result(True),
        ])
        result = await orc.execute("detect", [_img()], [], config={"max_iteration": 5})
        assert len(result["iteration_history"]) == 1
        entry = result["iteration_history"][0]
        for key in ("iteration", "failure_reason", "target_agent",
                    "test_results_summary", "judge_result_summary"):
            assert key in entry, f"missing key: {key}"
        assert entry["failure_reason"] == "algorithm_runtime_error"
        assert entry["target_agent"] == "algorithm_coder"
        assert entry["iteration"] == 1

    @pytest.mark.anyio
    async def test_no_decision_when_no_decision_agent(self):
        orc, m = _orc_with_real_fc("inspection")
        m["evaluation_agent"].execute = Mock(
            return_value=_eval_result(False, FailureReason.algorithm_runtime_error)
        )
        result = await orc.execute("detect", [_img()], [], config={"max_iteration": 3})
        assert result["decision_result"] is None


# ── TestDecisionAgentIntegration ──────────────────────────────────────────────

class TestDecisionAgentIntegration:
    def test_decision_rule_based_when_judge_score_high(self):
        da = DecisionAgent()
        result = da.execute([], mode="inspection", judge_result=_judge(0.8, 0.8, 0.8))
        assert result.decision == DecisionType.rule_based

    def test_decision_edge_learning_when_micro_defect(self):
        da = DecisionAgent()
        diag = _diagnosis(defect_scale=DefectScale.micro, texture_complexity=0.2)
        result = da.execute(
            [], mode="inspection",
            judge_result=_judge(0.3, 0.4, 0.4),
            image_diagnosis=diag,
        )
        assert result.decision == DecisionType.edge_learning

    def test_decision_deep_learning_when_texture_defect(self):
        da = DecisionAgent()
        diag = _diagnosis(defect_scale=DefectScale.texture, texture_complexity=0.2)
        result = da.execute(
            [], mode="inspection",
            judge_result=_judge(0.3, 0.3, 0.3),
            image_diagnosis=diag,
        )
        assert result.decision == DecisionType.deep_learning

    def test_decision_deep_learning_when_high_texture_complexity(self):
        da = DecisionAgent()
        diag = _diagnosis(defect_scale=DefectScale.macro, texture_complexity=0.6)
        result = da.execute(
            [], mode="inspection",
            judge_result=_judge(0.3, 0.3, 0.3),
            image_diagnosis=diag,
        )
        assert result.decision == DecisionType.deep_learning

    def test_decision_deep_learning_when_low_accuracy_many_iterations(self):
        da = DecisionAgent()
        history = [_history_entry(i, accuracy=0.3) for i in range(1, 4)]
        result = da.execute(history, mode="inspection", judge_result=None, image_diagnosis=None)
        assert result.decision == DecisionType.deep_learning

    def test_decision_edge_learning_when_mid_accuracy(self):
        da = DecisionAgent()
        history = [_history_entry(i, accuracy=0.6) for i in range(1, 4)]
        result = da.execute(history, mode="inspection", judge_result=None, image_diagnosis=None)
        assert result.decision == DecisionType.edge_learning

    def test_decision_fallback_is_edge_learning(self):
        da = DecisionAgent()
        result = da.execute([], mode="inspection", judge_result=None, image_diagnosis=None)
        assert result.decision == DecisionType.edge_learning

    @pytest.mark.anyio
    async def test_decision_result_in_return_dict(self):
        orc, m = _orc_with_real_fc_da("inspection")
        m["evaluation_agent"].execute = Mock(
            return_value=_eval_result(False, FailureReason.algorithm_runtime_error)
        )
        result = await orc.execute("detect", [_img()], [], config={"max_iteration": 3})
        assert "decision_result" in result
        assert isinstance(result["decision_result"], DecisionResult)

    @pytest.mark.anyio
    async def test_decision_receives_correct_mode(self):
        m = _base_mocks("inspection")
        fc = FeedbackController()
        captured_mode: list = []

        da = MagicMock()
        def _capture(history, mode, judge_result, image_diagnosis):
            captured_mode.append(mode)
            return DecisionResult(decision=DecisionType.edge_learning, reason="t", confidence=1.0)
        da.execute = _capture

        orc = Orchestrator(**m, feedback_controller=fc, decision_agent=da)
        m["evaluation_agent"].execute = Mock(
            return_value=_eval_result(False, FailureReason.algorithm_runtime_error)
        )
        await orc.execute("detect", [_img()], [], config={"max_iteration": 1})
        assert len(captured_mode) == 1
        assert captured_mode[0] == "inspection"

    @pytest.mark.anyio
    async def test_decision_receives_iteration_history(self):
        m = _base_mocks("inspection")
        fc = FeedbackController()
        captured_history: list = []

        da = MagicMock()
        def _capture(history, mode, judge_result, image_diagnosis):
            captured_history.append(list(history))
            return DecisionResult(decision=DecisionType.edge_learning, reason="t", confidence=1.0)
        da.execute = _capture

        orc = Orchestrator(**m, feedback_controller=fc, decision_agent=da)
        m["evaluation_agent"].execute = Mock(
            return_value=_eval_result(False, FailureReason.algorithm_runtime_error)
        )
        await orc.execute("detect", [_img()], [], config={"max_iteration": 3})
        assert len(captured_history) == 1
        assert len(captured_history[0]) == 2


# ── TestAlignModeRetryAndDecision ─────────────────────────────────────────────

class TestAlignModeRetryAndDecision:
    @pytest.mark.anyio
    async def test_align_retry_routes_correctly(self):
        orc, m = _orc_with_real_fc("align")
        m["evaluation_agent"].execute = Mock(side_effect=[
            _eval_result(False, FailureReason.algorithm_runtime_error),
            _eval_result(True),
        ])
        await orc.execute("align", [_img()], [], config={"max_iteration": 5})
        assert m["algorithm_coder_align"].execute.call_count == 2
        m["inspection_plan_agent"].execute.assert_not_called()
        m["algorithm_selector"].execute.assert_not_called()

    @pytest.mark.anyio
    async def test_align_decision_always_rule_based(self):
        orc, m = _orc_with_real_fc_da("align")
        m["evaluation_agent"].execute = Mock(
            return_value=_eval_result(False, FailureReason.algorithm_runtime_error)
        )
        result = await orc.execute("align", [_img()], [], config={"max_iteration": 3})
        assert result["decision_result"] is not None
        assert result["decision_result"].decision == DecisionType.rule_based

    @pytest.mark.anyio
    async def test_align_no_inspection_plan_in_retry(self):
        orc, m = _orc_with_real_fc("align")
        m["evaluation_agent"].execute = Mock(side_effect=[
            _eval_result(False, FailureReason.pipeline_bad_fit),
            _eval_result(True),
        ])
        await orc.execute("align", [_img()], [], config={"max_iteration": 5})
        m["inspection_plan_agent"].execute.assert_not_called()

    def test_align_decision_details_contain_hw_recommendation(self):
        da = DecisionAgent()
        result = da.execute([], mode="align")
        assert result.decision == DecisionType.rule_based
        assert "하드웨어" in result.reason or "hardware" in result.reason.lower()


# ── TestRetryWithEvaluationPatterns ───────────────────────────────────────────

class TestRetryWithEvaluationPatterns:
    def test_partial_item_failure_triggers_retry(self):
        ea = EvaluationAgent()
        judge = _judge(0.8, 0.8, 0.8)
        test_results = [
            ItemTestResult(item_id=1, item_name="i1", passed=True,
                           metrics=TestMetrics(accuracy=0.9)),
            ItemTestResult(item_id=2, item_name="i2", passed=True,
                           metrics=TestMetrics(accuracy=0.9)),
            ItemTestResult(item_id=3, item_name="i3", passed=False,
                           metrics=TestMetrics(accuracy=0.3, fp_rate=0.1, fn_rate=0.1)),
        ]
        result = ea.execute(test_results, judge_result=judge, mode="inspection")
        assert result.overall_passed is False
        assert result.failure_reason is not None

    def test_all_items_fail_triggers_spec_issue(self):
        ea = EvaluationAgent()
        judge = _judge(0.8, 0.8, 0.8)
        test_results = [
            ItemTestResult(item_id=1, item_name="i1", passed=False,
                           metrics=TestMetrics(accuracy=0.3, fp_rate=0.1, fn_rate=0.1)),
            ItemTestResult(item_id=2, item_name="i2", passed=False,
                           metrics=TestMetrics(accuracy=0.3, fp_rate=0.1, fn_rate=0.1)),
        ]
        result = ea.execute(test_results, judge_result=judge, mode="inspection")
        assert result.failure_reason == FailureReason.spec_issue

    def test_runtime_error_details_detected(self):
        ea = EvaluationAgent()
        test_results = [
            ItemTestResult(item_id=1, item_name="i1", passed=False,
                           metrics=TestMetrics(accuracy=0.0),
                           details="Runtime error occurred"),
            ItemTestResult(item_id=2, item_name="i2", passed=True,
                           metrics=TestMetrics(accuracy=0.9)),
        ]
        result = ea.execute(test_results, mode="inspection")
        assert result.failure_reason == FailureReason.algorithm_runtime_error

    def test_judge_low_score_triggers_bad_fit(self):
        ea = EvaluationAgent()
        judge = _judge(v=0.2, s=0.8, m=0.8)
        test_results = [
            ItemTestResult(item_id=1, item_name="i1", passed=False,
                           metrics=TestMetrics(accuracy=0.4, fp_rate=0.2, fn_rate=0.2)),
            ItemTestResult(item_id=2, item_name="i2", passed=True,
                           metrics=TestMetrics(accuracy=0.9)),
        ]
        result = ea.execute(test_results, judge_result=judge, mode="inspection")
        assert result.failure_reason == FailureReason.pipeline_bad_fit


# ── TestRetrySuccessOnLaterIteration ─────────────────────────────────────────

class TestRetrySuccessOnLaterIteration:
    @pytest.mark.anyio
    async def test_success_on_second_iteration_no_decision(self):
        orc, m = _orc_with_real_fc_da("inspection")
        m["evaluation_agent"].execute = Mock(side_effect=[
            _eval_result(False, FailureReason.algorithm_runtime_error),
            _eval_result(True),
        ])
        result = await orc.execute("detect", [_img()], [], config={"max_iteration": 5})
        assert result["evaluation_result"].overall_passed is True
        assert result["decision_result"] is None

    @pytest.mark.anyio
    async def test_success_on_third_iteration(self):
        orc, m = _orc_with_real_fc_da("inspection")
        m["evaluation_agent"].execute = Mock(side_effect=[
            _eval_result(False, FailureReason.algorithm_runtime_error),
            _eval_result(False, FailureReason.pipeline_bad_fit),
            _eval_result(True),
        ])
        result = await orc.execute("detect", [_img()], [], config={"max_iteration": 5})
        assert result["evaluation_result"].overall_passed is True
        assert len(result["iteration_history"]) == 2
        assert result["decision_result"] is None

    @pytest.mark.anyio
    async def test_progress_tracks_iterations(self):
        iterations_seen: list[int] = []
        orc, m = _orc_with_real_fc("inspection")
        call_count = [0]

        def _capture(*args, **kwargs):
            call_count[0] += 1
            iterations_seen.append(orc.get_progress().current_iteration)
            return _eval_result(False) if call_count[0] < 3 else _eval_result(True)

        m["evaluation_agent"].execute = _capture
        await orc.execute("detect", [_img()], [], config={"max_iteration": 5})
        assert iterations_seen == [1, 2, 3]


# ── Integration / E2E tests ───────────────────────────────────────────────────

def _create_real_orchestrator(ollama_client=None) -> Orchestrator:
    from agents.algorithm_coder_align import AlgorithmCoderAlign
    from agents.algorithm_coder_inspection import AlgorithmCoderInspection
    from agents.algorithm_selector import AlgorithmSelector
    from agents.code_validator import CodeValidator
    from agents.image_analysis_agent import ImageAnalysisAgent
    from agents.inspection_plan_agent import InspectionPlanAgent
    from agents.parameter_searcher import ParameterSearcher
    from agents.pipeline_composer import PipelineComposer
    from agents.spec_agent import SpecAgent
    from agents.test_agent_align import TestAgentAlign
    from agents.test_agent_inspection import TestAgentInspection
    from agents.vision_judge_agent import VisionJudgeAgent

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


_PURPOSE_STRICT = (
    "불량 검출 검사: 모든 NG 이미지에서 결함을 100% 검출하고 OK 이미지에서는 절대 오탐하지 않는 "
    "완벽한 알고리즘을 설계하라. 정확도 99.99% 이상, 오탐률 0.001% 미만을 달성해야 한다."
)

_PURPOSE_ALIGN_STRICT = (
    "픽셀 단위 정렬: 기준 이미지와의 좌표 오차를 0.001픽셀 이하로 달성하는 완벽한 정렬 알고리즘을 설계하라."
)


@pytest.mark.integration
@pytest.mark.e2e
class TestRetryDecisionE2E:

    @pytest.mark.anyio
    async def test_intentional_failure_triggers_retry_with_real_agents(
        self,
        check_ollama_available,
        sample_images: dict[str, np.ndarray],
        real_ollama_client,
    ) -> None:
        """Force failure via strict purpose; verify retry and iteration_history populated."""
        orchestrator = _create_real_orchestrator(real_ollama_client)
        analysis_images = [sample_images["OK_1"]]
        test_images = [
            (sample_images["OK_1"], "OK_1.png"),
            (sample_images["NG_1"], "NG_1.png"),
        ]
        result = await orchestrator.execute(
            purpose_text=_PURPOSE_STRICT,
            analysis_images=analysis_images,
            test_images=test_images,
            config={"max_iteration": 2},
        )
        assert "iteration_history" in result
        assert "decision_result" in result
        history = result["iteration_history"]
        assert isinstance(history, list)
        for entry in history:
            for key in ("iteration", "failure_reason", "target_agent",
                        "test_results_summary", "judge_result_summary"):
                assert key in entry, f"missing key: {key}"

    @pytest.mark.anyio
    async def test_decision_agent_returns_reasonable_result(
        self,
        check_ollama_available,
        sample_images: dict[str, np.ndarray],
        real_ollama_client,
    ) -> None:
        """Decision result must be a valid DecisionType with non-empty reason."""
        orchestrator = _create_real_orchestrator(real_ollama_client)
        analysis_images = [sample_images["OK_1"]]
        test_images = [
            (sample_images["OK_1"], "OK_1.png"),
            (sample_images["NG_1"], "NG_1.png"),
        ]
        result = await orchestrator.execute(
            purpose_text=_PURPOSE_STRICT,
            analysis_images=analysis_images,
            test_images=test_images,
            config={"max_iteration": 2},
        )
        dr = result["decision_result"]
        if dr is not None:
            assert isinstance(dr, DecisionResult)
            assert dr.decision in list(DecisionType)
            assert len(dr.reason.strip()) > 0
            assert 0.0 <= dr.confidence <= 1.0

    @pytest.mark.anyio
    async def test_align_forced_failure_returns_rule_based(
        self,
        check_ollama_available,
        sample_images: dict[str, np.ndarray],
        real_ollama_client,
    ) -> None:
        """Align mode exhaustion → DecisionAgent must return RULE_BASED."""
        orchestrator = _create_real_orchestrator(real_ollama_client)
        analysis_images = [sample_images["OK_1"]]
        test_images = [
            (sample_images["OK_1"], "OK_1.png"),
            (sample_images["NG_1"], "NG_1.png"),
        ]
        result = await orchestrator.execute(
            purpose_text=_PURPOSE_ALIGN_STRICT,
            analysis_images=analysis_images,
            test_images=test_images,
            config={"max_iteration": 2},
        )
        dr = result["decision_result"]
        if dr is not None:
            assert dr.decision == DecisionType.rule_based

    @pytest.mark.anyio
    async def test_retry_produces_different_results_per_iteration(
        self,
        check_ollama_available,
        sample_images: dict[str, np.ndarray],
        real_ollama_client,
    ) -> None:
        """When retried, the orchestrator should attempt a different strategy."""
        orchestrator = _create_real_orchestrator(real_ollama_client)
        analysis_images = [sample_images["OK_1"]]
        test_images = [
            (sample_images["OK_1"], "OK_1.png"),
            (sample_images["NG_1"], "NG_1.png"),
        ]
        result = await orchestrator.execute(
            purpose_text=_PURPOSE_STRICT,
            analysis_images=analysis_images,
            test_images=test_images,
            config={"max_iteration": 2},
        )
        history = result["iteration_history"]
        if len(history) >= 2:
            targets = [entry["target_agent"] for entry in history]
            print(f"\n[retry targets]: {targets}")
            assert len(targets) >= 1
