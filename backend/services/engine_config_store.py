"""Engine configuration singleton store."""


class EngineConfigStore:
    def __init__(self):
        self._engine_mode: str = "local"
        self._colab_url: str | None = None

    def get(self) -> dict:
        return {"engine_mode": self._engine_mode, "colab_url": self._colab_url}

    def save(self, mode: str, url: str | None) -> None:
        self._engine_mode = mode
        self._colab_url = url

    def reset(self) -> None:
        self._engine_mode = "local"
        self._colab_url = None


engine_config_store = EngineConfigStore()
