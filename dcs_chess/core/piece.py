"""Piece class (FR-C3)."""

from __future__ import annotations

import typing

from .constants import (
    WHITE, BLACK,
    PIECE_SYMBOLS, PIECE_NAMES, PIECE_TYPES,
    UNICODE_PIECE_SYMBOLS,
)


class Piece:
    """A chess piece with a type and colour.

    Hashable, comparable by value.
    """

    __slots__ = ("piece_type", "color")

    def __init__(self, piece_type: int, color: bool) -> None:
        self.piece_type: int = piece_type
        self.color: bool = color

    def symbol(self) -> str:
        """Single-character symbol; uppercase for White."""
        sym = PIECE_SYMBOLS[self.piece_type]
        assert sym is not None
        return sym.upper() if self.color else sym

    def unicode_symbol(self, *, invert_color: bool = False) -> str:
        """Unicode piece symbol."""
        sym = self.symbol()
        if invert_color:
            sym = sym.swapcase()
        return UNICODE_PIECE_SYMBOLS[sym]

    @classmethod
    def from_symbol(cls, symbol: str) -> Piece:
        """Create a :class:`Piece` from a single-character symbol.

        Uppercase is White, lowercase is Black.
        Raises :exc:`ValueError` for unknown symbols.
        """
        lower = symbol.lower()
        if lower not in PIECE_SYMBOLS:
            raise ValueError(f"Expected piece symbol, got: {symbol!r}")
        piece_type = PIECE_SYMBOLS.index(lower)
        if piece_type == 0:
            raise ValueError(f"Expected piece symbol, got: {symbol!r}")
        color = symbol.isupper()
        return cls(piece_type, color)

    def __hash__(self) -> int:
        return self.piece_type - 1 + (not self.color) * 6

    def __eq__(self, other: object) -> bool:
        if isinstance(other, Piece):
            return self.piece_type == other.piece_type and self.color == other.color
        return NotImplemented

    def __repr__(self) -> str:
        return f"Piece.from_symbol({self.symbol()!r})"

    def __str__(self) -> str:
        return self.symbol()

    def __copy__(self) -> Piece:
        return Piece(self.piece_type, self.color)

    def __deepcopy__(self, memo: typing.Dict[int, typing.Any]) -> Piece:
        return Piece(self.piece_type, self.color)
