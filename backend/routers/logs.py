"""Router for log retrieval endpoints."""

from fastapi import APIRouter

from backend.services.logger import via_logger

router = APIRouter()


@router.get("")
async def get_logs(
    agent: str | None = None,
    level: str | None = None,
    limit: int = 100,
):
    logs = via_logger.get_logs(agent=agent, level=level, limit=limit)
    return {"logs": logs, "total": len(logs)}


@router.get("/agents")
async def get_agents():
    return via_logger.get_agents()


@router.delete("")
async def clear_logs():
    via_logger.clear()
    return {"cleared": True}
