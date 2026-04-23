"""Router for agent directive endpoints."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.services.directive_store import AGENT_NAMES, directive_store

router = APIRouter()


class AgentDirectives(BaseModel):
    orchestrator: str | None = None
    spec: str | None = None
    image_analysis: str | None = None
    pipeline_composer: str | None = None
    vision_judge: str | None = None
    inspection_plan: str | None = None
    algorithm_coder: str | None = None
    test: str | None = None


class SingleDirective(BaseModel):
    directive: str | None = None


@router.post("")
async def save_directives(body: AgentDirectives):
    directive_store.save(body.model_dump())
    return directive_store.get()


@router.get("")
async def get_directives():
    return directive_store.get()


@router.put("/{agent_name}")
async def update_directive(agent_name: str, body: SingleDirective):
    if agent_name not in AGENT_NAMES:
        raise HTTPException(status_code=404, detail=f"Unknown agent: '{agent_name}'")
    directive_store.update(agent_name, body.directive)
    return directive_store.get()


@router.delete("")
async def reset_directives():
    directive_store.reset()
    return directive_store.get()
