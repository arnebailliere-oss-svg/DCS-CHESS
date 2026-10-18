"""Move class (FR-C4)."""

from __future__ import annotations

import typing

from .constants import SQUARE_NAMES, PIECE_SYMBOLS


class Move:
    """A chess move: origin, destination, optional promotion or drop.

    The null move is ``Move(0, 0)`` (also ``Move.null()``); it is falsy.
    Equality and hashing are by the four fields.
    """

    __slots__ = ("from_square", "to_square", "promotion", "drop")

    def __init__(
        self,
        from_square: int,
        to_square: int,
        promotion: typing.Optional[int] = None,
        drop: typing.Optional[int] = None,
    ) -> None:
        self.from_square: int = from_square
        self.to_square: int = to_square
        self.promotion: typing.Optional[int] = promotion
        self.drop: typing.Optional[int] = drop

    def uci(self) -> str:
        """UCI string: ``e2e4``, ``e7e8q``, ``P@e4``, ``0000`` for null."""
        if self.drop:
            return (
                PIECE_SYMBOLS[self.drop].upper()  # type: ignore[union-attr]
                + "@"
                + SQUARE_NAMES[self.to_square]
            )
        if not self:
            return "0000"
        result = SQUARE_NAMES[self.from_square] + SQUARE_NAMES[self.to_square]
        if self.promotion:
            result += PIECE_SYMBOLS[self.promotion]  # type: ignore[operator]
        return result

    def xboard(self) -> str:
        """XBoard string: same as UCI except ``@@@@`` for the null move."""
        if not self:
            return "@@@@"
        return self.uci()

    @classmethod
    def from_uci(cls, uci: str) -> Move:
        """Parse a UCI move string.

        Raises :exc:`InvalidMoveError` (a :exc:`ValueError`) for bad input.
        """
        if uci == "0000":
            return cls.null()

        if len(uci) >= 4 and uci[1] == "@":
            # Drop move: P@e4
            drop_symbol = uci[0].lower()
            if drop_symbol not in PIECE_SYMBOLS:
                raise ValueError(f"Invalid drop piece in UCI string: {uci!r}")
            drop = PIECE_SYMBOLS.index(drop_symbol)
            to_sq = _parse_square_for_uci(uci[2:4])
            return cls(to_sq, to_sq, drop=drop)

        if len(uci) < 4 or len(uci) > 5:
            raise ValueError(f"Expected UCI string, got: {uci!r}")

        from_sq = _parse_square_for_uci(uci[0:2])
        to_sq = _parse_square_for_uci(uci[2:4])

        promotion = None
        if len(uci) == 5:
            promo_char = uci[4].lower()
            if promo_char not in PIECE_SYMBOLS:
                raise ValueError(f"Invalid promotion piece in UCI string: {uci!r}")
            promotion = PIECE_SYMBOLS.index(promo_char)
            if promotion == 0:
                raise ValueError(f"Invalid promotion piece in UCI string: {uci!r}")

        return cls(from_sq, to_sq, promotion=promotion)

    @classmethod
    def null(cls) -> Move:
        """The null move."""
        return cls(0, 0)

    def __bool__(self) -> bool:
        return bool(
            self.from_square or self.to_square or self.promotion or self.drop
        )

    def __eq__(self, other: object) -> bool:
        if isinstance(other, Move):
            return (
                self.from_square == other.from_square
                and self.to_square == other.to_square
                and self.promotion == other.promotion
                and self.drop == other.drop
            )
        return NotImplemented

    def __hash__(self) -> int:
        return hash((self.from_square, self.to_square, self.promotion, self.drop))

    def __repr__(self) -> str:
        return f"Move.from_uci({self.uci()!r})"

    def __str__(self) -> str:
        return self.uci()

    def __copy__(self) -> Move:
        return Move(self.from_square, self.to_square, self.promotion, self.drop)

    def __deepcopy__(self, memo: typing.Dict[int, typing.Any]) -> Move:
        return Move(self.from_square, self.to_square, self.promotion, self.drop)


def _parse_square_for_uci(name: str) -> int:
    """Parse a two-character square name for UCI, raising ValueError on failure."""
    if len(name) != 2:
        raise ValueError(f"Expected square name, got: {name!r}")
    file_idx = ord(name[0]) - ord("a")
    rank_idx = ord(name[1]) - ord("1")
    if not (0 <= file_idx <= 7 and 0 <= rank_idx <= 7):
        raise ValueError(f"Expected square name, got: {name!r}")
    return rank_idx * 8 + file_idx
