"""Tests for Step 31: Pipeline Execution API."""
from __future__ import annotations

import asyncio
from unittest.mock import Mock

import cv2
import httpx
import numpy as np
import pytest

from agents.models import ExecutionProgress
from backend.main import app
from backend.services.config_store import config_store
from backend.services.directive_store import directive_store
from backend.services.execution_manager import ExecutionManager, ExecutionState
from backend.services.image_store import image_store
from backend.routers.execute import get_manager


@pytest.fixture(params=["asyncio"])
def anyio_backend(request):
    return request.param


@pytest.fixture(autouse=True)
def reset_stores():
    image_store.clear()
    config_store.clear()
    directive_store.reset()
    yield
    image_store.clear()
    config_store.clear()
    directive_store.reset()


@pytest.fixture
def async_client():
    transport = httpx.ASGITransport(app=app)
    return httpx.AsyncClient(transport=transport, base_url="http://testserver")


# ── Mock helpers ──────────────────────────────────────────────────────────────


def _mock_progress(agent: str = "", iteration: int = 0, status: str = "idle") -> ExecutionProgress:
    return ExecutionProgress(current_agent=agent, current_iteration=iteration, status=status, message="")


def _fast_factory(result: dict | None = None, exc: Exception | None = None):
    """Factory returning a mock orchestrator that completes immediately."""
    def factory():
        orc = Mock()
        progress = _mock_progress(status="running")

        if exc is not None:
            async def _execute(*a, **kw):
                raise exc
        else:
            async def _execute(*a, **kw):
                progress.status = "success"
                return result if result is not None else {"ok": True}

        orc.execute = _execute
        orc.get_progress = Mock(return_value=progress)
        return orc

    return factory


def _hang_factory():
    """Factory returning a mock orchestrator that hangs until cancelled."""
    def factory():
        orc = Mock()
        progress = _mock_progress(status="running")

        async def _execute(*a, **kw):
            await asyncio.sleep(1000)

        orc.execute = _execute
        orc.get_progress = Mock(return_value=progress)
        return orc

    return factory


# ── Fixtures ─────────────────────────────────────────────────────────────────


@pytest.fixture
def image_path(tmp_path):
    img = np.zeros((100, 100, 3), dtype=np.uint8)
    path = tmp_path / "analysis.png"
    cv2.imwrite(str(path), img)
    return str(path)


@pytest.fixture
def setup_analysis_image(image_path):
    image_store.add({
        "id": "a1",
        "filename": "analysis.png",
        "purpose": "analysis",
        "label": "OK",
        "index": 1,
        "path": image_path,
    })


@pytest.fixture
def setup_config():
    config_store.save({"max_iteration": 3})


@pytest.fixture
def full_setup(setup_analysis_image, setup_config):
    pass


@pytest.fixture
def mock_api_mgr(tmp_path):
    """Fast execution manager wired into the FastAPI app via dependency override."""
    img = np.zeros((100, 100, 3), dtype=np.uint8)
    path = tmp_path / "analysis.png"
    cv2.imwrite(str(path), img)
    image_store.add({
        "id": "a1", "filename": "analysis.png", "purpose": "analysis",
        "label": "OK", "index": 1, "path": str(path),
    })
    config_store.save({"max_iteration": 3})
    mgr = ExecutionManager(orchestrator_factory=_fast_factory())
    app.dependency_overrides[get_manager] = lambda: mgr
    yield mgr
    app.dependency_overrides.clear()


@pytest.fixture
def hang_api_mgr(tmp_path):
    """Hanging execution manager wired into the FastAPI app via dependency override."""
    img = np.zeros((100, 100, 3), dtype=np.uint8)
    path = tmp_path / "analysis.png"
    cv2.imwrite(str(path), img)
    image_store.add({
        "id": "a1", "filename": "analysis.png", "purpose": "analysis",
        "label": "OK", "index": 1, "path": str(path),
    })
    config_store.save({"max_iteration": 3})
    mgr = ExecutionManager(orchestrator_factory=_hang_factory())
    app.dependency_overrides[get_manager] = lambda: mgr
    yield mgr
    app.dependency_overrides.clear()


# ── ExecutionState ────────────────────────────────────────────────────────────


