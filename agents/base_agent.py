"""Abstract base class for all VIA agents."""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional

from backend.services.logger import via_logger


class BaseAgent(ABC):
    def __init__(self, name: str, directive: Optional[str] = None) -> None:
        self._name = name
        self._directive = directive

    @abstractmethod
    async def execute(self, **kwargs) -> dict:
        ...

    @property
    def agent_name(self) -> str:
        return self._name

    def get_directive(self) -> Optional[str]:
        return self._directive

    def set_directive(self, directive: str) -> None:
        self._directive = directive

    def _log(self, level: str, message: str, details: Optional[dict] = None) -> None:
        via_logger.log(self._name, level, message, details)
