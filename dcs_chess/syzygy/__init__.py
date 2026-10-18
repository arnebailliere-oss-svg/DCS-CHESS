"""Syzygy endgame tablebase probing (FR-Y1 + FR-Y2).

Implements WDL (Win/Draw/Loss) and DTZ (Distance to Zeroing) probing
for Syzygy tablebases. File format based on publicly documented
Syzygy/Fathom specifications.
"""

from __future__ import annotations

import collections
import math
import mmap
import os
import re
import struct
import threading
import typing
from typing import (
    Deque, Dict, Iterable, Iterator, List, Optional,
    Set, Tuple, Type, TypeVar, Union,
)

if typing.TYPE_CHECKING:
    from types import TracebackType

from ..core.constants import (
    KING, QUEEN, ROOK, BISHOP, KNIGHT, PAWN,
    WHITE, BLACK,
    A1, B1, C1, D1, E1, F1, G1, H1,
    A2, B2, C2, D2, E2, F2, G2, H2,
    A3, B3, C3, D3, E3, F3, G3, H3,
    A4, B4, C4, D4, E4, F4, G4, H4,
    A5, B5, C5, D5, E5, F5, G5, H5,
    A6, B6, C6, D6, E6, F6, G6, H6,
    A7, B7, C7, D7, E7, F7, G7, H7,
    A8, B8, C8, D8, E8, F8, G8, H8,
    SQUARES,
    BB_EMPTY,
    PIECE_TYPES, PIECE_SYMBOLS,
)
from ..core.functions import (
    square_file, square_rank, square_mirror,
    lsb, msb, scan_forward, scan_reversed, popcount,
)
from ..core.board import Board as _Board

TBPIECES = 7

PCHR = ["K", "Q", "R", "B", "N", "P"]

TABLENAME_REGEX = re.compile(r"^[KQRBNP]+v[KQRBNP]+\Z")

UINT16 = struct.Struct("<H")
UINT32 = struct.Struct("<I")
UINT32_BE = struct.Struct(">I")
UINT64_BE = struct.Struct(">Q")

# WDL mapping tables.
WDL_TO_MAP = [1, 3, 0, 2, 0]
PA_FLAGS = [8, 0, 0, 0, 4]
WDL_TO_DTZ = [-1, -101, 0, 101, 1]

FILE_TO_FILE = [0, 1, 2, 3, 3, 2, 1, 0]

# Triangular index: maps the 64 squares onto the 10-square triangle
# (a1-d1-d4 with symmetry). 6 means "off triangle" (not one of the 10).
TRIANGLE = [
    6, 0, 1, 2, 2, 1, 0, 6,
    0, 7, 3, 4, 4, 3, 7, 0,
    1, 3, 8, 5, 5, 8, 3, 1,
    2, 4, 5, 9, 9, 5, 4, 2,
    2, 4, 5, 9, 9, 5, 4, 2,
    1, 3, 8, 5, 5, 8, 3, 1,
    0, 7, 3, 4, 4, 3, 7, 0,
    6, 0, 1, 2, 2, 1, 0, 6,
]

INVTRIANGLE = [1, 2, 3, 10, 11, 19, 0, 9, 18, 27]

DIAG = [
    0, 0, 0, 0, 0, 0, 0, 8,
    0, 1, 0, 0, 0, 0, 9, 0,
    0, 0, 2, 0, 0, 10, 0, 0,
    0, 0, 0, 3, 11, 0, 0, 0,
    0, 0, 0, 12, 4, 0, 0, 0,
    0, 0, 13, 0, 0, 5, 0, 0,
    0, 14, 0, 0, 0, 0, 6, 0,
    15, 0, 0, 0, 0, 0, 0, 7,
]

FLAP = [
    0, 0, 0, 0, 0, 0, 0, 0,
    0, 6, 12, 18, 18, 12, 6, 0,
    1, 7, 13, 19, 19, 13, 7, 1,
    2, 8, 14, 20, 20, 14, 8, 2,
    3, 9, 15, 21, 21, 15, 9, 3,
    4, 10, 16, 22, 22, 16, 10, 4,
    5, 11, 17, 23, 23, 17, 11, 5,
    0, 0, 0, 0, 0, 0, 0, 0,
]

INVFLAP = [
    8, 16, 24, 32, 40, 48,
    9, 17, 25, 33, 41, 49,
    10, 18, 26, 34, 42, 50,
    11, 19, 27, 35, 43, 51,
]

PTWIST = [
    0, 0, 0, 0, 0, 0, 0, 0,
    47, 35, 23, 11, 10, 22, 34, 46,
    45, 33, 21, 9, 8, 20, 32, 44,
    43, 31, 19, 7, 6, 18, 30, 42,
    41, 29, 17, 5, 4, 16, 28, 40,
    39, 27, 15, 3, 2, 14, 26, 38,
    37, 25, 13, 1, 0, 12, 24, 36,
    0, 0, 0, 0, 0, 0, 0, 0,
]

MTWIST = [
    15, 63, 55, 47, 40, 48, 56, 12,
    62, 11, 39, 31, 24, 32, 8, 57,
    54, 38, 7, 23, 16, 4, 33, 49,
    46, 30, 22, 3, 0, 17, 25, 41,
    45, 29, 21, 2, 1, 18, 26, 42,
    53, 37, 6, 20, 19, 5, 34, 50,
    61, 10, 36, 28, 27, 35, 9, 58,
    14, 60, 52, 44, 43, 51, 59, 13,
]

LOWER = [
    28, 0, 1, 2, 3, 4, 5, 6,
    0, 29, 7, 8, 9, 10, 11, 12,
    1, 7, 30, 13, 14, 15, 16, 17,
    2, 8, 13, 31, 18, 19, 20, 21,
    3, 9, 14, 18, 32, 22, 23, 24,
    4, 10, 15, 19, 22, 33, 25, 26,
    5, 11, 16, 20, 23, 25, 34, 27,
    6, 12, 17, 21, 24, 26, 27, 35,
]

KK_IDX = [
    [-1, -1, -1, 0, 1, 2, 3, 4, -1, -1, -1, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48, 49, 50, 51, 52, 53, 54, 55, 56, 57],
    [58, -1, -1, -1, 59, 60, 61, 62, 63, -1, -1, -1, 64, 65, 66, 67, 68, 69, 70, 71, 72, 73, 74, 75, 76, 77, 78, 79, 80, 81, 82, 83, 84, 85, 86, 87, 88, 89, 90, 91, 92, 93, 94, 95, 96, 97, 98, 99, 100, 101, 102, 103, 104, 105, 106, 107, 108, 109, 110, 111, 112, 113, 114, 115],
    [116, 117, -1, -1, -1, 118, 119, 120, 121, 122, -1, -1, -1, 123, 124, 125, 126, 127, 128, 129, 130, 131, 132, 133, 134, 135, 136, 137, 138, 139, 140, 141, 142, 143, 144, 145, 146, 147, 148, 149, 150, 151, 152, 153, 154, 155, 156, 157, 158, 159, 160, 161, 162, 163, 164, 165, 166, 167, 168, 169, 170, 171, 172, 173],
    [174, -1, -1, -1, 175, 176, 177, 178, 179, -1, -1, -1, 180, 181, 182, 183, 184, -1, -1, -1, 185, 186, 187, 188, 189, 190, 191, 192, 193, 194, 195, 196, 197, 198, 199, 200, 201, 202, 203, 204, 205, 206, 207, 208, 209, 210, 211, 212, 213, 214, 215, 216, 217, 218, 219, 220, 221, 222, 223, 224, 225, 226, 227, 228],
    [229, 230, -1, -1, -1, 231, 232, 233, 234, 235, -1, -1, -1, 236, 237, 238, 239, 240, -1, -1, -1, 241, 242, 243, 244, 245, 246, 247, 248, 249, 250, 251, 252, 253, 254, 255, 256, 257, 258, 259, 260, 261, 262, 263, 264, 265, 266, 267, 268, 269, 270, 271, 272, 273, 274, 275, 276, 277, 278, 279, 280, 281, 282, 283],
    [284, 285, 286, 287, 288, 289, 290, 291, 292, 293, -1, -1, -1, 294, 295, 296, 297, 298, -1, -1, -1, 299, 300, 301, 302, 303, -1, -1, -1, 304, 305, 306, 307, 308, 309, 310, 311, 312, 313, 314, 315, 316, 317, 318, 319, 320, 321, 322, 323, 324, 325, 326, 327, 328, 329, 330, 331, 332, 333, 334, 335, 336, 337, 338],
    [-1, -1, 339, 340, 341, 342, 343, 344, -1, -1, 345, 346, 347, 348, 349, 350, -1, -1, 441, 351, 352, 353, 354, 355, -1, -1, -1, 442, 356, 357, 358, 359, -1, -1, -1, -1, 443, 360, 361, 362, -1, -1, -1, -1, -1, 444, 363, 364, -1, -1, -1, -1, -1, -1, 445, 365, -1, -1, -1, -1, -1, -1, -1, 446],
    [-1, -1, -1, 366, 367, 368, 369, 370, -1, -1, -1, 371, 372, 373, 374, 375, -1, -1, -1, 376, 377, 378, 379, 380, -1, -1, -1, 447, 381, 382, 383, 384, -1, -1, -1, -1, 448, 385, 386, 387, -1, -1, -1, -1, -1, 449, 388, 389, -1, -1, -1, -1, -1, -1, 450, 390, -1, -1, -1, -1, -1, -1, -1, 451],
    [452, 391, 392, 393, 394, 395, 396, 397, -1, -1, -1, -1, 398, 399, 400, 401, -1, -1, -1, -1, 402, 403, 404, 405, -1, -1, -1, -1, 406, 407, 408, 409, -1, -1, -1, -1, 453, 410, 411, 412, -1, -1, -1, -1, -1, 454, 413, 414, -1, -1, -1, -1, -1, -1, 455, 415, -1, -1, -1, -1, -1, -1, -1, 456],
    [457, 416, 417, 418, 419, 420, 421, 422, -1, 458, 423, 424, 425, 426, 427, 428, -1, -1, -1, -1, -1, 429, 430, 431, -1, -1, -1, -1, -1, 432, 433, 434, -1, -1, -1, -1, -1, 435, 436, 437, -1, -1, -1, -1, -1, 459, 438, 439, -1, -1, -1, -1, -1, -1, 460, 440, -1, -1, -1, -1, -1, -1, -1, 461],
]

