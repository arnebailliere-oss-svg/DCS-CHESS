"""Module-level differential comparison: introspect and compare public names."""

from __future__ import annotations

import types
from typing import Any, Sequence

from tests.differential.compare import ComparisonResult, compare


def public_names(module: types.ModuleType, *, uppercase_only: bool = False) -> set[str]:
    """Return public names from a module (no leading underscore)."""
    names = {n for n in dir(module) if not n.startswith("_")}
    if uppercase_only:
        names = {n for n in names if n[0].isupper() or n.isupper()}
    return names


def compare_constants(
    dcs_module: types.ModuleType,
    ref_module: types.ModuleType,
    names: Sequence[str] | None = None,
) -> list[ComparisonResult]:
    """Compare constant values between DCS and reference modules.

    If *names* is None, compares all uppercase public names present in both.
    """
    if names is None:
        dcs_names = public_names(dcs_module, uppercase_only=True)
        ref_names = public_names(ref_module, uppercase_only=True)
        names = sorted(dcs_names & ref_names)

    results: list[ComparisonResult] = []
    for name in names:
        dcs_val = getattr(dcs_module, name, _MISSING)
        ref_val = getattr(ref_module, name, _MISSING)

        if dcs_val is _MISSING:
            results.append(ComparisonResult(
                name=name, passed=False,
                detail=f"missing from dcs_chess",
            ))
            continue
        if ref_val is _MISSING:
            results.append(ComparisonResult(
                name=name, passed=False,
                detail=f"missing from reference",
            ))
            continue

        if callable(dcs_val) and not isinstance(dcs_val, type):
            continue

        results.append(compare(dcs_val, ref_val, name=name))

    return results


def compare_modules(
    dcs_module: types.ModuleType,
    ref_module: types.ModuleType,
    names: Sequence[str] | None = None,
) -> list[ComparisonResult]:
    """Compare all matching public names between two modules.

    Returns ComparisonResult for each name — constants by value, callables
    flagged as present/absent (call-level comparison needs specific inputs).
    """
    if names is None:
        ref_names = public_names(ref_module)
        names = sorted(ref_names)

    results: list[ComparisonResult] = []
    for name in names:
        dcs_val = getattr(dcs_module, name, _MISSING)
        ref_val = getattr(ref_module, name, _MISSING)

        if dcs_val is _MISSING:
            results.append(ComparisonResult(
                name=name, passed=False,
                detail="missing from dcs_chess",
            ))
            continue

        if callable(ref_val) and not isinstance(ref_val, type):
            results.append(ComparisonResult(
                name=name, passed=True,
                detail="callable present (needs input-level comparison)",
            ))
        elif isinstance(ref_val, type):
            results.append(ComparisonResult(
                name=name,
                passed=isinstance(dcs_val, type),
                detail="" if isinstance(dcs_val, type) else "expected a class",
            ))
        else:
            results.append(compare(dcs_val, ref_val, name=name))

    return results


class _MissingSentinel:
    def __repr__(self) -> str:
        return "<MISSING>"

_MISSING = _MissingSentinel()
