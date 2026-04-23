"""Tests for Step 10: OllamaClient service."""

import asyncio
import base64
from unittest.mock import AsyncMock, Mock, patch

import httpx
import pytest

from backend.services.ollama_client import (
    OllamaClient,
    OllamaConnectionError,
    OllamaError,
    OllamaGenerationError,
    OllamaModelNotFoundError,
    ollama_client,
)


@pytest.fixture(params=["asyncio"])
def anyio_backend(request):
    return request.param


def make_response(status_code: int = 200, json_data: dict | None = None) -> Mock:
    resp = Mock()
    resp.status_code = status_code
    resp.json.return_value = json_data if json_data is not None else {}
    resp.raise_for_status = Mock()
    return resp


@pytest.fixture
def mock_http():
    """Patches httpx.AsyncClient so no real HTTP requests are made."""
    mock_instance = AsyncMock()
    with patch("backend.services.ollama_client.httpx.AsyncClient", return_value=mock_instance):
        yield mock_instance


# ---- Exception Hierarchy ----


class TestExceptionHierarchy:
    def test_ollama_error_is_exception(self):
        assert issubclass(OllamaError, Exception)

    def test_connection_error_inherits_ollama_error(self):
        assert issubclass(OllamaConnectionError, OllamaError)

    def test_model_not_found_inherits_ollama_error(self):
        assert issubclass(OllamaModelNotFoundError, OllamaError)

    def test_generation_error_inherits_ollama_error(self):
        assert issubclass(OllamaGenerationError, OllamaError)


# ---- Constructor Defaults ----


class TestConstructorDefaults:
    def test_default_base_url(self):
        client = OllamaClient()
        assert client.base_url == "http://localhost:11434"

    def test_default_model(self):
        client = OllamaClient()
        assert client.model == "gemma4:e4b"

    def test_default_health_timeout(self):
        client = OllamaClient()
        assert client.health_timeout == 30.0

    def test_default_generate_timeout(self):
        client = OllamaClient()
        assert client.generate_timeout == 600.0

    def test_default_max_retries(self):
        client = OllamaClient()
        assert client.max_retries == 2

    def test_custom_params(self):
        client = OllamaClient(
            base_url="http://custom:9999",
            model="custom_model",
            health_timeout=10.0,
            generate_timeout=120.0,
            max_retries=5,
        )
        assert client.base_url == "http://custom:9999"
        assert client.model == "custom_model"
        assert client.health_timeout == 10.0
        assert client.generate_timeout == 120.0
        assert client.max_retries == 5


# ---- check_health ----


class TestCheckHealth:
    @pytest.mark.anyio
    async def test_check_health_returns_true_when_model_found(self, mock_http):
        mock_http.get.return_value = make_response(200, {"models": [{"name": "gemma4:e4b"}]})
        client = OllamaClient()
        result = await client.check_health()
        assert result is True

    @pytest.mark.anyio
    async def test_check_health_raises_model_not_found_when_missing(self, mock_http):
        mock_http.get.return_value = make_response(200, {"models": [{"name": "other_model"}]})
        client = OllamaClient()
        with pytest.raises(OllamaModelNotFoundError):
            await client.check_health()

    @pytest.mark.anyio
    async def test_check_health_raises_connection_error(self, mock_http):
        mock_http.get.side_effect = httpx.ConnectError("refused")
        client = OllamaClient()
        with pytest.raises(OllamaConnectionError):
            await client.check_health()

    @pytest.mark.anyio
    async def test_check_health_uses_health_timeout(self, mock_http):
        mock_http.get.return_value = make_response(200, {"models": [{"name": "gemma4:e4b"}]})
        client = OllamaClient(health_timeout=15.0)
        await client.check_health()
        _, kwargs = mock_http.get.call_args
        assert kwargs.get("timeout") == 15.0

    @pytest.mark.anyio
    async def test_check_health_logs_on_success(self, mock_http):
        mock_http.get.return_value = make_response(200, {"models": [{"name": "gemma4:e4b"}]})
        with patch("backend.services.ollama_client.via_logger") as mock_logger:
            client = OllamaClient()
            await client.check_health()
        calls = mock_logger.log.call_args_list
        assert any(c.args[0] == "ollama_client" for c in calls)
        assert any(c.args[1] == "INFO" for c in calls)


# ---- generate ----


