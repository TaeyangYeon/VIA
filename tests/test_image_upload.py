"""Tests for Step 6: Image upload API + validation logic."""

import io
import uuid

import cv2
import numpy as np
import pytest
import httpx

from backend.main import app


@pytest.fixture(params=["asyncio"])
def anyio_backend(request):
    return request.param


@pytest.fixture
def async_client():
    """Create an async test client using ASGITransport."""
    transport = httpx.ASGITransport(app=app)
    return httpx.AsyncClient(transport=transport, base_url="http://testserver")


def make_png_bytes(width=100, height=100, color=(0, 255, 0)):
    """Create a valid PNG image in memory and return its bytes."""
    img = np.zeros((height, width, 3), dtype=np.uint8)
    img[:] = color
    success, encoded = cv2.imencode(".png", img)
    assert success
    return encoded.tobytes()


def make_jpg_bytes(width=100, height=100):
    """Create a valid JPEG image in memory and return its bytes."""
    img = np.zeros((height, width, 3), dtype=np.uint8)
    img[:] = (128, 128, 128)
    success, encoded = cv2.imencode(".jpg", img)
    assert success
    return encoded.tobytes()


def make_bmp_bytes(width=100, height=100):
    """Create a valid BMP image in memory and return its bytes."""
    img = np.zeros((height, width, 3), dtype=np.uint8)
    img[:] = (200, 100, 50)
    success, encoded = cv2.imencode(".bmp", img)
    assert success
    return encoded.tobytes()


# --- Filename validation: valid cases ---


class TestValidFilenames:
    """Test that valid filenames are accepted."""

    @pytest.mark.anyio
    async def test_ok_1_png(self, async_client, tmp_path, monkeypatch):
        monkeypatch.setattr("backend.routers.images.config.upload_dir", str(tmp_path))
        content = make_png_bytes()
        async with async_client as client:
            response = await client.post(
                "/api/images/upload",
                params={"purpose": "analysis"},
                files={"file": ("OK_1.png", content, "image/png")},
            )
        assert response.status_code == 200
        data = response.json()
        assert data["filename"] == "OK_1.png"
        assert data["label"] == "OK"
        assert data["index"] == 1

    @pytest.mark.anyio
    async def test_ng_3_jpg(self, async_client, tmp_path, monkeypatch):
        monkeypatch.setattr("backend.routers.images.config.upload_dir", str(tmp_path))
        content = make_jpg_bytes()
        async with async_client as client:
            response = await client.post(
                "/api/images/upload",
                params={"purpose": "analysis"},
                files={"file": ("NG_3.jpg", content, "image/jpeg")},
            )
        assert response.status_code == 200
        data = response.json()
        assert data["label"] == "NG"
        assert data["index"] == 3

    @pytest.mark.anyio
    async def test_ok_12_bmp(self, async_client, tmp_path, monkeypatch):
        monkeypatch.setattr("backend.routers.images.config.upload_dir", str(tmp_path))
        content = make_bmp_bytes()
        async with async_client as client:
            response = await client.post(
                "/api/images/upload",
                params={"purpose": "test"},
                files={"file": ("OK_12.bmp", content, "image/bmp")},
            )
        assert response.status_code == 200
        data = response.json()
        assert data["label"] == "OK"
        assert data["index"] == 12

    @pytest.mark.anyio
    async def test_ok_1_jpeg(self, async_client, tmp_path, monkeypatch):
        monkeypatch.setattr("backend.routers.images.config.upload_dir", str(tmp_path))
        content = make_jpg_bytes()
        async with async_client as client:
            response = await client.post(
                "/api/images/upload",
                params={"purpose": "analysis"},
                files={"file": ("OK_1.jpeg", content, "image/jpeg")},
            )
        assert response.status_code == 200
        assert response.json()["label"] == "OK"

    @pytest.mark.anyio
    async def test_ok_1_tiff(self, async_client, tmp_path, monkeypatch):
        monkeypatch.setattr("backend.routers.images.config.upload_dir", str(tmp_path))
        img = np.zeros((100, 100, 3), dtype=np.uint8)
        success, encoded = cv2.imencode(".tiff", img)
        assert success
        content = encoded.tobytes()
        async with async_client as client:
            response = await client.post(
                "/api/images/upload",
                params={"purpose": "analysis"},
                files={"file": ("OK_1.tiff", content, "image/tiff")},
            )
        assert response.status_code == 200
        assert response.json()["label"] == "OK"


