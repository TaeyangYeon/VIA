"""Tests for CodeValidator — static analysis of AI-generated algorithm code."""
import dataclasses
import pytest

from agents.code_validator import ValidationResult, CodeValidator


# ── Fixtures ──────────────────────────────────────────────────────────────────

VALID_INSPECTION_CODE = """
import cv2
import numpy as np

def inspect_item(image):
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    return {"result": "OK", "details": {}}
"""

VALID_INSPECTION_CODE_TYPED = """
import cv2
import numpy as np

def inspect_item(image: np.ndarray):
    return {"result": "OK", "details": {}}
"""

VALID_ALIGN_CODE = """
import cv2
import numpy as np

def align(image):
    return {"x": 0.0, "y": 0.0, "confidence": 1.0, "method_used": "template"}
"""

VALID_ALIGN_CODE_TYPED = """
import cv2
import numpy as np

def align(image: np.ndarray):
    return {"x": 0.0, "y": 0.0, "confidence": 1.0, "method_used": "template"}
"""

MULTI_INSPECT_CODE = """
import cv2
import numpy as np

def inspect_item(image):
    return {"result": "OK", "details": {}}

def inspect_item(image):
    return {"result": "NG", "details": {}}
"""


# ── ValidationResult ──────────────────────────────────────────────────────────

class TestValidationResult:
    def test_is_dataclass(self):
        assert dataclasses.is_dataclass(ValidationResult)

    def test_fields_exist(self):
        result = ValidationResult(is_valid=True, errors=[], warnings=[])
        assert hasattr(result, "is_valid")
        assert hasattr(result, "errors")
        assert hasattr(result, "warnings")

    def test_valid_result(self):
        result = ValidationResult(is_valid=True, errors=[], warnings=[])
        assert result.is_valid is True
        assert result.errors == []
        assert result.warnings == []

    def test_invalid_result_has_errors(self):
        result = ValidationResult(is_valid=False, errors=["syntax error"], warnings=[])
        assert result.is_valid is False
        assert "syntax error" in result.errors

    def test_result_with_warnings(self):
        result = ValidationResult(is_valid=True, errors=[], warnings=["dangerous call"])
        assert result.is_valid is True
        assert len(result.warnings) == 1


# ── CodeValidator structure ───────────────────────────────────────────────────

class TestCodeValidatorStructure:
    def test_importable(self):
        from agents.code_validator import CodeValidator
        assert CodeValidator is not None

    def test_not_base_agent_subclass(self):
        from agents.base_agent import BaseAgent
        assert not issubclass(CodeValidator, BaseAgent)

    def test_has_validate_method(self):
        assert callable(getattr(CodeValidator(), "validate", None))

    def test_has_validate_syntax_method(self):
        assert callable(getattr(CodeValidator(), "validate_syntax", None))

    def test_has_validate_imports_method(self):
        assert callable(getattr(CodeValidator(), "validate_imports", None))

    def test_has_validate_functions_method(self):
        assert callable(getattr(CodeValidator(), "validate_functions", None))

    def test_validate_returns_validation_result(self):
        result = CodeValidator().validate(VALID_INSPECTION_CODE, mode="inspection")
        assert isinstance(result, ValidationResult)

    def test_validate_syntax_returns_validation_result(self):
        result = CodeValidator().validate_syntax(VALID_INSPECTION_CODE)
        assert isinstance(result, ValidationResult)

    def test_validate_imports_returns_validation_result(self):
        result = CodeValidator().validate_imports(VALID_INSPECTION_CODE)
        assert isinstance(result, ValidationResult)

    def test_validate_functions_returns_validation_result(self):
        result = CodeValidator().validate_functions(VALID_INSPECTION_CODE, mode="inspection")
        assert isinstance(result, ValidationResult)


# ── validate_syntax ───────────────────────────────────────────────────────────

