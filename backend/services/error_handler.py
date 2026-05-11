"""Centralized error handling for VIA backend."""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse


class VIAError(Exception):
    def __init__(
        self,
        message: str,
        *,
        agent_name: str | None = None,
        error_code: str | None = None,
        user_message: str | None = None,
    ) -> None:
        super().__init__(message)
        self.agent_name = agent_name
        self.error_code = error_code
        self.user_message = user_message


class AgentExecutionError(VIAError):
    """An agent raised an unexpected exception during execution."""


class OllamaConnectionError(VIAError):
    """Ollama server is unreachable or returned an unexpected response."""


class ImageProcessingError(VIAError):
    """Image loading or processing failed."""


class ConfigurationError(VIAError):
    """Invalid or missing application configuration."""


class ExportError(VIAError):
    """Result export failed."""


def format_error_response(error: VIAError) -> dict:
    return {
        "error_code": error.error_code,
        "agent": error.agent_name,
        "message": error.user_message if error.user_message is not None else str(error),
        "details": str(error),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(OllamaConnectionError)
    async def _ollama_handler(request: Request, exc: OllamaConnectionError) -> JSONResponse:
        return JSONResponse(status_code=503, content=format_error_response(exc))

    @app.exception_handler(ImageProcessingError)
    async def _image_handler(request: Request, exc: ImageProcessingError) -> JSONResponse:
        return JSONResponse(status_code=400, content=format_error_response(exc))

    @app.exception_handler(ConfigurationError)
    async def _config_handler(request: Request, exc: ConfigurationError) -> JSONResponse:
        return JSONResponse(status_code=400, content=format_error_response(exc))

    @app.exception_handler(VIAError)
    async def _via_handler(request: Request, exc: VIAError) -> JSONResponse:
        return JSONResponse(status_code=500, content=format_error_response(exc))
