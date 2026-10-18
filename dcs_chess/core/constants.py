"""All FR-C1 constants: squares, colours, piece types, FEN, status flags, regex, and bitboards."""

from __future__ import annotations

import re
import typing

# ---------------------------------------------------------------------------
# Colours
# ---------------------------------------------------------------------------

WHITE: bool = True
BLACK: bool = False
COLORS: typing.List[bool] = [WHITE, BLACK]
COLOR_NAMES: typing.List[str] = ["black", "white"]

# ---------------------------------------------------------------------------
# Piece types (1–6, 0 reserved for "no piece type")
# ---------------------------------------------------------------------------

PAWN: int = 1
KNIGHT: int = 2
BISHOP: int = 3
ROOK: int = 4
QUEEN: int = 5
KING: int = 6

PIECE_TYPES: typing.List[int] = [PAWN, KNIGHT, BISHOP, ROOK, QUEEN, KING]
PIECE_SYMBOLS: typing.List[typing.Optional[str]] = [None, "p", "n", "b", "r", "q", "k"]
PIECE_NAMES: typing.List[typing.Optional[str]] = [
    None, "pawn", "knight", "bishop", "rook", "queen", "king",
]

UNICODE_PIECE_SYMBOLS: typing.Dict[str, str] = {
    "R": "♖", "r": "♜",
    "N": "♘", "n": "♞",
    "B": "♗", "b": "♝",
    "Q": "♕", "q": "♛",
    "K": "♔", "k": "♚",
    "P": "♙", "p": "♟",
}

# ---------------------------------------------------------------------------
# Squares  (a1 = 0, h8 = 63)
# ---------------------------------------------------------------------------

FILE_NAMES: typing.List[str] = ["a", "b", "c", "d", "e", "f", "g", "h"]
RANK_NAMES: typing.List[str] = ["1", "2", "3", "4", "5", "6", "7", "8"]

# Individual square constants A1..H8
A1, B1, C1, D1, E1, F1, G1, H1 = range(8)
A2, B2, C2, D2, E2, F2, G2, H2 = range(8, 16)
A3, B3, C3, D3, E3, F3, G3, H3 = range(16, 24)
A4, B4, C4, D4, E4, F4, G4, H4 = range(24, 32)
A5, B5, C5, D5, E5, F5, G5, H5 = range(32, 40)
A6, B6, C6, D6, E6, F6, G6, H6 = range(40, 48)
A7, B7, C7, D7, E7, F7, G7, H7 = range(48, 56)
A8, B8, C8, D8, E8, F8, G8, H8 = range(56, 64)

SQUARE_NAMES: typing.List[str] = [
    f + r for r in RANK_NAMES for f in FILE_NAMES
]

SQUARES: typing.List[int] = list(range(64))

# ---------------------------------------------------------------------------
# FEN constants
# ---------------------------------------------------------------------------

STARTING_BOARD_FEN: str = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR"
STARTING_FEN: str = STARTING_BOARD_FEN + " w KQkq - 0 1"

# ---------------------------------------------------------------------------
# Regex patterns
# ---------------------------------------------------------------------------

SAN_REGEX: re.Pattern[str] = re.compile(
    r"^([NBKRQ])?([a-h])?([1-8])?[\-x]?([a-h][1-8])(=?[nbrqkNBRQK])?[\+#]?\Z"
)

FEN_CASTLING_REGEX: re.Pattern[str] = re.compile(
    r"^(?:-|[KQABCDEFGH]{0,2}[kqabcdefgh]{0,2})\Z"
)

# ---------------------------------------------------------------------------
# Board status flags  (bitmask — powers of two so they compose with |)
# ---------------------------------------------------------------------------

STATUS_VALID: int = 0
STATUS_NO_WHITE_KING: int = 1 << 0
STATUS_NO_BLACK_KING: int = 1 << 1
STATUS_TOO_MANY_KINGS: int = 1 << 2
STATUS_TOO_MANY_WHITE_PAWNS: int = 1 << 3
STATUS_TOO_MANY_BLACK_PAWNS: int = 1 << 4
STATUS_PAWNS_ON_BACKRANK: int = 1 << 5
STATUS_TOO_MANY_WHITE_PIECES: int = 1 << 6
STATUS_TOO_MANY_BLACK_PIECES: int = 1 << 7
STATUS_BAD_CASTLING_RIGHTS: int = 1 << 8
STATUS_INVALID_EP_SQUARE: int = 1 << 9
STATUS_OPPOSITE_CHECK: int = 1 << 10
STATUS_EMPTY: int = 1 << 11
STATUS_RACE_CHECK: int = 1 << 12
STATUS_RACE_OVER: int = 1 << 13
STATUS_RACE_MATERIAL: int = 1 << 14
STATUS_TOO_MANY_CHECKERS: int = 1 << 15
STATUS_IMPOSSIBLE_CHECK: int = 1 << 16

