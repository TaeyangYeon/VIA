"""Orchestrator agent for controlling the full pipeline execution."""
from __future__ import annotations

from typing import Optional

import numpy as np

from agents.algorithm_coder_align import AlgorithmCoderAlign
from agents.algorithm_coder_inspection import AlgorithmCoderInspection
from agents.algorithm_selector import AlgorithmSelector
from agents.base_agent import BaseAgent
from agents.code_validator import CodeValidator
from agents.decision_agent import DecisionAgent
from agents.evaluation_agent import EvaluationAgent
from agents.feedback_controller import FeedbackController
from agents.image_analysis_agent import ImageAnalysisAgent
from agents.inspection_plan_agent import InspectionPlanAgent
from agents.models import (
    AgentDirectives,
    AlgorithmCategory,
    AlgorithmResult,
    DecisionResult,
    EvaluationResult,
    ExecutionProgress,
    FailureReason,
    ImageDiagnosis,
    InspectionMode,
    InspectionPlan,
    JudgementResult,
    ProcessingPipeline,
    SpecResult,
)
from agents.parameter_searcher import ParameterSearcher
from agents.pipeline_composer import PipelineComposer
from agents.spec_agent import SpecAgent
from agents.test_agent_align import TestAgentAlign
from agents.test_agent_inspection import TestAgentInspection
from agents.vision_judge_agent import VisionJudgeAgent

# Stage ordering for partial pipeline restarts (image_analysis is always excluded)
_STAGE_ORDER: dict[str, int] = {
    "pipeline_composer": 1,
    "parameter_searcher": 2,
    "inspection_plan": 3,
    "algorithm_selector": 4,
    "algorithm_coder": 5,
}


