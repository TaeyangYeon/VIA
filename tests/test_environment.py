"""Step 1: Environment verification tests."""
import sys
import importlib
from pathlib import Path


class TestPythonVersion:
    def test_python_major_minor(self):
        assert sys.version_info.major == 3
        assert sys.version_info.minor == 11


class TestDependencies:
    """All packages in requirements.txt must be importable."""

    def test_import_fastapi(self):
        importlib.import_module("fastapi")

    def test_import_uvicorn(self):
        importlib.import_module("uvicorn")

    def test_import_cv2(self):
        importlib.import_module("cv2")

    def test_import_numpy(self):
        importlib.import_module("numpy")

    def test_import_httpx(self):
        importlib.import_module("httpx")

    def test_import_structlog(self):
        importlib.import_module("structlog")

    def test_import_pytest(self):
        importlib.import_module("pytest")

    def test_import_pydantic(self):
        importlib.import_module("pydantic")


class TestProjectFiles:
    def test_python_version_file_exists(self):
        version_file = Path(__file__).resolve().parent.parent / ".python-version"
        assert version_file.exists(), ".python-version file not found"

    def test_python_version_file_content(self):
        version_file = Path(__file__).resolve().parent.parent / ".python-version"
        content = version_file.read_text().strip()
        assert content.startswith("3.11"), f"Expected 3.11.x, got {content}"
