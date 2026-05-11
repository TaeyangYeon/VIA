"""
Step 3: Ollama + gemma4:e4b multimodal integration tests.

These tests require a running Ollama server with gemma4:e4b model pulled.
All tests are marked with @pytest.mark.integration and will be skipped
if Ollama is not available.
"""

import base64
import pytest
import httpx
import numpy as np
import cv2

OLLAMA_BASE_URL = "http://localhost:11434"
MODEL_NAME = "gemma4:e4b"
HEALTH_TIMEOUT = 300.0
GENERATE_TIMEOUT = 600.0


def is_ollama_running() -> bool:
    """Check if Ollama server is reachable."""
    try:
        resp = httpx.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=HEALTH_TIMEOUT)
        return resp.status_code == 200
    except (httpx.ConnectError, httpx.TimeoutException):
        return False


def is_model_available() -> bool:
    """Check if gemma4:e4b is available in Ollama."""
    try:
        resp = httpx.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=HEALTH_TIMEOUT)
        if resp.status_code != 200:
            return False
        models = resp.json().get("models", [])
        return any(m["name"].startswith(MODEL_NAME) for m in models)
    except (httpx.ConnectError, httpx.TimeoutException):
        return False


skip_no_ollama = pytest.mark.skipif(
    not is_ollama_running(),
    reason="Ollama server is not running at localhost:11434",
)

skip_no_model = pytest.mark.skipif(
    not is_model_available(),
    reason=f"{MODEL_NAME} model is not available in Ollama",
)


def create_test_image_base64() -> str:
    """Create a simple 100x100 test image with colored rectangles, return as base64."""
    img = np.zeros((100, 100, 3), dtype=np.uint8)
    # Red rectangle top-left
    cv2.rectangle(img, (10, 10), (40, 40), (0, 0, 255), -1)
    # Green rectangle bottom-right
    cv2.rectangle(img, (60, 60), (90, 90), (0, 255, 0), -1)
    # Blue circle center
    cv2.circle(img, (50, 50), 15, (255, 0, 0), -1)

    _, buffer = cv2.imencode(".png", img)
    return base64.b64encode(buffer).decode("utf-8")


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.integration
@skip_no_ollama
class TestOllamaServerHealth:
    """Test that the Ollama server is reachable and responding."""

    def test_server_reachable(self):
        """GET /api/tags should return 200."""
        resp = httpx.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=HEALTH_TIMEOUT)
        assert resp.status_code == 200

    def test_server_returns_json(self):
        """GET /api/tags should return valid JSON with 'models' key."""
        resp = httpx.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=HEALTH_TIMEOUT)
        data = resp.json()
        assert "models" in data
        assert isinstance(data["models"], list)


@pytest.mark.integration
@skip_no_ollama
@skip_no_model
class TestGemma3ModelAvailability:
    """Test that gemma4:e4b is pulled and available."""

    def test_model_in_list(self):
        """gemma4:e4b should appear in the model list."""
        resp = httpx.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=HEALTH_TIMEOUT)
        models = resp.json()["models"]
        model_names = [m["name"] for m in models]
        assert any(name.startswith(MODEL_NAME) for name in model_names), (
            f"{MODEL_NAME} not found in models: {model_names}"
        )

    def test_model_has_size(self):
        """The pulled model should have a non-zero size."""
        resp = httpx.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=HEALTH_TIMEOUT)
        models = resp.json()["models"]
        target = next(m for m in models if m["name"].startswith(MODEL_NAME))
        assert target.get("size", 0) > 0


@pytest.mark.integration
@skip_no_ollama
@skip_no_model
class TestTextGeneration:
    """Test text-only generation with gemma4:e4b."""

    def test_text_generation_returns_response(self):
        """POST /api/generate with a simple prompt should return text."""
        payload = {
            "model": MODEL_NAME,
            "prompt": "Say hello in one sentence.",
            "stream": False,
        }
        resp = httpx.post(
            f"{OLLAMA_BASE_URL}/api/generate",
            json=payload,
            timeout=GENERATE_TIMEOUT,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "response" in data
        assert len(data["response"].strip()) > 0

    def test_text_generation_done_flag(self):
        """Generation response should have done=True when stream=False."""
        payload = {
            "model": MODEL_NAME,
            "prompt": "Reply with OK.",
            "stream": False,
        }
        resp = httpx.post(
            f"{OLLAMA_BASE_URL}/api/generate",
            json=payload,
            timeout=GENERATE_TIMEOUT,
        )
        data = resp.json()
        assert data.get("done") is True


@pytest.mark.integration
@skip_no_ollama
@skip_no_model
class TestMultimodalGeneration:
    """Test multimodal (image + text) generation with gemma4:e4b."""

    def test_multimodal_returns_response(self):
        """POST /api/generate with image should return a non-empty text response."""
        image_b64 = create_test_image_base64()
        payload = {
            "model": MODEL_NAME,
            "prompt": "Describe this image briefly.",
            "images": [image_b64],
            "stream": False,
        }
        resp = httpx.post(
            f"{OLLAMA_BASE_URL}/api/generate",
            json=payload,
            timeout=GENERATE_TIMEOUT,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "response" in data
        assert len(data["response"].strip()) > 0

    def test_multimodal_mentions_visual_content(self):
        """The model response should reference something visual (color, shape, etc.)."""
        image_b64 = create_test_image_base64()
        payload = {
            "model": MODEL_NAME,
            "prompt": "What colors and shapes do you see in this image? List them.",
            "images": [image_b64],
            "stream": False,
        }
        resp = httpx.post(
            f"{OLLAMA_BASE_URL}/api/generate",
            json=payload,
            timeout=GENERATE_TIMEOUT,
        )
        data = resp.json()
        response_text = data["response"].lower()
        # The model should mention at least one visual element
        visual_keywords = [
            "red", "green", "blue", "color", "rectangle", "square",
            "circle", "shape", "black", "background", "image",
        ]
        assert any(kw in response_text for kw in visual_keywords), (
            f"Response does not mention any visual content: {data['response'][:200]}"
        )

    def test_multimodal_done_flag(self):
        """Multimodal generation should complete with done=True."""
        image_b64 = create_test_image_base64()
        payload = {
            "model": MODEL_NAME,
            "prompt": "What is in this image?",
            "images": [image_b64],
            "stream": False,
        }
        resp = httpx.post(
            f"{OLLAMA_BASE_URL}/api/generate",
            json=payload,
            timeout=GENERATE_TIMEOUT,
        )
        data = resp.json()
        assert data.get("done") is True
