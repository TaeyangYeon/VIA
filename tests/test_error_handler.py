"""Tests for Step 48: VIA Error Handler Service."""
from __future__ import annotations

import pytest
import httpx
from fastapi import FastAPI


@pytest.fixture(params=["asyncio"])
def anyio_backend(request):
    return request.param


# ── VIAError base class ────────────────────────────────────────


class TestVIAErrorBase:
    def test_is_exception(self):
        from backend.services.error_handler import VIAError
        assert isinstance(VIAError("oops"), Exception)

    def test_message_accessible(self):
        from backend.services.error_handler import VIAError
        assert str(VIAError("oops")) == "oops"

    def test_agent_name_stored(self):
        from backend.services.error_handler import VIAError
        err = VIAError("msg", agent_name="spec_agent")
        assert err.agent_name == "spec_agent"

    def test_error_code_stored(self):
        from backend.services.error_handler import VIAError
        err = VIAError("msg", error_code="SPEC_FAIL")
        assert err.error_code == "SPEC_FAIL"

    def test_user_message_stored(self):
        from backend.services.error_handler import VIAError
        err = VIAError("msg", user_message="Friendly")
        assert err.user_message == "Friendly"

    def test_all_fields_default_none(self):
        from backend.services.error_handler import VIAError
        err = VIAError("msg")
        assert err.agent_name is None
        assert err.error_code is None
        assert err.user_message is None


# ── Subclasses ─────────────────────────────────────────────────


class TestErrorSubclasses:
    def test_agent_execution_error_is_via_error(self):
        from backend.services.error_handler import AgentExecutionError, VIAError
        assert isinstance(AgentExecutionError("fail", agent_name="a", error_code="E"), VIAError)

    def test_ollama_connection_error_is_via_error(self):
        from backend.services.error_handler import OllamaConnectionError, VIAError
        assert isinstance(OllamaConnectionError("fail"), VIAError)

    def test_image_processing_error_is_via_error(self):
        from backend.services.error_handler import ImageProcessingError, VIAError
        assert isinstance(ImageProcessingError("fail"), VIAError)

    def test_configuration_error_is_via_error(self):
        from backend.services.error_handler import ConfigurationError, VIAError
        assert isinstance(ConfigurationError("fail"), VIAError)

    def test_export_error_is_via_error(self):
        from backend.services.error_handler import ExportError, VIAError
        assert isinstance(ExportError("fail"), VIAError)

    def test_agent_execution_error_preserves_agent_name(self):
        from backend.services.error_handler import AgentExecutionError
        err = AgentExecutionError("fail", agent_name="pipeline_composer")
        assert err.agent_name == "pipeline_composer"


# ── format_error_response ──────────────────────────────────────


class TestFormatErrorResponse:
    def test_returns_dict(self):
        from backend.services.error_handler import VIAError, format_error_response
        assert isinstance(format_error_response(VIAError("fail")), dict)

    def test_has_all_required_keys(self):
        from backend.services.error_handler import VIAError, format_error_response
        resp = format_error_response(VIAError("fail"))
        for key in ("error_code", "agent", "message", "details", "timestamp"):
            assert key in resp

    def test_error_code_propagated(self):
        from backend.services.error_handler import VIAError, format_error_response
        resp = format_error_response(VIAError("fail", error_code="MY_CODE"))
        assert resp["error_code"] == "MY_CODE"

    def test_agent_name_propagated(self):
        from backend.services.error_handler import VIAError, format_error_response
        resp = format_error_response(VIAError("fail", agent_name="spec_agent"))
        assert resp["agent"] == "spec_agent"

    def test_user_message_preferred_over_str(self):
        from backend.services.error_handler import VIAError, format_error_response
        resp = format_error_response(VIAError("internal", user_message="Friendly"))
        assert resp["message"] == "Friendly"

    def test_falls_back_to_str_without_user_message(self):
        from backend.services.error_handler import VIAError, format_error_response
        resp = format_error_response(VIAError("internal msg"))
        assert resp["message"] == "internal msg"

    def test_timestamp_is_nonempty_string(self):
        from backend.services.error_handler import VIAError, format_error_response
        resp = format_error_response(VIAError("fail"))
        assert isinstance(resp["timestamp"], str)
        assert len(resp["timestamp"]) > 10


# ── FastAPI exception handler ──────────────────────────────────


def _build_test_app() -> FastAPI:
    from backend.services.error_handler import (
        VIAError,
        AgentExecutionError,
        OllamaConnectionError,
        ImageProcessingError,
        ConfigurationError,
        register_error_handlers,
    )

    test_app = FastAPI()
    register_error_handlers(test_app)

    @test_app.get("/raise-via")
    async def raise_via():
        raise VIAError("generic error", error_code="VIA_ERR")

    @test_app.get("/raise-agent")
    async def raise_agent():
        raise AgentExecutionError("agent error", agent_name="spec", error_code="AGENT_ERR")

    @test_app.get("/raise-ollama")
    async def raise_ollama():
        raise OllamaConnectionError("offline", error_code="OLLAMA_DOWN")

    @test_app.get("/raise-image")
    async def raise_image():
        raise ImageProcessingError("bad image", error_code="IMG_ERR")

    @test_app.get("/raise-config")
    async def raise_config():
        raise ConfigurationError("bad config", error_code="CFG_ERR")

    return test_app


@pytest.mark.anyio
async def test_via_error_returns_500():
    transport = httpx.ASGITransport(app=_build_test_app())
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        res = await c.get("/raise-via")
    assert res.status_code == 500


@pytest.mark.anyio
async def test_agent_execution_error_returns_500():
    transport = httpx.ASGITransport(app=_build_test_app())
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        res = await c.get("/raise-agent")
    assert res.status_code == 500


@pytest.mark.anyio
async def test_ollama_connection_error_returns_503():
    transport = httpx.ASGITransport(app=_build_test_app())
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        res = await c.get("/raise-ollama")
    assert res.status_code == 503


@pytest.mark.anyio
async def test_image_processing_error_returns_400():
    transport = httpx.ASGITransport(app=_build_test_app())
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        res = await c.get("/raise-image")
    assert res.status_code == 400


@pytest.mark.anyio
async def test_configuration_error_returns_400():
    transport = httpx.ASGITransport(app=_build_test_app())
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        res = await c.get("/raise-config")
    assert res.status_code == 400


@pytest.mark.anyio
async def test_error_response_body_has_error_code():
    transport = httpx.ASGITransport(app=_build_test_app())
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        res = await c.get("/raise-via")
    assert res.json()["error_code"] == "VIA_ERR"


@pytest.mark.anyio
async def test_error_response_body_has_timestamp():
    transport = httpx.ASGITransport(app=_build_test_app())
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        res = await c.get("/raise-via")
    body = res.json()
    assert "timestamp" in body
    assert isinstance(body["timestamp"], str)
