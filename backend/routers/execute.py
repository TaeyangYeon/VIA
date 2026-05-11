"""Router for pipeline execution endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from backend.services.execution_manager import (
    ExecutionManager,
    ExecutionState,
    execution_manager as _execution_manager,
)

router = APIRouter()


class ExecuteRequest(BaseModel):
    purpose_text: str


def get_manager() -> ExecutionManager:
    return _execution_manager


def _state_to_dict(state: ExecutionState) -> dict:
    return {
        "execution_id": state.execution_id,
        "status": state.status,
        "current_agent": state.current_agent,
        "current_iteration": state.current_iteration,
        "result": state.result,
        "error": state.error,
        "started_at": state.started_at,
        "completed_at": state.completed_at,
    }


@router.post("", status_code=202)
async def start_execution(
    body: ExecuteRequest,
    mgr: ExecutionManager = Depends(get_manager),
):
    try:
        eid = await mgr.start(body.purpose_text)
        return {"execution_id": eid, "status": "running"}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except RuntimeError as exc:
        raise HTTPException(status_code=409, detail=str(exc))


@router.get("/history")
def get_history(mgr: ExecutionManager = Depends(get_manager)):
    return [_state_to_dict(s) for s in mgr.get_history()]


@router.get("/{execution_id}")
def get_execution(
    execution_id: str,
    mgr: ExecutionManager = Depends(get_manager),
):
    state = mgr.get_status(execution_id)
    if state is None:
        raise HTTPException(status_code=404, detail="execution not found")
    return _state_to_dict(state)


@router.post("/{execution_id}/cancel")
async def cancel_execution(
    execution_id: str,
    mgr: ExecutionManager = Depends(get_manager),
):
    state = mgr.get_status(execution_id)
    if state is None:
        raise HTTPException(status_code=404, detail="execution not found")
    if state.status != "running":
        raise HTTPException(status_code=400, detail="execution is not running")
    result = await mgr.cancel(execution_id)
    return _state_to_dict(result)
