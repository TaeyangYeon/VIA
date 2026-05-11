"""Tests for EvaluationAgent: rule-based per-item failure analysis."""
from __future__ import annotations

import inspect

import pytest

from agents.base_agent import BaseAgent
from agents.evaluation_agent import EvaluationAgent
from agents.models import (
    AlgorithmCategory,
    EvaluationResult,
    FailureReason,
    InspectionItem,
    InspectionPlan,
    ItemTestResult,
    JudgementResult,
    TestMetrics,
)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _item(
    item_id: int = 1,
    name: str = "item",
    passed: bool = True,
    accuracy: float = 0.9,
    fp_rate: float = 0.05,
    fn_rate: float = 0.05,
    coord_error: float | None = None,
    success_rate: float | None = None,
    details: str = "",
) -> ItemTestResult:
    return ItemTestResult(
        item_id=item_id,
        item_name=name,
        passed=passed,
        metrics=TestMetrics(
            accuracy=accuracy,
            fp_rate=fp_rate,
            fn_rate=fn_rate,
            coord_error=coord_error,
            success_rate=success_rate,
        ),
        details=details,
    )


def _judge(
    visibility: float = 0.8,
    separability: float = 0.8,
    measurability: float = 0.8,
) -> JudgementResult:
    return JudgementResult(
        visibility_score=visibility,
        separability_score=separability,
        measurability_score=measurability,
    )


def _plan_item(item_id: int, name: str = "item", depends_on: list[int] | None = None) -> InspectionItem:
    return InspectionItem(
        id=item_id,
        name=name,
        purpose="test",
        method=AlgorithmCategory.BLOB,
        depends_on=depends_on or [],
    )


def _plan(*items: InspectionItem) -> InspectionPlan:
    return InspectionPlan(items=list(items))


# ── 1. Class structure ────────────────────────────────────────────────────────

def test_is_subclass_of_base_agent():
    assert issubclass(EvaluationAgent, BaseAgent)


def test_agent_name():
    assert EvaluationAgent().agent_name == "evaluation_agent"


def test_execute_is_synchronous():
    assert not inspect.iscoroutinefunction(EvaluationAgent.execute)


def test_instantiate_no_directive():
    agent = EvaluationAgent()
    assert agent.get_directive() is None


def test_instantiate_with_directive():
    agent = EvaluationAgent(directive="focus on edge cases")
    assert agent.get_directive() == "focus on edge cases"


def test_set_directive():
    agent = EvaluationAgent()
    agent.set_directive("new directive")
    assert agent.get_directive() == "new directive"


def test_no_ollama_import():
    import agents.evaluation_agent as mod
    source = inspect.getsource(mod)
    assert "ollama" not in source


# ── 2. All-pass scenario ──────────────────────────────────────────────────────

def test_all_pass_overall_passed_true():
    result = EvaluationAgent().execute([_item(1, passed=True), _item(2, passed=True)])
    assert result.overall_passed is True


def test_all_pass_failure_reason_none():
    result = EvaluationAgent().execute([_item(1, passed=True), _item(2, passed=True)])
    assert result.failure_reason is None


def test_all_pass_failed_items_empty():
    result = EvaluationAgent().execute([_item(1, passed=True), _item(2, passed=True)])
    assert result.failed_items == []


def test_all_pass_analysis_mentions_total_count():
    result = EvaluationAgent().execute([_item(1, passed=True), _item(2, passed=True)])
    assert "2" in result.analysis


# ── 3. Runtime error detection ────────────────────────────────────────────────

def test_runtime_error_detected_lowercase():
    # Single failing item triggers spec_issue too, but runtime_error has higher priority
    result = EvaluationAgent().execute([
        _item(1, passed=False, details="error: function_extraction_failed"),
        _item(2, passed=True),
    ])
    assert result.failure_reason == FailureReason.algorithm_runtime_error


def test_runtime_error_detected_capital_e():
    result = EvaluationAgent().execute([
        _item(1, passed=False, details="Error: execution failed"),
        _item(2, passed=True),
    ])
    assert result.failure_reason == FailureReason.algorithm_runtime_error


def test_runtime_error_detected_all_caps():
    result = EvaluationAgent().execute([
        _item(1, passed=False, details="ERROR occurred"),
        _item(2, passed=True),
    ])
    assert result.failure_reason == FailureReason.algorithm_runtime_error


