"""Step 49 bugfix: Orchestrator graceful exception handling for algorithm_coder and inspection_plan."""
from __future__ import annotations

from unittest.mock import AsyncMock, Mock

import numpy as np
import pytest

from agents.code_validator import ValidationResult
from agents.models import (
    AlgorithmCategory,
    AlgorithmResult,
    DefectScale,
    EvaluationResult,
    FailureReason,
    FeedbackAction,
    IlluminationType,
    ImageDiagnosis,
    InspectionItem,
    InspectionMode,
    InspectionPlan,
    JudgementResult,
    NoiseFrequency,
    ProcessingPipeline,
    SpecResult,
    TestMetrics,
)
from agents.orchestrator import Orchestrator


@pytest.fixture(params=["asyncio"])
def anyio_backend(request):
    return request.param


# ── Helpers ───────────────────────────────────────────────────────────────────

def _img() -> np.ndarray:
    return np.zeros((64, 64, 3), dtype=np.uint8)


def _pipeline(name: str = "pipe") -> ProcessingPipeline:
    return ProcessingPipeline(name=name, blocks=[])


def _diagnosis() -> ImageDiagnosis:
    return ImageDiagnosis(
        contrast=0.5, noise_level=0.1, edge_density=0.3, lighting_uniformity=0.8,
        illumination_type=IlluminationType.uniform, noise_frequency=NoiseFrequency.high_freq,
        reflection_level=0.1, texture_complexity=0.2, surface_type="metal",
        defect_scale=DefectScale.macro, blob_feasibility=0.7, blob_count_estimate=3,
        blob_size_variance=0.1, color_discriminability=0.6, dominant_channel_ratio=0.5,
        structural_regularity=0.8, pattern_repetition=0.3, background_uniformity=0.9,
        optimal_color_space="gray", threshold_candidate=128.0, edge_sharpness=0.7,
    )


def _spec(mode: str = "inspection") -> SpecResult:
    return SpecResult(
        mode=InspectionMode(mode),
        goal="detect scratches",
        success_criteria={"accuracy": 0.95},
    )


def _judge() -> JudgementResult:
    return JudgementResult(visibility_score=0.8, separability_score=0.8, measurability_score=0.8)


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


def _eval_passed() -> EvaluationResult:
    return EvaluationResult(overall_passed=True, failure_reason=None, failed_items=[], analysis="ok")


def _feedback(target: str, reason: FailureReason) -> FeedbackAction:
    return FeedbackAction(target_agent=target, reason=reason, context={})


def _mocks(mode: str = "inspection") -> dict:
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
    test_insp.execute = Mock(return_value=[])
    test_insp.set_directive = Mock()

    test_aln = Mock()
    test_aln.execute = Mock(return_value=[])
    test_aln.set_directive = Mock()

    eval_agent = Mock()
    eval_agent.execute = Mock(return_value=_eval_passed())
    eval_agent.set_directive = Mock()

    fc = Mock()
    fc.reset = Mock()
    fc.execute = Mock(return_value=_feedback("algorithm_coder", FailureReason.algorithm_runtime_error))

    return dict(
        spec_agent=spec, image_analysis_agent=img_agent,
        pipeline_composer=composer, parameter_searcher=searcher,
        vision_judge_agent=judge, inspection_plan_agent=plan_agent,
        algorithm_selector=selector, algorithm_coder_inspection=coder_insp,
        algorithm_coder_align=coder_align, code_validator=validator,
        test_agent_inspection=test_insp, test_agent_align=test_aln,
        evaluation_agent=eval_agent,
        feedback_controller=fc,
    )


def _orc(mode: str = "inspection") -> tuple[Orchestrator, dict]:
    m = _mocks(mode)
    return Orchestrator(**m), m


def _orc_no_fc(mode: str = "inspection") -> tuple[Orchestrator, dict]:
    m = _mocks(mode)
    del m["feedback_controller"]
    orc = Orchestrator(**m)
    return orc, m


# ── TestAlgorithmCoderInspectionException ─────────────────────────────────────

