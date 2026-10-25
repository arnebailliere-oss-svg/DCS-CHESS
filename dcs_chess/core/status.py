"""FR-C9: Status, Termination, and Outcome types."""

from __future__ import annotations

import enum
from typing import Optional


class Status(enum.IntFlag):
    """Board validity status as a combination of flags.

    STATUS_VALID is 0; any non-zero value indicates at least one problem.
    Flag values follow the FR-C9 specification for interface compatibility.
    """

    VALID = 0
    NO_WHITE_KING = 1 << 0
    NO_BLACK_KING = 1 << 1
    TOO_MANY_KINGS = 1 << 2
    TOO_MANY_WHITE_PAWNS = 1 << 3
    TOO_MANY_BLACK_PAWNS = 1 << 4
    PAWNS_ON_BACKRANK = 1 << 5
    TOO_MANY_WHITE_PIECES = 1 << 6
    TOO_MANY_BLACK_PIECES = 1 << 7
    BAD_CASTLING_RIGHTS = 1 << 8
    INVALID_EP_SQUARE = 1 << 9
    OPPOSITE_CHECK = 1 << 10
    EMPTY = 1 << 11
    RACE_CHECK = 1 << 12
    RACE_OVER = 1 << 13
    RACE_MATERIAL = 1 << 14
    TOO_MANY_CHECKERS = 1 << 15
    IMPOSSIBLE_CHECK = 1 << 16


class Termination(enum.Enum):
    """Reason a game ended."""

    CHECKMATE = enum.auto()
    STALEMATE = enum.auto()
    INSUFFICIENT_MATERIAL = enum.auto()
    SEVENTYFIVE_MOVES = enum.auto()
    FIVEFOLD_REPETITION = enum.auto()
    FIFTY_MOVES = enum.auto()
    THREEFOLD_REPETITION = enum.auto()
    VARIANT_WIN = enum.auto()
    VARIANT_LOSS = enum.auto()
    VARIANT_DRAW = enum.auto()


class Outcome:
    """The outcome of a game: a termination reason and an optional winner."""

    def __init__(self, termination: Termination, winner: Optional[bool]) -> None:
        self.termination = termination
        self.winner = winner

    def result(self) -> str:
        """Return ``'1-0'``, ``'0-1'``, or ``'1/2-1/2'``."""
        if self.winner is True:
            return "1-0"
        elif self.winner is False:
            return "0-1"
        else:
            return "1/2-1/2"

    def __repr__(self) -> str:
        return (
            f"Outcome(termination={self.termination!r}, "
            f"winner={self.winner!r})"
        )

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Outcome):
            return NotImplemented
        return (
            self.termination == other.termination
            and self.winner == other.winner
        )

    def __hash__(self) -> int:
        return hash((self.termination, self.winner))
