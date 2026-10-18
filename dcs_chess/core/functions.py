"""Square and bitboard functions (FR-C2)."""

from __future__ import annotations

import typing

from .constants import (
    SQUARES, SQUARE_NAMES, FILE_NAMES,
    PIECE_SYMBOLS, PIECE_NAMES,
    BB_ALL, BB_SQUARES, BB_FILES, BB_RANKS,
    BB_FILE_A, BB_FILE_B, BB_FILE_G, BB_FILE_H,
    BB_RANK_1, BB_RANK_8,
    BB_RAYS,
)

# ---------------------------------------------------------------------------
# Square functions
# ---------------------------------------------------------------------------

def square(file_index: int, rank_index: int) -> int:
    """Return the square index for the given file (0–7) and rank (0–7)."""
    return rank_index * 8 + file_index


def square_file(sq: int) -> int:
    """Return the file index (0 = a, 7 = h) of a square."""
    return sq & 7


def square_rank(sq: int) -> int:
    """Return the rank index (0 = 1, 7 = 8) of a square."""
    return sq >> 3


def square_name(sq: int) -> str:
    """Return the algebraic name of a square (e.g. ``'e4'``)."""
    return SQUARE_NAMES[sq]


def parse_square(name: str) -> int:
    """Parse an algebraic square name and return its index.

    Raises :exc:`ValueError` if the name is not valid.
    """
    if len(name) != 2:
        raise ValueError(f"Expected square name, got: {name!r}")
    try:
        file_index = FILE_NAMES.index(name[0])
    except ValueError:
        raise ValueError(f"Expected square name, got: {name!r}")
    try:
        rank_index = int(name[1]) - 1
    except ValueError:
        raise ValueError(f"Expected square name, got: {name!r}")
    if not (0 <= rank_index <= 7):
        raise ValueError(f"Expected square name, got: {name!r}")
    return square(file_index, rank_index)


def square_distance(a: int, b: int) -> int:
    """Chebyshev distance (king steps) between two squares."""
    return max(abs(square_file(a) - square_file(b)),
               abs(square_rank(a) - square_rank(b)))


def square_manhattan_distance(a: int, b: int) -> int:
    """Manhattan distance between two squares."""
    return (abs(square_file(a) - square_file(b)) +
            abs(square_rank(a) - square_rank(b)))


# Pre-compute the knight-distance table via BFS
def _compute_knight_distances() -> typing.List[typing.List[int]]:
    from collections import deque
    table = [[0] * 64 for _ in range(64)]
    _knight_deltas = [(-2, -1), (-2, 1), (-1, -2), (-1, 2),
                      (1, -2), (1, 2), (2, -1), (2, 1)]
    for start in range(64):
        dist = [-1] * 64
        dist[start] = 0
        q: typing.Deque[int] = deque([start])
        while q:
            sq = q.popleft()
            f, r = sq & 7, sq >> 3
            for df, dr in _knight_deltas:
                nf, nr = f + df, r + dr
                if 0 <= nf <= 7 and 0 <= nr <= 7:
                    nsq = nr * 8 + nf
                    if dist[nsq] == -1:
                        dist[nsq] = dist[sq] + 1
                        q.append(nsq)
        table[start] = dist
    return table

_KNIGHT_DISTANCE: typing.List[typing.List[int]] = _compute_knight_distances()


def square_knight_distance(a: int, b: int) -> int:  # noqa: F811
    """Minimum number of knight moves between two squares."""
    return _KNIGHT_DISTANCE[a][b]


def square_mirror(sq: int) -> int:
    """Mirror a square vertically (same file, opposite half)."""
    return sq ^ 0x38


# ---------------------------------------------------------------------------
# Piece symbol/name functions
# ---------------------------------------------------------------------------

def piece_symbol(piece_type: int) -> str:
    """Return the single-character symbol for *piece_type* (lowercase)."""
    return PIECE_SYMBOLS[piece_type]  # type: ignore[return-value]


def piece_name(piece_type: int) -> str:
    """Return the English name for *piece_type* (lowercase)."""
    return PIECE_NAMES[piece_type]  # type: ignore[return-value]


# ---------------------------------------------------------------------------
# Bitboard scan functions
# ---------------------------------------------------------------------------

def lsb(bb: int) -> int:
    """Return the index of the least significant set bit, or -1 if empty."""
    if not bb:
        return -1
    return (bb & -bb).bit_length() - 1


def msb(bb: int) -> int:
    """Return the index of the most significant set bit, or -1 if empty."""
    if not bb:
        return -1
    return bb.bit_length() - 1


def scan_forward(bb: int) -> typing.Iterator[int]:
    """Iterate over set bit indices from the LSB upward."""
    while bb:
        bit = bb & -bb
        yield bit.bit_length() - 1
        bb ^= bit