def test_runtime_error_not_triggered_on_passed_item():
    result = EvaluationAgent().execute([
        _item(1, passed=True, details="error message here"),
    ])
    assert result.overall_passed is True
    assert result.failure_reason is None


def test_runtime_error_wins_when_mixed_with_other_failures():
    result = EvaluationAgent().execute([
        _item(1, passed=False, details="error: crash"),
        _item(2, passed=False, details=""),
    ])
    assert result.failure_reason == FailureReason.algorithm_runtime_error


# ── 4. Spec issue ─────────────────────────────────────────────────────────────

def test_spec_issue_when_all_two_items_fail():
    result = EvaluationAgent().execute([
        _item(1, passed=False),
        _item(2, passed=False),
    ])
    assert result.failure_reason == FailureReason.spec_issue


def test_spec_issue_when_all_three_items_fail():
    result = EvaluationAgent().execute([
        _item(1, passed=False),
        _item(2, passed=False),
        _item(3, passed=False),
    ])
    assert result.failure_reason == FailureReason.spec_issue


def test_spec_issue_not_triggered_when_some_pass():
    result = EvaluationAgent().execute([
        _item(1, passed=False),
        _item(2, passed=True),
        _item(3, passed=False),
    ])
    assert result.failure_reason != FailureReason.spec_issue


def test_spec_issue_single_item_all_fail():
    result = EvaluationAgent().execute([_item(1, passed=False)])
    assert result.failure_reason == FailureReason.spec_issue


# ── 5. Inspection plan issue ──────────────────────────────────────────────────

def test_plan_issue_three_fail_with_dependency_chain():
    # 4 total; items 1,2,3 fail; item 2 depends on item 1 (both failed)
    test_results = [
        _item(1, passed=False),
        _item(2, passed=False),
        _item(3, passed=False),
        _item(4, passed=True),
    ]
    plan = _plan(
        _plan_item(1),
        _plan_item(2, depends_on=[1]),
        _plan_item(3),
        _plan_item(4),
    )
    result = EvaluationAgent().execute(test_results, plan=plan)
    assert result.failure_reason == FailureReason.inspection_plan_issue


def test_plan_issue_not_triggered_when_only_two_fail():
    test_results = [
        _item(1, passed=False),
        _item(2, passed=False),
        _item(3, passed=True),
        _item(4, passed=True),
    ]
    plan = _plan(
        _plan_item(1),
        _plan_item(2, depends_on=[1]),
        _plan_item(3),
        _plan_item(4),
    )
    result = EvaluationAgent().execute(test_results, plan=plan)
    assert result.failure_reason != FailureReason.inspection_plan_issue


def test_plan_issue_not_triggered_without_dependency_chain():
    test_results = [
        _item(1, passed=False),
        _item(2, passed=False),
        _item(3, passed=False),
        _item(4, passed=True),
    ]
    plan = _plan(
        _plan_item(1),
        _plan_item(2),
        _plan_item(3),
        _plan_item(4),
    )
    result = EvaluationAgent().execute(test_results, plan=plan)
    assert result.failure_reason != FailureReason.inspection_plan_issue


def test_plan_issue_not_triggered_when_plan_is_none():
    test_results = [
        _item(1, passed=False),
        _item(2, passed=False),
        _item(3, passed=False),
        _item(4, passed=True),
    ]
    result = EvaluationAgent().execute(test_results, plan=None)
    assert result.failure_reason != FailureReason.inspection_plan_issue


def test_plan_issue_four_fail_with_chain():
    test_results = [
        _item(1, passed=False),
        _item(2, passed=False),
        _item(3, passed=False),
        _item(4, passed=False),
        _item(5, passed=True),
    ]
    plan = _plan(
        _plan_item(1),
        _plan_item(2),
        _plan_item(3, depends_on=[2]),
        _plan_item(4),
        _plan_item(5),
    )
    result = EvaluationAgent().execute(test_results, plan=plan)
    assert result.failure_reason == FailureReason.inspection_plan_issue


# ── 6. Pipeline bad fit ───────────────────────────────────────────────────────