PP_IDX = [
    [0, -1, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, -1, 47, 48, 49, 50, 51, 52, 53, 54, 55, 56, 57, 58, 59, 60, 61],
    [62, -1, -1, 63, 64, 65, -1, 66, -1, 67, 68, 69, 70, 71, 72, -1, 73, 74, 75, 76, 77, 78, 79, 80, 81, 82, 83, 84, 85, 86, 87, 88, 89, 90, 91, 92, 93, 94, 95, 96, -1, 97, 98, 99, 100, 101, 102, 103, -1, 104, 105, 106, 107, 108, 109, -1, 110, -1, 111, 112, 113, 114, -1, 115],
    [116, -1, -1, -1, 117, -1, -1, 118, -1, 119, 120, 121, 122, 123, 124, -1, -1, 125, 126, 127, 128, 129, 130, -1, 131, 132, 133, 134, 135, 136, 137, 138, -1, 139, 140, 141, 142, 143, 144, 145, -1, 146, 147, 148, 149, 150, 151, -1, -1, 152, 153, 154, 155, 156, 157, -1, 158, -1, -1, 159, 160, -1, -1, 161],
    [162, -1, -1, -1, -1, -1, -1, 163, -1, 164, -1, 165, 166, 167, 168, -1, -1, 169, 170, 171, 172, 173, 174, -1, -1, 175, 176, 177, 178, 179, 180, -1, -1, 181, 182, 183, 184, 185, 186, -1, -1, -1, 187, 188, 189, 190, 191, -1, -1, 192, 193, 194, 195, 196, 197, -1, 198, -1, -1, -1, -1, -1, -1, 199],
    [200, -1, -1, -1, -1, -1, -1, 201, -1, 202, -1, -1, 203, -1, 204, -1, -1, -1, 205, 206, 207, 208, -1, -1, -1, 209, 210, 211, 212, 213, 214, -1, -1, -1, 215, 216, 217, 218, 219, -1, -1, -1, 220, 221, 222, 223, -1, -1, -1, 224, -1, 225, 226, -1, 227, -1, 228, -1, -1, -1, -1, -1, -1, 229],
    [230, -1, -1, -1, -1, -1, -1, 231, -1, 232, -1, -1, -1, -1, 233, -1, -1, -1, 234, -1, 235, 236, -1, -1, -1, -1, 237, 238, 239, 240, -1, -1, -1, -1, -1, 241, 242, 243, -1, -1, -1, -1, 244, 245, 246, 247, -1, -1, -1, 248, -1, -1, -1, -1, 249, -1, 250, -1, -1, -1, -1, -1, -1, 251],
    [-1, -1, -1, -1, -1, -1, -1, 259, -1, 252, -1, -1, -1, -1, 260, -1, -1, -1, 253, -1, -1, 261, -1, -1, -1, -1, -1, 254, 262, -1, -1, -1, -1, -1, -1, -1, 255, -1, -1, -1, -1, -1, -1, -1, -1, 256, -1, -1, -1, -1, -1, -1, -1, -1, 257, -1, -1, -1, -1, -1, -1, -1, -1, 258],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 268, -1, -1, -1, 263, -1, -1, 269, -1, -1, -1, -1, -1, 264, 270, -1, -1, -1, -1, -1, -1, -1, 265, -1, -1, -1, -1, -1, -1, -1, -1, 266, -1, -1, -1, -1, -1, -1, -1, -1, 267, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 274, -1, -1, -1, -1, -1, 271, 275, -1, -1, -1, -1, -1, -1, -1, 272, -1, -1, -1, -1, -1, -1, -1, -1, 273, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 277, -1, -1, -1, -1, -1, -1, -1, 276, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
]

PAWNIDX = [
    [0, 1, 2, 3, 4, 5, 0, 1, 2, 3, 4, 5, 0, 1, 2, 3, 4, 5, 0, 1, 2, 3, 4, 5],
    [0, 47, 92, 135, 176, 215, 0, 35, 68, 99, 128, 155, 0, 23, 44, 63, 80, 95, 0, 11, 20, 27, 32, 35],
    [0, 1081, 2071, 2974, 3794, 4535, 0, 595, 1123, 1588, 1994, 2345, 0, 253, 463, 634, 770, 875, 0, 55, 91, 112, 122, 125],
    [0, 16215, 30405, 42746, 53406, 62545, 0, 6545, 12001, 16496, 20150, 23075, 0, 1771, 3101, 4070, 4750, 5205, 0, 165, 249, 284, 294, 295],
    [0, 178365, 327360, 450770, 552040, 634291, 0, 52360, 93280, 124745, 148496, 166046, 0, 8855, 14840, 18716, 21096, 22461, 0, 330, 456, 491, 496, 496],
]

PFACTOR = [
    [6, 6, 6, 6],
    [252, 180, 108, 36],
    [5201, 2645, 953, 125],
    [70315, 25375, 5491, 295],
    [700336, 178696, 23176, 496],
]

