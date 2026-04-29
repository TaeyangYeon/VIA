"""Feedback controller for determining retry strategies based on failure reasons."""
from __future__ import annotations

from typing import Optional

from agents.base_agent import BaseAgent
from agents.models import (
    EvaluationResult,
    FeedbackAction,
    FailureReason,
    JudgementResult,
)

# reason → (target_agent, action)
_MAPPING: dict[FailureReason, tuple[str, str]] = {
    FailureReason.pipeline_bad_fit:        ("pipeline_composer",  "recompose"),
    FailureReason.pipeline_bad_params:     ("parameter_searcher", "re-search"),
    FailureReason.algorithm_wrong_category:("algorithm_selector", "re-select"),
    FailureReason.algorithm_runtime_error: ("algorithm_coder",    "regenerate"),
    FailureReason.inspection_plan_issue:   ("inspection_plan",    "redesign"),
    FailureReason.spec_issue:              ("spec_agent",         "re-extract"),
}

# Escalation: reason → next reason (end of chain has no entry)
_ESCALATION: dict[FailureReason, FailureReason] = {
    FailureReason.pipeline_bad_params:      FailureReason.pipeline_bad_fit,
    FailureReason.pipeline_bad_fit:         FailureReason.spec_issue,
    FailureReason.algorithm_runtime_error:  FailureReason.algorithm_wrong_category,
    FailureReason.algorithm_wrong_category: FailureReason.inspection_plan_issue,
}


class FeedbackController(BaseAgent):
    def __init__(self, directive: Optional[str] = None) -> None:
        super().__init__("feedback_controller", directive)
        self._failure_history: list[dict] = []
        self._reason_counts: dict[str, int] = {}
        self._target_retry_counts: dict[str, int] = {}
        self._consecutive_reason: Optional[FailureReason] = None
        self._consecutive_count: int = 0

    def reset(self) -> None:
        self._failure_history.clear()
        self._reason_counts.clear()
        self._target_retry_counts.clear()
        self._consecutive_reason = None
        self._consecutive_count = 0

    def execute(
        self,
        eval_result: EvaluationResult,
        judge_result: Optional[JudgementResult] = None,
    ) -> Optional[FeedbackAction]:
        if self._directive:
            self._log("INFO", f"Directive: {self._directive}")

        if eval_result.overall_passed or eval_result.failure_reason is None:
            return None

        reason = eval_result.failure_reason

        # Track consecutive occurrences
        if reason == self._consecutive_reason:
            self._consecutive_count += 1
        else:
            self._consecutive_reason = reason
            self._consecutive_count = 1

        # Update reason count
        key = reason.value
        self._reason_counts[key] = self._reason_counts.get(key, 0) + 1

        # Record in history
        self._failure_history.append({
            "reason": reason.value,
            "failed_items": eval_result.failed_items,
        })

        # Determine effective reason (escalate if consecutive >= 2)
        escalated = False
        escalated_from: Optional[str] = None
        effective_reason = reason
        if self._consecutive_count >= 2 and reason in _ESCALATION:
            escalated_from = reason.value
            effective_reason = _ESCALATION[reason]
            escalated = True

        target_agent, action = _MAPPING[effective_reason]

        # Track retries per target
        retry_count = self._target_retry_counts.get(target_agent, 0)
        self._target_retry_counts[target_agent] = retry_count + 1

        context: dict = {
            "action": action,
            "failed_items": eval_result.failed_items,
            "failure_history": list(self._failure_history),
            "reason_counts": dict(self._reason_counts),
        }
        if escalated:
            context["escalated"] = True
            context["escalated_from"] = escalated_from
        if judge_result is not None:
            context["judge_feedback"] = {
                "visibility_score": judge_result.visibility_score,
                "separability_score": judge_result.separability_score,
                "measurability_score": judge_result.measurability_score,
                "problems": judge_result.problems,
                "next_suggestion": judge_result.next_suggestion,
            }

        self._log("INFO", "FeedbackAction determined", {
            "reason": reason.value,
            "effective_reason": effective_reason.value,
            "target_agent": target_agent,
            "escalated": escalated,
        })

        return FeedbackAction(
            target_agent=target_agent,
            reason=effective_reason,
            context=context,
            retry_count=retry_count,
        )