# ---------------------------------------------------------------------------
# Bitboard constants and attack tables
# ---------------------------------------------------------------------------

BB_EMPTY: int = 0
BB_ALL: int = 0xFFFF_FFFF_FFFF_FFFF

BB_SQUARES: typing.List[int] = [1 << sq for sq in SQUARES]

(
    BB_A1, BB_B1, BB_C1, BB_D1, BB_E1, BB_F1, BB_G1, BB_H1,
    BB_A2, BB_B2, BB_C2, BB_D2, BB_E2, BB_F2, BB_G2, BB_H2,
    BB_A3, BB_B3, BB_C3, BB_D3, BB_E3, BB_F3, BB_G3, BB_H3,
    BB_A4, BB_B4, BB_C4, BB_D4, BB_E4, BB_F4, BB_G4, BB_H4,
    BB_A5, BB_B5, BB_C5, BB_D5, BB_E5, BB_F5, BB_G5, BB_H5,
    BB_A6, BB_B6, BB_C6, BB_D6, BB_E6, BB_F6, BB_G6, BB_H6,
    BB_A7, BB_B7, BB_C7, BB_D7, BB_E7, BB_F7, BB_G7, BB_H7,
    BB_A8, BB_B8, BB_C8, BB_D8, BB_E8, BB_F8, BB_G8, BB_H8,
) = BB_SQUARES

# File and rank masks
BB_FILES: typing.List[int] = [0x0101_0101_0101_0101 << i for i in range(8)]

(
    BB_FILE_A, BB_FILE_B, BB_FILE_C, BB_FILE_D,
    BB_FILE_E, BB_FILE_F, BB_FILE_G, BB_FILE_H,
) = BB_FILES

BB_RANKS: typing.List[int] = [0xFF << (8 * i) for i in range(8)]

(
    BB_RANK_1, BB_RANK_2, BB_RANK_3, BB_RANK_4,
    BB_RANK_5, BB_RANK_6, BB_RANK_7, BB_RANK_8,
) = BB_RANKS

# Derived area masks
BB_LIGHT_SQUARES: int = 0x55AA_55AA_55AA_55AA
BB_DARK_SQUARES: int = 0xAA55_AA55_AA55_AA55
BB_CORNERS: int = BB_A1 | BB_H1 | BB_A8 | BB_H8
BB_CENTER: int = BB_D4 | BB_E4 | BB_D5 | BB_E5
BB_BACKRANKS: int = BB_RANK_1 | BB_RANK_8


# ---------------------------------------------------------------------------
# Bit helpers (internal)
# ---------------------------------------------------------------------------

def _scan_forward(bb: int) -> typing.Iterator[int]:
    while bb:
        lsb = bb & -bb
        yield lsb.bit_length() - 1
        bb ^= lsb


# ---------------------------------------------------------------------------
# Knight and king attack tables
# ---------------------------------------------------------------------------

def _compute_knight_attacks() -> typing.List[int]:
    table: typing.List[int] = []
    for sq in SQUARES:
        bb = BB_SQUARES[sq]
        attacks = BB_EMPTY
        attacks |= (bb << 17) & ~BB_FILE_A
        attacks |= (bb << 15) & ~BB_FILE_H
        attacks |= (bb << 10) & ~(BB_FILE_A | BB_FILE_B)
        attacks |= (bb << 6)  & ~(BB_FILE_G | BB_FILE_H)
        attacks |= (bb >> 6)  & ~(BB_FILE_A | BB_FILE_B)
        attacks |= (bb >> 10) & ~(BB_FILE_G | BB_FILE_H)
        attacks |= (bb >> 15) & ~BB_FILE_A
        attacks |= (bb >> 17) & ~BB_FILE_H
        table.append(attacks & BB_ALL)
    return table


def _compute_king_attacks() -> typing.List[int]:
    table: typing.List[int] = []
    for sq in SQUARES:
        bb = BB_SQUARES[sq]
        attacks = BB_EMPTY
        attacks |= (bb << 8)
        attacks |= (bb >> 8)
        attacks |= (bb << 1) & ~BB_FILE_A
        attacks |= (bb >> 1) & ~BB_FILE_H
        attacks |= (bb << 9) & ~BB_FILE_A
        attacks |= (bb << 7) & ~BB_FILE_H
        attacks |= (bb >> 7) & ~BB_FILE_A
        attacks |= (bb >> 9) & ~BB_FILE_H
        table.append(attacks & BB_ALL)
    return table