def test_pipeline_bad_fit_low_visibility_score():
    result = EvaluationAgent().execute(
        [_item(1, passed=False), _item(2, passed=True)],
        judge_result=_judge(visibility=0.3),
    )
    assert result.failure_reason == FailureReason.pipeline_bad_fit


def test_pipeline_bad_fit_low_separability_score():
    result = EvaluationAgent().execute(
        [_item(1, passed=False), _item(2, passed=True)],
        judge_result=_judge(separability=0.39),
    )
    assert result.failure_reason == FailureReason.pipeline_bad_fit


def test_pipeline_bad_fit_low_measurability_score():
    result = EvaluationAgent().execute(
        [_item(1, passed=False), _item(2, passed=True)],
        judge_result=_judge(measurability=0.1),
    )
    assert result.failure_reason == FailureReason.pipeline_bad_fit


def test_pipeline_bad_fit_boundary_exactly_04_not_triggered():
    # visibility_score == 0.4 means NOT low (condition is strictly < 0.4)
    result = EvaluationAgent().execute(
        [_item(1, passed=False), _item(2, passed=True)],
        judge_result=_judge(visibility=0.4, separability=0.8, measurability=0.8),
    )
    assert result.failure_reason != FailureReason.pipeline_bad_fit


# ── 7. Pipeline bad params ────────────────────────────────────────────────────

def test_pipeline_bad_params_when_judge_moderate():
    # All >= 0.4, some < 0.7 → moderate → pipeline_bad_params
    result = EvaluationAgent().execute(
        [_item(1, passed=False), _item(2, passed=True)],
        judge_result=_judge(visibility=0.6, separability=0.5, measurability=0.8),
    )
    assert result.failure_reason == FailureReason.pipeline_bad_params


def test_pipeline_bad_params_when_all_judge_scores_high():
    result = EvaluationAgent().execute(
        [_item(1, passed=False), _item(2, passed=True)],
        judge_result=_judge(visibility=0.8, separability=0.8, measurability=0.8),
    )
    assert result.failure_reason == FailureReason.pipeline_bad_params


def test_pipeline_bad_params_when_no_judge():
    result = EvaluationAgent().execute(
        [_item(1, passed=False), _item(2, passed=True)],
        judge_result=None,
    )
    assert result.failure_reason == FailureReason.pipeline_bad_params


def test_pipeline_bad_params_is_default_fallback():
    result = EvaluationAgent().execute(
        [_item(1, passed=False, accuracy=0.7, fp_rate=0.1, fn_rate=0.1), _item(2, passed=True)],
    )
    assert result.failure_reason == FailureReason.pipeline_bad_params


# ── 8. Algorithm wrong category — inspection mode ─────────────────────────────

def test_wrong_category_inspection_all_thresholds_met():
    result = EvaluationAgent().execute(
        [_item(1, passed=False, accuracy=0.4, fp_rate=0.4, fn_rate=0.4), _item(2, passed=True)],
        mode="inspection",
    )
    assert result.failure_reason == FailureReason.algorithm_wrong_category


def test_wrong_category_inspection_accuracy_at_boundary():
    # accuracy == 0.5 is NOT < 0.5 → not triggered
    result = EvaluationAgent().execute(
        [_item(1, passed=False, accuracy=0.5, fp_rate=0.4, fn_rate=0.4), _item(2, passed=True)],
        mode="inspection",
    )
    assert result.failure_reason != FailureReason.algorithm_wrong_category


def test_wrong_category_inspection_fp_rate_at_boundary():
    # fp_rate == 0.3 is NOT > 0.3 → not triggered
    result = EvaluationAgent().execute(
        [_item(1, passed=False, accuracy=0.4, fp_rate=0.3, fn_rate=0.4), _item(2, passed=True)],
        mode="inspection",
    )
    assert result.failure_reason != FailureReason.algorithm_wrong_category


def test_wrong_category_inspection_fn_rate_at_boundary():
    # fn_rate == 0.3 is NOT > 0.3 → not triggered
    result = EvaluationAgent().execute(
        [_item(1, passed=False, accuracy=0.4, fp_rate=0.4, fn_rate=0.3), _item(2, passed=True)],
        mode="inspection",
    )
    assert result.failure_reason != FailureReason.algorithm_wrong_category


