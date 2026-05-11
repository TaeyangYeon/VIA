"""Tests for TestAgentInspection — synchronous code execution and per-item metrics."""
import inspect

import numpy as np
import pytest

from agents.base_agent import BaseAgent
from agents.models import (
    AlgorithmCategory,
    InspectionItem,
    InspectionPlan,
    ItemTestResult,
    TestMetrics,
)
from agents.test_agent_inspection import TestAgentInspection
from backend.services.logger import via_logger


# ── Helpers ───────────────────────────────────────────────────────────────────

def _img() -> np.ndarray:
    return np.zeros((50, 50, 3), dtype=np.uint8)


def _item(
    item_id: int = 1,
    name: str = "항목",
    criteria: str = "",
    depends_on: list | None = None,
) -> InspectionItem:
    return InspectionItem(
        id=item_id,
        name=name,
        purpose="목적",
        method=AlgorithmCategory.BLOB,
        depends_on=depends_on or [],
        safety_role="",
        success_criteria=criteria,
    )


def _plan(*items: InspectionItem) -> InspectionPlan:
    return InspectionPlan(items=list(items))


def _code(*results: str) -> str:
    """Build multi-function code string; i-th function returns results[i]."""
    fns = [
        f"def inspect_item(image):\n    return {{'result': '{r}', 'details': {{}}}}"
        for r in results
    ]
    return "\n\n".join(fns)


def _err_code() -> str:
    return "def inspect_item(image):\n    raise RuntimeError('test error')"


def _run(
    fn_results: list,
    images: list,
    items: list | None = None,
    agent: TestAgentInspection | None = None,
) -> list:
    if agent is None:
        agent = TestAgentInspection()
    if items is None:
        items = [_item(i + 1) for i in range(len(fn_results))]
    return agent.execute(
        code=_code(*fn_results),
        plan=_plan(*items),
        test_images=images,
    )


# ── 1. Class Structure ────────────────────────────────────────────────────────

class TestClassStructure:
    def test_inherits_base_agent(self):
        assert issubclass(TestAgentInspection, BaseAgent)

    def test_agent_name(self):
        assert TestAgentInspection().agent_name == "test_agent_inspection"

    def test_execute_is_synchronous(self):
        assert not inspect.iscoroutinefunction(TestAgentInspection().execute)

    def test_directive_none_by_default(self):
        assert TestAgentInspection().get_directive() is None

    def test_directive_in_constructor(self):
        assert TestAgentInspection(directive="d").get_directive() == "d"

    def test_set_directive(self):
        agent = TestAgentInspection()
        agent.set_directive("new")
        assert agent.get_directive() == "new"


# ── 2. Return Type ────────────────────────────────────────────────────────────

class TestReturnType:
    def test_returns_list(self):
        result = _run(["OK"], [(_img(), "OK_1.png")])
        assert isinstance(result, list)

    def test_returns_item_test_result_instances(self):
        result = _run(["OK"], [(_img(), "OK_1.png")])
        assert all(isinstance(r, ItemTestResult) for r in result)

    def test_result_count_matches_plan_items(self):
        result = _run(["OK", "NG"], [(_img(), "OK_1.png")])
        assert len(result) == 2

    def test_item_ids_match_plan(self):
        result = _run(["OK", "NG"], [(_img(), "OK_1.png")], items=[_item(5), _item(7)])
        assert result[0].item_id == 5
        assert result[1].item_id == 7

    def test_item_names_match_plan(self):
        result = _run(["OK"], [(_img(), "OK_1.png")], items=[_item(1, name="스크래치검사")])
        assert result[0].item_name == "스크래치검사"


# ── 3. Function Extraction ────────────────────────────────────────────────────

class TestFunctionExtraction:
    def test_single_function_extracted_and_executed(self):
        result = _run(["OK"], [(_img(), "OK_1.png")])
        assert result[0].metrics.accuracy == 1.0

    def test_first_function_mapped_to_first_item(self):
        # fn0 returns OK, fn1 returns NG; NG image → item0 wrong
        result = _run(["OK", "NG"], [(_img(), "NG_1.png")])
        assert result[0].metrics.accuracy == 0.0

    def test_second_function_mapped_to_second_item(self):
        # fn1 returns NG; NG image → item1 correct
        result = _run(["OK", "NG"], [(_img(), "NG_1.png")])
        assert result[1].metrics.accuracy == 1.0

    def test_malformed_code_fails_gracefully(self):
        agent = TestAgentInspection()
        result = agent.execute(
            code="this is ??? not valid python",
            plan=_plan(_item(1)),
            test_images=[(_img(), "OK_1.png")],
        )
        assert result[0].passed is False
        assert result[0].metrics.accuracy == 0.0

    def test_fewer_functions_than_items_handled(self):
        # 1 function, 2 items — second item gets no function
        result = _run(["OK"], [(_img(), "OK_1.png")], items=[_item(1), _item(2)])
        assert len(result) == 2
        assert result[1].passed is False

    def test_extraction_failure_error_in_details(self):
        agent = TestAgentInspection()
        result = agent.execute(
            code="not valid python !!!",
            plan=_plan(_item(1)),
            test_images=[(_img(), "OK_1.png")],
        )
        assert "error" in result[0].details.lower()