MULTIDX = [
    [0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
    [0, 63, 118, 165, 204, 235, 258, 273, 284, 291],
    [0, 1953, 3438, 4519, 5260, 5725, 5978, 6083, 6138, 6159],
    [0, 39711, 65946, 82161, 91300, 95795, 97566, 98021, 98186, 98221],
    [0, 595665, 936720, 1115085, 1197336, 1228801, 1237656, 1239021, 1239351, 1239386],
]

MFACTOR = [10, 294, 6162, 98222, 1239386]


class MissingTableError(KeyError):
    """A required Syzygy table is missing."""


def binom(x: int, y: int) -> int:
    """Binomial coefficient C(x, y)."""
    if y < 0 or y > x:
        return 0
    if y == 0 or y == x:
        return 1
    y = min(y, x - y)
    result = 1
    for i in range(y):
        result = result * (x - i) // (i + 1)
    return result


def subfactor(k: int, n: int) -> int:
    """Number of ways to place k items on n squares in order."""
    if k == 0:
        return n
    f = n
    l = 1  # noqa: E741
    for i in range(1, k):
        f *= n - i
        l *= i + 1  # noqa: E741
    return f // l


def flipdiag(square: int) -> int:
    """Flip a square along the a1-h8 diagonal."""
    return ((square >> 3) | (square << 3)) & 63


def offdiag(square: int) -> int:
    """Return signed distance from a1-h8 diagonal. Positive = below, negative = above."""
    return square_rank(square) - square_file(square)


def test45(sq: int) -> bool:
    """Test if a square is in the a8-h1 upper-left triangle."""
    r = square_rank(sq)
    f = square_file(sq)
    return r >= 4 and r > f and r + f < 7


_PT_TO_PCHR = {QUEEN: "Q", ROOK: "R", BISHOP: "B", KNIGHT: "N", PAWN: "P"}


def calc_key(board: _Board, *, mirror: bool = False) -> str:
    """Calculate the tablebase key for a position."""
    w: List[str] = []
    b: List[str] = []
    for pt in (QUEEN, ROOK, BISHOP, KNIGHT, PAWN):
        ch = _PT_TO_PCHR[pt]
        for _ in range(bin(board.pieces_mask(pt, WHITE)).count("1")):
            w.append(ch)
        for _ in range(bin(board.pieces_mask(pt, BLACK)).count("1")):
            b.append(ch)

    if mirror:
        return "K" + "".join(b) + "v" + "K" + "".join(w)
    return "K" + "".join(w) + "v" + "K" + "".join(b)


def recalc_key(pieces: List[int], *, mirror: bool = False) -> str:
    """Recalculate tablebase key from encoded piece list (piece_type | color_bit)."""
    w = 8 if mirror else 0
    b = 0 if mirror else 8

    return "".join([
        "K" * pieces.count(6 ^ w),
        "Q" * pieces.count(5 ^ w),
        "R" * pieces.count(4 ^ w),
        "B" * pieces.count(3 ^ w),
        "N" * pieces.count(2 ^ w),
        "P" * pieces.count(1 ^ w),
        "v",
        "K" * pieces.count(6 ^ b),
        "Q" * pieces.count(5 ^ b),
        "R" * pieces.count(4 ^ b),
        "B" * pieces.count(3 ^ b),
        "N" * pieces.count(2 ^ b),
        "P" * pieces.count(1 ^ b),
    ])


def normalize_tablename(name: str, *, mirror: bool = False) -> str:
    """Normalize a tablebase name to canonical form (stronger side first)."""
    parts = name.split("v")
    if len(parts) != 2:
        return name

    w, b = parts[0], parts[1]

    w_pieces = sorted(w, key=lambda p: PCHR.index(p))
    b_pieces = sorted(b, key=lambda p: PCHR.index(p))
    w = "".join(w_pieces)
    b = "".join(b_pieces)

    if _compare_sides(w_pieces, b_pieces) < 0:
        w, b = b, w

    if mirror:
        return b + "v" + w
    return w + "v" + b


def _compare_sides(w_pieces: List[str], b_pieces: List[str]) -> int:
    """Compare two sides. Returns >0 if white side is stronger or equal."""
    if len(w_pieces) != len(b_pieces):
        return len(w_pieces) - len(b_pieces)

    for wp, bp in zip(w_pieces, b_pieces):
        wi = PCHR.index(wp) if wp in PCHR else 5
        bi = PCHR.index(bp) if bp in PCHR else 5
        if wi != bi:
            return bi - wi  # lower index = stronger piece
    return 0


def is_tablename(name: str, *, one_king: bool = True, piece_count: Optional[int] = 7, normalized: bool = True) -> bool:
    """Check if a string is a valid tablebase name."""
    if not TABLENAME_REGEX.match(name):
        return False

    parts = name.split("v")
    w, b = parts[0], parts[1]

    if one_king:
        if not w.startswith("K") or not b.startswith("K"):
            return False
        if w.count("K") != 1 or b.count("K") != 1:
            return False

    total = len(w) + len(b)
    if piece_count is not None and total > piece_count:
        return False
    if one_king and total < 3:
        return False

    if normalized:
        if normalize_tablename(name) != name:
            return False

    return True


def tablenames(*, one_king: bool = True, piece_count: int = 6) -> Iterator[str]:
    """Generate all valid tablebase names up to a given piece count."""
    if one_king:
        piece_chars = PCHR[1:]  # Q, R, B, N, P
    else:
        piece_chars = PCHR  # K, Q, R, B, N, P
    min_total = 3 if one_king else 2

    for total in range(min_total, piece_count + 1):
        for w_count in range(1, total):
            b_count = total - w_count
            if b_count < 1:
                continue

            if one_king:
                configs = [(True, True)]
            else:
                configs = [(False, False)]

            for w_king, b_king in configs:
                w_non = w_count - (1 if w_king else 0)
                b_non = b_count - (1 if b_king else 0)
                if w_non < 0 or b_non < 0:
                    continue

                for wp in _piece_combinations(piece_chars, w_non):
                    for bp in _piece_combinations(piece_chars, b_non):
                        w_str = ("K" if w_king else "") + "".join(wp)
                        b_str = ("K" if b_king else "") + "".join(bp)
                        name = w_str + "v" + b_str
                        if is_tablename(name, one_king=one_king, piece_count=piece_count):
                            yield name


def _piece_combinations(chars: List[str], count: int) -> Iterator[Tuple[str, ...]]:
    """Generate sorted piece combinations (non-increasing order by strength)."""
    if count == 0:
        yield ()
        return
    for i, c in enumerate(chars):
        for rest in _piece_combinations(chars[i:], count - 1):
            yield (c,) + rest


def dependencies(target: str, *, one_king: bool = True) -> Iterator[str]:
    """Generate the tablebase dependencies of a target tablename.

    Includes capture dependencies (remove a piece) and promotion
    dependencies (replace a pawn with Q, R, B, or N).
    """
    parts = target.split("v")
    w, b = parts[0], parts[1]
    w_pieces = list(w)
    b_pieces = list(b)

    seen: Set[str] = set()

    def _emit(name: str) -> Iterator[str]:
        name = normalize_tablename(name)
        if name not in seen and is_tablename(name, one_king=one_king):
            seen.add(name)
            yield name

    promos = ["Q", "R", "B", "N"] if one_king else ["K", "Q", "R", "B", "N"]

    for i in range(len(w_pieces)):
        if w_pieces[i] == "P":
            for promo in promos:
                sub = w_pieces[:i] + [promo] + w_pieces[i + 1:]
                sub_sorted = sorted(sub, key=lambda c: PCHR.index(c))
                name = "".join(sub_sorted) + "v" + "".join(b_pieces)
                yield from _emit(name)

    for i in range(len(b_pieces)):
        if b_pieces[i] == "P":
            for promo in promos:
                sub = b_pieces[:i] + [promo] + b_pieces[i + 1:]
                sub_sorted = sorted(sub, key=lambda c: PCHR.index(c))
                name = "".join(w_pieces) + "v" + "".join(sub_sorted)
                yield from _emit(name)

    # Capture dependencies: remove one non-king piece from either side.
    for i in range(len(w_pieces)):
        if one_king and w_pieces[i] == "K":
            continue
        sub = w_pieces[:i] + w_pieces[i + 1:]
        name = "".join(sub) + "v" + "".join(b_pieces)
        yield from _emit(name)

    for i in range(len(b_pieces)):
        if one_king and b_pieces[i] == "K":
            continue
        sub = b_pieces[:i] + b_pieces[i + 1:]
        name = "".join(w_pieces) + "v" + "".join(sub)
        yield from _emit(name)


def all_dependencies(targets: Iterable[str], *, one_king: bool = True) -> Iterator[str]:
    """Generate all transitive dependencies for the given targets, including the targets themselves."""
    seen: Set[str] = set()
    queue = list(targets)
    for target in queue:
        if target not in seen:
            seen.add(target)
            yield target
    while queue:
        target = queue.pop(0)
        for dep in dependencies(target, one_king=one_king):
            if dep not in seen:
                seen.add(dep)
                yield dep
                queue.append(dep)


def dtz_before_zeroing(wdl: int) -> int:
    """Convert a WDL value to a DTZ value before the zeroing move."""
    return WDL_TO_DTZ[wdl + 2]


class PairsData:
    """Huffman-compressed pairs data for a tablebase block."""

    def __init__(self) -> None:
        self.indextable: int = 0
        self.sizetable: int = 0
        self.data: int = 0
        self.offset: int = 0
        self.symlen: List[int] = []
        self.sympat: int = 0
        self.blocksize: int = 0
        self.idxbits: int = 0
        self.min_len: int = 0
        self.base: List[int] = []
        self.num_blocks: int = 0
        self.max_len: int = 0
        self.real_num_blocks: int = 0
        self.num_indices: int = 0
        self.flags: int = 0
        self.const_value: int = 0
        self.num_syms: int = 0


class PawnFileData:
    """Per-file data for pawn tables (WDL)."""

    def __init__(self) -> None:
        self.precomp: Dict[int, Optional[PairsData]] = {}
        self.pieces: Dict[int, List[int]] = {}
        self.norm: Dict[int, List[int]] = {}
        self.factor: Dict[int, List[int]] = {}


class PawnFileDataDtz:
    """Per-file data for pawn tables (DTZ)."""

    def __init__(self) -> None:
        self.precomp: Optional[PairsData] = None
        self.pieces: List[int] = []
        self.norm: List[int] = []
        self.factor: List[int] = []


class Table:
    """Base class for Syzygy tablebase tables."""

    def __init__(self, path: str, *, variant: Type[_Board] = _Board) -> None:
        self.path = path
        self.variant = variant

        self.data: Optional[mmap.mmap] = None
        self.fd: Optional[int] = None

        self.key: str = ""
        self.mirrored_key: str = ""
        self.num: int = 0
        self.has_pawns: bool = False
        self.pawns: List[int] = [0, 0]
        self.enc_type: int = 0

        # Parse the tablename from the filename.
        basename = os.path.basename(path)
        name = basename.split(".")[0]
        self.key = normalize_tablename(name)
        self.mirrored_key = normalize_tablename(name, mirror=True)
        self.symmetric = self.key == self.mirrored_key

        parts = name.split("v")
        self.num = len(parts[0]) + len(parts[1])

        self.has_pawns = "P" in name
        if self.has_pawns:
            self.pawns = [parts[0].count("P"), parts[1].count("P")]
            if self.pawns[1] > 0 and (self.pawns[0] == 0 or self.pawns[1] < self.pawns[0]):
                self.pawns[0], self.pawns[1] = self.pawns[1], self.pawns[0]
        else:
            self.pawns = [0, 0]
            j = 0
            for piece_type in PCHR:
                if parts[0].count(piece_type) == 1:
                    j += 1
                if parts[1].count(piece_type) == 1:
                    j += 1
            if j >= 3:
                self.enc_type = 0
            elif j == 2:
                self.enc_type = 2
            else:
                self.enc_type = 1 + j

    def init_mmap(self) -> None:
        """Memory-map the table file."""
        if self.data is not None:
            return
        self.fd = os.open(self.path, os.O_RDONLY | getattr(os, "O_BINARY", 0))
        self.data = mmap.mmap(self.fd, 0, access=mmap.ACCESS_READ)

    def close(self) -> None:
        """Close the memory-mapped file."""
        if self.data is not None:
            self.data.close()
            self.data = None
        if self.fd is not None:
            os.close(self.fd)
            self.fd = None

    def __enter__(self) -> Table:
        return self

    def __exit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_value: Optional[BaseException],
        traceback: Optional[TracebackType],
    ) -> None:
        self.close()

    def read_uint16(self, data_ptr: int) -> int:
        assert self.data is not None
        return UINT16.unpack_from(self.data, data_ptr)[0]

    def read_uint32(self, data_ptr: int) -> int:
        assert self.data is not None
        return UINT32.unpack_from(self.data, data_ptr)[0]

    def read_uint32_be(self, data_ptr: int) -> int:
        assert self.data is not None
        return UINT32_BE.unpack_from(self.data, data_ptr)[0]

    def read_uint64_be(self, data_ptr: int) -> int:
        assert self.data is not None
        return UINT64_BE.unpack_from(self.data, data_ptr)[0]

    def check_magic(self, magic: Optional[bytes], pawnless_magic: Optional[bytes]) -> None:
        assert self.data is not None
        if self.has_pawns:
            if magic is not None:
                assert self.data[:4] == magic, f"bad magic: {self.data[:4]!r} != {magic!r}"
        else:
            if pawnless_magic is not None:
                assert self.data[:4] == pawnless_magic, f"bad magic: {self.data[:4]!r} != {pawnless_magic!r}"

    def set_norm_piece(self, norm: List[int], pieces: List[int]) -> None:
        """Set normalization factors for piece-only tables."""
        if self.enc_type == 0:
            norm[0] = 3
        elif self.enc_type == 2:
            norm[0] = 2
        else:
            norm[0] = self.enc_type - 1

        i = norm[0]
        while i < self.num:
            j = i
            while j < self.num and pieces[j] == pieces[i]:
                norm[i] += 1
                j += 1
            i += norm[i]

    def set_norm_pawn(self, norm: List[int], pieces: List[int]) -> None:
        """Set normalization factors for pawn tables."""
        norm[0] = self.pawns[0]
        i = norm[0]
        if pieces[i] == pieces[i - 1]:
            norm[i] = norm[0] + 1
            i += 1
        while i < self.num:
            j = i
            while j < self.num and pieces[j] == pieces[i]:
                j += 1
            norm[i] = j - i
            i = j

    def calc_factors_piece(self, factor: List[int], order: int, norm: List[int]) -> int:
        """Calculate encoding factors for piece-only tables."""
        PIVFAC = [31332, 28056, 462]

        n = 64 - norm[0]

        f = 1
        i = norm[0]
        k = 0
        while i < self.num or k == order:
            if k == order:
                factor[0] = f
                if self.enc_type < len(PIVFAC):
                    f *= PIVFAC[self.enc_type]
            else:
                factor[i] = f
                f *= subfactor(norm[i], n)
                n -= norm[i]
                i += norm[i]
            k += 1

        return f

    def calc_factors_pawn(self, factor: List[int], order: int, order2: int, norm: List[int], f: int) -> int:
        """Calculate encoding factors for pawn tables."""
        i = norm[0]
        if order2 < 0x0f:
            i += norm[i]

        n = 64 - i

        fac = 1
        k = 0
        while i < self.num or k == order or k == order2:
            if k == order:
                factor[0] = fac
                fac *= PFACTOR[norm[0] - 1][f]
            elif k == order2:
                factor[norm[0]] = fac
                fac *= subfactor(norm[norm[0]], 48 - norm[0])
            else:
                factor[i] = fac
                fac *= subfactor(norm[i], n)
                n -= norm[i]
                i += norm[i]
            k += 1

        return fac

    def setup_pairs(self, data_ptr: int, tb_size: int, size_idx: int, wdl: int) -> PairsData:
        """Parse Huffman-compressed pairs data from the table file."""
        assert self.data is not None
        d = PairsData()

        self._flags = self.data[data_ptr]
        if self.data[data_ptr] & 0x80:
            d.idxbits = 0
            if wdl:
                d.min_len = self.data[data_ptr + 1]
            else:
                d.min_len = 0
            self._next = data_ptr + 2
            self.size[size_idx + 0] = 0
            self.size[size_idx + 1] = 0
            self.size[size_idx + 2] = 0
            return d

        d.blocksize = self.data[data_ptr + 1]
        d.idxbits = self.data[data_ptr + 2]

        real_num_blocks = self.read_uint32(data_ptr + 4)
        num_blocks = real_num_blocks + self.data[data_ptr + 3]
        max_len = self.data[data_ptr + 8]
        min_len = self.data[data_ptr + 9]
        h = max_len - min_len + 1
        num_syms = self.read_uint16(data_ptr + 10 + 2 * h)

        d.offset = data_ptr + 10
        d.symlen = [0 for _ in range(h * 8 + num_syms)]
        d.sympat = data_ptr + 12 + 2 * h
        d.min_len = min_len

        self._next = data_ptr + 12 + 2 * h + 3 * num_syms + (num_syms & 1)

        num_indices = (tb_size + (1 << d.idxbits) - 1) >> d.idxbits
        self.size[size_idx + 0] = 6 * num_indices
        self.size[size_idx + 1] = 2 * num_blocks
        self.size[size_idx + 2] = (1 << d.blocksize) * real_num_blocks

        tmp = [0 for _ in range(num_syms)]
        for i in range(num_syms):
            if not tmp[i]:
                self.calc_symlen(d, i, tmp)

        d.base = [0 for _ in range(h)]
        d.base[h - 1] = 0
        for i in range(h - 2, -1, -1):
            d.base[i] = (d.base[i + 1] + self.read_uint16(d.offset + i * 2) - self.read_uint16(d.offset + i * 2 + 2)) // 2
        for i in range(h):
            d.base[i] <<= 64 - (min_len + i)

        d.offset -= 2 * d.min_len

        return d

    def calc_symlen(self, d: PairsData, s: int, tmp: List[int]) -> None:
        """Calculate the length of a Huffman symbol."""
        assert self.data is not None

        w = d.sympat + 3 * s
        s2 = (self.data[w + 2] << 4) | (self.data[w + 1] >> 4)

        if s2 == 0x0fff:
            d.symlen[s] = 0
        else:
            s1 = ((self.data[w + 1] & 0x0f) << 8) | self.data[w]

            if not tmp[s1]:
                self.calc_symlen(d, s1, tmp)
            if not tmp[s2]:
                self.calc_symlen(d, s2, tmp)

            d.symlen[s] = d.symlen[s1] + d.symlen[s2] + 1

        tmp[s] = 1

    def decompress_pairs(self, d: PairsData, idx: int) -> int:
        """Decompress a value from the compressed pairs data."""
        assert self.data is not None

        if not d.idxbits:
            return d.min_len

        mainidx = idx >> d.idxbits
        litidx = (idx & (1 << d.idxbits) - 1) - (1 << (d.idxbits - 1))
        block = self.read_uint32(d.indextable + 6 * mainidx)

        idx_offset = self.read_uint16(d.indextable + 6 * mainidx + 4)
        litidx += idx_offset

        if litidx < 0:
            while litidx < 0:
                block -= 1
                litidx += self.read_uint16(d.sizetable + 2 * block) + 1
        else:
            while litidx > self.read_uint16(d.sizetable + 2 * block):
                litidx -= self.read_uint16(d.sizetable + 2 * block) + 1
                block += 1

        ptr = d.data + (block << d.blocksize)

        m = d.min_len
        base_idx = -m
        symlen_idx = 0

        code = self.read_uint64_be(ptr)

        ptr += 2 * 4
        bitcnt = 0
        while True:
            l = m  # noqa: E741
            while code < d.base[base_idx + l]:
                l += 1  # noqa: E741
            sym = self.read_uint16(d.offset + l * 2)
            sym += (code - d.base[base_idx + l]) >> (64 - l)
            if litidx < d.symlen[symlen_idx + sym] + 1:
                break
            litidx -= d.symlen[symlen_idx + sym] + 1
            code <<= l
            bitcnt += l
            if bitcnt >= 32:
                bitcnt -= 32
                code |= self.read_uint32_be(ptr) << bitcnt
                ptr += 4

            code &= 0xffffffffffffffff

        sympat = d.sympat
        while d.symlen[symlen_idx + sym]:
            w = sympat + 3 * sym
            s1 = ((self.data[w + 1] & 0xf) << 8) | self.data[w]
            if litidx < d.symlen[symlen_idx + s1] + 1:
                sym = s1
            else:
                litidx -= d.symlen[symlen_idx + s1] + 1
                sym = (self.data[w + 2] << 4) | (self.data[w + 1] >> 4)

        w = sympat + 3 * sym
        if isinstance(self, DtzTable):
            return ((self.data[w + 1] & 0x0f) << 8) | self.data[w]
        else:
            return self.data[w]

    def encode_piece(self, norm: List[int], pos: List[int], factor: List[int]) -> int:
        """Encode a piece position into a table index."""
        n = self.num

        if self.enc_type < 3:
            if pos[0] & 0x04:
                for i in range(n):
                    pos[i] ^= 0x07
            if pos[0] & 0x20:
                for i in range(n):
                    pos[i] ^= 0x38
            for i in range(n):
                if offdiag(pos[i]):
                    break
            if i < (3 if self.enc_type == 0 else 2) and offdiag(pos[i]) > 0:
                for i in range(n):
                    pos[i] = flipdiag(pos[i])

        if self.enc_type == 0:
            i = int(pos[1] > pos[0])
            j = int(pos[2] > pos[0]) + int(pos[2] > pos[1])

            if offdiag(pos[0]):
                idx = TRIANGLE[pos[0]] * 63 * 62 + (pos[1] - i) * 62 + (pos[2] - j)
            elif offdiag(pos[1]):
                idx = 6 * 63 * 62 + DIAG[pos[0]] * 28 * 62 + LOWER[pos[1]] * 62 + pos[2] - j
            elif offdiag(pos[2]):
                idx = 6 * 63 * 62 + 4 * 28 * 62 + DIAG[pos[0]] * 7 * 28 + (DIAG[pos[1]] - i) * 28 + LOWER[pos[2]]
            else:
                idx = 6 * 63 * 62 + 4 * 28 * 62 + 4 * 7 * 28 + DIAG[pos[0]] * 7 * 6 + (DIAG[pos[1]] - i) * 6 + (DIAG[pos[2]] - j)
            i = 3
        elif self.enc_type == 2:
            idx = KK_IDX[TRIANGLE[pos[0]]][pos[1]]
            i = 2
        elif self.enc_type == 3:
            if TRIANGLE[pos[0]] > TRIANGLE[pos[1]]:
                pos[0], pos[1] = pos[1], pos[0]
            if pos[0] & 0x04:
                for i in range(n):
                    pos[i] ^= 0x07
            if pos[0] & 0x20:
                for i in range(n):
                    pos[i] ^= 0x38
            if offdiag(pos[0]) > 0 or (offdiag(pos[0]) == 0 and offdiag(pos[1]) > 0):
                for i in range(n):
                    pos[i] = flipdiag(pos[i])
            if test45(pos[1]) and TRIANGLE[pos[0]] == TRIANGLE[pos[1]]:
                pos[0], pos[1] = pos[1], pos[0]
                for i in range(n):
                    pos[i] = flipdiag(pos[i] ^ 0x38)
            idx = PP_IDX[TRIANGLE[pos[0]]][pos[1]]
            i = 2
        else:
            for i in range(1, norm[0]):
                if TRIANGLE[pos[0]] > TRIANGLE[pos[i]]:
                    pos[0], pos[i] = pos[i], pos[0]
            if pos[0] & 0x04:
                for i in range(n):
                    pos[i] ^= 0x07
            if pos[0] & 0x20:
                for i in range(n):
                    pos[i] ^= 0x38
            if offdiag(pos[0]) > 0:
                for i in range(n):
                    pos[i] = flipdiag(pos[i])
            for i in range(1, norm[0]):
                for j in range(i + 1, norm[0]):
                    if MTWIST[pos[i]] > MTWIST[pos[j]]:
                        pos[i], pos[j] = pos[j], pos[i]

            idx = MULTIDX[norm[0] - 1][TRIANGLE[pos[0]]]
            i = 1
            while i < norm[0]:
                idx += binom(MTWIST[pos[i]], i)
                i += 1

        idx *= factor[0]

        while i < n:
            t = norm[i]

            for j in range(i, i + t):
                for k in range(j + 1, i + t):
                    if pos[j] > pos[k]:
                        pos[j], pos[k] = pos[k], pos[j]

            s = 0
            for m in range(i, i + t):
                p = pos[m]
                j = 0
                for l in range(i):
                    j += int(p > pos[l])
                s += binom(p - j, m - i + 1)

            idx += s * factor[i]
            i += t

        return idx

    def encode_pawn(self, norm: List[int], pos: List[int], factor: List[int]) -> int:
        """Encode a pawn position into a table index."""
        n = self.num

        if pos[0] & 0x04:
            for i in range(n):
                pos[i] ^= 0x07

        for i in range(1, self.pawns[0]):
            for j in range(i + 1, self.pawns[0]):
                if PTWIST[pos[i]] < PTWIST[pos[j]]:
                    pos[i], pos[j] = pos[j], pos[i]

        t = self.pawns[0] - 1
        idx = PAWNIDX[t][FLAP[pos[0]]]
        for i in range(t, 0, -1):
            idx += binom(PTWIST[pos[i]], t - i + 1)
        idx *= factor[0]

        i = self.pawns[0]
        t = i + self.pawns[1]
        if t > i:
            for j in range(i, t):
                for k in range(j + 1, t):
                    if pos[j] > pos[k]:
                        pos[j], pos[k] = pos[k], pos[j]
            s = 0
            for m in range(i, t):
                p = pos[m]
                j = 0
                for k in range(i):
                    j += int(p > pos[k])
                s += binom(p - j - 8, m - i + 1)
            idx += s * factor[i]
            i = t

        while i < n:
            t = norm[i]
            for j in range(i, i + t):
                for k in range(j + 1, i + t):
                    if pos[j] > pos[k]:
                        pos[j], pos[k] = pos[k], pos[j]

            s = 0
            for m in range(i, i + t):
                p = pos[m]
                j = 0
                for k in range(i):
                    j += int(p > pos[k])
                s += binom(p - j, m - i + 1)

            idx += s * factor[i]
            i += t

        return idx

    def pawn_file(self, pos: List[int]) -> int:
        """Determine which file-slot a pawn configuration belongs to."""
        for i in range(1, self.pawns[0]):
            if FLAP[pos[0]] > FLAP[pos[i]]:
                pos[0], pos[i] = pos[i], pos[0]
        return FILE_TO_FILE[pos[0] & 0x07]


