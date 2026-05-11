"""Tests for Step 7: ImageStore service + management API endpoints."""

import uuid
from pathlib import Path

import cv2
import httpx
import numpy as np
import pytest

from backend.main import app
from backend.services.image_store import ImageStore, image_store


# ---- Fixtures ----


@pytest.fixture(params=["asyncio"])
def anyio_backend(request):
    return request.param


@pytest.fixture
def async_client():
    transport = httpx.ASGITransport(app=app)
    return httpx.AsyncClient(transport=transport, base_url="http://testserver")


@pytest.fixture(autouse=True)
def reset_store():
    """Clear the singleton store before and after each test."""
    image_store.clear()
    yield
    image_store.clear()


def make_png_bytes(width=100, height=100, color=(0, 255, 0)):
    img = np.zeros((height, width, 3), dtype=np.uint8)
    img[:] = color
    success, encoded = cv2.imencode(".png", img)
    assert success
    return encoded.tobytes()


def make_metadata(
    image_id=None,
    filename="OK_1.png",
    label="OK",
    index=1,
    purpose="analysis",
    path="/tmp/OK_1.png",
):
    return {
        "id": image_id or str(uuid.uuid4()),
        "filename": filename,
        "label": label,
        "index": index,
        "purpose": purpose,
        "path": path,
    }


# ---- ImageStore Unit Tests ----


class TestImageStoreAdd:
    def test_add_stores_metadata_and_returns_it(self):
        store = ImageStore()
        meta = make_metadata(image_id="id-1")
        result = store.add(meta)
        assert result["id"] == "id-1"
        assert result["filename"] == "OK_1.png"

    def test_add_attaches_uploaded_at_timestamp(self):
        store = ImageStore()
        meta = make_metadata(image_id="id-2")
        result = store.add(meta)
        assert "uploaded_at" in result
        assert "T" in result["uploaded_at"]

    def test_add_uploaded_at_is_utc(self):
        store = ImageStore()
        meta = make_metadata(image_id="id-3")
        result = store.add(meta)
        ts = result["uploaded_at"]
        assert ts.endswith("Z") or ts.endswith("+00:00")

    def test_add_does_not_mutate_input_dict(self):
        store = ImageStore()
        meta = make_metadata(image_id="id-4")
        original_keys = set(meta.keys())
        store.add(meta)
        assert set(meta.keys()) == original_keys


class TestImageStoreGet:
    def test_get_existing_returns_metadata(self):
        store = ImageStore()
        store.add(make_metadata(image_id="get-1"))
        result = store.get("get-1")
        assert result is not None
        assert result["id"] == "get-1"

    def test_get_nonexistent_returns_none(self):
        store = ImageStore()
        assert store.get("nonexistent-id") is None

    def test_get_returns_uploaded_at(self):
        store = ImageStore()
        store.add(make_metadata(image_id="get-2"))
        result = store.get("get-2")
        assert "uploaded_at" in result


class TestImageStoreListAll:
    def test_list_all_empty_store_returns_empty_list(self):
        store = ImageStore()
        assert store.list_all() == []

    def test_list_all_returns_all_stored_items(self):
        store = ImageStore()
        store.add(make_metadata(image_id="ls-1", purpose="analysis"))
        store.add(make_metadata(image_id="ls-2", purpose="test"))
        result = store.list_all()
        assert len(result) == 2

    def test_list_all_filter_by_purpose(self):
        store = ImageStore()
        store.add(make_metadata(image_id="ls-3", purpose="analysis"))
        store.add(make_metadata(image_id="ls-4", purpose="test"))
        result = store.list_all(purpose="analysis")
        assert len(result) == 1
        assert result[0]["id"] == "ls-3"

    def test_list_all_filter_by_label(self):
        store = ImageStore()
        store.add(make_metadata(image_id="ls-5", label="OK"))
        store.add(make_metadata(image_id="ls-6", label="NG"))
        result = store.list_all(label="NG")
        assert len(result) == 1
        assert result[0]["id"] == "ls-6"

    def test_list_all_filter_by_both_purpose_and_label(self):
        store = ImageStore()
        store.add(make_metadata(image_id="ls-7", purpose="analysis", label="OK"))
        store.add(make_metadata(image_id="ls-8", purpose="analysis", label="NG"))
        store.add(make_metadata(image_id="ls-9", purpose="test", label="OK"))
        result = store.list_all(purpose="analysis", label="OK")
        assert len(result) == 1
        assert result[0]["id"] == "ls-7"