class TestExecutionState:
    def test_stores_all_required_fields(self):
        state = ExecutionState(
            execution_id="abc",
            status="running",
            current_agent="spec",
            current_iteration=2,
            result=None,
            error=None,
            started_at="2026-01-01T00:00:00+00:00",
            completed_at=None,
        )
        assert state.execution_id == "abc"
        assert state.status == "running"
        assert state.current_agent == "spec"
        assert state.current_iteration == 2

    def test_result_and_error_accept_none(self):
        state = ExecutionState(
            execution_id="x", status="idle", current_agent="",
            current_iteration=0, result=None, error=None,
            started_at="2026-01-01T00:00:00+00:00", completed_at=None,
        )
        assert state.result is None
        assert state.error is None

    def test_completed_at_accepts_none(self):
        state = ExecutionState(
            execution_id="x", status="idle", current_agent="",
            current_iteration=0, result=None, error=None,
            started_at="2026-01-01T00:00:00+00:00", completed_at=None,
        )
        assert state.completed_at is None


# ── ExecutionManager.start() ──────────────────────────────────────────────────


class TestExecutionManagerStart:
    @pytest.mark.anyio
    async def test_returns_uuid_string(self, full_setup):
        mgr = ExecutionManager(orchestrator_factory=_fast_factory())
        eid = await mgr.start("detect defects")
        assert isinstance(eid, str)
        assert len(eid) == 36

    @pytest.mark.anyio
    async def test_initial_status_is_running(self, full_setup):
        mgr = ExecutionManager(orchestrator_factory=_hang_factory())
        eid = await mgr.start("detect defects")
        state = mgr.get_status(eid)
        assert state is not None
        assert state.status == "running"

    @pytest.mark.anyio
    async def test_raises_value_error_for_empty_purpose(self, full_setup):
        mgr = ExecutionManager(orchestrator_factory=_fast_factory())
        with pytest.raises(ValueError, match="purpose_text"):
            await mgr.start("")

    @pytest.mark.anyio
    async def test_raises_value_error_for_whitespace_purpose(self, full_setup):
        mgr = ExecutionManager(orchestrator_factory=_fast_factory())
        with pytest.raises(ValueError, match="purpose_text"):
            await mgr.start("   ")

    @pytest.mark.anyio
    async def test_raises_when_no_analysis_images(self, setup_config):
        mgr = ExecutionManager(orchestrator_factory=_fast_factory())
        with pytest.raises(ValueError, match="analysis image"):
            await mgr.start("detect defects")

    @pytest.mark.anyio
    async def test_raises_when_config_not_set(self, setup_analysis_image):
        mgr = ExecutionManager(orchestrator_factory=_fast_factory())
        with pytest.raises(ValueError, match="config"):
            await mgr.start("detect defects")

    @pytest.mark.anyio
    async def test_raises_runtime_error_when_already_running(self, full_setup):
        mgr = ExecutionManager(orchestrator_factory=_hang_factory())
        await mgr.start("first")
        with pytest.raises(RuntimeError, match="already running"):
            await mgr.start("second")

    @pytest.mark.anyio
    async def test_stores_state_by_execution_id(self, full_setup):
        mgr = ExecutionManager(orchestrator_factory=_hang_factory())
        eid = await mgr.start("detect defects")
        state = mgr.get_status(eid)
        assert state is not None
        assert state.execution_id == eid


# ── ExecutionManager.get_status() ─────────────────────────────────────────────


class TestExecutionManagerStatus:
    def test_returns_none_for_unknown_id(self):
        mgr = ExecutionManager(orchestrator_factory=_fast_factory())
        assert mgr.get_status("nonexistent") is None

    @pytest.mark.anyio
    async def test_returns_state_for_known_id(self, full_setup):
        mgr = ExecutionManager(orchestrator_factory=_hang_factory())
        eid = await mgr.start("test")
        assert mgr.get_status(eid) is not None

    @pytest.mark.anyio
    async def test_status_becomes_success_after_task_completes(self, full_setup):
        mgr = ExecutionManager(orchestrator_factory=_fast_factory())
        eid = await mgr.start("test")
        await asyncio.sleep(0)  # yield to let background task finish
        assert mgr.get_status(eid).status == "success"

    @pytest.mark.anyio
    async def test_status_becomes_failed_on_orchestrator_error(self, full_setup):
        mgr = ExecutionManager(orchestrator_factory=_fast_factory(exc=RuntimeError("oops")))
        eid = await mgr.start("test")
        await asyncio.sleep(0)
        state = mgr.get_status(eid)
        assert state.status == "failed"
        assert "oops" in state.error


# ── ExecutionManager.cancel() ─────────────────────────────────────────────────


