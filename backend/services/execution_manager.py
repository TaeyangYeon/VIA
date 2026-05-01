"""Pipeline execution lifecycle management service."""
from __future__ import annotations

import asyncio
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable, Optional

import cv2
import numpy as np

from agents.models import AgentDirectives
from backend.services.config_store import config_store
from backend.services.directive_store import directive_store
from backend.services.image_store import image_store


@dataclass
class ExecutionState:
    execution_id: str
    status: str  # running | success | failed | cancelled
    current_agent: str
    current_iteration: int
    result: Optional[dict]
    error: Optional[str]
    started_at: str
    completed_at: Optional[str]


class ExecutionManager:
    def __init__(self, orchestrator_factory: Optional[Callable] = None) -> None:
        self._factory = orchestrator_factory
        self._executions: dict[str, ExecutionState] = {}
        self._running_id: Optional[str] = None
        self._task: Optional[asyncio.Task] = None
        self._active_orc: Any = None

    def is_running(self) -> bool:
        return (
            self._running_id is not None
            and self._task is not None
            and not self._task.done()
        )

    async def start(self, purpose_text: str) -> str:
        if not purpose_text.strip():
            raise ValueError("purpose_text cannot be empty")

        analysis_metas = image_store.list_all(purpose="analysis")
        if not analysis_metas:
            raise ValueError("at least one analysis image is required")

        cfg = config_store.get()
        if cfg is None:
            raise ValueError("config not set")

        if self.is_running():
            raise RuntimeError("execution already running")

        execution_id = str(uuid.uuid4())
        state = ExecutionState(
            execution_id=execution_id,
            status="running",
            current_agent="",
            current_iteration=0,
            result=None,
            error=None,
            started_at=datetime.now(timezone.utc).isoformat(),
            completed_at=None,
        )
        self._executions[execution_id] = state
        self._running_id = execution_id

        orchestrator = self._get_orchestrator()
        self._active_orc = orchestrator

        directives = self._build_directives()
        analysis_images = self._load_images(analysis_metas)
        test_metas = image_store.list_all(purpose="test")
        test_images = [(self._load_image(m), m["filename"]) for m in test_metas]

        self._task = asyncio.create_task(
            self._run(
                orchestrator, state, purpose_text,
                analysis_images, test_images, directives, cfg,
            )
        )

        return execution_id

    def get_status(self, execution_id: str) -> Optional[ExecutionState]:
        state = self._executions.get(execution_id)
        if state is None:
            return None
        if state.status == "running" and self._active_orc is not None:
            progress = self._active_orc.get_progress()
            state.current_agent = progress.current_agent
            state.current_iteration = progress.current_iteration
        return state

    async def cancel(self, execution_id: str) -> Optional[ExecutionState]:
        state = self._executions.get(execution_id)
        if state is None:
            return None
        if state.status != "running":
            return state
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except (asyncio.CancelledError, Exception):
                pass
        # Python 3.11 C-Task may skip the coroutine body when cancelled before it starts.
        # Force-update state to ensure consistency regardless of which path was taken.
        if state.status == "running":
            state.status = "cancelled"
            if state.completed_at is None:
                state.completed_at = datetime.now(timezone.utc).isoformat()
        if self._running_id == state.execution_id:
            self._running_id = None
            self._active_orc = None
        return state

    def get_history(self) -> list[ExecutionState]:
        return sorted(
            self._executions.values(),
            key=lambda s: s.started_at,
            reverse=True,
        )

    def _get_orchestrator(self) -> Any:
        if self._factory is not None:
            return self._factory()
        return _create_real_orchestrator()

    def _build_directives(self) -> AgentDirectives:
        d = directive_store.get()
        return AgentDirectives(
            orchestrator=d.get("orchestrator"),
            spec=d.get("spec"),
            image_analysis=d.get("image_analysis"),
            pipeline_composer=d.get("pipeline_composer"),
            vision_judge=d.get("vision_judge"),
            inspection_plan=d.get("inspection_plan"),
            algorithm_coder=d.get("algorithm_coder"),
            test=d.get("test"),
        )

    def _load_images(self, metas: list[dict]) -> list[np.ndarray]:
        images = []
        for meta in metas:
            img = cv2.imread(meta["path"])
            if img is not None:
                images.append(img)
        return images

    def _load_image(self, meta: dict) -> np.ndarray:
        img = cv2.imread(meta["path"])
        return img if img is not None else np.zeros((100, 100, 3), dtype=np.uint8)

    async def _run(
        self,
        orchestrator: Any,
        state: ExecutionState,
        purpose_text: str,
        analysis_images: list[np.ndarray],
        test_images: list[tuple[np.ndarray, str]],
        directives: AgentDirectives,
        config: dict,
    ) -> None:
        try:
            result = await orchestrator.execute(
                purpose_text=purpose_text,
                analysis_images=analysis_images,
                test_images=test_images,
                directives=directives,
                config=config,
            )
            state.status = "success"
            state.result = result
        except asyncio.CancelledError:
            state.status = "cancelled"
            raise
        except Exception as exc:
            state.status = "failed"
            state.error = str(exc)
        finally:
            state.completed_at = datetime.now(timezone.utc).isoformat()
            if self._running_id == state.execution_id:
                self._running_id = None
                self._active_orc = None


def _create_real_orchestrator() -> Any:
    from agents.algorithm_coder_align import AlgorithmCoderAlign
    from agents.algorithm_coder_inspection import AlgorithmCoderInspection
    from agents.algorithm_selector import AlgorithmSelector
    from agents.code_validator import CodeValidator
    from agents.decision_agent import DecisionAgent
    from agents.evaluation_agent import EvaluationAgent
    from agents.feedback_controller import FeedbackController
    from agents.image_analysis_agent import ImageAnalysisAgent
    from agents.inspection_plan_agent import InspectionPlanAgent
    from agents.orchestrator import Orchestrator
    from agents.parameter_searcher import ParameterSearcher
    from agents.pipeline_composer import PipelineComposer
    from agents.spec_agent import SpecAgent
    from agents.test_agent_align import TestAgentAlign
    from agents.test_agent_inspection import TestAgentInspection
    from agents.vision_judge_agent import VisionJudgeAgent
    from backend.services.ollama_client import ollama_client

    return Orchestrator(
        spec_agent=SpecAgent(ollama_client),
        image_analysis_agent=ImageAnalysisAgent(),
        pipeline_composer=PipelineComposer(),
        parameter_searcher=ParameterSearcher(),
        vision_judge_agent=VisionJudgeAgent(ollama_client),
        inspection_plan_agent=InspectionPlanAgent(ollama_client),
        algorithm_selector=AlgorithmSelector(),
        algorithm_coder_inspection=AlgorithmCoderInspection(ollama_client),
        algorithm_coder_align=AlgorithmCoderAlign(ollama_client),
        code_validator=CodeValidator(),
        test_agent_inspection=TestAgentInspection(),
        test_agent_align=TestAgentAlign(),
        evaluation_agent=EvaluationAgent(),
        feedback_controller=FeedbackController(),
        decision_agent=DecisionAgent(),
    )


execution_manager = ExecutionManager()