class TestGenerate:
    @pytest.mark.anyio
    async def test_generate_returns_response_text(self, mock_http):
        mock_http.post.return_value = make_response(200, {"response": "Hello world"})
        client = OllamaClient()
        result = await client.generate("Say hello")
        assert result == "Hello world"

    @pytest.mark.anyio
    async def test_generate_posts_to_generate_endpoint(self, mock_http):
        mock_http.post.return_value = make_response(200, {"response": "ok"})
        client = OllamaClient()
        await client.generate("test")
        url = mock_http.post.call_args.args[0]
        assert "api/generate" in url

    @pytest.mark.anyio
    async def test_generate_includes_system_prompt(self, mock_http):
        mock_http.post.return_value = make_response(200, {"response": "ok"})
        client = OllamaClient()
        await client.generate("test prompt", system="Be concise")
        payload = mock_http.post.call_args.kwargs.get("json", {})
        assert payload.get("system") == "Be concise"

    @pytest.mark.anyio
    async def test_generate_stream_is_false(self, mock_http):
        mock_http.post.return_value = make_response(200, {"response": "ok"})
        client = OllamaClient()
        await client.generate("test")
        payload = mock_http.post.call_args.kwargs.get("json", {})
        assert payload.get("stream") is False

    @pytest.mark.anyio
    async def test_generate_raises_error_on_empty_response(self, mock_http):
        mock_http.post.return_value = make_response(200, {"response": ""})
        client = OllamaClient(max_retries=0)
        with pytest.raises(OllamaGenerationError):
            await client.generate("test")

    @pytest.mark.anyio
    async def test_generate_raises_connection_error_after_retries(self, mock_http):
        mock_http.post.side_effect = httpx.ConnectError("refused")
        client = OllamaClient(max_retries=0)
        with pytest.raises(OllamaConnectionError):
            await client.generate("test")

    @pytest.mark.anyio
    async def test_generate_raises_error_on_non_200(self, mock_http):
        mock_http.post.return_value = make_response(500, {})
        client = OllamaClient(max_retries=0)
        with pytest.raises(OllamaGenerationError):
            await client.generate("test")

    @pytest.mark.anyio
    async def test_generate_logs_request(self, mock_http):
        mock_http.post.return_value = make_response(200, {"response": "ok"})
        with patch("backend.services.ollama_client.via_logger") as mock_logger:
            client = OllamaClient()
            await client.generate("test prompt")
        assert mock_logger.log.called
        calls = mock_logger.log.call_args_list
        assert any(c.args[0] == "ollama_client" for c in calls)


# ---- generate_with_images ----


class TestGenerateWithImages:
    @pytest.mark.anyio
    async def test_generate_with_images_passes_base64_in_payload(self, mock_http):
        mock_http.post.return_value = make_response(200, {"response": "I see an image"})
        b64_img = base64.b64encode(b"fake_image_bytes").decode()
        client = OllamaClient()
        result = await client.generate_with_images("What do you see?", [b64_img])
        assert result == "I see an image"
        payload = mock_http.post.call_args.kwargs.get("json", {})
        assert payload["images"] == [b64_img]

    @pytest.mark.anyio
    async def test_generate_with_images_multiple_images(self, mock_http):
        mock_http.post.return_value = make_response(200, {"response": "ok"})
        images = [base64.b64encode(b"img1").decode(), base64.b64encode(b"img2").decode()]
        client = OllamaClient()
        await client.generate_with_images("describe", images)
        payload = mock_http.post.call_args.kwargs.get("json", {})
        assert len(payload["images"]) == 2

    @pytest.mark.anyio
    async def test_generate_with_images_no_data_uri_prefix(self, mock_http):
        mock_http.post.return_value = make_response(200, {"response": "ok"})
        b64_img = base64.b64encode(b"raw_bytes").decode()
        client = OllamaClient()
        await client.generate_with_images("test", [b64_img])
        payload = mock_http.post.call_args.kwargs.get("json", {})
        assert not payload["images"][0].startswith("data:")


# ---- generate_with_image_paths ----


