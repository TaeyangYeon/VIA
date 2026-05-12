"""Tests for Step 53-hotfix: backend result serialization and GET response mapping."""
from __future__ import annotations

import asyncio
from unittest.mock import Mock

import cv2
import httpx
import numpy as np
import pytest

from agents.models import (
    AlgorithmCategory,
    AlgorithmResult,
    DecisionResult,
    DecisionType,
    EvaluationResult,
    FailureReason,
    InspectionItem,
    InspectionMode,
    InspectionPlan,
    ItemTestResult,
    PipelineBlock,
    ProcessingPipeline,
    SpecResult,
    TestMetrics,
)
from backend.main import app
from backend.routers.execute import get_manager
from backend.services.config_store import config_store
from backend.services.execution_manager import ExecutionManager
from backend.services.image_store import image_store


# ── Fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture(params=["asyncio"])
def anyio_backend(request):
    return request.param


@pytest.fixture(autouse=True)
def reset_stores():
    image_store.clear()
    config_store.clear()
    yield
    image_store.clear()
    config_store.clear()


@pytest.fixture
def image_path(tmp_path):
    img = np.zeros((100, 100, 3), dtype=np.uint8)
    path = tmp_path / "ok.png"
    cv2.imwrite(str(path), img)
    return str(path)


@pytest.fixture
def setup_full(image_path):
    image_store.add({
        "id": "a1", "filename": "ok.png", "purpose": "analysis",
        "label": "OK", "index": 1, "path": image_path,
    })
    config_store.save({"mode": "inspection", "max_iteration": 3})


@pytest.fixture
def async_client():
    transport = httpx.ASGITransport(app=app)
    return httpx.AsyncClient(transport=transport, base_url="http://testserver")


# ── Mock orchestrator output ──────────────────────────────────────────────────

def _make_pipeline():
    return ProcessingPipeline(
        name="BlobPipeline",
        blocks=[
            PipelineBlock(name="GaussianBlur", when_condition="always", params={"ksize": 5}),
            PipelineBlock(name="Threshold", when_condition="always", params={"thresh": 127}),
        ],
        score=0.95,
    )


def _make_algorithm_result():
    return AlgorithmResult(
        code="import cv2\nimg = cv2.imread('test.png')",
        explanation="가우시안 블러로 노이즈 제거 후 임계값 처리합니다.",
        category=AlgorithmCategory.BLOB,
        pipeline=_make_pipeline(),
    )


def _make_test_results():
    return [
        ItemTestResult(
            item_id=1, item_name="OK_1.png", passed=True,
            metrics=TestMetrics(accuracy=0.99, fp_rate=0.01, fn_rate=0.0),
        ),
        ItemTestResult(
            item_id=2, item_name="NG_1.png", passed=False,
            metrics=TestMetrics(accuracy=0.75, fp_rate=0.1, fn_rate=0.2),
        ),
    ]


def _make_evaluation_result(passed: bool = True):
    return EvaluationResult(
        overall_passed=passed,
        failure_reason=None if passed else FailureReason.pipeline_bad_params,
        failed_items=[] if passed else [2],
        analysis="분석 완료",
    )


def _make_decision_result():
    return DecisionResult(
        decision=DecisionType.rule_based,
        reason="단순 임계값으로 충분한 정확도 달성",
        confidence=0.92,
    )


def _make_inspection_plan():
    return InspectionPlan(
        items=[
            InspectionItem(
                id=1, name="결함 검출", purpose="표면 결함 탐지",
                method=AlgorithmCategory.BLOB,
            ),
        ],
        mode=InspectionMode.inspection,
    )


def _make_orchestrator_raw(passed: bool = True) -> dict:
    return {
        "spec_result": SpecResult(
            mode=InspectionMode.inspection,
            goal="표면 결함 검출",
            success_criteria={"accuracy": 0.95},
        ),
        "diagnosis": None,
        "best_pipeline": _make_pipeline(),
        "judge_result": None,
        "inspection_plan": _make_inspection_plan(),
        "algorithm_category": AlgorithmCategory.BLOB,
        "algorithm_result": _make_algorithm_result(),
        "code_validation": None,
        "test_results": _make_test_results(),
        "evaluation_result": _make_evaluation_result(passed),
        "warnings": [],
        "iteration_history": [],
        "decision_result": _make_decision_result() if passed else None,
    }


