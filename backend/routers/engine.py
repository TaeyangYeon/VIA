"""Router for engine configuration endpoints."""

from typing import Literal, Optional

import httpx
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel, model_validator

from backend.services.colab_notebook_generator import ColabNotebookGenerator
from backend.services.engine_config_store import engine_config_store
from backend.services.ollama_client import OllamaConnectionError, OllamaModelNotFoundError, ollama_client

router = APIRouter()

_LOCALHOST = "http://localhost:11434"


class EngineConfigRequest(BaseModel):
    engine_mode: Literal["local", "colab"]
    colab_url: Optional[str] = None

    @model_validator(mode="after")
    def colab_requires_url(self) -> "EngineConfigRequest":
        if self.engine_mode == "colab" and not self.colab_url:
            raise ValueError("colab_url is required when engine_mode is 'colab'")
        return self


@router.post("/config")
async def save_engine_config(body: EngineConfigRequest):
    warning: Optional[str] = None

    if body.engine_mode == "colab":
        try:
            async with httpx.AsyncClient() as http:
                await http.get(f"{body.colab_url}/api/tags", timeout=10.0)
        except (httpx.ConnectError, httpx.TimeoutException):
            warning = f"Colab URL unreachable: {body.colab_url}"

        engine_config_store.save("colab", body.colab_url)
        await ollama_client.set_base_url(body.colab_url)
    else:
        engine_config_store.save("local", None)
        await ollama_client.set_base_url(_LOCALHOST)

    result = {**engine_config_store.get()}
    if warning:
        result["warning"] = warning
    return result


@router.get("/status")
async def get_engine_status():
    store = engine_config_store.get()
    base_url = ollama_client.get_base_url()
    connected = False
    model_available = False
    error: Optional[str] = None

    try:
        await ollama_client.check_health()
        connected = True
        model_available = True
    except OllamaModelNotFoundError as e:
        connected = True
        model_available = False
        error = str(e)
    except OllamaConnectionError as e:
        connected = False
        model_available = False
        error = str(e)

    return {
        "engine_mode": store["engine_mode"],
        "base_url": base_url,
        "connected": connected,
        "model_available": model_available,
        "error": error,
    }


@router.get("/setup-notebook")
def download_setup_notebook(model: str = Query(default="gemma4:e4b")):
    try:
        nb = ColabNotebookGenerator().generate(model=model)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    import nbformat as _nbformat
    nb_json = _nbformat.writes(nb)
    filename = f"via_colab_setup_notebook_{model.replace(':', '_')}.ipynb"
    return JSONResponse(
        content=_nbformat.reads(nb_json, as_version=4),
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
