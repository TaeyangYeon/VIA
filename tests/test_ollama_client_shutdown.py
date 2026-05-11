"""Tests for Step 48: OllamaClient graceful shutdown."""
from __future__ import annotations

import pytest
from unittest.mock import AsyncMock


@pytest.fixture(params=["asyncio"])
def anyio_backend(request):
    return request.param


class TestOllamaClientShutdown:
    @pytest.mark.anyio
    async def test_shutdown_sets_client_to_none(self):
        from backend.services.ollama_client import OllamaClient
        client = OllamaClient()
        client._get_client()  # force init
        assert client._client is not None
        await client.shutdown()
        assert client._client is None

    @pytest.mark.anyio
    async def test_shutdown_calls_aclose(self):
        from backend.services.ollama_client import OllamaClient
        client = OllamaClient()
        mock_http = AsyncMock()
        client._client = mock_http
        await client.shutdown()
        mock_http.aclose.assert_called_once()

    @pytest.mark.anyio
    async def test_shutdown_idempotent_when_no_client(self):
        from backend.services.ollama_client import OllamaClient
        client = OllamaClient()
        assert client._client is None
        await client.shutdown()  # must not raise
        await client.shutdown()  # still must not raise
        assert client._client is None

    @pytest.mark.anyio
    async def test_shutdown_idempotent_after_first_call(self):
        from backend.services.ollama_client import OllamaClient
        client = OllamaClient()
        client._get_client()
        await client.shutdown()
        await client.shutdown()  # second call must not raise
        assert client._client is None

    @pytest.mark.anyio
    async def test_client_reinitializes_after_shutdown(self):
        from backend.services.ollama_client import OllamaClient
        client = OllamaClient()
        client._get_client()
        await client.shutdown()
        assert client._client is None
        new_http = client._get_client()
        assert new_http is not None
        assert client._client is not None
        await client.shutdown()  # cleanup

    @pytest.mark.anyio
    async def test_shutdown_does_not_close_unowned_context_manager_client(self):
        """shutdown() should still set _client=None even for non-owned clients."""
        from backend.services.ollama_client import OllamaClient
        client = OllamaClient()
        mock_http = AsyncMock()
        client._client = mock_http
        client._owned = False
        await client.shutdown()
        assert client._client is None

    @pytest.mark.anyio
    async def test_module_level_shutdown_function_exists(self):
        from backend.services.ollama_client import shutdown_ollama_client
        assert callable(shutdown_ollama_client)

    @pytest.mark.anyio
    async def test_module_level_shutdown_function_is_callable(self):
        from backend.services.ollama_client import shutdown_ollama_client, ollama_client
        await shutdown_ollama_client()
        assert ollama_client._client is None
