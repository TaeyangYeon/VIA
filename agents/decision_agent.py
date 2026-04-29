"""Decision agent for final rule-based vs EL vs DL determination."""
from __future__ import annotations

from typing import Optional

from agents.base_agent import BaseAgent
from agents.models import (
    DecisionResult,
    DecisionType,
    DefectScale,
    ImageDiagnosis,
    JudgementResult,
)


class DecisionAgent(BaseAgent):
    def __init__(self, directive: Optional[str] = None) -> None:
        super().__init__("decision_agent", directive)

    def execute(
        self,
        iteration_history: list[dict],
        mode: str = "inspection",
        judge_result: Optional[JudgementResult] = None,
        image_diagnosis: Optional[ImageDiagnosis] = None,
    ) -> DecisionResult:
        if self._directive:
            self._log("INFO", f"Directive: {self._directive}")

        iteration_count = len(iteration_history)
        best_accuracy = self._best_accuracy(iteration_history)
        judge_avg = self._judge_avg(judge_result)

        details: dict = {
            "mode": mode,
            "iteration_count": iteration_count,
            "best_accuracy": best_accuracy,
            "latest_judge_avg": judge_avg,
        }
        if image_diagnosis is not None:
            details["defect_scale"] = self._defect_scale_str(image_diagnosis.defect_scale)
            details["texture_complexity"] = image_diagnosis.texture_complexity

        decision, reason = self._decide(
            mode=mode,
            iteration_count=iteration_count,
            best_accuracy=best_accuracy,
            judge_avg=judge_avg,
            image_diagnosis=image_diagnosis,
        )

        self._log("INFO", "Decision made", {"decision": decision.value, "mode": mode})

        return DecisionResult(
            decision=decision,
            reason=reason,
            confidence=1.0,
            details=details,
        )

    # ── Private ───────────────────────────────────────────────────────────────

    def _decide(
        self,
        mode: str,
        iteration_count: int,
        best_accuracy: Optional[float],
        judge_avg: Optional[float],
        image_diagnosis: Optional[ImageDiagnosis],
    ) -> tuple[DecisionType, str]:
        if mode == "align":
            return (
                DecisionType.rule_based,
                "정렬 모드에서는 하드웨어 및 광학 장비 개선이 필요합니다. "
                "카메라 위치, 조명 조건, 광학계 보정을 검토하십시오.",
            )

        # Rule 1: judge avg >= 0.6 → more parameter tuning room remains
        if judge_avg is not None and judge_avg >= 0.6:
            return (
                DecisionType.rule_based,
                f"판별 점수 평균({judge_avg:.2f})이 임계값 이상입니다. "
                "파라미터 조정 여지가 남아있어 규칙 기반 방식을 유지합니다.",
            )

        if image_diagnosis is not None:
            ds = self._defect_scale_str(image_diagnosis.defect_scale)

            # Rule 2: micro + low texture → Edge Learning
            if ds == DefectScale.micro.value and image_diagnosis.texture_complexity < 0.3:
                return (
                    DecisionType.edge_learning,
                    "결함이 미세하고 일관된 패턴을 가집니다. "
                    "수십~수백 장의 학습 이미지로 Edge Learning을 권장합니다.",
                )

            # Rule 3: texture defect OR high texture complexity → Deep Learning
            if ds == DefectScale.texture.value or image_diagnosis.texture_complexity >= 0.5:
                return (
                    DecisionType.deep_learning,
                    "결함 형태가 다양하거나 텍스처가 복잡합니다. "
                    "불규칙한 패턴을 처리하기 위해 딥러닝 방식을 권장합니다.",
                )

        # Rules 4–5: history-based
        if iteration_count >= 3 and best_accuracy is not None:
            if best_accuracy < 0.5:
                return (
                    DecisionType.deep_learning,
                    f"{iteration_count}회 반복 후 최고 정확도({best_accuracy:.2f})가 "
                    "0.5 미만입니다. 규칙 기반 한계로 딥러닝을 권장합니다.",
                )
            if best_accuracy < 0.7:
                return (
                    DecisionType.edge_learning,
                    f"{iteration_count}회 반복 후 최고 정확도({best_accuracy:.2f})가 "
                    "0.7 미만입니다. Edge Learning으로의 전환을 권장합니다.",
                )

        # Default fallback
        return (
            DecisionType.edge_learning,
            "현재 조건에서 규칙 기반 개선 여지가 불명확합니다. "
            "Edge Learning 적용을 권장합니다.",
        )

    @staticmethod
    def _defect_scale_str(defect_scale) -> str:
        """Normalize DefectScale enum or plain str to str value."""
        return defect_scale.value if hasattr(defect_scale, "value") else defect_scale

    def _best_accuracy(self, iteration_history: list[dict]) -> Optional[float]:
        best: Optional[float] = None
        for entry in iteration_history:
            for item in entry.get("test_results") or []:
                acc = getattr(getattr(item, "metrics", None), "accuracy", None)
                if acc is not None:
                    best = acc if best is None else max(best, acc)
        return best

    def _judge_avg(self, judge_result: Optional[JudgementResult]) -> Optional[float]:
        if judge_result is None:
            return None
        return (
            judge_result.visibility_score
            + judge_result.separability_score
            + judge_result.measurability_score
        ) / 3
