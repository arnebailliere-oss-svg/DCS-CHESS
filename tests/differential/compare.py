"""Core comparison utilities for differential testing.

Supports exact, set-equality, and approximate comparison modes as requested
by ADV for different output types (integers, move lists, float scores).
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Callable, Literal, Sequence


CompareMode = Literal["exact", "set", "approx"]


@dataclass
class ComparisonResult:
    """Result of a single differential comparison."""

    name: str
    passed: bool
    dcs_value: Any = None
    ref_value: Any = None
    mode: CompareMode = "exact"
    detail: str = ""

    def __bool__(self) -> bool:
        return self.passed

    def __repr__(self) -> str:
        status = "PASS" if self.passed else "FAIL"
        s = f"<{status} {self.name}"
        if not self.passed and self.detail:
            s += f": {self.detail}"
        return s + ">"


def compare(
    dcs_result: Any,
    ref_result: Any,
    *,
    mode: CompareMode = "exact",
    name: str = "",
    rtol: float = 1e-9,
    atol: float = 0.0,
) -> ComparisonResult:
    """Compare a DCS result against the reference library result.

    Modes:
        exact  — ``dcs_result == ref_result`` (default)
        set    — both converted to sets, order-independent comparison
        approx — numeric closeness via ``math.isclose(rtol, atol)``
    """
    if mode == "exact":
        passed = dcs_result == ref_result
        detail = "" if passed else f"dcs={dcs_result!r} != ref={ref_result!r}"
    elif mode == "set":
        dcs_set = set(dcs_result) if not isinstance(dcs_result, set) else dcs_result
        ref_set = set(ref_result) if not isinstance(ref_result, set) else ref_result
        passed = dcs_set == ref_set
        if not passed:
            missing = ref_set - dcs_set
            extra = dcs_set - ref_set
            parts = []
            if missing:
                parts.append(f"missing={missing}")
            if extra:
                parts.append(f"extra={extra}")
            detail = "; ".join(parts)
        else:
            detail = ""
    elif mode == "approx":
        try:
            if isinstance(dcs_result, (list, tuple)):
                passed = len(dcs_result) == len(ref_result) and all(
                    math.isclose(a, b, rel_tol=rtol, abs_tol=atol)
                    for a, b in zip(dcs_result, ref_result)
                )
            else:
                passed = math.isclose(
                    dcs_result, ref_result, rel_tol=rtol, abs_tol=atol
                )
            detail = "" if passed else f"dcs={dcs_result!r} !~ ref={ref_result!r}"
        except TypeError:
            passed = dcs_result == ref_result
            detail = "" if passed else f"dcs={dcs_result!r} != ref={ref_result!r}"
    else:
        raise ValueError(f"Unknown comparison mode: {mode!r}")

    return ComparisonResult(
        name=name,
        passed=passed,
        dcs_value=dcs_result,
        ref_value=ref_result,
        mode=mode,
        detail=detail,
    )


def compare_all(
    results: Sequence[ComparisonResult],
) -> tuple[list[ComparisonResult], list[ComparisonResult]]:
    """Split results into (passed, failed) lists."""
    passed = [r for r in results if r.passed]
    failed = [r for r in results if not r.passed]
    return passed, failed
