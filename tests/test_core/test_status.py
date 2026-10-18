"""Tests for dcs_chess.core.status (FR-C9) — differential against python-chess."""

import chess as ref
import pytest

from dcs_chess.core import Status, Termination, Outcome


class TestStatus:
    def test_valid_is_zero(self):
        assert Status.VALID == 0

    def test_flags_are_powers_of_two(self):
        for member in Status:
            if member.value != 0:
                assert member.value & (member.value - 1) == 0

    def test_combinable(self):
        combined = Status.NO_WHITE_KING | Status.NO_BLACK_KING
        assert Status.NO_WHITE_KING in combined
        assert Status.NO_BLACK_KING in combined

    @pytest.mark.parametrize("name", [
        "NO_WHITE_KING", "NO_BLACK_KING", "TOO_MANY_KINGS",
        "TOO_MANY_WHITE_PAWNS", "TOO_MANY_BLACK_PAWNS",
        "PAWNS_ON_BACKRANK", "TOO_MANY_WHITE_PIECES",
        "TOO_MANY_BLACK_PIECES", "BAD_CASTLING_RIGHTS",
        "INVALID_EP_SQUARE", "OPPOSITE_CHECK", "EMPTY",
        "RACE_CHECK", "RACE_OVER", "RACE_MATERIAL",
        "TOO_MANY_CHECKERS", "IMPOSSIBLE_CHECK",
    ])
    def test_flag_value_matches_reference(self, name: str):
        dcs_val = Status[name].value
        ref_val = getattr(ref, f"STATUS_{name}")
        assert dcs_val == ref_val, f"Status.{name}: dcs={dcs_val}, ref={ref_val}"


class TestTermination:
    @pytest.mark.parametrize("name", [
        "CHECKMATE", "STALEMATE", "INSUFFICIENT_MATERIAL",
        "SEVENTYFIVE_MOVES", "FIVEFOLD_REPETITION",
        "FIFTY_MOVES", "THREEFOLD_REPETITION",
        "VARIANT_WIN", "VARIANT_LOSS", "VARIANT_DRAW",
    ])
    def test_termination_value_matches_reference(self, name: str):
        dcs_val = Termination[name].value
        ref_val = ref.Termination[name].value
        assert dcs_val == ref_val, f"Termination.{name}: dcs={dcs_val}, ref={ref_val}"


class TestOutcome:
    def test_white_wins(self):
        o = Outcome(Termination.CHECKMATE, winner=True)
        assert o.result() == "1-0"

    def test_black_wins(self):
        o = Outcome(Termination.CHECKMATE, winner=False)
        assert o.result() == "0-1"

    def test_draw(self):
        o = Outcome(Termination.STALEMATE, winner=None)
        assert o.result() == "1/2-1/2"

    def test_equality(self):
        a = Outcome(Termination.CHECKMATE, True)
        b = Outcome(Termination.CHECKMATE, True)
        assert a == b

    def test_inequality(self):
        a = Outcome(Termination.CHECKMATE, True)
        b = Outcome(Termination.STALEMATE, None)
        assert a != b

    def test_hashable(self):
        o = Outcome(Termination.CHECKMATE, True)
        s = {o}
        assert len(s) == 1
