"""Tests for Step 5: FastAPI project initialization and /health endpoint."""

import pytest
import httpx

from backend.main import app
from backend.config import VIAConfig


@pytest.fixture(params=["asyncio"])
def anyio_backend(request):
    return request.param


# --- App metadata tests ---


class TestAppMetadata:
    """Test FastAPI app instance configuration."""

    def test_app_title(self):
        assert app.title == "VIA API"

    def test_app_version(self):
        assert app.version == "0.1.0"


# --- Config tests ---


class TestVIAConfig:
    """Test VIAConfig default values."""

    def test_default_host(self):
        config = VIAConfig()
        assert config.host == "0.0.0.0"

    def test_default_port(self):
        config = VIAConfig()
        assert config.port == 8000

    def test_default_debug(self):
        config = VIAConfig()
        assert config.debug is True

    def test_default_cors_origins(self):
        config = VIAConfig()
        assert config.cors_origins == ["*"]

    def test_default_upload_dir(self):
        config = VIAConfig()
        assert config.upload_dir == "./uploads"

    def test_default_log_level(self):
        config = VIAConfig()
        assert config.log_level == "INFO"


# --- Health endpoint tests ---


@pytest.fixture
def async_client():
    """Create an async test client using ASGITransport."""
    transport = httpx.ASGITransport(app=app)
    return httpx.AsyncClient(transport=transport, base_url="http://testserver")


class TestHealthEndpoint:
    """Test GET /health endpoint."""

    @pytest.mark.anyio
    async def test_health_returns_200(self, async_client):
        async with async_client as client:
            response = await client.get("/health")
        assert response.status_code == 200

    @pytest.mark.anyio
    async def test_health_returns_correct_json(self, async_client):
        async with async_client as client:
            response = await client.get("/health")
        data = response.json()
        assert data == {"status": "ok", "version": "0.1.0"}

    @pytest.mark.anyio
    async def test_health_status_field(self, async_client):
        async with async_client as client:
            response = await client.get("/health")
        assert response.json()["status"] == "ok"

    @pytest.mark.anyio
    async def test_health_version_field(self, async_client):
        async with async_client as client:
            response = await client.get("/health")
        assert response.json()["version"] == "0.1.0"

    @pytest.mark.anyio
    async def test_health_content_type(self, async_client):
        async with async_client as client:
            response = await client.get("/health")
        assert response.headers["content-type"] == "application/json"


# --- CORS tests ---


class TestCORSMiddleware:
    """Test CORS middleware configuration."""

    @pytest.mark.anyio
    async def test_cors_allows_origin(self, async_client):
        async with async_client as client:
            response = await client.options(
                "/health",
                headers={
                    "Origin": "http://localhost:3000",
                    "Access-Control-Request-Method": "GET",
                },
            )
        assert response.headers.get("access-control-allow-origin") == "*"

    @pytest.mark.anyio
    async def test_cors_allows_methods(self, async_client):
        async with async_client as client:
            response = await client.options(
                "/health",
                headers={
                    "Origin": "http://localhost:3000",
                    "Access-Control-Request-Method": "GET",
                },
            )
        allowed = response.headers.get("access-control-allow-methods")
        assert "GET" in allowed


# --- 404 test ---


class TestUndefinedRoutes:
    """Test that undefined routes return 404."""

    @pytest.mark.anyio
    async def test_undefined_route_returns_404(self, async_client):
        async with async_client as client:
            response = await client.get("/nonexistent")
        assert response.status_code == 404
