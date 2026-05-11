"""Tests for Step 41: Engine Config API - OllamaClient URL management and engine routing."""

import pytest
import httpx
from unittest.mock import AsyncMock, Mock, patch

from backend.main import app
from backend.services.ollama_client import (
    OllamaClient,
    OllamaConnectionError,
    OllamaModelNotFoundError,
    ollama_client,
)
from backend.services.engine_config_store import EngineConfigStore, engine_config_store


@pytest.fixture(params=["asyncio"])
def anyio_backend(request):
    return request.param


@pytest.fixture
def async_client():
    transport = httpx.ASGITransport(app=app)
    return httpx.AsyncClient(transport=transport, base_url="http://testserver")


@pytest.fixture(autouse=True)
def reset_engine_state():
    engine_config_store.reset()
    yield
    engine_config_store.reset()


def _setup_http_mock(mock_cls, get_response=None, get_error=None):
    """Configure mock httpx.AsyncClient class for async context manager usage."""
    mock_http = AsyncMock()
    if get_error is not None:
        mock_http.get.side_effect = get_error
    else:
        mock_http.get.return_value = get_response
    mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_http)
    mock_cls.return_value.__aexit__ = AsyncMock(return_value=None)


def _ok_response():
    resp = Mock(status_code=200)
    resp.json.return_value = {"models": []}
    return resp


# ============================================================
# OllamaClient.get_base_url()
# ============================================================


class TestOllamaClientGetBaseUrl:
    def test_default_localhost(self):
        client = OllamaClient()
        assert client.get_base_url() == "http://localhost:11434"

    def test_reflects_constructor_value(self):
        client = OllamaClient(base_url="http://custom:9999")
        assert client.get_base_url() == "http://custom:9999"

    def test_singleton_returns_localhost(self):
        assert ollama_client.get_base_url() == "http://localhost:11434"


# ============================================================
# OllamaClient.set_base_url()
# ============================================================


class TestOllamaClientSetBaseUrl:
    @pytest.mark.anyio
    async def test_updates_base_url_attribute(self):
        client = OllamaClient()
        await client.set_base_url("http://colab:7860")
        assert client.base_url == "http://colab:7860"

    @pytest.mark.anyio
    async def test_get_base_url_reflects_new_url(self):
        client = OllamaClient()
        await client.set_base_url("http://new-host:1234")
        assert client.get_base_url() == "http://new-host:1234"

    @pytest.mark.anyio
    async def test_closes_existing_http_client(self):
        client = OllamaClient()
        existing = AsyncMock()
        client._client = existing
        await client.set_base_url("http://new:11434")
        existing.aclose.assert_called_once()

    @pytest.mark.anyio
    async def test_nullifies_client_for_lazy_recreation(self):
        client = OllamaClient()
        client._client = AsyncMock()
        await client.set_base_url("http://new:11434")
        assert client._client is None

    @pytest.mark.anyio
    async def test_no_error_when_no_existing_client(self):
        client = OllamaClient()
        assert client._client is None
        await client.set_base_url("http://new:11434")
        assert client.base_url == "http://new:11434"

    @pytest.mark.anyio
    async def test_chained_updates_work(self):
        client = OllamaClient()
        await client.set_base_url("http://first:1234")
        client._client = AsyncMock()
        await client.set_base_url("http://second:5678")
        assert client.base_url == "http://second:5678"


# ============================================================
# EngineConfigStore
# ============================================================


