"""Structured logging service for agent activities."""

import threading
from collections import deque
from datetime import datetime, timezone

import structlog

structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        structlog.processors.JSONRenderer(),
    ],
    wrapper_class=structlog.BoundLogger,
    context_class=dict,
    logger_factory=structlog.PrintLoggerFactory(),
)

_VALID_LEVELS = {"DEBUG", "INFO", "WARNING", "ERROR"}
_struct_logger = structlog.get_logger("via")


class VIALogger:
    def __init__(self, max_size: int = 1000):
        self._max_size = max_size
        self._buffer: deque[dict] = deque(maxlen=max_size)
        self._lock = threading.Lock()

    def log(self, agent: str, level: str, message: str, details: dict | None = None) -> None:
        if not agent:
            raise ValueError("agent must be a non-empty string")
        if level not in _VALID_LEVELS:
            raise ValueError(f"level must be one of {_VALID_LEVELS}, got {level!r}")

        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "agent": agent,
            "level": level,
            "message": message,
            "details": details,
        }
        with self._lock:
            self._buffer.append(entry)

        log_fn = getattr(_struct_logger, level.lower(), _struct_logger.info)
        log_fn(message, agent=agent, details=details)

    def get_logs(
        self,
        agent: str | None = None,
        level: str | None = None,
        limit: int = 100,
    ) -> list[dict]:
        with self._lock:
            items = list(self._buffer)

        items = list(reversed(items))

        if agent is not None:
            items = [e for e in items if e["agent"] == agent]
        if level is not None:
            items = [e for e in items if e["level"] == level]

        return items[:limit]

    def clear(self) -> None:
        with self._lock:
            self._buffer.clear()

    def get_agents(self) -> list[str]:
        with self._lock:
            agents = list(dict.fromkeys(e["agent"] for e in self._buffer))
        return agents


via_logger = VIALogger()