def _fast_factory(raw: dict | None = None, exc: Exception | None = None):
    def factory():
        orc = Mock()
        from agents.models import ExecutionProgress
        progress = ExecutionProgress(current_agent="", current_iteration=0, status="running", message="")

        if exc is not None:
            async def _execute(*a, **kw):
                raise exc
        else:
            async def _execute(*a, **kw):
                return raw if raw is not None else _make_orchestrator_raw()

        orc.execute = _execute
        orc.get_progress = Mock(return_value=progress)
        return orc

    return factory


# ── Unit tests: _map_result ───────────────────────────────────────────────────


class TestMapResult:
    """Test the _map_result mapping on the ExecutionManager directly."""

    def test_algorithm_code_extracted(self):
        mgr = ExecutionManager()
        raw = _make_orchestrator_raw()
        result = mgr._map_result(raw)
        assert result["algorithm_code"] == "import cv2\nimg = cv2.imread('test.png')"

    def test_algorithm_explanation_extracted(self):
        mgr = ExecutionManager()
        raw = _make_orchestrator_raw()
        result = mgr._map_result(raw)
        assert result["algorithm_explanation"] == "가우시안 블러로 노이즈 제거 후 임계값 처리합니다."

    def test_pipeline_serialized_to_dict(self):
        mgr = ExecutionManager()
        raw = _make_orchestrator_raw()
        result = mgr._map_result(raw)
        assert isinstance(result["pipeline"], dict)
        assert "blocks" in result["pipeline"]

    def test_pipeline_blocks_have_name_and_params(self):
        mgr = ExecutionManager()
        raw = _make_orchestrator_raw()
        result = mgr._map_result(raw)
        blocks = result["pipeline"]["blocks"]
        assert len(blocks) == 2
        assert blocks[0]["name"] == "GaussianBlur"
        assert blocks[0]["params"] == {"ksize": 5}

    def test_item_results_mapped(self):
        mgr = ExecutionManager()
        raw = _make_orchestrator_raw()
        result = mgr._map_result(raw)
        assert result["item_results"] is not None
        assert len(result["item_results"]) == 2
        first = result["item_results"][0]
        assert first["item_name"] == "OK_1.png"
        assert first["passed"] is True
        assert first["metrics"]["accuracy"] == 0.99
        assert first["metrics"]["fp_rate"] == 0.01
        assert first["metrics"]["fn_rate"] == 0.0

    def test_decision_value_extracted(self):
        mgr = ExecutionManager()
        raw = _make_orchestrator_raw()
        result = mgr._map_result(raw)
        assert result["decision"] == "rule_based"

    def test_decision_reason_extracted(self):
        mgr = ExecutionManager()
        raw = _make_orchestrator_raw()
        result = mgr._map_result(raw)
        assert result["decision_reason"] == "단순 임계값으로 충분한 정확도 달성"

    def test_summary_is_non_empty_string(self):
        mgr = ExecutionManager()
        raw = _make_orchestrator_raw()
        result = mgr._map_result(raw)
        assert isinstance(result["summary"], str)
        assert len(result["summary"]) > 0

    def test_result_is_json_serializable(self):
        import json
        mgr = ExecutionManager()
        raw = _make_orchestrator_raw()
        result = mgr._map_result(raw)
        serialized = json.dumps(result)
        parsed = json.loads(serialized)
        assert parsed["algorithm_code"] is not None

    def test_inspection_plan_serialized(self):
        mgr = ExecutionManager()
        raw = _make_orchestrator_raw()
        result = mgr._map_result(raw)
        assert result["inspection_plan"] is not None
        assert isinstance(result["inspection_plan"], (dict, list))

    def test_null_algorithm_result_no_crash(self):
        mgr = ExecutionManager()
        raw = _make_orchestrator_raw()
        raw["algorithm_result"] = None
        result = mgr._map_result(raw)
        assert result["algorithm_code"] is None
        assert result["algorithm_explanation"] is None

    def test_empty_test_results_no_crash(self):
        mgr = ExecutionManager()
        raw = _make_orchestrator_raw()
        raw["test_results"] = []
        result = mgr._map_result(raw)
        assert result["item_results"] is None or result["item_results"] == []

    def test_null_decision_result_no_crash(self):
        mgr = ExecutionManager()
        raw = _make_orchestrator_raw(passed=False)
        raw["decision_result"] = None
        result = mgr._map_result(raw)
        assert result["decision"] is None
        assert result["decision_reason"] is None

    def test_null_pipeline_no_crash(self):
        mgr = ExecutionManager()
        raw = _make_orchestrator_raw()
        raw["best_pipeline"] = None
        result = mgr._map_result(raw)
        assert result["pipeline"] is None

    def test_no_raw_orchestrator_keys_leak(self):
        """Frontend-facing result must NOT contain raw orchestrator keys."""
        mgr = ExecutionManager()
        raw = _make_orchestrator_raw()
        result = mgr._map_result(raw)
        for forbidden in ("spec_result", "diagnosis", "best_pipeline", "algorithm_result",
                          "evaluation_result", "code_validation", "iteration_history"):
            assert forbidden not in result, f"Raw key '{forbidden}' leaked into mapped result"