class WdlTable(Table):
    """Win/Draw/Loss tablebase table."""

    WDL_MAGIC = b"\x71\xe8\x23\x5d"
    WDL_MAGIC_PAWNLESS = b"\x71\xe8\x23\x5d"

    def __init__(self, path: str, *, variant: Type[_Board] = _Board) -> None:
        super().__init__(path, variant=variant)
        self.initialized = False

    def init_table_wdl(self) -> None:
        """Initialize the WDL table from the memory-mapped file."""
        self.init_mmap()
        assert self.data is not None

        if self.initialized:
            return

        self.check_magic(self.WDL_MAGIC, self.WDL_MAGIC_PAWNLESS)

        self.tb_size: List[int] = [0 for _ in range(8)]
        self.size: List[int] = [0 for _ in range(8 * 3)]

        self.precomp: Dict[int, PairsData] = {}
        self.pieces: Dict[int, List[int]] = {}
        self.factor: List[List[int]] = [[0 for _ in range(TBPIECES)] for _ in range(2)]
        self.norm: List[List[int]] = [[0 for _ in range(self.num)] for _ in range(2)]

        self.files: List[PawnFileData] = [PawnFileData() for _ in range(4)]

        split = self.data[4] & 0x01
        files = 4 if self.data[4] & 0x02 else 1

        data_ptr = 5

        if not self.has_pawns:
            self.setup_pieces_piece(data_ptr)
            data_ptr += self.num + 1
            data_ptr += data_ptr & 0x01

            self.precomp[0] = self.setup_pairs(data_ptr, self.tb_size[0], 0, True)
            data_ptr = self._next
            if split:
                self.precomp[1] = self.setup_pairs(data_ptr, self.tb_size[1], 3, True)
                data_ptr = self._next

            self.precomp[0].indextable = data_ptr
            data_ptr += self.size[0]
            if split:
                self.precomp[1].indextable = data_ptr
                data_ptr += self.size[3]

            self.precomp[0].sizetable = data_ptr
            data_ptr += self.size[1]
            if split:
                self.precomp[1].sizetable = data_ptr
                data_ptr += self.size[4]

            data_ptr = (data_ptr + 0x3f) & ~0x3f
            self.precomp[0].data = data_ptr
            data_ptr += self.size[2]
            if split:
                data_ptr = (data_ptr + 0x3f) & ~0x3f
                self.precomp[1].data = data_ptr

            self.key = recalc_key(self.pieces[0])
            self.mirrored_key = recalc_key(self.pieces[0], mirror=True)
        else:
            s = 1 + int(self.pawns[1] > 0)
            for f in range(4):
                self.setup_pieces_pawn(data_ptr, 2 * f, f)
                data_ptr += self.num + s
            data_ptr += data_ptr & 0x01

            for f in range(files):
                self.files[f].precomp[0] = self.setup_pairs(data_ptr, self.tb_size[2 * f], 6 * f, True)
                data_ptr = self._next
                if split:
                    self.files[f].precomp[1] = self.setup_pairs(data_ptr, self.tb_size[2 * f + 1], 6 * f + 3, True)
                    data_ptr = self._next

            for f in range(files):
                self.files[f].precomp[0].indextable = data_ptr
                data_ptr += self.size[6 * f]
                if split:
                    self.files[f].precomp[1].indextable = data_ptr
                    data_ptr += self.size[6 * f + 3]

            for f in range(files):
                self.files[f].precomp[0].sizetable = data_ptr
                data_ptr += self.size[6 * f + 1]
                if split:
                    self.files[f].precomp[1].sizetable = data_ptr
                    data_ptr += self.size[6 * f + 4]

            for f in range(files):
                data_ptr = (data_ptr + 0x3f) & ~0x3f
                self.files[f].precomp[0].data = data_ptr
                data_ptr += self.size[6 * f + 2]
                if split:
                    data_ptr = (data_ptr + 0x3f) & ~0x3f
                    self.files[f].precomp[1].data = data_ptr
                    data_ptr += self.size[6 * f + 5]

        self.initialized = True

    def setup_pieces_piece(self, p_data: int) -> None:
        """Set up piece ordering and normalization for pieceless tables."""
        assert self.data is not None

        self.pieces[0] = [self.data[p_data + i + 1] & 0x0f for i in range(self.num)]
        order = self.data[p_data] & 0x0f
        self.set_norm_piece(self.norm[0], self.pieces[0])
        self.tb_size[0] = self.calc_factors_piece(self.factor[0], order, self.norm[0])

        self.pieces[1] = [self.data[p_data + i + 1] >> 4 for i in range(self.num)]
        order = self.data[p_data] >> 4
        self.set_norm_piece(self.norm[1], self.pieces[1])
        self.tb_size[1] = self.calc_factors_piece(self.factor[1], order, self.norm[1])

    def setup_pieces_pawn(self, p_data: int, p_tb_size: int, f: int) -> None:
        """Set up piece ordering for pawn tables."""
        assert self.data is not None

        j = 1 + int(self.pawns[1] > 0)
        order = self.data[p_data] & 0x0f
        order2 = self.data[p_data + 1] & 0x0f if self.pawns[1] else 0x0f
        self.files[f].pieces[0] = [self.data[p_data + i + j] & 0x0f for i in range(self.num)]
        self.files[f].norm[0] = [0 for _ in range(self.num)]
        self.set_norm_pawn(self.files[f].norm[0], self.files[f].pieces[0])
        self.files[f].factor[0] = [0 for _ in range(TBPIECES)]
        self.tb_size[p_tb_size] = self.calc_factors_pawn(self.files[f].factor[0], order, order2, self.files[f].norm[0], f)

        order = self.data[p_data] >> 4
        order2 = self.data[p_data + 1] >> 4 if self.pawns[1] else 0x0f
        self.files[f].pieces[1] = [self.data[p_data + i + j] >> 4 for i in range(self.num)]
        self.files[f].norm[1] = [0 for _ in range(self.num)]
        self.set_norm_pawn(self.files[f].norm[1], self.files[f].pieces[1])
        self.files[f].factor[1] = [0 for _ in range(TBPIECES)]
        self.tb_size[p_tb_size + 1] = self.calc_factors_pawn(self.files[f].factor[1], order, order2, self.files[f].norm[1], f)

    def probe_wdl_table(self, board: _Board) -> int:
        """Probe the WDL table for a position."""
        self.init_table_wdl()
        return self._probe_wdl_table(board)

    def _probe_wdl_table(self, board: _Board) -> int:
        """Internal WDL table probe."""
        self.init_table_wdl()

        key = calc_key(board)

        if not self.symmetric:
            if key != self.key:
                cmirror = 8
                mirror = 0x38
                bside = int(board.turn == WHITE)
            else:
                cmirror = mirror = 0
                bside = int(board.turn != WHITE)
        else:
            cmirror = 0 if board.turn == WHITE else 8
            mirror = 0 if board.turn == WHITE else 0x38
            bside = 0

        if not self.has_pawns:
            p = [0 for _ in range(TBPIECES)]
            i = 0
            while i < self.num:
                piece_type = self.pieces[bside][i] & 0x07
                color = (self.pieces[bside][i] ^ cmirror) >> 3
                bb = board.pieces_mask(piece_type, WHITE if color == 0 else BLACK)

                for square in scan_forward(bb):
                    p[i] = square
                    i += 1

            idx = self.encode_piece(self.norm[bside], p, self.factor[bside])
            res = self.decompress_pairs(self.precomp[bside], idx)
        else:
            p = [0 for _ in range(TBPIECES)]
            i = 0
            k = self.files[0].pieces[0][0] ^ cmirror
            color = k >> 3
            piece_type = k & 0x07
            bb = board.pieces_mask(piece_type, WHITE if color == 0 else BLACK)

            for square in scan_forward(bb):
                p[i] = square ^ mirror
                i += 1

            f = self.pawn_file(p)
            pc = self.files[f].pieces[bside]
            while i < self.num:
                color = (pc[i] ^ cmirror) >> 3
                piece_type = pc[i] & 0x07
                bb = board.pieces_mask(piece_type, WHITE if color == 0 else BLACK)

                for square in scan_forward(bb):
                    p[i] = square ^ mirror
                    i += 1

            idx = self.encode_pawn(self.files[f].norm[bside], p, self.files[f].factor[bside])
            res = self.decompress_pairs(self.files[f].precomp[bside], idx)

        return res - 2


