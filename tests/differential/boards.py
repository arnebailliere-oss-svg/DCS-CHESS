"""Board-level differential comparison helpers.

Compare board states, move lists, and game predicates between dcs_chess
and the reference library on the same FEN positions.
"""

from __future__ import annotations

from typing import Any, Callable, Sequence

from tests.differential.compare import ComparisonResult, compare, CompareMode


def compare_board_state(
    dcs_board: Any,
    ref_board: Any,
    *,
    fen: str = "",
) -> list[ComparisonResult]:
    """Compare all observable board state between DCS and reference boards."""
    tag = f"[{fen}] " if fen else ""
    results: list[ComparisonResult] = []

    results.append(compare(
        dcs_board.fen(), ref_board.fen(),
        name=f"{tag}fen",
    ))
    results.append(compare(
        bool(dcs_board.turn), bool(ref_board.turn),
        name=f"{tag}turn",
    ))
    results.append(compare(
        int(dcs_board.castling_rights), int(ref_board.castling_rights),
        name=f"{tag}castling_rights",
    ))
    results.append(compare(
        dcs_board.ep_square, ref_board.ep_square,
        name=f"{tag}ep_square",
    ))
    results.append(compare(
        dcs_board.halfmove_clock, ref_board.halfmove_clock,
        name=f"{tag}halfmove_clock",
    ))
    results.append(compare(
        dcs_board.fullmove_number, ref_board.fullmove_number,
        name=f"{tag}fullmove_number",
    ))

    return results


def compare_move_lists(
    dcs_board: Any,
    ref_board: Any,
    *,
    fen: str = "",
    mode: CompareMode = "set",
) -> list[ComparisonResult]:
    """Compare legal/pseudo-legal move generation between boards."""
    tag = f"[{fen}] " if fen else ""
    results: list[ComparisonResult] = []

    dcs_legal = {m.uci() for m in dcs_board.legal_moves}
    ref_legal = {m.uci() for m in ref_board.legal_moves}
    results.append(compare(dcs_legal, ref_legal, name=f"{tag}legal_moves", mode="set"))

    dcs_pseudo = {m.uci() for m in dcs_board.pseudo_legal_moves}
    ref_pseudo = {m.uci() for m in ref_board.pseudo_legal_moves}
    results.append(compare(dcs_pseudo, ref_pseudo, name=f"{tag}pseudo_legal_moves", mode="set"))

    return results


def compare_predicates(
    dcs_board: Any,
    ref_board: Any,
    *,
    fen: str = "",
) -> list[ComparisonResult]:
    """Compare game-state predicates between boards."""
    tag = f"[{fen}] " if fen else ""
    results: list[ComparisonResult] = []

    predicate_names = [
        "is_check", "is_checkmate", "is_stalemate", "is_game_over",
        "is_insufficient_material", "is_seventyfive_moves",
        "is_fivefold_repetition", "can_claim_draw",
        "is_fifty_moves", "can_claim_fifty_moves",
        "can_claim_threefold_repetition",
        "is_valid",
    ]

    for name in predicate_names:
        dcs_fn = getattr(dcs_board, name, None)
        ref_fn = getattr(ref_board, name, None)
        if dcs_fn is None or ref_fn is None:
            results.append(ComparisonResult(
                name=f"{tag}{name}",
                passed=False,
                detail=f"{'dcs' if dcs_fn is None else 'ref'} missing {name}",
            ))
            continue
        try:
            results.append(compare(dcs_fn(), ref_fn(), name=f"{tag}{name}"))
        except Exception as exc:
            results.append(ComparisonResult(
                name=f"{tag}{name}",
                passed=False,
                detail=f"exception: {exc}",
            ))

    return results


def compare_notation(
    dcs_board: Any,
    ref_board: Any,
    ref_move: Any,
    dcs_move: Any,
    *,
    fen: str = "",
) -> list[ComparisonResult]:
    """Compare SAN, LAN, UCI, XBoard notation for a single move."""
    tag = f"[{fen}] " if fen else ""
    results: list[ComparisonResult] = []

    for fmt in ("san", "lan", "uci", "xboard"):
        dcs_fn = getattr(dcs_board, fmt, None)
        ref_fn = getattr(ref_board, fmt, None)
        if dcs_fn is None or ref_fn is None:
            continue
        try:
            results.append(compare(
                dcs_fn(dcs_move), ref_fn(ref_move),
                name=f"{tag}{fmt}({ref_move.uci()})",
            ))
        except Exception as exc:
            results.append(ComparisonResult(
                name=f"{tag}{fmt}({ref_move.uci()})",
                passed=False,
                detail=f"exception: {exc}",
            ))

    return results


def run_position_suite(
    fens: Sequence[str],
    dcs_board_cls: type,
    ref_board_cls: type,
    *,
    check_moves: bool = True,
    check_predicates: bool = True,
) -> list[ComparisonResult]:
    """Run differential comparison across a list of FEN positions."""
    results: list[ComparisonResult] = []
    for fen in fens:
        try:
            dcs_b = dcs_board_cls(fen)
        except Exception as exc:
            results.append(ComparisonResult(
                name=f"[{fen}] init",
                passed=False,
                detail=f"dcs_chess failed: {exc}",
            ))
            continue

        try:
            ref_b = ref_board_cls(fen)
        except Exception as exc:
            results.append(ComparisonResult(
                name=f"[{fen}] init",
                passed=False,
                detail=f"reference failed: {exc}",
            ))
            continue

        results.extend(compare_board_state(dcs_b, ref_b, fen=fen))

        if check_moves:
            results.extend(compare_move_lists(dcs_b, ref_b, fen=fen))

        if check_predicates:
            results.extend(compare_predicates(dcs_b, ref_b, fen=fen))

    return results
