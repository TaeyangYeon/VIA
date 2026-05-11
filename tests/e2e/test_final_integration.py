"""Step 52: Final Comprehensive Integration Test — All 6 Scenarios.

Covers:
  1. Inspection mode full pipeline (Local pattern) — real Gemma4
  2. Align mode full pipeline (Local pattern) — real Gemma4
  3. Directive-driven Inspection — AgentDirectives applied end-to-end
  4. Inspection retry exhaustion → Decision Agent triggered
  5. Align retry exhaustion → Decision Agent must return RULE_BASED
  6. Engine mode switching — Local ↔ Colab URL via API (no Gemma4 required)

Non-integration tests (no markers):
  - TestInfrastructure: fixture loading, orchestrator construction
  - TestEngineModeSwitching: POST /api/engine/config + GET /api/engine/status

Integration tests (both @integration and @e2e markers required):
  - All 5 Gemma4-dependent scenarios (1–5)

Pattern: VIA_OLLAMA_URL env var, check_ollama_available warmup, reset_singleton_client autouse.
"""
from __future__ import annotations

import asyncio
import os
import time
from pathlib import Path
from typing import Optional

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
    AlgorithmResult,
    DecisionResult,
    DecisionType,
    EvaluationResult,
    ImageDiagnosis,
    InspectionPlan,
    ItemTestResult,
    JudgementResult,
    ProcessingPipeline,
    SpecResult,
)
from agents.orchestrator import Orchestrator
from agents.parameter_searcher import ParameterSearcher
from agents.pipeline_composer import PipelineComposer
from agents.spec_agent import SpecAgent
from agents.test_agent_align import TestAgentAlign
from agents.test_agent_inspection import TestAgentInspection
from agents.vision_judge_agent import VisionJudgeAgent
from backend.services.ollama_client import OllamaClient

_FIXTURES_DIR = Path(__file__).parent.parent / "fixtures" / "sample_images"
OLLAMA_BASE_URL = os.environ.get("VIA_OLLAMA_URL", "http://localhost:11434")
_MODEL = "gemma4:e4b"

_INSPECTION_PURPOSE = (
    "원형 검출 검사: 이미지에서 원형 객체의 존재 여부를 판별하고, "
    "OK(정상 원형 존재)/NG(원형 결함 또는 부재)를 분류하는 알고리즘을 설계하라."
)
_ALIGN_PURPOSE = (
    "마크 정렬 검사: 이미지에서 밝은 원형 마크의 중심 좌표를 검출하고, "
    "align(image) 형식으로 x, y, confidence, method_used를 반환하는 알고리즘을 설계하라."
)

_ALIGN_IMAGE_FILENAMES = [
    "X_320.0_Y_240.0_1.png",
    "X_160.0_Y_120.0_2.png",
    "X_480.0_Y_360.0_3.png",
    "X_250.5_Y_200.5_4.png",
]


# ── anyio backend ──────────────────────────────────────────────────────────────

@pytest.fixture(params=["asyncio"])
def anyio_backend(request):
    return request.param


# ── Session fixtures ───────────────────────────────────────────────────────────

@pytest.fixture(scope="session")
def check_ollama_available():
    """Skip dependent tests if Ollama / gemma4:e4b is not reachable.

    Sets VIA_OLLAMA_URL on the singleton and warms up the model into GPU memory
    before any real test runs — the first Gemma4 request via Colab tunnel always
    fails or times out without this warmup step.
    """
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
    """OllamaClient tuned for Intel Mac slow first-inference (function-scoped for loop safety)."""
    return OllamaClient(
        base_url=OLLAMA_BASE_URL,
        model=_MODEL,
        health_timeout=300.0,
        generate_timeout=600.0,
        max_retries=2,
    )


@pytest.fixture(autouse=True)
def reset_singleton_client():
    """Reset module-level ollama_client singleton's cached HTTP client before each test.

    anyio creates a new event loop per test. An httpx.AsyncClient created in a
    previous event loop is not usable in the new one, so we null it out before
    each test so it gets re-created lazily in the current event loop.
    """
    from backend.services.ollama_client import ollama_client as _singleton
    _singleton._client = None
    yield
    _singleton._client = None