# --- Filename validation: invalid cases ---


class TestInvalidFilenames:
    """Test that invalid filenames are rejected with 422."""

    @pytest.mark.anyio
    async def test_lowercase_prefix(self, async_client, tmp_path, monkeypatch):
        monkeypatch.setattr("backend.routers.images.config.upload_dir", str(tmp_path))
        content = make_png_bytes()
        async with async_client as client:
            response = await client.post(
                "/api/images/upload",
                params={"purpose": "analysis"},
                files={"file": ("ok_1.png", content, "image/png")},
            )
        assert response.status_code == 422

    @pytest.mark.anyio
    async def test_zero_index(self, async_client, tmp_path, monkeypatch):
        monkeypatch.setattr("backend.routers.images.config.upload_dir", str(tmp_path))
        content = make_png_bytes()
        async with async_client as client:
            response = await client.post(
                "/api/images/upload",
                params={"purpose": "analysis"},
                files={"file": ("OK_0.png", content, "image/png")},
            )
        assert response.status_code == 422

    @pytest.mark.anyio
    async def test_negative_index(self, async_client, tmp_path, monkeypatch):
        monkeypatch.setattr("backend.routers.images.config.upload_dir", str(tmp_path))
        content = make_png_bytes()
        async with async_client as client:
            response = await client.post(
                "/api/images/upload",
                params={"purpose": "analysis"},
                files={"file": ("OK_-1.png", content, "image/png")},
            )
        assert response.status_code == 422

    @pytest.mark.anyio
    async def test_no_prefix(self, async_client, tmp_path, monkeypatch):
        monkeypatch.setattr("backend.routers.images.config.upload_dir", str(tmp_path))
        content = make_png_bytes()
        async with async_client as client:
            response = await client.post(
                "/api/images/upload",
                params={"purpose": "analysis"},
                files={"file": ("test.png", content, "image/png")},
            )
        assert response.status_code == 422

    @pytest.mark.anyio
    async def test_no_number(self, async_client, tmp_path, monkeypatch):
        monkeypatch.setattr("backend.routers.images.config.upload_dir", str(tmp_path))
        content = make_png_bytes()
        async with async_client as client:
            response = await client.post(
                "/api/images/upload",
                params={"purpose": "analysis"},
                files={"file": ("OK_.png", content, "image/png")},
            )
        assert response.status_code == 422

    @pytest.mark.anyio
    async def test_no_extension(self, async_client, tmp_path, monkeypatch):
        monkeypatch.setattr("backend.routers.images.config.upload_dir", str(tmp_path))
        content = make_png_bytes()
        async with async_client as client:
            response = await client.post(
                "/api/images/upload",
                params={"purpose": "analysis"},
                files={"file": ("OK_1", content, "application/octet-stream")},
            )
        assert response.status_code == 422

    @pytest.mark.anyio
    async def test_wrong_extension(self, async_client, tmp_path, monkeypatch):
        monkeypatch.setattr("backend.routers.images.config.upload_dir", str(tmp_path))
        content = make_png_bytes()
        async with async_client as client:
            response = await client.post(
                "/api/images/upload",
                params={"purpose": "analysis"},
                files={"file": ("OK_1.gif", content, "image/gif")},
            )
        assert response.status_code == 422

    @pytest.mark.anyio
    async def test_space_in_filename(self, async_client, tmp_path, monkeypatch):
        monkeypatch.setattr("backend.routers.images.config.upload_dir", str(tmp_path))
        content = make_png_bytes()
        async with async_client as client:
            response = await client.post(
                "/api/images/upload",
                params={"purpose": "analysis"},
                files={"file": ("OK 1.png", content, "image/png")},
            )
        assert response.status_code == 422


# --- Purpose validation ---


