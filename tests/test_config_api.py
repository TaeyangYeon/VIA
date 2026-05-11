"""Tests for Step 8: Execution Config API."""

import pytest
import httpx

from backend.main import app
from backend.services.config_store import config_store


@pytest.fixture(params=["asyncio"])
def anyio_backend(request):
    return request.param


@pytest.fixture
def async_client():
    transport = httpx.ASGITransport(app=app)
    return httpx.AsyncClient(transport=transport, base_url="http://testserver")


@pytest.fixture(autouse=True)
def reset_config():
    config_store.clear()
    yield
    config_store.clear()


# ---- ConfigStore Unit Tests ----


class TestConfigStoreSave:
    def test_save_and_get_returns_config(self):
        config_store.save({"mode": "inspection", "max_iteration": 5})
        result = config_store.get()
        assert result is not None
        assert result["mode"] == "inspection"

    def test_get_returns_none_when_empty(self):
        assert config_store.get() is None

    def test_clear_resets_to_none(self):
        config_store.save({"mode": "align", "max_iteration": 3})
        config_store.clear()
        assert config_store.get() is None

    def test_save_overwrites_previous(self):
        config_store.save({"mode": "inspection", "max_iteration": 5})
        config_store.save({"mode": "align", "max_iteration": 10})
        result = config_store.get()
        assert result["mode"] == "align"
        assert result["max_iteration"] == 10


# ---- POST /api/config ----


class TestPostConfig:
    @pytest.mark.anyio
    async def test_post_inspection_config_returns_200(self, async_client):
        payload = {
            "mode": "inspection",
            "max_iteration": 5,
            "success_criteria": {
                "accuracy": 0.95,
                "fp_rate": 0.05,
                "fn_rate": 0.05,
            },
        }
        async with async_client as client:
            response = await client.post("/api/config", json=payload)
        assert response.status_code == 200

    @pytest.mark.anyio
    async def test_post_align_config_returns_200(self, async_client):
        payload = {
            "mode": "align",
            "max_iteration": 3,
            "success_criteria": {
                "coord_error": 2.0,
                "success_rate": 0.95,
            },
        }
        async with async_client as client:
            response = await client.post("/api/config", json=payload)
        assert response.status_code == 200

    @pytest.mark.anyio
    async def test_post_config_saves_to_store(self, async_client):
        payload = {
            "mode": "inspection",
            "max_iteration": 5,
            "success_criteria": {"accuracy": 0.9, "fp_rate": 0.1, "fn_rate": 0.1},
        }
        async with async_client as client:
            await client.post("/api/config", json=payload)
        assert config_store.get() is not None
        assert config_store.get()["mode"] == "inspection"

    @pytest.mark.anyio
    async def test_post_config_response_includes_saved_config(self, async_client):
        payload = {
            "mode": "inspection",
            "max_iteration": 7,
            "success_criteria": {"accuracy": 0.9, "fp_rate": 0.1, "fn_rate": 0.1},
        }
        async with async_client as client:
            response = await client.post("/api/config", json=payload)
        data = response.json()
        assert data["mode"] == "inspection"
        assert data["max_iteration"] == 7

    @pytest.mark.anyio
    async def test_post_config_default_max_iteration(self, async_client):
        payload = {
            "mode": "inspection",
            "success_criteria": {"accuracy": 0.9, "fp_rate": 0.1, "fn_rate": 0.1},
        }
        async with async_client as client:
            response = await client.post("/api/config", json=payload)
        assert response.status_code == 200
        assert response.json()["max_iteration"] == 5

    @pytest.mark.anyio
    async def test_post_config_invalid_mode_returns_422(self, async_client):
        payload = {
            "mode": "invalid_mode",
            "max_iteration": 5,
            "success_criteria": {"accuracy": 0.9, "fp_rate": 0.1, "fn_rate": 0.1},
        }
        async with async_client as client:
            response = await client.post("/api/config", json=payload)
        assert response.status_code == 422

    @pytest.mark.anyio
    async def test_post_config_max_iteration_below_range_returns_422(self, async_client):
        payload = {
            "mode": "inspection",
            "max_iteration": 0,
            "success_criteria": {"accuracy": 0.9, "fp_rate": 0.1, "fn_rate": 0.1},
        }
        async with async_client as client:
            response = await client.post("/api/config", json=payload)
        assert response.status_code == 422

    @pytest.mark.anyio
    async def test_post_config_max_iteration_above_range_returns_422(self, async_client):
        payload = {
            "mode": "inspection",
            "max_iteration": 21,
            "success_criteria": {"accuracy": 0.9, "fp_rate": 0.1, "fn_rate": 0.1},
        }
        async with async_client as client:
            response = await client.post("/api/config", json=payload)
        assert response.status_code == 422

    @pytest.mark.anyio
    async def test_post_config_accuracy_out_of_range_returns_422(self, async_client):
        payload = {
            "mode": "inspection",
            "max_iteration": 5,
            "success_criteria": {"accuracy": 1.5, "fp_rate": 0.1, "fn_rate": 0.1},
        }
        async with async_client as client:
            response = await client.post("/api/config", json=payload)
        assert response.status_code == 422

    @pytest.mark.anyio
    async def test_post_missing_mode_returns_422(self, async_client):
        payload = {
            "max_iteration": 5,
            "success_criteria": {"accuracy": 0.9, "fp_rate": 0.1, "fn_rate": 0.1},
        }
        async with async_client as client:
            response = await client.post("/api/config", json=payload)
        assert response.status_code == 422