# ── 4. Ground Truth Parsing ───────────────────────────────────────────────────

class TestGroundTruthParsing:
    def test_ok_prefix_treated_as_ok(self):
        result = _run(["OK"], [(_img(), "OK_001.png")])
        assert result[0].metrics.accuracy == 1.0

    def test_ng_prefix_treated_as_ng(self):
        result = _run(["NG"], [(_img(), "NG_001.jpg")])
        assert result[0].metrics.accuracy == 1.0

    def test_ok_image_predicted_ng_is_wrong(self):
        result = _run(["NG"], [(_img(), "OK_1.png")])
        assert result[0].metrics.accuracy == 0.0

    def test_ng_image_predicted_ok_is_wrong(self):
        result = _run(["OK"], [(_img(), "NG_1.png")])
        assert result[0].metrics.accuracy == 0.0

    def test_unknown_filename_does_not_crash(self):
        result = _run(["OK"], [(_img(), "unknown_sample.png")])
        assert len(result) == 1


# ── 5. Metrics Computation ────────────────────────────────────────────────────

class TestMetricsComputation:
    def test_all_ok_correct_accuracy_one(self):
        images = [(_img(), f"OK_{i}.png") for i in range(5)]
        r = _run(["OK"], images)[0]
        assert r.metrics.accuracy == pytest.approx(1.0)

    def test_all_ng_correct_accuracy_one(self):
        images = [(_img(), f"NG_{i}.png") for i in range(5)]
        r = _run(["NG"], images)[0]
        assert r.metrics.accuracy == pytest.approx(1.0)

    def test_all_ok_wrong_accuracy_zero(self):
        images = [(_img(), f"OK_{i}.png") for i in range(3)]
        r = _run(["NG"], images)[0]
        assert r.metrics.accuracy == pytest.approx(0.0)

    def test_mixed_accuracy(self):
        # 4 OK correct, 1 NG wrong → 4/5
        images = [(_img(), f"OK_{i}.png") for i in range(4)] + [(_img(), "NG_1.png")]
        r = _run(["OK"], images)[0]
        assert r.metrics.accuracy == pytest.approx(4 / 5)

    def test_fp_rate_all_ok_wrongly_ng(self):
        images = [(_img(), f"OK_{i}.png") for i in range(3)]
        r = _run(["NG"], images)[0]
        assert r.metrics.fp_rate == pytest.approx(1.0)

    def test_fp_rate_zero_when_all_ok_correct(self):
        result = _run(["OK"], [(_img(), "OK_1.png")])[0]
        assert result.metrics.fp_rate == pytest.approx(0.0)

    def test_fn_rate_all_ng_wrongly_ok(self):
        images = [(_img(), f"NG_{i}.png") for i in range(4)]
        r = _run(["OK"], images)[0]
        assert r.metrics.fn_rate == pytest.approx(1.0)

    def test_fp_rate_zero_when_no_ok_images(self):
        images = [(_img(), "NG_1.png"), (_img(), "NG_2.png")]
        r = _run(["NG"], images)[0]
        assert r.metrics.fp_rate == pytest.approx(0.0)

    def test_fn_rate_zero_when_no_ng_images(self):
        images = [(_img(), "OK_1.png"), (_img(), "OK_2.png")]
        r = _run(["OK"], images)[0]
        assert r.metrics.fn_rate == pytest.approx(0.0)

    def test_metrics_are_floats(self):
        r = _run(["OK"], [(_img(), "OK_1.png")])[0]
        assert isinstance(r.metrics.accuracy, float)
        assert isinstance(r.metrics.fp_rate, float)
        assert isinstance(r.metrics.fn_rate, float)

    def test_metrics_clamped_zero_to_one(self):
        r = _run(["OK"], [(_img(), "OK_1.png")])[0]
        assert 0.0 <= r.metrics.accuracy <= 1.0
        assert 0.0 <= r.metrics.fp_rate <= 1.0
        assert 0.0 <= r.metrics.fn_rate <= 1.0