class TestPurposeValidation:
    """Test that invalid purpose values are rejected."""

    @pytest.mark.anyio
    async def test_invalid_purpose(self, async_client, tmp_path, monkeypatch):
        monkeypatch.setattr("backend.routers.images.config.upload_dir", str(tmp_path))
        content = make_png_bytes()
        async with async_client as client:
            response = await client.post(
                "/api/images/upload",
                params={"purpose": "invalid"},
                files={"file": ("OK_1.png", content, "image/png")},
            )
        assert response.status_code == 422
        assert "purpose" in response.json()["detail"].lower()


# --- File size validation ---


class TestFileSizeValidation:
    """Test that oversized files are rejected."""

    @pytest.mark.anyio
    async def test_file_exceeds_50mb(self, async_client, tmp_path, monkeypatch):
        monkeypatch.setattr("backend.routers.images.config.upload_dir", str(tmp_path))
        # Create content just over 50MB
        content = b"\x00" * (50 * 1024 * 1024 + 1)
        async with async_client as client:
            response = await client.post(
                "/api/images/upload",
                params={"purpose": "analysis"},
                files={"file": ("OK_1.png", content, "image/png")},
            )
        assert response.status_code == 422
        assert "size" in response.json()["detail"].lower()


# --- Image integrity validation ---


class TestImageIntegrity:
    """Test that corrupt/invalid image data is rejected."""

    @pytest.mark.anyio
    async def test_corrupt_image_data(self, async_client, tmp_path, monkeypatch):
        monkeypatch.setattr("backend.routers.images.config.upload_dir", str(tmp_path))
        content = b"this is not an image at all, just random text data"
        async with async_client as client:
            response = await client.post(
                "/api/images/upload",
                params={"purpose": "analysis"},
                files={"file": ("OK_1.png", content, "image/png")},
            )
        assert response.status_code == 422
        assert "image" in response.json()["detail"].lower()

    @pytest.mark.anyio
    async def test_random_bytes(self, async_client, tmp_path, monkeypatch):
        monkeypatch.setattr("backend.routers.images.config.upload_dir", str(tmp_path))
        rng = np.random.default_rng(42)
        content = rng.bytes(1024)
        async with async_client as client:
            response = await client.post(
                "/api/images/upload",
                params={"purpose": "analysis"},
                files={"file": ("NG_1.png", content, "image/png")},
            )
        assert response.status_code == 422


# --- Successful upload response ---


class TestUploadSuccess:
    """Test successful upload returns correct JSON and saves file."""

    @pytest.mark.anyio
    async def test_response_fields(self, async_client, tmp_path, monkeypatch):
        monkeypatch.setattr("backend.routers.images.config.upload_dir", str(tmp_path))
        content = make_png_bytes()
        async with async_client as client:
            response = await client.post(
                "/api/images/upload",
                params={"purpose": "analysis"},
                files={"file": ("OK_1.png", content, "image/png")},
            )
        assert response.status_code == 200
        data = response.json()
        # Check all required fields exist
        assert "id" in data
        assert "filename" in data
        assert "label" in data
        assert "index" in data
        assert "purpose" in data
        assert "path" in data
        # Validate id is a valid UUID
        uuid.UUID(data["id"])

    @pytest.mark.anyio
    async def test_file_saved_to_disk(self, async_client, tmp_path, monkeypatch):
        monkeypatch.setattr("backend.routers.images.config.upload_dir", str(tmp_path))
        content = make_png_bytes()
        async with async_client as client:
            response = await client.post(
                "/api/images/upload",
                params={"purpose": "analysis"},
                files={"file": ("OK_1.png", content, "image/png")},
            )
        assert response.status_code == 200
        saved_path = tmp_path / "analysis" / "OK_1.png"
        assert saved_path.exists()
        assert saved_path.read_bytes() == content

    @pytest.mark.anyio
    async def test_response_path_matches(self, async_client, tmp_path, monkeypatch):
        monkeypatch.setattr("backend.routers.images.config.upload_dir", str(tmp_path))
        content = make_png_bytes()
        async with async_client as client:
            response = await client.post(
                "/api/images/upload",
                params={"purpose": "analysis"},
                files={"file": ("OK_1.png", content, "image/png")},
            )
        data = response.json()
        expected_path = str(tmp_path / "analysis" / "OK_1.png")
        assert data["path"] == expected_path


