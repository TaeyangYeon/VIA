"""FastAPI application entry point."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.config import VIAConfig
from backend.routers.config import router as config_router
from backend.routers.directives import router as directives_router
from backend.routers.engine import router as engine_router
from backend.routers.execute import router as execute_router
from backend.routers.export import router as export_router
from backend.routers.images import router as images_router
from backend.routers.logs import router as logs_router
from backend.services.error_handler import register_error_handlers

config = VIAConfig()

app = FastAPI(title="VIA API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=config.cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

register_error_handlers(app)

app.include_router(images_router, prefix="/api/images")
app.include_router(config_router, prefix="/api/config")
app.include_router(directives_router, prefix="/api/directives")
app.include_router(logs_router, prefix="/api/logs")
app.include_router(execute_router, prefix="/api/execute")
app.include_router(engine_router, prefix="/api/engine")
app.include_router(export_router, prefix="/api/export")


@app.get("/health")
async def health():
    return {"status": "ok", "version": app.version}