# ── Integration tests: state.result after execution ──────────────────────────


class TestExecutionManagerResultStorage:
    @pytest.mark.anyio
    async def test_state_result_populated_after_success(self, setup_full):
        mgr = ExecutionManager(orchestrator_factory=_fast_factory(_make_orchestrator_raw()))
        eid = await mgr.start("결함 검출")
        await asyncio.sleep(0.05)
        state = mgr.get_status(eid)
        assert state.status == "success"
        assert state.result is not None
        assert "algorithm_code" in state.result

    @pytest.mark.anyio
    async def test_state_result_has_summary(self, setup_full):
        mgr = ExecutionManager(orchestrator_factory=_fast_factory(_make_orchestrator_raw()))
        eid = await mgr.start("결함 검출")
        await asyncio.sleep(0.05)
        state = mgr.get_status(eid)
        assert state.result["summary"] is not None

    @pytest.mark.anyio
    async def test_state_result_has_pipeline_dict(self, setup_full):
        mgr = ExecutionManager(orchestrator_factory=_fast_factory(_make_orchestrator_raw()))
        eid = await mgr.start("결함 검출")
        await asyncio.sleep(0.05)
        state = mgr.get_status(eid)
        assert isinstance(state.result["pipeline"], dict)

    @pytest.mark.anyio
    async def test_state_result_is_none_on_failure(self, setup_full):
        mgr = ExecutionManager(orchestrator_factory=_fast_factory(exc=RuntimeError("오류")))
        eid = await mgr.start("결함 검출")
        await asyncio.sleep(0.05)
        state = mgr.get_status(eid)
        assert state.status == "failed"
        assert state.result is None


# ── API-level tests: GET response includes result ─────────────────────────────


