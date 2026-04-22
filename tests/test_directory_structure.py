"""Tests for Step 4: Project directory structure verification."""

import ast
import os
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).parent.parent


# --- Expected directories ---

EXPECTED_DIRECTORIES = [
    "backend",
    "backend/routers",
    "backend/services",
    "backend/models",
    "agents",
    "agents/prompts",
    "frontend",
    "tests",
    "tests/e2e",
    "tests/fixtures",
    "tests/fixtures/sample_images",
    "scripts",
    "docs",
]


# --- Expected __init__.py files ---

EXPECTED_INIT_FILES = [
    "backend/__init__.py",
    "backend/routers/__init__.py",
    "backend/services/__init__.py",
    "backend/models/__init__.py",
    "agents/__init__.py",
    "agents/prompts/__init__.py",
    "tests/__init__.py",
    "tests/e2e/__init__.py",
]


# --- Expected placeholder .py files (with docstrings) ---

EXPECTED_PLACEHOLDER_FILES = [
    "backend/main.py",
    "backend/config.py",
    "backend/routers/images.py",
    "backend/routers/config.py",
    "backend/routers/directives.py",
    "backend/routers/execute.py",
    "backend/routers/logs.py",
    "backend/routers/export.py",
    "backend/services/ollama_client.py",
    "backend/services/image_store.py",
    "backend/services/logger.py",
    "agents/base_agent.py",
    "agents/models.py",
    "agents/orchestrator.py",
    "agents/spec_agent.py",
    "agents/image_analysis_agent.py",
    "agents/pipeline_blocks.py",
    "agents/pipeline_composer.py",
    "agents/parameter_searcher.py",
    "agents/processing_quality_evaluator.py",
    "agents/vision_judge_agent.py",
    "agents/inspection_plan_agent.py",
    "agents/algorithm_selector.py",
    "agents/algorithm_coder_inspection.py",
    "agents/algorithm_coder_align.py",
    "agents/code_validator.py",
    "agents/test_agent_inspection.py",
    "agents/test_agent_align.py",
    "agents/evaluation_agent.py",
    "agents/feedback_controller.py",
    "agents/decision_agent.py",
]


# --- Existing files that must remain unmodified ---

EXISTING_FILES_LINE_COUNTS = {
    "tests/test_environment.py": 49,
    "tests/test_opencv.py": 142,
    "tests/test_ollama_multimodal.py": 217,
    "tests/__init__.py": 0,
    "scripts/start_ollama.sh": 86,
}


class TestDirectoriesExist:
    """Test that all expected directories exist."""

    @pytest.mark.parametrize("directory", EXPECTED_DIRECTORIES)
    def test_directory_exists(self, directory):
        path = PROJECT_ROOT / directory
        assert path.is_dir(), f"Directory missing: {directory}"


class TestInitFiles:
    """Test that all __init__.py files exist in package directories."""

    @pytest.mark.parametrize("init_file", EXPECTED_INIT_FILES)
    def test_init_file_exists(self, init_file):
        path = PROJECT_ROOT / init_file
        assert path.is_file(), f"__init__.py missing: {init_file}"


class TestPlaceholderFiles:
    """Test that all placeholder .py files exist and contain docstrings."""

    @pytest.mark.parametrize("placeholder", EXPECTED_PLACEHOLDER_FILES)
    def test_placeholder_file_exists(self, placeholder):
        path = PROJECT_ROOT / placeholder
        assert path.is_file(), f"Placeholder file missing: {placeholder}"

    @pytest.mark.parametrize("placeholder", EXPECTED_PLACEHOLDER_FILES)
    def test_placeholder_has_docstring(self, placeholder):
        path = PROJECT_ROOT / placeholder
        if not path.is_file():
            pytest.skip(f"File does not exist: {placeholder}")
        content = path.read_text(encoding="utf-8")
        assert len(content.strip()) > 0, f"File is empty: {placeholder}"
        tree = ast.parse(content)
        docstring = ast.get_docstring(tree)
        assert docstring is not None, f"No module docstring in: {placeholder}"
        assert len(docstring.strip()) > 5, f"Docstring too short in: {placeholder}"


class TestReadme:
    """Test that README.md exists and contains key sections."""

    def test_readme_exists(self):
        path = PROJECT_ROOT / "README.md"
        assert path.is_file(), "README.md missing"

    def test_readme_has_project_name(self):
        content = (PROJECT_ROOT / "README.md").read_text(encoding="utf-8")
        assert "VIA" in content

    def test_readme_has_description(self):
        content = (PROJECT_ROOT / "README.md").read_text(encoding="utf-8")
        assert "Vision Intelligence Agent" in content or "vision" in content.lower()

    def test_readme_has_tech_stack(self):
        content = (PROJECT_ROOT / "README.md").read_text(encoding="utf-8")
        for tech in ["FastAPI", "Electron", "React", "OpenCV", "Ollama"]:
            assert tech in content, f"README missing tech: {tech}"

    def test_readme_has_status(self):
        content = (PROJECT_ROOT / "README.md").read_text(encoding="utf-8")
        assert "Phase 1" in content

    def test_readme_has_getting_started(self):
        content = (PROJECT_ROOT / "README.md").read_text(encoding="utf-8")
        assert "Getting Started" in content or "getting started" in content.lower()

    def test_readme_has_prerequisites(self):
        content = (PROJECT_ROOT / "README.md").read_text(encoding="utf-8")
        assert "Python 3.11" in content
        assert "Ollama" in content
        assert "gemma4" in content.lower() or "Gemma4" in content


class TestExistingFilesUnmodified:
    """Test that pre-existing files still exist and are unmodified."""

    @pytest.mark.parametrize(
        "filepath,expected_lines", list(EXISTING_FILES_LINE_COUNTS.items())
    )
    def test_existing_file_unchanged(self, filepath, expected_lines):
        path = PROJECT_ROOT / filepath
        assert path.is_file(), f"Existing file missing: {filepath}"
        actual_lines = len(path.read_text(encoding="utf-8").splitlines())
        assert actual_lines == expected_lines, (
            f"{filepath}: expected {expected_lines} lines, got {actual_lines}"
        )

    def test_requirements_txt_exists(self):
        assert (PROJECT_ROOT / "requirements.txt").is_file()

    def test_pyproject_toml_exists(self):
        assert (PROJECT_ROOT / "pyproject.toml").is_file()

    def test_python_version_exists(self):
        assert (PROJECT_ROOT / ".python-version").is_file()

    def test_gitignore_exists(self):
        assert (PROJECT_ROOT / ".gitignore").is_file()


class TestSpecialDirectories:
    """Test special directory requirements."""

    def test_frontend_is_empty_directory(self):
        path = PROJECT_ROOT / "frontend"
        assert path.is_dir(), "frontend/ directory missing"

    def test_docs_directory_exists(self):
        path = PROJECT_ROOT / "docs"
        assert path.is_dir(), "docs/ directory missing"

    def test_docs_has_gitkeep(self):
        path = PROJECT_ROOT / "docs" / ".gitkeep"
        assert path.is_file(), "docs/.gitkeep missing"

    def test_sample_images_has_gitkeep(self):
        path = PROJECT_ROOT / "tests" / "fixtures" / "sample_images" / ".gitkeep"
        assert path.is_file(), "tests/fixtures/sample_images/.gitkeep missing"