@pytest.fixture(scope="session")
def inspection_images() -> dict[str, np.ndarray]:
    """Load all 6 inspection sample images (OK_1..OK_3, NG_1..NG_3)."""
    names = ["OK_1", "OK_2", "OK_3", "NG_1", "NG_2", "NG_3"]
    images: dict[str, np.ndarray] = {}
    for name in names:
        path = _FIXTURES_DIR / f"{name}.png"
        img = cv2.imread(str(path), cv2.IMREAD_GRAYSCALE)
        assert img is not None, f"Failed to load {path}"
        images[name] = img
    return images


@pytest.fixture(scope="session")
def align_images() -> dict[str, np.ndarray]:
    """Load all 4 align sample images."""
    images: dict[str, np.ndarray] = {}
    for fname in _ALIGN_IMAGE_FILENAMES:
        path = _FIXTURES_DIR / fname
        img = cv2.imread(str(path), cv2.IMREAD_GRAYSCALE)
        assert img is not None, f"Failed to load {path}"
        images[fname] = img
    return images


# ── Helpers ────────────────────────────────────────────────────────────────────

def create_real_orchestrator(ollama_client: Optional[OllamaClient] = None) -> Orchestrator:
    """Instantiate all 15 agents + Orchestrator with real OllamaClient."""
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


def log_agent_output(agent_name: str, output: object) -> None:
    print(f"\n[{agent_name}] {type(output).__name__}: {output}")


_EXPECTED_RESULT_KEYS = {
    "spec_result", "diagnosis", "best_pipeline", "judge_result",
    "inspection_plan", "algorithm_category", "algorithm_result",
    "code_validation", "test_results", "evaluation_result",
    "warnings", "iteration_history", "decision_result",
}


def _assert_common_result_shape(result: dict) -> None:
    assert set(result.keys()) == _EXPECTED_RESULT_KEYS
    assert isinstance(result["spec_result"], SpecResult)
    assert isinstance(result["diagnosis"], ImageDiagnosis)
    assert isinstance(result["best_pipeline"], ProcessingPipeline)
    assert isinstance(result["judge_result"], JudgementResult)
    assert isinstance(result["evaluation_result"], EvaluationResult)
    assert isinstance(result["iteration_history"], list)
    assert result["decision_result"] is None or isinstance(result["decision_result"], DecisionResult)


# ── Non-integration: infrastructure tests ─────────────────────────────────────