class TestExecutionManagerCancel:
    @pytest.mark.anyio
    async def test_cancel_returns_none_for_unknown_id(self):
        mgr = ExecutionManager(orchestrator_factory=_fast_factory())
        result = await mgr.cancel("nonexistent")
        assert result is None

    @pytest.mark.anyio
    async def test_cancel_sets_status_to_cancelled(self, full_setup):
        mgr = ExecutionManager(orchestrator_factory=_hang_factory())
        eid = await mgr.start("test")
        state = await mgr.cancel(eid)
        assert state.status == "cancelled"

    @pytest.mark.anyio
    async def test_cancel_sets_completed_at(self, full_setup):
        mgr = ExecutionManager(orchestrator_factory=_hang_factory())
        eid = await mgr.start("test")
        state = await mgr.cancel(eid)
        assert state.completed_at is not None

    @pytest.mark.anyio
    async def test_cancel_returns_state_unchanged_when_already_completed(self, full_setup):
        mgr = ExecutionManager(orchestrator_factory=_fast_factory())
        eid = await mgr.start("test")
        await asyncio.sleep(0)  # let it complete as success
        state = await mgr.cancel(eid)
        assert state.status == "success"  # unchanged

    @pytest.mark.anyio
    async def test_cancel_clears_running_state_allowing_new_start(self, full_setup):
        mgr = ExecutionManager(orchestrator_factory=_hang_factory())
        eid1 = await mgr.start("first")
        await mgr.cancel(eid1)
        eid2 = await mgr.start("second")
        assert eid2 != eid1


# ── ExecutionManager.is_running() ─────────────────────────────────────────────


class TestExecutionManagerIsRunning:
    def test_false_initially(self):
        mgr = ExecutionManager(orchestrator_factory=_fast_factory())
        assert not mgr.is_running()

    @pytest.mark.anyio
    async def test_true_while_hanging_execution_runs(self, full_setup):
        mgr = ExecutionManager(orchestrator_factory=_hang_factory())
        await mgr.start("test")
        assert mgr.is_running()

    @pytest.mark.anyio
    async def test_false_after_fast_execution_completes(self, full_setup):
        mgr = ExecutionManager(orchestrator_factory=_fast_factory())
        await mgr.start("test")
        await asyncio.sleep(0)
        assert not mgr.is_running()


# ── ExecutionManager.get_history() ────────────────────────────────────────────


class TestExecutionManagerHistory:
    def test_empty_initially(self):
        mgr = ExecutionManager(orchestrator_factory=_fast_factory())
        assert mgr.get_history() == []

    @pytest.mark.anyio
    async def test_contains_execution_after_start(self, full_setup):
        mgr = ExecutionManager(orchestrator_factory=_hang_factory())
        eid = await mgr.start("test")
        history = mgr.get_history()
        assert len(history) == 1
        assert history[0].execution_id == eid

    @pytest.mark.anyio
    async def test_returns_list_type(self, full_setup):
        mgr = ExecutionManager(orchestrator_factory=_fast_factory())
        await mgr.start("test")
        assert isinstance(mgr.get_history(), list)


# ── API: POST /api/execute ────────────────────────────────────────────────────


class TestPostExecuteAPI:
    @pytest.mark.anyio
    async def test_returns_202_accepted(self, mock_api_mgr, async_client):
        async with async_client as client:
            resp = await client.post("/api/execute", json={"purpose_text": "detect defects"})
        assert resp.status_code == 202

    @pytest.mark.anyio
    async def test_response_contains_execution_id_and_running_status(self, mock_api_mgr, async_client):
        async with async_client as client:
            resp = await client.post("/api/execute", json={"purpose_text": "detect defects"})
        body = resp.json()
        assert "execution_id" in body
        assert body["status"] == "running"

    @pytest.mark.anyio
    async def test_returns_400_for_empty_purpose(self, mock_api_mgr, async_client):
        async with async_client as client:
            resp = await client.post("/api/execute", json={"purpose_text": ""})
        assert resp.status_code == 400

    @pytest.mark.anyio
    async def test_returns_400_for_whitespace_purpose(self, mock_api_mgr, async_client):
        async with async_client as client:
            resp = await client.post("/api/execute", json={"purpose_text": "   "})
        assert resp.status_code == 400

    @pytest.mark.anyio
    async def test_returns_400_when_no_analysis_images(self, async_client):
        config_store.save({"max_iteration": 3})
        mgr = ExecutionManager(orchestrator_factory=_fast_factory())
        app.dependency_overrides[get_manager] = lambda: mgr
        try:
            async with async_client as client:
                resp = await client.post("/api/execute", json={"purpose_text": "detect"})
            assert resp.status_code == 400
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.anyio
    async def test_returns_400_when_config_not_set(self, tmp_path, async_client):
        img = np.zeros((100, 100, 3), dtype=np.uint8)
        path = tmp_path / "img.png"
        cv2.imwrite(str(path), img)
        image_store.add({
            "id": "a2", "filename": "img.png", "purpose": "analysis",
            "label": "OK", "index": 1, "path": str(path),
        })
        mgr = ExecutionManager(orchestrator_factory=_fast_factory())
        app.dependency_overrides[get_manager] = lambda: mgr
        try:
            async with async_client as client:
                resp = await client.post("/api/execute", json={"purpose_text": "detect"})
            assert resp.status_code == 400
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.anyio
    async def test_returns_409_when_already_running(self, hang_api_mgr, async_client):
        async with async_client as client:
            await client.post("/api/execute", json={"purpose_text": "first"})
            resp = await client.post("/api/execute", json={"purpose_text": "second"})
        assert resp.status_code == 409

    @pytest.mark.anyio
    async def test_missing_purpose_text_returns_422(self, mock_api_mgr, async_client):
        async with async_client as client:
            resp = await client.post("/api/execute", json={})
        assert resp.status_code == 422


