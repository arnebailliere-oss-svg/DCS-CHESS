"""Differential tests for CORE-010: Status, Termination, Outcome (FR-C9)."""

from __future__ import annotations

import chess as ref
import pytest

from dcs_chess.core.status import Status, Termination, Outcome


class TestStatus:
    def test_valid_is_zero(self):
        assert Status.VALID == 0
        assert ref.STATUS_VALID == 0

    _FLAG_NAMES = [
        "NO_WHITE_KING", "NO_BLACK_KING", "TOO_MANY_KINGS",
        "TOO_MANY_WHITE_PAWNS", "TOO_MANY_BLACK_PAWNS",
        "PAWNS_ON_BACKRANK", "TOO_MANY_WHITE_PIECES",
        "TOO_MANY_BLACK_PIECES", "BAD_CASTLING_RIGHTS",
        "INVALID_EP_SQUARE", "OPPOSITE_CHECK", "EMPTY",
        "RACE_CHECK", "RACE_OVER", "RACE_MATERIAL",
        "TOO_MANY_CHECKERS", "IMPOSSIBLE_CHECK",
    ]

    @pytest.mark.parametrize("name", _FLAG_NAMES)
    def test_flag_value_matches(self, name: str):
        dcs_val = getattr(Status, name).value
        ref_val = getattr(ref, f"STATUS_{name}")
        assert dcs_val == ref_val, f"Status.{name}: dcs={dcs_val}, ref={ref_val}"

    def test_flags_compose(self):
        combined = Status.NO_WHITE_KING | Status.TOO_MANY_KINGS
        assert int(combined) == (ref.STATUS_NO_WHITE_KING | ref.STATUS_TOO_MANY_KINGS)


class TestTermination:
    _NAMES = [
        "CHECKMATE", "STALEMATE", "INSUFFICIENT_MATERIAL",
        "SEVENTYFIVE_MOVES", "FIVEFOLD_REPETITION",
        "FIFTY_MOVES", "THREEFOLD_REPETITION",
        "VARIANT_WIN", "VARIANT_LOSS", "VARIANT_DRAW",
    ]

    @pytest.mark.parametrize("name", _NAMES)
    def test_termination_exists(self, name: str):
        assert hasattr(Termination, name)
        assert hasattr(ref.Termination, name)

    @pytest.mark.parametrize("name", _NAMES)
    def test_termination_value_matches(self, name: str):
        dcs_val = getattr(Termination, name).value
        ref_val = getattr(ref.Termination, name).value
        assert dcs_val == ref_val, f"Termination.{name}: dcs={dcs_val}, ref={ref_val}"


class TestOutcome:
    def test_white_wins(self):
        d = Outcome(Termination.CHECKMATE, True)
        r = ref.Outcome(ref.Termination.CHECKMATE, True)
        assert d.result() == r.result() == "1-0"

    def test_black_wins(self):
        d = Outcome(Termination.CHECKMATE, False)
        r = ref.Outcome(ref.Termination.CHECKMATE, False)
        assert d.result() == r.result() == "0-1"

    def test_draw(self):
        d = Outcome(Termination.STALEMATE, None)
        r = ref.Outcome(ref.Termination.STALEMATE, None)
        assert d.result() == r.result() == "1/2-1/2"

    def test_equality(self):
        a = Outcome(Termination.CHECKMATE, True)
        b = Outcome(Termination.CHECKMATE, True)
        assert a == b

    def test_inequality(self):
        a = Outcome(Termination.CHECKMATE, True)
        b = Outcome(Termination.CHECKMATE, False)
        assert a != b