class TestImageStoreDelete:
    def test_delete_existing_returns_true(self, tmp_path):
        store = ImageStore()
        file_path = tmp_path / "OK_1.png"
        file_path.write_bytes(b"image data")
        store.add(make_metadata(image_id="del-1", path=str(file_path)))
        assert store.delete("del-1") is True

    def test_delete_removes_metadata(self, tmp_path):
        store = ImageStore()
        file_path = tmp_path / "OK_1.png"
        file_path.write_bytes(b"image data")
        store.add(make_metadata(image_id="del-2", path=str(file_path)))
        store.delete("del-2")
        assert store.get("del-2") is None

    def test_delete_removes_file_from_disk(self, tmp_path):
        store = ImageStore()
        file_path = tmp_path / "OK_1.png"
        file_path.write_bytes(b"image data")
        store.add(make_metadata(image_id="del-3", path=str(file_path)))
        store.delete("del-3")
        assert not file_path.exists()

    def test_delete_handles_missing_file_gracefully(self, tmp_path):
        store = ImageStore()
        missing_path = tmp_path / "gone.png"
        store.add(make_metadata(image_id="del-4", path=str(missing_path)))
        result = store.delete("del-4")
        assert result is True
        assert store.get("del-4") is None

    def test_delete_nonexistent_returns_false(self):
        store = ImageStore()
        assert store.delete("nonexistent") is False


class TestImageStoreClear:
    def test_clear_all_removes_all_metadata(self):
        store = ImageStore()
        store.add(make_metadata(image_id="clr-1", purpose="analysis"))
        store.add(make_metadata(image_id="clr-2", purpose="test"))
        store.clear()
        assert store.count() == 0

    def test_clear_empty_store_does_not_raise(self):
        store = ImageStore()
        store.clear()
        assert store.count() == 0

    def test_clear_by_purpose_removes_only_matching(self):
        store = ImageStore()
        store.add(make_metadata(image_id="clr-3", purpose="analysis"))
        store.add(make_metadata(image_id="clr-4", purpose="test"))
        store.clear(purpose="analysis")
        assert store.count() == 1
        assert store.get("clr-4") is not None
        assert store.get("clr-3") is None


class TestImageStoreCount:
    def test_count_empty_is_zero(self):
        store = ImageStore()
        assert store.count() == 0

    def test_count_all(self):
        store = ImageStore()
        store.add(make_metadata(image_id="cnt-1", purpose="analysis"))
        store.add(make_metadata(image_id="cnt-2", purpose="test"))
        assert store.count() == 2

    def test_count_by_purpose(self):
        store = ImageStore()
        store.add(make_metadata(image_id="cnt-3", purpose="analysis"))
        store.add(make_metadata(image_id="cnt-4", purpose="analysis"))
        store.add(make_metadata(image_id="cnt-5", purpose="test"))
        assert store.count("analysis") == 2
        assert store.count("test") == 1


# ---- API Integration Tests ----


class TestListImagesAPI:
    @pytest.mark.anyio
    async def test_list_all_empty(self, async_client):
        async with async_client as client:
            response = await client.get("/api/images")
        assert response.status_code == 200
        assert response.json() == []

    @pytest.mark.anyio
    async def test_list_all_returns_stored_images(self, async_client):
        image_store.add(make_metadata(image_id="api-1", purpose="analysis"))
        image_store.add(make_metadata(image_id="api-2", purpose="test"))
        async with async_client as client:
            response = await client.get("/api/images")
        assert response.status_code == 200
        assert len(response.json()) == 2

    @pytest.mark.anyio
    async def test_list_filter_by_purpose(self, async_client):
        image_store.add(make_metadata(image_id="api-3", purpose="analysis"))
        image_store.add(make_metadata(image_id="api-4", purpose="test"))
        async with async_client as client:
            response = await client.get("/api/images", params={"purpose": "analysis"})
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["id"] == "api-3"

    @pytest.mark.anyio
    async def test_list_filter_by_label(self, async_client):
        image_store.add(make_metadata(image_id="api-5", label="OK"))
        image_store.add(make_metadata(image_id="api-6", label="NG"))
        async with async_client as client:
            response = await client.get("/api/images", params={"label": "OK"})
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["id"] == "api-5"


class TestGetImageAPI:
    @pytest.mark.anyio
    async def test_get_existing_image(self, async_client):
        image_store.add(make_metadata(image_id="get-api-1"))
        async with async_client as client:
            response = await client.get("/api/images/get-api-1")
        assert response.status_code == 200
        assert response.json()["id"] == "get-api-1"

    @pytest.mark.anyio
    async def test_get_nonexistent_returns_404(self, async_client):
        async with async_client as client:
            response = await client.get("/api/images/nonexistent-id")
        assert response.status_code == 404