# ---- GET /api/config ----


class TestGetConfig:
    @pytest.mark.anyio
    async def test_get_config_when_none_returns_404(self, async_client):
        async with async_client as client:
            response = await client.get("/api/config")
        assert response.status_code == 404

    @pytest.mark.anyio
    async def test_get_config_returns_saved_config(self, async_client):
        payload = {
            "mode": "align",
            "max_iteration": 3,
            "success_criteria": {"coord_error": 1.5, "success_rate": 0.9},
        }
        async with async_client as client:
            await client.post("/api/config", json=payload)
            response = await client.get("/api/config")
        assert response.status_code == 200
        data = response.json()
        assert data["mode"] == "align"
        assert data["max_iteration"] == 3


# ---- Extreme Goal Warning Logic ----


class TestExtremeGoalWarnings:
    @pytest.mark.anyio
    async def test_accuracy_above_0_99_triggers_warning(self, async_client):
        payload = {
            "mode": "inspection",
            "max_iteration": 5,
            "success_criteria": {"accuracy": 0.999, "fp_rate": 0.05, "fn_rate": 0.05},
        }
        async with async_client as client:
            response = await client.post("/api/config", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert "warnings" in data
        assert any("99%" in w for w in data["warnings"])

    @pytest.mark.anyio
    async def test_fp_rate_below_0_001_triggers_warning(self, async_client):
        payload = {
            "mode": "inspection",
            "max_iteration": 5,
            "success_criteria": {"accuracy": 0.9, "fp_rate": 0.0001, "fn_rate": 0.05},
        }
        async with async_client as client:
            response = await client.post("/api/config", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert "warnings" in data
        assert any("false positive" in w.lower() for w in data["warnings"])

    @pytest.mark.anyio
    async def test_fn_rate_below_0_001_triggers_warning(self, async_client):
        payload = {
            "mode": "inspection",
            "max_iteration": 5,
            "success_criteria": {"accuracy": 0.9, "fp_rate": 0.05, "fn_rate": 0.0001},
        }
        async with async_client as client:
            response = await client.post("/api/config", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert "warnings" in data
        assert any("false negative" in w.lower() for w in data["warnings"])

    @pytest.mark.anyio
    async def test_coord_error_below_0_5_triggers_warning(self, async_client):
        payload = {
            "mode": "align",
            "max_iteration": 5,
            "success_criteria": {"coord_error": 0.3, "success_rate": 0.9},
        }
        async with async_client as client:
            response = await client.post("/api/config", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert "warnings" in data
        assert any("sub-pixel" in w.lower() or "pixel" in w.lower() for w in data["warnings"])

    @pytest.mark.anyio
    async def test_no_warnings_for_normal_targets(self, async_client):
        payload = {
            "mode": "inspection",
            "max_iteration": 5,
            "success_criteria": {"accuracy": 0.95, "fp_rate": 0.05, "fn_rate": 0.05},
        }
        async with async_client as client:
            response = await client.post("/api/config", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data.get("warnings", []) == []

    @pytest.mark.anyio
    async def test_extreme_config_still_saved_despite_warnings(self, async_client):
        payload = {
            "mode": "inspection",
            "max_iteration": 5,
            "success_criteria": {"accuracy": 0.999, "fp_rate": 0.05, "fn_rate": 0.05},
        }
        async with async_client as client:
            await client.post("/api/config", json=payload)
        saved = config_store.get()
        assert saved is not None
        assert saved["success_criteria"]["accuracy"] == 0.999

    @pytest.mark.anyio
    async def test_multiple_warnings_returned_together(self, async_client):
        payload = {
            "mode": "inspection",
            "max_iteration": 5,
            "success_criteria": {"accuracy": 0.999, "fp_rate": 0.0001, "fn_rate": 0.0001},
        }
        async with async_client as client:
            response = await client.post("/api/config", json=payload)
        data = response.json()
        assert len(data["warnings"]) >= 3
