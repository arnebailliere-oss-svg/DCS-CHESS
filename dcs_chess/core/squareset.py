"""SquareSet class (FR-C5)."""

from __future__ import annotations

import typing

from .constants import (
    BB_ALL, BB_EMPTY, BB_SQUARES, BB_RAYS,
    SQUARE_NAMES, FILE_NAMES, RANK_NAMES,
)


class SquareSet:
    """A mutable set of squares, backed by a 64-bit mask.

    Supports set operations, bitwise operators, iteration, ``in``, ``len``,
    ``bool``, ``int()``, text rendering, and equality with integer masks.
    """

    __slots__ = ("_mask",)

    def __init__(self, mask: typing.Union[int, typing.Iterable[int]] = BB_EMPTY) -> None:
        if isinstance(mask, int):
            self._mask = mask & BB_ALL
        else:
            m = BB_EMPTY
            for sq in mask:
                m |= BB_SQUARES[sq]
            self._mask = m

    # --- Container protocol ---

    def __contains__(self, square: object) -> bool:
        if isinstance(square, int):
            return bool(self._mask & BB_SQUARES[square])
        return False

    def __len__(self) -> int:
        return bin(self._mask).count("1")

    def __bool__(self) -> bool:
        return bool(self._mask)

    def __int__(self) -> int:
        return self._mask

    # --- Iteration ---

    def __iter__(self) -> typing.Iterator[int]:
        bb = self._mask
        while bb:
            lsb = bb & -bb
            yield lsb.bit_length() - 1
            bb ^= lsb

    def __reversed__(self) -> typing.Iterator[int]:
        bb = self._mask
        while bb:
            idx = bb.bit_length() - 1
            yield idx
            bb ^= BB_SQUARES[idx]

    # --- Equality (also with plain ints) ---

    def __eq__(self, other: object) -> bool:
        if isinstance(other, SquareSet):
            return self._mask == other._mask
        if isinstance(other, int):
            return self._mask == (other & BB_ALL)
        return NotImplemented

    __hash__ = None  # type: ignore[assignment]

    # --- Bitwise operators ---

    def __and__(self, other: typing.Union[SquareSet, int]) -> SquareSet:
        return SquareSet(self._mask & _to_mask(other))

    def __or__(self, other: typing.Union[SquareSet, int]) -> SquareSet:
        return SquareSet(self._mask | _to_mask(other))

    def __xor__(self, other: typing.Union[SquareSet, int]) -> SquareSet:
        return SquareSet(self._mask ^ _to_mask(other))

    def __sub__(self, other: typing.Union[SquareSet, int]) -> SquareSet:
        return SquareSet(self._mask & ~_to_mask(other))

    def __invert__(self) -> SquareSet:
        return SquareSet(~self._mask & BB_ALL)

    def __lshift__(self, shift: int) -> SquareSet:
        return SquareSet((self._mask << shift) & BB_ALL)

    def __rshift__(self, shift: int) -> SquareSet:
        return SquareSet(self._mask >> shift)

    # --- In-place bitwise ---

    def __iand__(self, other: typing.Union[SquareSet, int]) -> SquareSet:
        self._mask &= _to_mask(other)
        return self

    def __ior__(self, other: typing.Union[SquareSet, int]) -> SquareSet:
        self._mask |= _to_mask(other)
        self._mask &= BB_ALL
        return self

    def __ixor__(self, other: typing.Union[SquareSet, int]) -> SquareSet:
        self._mask ^= _to_mask(other)
        self._mask &= BB_ALL
        return self

    def __isub__(self, other: typing.Union[SquareSet, int]) -> SquareSet:
        self._mask &= ~_to_mask(other)
        return self

    def __ilshift__(self, shift: int) -> SquareSet:
        self._mask = (self._mask << shift) & BB_ALL
        return self

    def __irshift__(self, shift: int) -> SquareSet:
        self._mask >>= shift
        return self

    # --- Reflected operators for int on the left ---

    def __rand__(self, other: int) -> SquareSet:
        return SquareSet(other & self._mask)

    def __ror__(self, other: int) -> SquareSet:
        return SquareSet((other | self._mask) & BB_ALL)

    def __rxor__(self, other: int) -> SquareSet:
        return SquareSet((other ^ self._mask) & BB_ALL)

    def __rsub__(self, other: int) -> SquareSet:
        return SquareSet(other & ~self._mask & BB_ALL)

    # --- Mutable set methods ---

    def add(self, square: int) -> None:
        self._mask |= BB_SQUARES[square]

    def discard(self, square: int) -> None:
        self._mask &= ~BB_SQUARES[square]

    def remove(self, square: int) -> None:
        if not (self._mask & BB_SQUARES[square]):
            raise KeyError(square)
        self._mask &= ~BB_SQUARES[square]

    def pop(self) -> int:
        if not self._mask:
            raise KeyError("pop from an empty SquareSet")
        lsb = self._mask & -self._mask
        sq = lsb.bit_length() - 1
        self._mask ^= lsb
        return sq

    def clear(self) -> None:
        self._mask = BB_EMPTY

    # --- Set algebra methods ---

    def update(self, *others: typing.Union[SquareSet, int]) -> None:
        for other in others:
            self._mask |= _to_mask(other)
        self._mask &= BB_ALL

    def intersection_update(self, *others: typing.Union[SquareSet, int]) -> None:
        for other in others:
            self._mask &= _to_mask(other)

    def difference_update(self, *others: typing.Union[SquareSet, int]) -> None:
        for other in others:
            self._mask &= ~_to_mask(other)

    def symmetric_difference_update(self, other: typing.Union[SquareSet, int]) -> None:
        self._mask ^= _to_mask(other)
        self._mask &= BB_ALL

    def union(self, other: typing.Union[SquareSet, int]) -> SquareSet:
        return SquareSet(self._mask | _to_mask(other))

    def intersection(self, other: typing.Union[SquareSet, int]) -> SquareSet:
        return SquareSet(self._mask & _to_mask(other))

    def difference(self, other: typing.Union[SquareSet, int]) -> SquareSet:
        return SquareSet(self._mask & ~_to_mask(other))

    def symmetric_difference(self, other: typing.Union[SquareSet, int]) -> SquareSet:
        return SquareSet((self._mask ^ _to_mask(other)) & BB_ALL)

    def issubset(self, other: typing.Union[SquareSet, int]) -> bool:
        return not (self._mask & ~_to_mask(other))

    def issuperset(self, other: typing.Union[SquareSet, int]) -> bool:
        return not (_to_mask(other) & ~self._mask)

    def isdisjoint(self, other: typing.Union[SquareSet, int]) -> bool:
        return not (self._mask & _to_mask(other))

    # --- Other methods ---

    def copy(self) -> SquareSet:
        return SquareSet(self._mask)

    def tolist(self) -> typing.List[bool]:
        return [bool(self._mask & BB_SQUARES[sq]) for sq in range(64)]

    def mirror(self) -> SquareSet:
        """Vertically flip the square set."""
        return SquareSet(_flip_vertical_mask(self._mask))

    def carry_rippler(self) -> typing.Iterator[SquareSet]:
        """Iterate over all subsets of this set (including empty and self)."""
        subset = BB_EMPTY
        while True:
            yield SquareSet(subset)
            subset = (subset - self._mask) & self._mask
            if not subset:
                break

    # --- Class methods ---

    @classmethod
    def ray(cls, a: int, b: int) -> SquareSet:
        return cls(BB_RAYS[a][b])

    @classmethod
    def between(cls, a: int, b: int) -> SquareSet:
        from .functions import between as _between
        return cls(_between(a, b))

    @classmethod
    def from_square(cls, square: int) -> SquareSet:
        return cls(BB_SQUARES[square])

    # --- String representations ---

    def __repr__(self) -> str:
        return f"SquareSet({self._mask:#018x})"

    def __str__(self) -> str:
        builder: typing.List[str] = []
        for rank in range(7, -1, -1):
            line: typing.List[str] = []
            for file in range(8):
                sq = rank * 8 + file
                line.append("1" if self._mask & BB_SQUARES[sq] else ".")
            builder.append(" ".join(line))
        return "\n".join(builder)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _to_mask(value: typing.Union['SquareSet', int, typing.Iterable[int]]) -> int:
    if isinstance(value, SquareSet):
        return value._mask
    if isinstance(value, int):
        return value & BB_ALL
    mask = 0
    for sq in value:
        mask |= 1 << sq
    return mask & BB_ALL


def _flip_vertical_mask(bb: int) -> int:
    bb = ((bb >> 8) & 0x00FF_00FF_00FF_00FF) | ((bb & 0x00FF_00FF_00FF_00FF) << 8)
    bb = ((bb >> 16) & 0x0000_FFFF_0000_FFFF) | ((bb & 0x0000_FFFF_0000_FFFF) << 16)
    bb = (bb >> 32) | ((bb & 0x0000_0000_FFFF_FFFF) << 32)
    return bb
