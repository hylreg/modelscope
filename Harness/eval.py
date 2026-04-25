from __future__ import annotations

from dataclasses import dataclass

from .schema import HarnessTaskSpec


@dataclass(frozen=True)
class EvalResult:
    passed: bool
    total: int
    passed_checks: int
    failed_checks: list[str]


def evaluate_task(task: HarnessTaskSpec, output: str) -> EvalResult:
    failed: list[str] = []
    passed = 0
    for check in task.checks:
        if check.kind == "contains":
            ok = check.value in output
        elif check.kind == "equals":
            ok = output.strip() == check.value
        elif check.kind == "startswith":
            ok = output.startswith(check.value)
        else:
            ok = output.endswith(check.value)

        if ok:
            passed += 1
        else:
            failed.append(f"{check.kind}:{check.value}")

    return EvalResult(
        passed=passed == len(task.checks),
        total=len(task.checks),
        passed_checks=passed,
        failed_checks=failed,
    )