class TestGenerateWithImagePaths:
    @pytest.mark.anyio
    async def test_generate_with_image_paths_reads_and_base64_encodes(self, mock_http, tmp_path):
        image_bytes = b"\x89PNG\r\n\x1a\n" + b"\x00" * 20
        image_file = tmp_path / "test.png"
        image_file.write_bytes(image_bytes)
        mock_http.post.return_value = make_response(200, {"response": "image analyzed"})

        client = OllamaClient()
        result = await client.generate_with_image_paths("analyze", [str(image_file)])

        assert result == "image analyzed"
        payload = mock_http.post.call_args.kwargs.get("json", {})
        assert payload["images"] == [base64.b64encode(image_bytes).decode()]

    @pytest.mark.anyio
    async def test_generate_with_image_paths_file_not_found(self, mock_http):
        client = OllamaClient()
        with pytest.raises((FileNotFoundError, OSError)):
            await client.generate_with_image_paths("test", ["/nonexistent/path/image.png"])

    @pytest.mark.anyio
    async def test_generate_with_image_paths_multiple_files(self, mock_http, tmp_path):
        (tmp_path / "img1.png").write_bytes(b"img1data")
        (tmp_path / "img2.png").write_bytes(b"img2data")
        mock_http.post.return_value = make_response(200, {"response": "ok"})

        client = OllamaClient()
        await client.generate_with_image_paths(
            "describe", [str(tmp_path / "img1.png"), str(tmp_path / "img2.png")]
        )
        payload = mock_http.post.call_args.kwargs.get("json", {})
        assert len(payload["images"]) == 2


# ---- Retry Logic ----


class TestRetryLogic:
    @pytest.mark.anyio
    async def test_generate_retries_on_timeout_and_succeeds(self, mock_http):
        mock_http.post.side_effect = [
            httpx.TimeoutException("timeout"),
            make_response(200, {"response": "ok after retry"}),
        ]
        with patch("asyncio.sleep", new_callable=AsyncMock):
            client = OllamaClient(max_retries=2)
            result = await client.generate("test")
        assert result == "ok after retry"
        assert mock_http.post.call_count == 2

    @pytest.mark.anyio
    async def test_generate_exhausts_retries_and_raises(self, mock_http):
        mock_http.post.side_effect = httpx.TimeoutException("timeout")
        with patch("asyncio.sleep", new_callable=AsyncMock):
            client = OllamaClient(max_retries=2)
            with pytest.raises(OllamaError):
                await client.generate("test")
        assert mock_http.post.call_count == 3  # 1 initial + 2 retries

    @pytest.mark.anyio
    async def test_generate_retry_backoff_is_exponential(self, mock_http):
        mock_http.post.side_effect = [
            httpx.TimeoutException("t1"),
            httpx.TimeoutException("t2"),
            make_response(200, {"response": "ok"}),
        ]
        with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            client = OllamaClient(max_retries=2)
            await client.generate("test")
        assert mock_sleep.call_count == 2
        delays = [c.args[0] for c in mock_sleep.call_args_list]
        assert delays[1] >= delays[0]  # second delay >= first delay (exponential)

    @pytest.mark.anyio
    async def test_no_retry_when_max_retries_zero(self, mock_http):
        mock_http.post.side_effect = httpx.TimeoutException("timeout")
        with patch("asyncio.sleep", new_callable=AsyncMock):
            client = OllamaClient(max_retries=0)
            with pytest.raises(OllamaError):
                await client.generate("test")
        assert mock_http.post.call_count == 1


# ---- Logging Integration ----


class TestLoggingIntegration:
    @pytest.mark.anyio
    async def test_generate_logs_error_on_connection_failure(self, mock_http):
        mock_http.post.side_effect = httpx.ConnectError("refused")
        with patch("backend.services.ollama_client.via_logger") as mock_logger:
            client = OllamaClient(max_retries=0)
            with pytest.raises(OllamaConnectionError):
                await client.generate("test")
        error_calls = [c for c in mock_logger.log.call_args_list if c.args[1] == "ERROR"]
        assert len(error_calls) >= 1
        assert error_calls[0].args[0] == "ollama_client"

    @pytest.mark.anyio
    async def test_check_health_logs_error_on_connection_failure(self, mock_http):
        mock_http.get.side_effect = httpx.ConnectError("refused")
        with patch("backend.services.ollama_client.via_logger") as mock_logger:
            client = OllamaClient()
            with pytest.raises(OllamaConnectionError):
                await client.check_health()
        error_calls = [c for c in mock_logger.log.call_args_list if c.args[1] == "ERROR"]
        assert len(error_calls) >= 1
        assert error_calls[0].args[0] == "ollama_client"


# ---- Async Context Manager ----


class TestAsyncContextManager:
    @pytest.mark.anyio
    async def test_context_manager_returns_ollama_client(self, mock_http):
        async with OllamaClient() as client:
            assert isinstance(client, OllamaClient)

    @pytest.mark.anyio
    async def test_context_manager_closes_http_client_on_exit(self, mock_http):
        async with OllamaClient():
            pass
        assert mock_http.aclose.called


# ---- Module-level Singleton ----


class TestSingleton:
    def test_module_level_singleton_is_ollama_client_instance(self):
        assert isinstance(ollama_client, OllamaClient)