class TestValidateSyntax:
    def test_valid_code_passes(self):
        result = CodeValidator().validate_syntax(VALID_INSPECTION_CODE)
        assert result.is_valid is True
        assert result.errors == []

    def test_empty_string_fails(self):
        result = CodeValidator().validate_syntax("")
        assert result.is_valid is False
        assert len(result.errors) > 0

    def test_whitespace_only_fails(self):
        result = CodeValidator().validate_syntax("   \n  ")
        assert result.is_valid is False
        assert len(result.errors) > 0

    def test_syntax_error_fails(self):
        result = CodeValidator().validate_syntax("def foo(:\n    pass")
        assert result.is_valid is False
        assert len(result.errors) > 0

    def test_syntax_error_message_is_informative(self):
        result = CodeValidator().validate_syntax("def foo(:\n    pass")
        assert any(
            kw in e.lower() for e in result.errors
            for kw in ("syntax", "invalid", "error", "parse")
        )

    def test_only_comments_passes_syntax(self):
        result = CodeValidator().validate_syntax("# just a comment\n# nothing else")
        assert result.is_valid is True

    def test_valid_align_code_passes(self):
        result = CodeValidator().validate_syntax(VALID_ALIGN_CODE)
        assert result.is_valid is True

    def test_incomplete_function_fails(self):
        result = CodeValidator().validate_syntax("def foo(")
        assert result.is_valid is False


# ── validate_imports ──────────────────────────────────────────────────────────

class TestValidateImports:
    def test_cv2_and_numpy_allowed(self):
        code = "import cv2\nimport numpy as np\ndef f(x): pass"
        result = CodeValidator().validate_imports(code)
        assert result.is_valid is True
        assert result.errors == []

    def test_os_import_rejected(self):
        code = "import cv2\nimport os\ndef f(x): pass"
        result = CodeValidator().validate_imports(code)
        assert result.is_valid is False
        assert len(result.errors) > 0

    def test_sys_import_rejected(self):
        result = CodeValidator().validate_imports("import sys\ndef f(x): pass")
        assert result.is_valid is False

    def test_subprocess_import_rejected(self):
        result = CodeValidator().validate_imports("import subprocess\ndef f(x): pass")
        assert result.is_valid is False

    def test_importlib_import_rejected(self):
        result = CodeValidator().validate_imports("import importlib\ndef f(x): pass")
        assert result.is_valid is False

    def test_from_os_import_rejected(self):
        result = CodeValidator().validate_imports("from os import path\ndef f(x): pass")
        assert result.is_valid is False

    def test_from_sys_import_rejected(self):
        result = CodeValidator().validate_imports("from sys import argv\ndef f(x): pass")
        assert result.is_valid is False

    def test_from_cv2_import_allowed(self):
        result = CodeValidator().validate_imports("from cv2 import imread\ndef f(x): pass")
        assert result.is_valid is True

    def test_from_numpy_import_allowed(self):
        result = CodeValidator().validate_imports("from numpy import array\ndef f(x): pass")
        assert result.is_valid is True

    def test_nested_import_inside_function_rejected(self):
        code = "def inspect_item(image):\n    import os\n    return {}"
        result = CodeValidator().validate_imports(code)
        assert result.is_valid is False

    def test_nested_from_import_inside_function_rejected(self):
        code = "def inspect_item(image):\n    from sys import argv\n    return {}"
        result = CodeValidator().validate_imports(code)
        assert result.is_valid is False

    def test_dunder_import_is_warning_not_error(self):
        code = (
            "import cv2\nimport numpy as np\n"
            "def f(x):\n    m = __import__('os')\n    return {}"
        )
        result = CodeValidator().validate_imports(code)
        assert result.errors == []
        assert len(result.warnings) > 0

    def test_exec_call_is_warning(self):
        code = "import cv2\ndef f(x):\n    exec('x = 1')\n    return {}"
        result = CodeValidator().validate_imports(code)
        assert any("exec" in w for w in result.warnings)

    def test_eval_call_is_warning(self):
        code = "import cv2\ndef f(x):\n    y = eval('1+1')\n    return {}"
        result = CodeValidator().validate_imports(code)
        assert any("eval" in w for w in result.warnings)

    def test_no_imports_is_valid(self):
        result = CodeValidator().validate_imports("def inspect_item(image):\n    return {}")
        assert result.is_valid is True

    def test_error_message_contains_module_name(self):
        result = CodeValidator().validate_imports("import subprocess\ndef f(x): pass")
        assert any("subprocess" in e for e in result.errors)

    def test_multiple_illegal_imports_all_reported(self):
        result = CodeValidator().validate_imports("import os\nimport sys\ndef f(x): pass")
        assert len(result.errors) >= 2

    def test_numpy_without_alias_allowed(self):
        result = CodeValidator().validate_imports("import numpy\ndef f(x): pass")
        assert result.is_valid is True