class TestGetExecutionResultAPI:
    @pytest.mark.anyio
    async def test_get_response_includes_result_key(self, setup_full, async_client):
        mgr = ExecutionManager(orchestrator_factory=_fast_factory(_make_orchestrator_raw()))
        app.dependency_overrides[get_manager] = lambda: mgr
        try:
            resp = await async_client.post("/api/execute", json={"purpose_text": "결함 검출"})
            eid = resp.json()["execution_id"]
            await asyncio.sleep(0.05)
            resp2 = await async_client.get(f"/api/execute/{eid}")
            assert resp2.status_code == 200
            body = resp2.json()
            assert "result" in body
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.anyio
    async def test_get_response_result_has_algorithm_code(self, setup_full, async_client):
        mgr = ExecutionManager(orchestrator_factory=_fast_factory(_make_orchestrator_raw()))
        app.dependency_overrides[get_manager] = lambda: mgr
        try:
            resp = await async_client.post("/api/execute", json={"purpose_text": "결함 검출"})
            eid = resp.json()["execution_id"]
            await asyncio.sleep(0.05)
            resp2 = await async_client.get(f"/api/execute/{eid}")
            result = resp2.json()["result"]
            assert result is not None
            assert "algorithm_code" in result
            assert result["algorithm_code"] == "import cv2\nimg = cv2.imread('test.png')"
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.anyio
    async def test_get_response_result_has_item_results(self, setup_full, async_client):
        mgr = ExecutionManager(orchestrator_factory=_fast_factory(_make_orchestrator_raw()))
        app.dependency_overrides[get_manager] = lambda: mgr
        try:
            resp = await async_client.post("/api/execute", json={"purpose_text": "결함 검출"})
            eid = resp.json()["execution_id"]
            await asyncio.sleep(0.05)
            resp2 = await async_client.get(f"/api/execute/{eid}")
            result = resp2.json()["result"]
            assert result["item_results"] is not None
            assert result["item_results"][0]["item_name"] == "OK_1.png"
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.anyio
    async def test_get_response_result_has_decision(self, setup_full, async_client):
        mgr = ExecutionManager(orchestrator_factory=_fast_factory(_make_orchestrator_raw()))
        app.dependency_overrides[get_manager] = lambda: mgr
        try:
            resp = await async_client.post("/api/execute", json={"purpose_text": "결함 검출"})
            eid = resp.json()["execution_id"]
            await asyncio.sleep(0.05)
            resp2 = await async_client.get(f"/api/execute/{eid}")
            result = resp2.json()["result"]
            assert result["decision"] == "rule_based"
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.anyio
    async def test_get_response_result_production_scenario_failed_with_decision(self, setup_full, async_client):
        """Exact production scenario: pipeline failed, max iterations reached, decision made."""
        failed_raw = {
            "spec_result": SpecResult(
                mode=InspectionMode.inspection,
                goal="표면 결함 검출",
                success_criteria={"accuracy": 0.95},
            ),
            "diagnosis": None,
            "best_pipeline": ProcessingPipeline(
                name="BlobPipeline",
                blocks=[PipelineBlock(name="GaussianBlur", when_condition="always", params={"ksize": 5})],
                score=0.72,
            ),
            "judge_result": None,
            "inspection_plan": InspectionPlan(
                items=[InspectionItem(id=1, name="결함", purpose="결함 검출", method=AlgorithmCategory.BLOB)],
                mode=InspectionMode.inspection,
            ),
            "algorithm_category": AlgorithmCategory.BLOB,
            "algorithm_result": AlgorithmResult(
                code="import cv2\ndef inspect_item_1(img):\n    return {'result': 'OK'}",
                explanation="임계값 처리",
                category=AlgorithmCategory.BLOB,
                pipeline=ProcessingPipeline(name="BlobPipeline", blocks=[], score=0.72),
            ),
            "code_validation": None,
            "test_results": [
                ItemTestResult(item_id=1, item_name="결함", passed=False,
                               metrics=TestMetrics(accuracy=0.45, fp_rate=0.2, fn_rate=0.3)),
            ],
            "evaluation_result": EvaluationResult(
                overall_passed=False,
                failure_reason=FailureReason.pipeline_bad_params,
            ),
            "warnings": [],
            "iteration_history": [],
            "decision_result": DecisionResult(
                decision=DecisionType.edge_learning,
                reason="정확도 부족으로 Edge Learning 권장",
                confidence=0.9,
            ),
        }
        mgr = ExecutionManager(orchestrator_factory=_fast_factory(failed_raw))
        app.dependency_overrides[get_manager] = lambda: mgr
        try:
            resp = await async_client.post("/api/execute", json={"purpose_text": "결함 검출"})
            eid = resp.json()["execution_id"]
            await asyncio.sleep(0.05)
            resp2 = await async_client.get(f"/api/execute/{eid}")
            assert resp2.status_code == 200
            body = resp2.json()
            assert body["status"] == "success"
            result = body["result"]
            assert result is not None, "result must be populated after execution"
            assert result["summary"] is not None, "summary must be non-null"
            assert "실패" in result["summary"]
            assert result["decision"] == "edge_learning"
            assert result["decision_reason"] == "정확도 부족으로 Edge Learning 권장"
            assert result["algorithm_code"] is not None
            assert result["item_results"] is not None
            assert len(result["item_results"]) == 1
            assert result["item_results"][0]["item_name"] == "결함"
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.anyio
    async def test_get_response_result_null_when_running(self, setup_full, async_client):
        """During execution, result should be null."""
        from tests.test_execute_api import _hang_factory
        mgr = ExecutionManager(orchestrator_factory=_hang_factory())
        app.dependency_overrides[get_manager] = lambda: mgr
        try:
            resp = await async_client.post("/api/execute", json={"purpose_text": "결함 검출"})
            eid = resp.json()["execution_id"]
            resp2 = await async_client.get(f"/api/execute/{eid}")
            assert resp2.json()["result"] is None
        finally:
            app.dependency_overrides.clear()
            mgr._task.cancel()
            try:
                await mgr._task
            except (asyncio.CancelledError, Exception):
                pass