# ── 9. Algorithm wrong category — align mode ──────────────────────────────────

def test_wrong_category_align_all_thresholds_met():
    result = EvaluationAgent().execute(
        [_item(1, passed=False, coord_error=11.0, success_rate=0.1), _item(2, passed=True)],
        mode="align",
    )
    assert result.failure_reason == FailureReason.algorithm_wrong_category


def test_wrong_category_align_coord_error_at_boundary():
    # coord_error == 10.0 is NOT > 10.0 → not triggered
    result = EvaluationAgent().execute(
        [_item(1, passed=False, coord_error=10.0, success_rate=0.1), _item(2, passed=True)],
        mode="align",
    )
    assert result.failure_reason != FailureReason.algorithm_wrong_category


def test_wrong_category_align_success_rate_at_boundary():
    # success_rate == 0.2 is NOT < 0.2 → not triggered
    result = EvaluationAgent().execute(
        [_item(1, passed=False, coord_error=11.0, success_rate=0.2), _item(2, passed=True)],
        mode="align",
    )
    assert result.failure_reason != FailureReason.algorithm_wrong_category


# ── 10. Priority ordering ─────────────────────────────────────────────────────

def test_priority_runtime_error_beats_spec_issue():
    # All items fail (spec_issue) AND one has "error" (runtime_error) → runtime_error wins
    result = EvaluationAgent().execute([
        _item(1, passed=False, details="error: crash"),
        _item(2, passed=False, details=""),
    ])
    assert result.failure_reason == FailureReason.algorithm_runtime_error


def test_priority_spec_issue_beats_plan_issue():
    # All 3 fail (spec_issue) AND dependency chain (plan_issue) → spec_issue wins
    test_results = [
        _item(1, passed=False),
        _item(2, passed=False),
        _item(3, passed=False),
    ]
    plan = _plan(_plan_item(1), _plan_item(2, depends_on=[1]), _plan_item(3))
    result = EvaluationAgent().execute(test_results, plan=plan)
    assert result.failure_reason == FailureReason.spec_issue


def test_priority_pipeline_bad_fit_beats_wrong_category():
    # Low judge score AND metrics matching wrong_category → pipeline_bad_fit wins
    result = EvaluationAgent().execute(
        [_item(1, passed=False, accuracy=0.4, fp_rate=0.4, fn_rate=0.4), _item(2, passed=True)],
        judge_result=_judge(visibility=0.3),
        mode="inspection",
    )
    assert result.failure_reason == FailureReason.pipeline_bad_fit


def test_priority_runtime_error_beats_pipeline_bad_fit():
    # "error" in details AND low judge scores → runtime_error wins
    result = EvaluationAgent().execute(
        [_item(1, passed=False, details="error: crash"), _item(2, passed=True)],
        judge_result=_judge(visibility=0.3),
    )
    assert result.failure_reason == FailureReason.algorithm_runtime_error


def test_priority_wrong_category_beats_bad_params():
    # No judge, metrics matching wrong_category → algorithm_wrong_category wins over default
    result = EvaluationAgent().execute(
        [_item(1, passed=False, accuracy=0.4, fp_rate=0.4, fn_rate=0.4), _item(2, passed=True)],
        judge_result=None,
        mode="inspection",
    )
    assert result.failure_reason == FailureReason.algorithm_wrong_category


# ── 11. failure_reason and failed_items ───────────────────────────────────────

def test_failure_reason_is_single_value():
    result = EvaluationAgent().execute([_item(1, passed=False), _item(2, passed=True)])
    assert isinstance(result.failure_reason, FailureReason)


def test_failed_items_contains_correct_ids():
    result = EvaluationAgent().execute([
        _item(3, passed=False),
        _item(7, passed=False),
        _item(2, passed=True),
    ])
    assert 3 in result.failed_items
    assert 7 in result.failed_items
    assert 2 not in result.failed_items


def test_failed_items_is_sorted():
    result = EvaluationAgent().execute([
        _item(5, passed=False),
        _item(1, passed=False),
        _item(3, passed=False),
    ])
    assert result.failed_items == sorted(result.failed_items)


def test_failure_reason_none_when_all_pass():
    result = EvaluationAgent().execute([_item(1, passed=True)])
    assert result.failure_reason is None