# ── validate_functions — inspection mode ──────────────────────────────────────

class TestValidateFunctionsInspection:
    def test_single_inspect_item_passes(self):
        result = CodeValidator().validate_functions(VALID_INSPECTION_CODE, mode="inspection")
        assert result.is_valid is True

    def test_typed_inspect_item_passes(self):
        result = CodeValidator().validate_functions(VALID_INSPECTION_CODE_TYPED, mode="inspection")
        assert result.is_valid is True

    def test_multiple_inspect_item_functions_valid(self):
        result = CodeValidator().validate_functions(MULTI_INSPECT_CODE, mode="inspection")
        assert result.is_valid is True

    def test_no_inspect_item_fails(self):
        code = "import cv2\ndef some_function(image):\n    return {}"
        result = CodeValidator().validate_functions(code, mode="inspection")
        assert result.is_valid is False
        assert len(result.errors) > 0

    def test_only_comments_fails(self):
        result = CodeValidator().validate_functions("# just comments", mode="inspection")
        assert result.is_valid is False

    def test_inspect_item_wrong_param_name_fails(self):
        code = "def inspect_item(img):\n    return {}"
        result = CodeValidator().validate_functions(code, mode="inspection")
        assert result.is_valid is False

    def test_inspect_item_extra_params_fails(self):
        code = "def inspect_item(image, threshold):\n    return {}"
        result = CodeValidator().validate_functions(code, mode="inspection")
        assert result.is_valid is False

    def test_inspect_item_no_params_fails(self):
        code = "def inspect_item():\n    return {}"
        result = CodeValidator().validate_functions(code, mode="inspection")
        assert result.is_valid is False

    def test_default_mode_is_inspection(self):
        result = CodeValidator().validate_functions(VALID_INSPECTION_CODE)
        assert result.is_valid is True


# ── validate_functions — align mode ──────────────────────────────────────────

class TestValidateFunctionsAlign:
    def test_single_align_function_passes(self):
        result = CodeValidator().validate_functions(VALID_ALIGN_CODE, mode="align")
        assert result.is_valid is True

    def test_typed_align_function_passes(self):
        result = CodeValidator().validate_functions(VALID_ALIGN_CODE_TYPED, mode="align")
        assert result.is_valid is True

    def test_no_align_function_fails(self):
        code = "def some_function(image):\n    return {}"
        result = CodeValidator().validate_functions(code, mode="align")
        assert result.is_valid is False

    def test_align_wrong_param_name_fails(self):
        code = "def align(img):\n    return {}"
        result = CodeValidator().validate_functions(code, mode="align")
        assert result.is_valid is False

    def test_align_extra_params_fails(self):
        code = "def align(image, scale):\n    return {}"
        result = CodeValidator().validate_functions(code, mode="align")
        assert result.is_valid is False

    def test_align_no_params_fails(self):
        code = "def align():\n    return {}"
        result = CodeValidator().validate_functions(code, mode="align")
        assert result.is_valid is False

    def test_inspection_code_in_align_mode_fails(self):
        result = CodeValidator().validate_functions(VALID_INSPECTION_CODE, mode="align")
        assert result.is_valid is False

    def test_only_comments_align_fails(self):
        result = CodeValidator().validate_functions("# nothing here", mode="align")
        assert result.is_valid is False


