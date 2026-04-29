"""Code validator for static analysis of generated algorithm code."""
import ast
from dataclasses import dataclass, field

from backend.services.logger import via_logger

_ALLOWED_MODULES = {"cv2", "numpy"}
_DANGEROUS_CALLS = {"__import__", "exec", "eval"}


@dataclass
class ValidationResult:
    is_valid: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


class CodeValidator:
    def validate(self, code: str, mode: str = "inspection") -> ValidationResult:
        all_errors: list[str] = []
        all_warnings: list[str] = []

        syntax = self.validate_syntax(code)
        all_errors.extend(syntax.errors)
        all_warnings.extend(syntax.warnings)

        if syntax.is_valid:
            imports = self.validate_imports(code)
            all_errors.extend(imports.errors)
            all_warnings.extend(imports.warnings)

            functions = self.validate_functions(code, mode=mode)
            all_errors.extend(functions.errors)
            all_warnings.extend(functions.warnings)

        is_valid = len(all_errors) == 0
        result = ValidationResult(is_valid=is_valid, errors=all_errors, warnings=all_warnings)

        if not is_valid:
            via_logger.log("code_validator", "ERROR", "Code validation failed",
                           {"errors": all_errors, "mode": mode})
        elif all_warnings:
            via_logger.log("code_validator", "WARNING", "Code has warnings",
                           {"warnings": all_warnings, "mode": mode})
        else:
            via_logger.log("code_validator", "INFO", "Code validation passed",
                           {"mode": mode})

        return result

    def validate_syntax(self, code: str) -> ValidationResult:
        if not code.strip():
            return ValidationResult(is_valid=False, errors=["syntax error: empty code"])
        try:
            ast.parse(code)
            return ValidationResult(is_valid=True)
        except SyntaxError as exc:
            return ValidationResult(is_valid=False, errors=[f"syntax error: {exc}"])

    def validate_imports(self, code: str) -> ValidationResult:
        try:
            tree = ast.parse(code)
        except SyntaxError as exc:
            return ValidationResult(is_valid=False, errors=[f"cannot parse code: {exc}"])

        errors: list[str] = []
        warnings: list[str] = []

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    module = alias.name.split(".")[0]
                    if module not in _ALLOWED_MODULES:
                        errors.append(f"forbidden import: {alias.name}")
            elif isinstance(node, ast.ImportFrom):
                module = (node.module or "").split(".")[0]
                if module not in _ALLOWED_MODULES:
                    errors.append(f"forbidden import: from {node.module} import ...")
            elif isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name) and node.func.id in _DANGEROUS_CALLS:
                    warnings.append(f"dangerous call: {node.func.id}()")

        return ValidationResult(is_valid=len(errors) == 0, errors=errors, warnings=warnings)

    def validate_functions(self, code: str, mode: str = "inspection") -> ValidationResult:
        try:
            tree = ast.parse(code)
        except SyntaxError as exc:
            return ValidationResult(is_valid=False,
                                    errors=[f"cannot parse code for function validation: {exc}"])

        if mode == "inspection":
            return self._check_inspect_item(tree)
        if mode == "align":
            return self._check_align(tree)
        return ValidationResult(is_valid=True)

    # ── private helpers ───────────────────────────────────────────────────────

    @staticmethod
    def _valid_single_image_param(func_def: ast.FunctionDef) -> bool:
        args = func_def.args
        all_args = args.posonlyargs + args.args + args.kwonlyargs
        return (
            len(all_args) == 1
            and all_args[0].arg == "image"
            and args.vararg is None
            and args.kwarg is None
        )

    def _check_inspect_item(self, tree: ast.AST) -> ValidationResult:
        valid = [
            node for node in ast.walk(tree)
            if isinstance(node, ast.FunctionDef)
            and node.name == "inspect_item"
            and self._valid_single_image_param(node)
        ]
        if not valid:
            return ValidationResult(
                is_valid=False,
                errors=["no valid inspect_item(image) function found"],
            )
        return ValidationResult(is_valid=True)

    def _check_align(self, tree: ast.AST) -> ValidationResult:
        valid = [
            node for node in ast.walk(tree)
            if isinstance(node, ast.FunctionDef)
            and node.name == "align"
            and self._valid_single_image_param(node)
        ]
        if not valid:
            return ValidationResult(
                is_valid=False,
                errors=["no valid align(image) function found"],
            )
        return ValidationResult(is_valid=True)