# ── API: GET /api/execute/{id} ────────────────────────────────────────────────


class TestGetExecutionAPI:
    @pytest.mark.anyio
    async def test_returns_200_with_execution_state(self, hang_api_mgr, async_client):
        async with async_client as client:
            start = await client.post("/api/execute", json={"purpose_text": "test"})
            eid = start.json()["execution_id"]
            resp = await client.get(f"/api/execute/{eid}")
        assert resp.status_code == 200
        assert resp.json()["execution_id"] == eid

    @pytest.mark.anyio
    async def test_returns_404_for_unknown_id(self, mock_api_mgr, async_client):
        async with async_client as client:
            resp = await client.get("/api/execute/does-not-exist")
        assert resp.status_code == 404

    @pytest.mark.anyio
    async def test_response_includes_all_required_fields(self, hang_api_mgr, async_client):
        async with async_client as client:
            start = await client.post("/api/execute", json={"purpose_text": "test"})
            eid = start.json()["execution_id"]
            resp = await client.get(f"/api/execute/{eid}")
        body = resp.json()
        for field in ("execution_id", "status", "current_agent", "current_iteration", "started_at"):
            assert field in body

    @pytest.mark.anyio
    async def test_completed_at_is_set_after_success(self, mock_api_mgr, async_client):
        async with async_client as client:
            start = await client.post("/api/execute", json={"purpose_text": "test"})
            eid = start.json()["execution_id"]
            await asyncio.sleep(0)  # let background task finish
            resp = await client.get(f"/api/execute/{eid}")
        assert resp.json()["completed_at"] is not None


# ── API: POST /api/execute/{id}/cancel ────────────────────────────────────────


class TestCancelExecutionAPI:
    @pytest.mark.anyio
    async def test_returns_200_when_cancelling_running_execution(self, hang_api_mgr, async_client):
        async with async_client as client:
            start = await client.post("/api/execute", json={"purpose_text": "test"})
            eid = start.json()["execution_id"]
            resp = await client.post(f"/api/execute/{eid}/cancel")
        assert resp.status_code == 200

    @pytest.mark.anyio
    async def test_response_status_is_cancelled(self, hang_api_mgr, async_client):
        async with async_client as client:
            start = await client.post("/api/execute", json={"purpose_text": "test"})
            eid = start.json()["execution_id"]
            resp = await client.post(f"/api/execute/{eid}/cancel")
        assert resp.json()["status"] == "cancelled"

    @pytest.mark.anyio
    async def test_returns_404_for_unknown_id(self, mock_api_mgr, async_client):
        async with async_client as client:
            resp = await client.post("/api/execute/nonexistent/cancel")
        assert resp.status_code == 404

    @pytest.mark.anyio
    async def test_returns_400_when_execution_already_completed(self, mock_api_mgr, async_client):
        async with async_client as client:
            start = await client.post("/api/execute", json={"purpose_text": "test"})
            eid = start.json()["execution_id"]
            await asyncio.sleep(0)  # let fast task finish
            resp = await client.post(f"/api/execute/{eid}/cancel")
        assert resp.status_code == 400


# ── API: GET /api/execute/history ─────────────────────────────────────────────


class TestHistoryAPI:
    @pytest.mark.anyio
    async def test_returns_200_with_list(self, mock_api_mgr, async_client):
        async with async_client as client:
            resp = await client.get("/api/execute/history")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    @pytest.mark.anyio
    async def test_empty_before_any_execution(self, mock_api_mgr, async_client):
        async with async_client as client:
            resp = await client.get("/api/execute/history")
        assert resp.json() == []

    @pytest.mark.anyio
    async def test_contains_execution_after_start(self, mock_api_mgr, async_client):
        async with async_client as client:
            await client.post("/api/execute", json={"purpose_text": "test"})
            resp = await client.get("/api/execute/history")
        assert len(resp.json()) == 1