class TestAlgorithmCoderInspectionException:
    @pytest.mark.anyio
    async def test_valueerror_enables_retry_loop(self):
        """ValueError from coder → synthetic EvaluationResult → retry loop → success."""
        orc, m = _orc("inspection")
        m["algorithm_coder_inspection"].execute = AsyncMock(side_effect=[
            ValueError("Failed to parse JSON response for item 'check' after retry"),
            _algo("inspection"),
        ])
        result = await orc.execute("detect", [_img()], [], config={"max_iteration": 5})
        assert m["algorithm_coder_inspection"].execute.call_count == 2
        assert result["evaluation_result"].overall_passed is True

    @pytest.mark.anyio
    async def test_runtime_error_also_caught_gracefully(self):
        """RuntimeError (not just ValueError) is also caught and converted."""
        orc, m = _orc("inspection")
        m["algorithm_coder_inspection"].execute = AsyncMock(side_effect=[
            RuntimeError("unexpected failure in coder"),
            _algo("inspection"),
        ])
        result = await orc.execute("detect", [_img()], [], config={"max_iteration": 5})
        assert result["evaluation_result"].overall_passed is True

    @pytest.mark.anyio
    async def test_sets_algorithm_runtime_error_failure_reason(self):
        """Caught exception → failure_reason=algorithm_runtime_error."""
        orc, m = _orc_no_fc("inspection")
        m["algorithm_coder_inspection"].execute = AsyncMock(
            side_effect=ValueError("parse error")
        )
        result = await orc.execute("detect", [_img()], [])
        assert result["evaluation_result"].failure_reason == FailureReason.algorithm_runtime_error

    @pytest.mark.anyio
    async def test_sets_overall_passed_false_when_no_retry(self):
        """Exception without retry → overall_passed=False, pipeline status=failed."""
        orc, m = _orc_no_fc("inspection")
        m["algorithm_coder_inspection"].execute = AsyncMock(
            side_effect=ValueError("parse error")
        )
        result = await orc.execute("detect", [_img()], [])
        assert result["evaluation_result"].overall_passed is False
        assert orc.get_progress().status == "failed"

    @pytest.mark.anyio
    async def test_skips_code_validator(self):
        """Exception before code is produced → validator must NOT be called."""
        orc, m = _orc_no_fc("inspection")
        m["algorithm_coder_inspection"].execute = AsyncMock(
            side_effect=ValueError("parse error")
        )
        await orc.execute("detect", [_img()], [])
        m["code_validator"].validate.assert_not_called()

    @pytest.mark.anyio
    async def test_skips_test_agent(self):
        """Exception before code is produced → test agent must NOT be called."""
        orc, m = _orc_no_fc("inspection")
        m["algorithm_coder_inspection"].execute = AsyncMock(
            side_effect=ValueError("parse error")
        )
        await orc.execute("detect", [_img()], [])
        m["test_agent_inspection"].execute.assert_not_called()

    @pytest.mark.anyio
    async def test_skips_evaluation_agent(self):
        """Exception creates synthetic EvaluationResult → evaluation_agent NOT called."""
        orc, m = _orc_no_fc("inspection")
        m["algorithm_coder_inspection"].execute = AsyncMock(
            side_effect=ValueError("parse error")
        )
        await orc.execute("detect", [_img()], [])
        m["evaluation_agent"].execute.assert_not_called()


# ── TestAlgorithmCoderAlignException ──────────────────────────────────────────

class TestAlgorithmCoderAlignException:
    @pytest.mark.anyio
    async def test_valueerror_enables_retry_loop(self):
        """ValueError from align coder → retry loop → success."""
        orc, m = _orc("align")
        m["algorithm_coder_align"].execute = AsyncMock(side_effect=[
            ValueError("Failed to parse JSON response after retry"),
            _algo("align"),
        ])
        result = await orc.execute("align", [_img()], [], config={"max_iteration": 5})
        assert m["algorithm_coder_align"].execute.call_count == 2
        assert result["evaluation_result"].overall_passed is True

    @pytest.mark.anyio
    async def test_runtime_error_also_caught(self):
        """RuntimeError from align coder is caught and enables retry."""
        orc, m = _orc("align")
        m["algorithm_coder_align"].execute = AsyncMock(side_effect=[
            RuntimeError("align coder boom"),
            _algo("align"),
        ])
        result = await orc.execute("align", [_img()], [], config={"max_iteration": 5})
        assert result["evaluation_result"].overall_passed is True

    @pytest.mark.anyio
    async def test_sets_algorithm_runtime_error_failure_reason(self):
        orc, m = _orc_no_fc("align")
        m["algorithm_coder_align"].execute = AsyncMock(
            side_effect=ValueError("parse error")
        )
        result = await orc.execute("align", [_img()], [])
        assert result["evaluation_result"].failure_reason == FailureReason.algorithm_runtime_error

    @pytest.mark.anyio
    async def test_skips_code_validator(self):
        orc, m = _orc_no_fc("align")
        m["algorithm_coder_align"].execute = AsyncMock(
            side_effect=ValueError("parse error")
        )
        await orc.execute("align", [_img()], [])
        m["code_validator"].validate.assert_not_called()

    @pytest.mark.anyio
    async def test_skips_test_agent(self):
        orc, m = _orc_no_fc("align")
        m["algorithm_coder_align"].execute = AsyncMock(
            side_effect=ValueError("parse error")
        )
        await orc.execute("align", [_img()], [])
        m["test_agent_align"].execute.assert_not_called()