class DtzTable(Table):
    """Distance to Zeroing tablebase table."""

    DTZ_MAGIC = b"\xd7\x66\x0c\xa5"
    DTZ_MAGIC_PAWNLESS = b"\xd7\x66\x0c\xa5"

    def __init__(self, path: str, *, variant: Type[_Board] = _Board) -> None:
        super().__init__(path, variant=variant)
        self.initialized = False

    def init_table_dtz(self) -> None:
        """Initialize the DTZ table from the memory-mapped file."""
        self.init_mmap()
        assert self.data is not None

        if self.initialized:
            return

        self.check_magic(self.DTZ_MAGIC, self.DTZ_MAGIC_PAWNLESS)

        self.factor: List[int] = [0 for _ in range(TBPIECES)]
        self.norm: List[int] = [0 for _ in range(self.num)]
        self.tb_size: List[int] = [0, 0, 0, 0]
        self.size: List[int] = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
        self.files: List[PawnFileDataDtz] = [PawnFileDataDtz() for _ in range(4)]

        files = 4 if self.data[4] & 0x02 else 1

        p_data = 5

        if not self.has_pawns:
            self.map_idx: List[List[int]] = [[0, 0, 0, 0]]

            self.setup_pieces_piece_dtz(p_data, 0)
            p_data += self.num + 1
            p_data += p_data & 0x01

            self.precomp: PairsData = self.setup_pairs(p_data, self.tb_size[0], 0, False)
            self.flags: Union[int, List[int]] = self._flags
            p_data = self._next
            self.p_map = p_data
            if self.flags & 2:
                if not self.flags & 16:
                    for i in range(4):
                        self.map_idx[0][i] = p_data + 1 - self.p_map
                        p_data += 1 + self.data[p_data]
                else:
                    for i in range(4):
                        self.map_idx[0][i] = (p_data + 2 - self.p_map) // 2
                        p_data += 2 + 2 * self.read_uint16(p_data)
            p_data += p_data & 0x01

            self.precomp.indextable = p_data
            p_data += self.size[0]

            self.precomp.sizetable = p_data
            p_data += self.size[1]

            p_data = (p_data + 0x3f) & ~0x3f
            self.precomp.data = p_data
            p_data += self.size[2]

            self.key = recalc_key(self.pieces)
            self.mirrored_key = recalc_key(self.pieces, mirror=True)
        else:
            s = 1 + int(self.pawns[1] > 0)
            for f in range(4):
                self.setup_pieces_pawn_dtz(p_data, f, f)
                p_data += self.num + s
            p_data += p_data & 0x01

            self.flags = []
            for f in range(files):
                self.files[f].precomp = self.setup_pairs(p_data, self.tb_size[f], 3 * f, False)
                p_data = self._next
                self.flags.append(self._flags)

            self.map_idx = []
            self.p_map = p_data
            for f in range(files):
                self.map_idx.append([])
                if self.flags[f] & 2:
                    if not self.flags[f] & 16:
                        for _ in range(4):
                            self.map_idx[-1].append(p_data + 1 - self.p_map)
                            p_data += 1 + self.data[p_data]
                    else:
                        p_data += p_data & 0x01
                        for _ in range(4):
                            self.map_idx[-1].append((p_data + 2 - self.p_map) // 2)
                            p_data += 2 + 2 * self.read_uint16(p_data)
            p_data += p_data & 0x01

            for f in range(files):
                self.files[f].precomp.indextable = p_data
                p_data += self.size[3 * f]

            for f in range(files):
                self.files[f].precomp.sizetable = p_data
                p_data += self.size[3 * f + 1]

            for f in range(files):
                p_data = (p_data + 0x3f) & ~0x3f
                self.files[f].precomp.data = p_data
                p_data += self.size[3 * f + 2]

        self.initialized = True

    def setup_pieces_piece_dtz(self, p_data: int, p_tb_size: int) -> None:
        """Set up piece ordering for DTZ piece-only tables."""
        assert self.data is not None
        self.pieces: List[int] = [self.data[p_data + i + 1] & 0x0f for i in range(self.num)]
        order = self.data[p_data] & 0x0f
        self.set_norm_piece(self.norm, self.pieces)
        self.tb_size[p_tb_size] = self.calc_factors_piece(self.factor, order, self.norm)

    def setup_pieces_pawn_dtz(self, p_data: int, p_tb_size: int, f: int) -> None:
        """Set up piece ordering for DTZ pawn tables."""
        assert self.data is not None
        j = 1 + int(self.pawns[1] > 0)
        order = self.data[p_data] & 0x0f
        order2 = self.data[p_data + 1] & 0x0f if self.pawns[1] else 0x0f
        self.files[f].pieces = [self.data[p_data + i + j] & 0x0f for i in range(self.num)]
        self.files[f].norm = [0 for _ in range(self.num)]
        self.set_norm_pawn(self.files[f].norm, self.files[f].pieces)
        self.files[f].factor = [0 for _ in range(TBPIECES)]
        self.tb_size[p_tb_size] = self.calc_factors_pawn(self.files[f].factor, order, order2, self.files[f].norm, f)

    def probe_dtz_table(self, board: _Board, wdl: int) -> Tuple[int, int]:
        """Probe the DTZ table for a position."""
        self.init_table_dtz()
        return self._probe_dtz_table(board, wdl)

    def _probe_dtz_table(self, board: _Board, wdl: int) -> Tuple[int, int]:
        """Internal DTZ table probe."""
        self.init_table_dtz()
        assert self.data is not None

        key = calc_key(board)

        if not self.symmetric:
            if key != self.key:
                cmirror = 8
                mirror = 0x38
                bside = int(board.turn == WHITE)
            else:
                cmirror = mirror = 0
                bside = int(board.turn != WHITE)
        else:
            cmirror = 0 if board.turn == WHITE else 8
            mirror = 0 if board.turn == WHITE else 0x38
            bside = 0

        if not self.has_pawns:
            assert isinstance(self.flags, int)

            if (self.flags & 1) != bside and not self.symmetric:
                return 0, -1

            pc = self.pieces
            p = [0 for _ in range(TBPIECES)]
            i = 0
            while i < self.num:
                piece_type = pc[i] & 0x07
                color = (pc[i] ^ cmirror) >> 3
                bb = board.pieces_mask(piece_type, WHITE if color == 0 else BLACK)

                for square in scan_forward(bb):
                    p[i] = square
                    i += 1

            idx = self.encode_piece(self.norm, p, self.factor)
            res = self.decompress_pairs(self.precomp, idx)

            if self.flags & 2:
                if not self.flags & 16:
                    res = self.data[self.p_map + self.map_idx[0][WDL_TO_MAP[wdl + 2]] + res]
                else:
                    res = self.read_uint16(self.p_map + 2 * (self.map_idx[0][WDL_TO_MAP[wdl + 2]] + res))

            if (not (self.flags & PA_FLAGS[wdl + 2])) or (wdl & 1):
                res *= 2
        else:
            assert isinstance(self.flags, list)

            k = self.files[0].pieces[0] ^ cmirror
            piece_type = k & 0x07
            color = k >> 3
            bb = board.pieces_mask(piece_type, WHITE if color == 0 else BLACK)

            i = 0
            p = [0 for _ in range(TBPIECES)]
            for square in scan_forward(bb):
                p[i] = square ^ mirror
                i += 1
            f = self.pawn_file(p)
            if self.flags[f] & 1 != bside:
                return 0, -1

            pc = self.files[f].pieces
            while i < self.num:
                piece_type = pc[i] & 0x07
                color = (pc[i] ^ cmirror) >> 3
                bb = board.pieces_mask(piece_type, WHITE if color == 0 else BLACK)

                for square in scan_forward(bb):
                    p[i] = square ^ mirror
                    i += 1

            idx = self.encode_pawn(self.files[f].norm, p, self.files[f].factor)
            res = self.decompress_pairs(self.files[f].precomp, idx)

            if self.flags[f] & 2:
                if not self.flags[f] & 16:
                    res = self.data[self.p_map + self.map_idx[f][WDL_TO_MAP[wdl + 2]] + res]
                else:
                    res = self.read_uint16(self.p_map + 2 * (self.map_idx[f][WDL_TO_MAP[wdl + 2]] + res))

            if (not (self.flags[f] & PA_FLAGS[wdl + 2])) or (wdl & 1):
                res *= 2

        return res, 1


class Tablebase:
    """Manages a collection of Syzygy tablebase files."""

    def __init__(
        self,
        *,
        max_fds: Optional[int] = 128,
        VariantBoard: Type[_Board] = _Board,
    ) -> None:
        self.max_fds = max_fds
        self.variant = VariantBoard

        self.wdl: Dict[str, WdlTable] = {}
        self.dtz: Dict[str, DtzTable] = {}

        self.lru: Deque[Table] = collections.deque()
        self.lru_lock = threading.Lock()

    def add_directory(self, directory: str, *, load_wdl: bool = True, load_dtz: bool = True) -> int:
        """Add all tablebase files from a directory."""
        count = 0
        for filename in os.listdir(directory):
            path = os.path.join(directory, filename)
            count += self.add_file(path, load_wdl=load_wdl, load_dtz=load_dtz)

        return count

    def add_file(self, path: str, *, load_wdl: bool = True, load_dtz: bool = True) -> int:
        """Add a single tablebase file."""
        count = 0
        basename = os.path.basename(path)
        name, _, ext = basename.rpartition(".")

        if not name or not TABLENAME_REGEX.match(name):
            return 0

        if ext == "rtbw" and load_wdl:
            if name not in self.wdl:
                self.wdl[name] = WdlTable(path, variant=self.variant)
                count += 1

        if ext == "rtbz" and load_dtz:
            if name not in self.dtz:
                self.dtz[name] = DtzTable(path, variant=self.variant)
                count += 1

        return count

    def probe_wdl(self, board: _Board) -> int:
        """Probe WDL tables for a position.

        Returns:
            2 for a win, 1 for a cursed win, 0 for a draw,
            -1 for a blessed loss, -2 for a loss.

        Raises:
            MissingTableError: If the required table is not loaded.
            KeyError: If the position cannot be probed.
        """
        # Must not have castling rights.
        assert not board.castling_rights

        # Only probe with <= TBPIECES pieces.
        if bin(board.occupied).count("1") > TBPIECES:
            raise MissingTableError(f"too many pieces: {bin(board.occupied).count('1')}")

        # KvK is always a draw — no table needed.
        if not board.pawns and not board.knights and not board.bishops and not board.rooks and not board.queens:
            return 0

        v, _ = self.probe_ab(board, -2, 2)

        if not board.ep_square:
            return v

        v1 = -3
        for move in board.generate_legal_ep():
            board.push(move)
            try:
                v0_plus, _ = self.probe_ab(board, -2, 2)
                v0 = -v0_plus
            finally:
                board.pop()
            if v0 > v1:
                v1 = v0

        if v1 > -3:
            if v1 >= v:
                v = v1
            elif v == 0:
                if all(board.is_en_passant(move) for move in board.generate_legal_moves()):
                    v = v1

        return v

    def probe_wdl_table(self, board: _Board) -> int:
        """Probe the WDL table directly."""
        if not board.pawns and not board.knights and not board.bishops and not board.rooks and not board.queens:
            return 0

        key = calc_key(board)
        mirrored_key = calc_key(board, mirror=True)

        if key in self.wdl:
            return self.wdl[key].probe_wdl_table(board)
        elif mirrored_key in self.wdl:
            return self.wdl[mirrored_key].probe_wdl_table(board)
        else:
            raise MissingTableError(f"missing WDL table: {key}")

    def get_wdl(self, board: _Board, default: Optional[int] = None) -> Optional[int]:
        """Probe WDL, returning a default value if the table is missing."""
        try:
            return self.probe_wdl(board)
        except MissingTableError:
            return default

    def probe_dtz(self, board: _Board) -> int:
        """Probe DTZ tables for a position."""
        assert not board.castling_rights

        if popcount(board.occupied) > TBPIECES:
            raise MissingTableError(f"too many pieces: {popcount(board.occupied)}")

        if not board.pawns and not board.knights and not board.bishops and not board.rooks and not board.queens:
            return 0

        v = self.probe_dtz_no_ep(board)

        if not board.ep_square:
            return v

        v1 = -3
        for move in board.generate_legal_ep():
            board.push(move)
            try:
                v0_plus, _ = self.probe_ab(board, -2, 2)
                v0 = -v0_plus
            finally:
                board.pop()
            if v0 > v1:
                v1 = v0

        if v1 > -3:
            v1 = WDL_TO_DTZ[v1 + 2]
            if v < -100:
                if v1 >= 0:
                    v = v1
            elif v < 0:
                if v1 >= 0 or v1 < -100:
                    v = v1
            elif v > 100:
                if v1 > 0:
                    v = v1
            elif v > 0:
                if v1 == 1:
                    v = v1
            elif v1 >= 0:
                v = v1
            else:
                if all(board.is_en_passant(move) for move in board.generate_legal_moves()):
                    v = v1

        return v

    def probe_dtz_no_ep(self, board: _Board) -> int:
        """Probe DTZ without en passant handling."""
        wdl, success = self.probe_ab(board, -2, 2, threats=True)

        if wdl == 0:
            return 0

        if success == 2 or not board.occupied_co[board.turn] & ~board.pawns:
            return dtz_before_zeroing(wdl)

        if wdl > 0:
            if success == 3:
                return 2 if wdl == 2 else 102

            for move in board.generate_legal_moves(board.pawns, ~board.occupied):
                if board.is_capture(move):
                    continue
                board.push(move)
                try:
                    v = -self.probe_wdl(board)
                finally:
                    board.pop()
                if v == wdl:
                    return 1 if v == 2 else 101

        dtz, success = self.probe_dtz_table(board, wdl)
        if success >= 0:
            return dtz_before_zeroing(wdl) + (dtz if wdl > 0 else -dtz)

        if wdl > 0:
            best = 0xffff
            for move in board.generate_legal_moves(~board.pawns, ~board.occupied):
                board.push(move)
                try:
                    v = -self.probe_dtz(board)
                    if v == 1 and board.is_checkmate():
                        best = 1
                    elif v > 0 and v + 1 < best:
                        best = v + 1
                finally:
                    board.pop()
            return best
        else:
            best = -1
            for move in board.generate_legal_moves():
                board.push(move)
                try:
                    if board.halfmove_clock == 0:
                        if wdl == -2:
                            v = -1
                        else:
                            v, success = self.probe_ab(board, 1, 2, threats=True)
                            v = 0 if v == 2 else -101
                    else:
                        v = -self.probe_dtz(board) - 1
                finally:
                    board.pop()
                if v < best:
                    best = v
            return best

    def probe_dtz_table(self, board: _Board, wdl: int) -> Tuple[int, int]:
        """Probe the DTZ table directly."""
        key = calc_key(board)
        mirrored_key = calc_key(board, mirror=True)

        if key in self.dtz:
            return self.dtz[key].probe_dtz_table(board, wdl)
        elif mirrored_key in self.dtz:
            return self.dtz[mirrored_key].probe_dtz_table(board, wdl)
        else:
            raise MissingTableError(f"missing DTZ table: {key}")

    def get_dtz(self, board: _Board, default: Optional[int] = None) -> Optional[int]:
        """Probe DTZ, returning a default value if the table is missing."""
        try:
            return self.probe_dtz(board)
        except MissingTableError:
            return default

    def probe_ab(self, board: _Board, alpha: int, beta: int, threats: bool = False) -> Tuple[int, int]:
        """Probe with alpha-beta window, resolving captures first."""
        for move in board.generate_legal_moves(to_mask=board.occupied_co[not board.turn]):
            board.push(move)
            try:
                v_plus, _ = self.probe_ab(board, -beta, -alpha)
                v = -v_plus
            finally:
                board.pop()

            if v > alpha:
                if v >= beta:
                    return v, 2
                alpha = v

        v = self.probe_wdl_table(board)

        if alpha >= v:
            return alpha, 1 + int(alpha > 0)
        else:
            return v, 1

    def sprobe_capts(self, board: _Board, alpha: int, beta: int) -> Tuple[int, int]:
        captures_found = False
        for move in board.generate_legal_captures():
            captures_found = True
            board.push(move)
            try:
                v_plus, _ = self.sprobe_ab(board, -beta, -alpha)
                v = -v_plus
            finally:
                board.pop()
            alpha = max(v, alpha)
            if alpha >= beta:
                break
        return (alpha, captures_found)

    def sprobe_ab(self, board: _Board, alpha: int, beta: int, threats: bool = False) -> Tuple[int, int]:
        if popcount(board.occupied_co[not board.turn]) > 1:
            v, captures_found = self.sprobe_capts(board, alpha, beta)
            if captures_found:
                return (v, 2)
        else:
            if any(board.generate_legal_captures()):
                return (-2, 2)

        threats_found = False
        if threats or popcount(board.occupied) >= 6:
            for threat in board.generate_legal_moves(~board.pawns):
                board.push(threat)
                try:
                    v_plus, captures_found = self.sprobe_capts(board, -beta, -alpha)
                    v = -v_plus
                finally:
                    board.pop()
                if captures_found and v > alpha:
                    threats_found = True
                    alpha = v
                    if alpha >= beta:
                        return (v, 3)

        v = self.probe_wdl_table(board)
        if v > alpha:
            return (v, 1)
        return (alpha, 3 if threats_found else 1)

    def close(self) -> None:
        """Close all loaded tables."""
        for table in self.wdl.values():
            table.close()
        for table in self.dtz.values():
            table.close()
        self.wdl.clear()
        self.dtz.clear()
        self.lru.clear()

    def __enter__(self) -> Tablebase:
        return self

    def __exit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_value: Optional[BaseException],
        traceback: Optional[TracebackType],
    ) -> None:
        self.close()


def open_tablebase(
    directory: str,
    *,
    load_wdl: bool = True,
    load_dtz: bool = True,
    max_fds: Optional[int] = 128,
    VariantBoard: Type[_Board] = _Board,
) -> Tablebase:
    """Open a Syzygy tablebase directory."""
    tablebase = Tablebase(max_fds=max_fds, VariantBoard=VariantBoard)
    tablebase.add_directory(directory, load_wdl=load_wdl, load_dtz=load_dtz)
    return tablebase
