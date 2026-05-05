"""Ollama API client with multimodal support."""

import asyncio
import base64

import httpx

from backend.services.logger import via_logger


class OllamaError(Exception):
    """Base exception for all Ollama client errors."""


class OllamaConnectionError(OllamaError):
    """Ollama server is unreachable."""


class OllamaModelNotFoundError(OllamaError):
    """Requested model not found in Ollama."""


class OllamaGenerationError(OllamaError):
    """Text or image generation failed."""


class OllamaClient:
    def __init__(
        self,
        base_url: str = "http://localhost:11434",
        model: str = "gemma4:e4b",
        health_timeout: float = 30.0,
        generate_timeout: float = 600.0,
        max_retries: int = 2,
    ):
        self.base_url = base_url
        self.model = model
        self.health_timeout = health_timeout
        self.generate_timeout = generate_timeout
        self.max_retries = max_retries
        self._client: httpx.AsyncClient | None = None
        self._owned: bool = False

    async def __aenter__(self) -> "OllamaClient":
        self._client = httpx.AsyncClient()
        self._owned = True
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        if self._owned and self._client is not None:
            await self._client.aclose()
            self._client = None
            self._owned = False

    def get_base_url(self) -> str:
        return self.base_url

    async def set_base_url(self, url: str) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None
        self.base_url = url

    def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient()
        return self._client

    async def check_health(self) -> bool:
        client = self._get_client()
        via_logger.log(
            "ollama_client", "INFO", "Checking Ollama health", details={"model": self.model}
        )
        try:
            resp = await client.get(
                f"{self.base_url}/api/tags",
                timeout=self.health_timeout,
            )
            models = resp.json().get("models", [])
            names = [m.get("name", "") for m in models]
            if not any(name.startswith(self.model) for name in names):
                raise OllamaModelNotFoundError(
                    f"Model {self.model!r} not found in Ollama. Available: {names}"
                )
            via_logger.log(
                "ollama_client", "INFO", "Ollama healthy", details={"model": self.model}
            )
            return True
        except OllamaModelNotFoundError:
            raise
        except httpx.ConnectError as e:
            via_logger.log(
                "ollama_client", "ERROR", "Ollama connection failed", details={"error": str(e)}
            )
            raise OllamaConnectionError(
                f"Cannot connect to Ollama at {self.base_url}"
            ) from e

    async def _do_generate(self, payload: dict) -> str:
        client = self._get_client()
        via_logger.log(
            "ollama_client", "INFO", "Sending generation request", details={"model": self.model}
        )
        last_exc: Exception | None = None
        for attempt in range(self.max_retries + 1):
            try:
                resp = await client.post(
                    f"{self.base_url}/api/generate",
                    json=payload,
                    timeout=self.generate_timeout,
                )
                if resp.status_code != 200:
                    raise OllamaGenerationError(
                        f"Unexpected status from Ollama: {resp.status_code}"
                    )
                text = resp.json().get("response", "")
                if not text:
                    raise OllamaGenerationError("Empty response from Ollama")
                via_logger.log("ollama_client", "INFO", "Generation complete")
                return text
            except OllamaGenerationError:
                raise
            except (httpx.TimeoutException, httpx.ConnectError) as e:
                last_exc = e
                if attempt < self.max_retries:
                    await asyncio.sleep(2 ** attempt)
                    continue

        if isinstance(last_exc, httpx.ConnectError):
            via_logger.log(
                "ollama_client",
                "ERROR",
                "Ollama connection failed after retries",
                details={"error": str(last_exc)},
            )
            raise OllamaConnectionError(
                f"Cannot connect to Ollama at {self.base_url}"
            ) from last_exc

        via_logger.log(
            "ollama_client",
            "ERROR",
            "Generation timed out after retries",
            details={"error": str(last_exc)},
        )
        raise OllamaGenerationError(
            f"Generation failed after {self.max_retries} retries"
        ) from last_exc

    async def generate(self, prompt: str, system: str | None = None) -> str:
        payload: dict = {"model": self.model, "prompt": prompt, "stream": False}
        if system is not None:
            payload["system"] = system
        return await self._do_generate(payload)

    async def generate_with_images(
        self,
        prompt: str,
        images: list[str],
        system: str | None = None,
    ) -> str:
        payload: dict = {
            "model": self.model,
            "prompt": prompt,
            "images": images,
            "stream": False,
        }
        if system is not None:
            payload["system"] = system
        return await self._do_generate(payload)

    async def generate_with_image_paths(
        self,
        prompt: str,
        image_paths: list[str],
        system: str | None = None,
    ) -> str:
        images: list[str] = []
        for path in image_paths:
            with open(path, "rb") as f:
                images.append(base64.b64encode(f.read()).decode())
        return await self.generate_with_images(prompt, images, system)


ollama_client = OllamaClient()
