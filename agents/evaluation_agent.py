"""Evaluation agent for per-item failure analysis and pass/fail determination."""
from __future__ import annotations

from typing import Optional

from agents.base_agent import BaseAgent
from agents.models import (
    EvaluationResult,
    FailureReason,
    InspectionPlan,
    ItemTestResult,
    JudgementResult,
)

_PRIORITY: list[FailureReason] = [
    FailureReason.algorithm_runtime_error,
    FailureReason.spec_issue,
    FailureReason.inspection_plan_issue,
    FailureReason.pipeline_bad_fit,
    FailureReason.algorithm_wrong_category,
    FailureReason.pipeline_bad_params,
]

_REASON_KO: dict[FailureReason, str] = {
    FailureReason.algorithm_runtime_error: "알고리즘 런타임 오류",
    FailureReason.spec_issue: "사양 문제",
    FailureReason.inspection_plan_issue: "검사 계획 구조 문제",
    FailureReason.pipeline_bad_fit: "파이프라인 부적합",
    FailureReason.algorithm_wrong_category: "알고리즘 카테고리 오류",
    FailureReason.pipeline_bad_params: "파이프라인 파라미터 부적합",
}


class EvaluationAgent(BaseAgent):
    def __init__(self, directive: Optional[str] = None) -> None:
        super().__init__("evaluation_agent", directive)

    def execute(
        self,
        test_results: list[ItemTestResult],
        judge_result: Optional[JudgementResult] = None,
        plan: Optional[InspectionPlan] = None,
        mode: str = "inspection",
    ) -> EvaluationResult:
        if self._directive:
            self._log("INFO", f"Directive: {self._directive}")

        if not test_results:
            return EvaluationResult(
                overall_passed=True,
                failure_reason=None,
                failed_items=[],
                analysis="검사 항목 없음.",
            )

        total = len(test_results)
        failed = [r for r in test_results if not r.passed]

        if not failed:
            return EvaluationResult(
                overall_passed=True,
                failure_reason=None,
                failed_items=[],
                analysis=f"전체 {total}개 항목 모두 통과.",
            )

        failed_ids: set[int] = {r.item_id for r in failed}
        fail_count = len(failed)

        collected: set[FailureReason] = set()

        for item in failed:
            collected.add(self._item_reason(item, judge_result, mode))

        if fail_count == total:
            collected.add(FailureReason.spec_issue)

        if fail_count >= 3 and plan is not None:
            for plan_item in plan.items:
                if plan_item.id in failed_ids and any(
                    dep in failed_ids for dep in plan_item.depends_on
                ):
                    collected.add(FailureReason.inspection_plan_issue)
                    break

        overall = min(collected, key=lambda r: _PRIORITY.index(r))
        analysis = (
            f"{total}개 항목 중 {fail_count}개 실패. "
            f"주요 원인: {_REASON_KO.get(overall, str(overall))}"
        )
        self._log("INFO", "Evaluation complete", {"overall": overall.value, "failed": fail_count})

        return EvaluationResult(
            overall_passed=False,
            failure_reason=overall,
            failed_items=sorted(failed_ids),
            analysis=analysis,
        )

    def _item_reason(
        self,
        item: ItemTestResult,
        judge_result: Optional[JudgementResult],
        mode: str,
    ) -> FailureReason:
        if "error" in (item.details or "").lower():
            return FailureReason.algorithm_runtime_error

        if judge_result is not None and self._is_low_scores(judge_result):
            return FailureReason.pipeline_bad_fit

        if mode == "align":
            if self._is_wrong_category_align(item.metrics):
                return FailureReason.algorithm_wrong_category
        else:
            if self._is_wrong_category_inspection(item.metrics):
                return FailureReason.algorithm_wrong_category

        return FailureReason.pipeline_bad_params

    def _is_low_scores(self, judge: JudgementResult) -> bool:
        return (
            judge.visibility_score < 0.4
            or judge.separability_score < 0.4
            or judge.measurability_score < 0.4
        )

    def _is_wrong_category_inspection(self, metrics) -> bool:
        acc = metrics.accuracy or 0.0
        fp = metrics.fp_rate or 0.0
        fn = metrics.fn_rate or 0.0
        return acc < 0.5 and fp > 0.3 and fn > 0.3

    def _is_wrong_category_align(self, metrics) -> bool:
        ce = metrics.coord_error or 0.0
        sr = metrics.success_rate or 0.0
        return ce > 10.0 and sr < 0.2
