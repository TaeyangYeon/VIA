"""Agent directive singleton store."""

from typing import Any

AGENT_NAMES = {
    "orchestrator",
    "spec",
    "image_analysis",
    "pipeline_composer",
    "vision_judge",
    "inspection_plan",
    "algorithm_coder",
    "test",
}


class DirectiveStore:
    def __init__(self):
        self._data: dict[str, str | None] = {name: None for name in AGENT_NAMES}

    def get(self) -> dict[str, str | None]:
        return dict(self._data)

    def save(self, data: dict[str, Any]) -> None:
        for key, value in data.items():
            if key in AGENT_NAMES:
                self._data[key] = value

    def update(self, agent_name: str, directive: str | None) -> None:
        if agent_name not in AGENT_NAMES:
            raise ValueError(f"Unknown agent: '{agent_name}'")
        self._data[agent_name] = directive

    def reset(self) -> None:
        self._data = {name: None for name in AGENT_NAMES}


directive_store = DirectiveStore()
