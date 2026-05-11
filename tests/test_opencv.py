"""Step 2: OpenCV + NumPy installation and verification tests."""
import platform

import cv2
import numpy as np


class TestImports:
    """Verify OpenCV and NumPy import correctly."""

    def test_import_cv2(self):
        assert cv2 is not None

    def test_import_numpy(self):
        assert np is not None


class TestVersions:
    """Verify version strings are valid."""

    def test_cv2_version_format(self):
        version = cv2.__version__
        parts = version.split(".")
        assert len(parts) >= 2, f"Unexpected version format: {version}"
        assert parts[0].isdigit(), f"Major version not numeric: {version}"
        assert version.startswith("4."), f"Expected OpenCV 4.x.x, got {version}"

    def test_numpy_version_format(self):
        version = np.__version__
        parts = version.split(".")
        assert len(parts) >= 2, f"Unexpected version format: {version}"
        assert parts[0].isdigit(), f"Major version not numeric: {version}"


class TestImageCreation:
    """Verify basic image creation with NumPy."""

    def test_blank_color_image(self):
        img = np.zeros((100, 100, 3), dtype=np.uint8)
        assert img.shape == (100, 100, 3)
        assert img.dtype == np.uint8

    def test_grayscale_rectangle(self):
        img = np.zeros((100, 100), dtype=np.uint8)
        assert img[50, 50] == 0  # before drawing
        cv2.rectangle(img, (20, 20), (80, 80), 255, -1)
        assert img[50, 50] == 255  # inside rectangle
        assert img[0, 0] == 0  # outside rectangle


class TestColorConversion:
    """Verify color space conversion."""

    def test_bgr_to_grayscale(self):
        bgr = np.zeros((100, 100, 3), dtype=np.uint8)
        bgr[:, :] = (50, 100, 150)  # BGR values
        gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
        assert gray.shape == (100, 100), f"Expected (H, W), got {gray.shape}"
        assert len(gray.shape) == 2  # no channel dimension


class TestImageIO:
    """Verify image save/load round-trip."""

    def test_save_and_load(self, tmp_path):
        # Create image with known values
        img = np.zeros((50, 50, 3), dtype=np.uint8)
        img[10:40, 10:40] = (0, 0, 255)  # red square in BGR

        filepath = str(tmp_path / "test_image.png")
        result = cv2.imwrite(filepath, img)
        assert result is True, "imwrite failed"

        loaded = cv2.imread(filepath)
        assert loaded is not None, "imread returned None"
        assert loaded.shape == img.shape
        np.testing.assert_array_equal(loaded, img)


class TestGaussianBlur:
    """Verify Gaussian blur operation."""

    def test_blur_preserves_shape(self):
        img = np.random.randint(0, 256, (100, 100), dtype=np.uint8)
        blurred = cv2.GaussianBlur(img, (5, 5), 1.0)
        assert blurred.shape == img.shape
        assert blurred.dtype == img.dtype


class TestThreshold:
    """Verify binary threshold operation."""

    def test_binary_threshold(self):
        img = np.zeros((100, 100), dtype=np.uint8)
        img[:50, :] = 200  # top half bright
        img[50:, :] = 50  # bottom half dark

        maxval = 255
        _, binary = cv2.threshold(img, 127, maxval, cv2.THRESH_BINARY)

        unique_values = set(np.unique(binary))
        assert unique_values == {0, maxval}, f"Expected {{0, {maxval}}}, got {unique_values}"


class TestNumpyOpenCVInterop:
    """Verify NumPy array operations work with OpenCV images."""

    def test_elementwise_addition(self):
        img1 = np.full((50, 50), 100, dtype=np.uint8)
        img2 = np.full((50, 50), 50, dtype=np.uint8)
        result = cv2.add(img1, img2)
        assert result[0, 0] == 150

    def test_slicing(self):
        img = np.zeros((100, 100, 3), dtype=np.uint8)
        img[20:80, 20:80] = (255, 255, 255)
        roi = img[30:70, 30:70]
        assert roi.shape == (40, 40, 3)
        assert np.all(roi == 255)

    def test_boolean_indexing(self):
        img = np.zeros((100, 100), dtype=np.uint8)
        img[25:75, 25:75] = 200
        mask = img > 100
        img[mask] = 255
        assert img[50, 50] == 255
        assert img[0, 0] == 0


class TestArchitecture:
    """Verify Intel Mac x86_64 architecture (informational)."""

    def test_platform_x86_64(self):
        machine = platform.machine()
        if machine != "x86_64":
            import warnings
            warnings.warn(
                f"Expected x86_64 (Intel Mac), got '{machine}'. "
                "Tests may still pass but VIA targets Intel Mac."
            )
        # Always pass — this is informational
        assert machine in ("x86_64", "arm64", "AMD64"), f"Unknown arch: {machine}"