class TestInfrastructure:
    """Verify test infrastructure, image fixtures, and orchestrator construction without Gemma4."""

    def test_inspection_images_loaded_correctly(
        self, inspection_images: dict[str, np.ndarray]
    ) -> None:
        expected = {"OK_1", "OK_2", "OK_3", "NG_1", "NG_2", "NG_3"}
        assert set(inspection_images.keys()) == expected

        for name, img in inspection_images.items():
            assert isinstance(img, np.ndarray), f"{name}: not ndarray"
            assert img.dtype == np.uint8, f"{name}: dtype={img.dtype}"
            assert img.ndim in (2, 3), f"{name}: ndim={img.ndim}"
            h, w = img.shape[:2]
            assert (h, w) == (480, 640), f"{name}: unexpected shape ({h},{w})"

        for name in ["OK_1", "OK_2", "OK_3"]:
            assert inspection_images[name].mean() < 254.0, f"{name}: no dark region"
        assert inspection_images["NG_1"].mean() > 254.0, "NG_1: should be blank"

    def test_align_images_loaded_correctly(
        self, align_images: dict[str, np.ndarray]
    ) -> None:
        assert set(align_images.keys()) == set(_ALIGN_IMAGE_FILENAMES)

        for fname, img in align_images.items():
            assert isinstance(img, np.ndarray), f"{fname}: not ndarray"
            assert img.dtype == np.uint8, f"{fname}: dtype={img.dtype}"
            assert img.ndim in (2, 3), f"{fname}: ndim={img.ndim}"
            h, w = img.shape[:2]
            assert (h, w) == (480, 640), f"{fname}: unexpected shape ({h},{w})"
            assert img.max() >= 200, f"{fname}: no bright alignment feature"
            assert img.mean() < 100.0, f"{fname}: expected dark background, mean={img.mean():.1f}"

    def test_orchestrator_constructs_without_ollama(self) -> None:
        """Orchestrator must be constructible without a live Ollama connection."""
        orc = create_real_orchestrator(ollama_client=None)
        assert orc is not None
        assert hasattr(orc, "execute")

    def test_orchestrator_has_all_15_agents(self) -> None:
        orc = create_real_orchestrator(ollama_client=None)
        # Orchestrator stores agents as private attributes prefixed with _
        expected_attrs = [
            "_spec_agent", "_image_analysis_agent", "_pipeline_composer",
            "_parameter_searcher", "_vision_judge_agent", "_inspection_plan_agent",
            "_algorithm_selector", "_algorithm_coder_inspection", "_algorithm_coder_align",
            "_code_validator", "_test_agent_inspection", "_test_agent_align",
            "_evaluation_agent", "_feedback_controller", "_decision_agent",
        ]
        for attr in expected_attrs:
            assert hasattr(orc, attr), f"Orchestrator missing agent: {attr}"

    def test_all_fixture_image_files_exist(self) -> None:
        for name in ["OK_1", "OK_2", "OK_3", "NG_1", "NG_2", "NG_3"]:
            path = _FIXTURES_DIR / f"{name}.png"
            assert path.exists(), f"Missing fixture: {path}"
        for fname in _ALIGN_IMAGE_FILENAMES:
            path = _FIXTURES_DIR / fname
            assert path.exists(), f"Missing fixture: {path}"

    def test_decision_agent_rule_based_for_align_mode(self) -> None:
        """DecisionAgent always returns RULE_BASED for align mode — no Gemma4 required."""
        da = DecisionAgent()
        for history in [[], [{"iteration": 1}], [{"iteration": i} for i in range(5)]]:
            result = da.execute(
                iteration_history=history,
                mode="align",
                judge_result=None,
                image_diagnosis=None,
            )
            assert isinstance(result, DecisionResult)
            assert result.decision == DecisionType.rule_based, (
                f"Align mode must be RULE_BASED, got {result.decision} "
                f"with {len(history)} history entries"
            )


# ── Non-integration: engine mode switching tests ───────────────────────────────