# --- Purpose routing ---


class TestPurposeRouting:
    """Test that files are saved to the correct subdirectory based on purpose."""

    @pytest.mark.anyio
    async def test_analysis_subdirectory(self, async_client, tmp_path, monkeypatch):
        monkeypatch.setattr("backend.routers.images.config.upload_dir", str(tmp_path))
        content = make_png_bytes()
        async with async_client as client:
            response = await client.post(
                "/api/images/upload",
                params={"purpose": "analysis"},
                files={"file": ("OK_1.png", content, "image/png")},
            )
        assert response.status_code == 200
        assert response.json()["purpose"] == "analysis"
        assert (tmp_path / "analysis" / "OK_1.png").exists()

    @pytest.mark.anyio
    async def test_test_subdirectory(self, async_client, tmp_path, monkeypatch):
        monkeypatch.setattr("backend.routers.images.config.upload_dir", str(tmp_path))
        content = make_png_bytes()
        async with async_client as client:
            response = await client.post(
                "/api/images/upload",
                params={"purpose": "test"},
                files={"file": ("NG_5.png", content, "image/png")},
            )
        assert response.status_code == 200
        assert response.json()["purpose"] == "test"
        assert (tmp_path / "test" / "NG_5.png").exists()

    @pytest.mark.anyio
    async def test_directory_auto_created(self, async_client, tmp_path, monkeypatch):
        monkeypatch.setattr("backend.routers.images.config.upload_dir", str(tmp_path))
        # Ensure subdirectories don't exist yet
        assert not (tmp_path / "analysis").exists()
        content = make_png_bytes()
        async with async_client as client:
            response = await client.post(
                "/api/images/upload",
                params={"purpose": "analysis"},
                files={"file": ("OK_1.png", content, "image/png")},
            )
        assert response.status_code == 200
        assert (tmp_path / "analysis").is_dir()


# --- ImageValidator unit tests ---


class TestImageValidatorUnit:
    """Unit tests for the ImageValidator service."""

    def test_valid_ok_filename(self):
        from backend.services.image_validator import ImageValidator

        result = ImageValidator.validate_filename("OK_1.png")
        assert result.valid is True
        assert result.label == "OK"
        assert result.index == 1

    def test_valid_ng_filename(self):
        from backend.services.image_validator import ImageValidator

        result = ImageValidator.validate_filename("NG_99.jpg")
        assert result.valid is True
        assert result.label == "NG"
        assert result.index == 99

    def test_invalid_filename_returns_error(self):
        from backend.services.image_validator import ImageValidator

        result = ImageValidator.validate_filename("bad.png")
        assert result.valid is False
        assert result.error is not None

    def test_validate_extension_valid(self):
        from backend.services.image_validator import ImageValidator

        assert ImageValidator.validate_extension("OK_1.png") is True
        assert ImageValidator.validate_extension("OK_1.jpg") is True
        assert ImageValidator.validate_extension("OK_1.jpeg") is True
        assert ImageValidator.validate_extension("OK_1.bmp") is True
        assert ImageValidator.validate_extension("OK_1.tiff") is True

    def test_validate_extension_invalid(self):
        from backend.services.image_validator import ImageValidator

        assert ImageValidator.validate_extension("OK_1.gif") is False
        assert ImageValidator.validate_extension("OK_1.webp") is False
        assert ImageValidator.validate_extension("OK_1") is False

    def test_validate_image_integrity_valid(self):
        from backend.services.image_validator import ImageValidator

        content = make_png_bytes()
        assert ImageValidator.validate_image_integrity(content) is True

    def test_validate_image_integrity_invalid(self):
        from backend.services.image_validator import ImageValidator

        assert ImageValidator.validate_image_integrity(b"not an image") is False

    def test_validate_file_size_within_limit(self):
        from backend.services.image_validator import ImageValidator

        content = b"\x00" * 1024  # 1KB
        assert ImageValidator.validate_file_size(content) is True

    def test_validate_file_size_exceeds_limit(self):
        from backend.services.image_validator import ImageValidator

        content = b"\x00" * (50 * 1024 * 1024 + 1)  # 50MB + 1 byte
        assert ImageValidator.validate_file_size(content) is False
