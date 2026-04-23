"""Image storage and metadata management service."""

from datetime import datetime, timezone
from pathlib import Path


class ImageStore:
    def __init__(self):
        self._store: dict[str, dict] = {}

    def add(self, metadata: dict) -> dict:
        entry = {**metadata, "uploaded_at": datetime.now(timezone.utc).isoformat()}
        self._store[metadata["id"]] = entry
        return entry

    def get(self, image_id: str) -> dict | None:
        return self._store.get(image_id)

    def list_all(self, purpose: str | None = None, label: str | None = None) -> list[dict]:
        items = list(self._store.values())
        if purpose is not None:
            items = [i for i in items if i.get("purpose") == purpose]
        if label is not None:
            items = [i for i in items if i.get("label") == label]
        return items

    def delete(self, image_id: str) -> bool:
        entry = self._store.pop(image_id, None)
        if entry is None:
            return False
        try:
            Path(entry["path"]).unlink()
        except FileNotFoundError:
            pass
        return True

    def clear(self, purpose: str | None = None) -> None:
        if purpose is None:
            to_delete = list(self._store.keys())
        else:
            to_delete = [k for k, v in self._store.items() if v.get("purpose") == purpose]
        for image_id in to_delete:
            entry = self._store.pop(image_id)
            try:
                Path(entry["path"]).unlink()
            except FileNotFoundError:
                pass

    def count(self, purpose: str | None = None) -> int:
        return len(self.list_all(purpose=purpose))


image_store = ImageStore()