BB_KNIGHT_ATTACKS: typing.List[int] = _compute_knight_attacks()
BB_KING_ATTACKS: typing.List[int] = _compute_king_attacks()

# ---------------------------------------------------------------------------
# Pawn attack tables  (indexed [color][square])
# ---------------------------------------------------------------------------

def _compute_pawn_attacks() -> typing.List[typing.List[int]]:
    white_table: typing.List[int] = []
    black_table: typing.List[int] = []
    for sq in SQUARES:
        bb = BB_SQUARES[sq]
        w_attacks = ((bb << 7) & ~BB_FILE_H) | ((bb << 9) & ~BB_FILE_A)
        white_table.append(w_attacks & BB_ALL)
        b_attacks = ((bb >> 7) & ~BB_FILE_A) | ((bb >> 9) & ~BB_FILE_H)
        black_table.append(b_attacks & BB_ALL)
    return [black_table, white_table]


BB_PAWN_ATTACKS: typing.List[typing.List[int]] = _compute_pawn_attacks()

# ---------------------------------------------------------------------------
# Sliding-piece masks and attack tables
# ---------------------------------------------------------------------------

def _carry_rippler(mask: int) -> typing.Iterator[int]:
    subset = BB_EMPTY
    while True:
        yield subset
        subset = (subset - mask) & mask
        if not subset:
            break


def _sliding_attacks(sq: int, occupied: int, deltas: typing.List[int]) -> int:
    attacks = BB_EMPTY
    for delta in deltas:
        s = sq
        while True:
            s += delta
            if s < 0 or s > 63:
                break
            if abs((s % 8) - ((s - delta) % 8)) > 2:
                break
            attacks |= BB_SQUARES[s]
            if occupied & BB_SQUARES[s]:
                break
    return attacks


def _compute_sliding_tables(
    deltas: typing.List[int],
) -> typing.Tuple[typing.List[int], typing.List[typing.Dict[int, int]]]:
    masks: typing.List[int] = []
    tables: typing.List[typing.Dict[int, int]] = []
    for sq in SQUARES:
        full_attacks = _sliding_attacks(sq, BB_EMPTY, deltas)
        edges = ((BB_RANK_1 | BB_RANK_8) & ~BB_RANKS[sq >> 3]) | \
                ((BB_FILE_A | BB_FILE_H) & ~BB_FILES[sq & 7])
        mask = full_attacks & ~edges
        masks.append(mask)

        attack_table: typing.Dict[int, int] = {}
        for subset in _carry_rippler(mask):
            attack_table[subset] = _sliding_attacks(sq, subset, deltas)
        tables.append(attack_table)
    return masks, tables


BB_DIAG_MASKS: typing.List[int]
BB_DIAG_ATTACKS: typing.List[typing.Dict[int, int]]
BB_DIAG_MASKS, BB_DIAG_ATTACKS = _compute_sliding_tables([-9, -7, 7, 9])

BB_FILE_MASKS: typing.List[int]
BB_FILE_ATTACKS: typing.List[typing.Dict[int, int]]
BB_FILE_MASKS, BB_FILE_ATTACKS = _compute_sliding_tables([-8, 8])

BB_RANK_MASKS: typing.List[int]
BB_RANK_ATTACKS: typing.List[typing.Dict[int, int]]
BB_RANK_MASKS, BB_RANK_ATTACKS = _compute_sliding_tables([-1, 1])

# ---------------------------------------------------------------------------
# Ray table
# ---------------------------------------------------------------------------

def _compute_rays() -> typing.List[typing.List[int]]:
    rays: typing.List[typing.List[int]] = [[BB_EMPTY] * 64 for _ in range(64)]
    for a in SQUARES:
        for delta_group in [(-9, 9), (-7, 7), (-8, 8), (-1, 1)]:
            ray = BB_SQUARES[a]
            for delta in delta_group:
                s = a
                while True:
                    s += delta
                    if s < 0 or s > 63:
                        break
                    if abs((s % 8) - ((s - delta) % 8)) > 2:
                        break
                    ray |= BB_SQUARES[s]
            for b in _scan_forward(ray & ~BB_SQUARES[a]):
                rays[a][b] = ray
    return rays


BB_RAYS: typing.List[typing.List[int]] = _compute_rays()