class TestDeleteImageAPI:
    @pytest.mark.anyio
    async def test_delete_existing_image_returns_200(self, async_client, tmp_path):
        file_path = tmp_path / "OK_1.png"
        file_path.write_bytes(b"data")
        image_store.add(make_metadata(image_id="del-api-1", path=str(file_path)))
        async with async_client as client:
            response = await client.delete("/api/images/del-api-1")
        assert response.status_code == 200
        assert image_store.get("del-api-1") is None

    @pytest.mark.anyio
    async def test_delete_nonexistent_returns_404(self, async_client):
        async with async_client as client:
            response = await client.delete("/api/images/nonexistent-id")
        assert response.status_code == 404


class TestClearImagesAPI:
    @pytest.mark.anyio
    async def test_clear_all_images(self, async_client):
        image_store.add(make_metadata(image_id="clr-api-1", purpose="analysis"))
        image_store.add(make_metadata(image_id="clr-api-2", purpose="test"))
        async with async_client as client:
            response = await client.delete("/api/images")
        assert response.status_code == 200
        assert image_store.count() == 0

    @pytest.mark.anyio
    async def test_clear_by_purpose(self, async_client):
        image_store.add(make_metadata(image_id="clr-api-3", purpose="analysis"))
        image_store.add(make_metadata(image_id="clr-api-4", purpose="test"))
        async with async_client as client:
            response = await client.delete("/api/images", params={"purpose": "analysis"})
        assert response.status_code == 200
        assert image_store.count() == 1
        assert image_store.get("clr-api-4") is not None


# ---- Upload-Store Integration Tests ----


class TestUploadStoreIntegration:
    @pytest.mark.anyio
    async def test_upload_registers_in_store(self, async_client, tmp_path, monkeypatch):
        monkeypatch.setattr("backend.routers.images.config.upload_dir", str(tmp_path))
        content = make_png_bytes()
        async with async_client as client:
            response = await client.post(
                "/api/images/upload",
                params={"purpose": "analysis"},
                files={"file": ("OK_1.png", content, "image/png")},
            )
        assert response.status_code == 200
        image_id = response.json()["id"]
        assert image_store.get(image_id) is not None

    @pytest.mark.anyio
    async def test_upload_response_includes_uploaded_at(self, async_client, tmp_path, monkeypatch):
        monkeypatch.setattr("backend.routers.images.config.upload_dir", str(tmp_path))
        content = make_png_bytes()
        async with async_client as client:
            response = await client.post(
                "/api/images/upload",
                params={"purpose": "analysis"},
                files={"file": ("OK_1.png", content, "image/png")},
            )
        assert response.status_code == 200
        assert "uploaded_at" in response.json()

    @pytest.mark.anyio
    async def test_uploaded_image_retrievable_via_get(self, async_client, tmp_path, monkeypatch):
        monkeypatch.setattr("backend.routers.images.config.upload_dir", str(tmp_path))
        content = make_png_bytes()
        async with async_client as client:
            upload_resp = await client.post(
                "/api/images/upload",
                params={"purpose": "analysis"},
                files={"file": ("OK_1.png", content, "image/png")},
            )
            image_id = upload_resp.json()["id"]
            get_resp = await client.get(f"/api/images/{image_id}")
        assert get_resp.status_code == 200
        assert get_resp.json()["id"] == image_id

    @pytest.mark.anyio
    async def test_uploaded_image_appears_in_list(self, async_client, tmp_path, monkeypatch):
        monkeypatch.setattr("backend.routers.images.config.upload_dir", str(tmp_path))
        content = make_png_bytes()
        async with async_client as client:
            await client.post(
                "/api/images/upload",
                params={"purpose": "analysis"},
                files={"file": ("OK_1.png", content, "image/png")},
            )
            list_resp = await client.get("/api/images")
        assert list_resp.status_code == 200
        assert len(list_resp.json()) == 1

    @pytest.mark.anyio
    async def test_uploaded_image_deletable_via_api(self, async_client, tmp_path, monkeypatch):
        monkeypatch.setattr("backend.routers.images.config.upload_dir", str(tmp_path))
        content = make_png_bytes()
        async with async_client as client:
            upload_resp = await client.post(
                "/api/images/upload",
                params={"purpose": "analysis"},
                files={"file": ("OK_1.png", content, "image/png")},
            )
            image_id = upload_resp.json()["id"]
            del_resp = await client.delete(f"/api/images/{image_id}")
        assert del_resp.status_code == 200
        assert image_store.get(image_id) is None