# ── 6. depends_on Ordering ────────────────────────────────────────────────────

class TestDependsOnOrdering:
    def test_independent_items_both_executed(self):
        result = _run(["OK", "OK"], [(_img(), "OK_1.png")])
        assert result[0].metrics.accuracy == 1.0
        assert result[1].metrics.accuracy == 1.0

    def test_downstream_skipped_when_dependency_fails(self):
        item1 = _item(1, criteria="accuracy >= 0.9")
        item2 = _item(2, depends_on=[1])
        agent = TestAgentInspection()
        # fn0 returns NG for OK image → item1 accuracy=0.0 → fails criteria
        result = agent.execute(
            code=_code("NG", "OK"),
            plan=_plan(item1, item2),
            test_images=[(_img(), "OK_1.png")],
        )
        assert result[0].passed is False
        assert result[1].passed is False

    def test_skipped_item_has_skip_in_details(self):
        item1 = _item(1, criteria="accuracy >= 0.9")
        item2 = _item(2, depends_on=[1])
        agent = TestAgentInspection()
        result = agent.execute(
            code=_code("NG", "OK"),
            plan=_plan(item1, item2),
            test_images=[(_img(), "OK_1.png")],
        )
        details_lower = result[1].details.lower()
        assert "skip" in details_lower or "depend" in details_lower

    def test_skipped_item_has_zero_metrics(self):
        item1 = _item(1, criteria="accuracy >= 1.0")
        item2 = _item(2, depends_on=[1])
        agent = TestAgentInspection()
        result = agent.execute(
            code=_code("NG", "OK"),
            plan=_plan(item1, item2),
            test_images=[(_img(), "OK_1.png")],
        )
        m = result[1].metrics
        assert m.accuracy == 0.0
        assert m.fp_rate == 0.0
        assert m.fn_rate == 0.0

    def test_downstream_executed_when_dependency_passes(self):
        item1 = _item(1)
        item2 = _item(2, depends_on=[1])
        agent = TestAgentInspection()
        result = agent.execute(
            code=_code("OK", "OK"),
            plan=_plan(item1, item2),
            test_images=[(_img(), "OK_1.png")],
        )
        assert result[0].passed is True
        assert result[1].passed is True


# ── 7. Success Criteria Parsing ───────────────────────────────────────────────

class TestSuccessCriteriaParsing:
    def test_accuracy_gte_passes(self):
        result = _run(["OK"], [(_img(), "OK_1.png")], items=[_item(1, criteria="accuracy >= 0.9")])
        assert result[0].passed is True

    def test_accuracy_gte_fails(self):
        result = _run(["NG"], [(_img(), "OK_1.png")], items=[_item(1, criteria="accuracy >= 0.9")])
        assert result[0].passed is False

    def test_fp_rate_lte_passes(self):
        # NG image only → fp_rate=0.0 → 0.0 <= 0.05 → passes
        result = _run(["OK"], [(_img(), "NG_1.png")], items=[_item(1, criteria="fp_rate <= 0.05")])
        assert result[0].passed is True

    def test_fp_rate_lte_fails(self):
        # 2 OK images, fn returns NG → fp_rate=1.0 → fails
        images = [(_img(), "OK_1.png"), (_img(), "OK_2.png")]
        result = _run(["NG"], images, items=[_item(1, criteria="fp_rate <= 0.05")])
        assert result[0].passed is False

    def test_fn_rate_lte_fails(self):
        images = [(_img(), "NG_1.png"), (_img(), "NG_2.png")]
        result = _run(["OK"], images, items=[_item(1, criteria="fn_rate <= 0.1")])
        assert result[0].passed is False

    def test_empty_criteria_uses_default_passes(self):
        result = _run(["OK"], [(_img(), "OK_1.png")], items=[_item(1, criteria="")])
        assert result[0].passed is True  # accuracy=1.0 >= 0.8

    def test_empty_criteria_uses_default_fails(self):
        images = [(_img(), "OK_1.png"), (_img(), "OK_2.png")]
        result = _run(["NG"], images, items=[_item(1, criteria="")])
        assert result[0].passed is False  # accuracy=0.0 < 0.8

    def test_unparseable_criteria_falls_back_to_default(self):
        result = _run(["OK"], [(_img(), "OK_1.png")], items=[_item(1, criteria="complex #$@! criteria")])
        # Should not raise; default accuracy >= 0.8 → passes
        assert result[0].passed is True