# ── TestInspectionPlanException ───────────────────────────────────────────────

class TestInspectionPlanException:
    @pytest.mark.anyio
    async def test_valueerror_enables_retry_loop(self):
        """ValueError from inspection plan → retry with inspection_plan target → success."""
        orc, m = _orc("inspection")
        m["inspection_plan_agent"].execute = AsyncMock(side_effect=[
            ValueError("JSON parse failure in plan agent"),
            _plan(),
        ])
        m["feedback_controller"].execute = Mock(
            return_value=_feedback("inspection_plan", FailureReason.inspection_plan_issue)
        )
        result = await orc.execute("detect", [_img()], [], config={"max_iteration": 5})
        assert m["inspection_plan_agent"].execute.call_count == 2
        assert result["evaluation_result"].overall_passed is True

    @pytest.mark.anyio
    async def test_sets_inspection_plan_issue_failure_reason(self):
        orc, m = _orc_no_fc("inspection")
        m["inspection_plan_agent"].execute = AsyncMock(
            side_effect=ValueError("JSON parse failure")
        )
        result = await orc.execute("detect", [_img()], [])
        assert result["evaluation_result"].failure_reason == FailureReason.inspection_plan_issue

    @pytest.mark.anyio
    async def test_sets_overall_passed_false(self):
        orc, m = _orc_no_fc("inspection")
        m["inspection_plan_agent"].execute = AsyncMock(
            side_effect=ValueError("JSON parse failure")
        )
        result = await orc.execute("detect", [_img()], [])
        assert result["evaluation_result"].overall_passed is False

    @pytest.mark.anyio
    async def test_skips_algorithm_selector(self):
        """Plan exception causes early return before algorithm_selector runs."""
        orc, m = _orc_no_fc("inspection")
        m["inspection_plan_agent"].execute = AsyncMock(
            side_effect=ValueError("parse error")
        )
        await orc.execute("detect", [_img()], [])
        m["algorithm_selector"].execute.assert_not_called()

    @pytest.mark.anyio
    async def test_skips_algorithm_coder(self):
        """Plan exception causes early return before algorithm_coder runs."""
        orc, m = _orc_no_fc("inspection")
        m["inspection_plan_agent"].execute = AsyncMock(
            side_effect=ValueError("parse error")
        )
        await orc.execute("detect", [_img()], [])
        m["algorithm_coder_inspection"].execute.assert_not_called()

    @pytest.mark.anyio
    async def test_runtime_error_also_caught(self):
        orc, m = _orc_no_fc("inspection")
        m["inspection_plan_agent"].execute = AsyncMock(
            side_effect=RuntimeError("unexpected plan failure")
        )
        result = await orc.execute("detect", [_img()], [])
        assert result["evaluation_result"].failure_reason == FailureReason.inspection_plan_issue


# ── TestExceptionLogging ──────────────────────────────────────────────────────

class TestExceptionLogging:
    @pytest.mark.anyio
    async def test_algorithm_coder_inspection_logs_error(self):
        """Exception in algorithm_coder_inspection → ERROR-level log emitted."""
        orc, m = _orc_no_fc("inspection")
        m["algorithm_coder_inspection"].execute = AsyncMock(
            side_effect=ValueError("JSON parse error")
        )
        log_calls: list[tuple[str, str]] = []
        orc._log = lambda level, msg, *a, **kw: log_calls.append((level, str(msg)))

        await orc.execute("detect", [_img()], [])

        error_calls = [msg for level, msg in log_calls if level == "ERROR"]
        assert len(error_calls) >= 1

    @pytest.mark.anyio
    async def test_inspection_plan_logs_error(self):
        """Exception in inspection_plan_agent → ERROR-level log emitted."""
        orc, m = _orc_no_fc("inspection")
        m["inspection_plan_agent"].execute = AsyncMock(
            side_effect=ValueError("plan parse error")
        )
        log_calls: list[tuple[str, str]] = []
        orc._log = lambda level, msg, *a, **kw: log_calls.append((level, str(msg)))

        await orc.execute("detect", [_img()], [])

        error_calls = [msg for level, msg in log_calls if level == "ERROR"]
        assert len(error_calls) >= 1
