"""Router for result export endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse, Response

from backend.services.execution_manager import (
    ExecutionManager,
    ExecutionState,
    execution_manager as _execution_manager,
)

router = APIRouter()


def get_manager() -> ExecutionManager:
    return _execution_manager


def _latest_success(mgr: ExecutionManager) -> ExecutionState | None:
    for state in mgr.get_history():
        if state.status == "success" and state.result is not None:
            return state
    return None


@router.get("/code")
async def export_code(mgr: ExecutionManager = Depends(get_manager)):
    state = _latest_success(mgr)
    if state is None:
        raise HTTPException(status_code=404, detail="No completed execution result available")

    algorithm_result = state.result.get("algorithm_result")
    if algorithm_result is None:
        raise HTTPException(status_code=404, detail="No algorithm code in execution result")

    code: str = algorithm_result.code or ""
    return Response(
        content=code.encode("utf-8"),
        media_type="text/x-python",
        headers={"Content-Disposition": 'attachment; filename="via_algorithm.py"'},
    )


@router.get("/result")
async def export_result(mgr: ExecutionManager = Depends(get_manager)):
    state = _latest_success(mgr)
    if state is None:
        raise HTTPException(status_code=404, detail="No completed execution result available")

    raw = state.result
    algorithm_result = raw.get("algorithm_result")
    best_pipeline = raw.get("best_pipeline")
    inspection_plan = raw.get("inspection_plan")
    evaluation_result = raw.get("evaluation_result")
    decision_result = raw.get("decision_result")
    test_results = raw.get("test_results") or []

    import dataclasses as _dc

    def _try_dump(obj):
        if obj is None:
            return None
        # Check the class (not the instance) to avoid Mock's magic __getattr__
        if hasattr(type(obj), "model_dump"):
            return obj.model_dump()
        if _dc.is_dataclass(type(obj)):
            return _dc.asdict(obj)
        return str(obj)

    def _dump_test_results(results):
        out = []
        for r in results:
            if _dc.is_dataclass(type(r)):
                out.append(_dc.asdict(r))
            else:
                out.append(str(r))
        return out

    payload = {
        "algorithm_code": algorithm_result.code if algorithm_result else None,
        "algorithm_explanation": algorithm_result.explanation if algorithm_result else None,
        "pipeline": _try_dump(best_pipeline),
        "inspection_plan": _try_dump(inspection_plan),
        "evaluation": _try_dump(evaluation_result),
        "item_results": _dump_test_results(test_results),
        "decision": _try_dump(decision_result),
        "warnings": raw.get("warnings") or [],
        "iteration_history": raw.get("iteration_history") or [],
        "execution_id": state.execution_id,
        "started_at": state.started_at,
        "completed_at": state.completed_at,
    }

    return JSONResponse(
        content=payload,
        headers={"Content-Disposition": 'attachment; filename="via_result.json"'},
    )