# ── validate (combined) ───────────────────────────────────────────────────────

class TestValidateCombined:
    def test_valid_inspection_code_passes_all(self):
        result = CodeValidator().validate(VALID_INSPECTION_CODE, mode="inspection")
        assert result.is_valid is True
        assert result.errors == []

    def test_valid_align_code_passes_all(self):
        result = CodeValidator().validate(VALID_ALIGN_CODE, mode="align")
        assert result.is_valid is True
        assert result.errors == []

    def test_syntax_error_makes_overall_invalid(self):
        result = CodeValidator().validate("def foo(:\n    pass", mode="inspection")
        assert result.is_valid is False
        assert len(result.errors) > 0

    def test_import_error_makes_overall_invalid(self):
        code = "import os\ndef inspect_item(image):\n    return {}"
        result = CodeValidator().validate(code, mode="inspection")
        assert result.is_valid is False

    def test_function_error_makes_overall_invalid(self):
        code = "import cv2\nimport numpy as np\ndef wrong_name(image):\n    return {}"
        result = CodeValidator().validate(code, mode="inspection")
        assert result.is_valid is False

    def test_import_and_function_errors_aggregated(self):
        code = "import os\ndef wrong_name(image):\n    return {}"
        result = CodeValidator().validate(code, mode="inspection")
        assert result.is_valid is False
        assert len(result.errors) >= 2

    def test_warnings_aggregated_in_combined(self):
        code = (
            "import cv2\nimport numpy as np\n"
            "def inspect_item(image):\n    eval('1')\n    return {}"
        )
        result = CodeValidator().validate(code, mode="inspection")
        assert len(result.warnings) > 0

    def test_default_mode_is_inspection(self):
        result = CodeValidator().validate(VALID_INSPECTION_CODE)
        assert result.is_valid is True

    def test_warnings_with_valid_code_is_still_valid(self):
        code = (
            "import cv2\nimport numpy as np\n"
            "def inspect_item(image):\n    __import__('os')\n    return {}"
        )
        result = CodeValidator().validate(code, mode="inspection")
        assert result.is_valid is True
        assert result.warnings

    def test_empty_string_fails_overall(self):
        result = CodeValidator().validate("", mode="inspection")
        assert result.is_valid is False


# ── Logging ───────────────────────────────────────────────────────────────────

class TestLogging:
    def setup_method(self):
        from backend.services.logger import via_logger
        via_logger.clear()

    def test_successful_validate_logs_info(self):
        from backend.services.logger import via_logger
        CodeValidator().validate(VALID_INSPECTION_CODE, mode="inspection")
        logs = via_logger.get_logs(agent="code_validator", level="INFO")
        assert len(logs) > 0

    def test_failed_validate_logs_error(self):
        from backend.services.logger import via_logger
        CodeValidator().validate("def wrong(x): pass", mode="inspection")
        logs = via_logger.get_logs(agent="code_validator", level="ERROR")
        assert len(logs) > 0

    def test_code_with_warnings_logs_warning(self):
        from backend.services.logger import via_logger
        code = (
            "import cv2\nimport numpy as np\n"
            "def inspect_item(image):\n    eval('1')\n    return {}"
        )
        CodeValidator().validate(code, mode="inspection")
        logs = via_logger.get_logs(agent="code_validator", level="WARNING")
        assert len(logs) > 0

    def test_successful_validate_does_not_log_error(self):
        from backend.services.logger import via_logger
        CodeValidator().validate(VALID_INSPECTION_CODE, mode="inspection")
        logs = via_logger.get_logs(agent="code_validator", level="ERROR")
        assert len(logs) == 0

    def test_agent_name_is_code_validator(self):
        from backend.services.logger import via_logger
        CodeValidator().validate(VALID_INSPECTION_CODE, mode="inspection")
        agents = via_logger.get_agents()
        assert "code_validator" in agents
