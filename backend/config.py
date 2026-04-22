"""Application configuration and settings."""

from pydantic_settings import BaseSettings


class VIAConfig(BaseSettings):
    """VIA application configuration."""

    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = True
    cors_origins: list[str] = ["*"]
    upload_dir: str = "./uploads"
    log_level: str = "INFO"

    model_config = {"env_prefix": "VIA_"}