class TestEngineConfigStore:
    def test_default_engine_mode_is_local(self):
        store = EngineConfigStore()
        assert store.get()["engine_mode"] == "local"

    def test_default_colab_url_is_none(self):
        store = EngineConfigStore()
        assert store.get()["colab_url"] is None

    def test_save_updates_engine_mode(self):
        store = EngineConfigStore()
        store.save("colab", "http://colab.example.com")
        assert store.get()["engine_mode"] == "colab"

    def test_save_updates_colab_url(self):
        store = EngineConfigStore()
        store.save("colab", "http://colab.example.com")
        assert store.get()["colab_url"] == "http://colab.example.com"

    def test_save_local_mode_with_none_url(self):
        store = EngineConfigStore()
        store.save("local", None)
        data = store.get()
        assert data["engine_mode"] == "local"
        assert data["colab_url"] is None

    def test_reset_restores_local_mode(self):
        store = EngineConfigStore()
        store.save("colab", "http://colab.example.com")
        store.reset()
        assert store.get()["engine_mode"] == "local"

    def test_reset_clears_colab_url(self):
        store = EngineConfigStore()
        store.save("colab", "http://colab.example.com")
        store.reset()
        assert store.get()["colab_url"] is None

    def test_save_overwrites_previous_config(self):
        store = EngineConfigStore()
        store.save("colab", "http://colab1.com")
        store.save("local", None)
        data = store.get()
        assert data["engine_mode"] == "local"
        assert data["colab_url"] is None


# ============================================================
# POST /api/engine/config
# ============================================================


class TestPostEngineConfig:
    @pytest.mark.anyio
    async def test_local_mode_returns_200(self, async_client):
        with patch("backend.routers.engine.ollama_client") as mock_oc:
            mock_oc.set_base_url = AsyncMock()
            async with async_client as client:
                response = await client.post("/api/engine/config", json={"engine_mode": "local"})
        assert response.status_code == 200

    @pytest.mark.anyio
    async def test_local_mode_saves_to_store(self, async_client):
        with patch("backend.routers.engine.ollama_client") as mock_oc:
            mock_oc.set_base_url = AsyncMock()
            async with async_client as client:
                await client.post("/api/engine/config", json={"engine_mode": "local"})
        assert engine_config_store.get()["engine_mode"] == "local"

    @pytest.mark.anyio
    async def test_local_mode_response_has_engine_mode(self, async_client):
        with patch("backend.routers.engine.ollama_client") as mock_oc:
            mock_oc.set_base_url = AsyncMock()
            async with async_client as client:
                response = await client.post("/api/engine/config", json={"engine_mode": "local"})
        assert response.json()["engine_mode"] == "local"

    @pytest.mark.anyio
    async def test_local_mode_calls_set_base_url_localhost(self, async_client):
        with patch("backend.routers.engine.ollama_client") as mock_oc:
            mock_oc.set_base_url = AsyncMock()
            async with async_client as client:
                await client.post("/api/engine/config", json={"engine_mode": "local"})
            mock_oc.set_base_url.assert_called_once_with("http://localhost:11434")

    @pytest.mark.anyio
    async def test_colab_mode_with_url_returns_200(self, async_client):
        with patch("httpx.AsyncClient") as mock_cls, \
             patch("backend.routers.engine.ollama_client") as mock_oc:
            _setup_http_mock(mock_cls, get_response=_ok_response())
            mock_oc.set_base_url = AsyncMock()
            async with async_client as client:
                response = await client.post(
                    "/api/engine/config",
                    json={"engine_mode": "colab", "colab_url": "http://colab.example.com"},
                )
        assert response.status_code == 200

    @pytest.mark.anyio
    async def test_colab_mode_saves_engine_mode_and_url(self, async_client):
        with patch("httpx.AsyncClient") as mock_cls, \
             patch("backend.routers.engine.ollama_client") as mock_oc:
            _setup_http_mock(mock_cls, get_response=_ok_response())
            mock_oc.set_base_url = AsyncMock()
            async with async_client as client:
                await client.post(
                    "/api/engine/config",
                    json={"engine_mode": "colab", "colab_url": "http://colab.example.com"},
                )
        assert engine_config_store.get()["engine_mode"] == "colab"
        assert engine_config_store.get()["colab_url"] == "http://colab.example.com"

    @pytest.mark.anyio
    async def test_colab_mode_calls_set_base_url_with_colab_url(self, async_client):
        with patch("httpx.AsyncClient") as mock_cls, \
             patch("backend.routers.engine.ollama_client") as mock_oc:
            _setup_http_mock(mock_cls, get_response=_ok_response())
            mock_oc.set_base_url = AsyncMock()
            async with async_client as client:
                await client.post(
                    "/api/engine/config",
                    json={"engine_mode": "colab", "colab_url": "http://colab.example.com"},
                )
            mock_oc.set_base_url.assert_called_once_with("http://colab.example.com")

    @pytest.mark.anyio
    async def test_invalid_mode_returns_422(self, async_client):
        async with async_client as client:
            response = await client.post("/api/engine/config", json={"engine_mode": "invalid"})
        assert response.status_code == 422

    @pytest.mark.anyio
    async def test_colab_without_url_returns_422(self, async_client):
        async with async_client as client:
            response = await client.post("/api/engine/config", json={"engine_mode": "colab"})
        assert response.status_code == 422

    @pytest.mark.anyio
    async def test_colab_unreachable_url_still_returns_200(self, async_client):
        with patch("httpx.AsyncClient") as mock_cls, \
             patch("backend.routers.engine.ollama_client") as mock_oc:
            _setup_http_mock(mock_cls, get_error=httpx.ConnectError("refused"))
            mock_oc.set_base_url = AsyncMock()
            async with async_client as client:
                response = await client.post(
                    "/api/engine/config",
                    json={"engine_mode": "colab", "colab_url": "http://unreachable.host"},
                )
        assert response.status_code == 200

    @pytest.mark.anyio
    async def test_colab_unreachable_url_still_saves(self, async_client):
        with patch("httpx.AsyncClient") as mock_cls, \
             patch("backend.routers.engine.ollama_client") as mock_oc:
            _setup_http_mock(mock_cls, get_error=httpx.ConnectError("refused"))
            mock_oc.set_base_url = AsyncMock()
            async with async_client as client:
                await client.post(
                    "/api/engine/config",
                    json={"engine_mode": "colab", "colab_url": "http://unreachable.host"},
                )
        assert engine_config_store.get()["colab_url"] == "http://unreachable.host"

    @pytest.mark.anyio
    async def test_colab_unreachable_url_returns_warning(self, async_client):
        with patch("httpx.AsyncClient") as mock_cls, \
             patch("backend.routers.engine.ollama_client") as mock_oc:
            _setup_http_mock(mock_cls, get_error=httpx.ConnectError("refused"))
            mock_oc.set_base_url = AsyncMock()
            async with async_client as client:
                response = await client.post(
                    "/api/engine/config",
                    json={"engine_mode": "colab", "colab_url": "http://unreachable.host"},
                )
        data = response.json()
        assert data.get("warning") or data.get("warnings")

    @pytest.mark.anyio
    async def test_colab_reachable_url_no_warning(self, async_client):
        with patch("httpx.AsyncClient") as mock_cls, \
             patch("backend.routers.engine.ollama_client") as mock_oc:
            _setup_http_mock(mock_cls, get_response=_ok_response())
            mock_oc.set_base_url = AsyncMock()
            async with async_client as client:
                response = await client.post(
                    "/api/engine/config",
                    json={"engine_mode": "colab", "colab_url": "http://reachable.host"},
                )
        data = response.json()
        assert not data.get("warning")


