"""Router for execution configuration endpoints."""

from typing import Annotated, Any, Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from backend.services.config_store import config_store

router = APIRouter()


class InspectionCriteria(BaseModel):
    accuracy: Annotated[float, Field(ge=0.0, le=1.0)]
    fp_rate: Annotated[float, Field(ge=0.0, le=1.0)]
    fn_rate: Annotated[float, Field(ge=0.0, le=1.0)]


class AlignCriteria(BaseModel):
    coord_error: float
    success_rate: Annotated[float, Field(ge=0.0, le=1.0)]


class ExecutionConfigRequest(BaseModel):
    mode: Literal["inspection", "align"]
    max_iteration: Annotated[int, Field(default=5, ge=1, le=20)]
    success_criteria: InspectionCriteria | AlignCriteria


def _build_warnings(mode: str, criteria: dict[str, Any]) -> list[str]:
    warnings: list[str] = []
    if mode == "inspection":
        if criteria.get("accuracy", 0) > 0.99:
            warnings.append("99%+ accuracy is extremely difficult")
        if criteria.get("fp_rate", 1) < 0.001:
            warnings.append("Near-zero false positive rate may be unrealistic")
        if criteria.get("fn_rate", 1) < 0.001:
            warnings.append("Near-zero false negative rate may be unrealistic")
    elif mode == "align":
        if criteria.get("coord_error", 1) < 0.5:
            warnings.append("Sub-pixel accuracy may require hardware improvements")
    return warnings


@router.post("")
async def save_config(body: ExecutionConfigRequest):
    criteria_dict = body.success_criteria.model_dump()
    data: dict[str, Any] = {
        "mode": body.mode,
        "max_iteration": body.max_iteration,
        "success_criteria": criteria_dict,
    }
    config_store.save(data)
    warnings = _build_warnings(body.mode, criteria_dict)
    return {**data, "warnings": warnings}


@router.get("")
async def get_config():
    cfg = config_store.get()
    if cfg is None:
        raise HTTPException(status_code=404, detail="No config saved yet.")
    return cfg
