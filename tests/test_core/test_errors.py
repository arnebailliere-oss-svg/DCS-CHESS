"""Tests for dcs_chess.core.errors (FR-C10)."""

import pytest

from dcs_chess.core import IllegalMoveError, InvalidMoveError, AmbiguousMoveError


class TestIllegalMoveError:
    def test_is_value_error(self):
        assert issubclass(IllegalMoveError, ValueError)

    def test_message_with_move(self):
        class FakeMove:
            def __str__(self):
                return "e2e4"
        class FakeBoard:
            def fen(self):
                return "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"

        err = IllegalMoveError(FakeMove(), FakeBoard())
        assert "e2e4" in str(err)

    def test_bare_message(self):
        err = IllegalMoveError()
        assert "illegal move" in str(err).lower()


class TestInvalidMoveError:
    def test_is_value_error(self):
        assert issubclass(InvalidMoveError, ValueError)

    def test_custom_message(self):
        err = InvalidMoveError("bad uci: xyz")
        assert "bad uci" in str(err)


class TestAmbiguousMoveError:
    def test_is_value_error(self):
        assert issubclass(AmbiguousMoveError, ValueError)

    def test_custom_message(self):
        err = AmbiguousMoveError("Nc3 is ambiguous")
        assert "ambiguous" in str(err).lower()
