"""Test agent for executing align mode code and computing coordinate metrics."""
from __future__ import annotations

import ast
import math
import re
from typing import Optional

import cv2
import numpy as np

from agents.base_agent import BaseAgent
from agents.models import ItemTestResult, TestMetrics

_GT_PATTERN = re.compile(r"X_([\d.]+)_Y_([\d.]+)_\d+\.\w+$")
_CRITERIA_PATTERN = re.compile(r"(coord_error|success_rate)\s*(>=|<=|>|<|==)\s*([0-9.]+)")
_DEFAULT_THRESHOLD = 2.0
_FAIL_ERROR = 9999.0


class TestAgentAlign(BaseAgent):
    def __init__(self, directive: Optional[str] = None) -> None:
        super().__init__("test_agent_align", directive)

    def execute(
        self,
        code: str,
        test_images: list[tuple[np.ndarray, str]],
        success_criteria: Optional[list[str]] = None,
    ) -> list[ItemTestResult]:
        if self._directive:
            self._log("INFO", f"Directive: {self._directive}")

        self._log("INFO", "Starting align test")

        align_fn = self._extract_align(code)
        if align_fn is None:
            return [ItemTestResult(
                item_id=0,
                item_name="align",
                passed=False,
                metrics=TestMetrics(accuracy=0.0, fp_rate=0.0, fn_rate=0.0,
                                    coord_error=0.0, success_rate=0.0),
                details="error: function_extraction_failed",
            )]

        metrics = self._compute_metrics(align_fn, test_images)
        passed = self._evaluate_criteria(success_criteria, metrics)
        self._log("INFO", "Completed align test", {"coord_error": metrics.coord_error})

        return [ItemTestResult(
            item_id=0,
            item_name="align",
            passed=passed,
            metrics=metrics,
        )]

    # ── Private helpers ───────────────────────────────────────────────────────

    def _extract_align(self, code: str):
        if not code.strip():
            self._log("WARNING", "Code is empty")
            return None
        try:
            tree = ast.parse(code)
        except SyntaxError as exc:
            self._log("WARNING", f"Code parse failed (SyntaxError): {exc}")
            return None

        ns: dict = {"np": np, "cv2": cv2}
        try:
            exec(code, ns)  # noqa: S102
        except Exception as exc:
            self._log("WARNING", f"Code exec failed: {exc}")
            return None

        fn = ns.get("align")
        if fn is None or not callable(fn):
            self._log("WARNING", "No callable 'align' function found in code")
            return None
        return fn

    def _compute_metrics(
        self, fn, test_images: list[tuple[np.ndarray, str]]
    ) -> TestMetrics:
        threshold = _DEFAULT_THRESHOLD
        errors: list[float] = []

        for image, filename in test_images:
            gt = self._parse_ground_truth(filename)
            if gt is None:
                self._log("WARNING", f"Filename '{filename}' does not match GT pattern — skipped")
                continue

            gt_x, gt_y = gt
            error = self._run_align(fn, image, gt_x, gt_y)
            errors.append(error)

        if not errors:
            return TestMetrics(accuracy=0.0, fp_rate=0.0, fn_rate=0.0,
                               coord_error=0.0, success_rate=0.0)

        coord_error = sum(errors) / len(errors)
        success_rate = sum(1 for e in errors if e < threshold) / len(errors)
        success_rate = max(0.0, min(1.0, success_rate))

        return TestMetrics(
            accuracy=0.0,
            fp_rate=0.0,
            fn_rate=0.0,
            coord_error=max(0.0, coord_error),
            success_rate=success_rate,
        )

    def _run_align(self, fn, image: np.ndarray, gt_x: float, gt_y: float) -> float:
        try:
            result = fn(image)
            pred_x = float(result.get("x", 0.0))
            pred_y = float(result.get("y", 0.0))
            return math.sqrt((pred_x - gt_x) ** 2 + (pred_y - gt_y) ** 2)
        except Exception:
            return _FAIL_ERROR

    def _parse_ground_truth(self, filename: str) -> Optional[tuple[float, float]]:
        m = _GT_PATTERN.search(filename)
        if not m:
            return None
        return float(m.group(1)), float(m.group(2))

    def _evaluate_criteria(
        self, criteria: Optional[list[str]], metrics: TestMetrics
    ) -> bool:
        if not criteria:
            coord_error = metrics.coord_error or 0.0
            success_rate = metrics.success_rate or 0.0
            return coord_error <= _DEFAULT_THRESHOLD and success_rate >= 0.9

        for criterion in criteria:
            m = _CRITERIA_PATTERN.match(criterion.strip())
            if not m:
                continue
            metric_name, op, value_str = m.groups()
            value = float(value_str)
            metric_val = float(getattr(metrics, metric_name, 0.0) or 0.0)
            ops = {
                ">=": metric_val >= value,
                "<=": metric_val <= value,
                ">": metric_val > value,
                "<": metric_val < value,
                "==": metric_val == value,
            }
            if not ops.get(op, False):
                return False
        return True