# ============================================================
# GET /api/engine/status
# ============================================================


class TestGetEngineStatus:
    @pytest.mark.anyio
    async def test_returns_200(self, async_client):
        with patch("backend.routers.engine.ollama_client") as mock_oc:
            mock_oc.check_health = AsyncMock(return_value=True)
            mock_oc.get_base_url.return_value = "http://localhost:11434"
            async with async_client as client:
                response = await client.get("/api/engine/status")
        assert response.status_code == 200

    @pytest.mark.anyio
    async def test_has_engine_mode_field(self, async_client):
        with patch("backend.routers.engine.ollama_client") as mock_oc:
            mock_oc.check_health = AsyncMock(return_value=True)
            mock_oc.get_base_url.return_value = "http://localhost:11434"
            async with async_client as client:
                response = await client.get("/api/engine/status")
        assert "engine_mode" in response.json()

    @pytest.mark.anyio
    async def test_has_base_url_field(self, async_client):
        with patch("backend.routers.engine.ollama_client") as mock_oc:
            mock_oc.check_health = AsyncMock(return_value=True)
            mock_oc.get_base_url.return_value = "http://localhost:11434"
            async with async_client as client:
                response = await client.get("/api/engine/status")
        assert "base_url" in response.json()

    @pytest.mark.anyio
    async def test_has_connected_field(self, async_client):
        with patch("backend.routers.engine.ollama_client") as mock_oc:
            mock_oc.check_health = AsyncMock(return_value=True)
            mock_oc.get_base_url.return_value = "http://localhost:11434"
            async with async_client as client:
                response = await client.get("/api/engine/status")
        assert "connected" in response.json()

    @pytest.mark.anyio
    async def test_has_model_available_field(self, async_client):
        with patch("backend.routers.engine.ollama_client") as mock_oc:
            mock_oc.check_health = AsyncMock(return_value=True)
            mock_oc.get_base_url.return_value = "http://localhost:11434"
            async with async_client as client:
                response = await client.get("/api/engine/status")
        assert "model_available" in response.json()

    @pytest.mark.anyio
    async def test_connected_true_when_health_ok(self, async_client):
        with patch("backend.routers.engine.ollama_client") as mock_oc:
            mock_oc.check_health = AsyncMock(return_value=True)
            mock_oc.get_base_url.return_value = "http://localhost:11434"
            async with async_client as client:
                response = await client.get("/api/engine/status")
        assert response.json()["connected"] is True

    @pytest.mark.anyio
    async def test_model_available_true_when_health_ok(self, async_client):
        with patch("backend.routers.engine.ollama_client") as mock_oc:
            mock_oc.check_health = AsyncMock(return_value=True)
            mock_oc.get_base_url.return_value = "http://localhost:11434"
            async with async_client as client:
                response = await client.get("/api/engine/status")
        assert response.json()["model_available"] is True

    @pytest.mark.anyio
    async def test_connected_false_on_connection_error(self, async_client):
        with patch("backend.routers.engine.ollama_client") as mock_oc:
            mock_oc.check_health = AsyncMock(side_effect=OllamaConnectionError("refused"))
            mock_oc.get_base_url.return_value = "http://localhost:11434"
            async with async_client as client:
                response = await client.get("/api/engine/status")
        assert response.json()["connected"] is False

    @pytest.mark.anyio
    async def test_model_available_false_when_model_not_found(self, async_client):
        with patch("backend.routers.engine.ollama_client") as mock_oc:
            mock_oc.check_health = AsyncMock(side_effect=OllamaModelNotFoundError("missing"))
            mock_oc.get_base_url.return_value = "http://localhost:11434"
            async with async_client as client:
                response = await client.get("/api/engine/status")
        assert response.json()["model_available"] is False

    @pytest.mark.anyio
    async def test_connected_true_when_model_not_found(self, async_client):
        with patch("backend.routers.engine.ollama_client") as mock_oc:
            mock_oc.check_health = AsyncMock(side_effect=OllamaModelNotFoundError("missing"))
            mock_oc.get_base_url.return_value = "http://localhost:11434"
            async with async_client as client:
                response = await client.get("/api/engine/status")
        assert response.json()["connected"] is True

    @pytest.mark.anyio
    async def test_error_field_set_when_connection_fails(self, async_client):
        with patch("backend.routers.engine.ollama_client") as mock_oc:
            mock_oc.check_health = AsyncMock(side_effect=OllamaConnectionError("refused"))
            mock_oc.get_base_url.return_value = "http://localhost:11434"
            async with async_client as client:
                response = await client.get("/api/engine/status")
        assert response.json().get("error") is not None

    @pytest.mark.anyio
    async def test_default_engine_mode_is_local(self, async_client):
        with patch("backend.routers.engine.ollama_client") as mock_oc:
            mock_oc.check_health = AsyncMock(return_value=True)
            mock_oc.get_base_url.return_value = "http://localhost:11434"
            async with async_client as client:
                response = await client.get("/api/engine/status")
        assert response.json()["engine_mode"] == "local"

    @pytest.mark.anyio
    async def test_base_url_matches_ollama_client(self, async_client):
        with patch("backend.routers.engine.ollama_client") as mock_oc:
            mock_oc.check_health = AsyncMock(return_value=True)
            mock_oc.get_base_url.return_value = "http://colab:7860"
            async with async_client as client:
                response = await client.get("/api/engine/status")
        assert response.json()["base_url"] == "http://colab:7860"