def scan_reversed(bb: int) -> typing.Iterator[int]:
    """Iterate over set bit indices from the MSB downward."""
    while bb:
        idx = bb.bit_length() - 1
        yield idx
        bb ^= BB_SQUARES[idx]


def popcount(bb: int) -> int:
    """Count set bits in a bitboard."""
    return bin(bb).count("1")


# ---------------------------------------------------------------------------
# Bitboard shift functions  (pieces leaving the board vanish)
# ---------------------------------------------------------------------------

def shift_up(bb: int) -> int:
    return (bb << 8) & BB_ALL


def shift_down(bb: int) -> int:
    return bb >> 8


def shift_left(bb: int) -> int:
    return (bb >> 1) & ~BB_FILE_H


def shift_right(bb: int) -> int:
    return (bb << 1) & ~BB_FILE_A & BB_ALL


def shift_2_up(bb: int) -> int:
    return (bb << 16) & BB_ALL


def shift_2_down(bb: int) -> int:
    return bb >> 16


def shift_2_left(bb: int) -> int:
    return (bb >> 2) & ~BB_FILE_G & ~BB_FILE_H


def shift_2_right(bb: int) -> int:
    return (bb << 2) & ~BB_FILE_A & ~BB_FILE_B & BB_ALL


def shift_up_left(bb: int) -> int:
    return (bb << 7) & ~BB_FILE_H & BB_ALL


def shift_up_right(bb: int) -> int:
    return (bb << 9) & ~BB_FILE_A & BB_ALL


def shift_down_left(bb: int) -> int:
    return (bb >> 9) & ~BB_FILE_H


def shift_down_right(bb: int) -> int:
    return (bb >> 7) & ~BB_FILE_A


# ---------------------------------------------------------------------------
# Bitboard flip/transform functions
# ---------------------------------------------------------------------------

def flip_vertical(bb: int) -> int:
    """Flip a bitboard vertically (rank 1 <-> rank 8, etc.)."""
    bb = ((bb >> 8) & 0x00FF_00FF_00FF_00FF) | ((bb & 0x00FF_00FF_00FF_00FF) << 8)
    bb = ((bb >> 16) & 0x0000_FFFF_0000_FFFF) | ((bb & 0x0000_FFFF_0000_FFFF) << 16)
    bb = (bb >> 32) | ((bb & 0x0000_0000_FFFF_FFFF) << 32)
    return bb


def flip_horizontal(bb: int) -> int:
    """Flip a bitboard horizontally (file a <-> file h, etc.)."""
    bb = ((bb >> 1) & 0x5555_5555_5555_5555) | ((bb & 0x5555_5555_5555_5555) << 1)
    bb = ((bb >> 2) & 0x3333_3333_3333_3333) | ((bb & 0x3333_3333_3333_3333) << 2)
    bb = ((bb >> 4) & 0x0F0F_0F0F_0F0F_0F0F) | ((bb & 0x0F0F_0F0F_0F0F_0F0F) << 4)
    return bb


def flip_diagonal(bb: int) -> int:
    """Flip a bitboard along the a1-h8 diagonal."""
    t = (bb ^ (bb << 28)) & 0x0F0F_0F0F_0000_0000
    bb = bb ^ t ^ (t >> 28)
    t = (bb ^ (bb << 14)) & 0x3333_0000_3333_0000
    bb = bb ^ t ^ (t >> 14)
    t = (bb ^ (bb << 7)) & 0x5500_5500_5500_5500
    bb = bb ^ t ^ (t >> 7)
    return bb


def flip_anti_diagonal(bb: int) -> int:
    """Flip a bitboard along the a8-h1 anti-diagonal."""
    t = bb ^ (bb << 36)
    bb ^= (t ^ (bb >> 36)) & 0xF0F0_F0F0_0F0F_0F0F
    t = (bb ^ (bb << 18)) & 0xCCCC_0000_CCCC_0000
    bb ^= t ^ (t >> 18)
    t = (bb ^ (bb << 9)) & 0xAA00_AA00_AA00_AA00
    bb ^= t ^ (t >> 9)
    return bb


# ---------------------------------------------------------------------------
# Ray and between
# ---------------------------------------------------------------------------

def ray(a: int, b: int) -> int:
    """Return the full ray through squares *a* and *b*, or 0 if not aligned."""
    return BB_RAYS[a][b]


def between(a: int, b: int) -> int:
    """Return the mask of squares strictly between *a* and *b* on a ray, or 0."""
    bb = BB_RAYS[a][b]
    if not bb:
        return 0
    # The squares between a and b: on the ray, excluding a and b,
    # and between them (not extending past either end).
    bb &= (BB_ALL << a) if a < b else (BB_ALL << b)
    bb &= (BB_ALL >> (63 - b)) if a < b else (BB_ALL >> (63 - a))
    bb &= ~BB_SQUARES[a] & ~BB_SQUARES[b]
    return bb
