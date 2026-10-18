"""Differential tests for CORE-011: Error classes (FR-C10)."""

from __future__ import annotations

import chess as ref
import pytest

from dcs_chess.core.errors import (
    IllegalMoveError,
    InvalidMoveError,
    AmbiguousMoveError,
)


class TestErrorHierarchy:
    def test_illegal_is_valueerror(self):
        assert issubclass(IllegalMoveError, ValueError)
        assert issubclass(ref.IllegalMoveError, ValueError)

    def test_invalid_is_valueerror(self):
        assert issubclass(InvalidMoveError, ValueError)
        assert issubclass(ref.InvalidMoveError, ValueError)

    def test_ambiguous_is_valueerror(self):
        assert issubclass(AmbiguousMoveError, ValueError)
        assert issubclass(ref.AmbiguousMoveError, ValueError)


class TestErrorInstantiation:
    def test_illegal_move_error_basic(self):
        e = IllegalMoveError()
        assert isinstance(e, ValueError)
        assert "illegal" in str(e).lower() or "move" in str(e).lower()

    def test_invalid_move_error_basic(self):
        e = InvalidMoveError()
        assert isinstance(e, ValueError)

    def test_ambiguous_move_error_basic(self):
        e = AmbiguousMoveError()
        assert isinstance(e, ValueError)

    def test_illegal_can_be_caught_as_valueerror(self):
        with pytest.raises(ValueError):
            raise IllegalMoveError()

    def test_invalid_can_be_caught_as_valueerror(self):
        with pytest.raises(ValueError):
            raise InvalidMoveError()

    def test_ambiguous_can_be_caught_as_valueerror(self):
        with pytest.raises(ValueError):
            raise AmbiguousMoveError()