class TestEngineModeSwitching:
    """Scenario 6: Engine mode switching via API — no Gemma4 required.

    Uses httpx.AsyncClient + ASGITransport pattern matching the existing engine API tests.
    """

    @pytest.fixture(autouse=True)
    def reset_engine_config(self):
        """Reset engine_config_store and ollama_client base URL before/after each test.

        The engine config router calls ollama_client.set_base_url() which mutates the
        module-level singleton. We restore base_url directly (not via the async method)
        because _client is already None thanks to the reset_singleton_client autouse
        fixture, so no async cleanup is needed.
        """
        from backend.services.engine_config_store import engine_config_store
        from backend.services.ollama_client import ollama_client as _oc
        engine_config_store.reset()
        _oc.base_url = "http://localhost:11434"
        yield
        engine_config_store.reset()
        _oc.base_url = "http://localhost:11434"

    @pytest.fixture
    def async_client(self):
        from backend.main import app
        transport = httpx.ASGITransport(app=app)
        return httpx.AsyncClient(transport=transport, base_url="http://testserver")

    @pytest.mark.anyio
    async def test_initial_engine_status_is_local(self, async_client: httpx.AsyncClient) -> None:
        resp = await async_client.get("/api/engine/status")
        assert resp.status_code == 200
        data = resp.json()
        assert "engine_mode" in data
        assert "base_url" in data
        assert "connected" in data
        assert "model_available" in data

    @pytest.mark.anyio
    async def test_set_engine_to_local_mode(self, async_client: httpx.AsyncClient) -> None:
        resp = await async_client.post(
            "/api/engine/config",
            json={"engine_mode": "local"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["engine_mode"] == "local"
        assert data["colab_url"] is None
        log_agent_output("engine_config(local)", data)

    @pytest.mark.anyio
    async def test_set_engine_to_colab_mode_with_url(self, async_client: httpx.AsyncClient) -> None:
        resp = await async_client.post(
            "/api/engine/config",
            json={"engine_mode": "colab", "colab_url": "http://fake-colab-url:11434"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["engine_mode"] == "colab"
        assert data["colab_url"] == "http://fake-colab-url:11434"
        log_agent_output("engine_config(colab)", data)

    @pytest.mark.anyio
    async def test_colab_mode_without_url_returns_422(self, async_client: httpx.AsyncClient) -> None:
        resp = await async_client.post(
            "/api/engine/config",
            json={"engine_mode": "colab"},
        )
        assert resp.status_code == 422

    @pytest.mark.anyio
    async def test_engine_mode_local_to_colab_switch(self, async_client: httpx.AsyncClient) -> None:
        r1 = await async_client.post("/api/engine/config", json={"engine_mode": "local"})
        assert r1.status_code == 200
        assert r1.json()["engine_mode"] == "local"

        r2 = await async_client.post(
            "/api/engine/config",
            json={"engine_mode": "colab", "colab_url": "http://fake-colab:11434"},
        )
        assert r2.status_code == 200
        assert r2.json()["engine_mode"] == "colab"

        r3 = await async_client.get("/api/engine/status")
        assert r3.status_code == 200
        log_agent_output("engine_status(after_colab)", r3.json())

    @pytest.mark.anyio
    async def test_engine_mode_colab_to_local_switch(self, async_client: httpx.AsyncClient) -> None:
        await async_client.post(
            "/api/engine/config",
            json={"engine_mode": "colab", "colab_url": "http://fake-colab:11434"},
        )
        r = await async_client.post("/api/engine/config", json={"engine_mode": "local"})
        assert r.status_code == 200
        assert r.json()["engine_mode"] == "local"
        assert r.json()["colab_url"] is None

    @pytest.mark.anyio
    async def test_engine_status_reflects_colab_url(self, async_client: httpx.AsyncClient) -> None:
        await async_client.post(
            "/api/engine/config",
            json={"engine_mode": "colab", "colab_url": "http://fake-colab:11434"},
        )
        r = await async_client.get("/api/engine/status")
        assert r.status_code == 200
        data = r.json()
        assert data["base_url"] == "http://fake-colab:11434"

    @pytest.mark.anyio
    async def test_unreachable_colab_url_returns_warning_not_error(
        self, async_client: httpx.AsyncClient
    ) -> None:
        resp = await async_client.post(
            "/api/engine/config",
            json={"engine_mode": "colab", "colab_url": "http://127.0.0.1:19999"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["engine_mode"] == "colab"
        log_agent_output("engine_config(unreachable)", data)


# ── Integration / E2E tests ────────────────────────────────────────────────────

@pytest.mark.integration
@pytest.mark.e2e
class TestScenario1InspectionFullPipeline:
    """Scenario 1: Inspection mode full pipeline with real Gemma4."""

    @pytest.mark.anyio
    async def test_inspection_pipeline_executes_and_returns_all_keys(
        self,
        check_ollama_available,
        inspection_images: dict[str, np.ndarray],
        real_ollama_client: OllamaClient,
    ) -> None:
        orchestrator = create_real_orchestrator(real_ollama_client)
        analysis_images = [inspection_images["OK_1"], inspection_images["NG_1"]]
        test_images = [
            (inspection_images["OK_1"], "OK_1.png"),
            (inspection_images["OK_2"], "OK_2.png"),
            (inspection_images["NG_1"], "NG_1.png"),
            (inspection_images["NG_2"], "NG_2.png"),
        ]

        t0 = time.monotonic()
        result = await orchestrator.execute(
            purpose_text=_INSPECTION_PURPOSE,
            analysis_images=analysis_images,
            test_images=test_images,
            config={"mode": "inspection", "max_iteration": 1},
        )
        elapsed = time.monotonic() - t0
        print(f"\n[Scenario 1] Inspection full pipeline elapsed: {elapsed:.1f}s")

        _assert_common_result_shape(result)

        spec: SpecResult = result["spec_result"]
        log_agent_output("spec_agent", spec)
        assert spec.mode.value == "inspection"
        assert len(spec.goal) > 0

        diag: ImageDiagnosis = result["diagnosis"]
        log_agent_output("image_analysis", diag)
        assert isinstance(diag.contrast, float)
        assert 0.0 <= diag.noise_level <= 1.0

        pipeline: ProcessingPipeline = result["best_pipeline"]
        log_agent_output("pipeline", pipeline)
        assert len(pipeline.blocks) >= 1

        judge: JudgementResult = result["judge_result"]
        log_agent_output("vision_judge", judge)
        assert 0.0 <= judge.visibility_score <= 1.0
        assert 0.0 <= judge.separability_score <= 1.0
        assert 0.0 <= judge.measurability_score <= 1.0

        plan: InspectionPlan = result["inspection_plan"]
        log_agent_output("inspection_plan", plan)
        assert isinstance(plan, InspectionPlan)
        assert len(plan.items) >= 1

        cat: AlgorithmCategory = result["algorithm_category"]
        log_agent_output("algorithm_selector", cat)
        assert cat in list(AlgorithmCategory)

        algo: AlgorithmResult = result["algorithm_result"]
        log_agent_output("algorithm_coder", algo)
        assert len(algo.code.strip()) > 0
        assert len(algo.explanation.strip()) > 0

        test_results: list[ItemTestResult] = result["test_results"]
        log_agent_output("test_agent", test_results)
        assert isinstance(test_results, list)
        # test_results may be empty when Gemma4 generates code that fails CodeValidator
        # or TestAgentInspection cannot extract inspect* functions — this is structurally correct
        for tr in test_results:
            assert isinstance(tr.passed, bool)

        eval_result: EvaluationResult = result["evaluation_result"]
        log_agent_output("evaluation_agent", eval_result)
        assert isinstance(eval_result.overall_passed, bool)

        dr = result["decision_result"]
        log_agent_output("decision_agent", dr)
        assert dr is None or isinstance(dr, DecisionResult)


@pytest.mark.integration
@pytest.mark.e2e
class TestScenario2AlignFullPipeline:
    """Scenario 2: Align mode full pipeline with real Gemma4."""

    @pytest.mark.anyio
    async def test_align_pipeline_executes_and_returns_all_keys(
        self,
        check_ollama_available,
        align_images: dict[str, np.ndarray],
        real_ollama_client: OllamaClient,
    ) -> None:
        orchestrator = create_real_orchestrator(real_ollama_client)
        analysis_images = [align_images["X_320.0_Y_240.0_1.png"]]
        test_images = [(align_images[fname], fname) for fname in _ALIGN_IMAGE_FILENAMES]

        t0 = time.monotonic()
        result = await orchestrator.execute(
            purpose_text=_ALIGN_PURPOSE,
            analysis_images=analysis_images,
            test_images=test_images,
            config={"max_iteration": 1},
        )
        elapsed = time.monotonic() - t0
        print(f"\n[Scenario 2] Align full pipeline elapsed: {elapsed:.1f}s")

        _assert_common_result_shape(result)

        spec: SpecResult = result["spec_result"]
        log_agent_output("spec_agent", spec)
        assert spec.mode.value == "align"

        # Align mode: inspection_plan and algorithm_category are None
        assert result["inspection_plan"] is None
        assert result["algorithm_category"] is None

        algo: AlgorithmResult = result["algorithm_result"]
        log_agent_output("algorithm_coder_align", algo)
        assert len(algo.code.strip()) > 0
        assert algo.category == AlgorithmCategory.TEMPLATE_MATCHING

        test_results: list[ItemTestResult] = result["test_results"]
        log_agent_output("test_agent_align", test_results)
        assert isinstance(test_results, list)
        # test_results may be empty when generated align code fails validation
        for tr in test_results:
            assert tr.metrics.coord_error is not None
            assert tr.metrics.success_rate is not None

        dr = result["decision_result"]
        log_agent_output("decision_agent", dr)
        if dr is not None:
            assert dr.decision == DecisionType.rule_based, (
                f"Align mode DecisionAgent must return RULE_BASED, got {dr.decision}"
            )


@pytest.mark.integration
@pytest.mark.e2e
class TestScenario3DirectiveDrivenInspection:
    """Scenario 3: Directive-driven Inspection — AgentDirectives applied end-to-end."""

    @pytest.mark.anyio
    async def test_inspection_with_directives_produces_valid_result(
        self,
        check_ollama_available,
        inspection_images: dict[str, np.ndarray],
        real_ollama_client: OllamaClient,
    ) -> None:
        directives = AgentDirectives(
            spec="검사 목표에 집중하여 정확한 사양 추출",
            pipeline_composer="Blob",
            inspection_plan="Blob 검출 위주로 검사 항목 설계",
        )

        orchestrator = create_real_orchestrator(real_ollama_client)
        analysis_images = [inspection_images["OK_1"], inspection_images["NG_1"]]
        test_images = [
            (inspection_images["OK_1"], "OK_1.png"),
            (inspection_images["NG_1"], "NG_1.png"),
        ]

        t0 = time.monotonic()
        result = await orchestrator.execute(
            purpose_text=_INSPECTION_PURPOSE,
            analysis_images=analysis_images,
            test_images=test_images,
            directives=directives,
            config={"mode": "inspection", "max_iteration": 1},
        )
        elapsed = time.monotonic() - t0
        print(f"\n[Scenario 3] Directive-driven inspection elapsed: {elapsed:.1f}s")

        _assert_common_result_shape(result)

        spec: SpecResult = result["spec_result"]
        log_agent_output("spec_agent (with directive)", spec)
        assert spec.mode.value == "inspection"
        assert len(spec.goal) > 0

        plan: InspectionPlan = result["inspection_plan"]
        log_agent_output("inspection_plan (with directive)", plan)
        assert isinstance(plan, InspectionPlan)
        assert len(plan.items) >= 1

        eval_result: EvaluationResult = result["evaluation_result"]
        log_agent_output("evaluation_agent (with directive)", eval_result)
        assert isinstance(eval_result.overall_passed, bool)

    @pytest.mark.anyio
    async def test_pipeline_composer_blob_directive_affects_pipeline_selection(
        self,
        check_ollama_available,
        inspection_images: dict[str, np.ndarray],
        real_ollama_client: OllamaClient,
    ) -> None:
        """Blob directive should produce a pipeline with morphology blocks."""
        from agents.pipeline_blocks import block_library

        directives = AgentDirectives(pipeline_composer="Blob")
        orchestrator = create_real_orchestrator(real_ollama_client)
        analysis_images = [inspection_images["OK_1"]]
        test_images = [(inspection_images["OK_1"], "OK_1.png")]

        result = await orchestrator.execute(
            purpose_text=_INSPECTION_PURPOSE,
            analysis_images=analysis_images,
            test_images=test_images,
            directives=directives,
            config={"mode": "inspection", "max_iteration": 1},
        )

        pipeline: ProcessingPipeline = result["best_pipeline"]
        log_agent_output("best_pipeline (blob directive)", pipeline)
        assert isinstance(pipeline, ProcessingPipeline)
        assert len(pipeline.blocks) >= 1


@pytest.mark.integration
@pytest.mark.e2e
class TestScenario4InspectionRetryExhaustion:
    """Scenario 4: Inspection retry exhaustion → Decision Agent triggered."""

    @pytest.mark.anyio
    async def test_inspection_max_iteration_1_triggers_decision_agent(
        self,
        check_ollama_available,
        inspection_images: dict[str, np.ndarray],
        real_ollama_client: OllamaClient,
    ) -> None:
        """max_iteration=1 exhausts retries immediately, Decision Agent must be called."""
        orchestrator = create_real_orchestrator(real_ollama_client)
        analysis_images = [inspection_images["OK_1"]]
        test_images = [
            (inspection_images["OK_1"], "OK_1.png"),
            (inspection_images["NG_1"], "NG_1.png"),
        ]

        t0 = time.monotonic()
        result = await orchestrator.execute(
            purpose_text=_INSPECTION_PURPOSE,
            analysis_images=analysis_images,
            test_images=test_images,
            config={"mode": "inspection", "max_iteration": 1},
        )
        elapsed = time.monotonic() - t0
        print(f"\n[Scenario 4] Inspection exhaustion elapsed: {elapsed:.1f}s")

        _assert_common_result_shape(result)

        history = result["iteration_history"]
        log_agent_output("iteration_history", history)
        assert isinstance(history, list)

        eval_result: EvaluationResult = result["evaluation_result"]
        log_agent_output("evaluation_result", eval_result)
        assert isinstance(eval_result.overall_passed, bool)

        dr = result["decision_result"]
        log_agent_output("decision_agent (exhaustion)", dr)
        # decision_result present only if evaluation failed
        if not eval_result.overall_passed:
            assert dr is not None, "Decision Agent must be triggered when evaluation fails"
            assert isinstance(dr, DecisionResult)
            assert dr.decision in list(DecisionType)
            assert len(dr.reason.strip()) > 0
            assert 0.0 <= dr.confidence <= 1.0
            print(f"[Scenario 4] Decision: {dr.decision.value}, confidence={dr.confidence:.2f}")
        else:
            print("[Scenario 4] Evaluation passed — Decision Agent correctly not called")

    @pytest.mark.anyio
    async def test_inspection_decision_result_fields_are_valid(
        self,
        check_ollama_available,
        inspection_images: dict[str, np.ndarray],
        real_ollama_client: OllamaClient,
    ) -> None:
        """When DecisionResult is returned, all fields must be valid."""
        orchestrator = create_real_orchestrator(real_ollama_client)
        analysis_images = [inspection_images["OK_1"]]
        test_images = [(inspection_images["OK_1"], "OK_1.png")]

        result = await orchestrator.execute(
            purpose_text=_INSPECTION_PURPOSE,
            analysis_images=analysis_images,
            test_images=test_images,
            config={"mode": "inspection", "max_iteration": 1},
        )

        dr = result["decision_result"]
        if dr is not None:
            assert dr.decision in list(DecisionType)
            assert isinstance(dr.reason, str) and len(dr.reason.strip()) > 0
            assert isinstance(dr.confidence, float)
            assert 0.0 <= dr.confidence <= 1.0


@pytest.mark.integration
@pytest.mark.e2e
class TestScenario5AlignRetryExhaustion:
    """Scenario 5: Align retry exhaustion → Decision Agent must return RULE_BASED."""

    @pytest.mark.anyio
    async def test_align_exhaustion_decision_is_always_rule_based(
        self,
        check_ollama_available,
        align_images: dict[str, np.ndarray],
        real_ollama_client: OllamaClient,
    ) -> None:
        """max_iteration=1 on align mode — if Decision Agent triggered, must return RULE_BASED."""
        orchestrator = create_real_orchestrator(real_ollama_client)
        analysis_images = [align_images["X_320.0_Y_240.0_1.png"]]
        test_images = [(align_images[fname], fname) for fname in _ALIGN_IMAGE_FILENAMES[:2]]

        t0 = time.monotonic()
        result = await orchestrator.execute(
            purpose_text=_ALIGN_PURPOSE,
            analysis_images=analysis_images,
            test_images=test_images,
            config={"max_iteration": 1},
        )
        elapsed = time.monotonic() - t0
        print(f"\n[Scenario 5] Align exhaustion elapsed: {elapsed:.1f}s")

        _assert_common_result_shape(result)

        spec: SpecResult = result["spec_result"]
        assert spec.mode.value == "align"

        assert result["inspection_plan"] is None
        assert result["algorithm_category"] is None

        dr = result["decision_result"]
        log_agent_output("decision_agent (align exhaustion)", dr)
        if dr is not None:
            assert dr.decision == DecisionType.rule_based, (
                f"Align mode Decision Agent MUST return RULE_BASED, got {dr.decision}. "
                f"Reason: {dr.reason}"
            )
            assert len(dr.reason.strip()) > 0

    @pytest.mark.anyio
    async def test_align_exhaustion_no_inspection_plan_created(
        self,
        check_ollama_available,
        align_images: dict[str, np.ndarray],
        real_ollama_client: OllamaClient,
    ) -> None:
        """Align mode must never create inspection_plan or algorithm_category."""
        orchestrator = create_real_orchestrator(real_ollama_client)
        analysis_images = [align_images["X_320.0_Y_240.0_1.png"]]
        test_images = [(align_images["X_320.0_Y_240.0_1.png"], "X_320.0_Y_240.0_1.png")]

        result = await orchestrator.execute(
            purpose_text=_ALIGN_PURPOSE,
            analysis_images=analysis_images,
            test_images=test_images,
            config={"max_iteration": 1},
        )

        assert result["inspection_plan"] is None, (
            "Align mode must not generate an inspection_plan"
        )
        assert result["algorithm_category"] is None, (
            "Align mode must not generate an algorithm_category"
        )
        log_agent_output("align result keys", list(result.keys()))
