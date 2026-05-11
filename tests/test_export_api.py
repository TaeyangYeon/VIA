"""Tests for Step 48: Export API endpoints."""
from __future__ import annotations

from unittest.mock import Mock

import httpx
import pytest

from backend.main import app
from backend.services.execution_manager import ExecutionManager, ExecutionState


@pytest.fixture(params=["asyncio"])
def anyio_backend(request):
    return request.param


@pytest.fixture(autouse=True)
def clear_overrides():
    yield
    app.dependency_overrides.clear()


@pytest.fixture
def async_client():
    transport = httpx.ASGITransport(app=app)
    return httpx.AsyncClient(transport=transport, base_url="http://testserver")


def _success_state(code: str = "import cv2\ndef run(img):\n    return img") -> ExecutionState:
    algo = Mock()
    algo.code = code
    algo.explanation = "Algorithm explanation"
    return ExecutionState(
        execution_id="exec-123",
        status="success",
        current_agent="",
        current_iteration=1,
        result={
            "algorithm_result": algo,
            "best_pipeline": None,
            "inspection_plan": None,
            "evaluation_result": Mock(overall_passed=True, analysis="OK", failed_items=[]),
            "decision_result": None,
            "test_results": [],
            "warnings": [],
            "iteration_history": [],
        },
        error=None,
        started_at="2026-05-08T00:00:00+00:00",
        completed_at="2026-05-08T00:01:00+00:00",
    )


def _failed_state() -> ExecutionState:
    return ExecutionState(
        execution_id="exec-456",
        status="failed",
        current_agent="",
        current_iteration=1,
        result=None,
        error="something failed",
        started_at="2026-05-08T00:00:00+00:00",
        completed_at="2026-05-08T00:01:00+00:00",
    )


def _set_manager(history: list[ExecutionState]) -> None:
    from backend.routers.export import get_manager
    mock_mgr = Mock(spec=ExecutionManager)
    mock_mgr.get_history.return_value = history
    app.dependency_overrides[get_manager] = lambda: mock_mgr


# ── GET /api/export/code ───────────────────────────────────────


@pytest.mark.anyio
async def test_export_code_404_when_no_executions(async_client):
    _set_manager([])
    res = await async_client.get("/api/export/code")
    assert res.status_code == 404


@pytest.mark.anyio
async def test_export_code_404_when_only_failed(async_client):
    _set_manager([_failed_state()])
    res = await async_client.get("/api/export/code")
    assert res.status_code == 404


@pytest.mark.anyio
async def test_export_code_200_on_success(async_client):
    _set_manager([_success_state()])
    res = await async_client.get("/api/export/code")
    assert res.status_code == 200


@pytest.mark.anyio
async def test_export_code_content_type_python(async_client):
    _set_manager([_success_state()])
    res = await async_client.get("/api/export/code")
    assert "text/x-python" in res.headers["content-type"]


@pytest.mark.anyio
async def test_export_code_content_disposition_attachment(async_client):
    _set_manager([_success_state()])
    res = await async_client.get("/api/export/code")
    cd = res.headers["content-disposition"]
    assert "attachment" in cd
    assert "via_algorithm.py" in cd


@pytest.mark.anyio
async def test_export_code_body_is_algorithm_code(async_client):
    code = "import cv2\ndef detect(img):\n    return img"
    _set_manager([_success_state(code=code)])
    res = await async_client.get("/api/export/code")
    assert "import cv2" in res.text
    assert "detect" in res.text


@pytest.mark.anyio
async def test_export_code_skips_failed_takes_success(async_client):
    """Failed execution in history should be skipped; success should be served."""
    _set_manager([_success_state(), _failed_state()])
    res = await async_client.get("/api/export/code")
    assert res.status_code == 200


# ── GET /api/export/result ─────────────────────────────────────


@pytest.mark.anyio
async def test_export_result_404_when_no_executions(async_client):
    _set_manager([])
    res = await async_client.get("/api/export/result")
    assert res.status_code == 404


@pytest.mark.anyio
async def test_export_result_404_when_only_failed(async_client):
    _set_manager([_failed_state()])
    res = await async_client.get("/api/export/result")
    assert res.status_code == 404


@pytest.mark.anyio
async def test_export_result_200_on_success(async_client):
    _set_manager([_success_state()])
    res = await async_client.get("/api/export/result")
    assert res.status_code == 200


@pytest.mark.anyio
async def test_export_result_content_type_json(async_client):
    _set_manager([_success_state()])
    res = await async_client.get("/api/export/result")
    assert "application/json" in res.headers["content-type"]


@pytest.mark.anyio
async def test_export_result_content_disposition_attachment(async_client):
    _set_manager([_success_state()])
    res = await async_client.get("/api/export/result")
    cd = res.headers["content-disposition"]
    assert "attachment" in cd
    assert "via_result.json" in cd


@pytest.mark.anyio
async def test_export_result_body_is_valid_json_dict(async_client):
    _set_manager([_success_state()])
    res = await async_client.get("/api/export/result")
    data = res.json()
    assert isinstance(data, dict)


@pytest.mark.anyio
async def test_export_result_includes_algorithm_code(async_client):
    code = "import cv2\ndef run(img):\n    return img"
    _set_manager([_success_state(code=code)])
    res = await async_client.get("/api/export/result")
    data = res.json()
    assert "algorithm_code" in data
    assert "import cv2" in data["algorithm_code"]


@pytest.mark.anyio
async def test_export_result_includes_algorithm_explanation(async_client):
    _set_manager([_success_state()])
    res = await async_client.get("/api/export/result")
    data = res.json()
    assert "algorithm_explanation" in data
