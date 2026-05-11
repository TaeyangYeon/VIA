"""Test agent for executing inspection mode code and computing per-item metrics."""
from __future__ import annotations

import ast
import re
from typing import Optional

import cv2
import numpy as np

from agents.base_agent import BaseAgent
from agents.models import InspectionItem, InspectionPlan, ItemTestResult, TestMetrics


class TestAgentInspection(BaseAgent):
    def __init__(self, directive: Optional[str] = None) -> None:
        super().__init__("test_agent_inspection", directive)

    def execute(
        self,
        code: str,
        plan: InspectionPlan,
        test_images: list[tuple[np.ndarray, str]],
    ) -> list[ItemTestResult]:
        if self._directive:
            self._log("INFO", f"Directive: {self._directive}")

        if not plan.items:
            return []

        functions = self._extract_functions(code)
        results: dict[int, ItemTestResult] = {}

        for item in self._topological_sort(plan.items):
            if self._has_failed_dependency(item, results):
                results[item.id] = ItemTestResult(
                    item_id=item.id,
                    item_name=item.name,
                    passed=False,
                    metrics=TestMetrics(accuracy=0.0, fp_rate=0.0, fn_rate=0.0),
                    details="skipped: dependency_failed",
                )
                continue

            item_index = next(i for i, it in enumerate(plan.items) if it.id == item.id)

            if item_index >= len(functions) or functions[item_index] is None:
                self._log("WARNING", f"No function for item '{item.name}' (index {item_index})")
                results[item.id] = ItemTestResult(
                    item_id=item.id,
                    item_name=item.name,
                    passed=False,
                    metrics=TestMetrics(accuracy=0.0, fp_rate=0.0, fn_rate=0.0),
                    details="error: function_extraction_failed",
                )
                continue

            fn = functions[item_index]
            self._log("INFO", f"Starting test for item: {item.name}")
            metrics = self._compute_metrics(fn, test_images)
            passed = self._evaluate_criteria(item.success_criteria, metrics)
            self._log("INFO", f"Completed item: {item.name}", {"accuracy": metrics.accuracy})
            results[item.id] = ItemTestResult(
                item_id=item.id,
                item_name=item.name,
                passed=passed,
                metrics=metrics,
            )

        return [results[item.id] for item in plan.items]

    # ── Private helpers ───────────────────────────────────────────────────────

    def _extract_functions(self, code: str) -> list:
        if not code.strip():
            return []
        try:
            tree = ast.parse(code)
        except SyntaxError:
            self._log("WARNING", "Code parse failed (SyntaxError)")
            return []

        lines = code.splitlines(keepends=True)
        func_nodes = [n for n in tree.body if isinstance(n, ast.FunctionDef)]
        functions = []
        for idx, node in enumerate(func_nodes):
            start = node.lineno - 1
            end = func_nodes[idx + 1].lineno - 1 if idx + 1 < len(func_nodes) else len(lines)
            func_src = "".join(lines[start:end]).rstrip()
            ns: dict = {"np": np, "cv2": cv2}
            try:
                exec(func_src, ns)  # noqa: S102
                fn = ns.get(node.name)
                functions.append(fn if callable(fn) else None)
            except Exception as exc:
                self._log("WARNING", f"Failed to exec function '{node.name}': {exc}")
                functions.append(None)
        return functions

    def _compute_metrics(
        self, fn, test_images: list[tuple[np.ndarray, str]]
    ) -> TestMetrics:
        if not test_images:
            return TestMetrics(accuracy=0.0, fp_rate=0.0, fn_rate=0.0)

        total = len(test_images)
        correct = fp = fn_count = 0
        total_ok = sum(1 for _, f in test_images if f.startswith("OK_"))
        total_ng = sum(1 for _, f in test_images if f.startswith("NG_"))

        for image, filename in test_images:
            expected = self._ground_truth(filename)
            predicted = self._predict(fn, image, expected)
            if predicted == expected:
                correct += 1
            elif expected == "OK":
                fp += 1
            elif expected == "NG":
                fn_count += 1

        accuracy = max(0.0, min(1.0, correct / total))
        fp_rate = max(0.0, min(1.0, fp / total_ok)) if total_ok > 0 else 0.0
        fn_rate = max(0.0, min(1.0, fn_count / total_ng)) if total_ng > 0 else 0.0
        return TestMetrics(accuracy=accuracy, fp_rate=fp_rate, fn_rate=fn_rate)

    def _predict(self, fn, image: np.ndarray, expected: str) -> str:
        try:
            result = fn(image)
            return result.get("result", "NG")
        except Exception:
            return "NG" if expected == "OK" else "OK"

    def _ground_truth(self, filename: str) -> str:
        if filename.startswith("OK_"):
            return "OK"
        if filename.startswith("NG_"):
            return "NG"
        return "UNKNOWN"

    def _evaluate_criteria(self, criteria: str, metrics: TestMetrics) -> bool:
        if not criteria.strip():
            return (metrics.accuracy or 0.0) >= 0.8
        pattern = r"(accuracy|fp_rate|fn_rate)\s*(>=|<=|>|<|==)\s*([0-9.]+)"
        m = re.match(pattern, criteria.strip())
        if not m:
            return (metrics.accuracy or 0.0) >= 0.8
        metric_name, op, value_str = m.groups()
        value = float(value_str)
        metric_val = getattr(metrics, metric_name, 0.0) or 0.0
        ops = {">=": metric_val >= value, "<=": metric_val <= value,
               ">": metric_val > value, "<": metric_val < value, "==": metric_val == value}
        return ops.get(op, False)

    def _topological_sort(self, items: list[InspectionItem]) -> list[InspectionItem]:
        in_degree = {item.id: 0 for item in items}
        for item in items:
            for dep_id in item.depends_on:
                if dep_id in in_degree:
                    in_degree[item.id] += 1

        queue = [item for item in items if in_degree[item.id] == 0]
        result: list[InspectionItem] = []
        while queue:
            node = queue.pop(0)
            result.append(node)
            for other in items:
                if node.id in other.depends_on:
                    in_degree[other.id] -= 1
                    if in_degree[other.id] == 0:
                        queue.append(other)

        # Append any remaining items (cycles or missing deps)
        processed = {item.id for item in result}
        for item in items:
            if item.id not in processed:
                result.append(item)
        return result

    def _has_failed_dependency(
        self, item: InspectionItem, results: dict[int, ItemTestResult]
    ) -> bool:
        return any(
            results[dep_id].passed is False
            for dep_id in item.depends_on
            if dep_id in results
        )