class Orchestrator(BaseAgent):
    def __init__(
        self,
        spec_agent: SpecAgent,
        image_analysis_agent: ImageAnalysisAgent,
        pipeline_composer: PipelineComposer,
        parameter_searcher: ParameterSearcher,
        vision_judge_agent: VisionJudgeAgent,
        inspection_plan_agent: InspectionPlanAgent,
        algorithm_selector: AlgorithmSelector,
        algorithm_coder_inspection: AlgorithmCoderInspection,
        algorithm_coder_align: AlgorithmCoderAlign,
        code_validator: CodeValidator,
        test_agent_inspection: TestAgentInspection,
        test_agent_align: TestAgentAlign,
        evaluation_agent: EvaluationAgent,
        feedback_controller: Optional[FeedbackController] = None,
        decision_agent: Optional[DecisionAgent] = None,
    ) -> None:
        super().__init__("orchestrator")
        self._spec_agent = spec_agent
        self._image_analysis_agent = image_analysis_agent
        self._pipeline_composer = pipeline_composer
        self._parameter_searcher = parameter_searcher
        self._vision_judge_agent = vision_judge_agent
        self._inspection_plan_agent = inspection_plan_agent
        self._algorithm_selector = algorithm_selector
        self._algorithm_coder_inspection = algorithm_coder_inspection
        self._algorithm_coder_align = algorithm_coder_align
        self._code_validator = code_validator
        self._test_agent_inspection = test_agent_inspection
        self._test_agent_align = test_agent_align
        self._evaluation_agent = evaluation_agent
        self._feedback_controller = feedback_controller
        self._decision_agent = decision_agent
        self._progress = ExecutionProgress(
            current_agent="", current_iteration=0, status="idle", message=""
        )

    def get_progress(self) -> ExecutionProgress:
        return self._progress

    async def execute(
        self,
        purpose_text: str,
        analysis_images: list[np.ndarray],
        test_images: list[tuple[np.ndarray, str]],
        directives: Optional[AgentDirectives] = None,
        config: Optional[dict] = None,
    ) -> dict:
        if self._feedback_controller is not None:
            self._feedback_controller.reset()

        max_iter: int = (config or {}).get("max_iteration", 5)
        iteration_history: list[dict] = []

        self._progress.status = "running"
        self._progress.current_iteration = 1
        self._progress.message = "파이프라인 시작"
        self._log("INFO", "Orchestrator started", {"purpose": purpose_text})

        try:
            self._distribute_directives(directives)

            self._progress.current_agent = "spec"
            self._log("INFO", "Starting spec agent")
            spec_result = await self._spec_agent.execute(user_text=purpose_text)
            self._log("INFO", "Spec agent completed")

            warnings = self._validate_goals(spec_result)

            # Image analysis runs exactly once — never re-run during retries
            self._progress.current_agent = "image_analysis"
            self._log("INFO", "Starting image analysis")
            first_image = analysis_images[0]
            diagnosis = self._image_analysis_agent.execute(first_image)
            self._log("INFO", "Image analysis completed")

            # Initial run from pipeline_composer
            (candidates, best_pipeline, best_judge, inspection_plan, algorithm_category,
             algorithm_result, code_validation, test_results, evaluation_result) = \
                await self._run_from_stage(
                    "pipeline_composer", spec_result, diagnosis,
                    None, None, None, None, None,
                    purpose_text, first_image, test_images,
                )

            # Retry loop — only executes when FeedbackController is wired in
            while not evaluation_result.overall_passed and self._feedback_controller is not None:
                if self._progress.current_iteration >= max_iter:
                    self._log("WARNING", f"Max iteration reached: {max_iter}")
                    break

                feedback = self._feedback_controller.execute(evaluation_result, best_judge)
                if feedback is None:
                    break

                iteration_history.append({
                    "iteration": self._progress.current_iteration,
                    "failure_reason": evaluation_result.failure_reason.value,
                    "target_agent": feedback.target_agent,
                    "test_results_summary": _summarize_test_results(test_results),
                    "judge_result_summary": _summarize_judge_result(best_judge),
                })

                self._progress.current_iteration += 1
                self._log(
                    "INFO",
                    f"Retry {self._progress.current_iteration}: "
                    f"target={feedback.target_agent}, reason={feedback.reason.value}",
                )

                restart_from = feedback.target_agent
                if restart_from == "spec_agent":
                    self._progress.current_agent = "spec"
                    self._log("INFO", "Starting spec agent (retry)")
                    spec_result = await self._spec_agent.execute(user_text=purpose_text)
                    restart_from = "pipeline_composer"

                (candidates, best_pipeline, best_judge, inspection_plan, algorithm_category,
                 algorithm_result, code_validation, test_results, evaluation_result) = \
                    await self._run_from_stage(
                        restart_from, spec_result, diagnosis,
                        candidates, best_pipeline, best_judge,
                        inspection_plan, algorithm_category,
                        purpose_text, first_image, test_images,
                    )

            decision_result: Optional[DecisionResult] = None
            if (
                not evaluation_result.overall_passed
                and self._progress.current_iteration >= max_iter
                and self._decision_agent is not None
            ):
                decision_result = self._decision_agent.execute(
                    iteration_history,
                    spec_result.mode,
                    best_judge,
                    diagnosis,
                )
                self._log("INFO", "Decision made", {"decision": decision_result.decision.value})

            if evaluation_result.overall_passed:
                self._progress.status = "success"
                self._progress.message = "파이프라인 성공"
            else:
                self._progress.status = "failed"
                self._progress.message = f"파이프라인 실패: {evaluation_result.failure_reason}"

            self._progress.current_agent = "orchestrator"
            self._log("INFO", "Pipeline completed", {"status": self._progress.status})

            return {
                "spec_result": spec_result,
                "diagnosis": diagnosis,
                "best_pipeline": best_pipeline,
                "judge_result": best_judge,
                "inspection_plan": inspection_plan,
                "algorithm_category": algorithm_category,
                "algorithm_result": algorithm_result,
                "code_validation": code_validation,
                "test_results": test_results,
                "evaluation_result": evaluation_result,
                "warnings": warnings,
                "iteration_history": iteration_history,
                "decision_result": decision_result,
            }

        except Exception as exc:
            self._progress.status = "failed"
            self._progress.message = f"오류: {exc}"
            self._log("ERROR", f"Pipeline failed: {exc}")
            raise

    async def _run_from_stage(
        self,
        start_from: str,
        spec_result: SpecResult,
        diagnosis: ImageDiagnosis,
        candidates: Optional[list[ProcessingPipeline]],
        best_pipeline: Optional[ProcessingPipeline],
        best_judge: Optional[JudgementResult],
        inspection_plan: Optional[InspectionPlan],
        algorithm_category: Optional[AlgorithmCategory],
        purpose_text: str,
        first_image: np.ndarray,
        test_images: list,
    ) -> tuple:
        """Run pipeline from start_from stage onwards, reusing cached state for skipped stages."""
        start_stage = _STAGE_ORDER.get(start_from, 5)
        mode = spec_result.mode

        if start_stage <= 1:
            self._progress.current_agent = "pipeline_composer"
            self._log("INFO", "Starting pipeline composer")
            candidates = self._pipeline_composer.execute(diagnosis)
            self._log("INFO", f"{len(candidates)} pipeline candidates generated")

        if start_stage <= 2:
            best_pipeline, best_judge = await self._select_best_pipeline(
                candidates, first_image, purpose_text
            )

        if start_stage <= 3 and mode == InspectionMode.inspection:
            self._progress.current_agent = "inspection_plan"
            self._log("INFO", "Starting inspection plan agent")
            diagnosis_summary = (
                f"surface={diagnosis.surface_type}, contrast={diagnosis.contrast:.2f}"
            )
            inspection_plan = await self._inspection_plan_agent.execute(
                purpose=purpose_text, image_diagnosis_summary=diagnosis_summary
            )
            self._log("INFO", "Inspection plan agent completed")

        if start_stage <= 4 and mode == InspectionMode.inspection:
            self._progress.current_agent = "algorithm_selector"
            self._log("INFO", "Starting algorithm selector")
            algorithm_category = self._algorithm_selector.execute(diagnosis)
            self._log("INFO", f"Algorithm selected: {algorithm_category}")

        algorithm_result: AlgorithmResult
        code_validation: object
        test_results: list
        evaluation_result: EvaluationResult

        if mode == InspectionMode.inspection:
            self._progress.current_agent = "algorithm_coder"
            self._log("INFO", "Starting algorithm coder (inspection)")
            algorithm_result = await self._algorithm_coder_inspection.execute(
                category=algorithm_category,
                pipeline=best_pipeline,
                plan=inspection_plan,
            )
            self._log("INFO", "Algorithm coder (inspection) completed")

            self._progress.current_agent = "code_validator"
            self._log("INFO", "Starting code validation")
            code_validation = self._code_validator.validate(algorithm_result.code, "inspection")
            self._log("INFO", f"Code validation: valid={code_validation.is_valid}")

            if code_validation.is_valid:
                self._progress.current_agent = "test_agent_inspection"
                self._log("INFO", "Starting test agent (inspection)")
                test_results = self._test_agent_inspection.execute(
                    algorithm_result.code, inspection_plan, test_images
                )
                self._log("INFO", "Test agent (inspection) completed")

                self._progress.current_agent = "evaluation_agent"
                self._log("INFO", "Starting evaluation agent")
                evaluation_result = self._evaluation_agent.execute(
                    test_results, judge_result=best_judge, plan=inspection_plan,
                    mode="inspection",
                )
                self._log("INFO", "Evaluation agent completed")
            else:
                test_results = []
                evaluation_result = EvaluationResult(
                    overall_passed=False,
                    failure_reason=FailureReason.algorithm_runtime_error,
                    failed_items=[],
                    analysis="코드 유효성 검사 실패",
                )

        else:  # align
            self._progress.current_agent = "algorithm_coder"
            self._log("INFO", "Starting algorithm coder (align)")
            algorithm_result = await self._algorithm_coder_align.execute(
                pipeline=best_pipeline
            )
            self._log("INFO", "Algorithm coder (align) completed")

            self._progress.current_agent = "code_validator"
            self._log("INFO", "Starting code validation")
            code_validation = self._code_validator.validate(algorithm_result.code, "align")
            self._log("INFO", f"Code validation: valid={code_validation.is_valid}")

            if code_validation.is_valid:
                self._progress.current_agent = "test_agent_align"
                self._log("INFO", "Starting test agent (align)")
                test_results = self._test_agent_align.execute(
                    algorithm_result.code, test_images
                )
                self._log("INFO", "Test agent (align) completed")

                self._progress.current_agent = "evaluation_agent"
                self._log("INFO", "Starting evaluation agent")
                evaluation_result = self._evaluation_agent.execute(
                    test_results, judge_result=best_judge, mode="align"
                )
                self._log("INFO", "Evaluation agent completed")
            else:
                test_results = []
                evaluation_result = EvaluationResult(
                    overall_passed=False,
                    failure_reason=FailureReason.algorithm_runtime_error,
                    failed_items=[],
                    analysis="코드 유효성 검사 실패",
                )

        return (
            candidates, best_pipeline, best_judge, inspection_plan, algorithm_category,
            algorithm_result, code_validation, test_results, evaluation_result,
        )

    def _distribute_directives(self, directives: Optional[AgentDirectives]) -> None:
        if directives is None:
            return
        pairs = [
            (directives.spec, self._spec_agent),
            (directives.image_analysis, self._image_analysis_agent),
            (directives.pipeline_composer, self._pipeline_composer),
            (directives.vision_judge, self._vision_judge_agent),
            (directives.inspection_plan, self._inspection_plan_agent),
            (directives.algorithm_coder, self._algorithm_coder_inspection),
            (directives.algorithm_coder, self._algorithm_coder_align),
            (directives.test, self._test_agent_inspection),
            (directives.test, self._test_agent_align),
        ]
        for value, agent in pairs:
            if value is not None:
                agent.set_directive(value)

    def _validate_goals(self, spec_result: SpecResult) -> list[str]:
        warnings: list[str] = []
        criteria = spec_result.success_criteria
        if not isinstance(criteria, dict):
            return warnings
        if criteria.get("accuracy", 0) > 0.99:
            warnings.append("accuracy > 0.99은 극단적인 목표입니다")
        if criteria.get("fp_rate", 1.0) < 0.001:
            warnings.append("fp_rate < 0.001은 극단적인 목표입니다")
        if criteria.get("fn_rate", 1.0) < 0.001:
            warnings.append("fn_rate < 0.001은 극단적인 목표입니다")
        if criteria.get("coord_error", 10.0) < 0.5:
            warnings.append("coord_error < 0.5은 극단적인 목표입니다")
        return warnings

    async def _select_best_pipeline(
        self,
        candidates: list[ProcessingPipeline],
        image: np.ndarray,
        purpose: str,
    ) -> tuple[ProcessingPipeline, JudgementResult]:
        self._log("INFO", f"Evaluating {len(candidates)} pipeline candidates")
        best_pipeline = candidates[0]
        best_judge: Optional[JudgementResult] = None
        best_score = -1.0

        for pipeline in candidates:
            self._progress.current_agent = "parameter_searcher"
            optimized = self._parameter_searcher.execute(pipeline, image)

            self._progress.current_agent = "vision_judge"
            judge = await self._vision_judge_agent.execute(
                original_image=image,
                processed_image=image,
                purpose=purpose,
                pipeline_name=optimized.name,
            )
            avg = (
                judge.visibility_score + judge.separability_score + judge.measurability_score
            ) / 3.0
            if avg > best_score:
                best_score = avg
                best_pipeline = optimized
                best_judge = judge

        self._log("INFO", f"Best pipeline: {best_pipeline.name} (score={best_score:.3f})")
        return best_pipeline, best_judge


def _summarize_test_results(test_results: list) -> dict:
    if not test_results:
        return {"count": 0, "passed": 0}
    passed = sum(1 for r in test_results if r.passed)
    return {"count": len(test_results), "passed": passed}


def _summarize_judge_result(judge_result: Optional[JudgementResult]) -> dict:
    if judge_result is None:
        return {}
    return {
        "visibility_score": judge_result.visibility_score,
        "separability_score": judge_result.separability_score,
        "measurability_score": judge_result.measurability_score,
    }
