"""Execution config singleton store."""

from typing import Any


class ConfigStore:
    def __init__(self):
        self._config: dict[str, Any] | None = None

    def save(self, data: dict[str, Any]) -> None:
        self._config = data

    def get(self) -> dict[str, Any] | None:
        return self._config

    def clear(self) -> None:
        self._config = None


config_store = ConfigStore()
