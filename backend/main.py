"""FastAPI application entry point."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.config import VIAConfig
from backend.routers.images import router as images_router

config = VIAConfig()

app = FastAPI(title="VIA API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=config.cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(images_router, prefix="/api/images")


@app.get("/health")
async def health():
    return {"status": "ok", "version": app.version}