# ── 12. Analysis / summary ────────────────────────────────────────────────────

def test_analysis_contains_korean_text():
    result = EvaluationAgent().execute([_item(1, passed=False), _item(2, passed=True)])
    assert any(ord(c) >= 0xAC00 for c in result.analysis)


def test_analysis_contains_total_item_count():
    result = EvaluationAgent().execute([
        _item(1, passed=False),
        _item(2, passed=True),
        _item(3, passed=True),
    ])
    assert "3" in result.analysis


def test_analysis_contains_fail_count():
    result = EvaluationAgent().execute([
        _item(1, passed=False),
        _item(2, passed=False),
        _item(3, passed=True),
    ])
    assert "2" in result.analysis


def test_analysis_is_non_empty_on_failure():
    result = EvaluationAgent().execute([_item(1, passed=False, details="error: crash"), _item(2, passed=True)])
    assert len(result.analysis) > 10


# ── 13. Edge cases ────────────────────────────────────────────────────────────

def test_empty_results_returns_success():
    result = EvaluationAgent().execute([])
    assert result.overall_passed is True
    assert result.failure_reason is None
    assert result.failed_items == []


def test_single_passing_item():
    result = EvaluationAgent().execute([_item(1, passed=True)])
    assert result.overall_passed is True


def test_no_judge_result_returns_valid_evaluation():
    result = EvaluationAgent().execute([_item(1, passed=False), _item(2, passed=True)], judge_result=None)
    assert isinstance(result, EvaluationResult)
    assert result.failure_reason is not None


def test_no_plan_no_plan_issue_detection():
    test_results = [
        _item(1, passed=False),
        _item(2, passed=False),
        _item(3, passed=False),
        _item(4, passed=True),
    ]
    result = EvaluationAgent().execute(test_results, plan=None)
    assert result.failure_reason != FailureReason.inspection_plan_issue


def test_mode_defaults_to_inspection():
    # Default mode uses inspection thresholds for wrong_category
    result_default = EvaluationAgent().execute(
        [_item(1, passed=False, accuracy=0.4, fp_rate=0.4, fn_rate=0.4), _item(2, passed=True)],
    )
    result_explicit = EvaluationAgent().execute(
        [_item(1, passed=False, accuracy=0.4, fp_rate=0.4, fn_rate=0.4), _item(2, passed=True)],
        mode="inspection",
    )
    assert result_default.failure_reason == result_explicit.failure_reason


# ── 14. Directive support ─────────────────────────────────────────────────────

def test_directive_set_and_get():
    agent = EvaluationAgent()
    agent.set_directive("custom directive")
    assert agent.get_directive() == "custom directive"


def test_directive_does_not_change_evaluation_result():
    items = [_item(1, passed=False), _item(2, passed=True)]
    without_directive = EvaluationAgent().execute(items)
    with_directive = EvaluationAgent(directive="special mode").execute(items)
    assert without_directive.failure_reason == with_directive.failure_reason
    assert without_directive.overall_passed == with_directive.overall_passed


# ── 15. Mode handling ─────────────────────────────────────────────────────────

def test_mode_inspection_wrong_category_uses_accuracy_fp_fn():
    result = EvaluationAgent().execute(
        [_item(1, passed=False, accuracy=0.4, fp_rate=0.4, fn_rate=0.4), _item(2, passed=True)],
        mode="inspection",
    )
    assert result.failure_reason == FailureReason.algorithm_wrong_category


def test_mode_align_wrong_category_uses_coord_error():
    result = EvaluationAgent().execute(
        [_item(1, passed=False, coord_error=15.0, success_rate=0.1), _item(2, passed=True)],
        mode="align",
    )
    assert result.failure_reason == FailureReason.algorithm_wrong_category


def test_mode_align_ignores_inspection_thresholds():
    # In align mode, accuracy/fp/fn conditions should NOT trigger wrong_category
    # coord_error=5.0 (not > 10.0) → not wrong_category in align mode
    result = EvaluationAgent().execute(
        [_item(1, passed=False, accuracy=0.4, fp_rate=0.4, fn_rate=0.4,
               coord_error=5.0, success_rate=0.5), _item(2, passed=True)],
        mode="align",
    )
    assert result.failure_reason != FailureReason.algorithm_wrong_category