# ── 8. Edge Cases ─────────────────────────────────────────────────────────────

class TestEdgeCases:
    def test_empty_test_images_zero_metrics(self):
        agent = TestAgentInspection()
        result = agent.execute(
            code=_code("OK"),
            plan=_plan(_item(1)),
            test_images=[],
        )
        m = result[0].metrics
        assert m.accuracy == 0.0
        assert m.fp_rate == 0.0
        assert m.fn_rate == 0.0

    def test_empty_test_images_not_passed(self):
        agent = TestAgentInspection()
        result = agent.execute(
            code=_code("OK"),
            plan=_plan(_item(1)),
            test_images=[],
        )
        assert result[0].passed is False

    def test_empty_plan_returns_empty_list(self):
        agent = TestAgentInspection()
        result = agent.execute(
            code="",
            plan=_plan(),
            test_images=[(_img(), "OK_1.png")],
        )
        assert result == []

    def test_runtime_error_counted_as_wrong_ok_image(self):
        agent = TestAgentInspection()
        result = agent.execute(
            code=_err_code(),
            plan=_plan(_item(1)),
            test_images=[(_img(), "OK_1.png")],
        )
        assert result[0].metrics.accuracy == 0.0

    def test_runtime_error_counted_as_wrong_ng_image(self):
        agent = TestAgentInspection()
        result = agent.execute(
            code=_err_code(),
            plan=_plan(_item(1)),
            test_images=[(_img(), "NG_1.png")],
        )
        assert result[0].metrics.accuracy == 0.0

    def test_only_ng_images_fp_rate_zero(self):
        images = [(_img(), f"NG_{i}.png") for i in range(3)]
        result = _run(["NG"], images)[0]
        assert result.metrics.fp_rate == pytest.approx(0.0)

    def test_only_ok_images_fn_rate_zero(self):
        images = [(_img(), f"OK_{i}.png") for i in range(3)]
        result = _run(["OK"], images)[0]
        assert result.metrics.fn_rate == pytest.approx(0.0)

    def test_single_image_ok(self):
        result = _run(["OK"], [(_img(), "OK_1.png")])[0]
        assert result.metrics.accuracy == 1.0

    def test_single_image_ng(self):
        result = _run(["NG"], [(_img(), "NG_1.png")])[0]
        assert result.metrics.accuracy == 1.0


# ── 9. Directive Support ──────────────────────────────────────────────────────

class TestDirectiveSupport:
    def test_directive_does_not_change_results(self):
        images = [(_img(), "OK_1.png")]
        r_no = _run(["OK"], images)
        r_dir = _run(["OK"], images, agent=TestAgentInspection(directive="엄격 검사"))
        assert r_no[0].metrics.accuracy == r_dir[0].metrics.accuracy

    def test_directive_is_logged(self):
        via_logger.clear()
        agent = TestAgentInspection(directive="테스트 지시")
        agent.execute(
            code=_code("OK"),
            plan=_plan(_item(1)),
            test_images=[(_img(), "OK_1.png")],
        )
        logs = via_logger.get_logs(agent="test_agent_inspection")
        assert any(
            "테스트 지시" in str(log.get("message", "")) or
            "테스트 지시" in str(log.get("details", ""))
            for log in logs
        )


# ── 10. Logging Verification ──────────────────────────────────────────────────

class TestLoggingVerification:
    def test_info_logged_per_item(self):
        via_logger.clear()
        _run(["OK"], [(_img(), "OK_1.png")])
        logs = via_logger.get_logs(agent="test_agent_inspection", level="INFO")
        assert len(logs) > 0

    def test_info_logged_for_multiple_items(self):
        via_logger.clear()
        _run(["OK", "NG"], [(_img(), "OK_1.png")])
        logs = via_logger.get_logs(agent="test_agent_inspection", level="INFO")
        assert len(logs) >= 2

    def test_warning_logged_on_extraction_failure(self):
        via_logger.clear()
        agent = TestAgentInspection()
        agent.execute(
            code="not valid python !!!",
            plan=_plan(_item(1)),
            test_images=[(_img(), "OK_1.png")],
        )
        all_logs = via_logger.get_logs(agent="test_agent_inspection")
        assert any(l["level"] == "WARNING" for l in all_logs)