# ============================================================
# Mode Switching Round-Trip
# ============================================================


class TestModeSwitching:
    @pytest.mark.anyio
    async def test_switch_local_to_colab_updates_store(self, async_client):
        with patch("httpx.AsyncClient") as mock_cls, \
             patch("backend.routers.engine.ollama_client") as mock_oc:
            _setup_http_mock(mock_cls, get_response=_ok_response())
            mock_oc.set_base_url = AsyncMock()
            async with async_client as client:
                await client.post("/api/engine/config", json={"engine_mode": "local"})
                await client.post(
                    "/api/engine/config",
                    json={"engine_mode": "colab", "colab_url": "http://colab.example.com"},
                )
        assert engine_config_store.get()["engine_mode"] == "colab"

    @pytest.mark.anyio
    async def test_switch_colab_to_local_resets_store(self, async_client):
        with patch("httpx.AsyncClient") as mock_cls, \
             patch("backend.routers.engine.ollama_client") as mock_oc:
            _setup_http_mock(mock_cls, get_response=_ok_response())
            mock_oc.set_base_url = AsyncMock()
            async with async_client as client:
                await client.post(
                    "/api/engine/config",
                    json={"engine_mode": "colab", "colab_url": "http://colab.example.com"},
                )
                await client.post("/api/engine/config", json={"engine_mode": "local"})
        assert engine_config_store.get()["engine_mode"] == "local"

    @pytest.mark.anyio
    async def test_round_trip_all_steps_return_200(self, async_client):
        with patch("httpx.AsyncClient") as mock_cls, \
             patch("backend.routers.engine.ollama_client") as mock_oc:
            _setup_http_mock(mock_cls, get_response=_ok_response())
            mock_oc.set_base_url = AsyncMock()
            async with async_client as client:
                r1 = await client.post("/api/engine/config", json={"engine_mode": "local"})
                r2 = await client.post(
                    "/api/engine/config",
                    json={"engine_mode": "colab", "colab_url": "http://colab.example.com"},
                )
                r3 = await client.post("/api/engine/config", json={"engine_mode": "local"})
        assert r1.status_code == 200
        assert r2.status_code == 200
        assert r3.status_code == 200

    @pytest.mark.anyio
    async def test_set_base_url_called_three_times_in_round_trip(self, async_client):
        with patch("httpx.AsyncClient") as mock_cls, \
             patch("backend.routers.engine.ollama_client") as mock_oc:
            _setup_http_mock(mock_cls, get_response=_ok_response())
            mock_oc.set_base_url = AsyncMock()
            async with async_client as client:
                await client.post("/api/engine/config", json={"engine_mode": "local"})
                await client.post(
                    "/api/engine/config",
                    json={"engine_mode": "colab", "colab_url": "http://colab.example.com"},
                )
                await client.post("/api/engine/config", json={"engine_mode": "local"})
            assert mock_oc.set_base_url.call_count == 3


# ============================================================
# Backward Compatibility
# ============================================================


class TestBackwardCompatibility:
    def test_singleton_is_ollamaclient_instance(self):
        assert isinstance(ollama_client, OllamaClient)

    def test_singleton_has_get_base_url(self):
        assert callable(getattr(ollama_client, "get_base_url", None))

    def test_singleton_has_set_base_url(self):
        assert callable(getattr(ollama_client, "set_base_url", None))

    def test_singleton_default_url_is_localhost(self):
        assert ollama_client.get_base_url() == "http://localhost:11434"

    def test_singleton_model_is_gemma4(self):
        assert ollama_client.model == "gemma4:e4b"
