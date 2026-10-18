"""Re-exports bitboard constants from constants.py for convenience.

All BB_* names live in constants.py (FR-C1 groups them together).
This module exists so that ``from dcs_chess.core.bitboards import ...``
still works.
"""

from .constants import (  # noqa: F401
    BB_EMPTY, BB_ALL, BB_SQUARES,
    BB_A1, BB_B1, BB_C1, BB_D1, BB_E1, BB_F1, BB_G1, BB_H1,
    BB_A2, BB_B2, BB_C2, BB_D2, BB_E2, BB_F2, BB_G2, BB_H2,
    BB_A3, BB_B3, BB_C3, BB_D3, BB_E3, BB_F3, BB_G3, BB_H3,
    BB_A4, BB_B4, BB_C4, BB_D4, BB_E4, BB_F4, BB_G4, BB_H4,
    BB_A5, BB_B5, BB_C5, BB_D5, BB_E5, BB_F5, BB_G5, BB_H5,
    BB_A6, BB_B6, BB_C6, BB_D6, BB_E6, BB_F6, BB_G6, BB_H6,
    BB_A7, BB_B7, BB_C7, BB_D7, BB_E7, BB_F7, BB_G7, BB_H7,
    BB_A8, BB_B8, BB_C8, BB_D8, BB_E8, BB_F8, BB_G8, BB_H8,
    BB_FILES, BB_FILE_A, BB_FILE_B, BB_FILE_C, BB_FILE_D,
    BB_FILE_E, BB_FILE_F, BB_FILE_G, BB_FILE_H,
    BB_RANKS, BB_RANK_1, BB_RANK_2, BB_RANK_3, BB_RANK_4,
    BB_RANK_5, BB_RANK_6, BB_RANK_7, BB_RANK_8,
    BB_LIGHT_SQUARES, BB_DARK_SQUARES,
    BB_CORNERS, BB_CENTER, BB_BACKRANKS,
    BB_KNIGHT_ATTACKS, BB_KING_ATTACKS, BB_PAWN_ATTACKS,
    BB_DIAG_MASKS, BB_DIAG_ATTACKS,
    BB_FILE_MASKS, BB_FILE_ATTACKS,
    BB_RANK_MASKS, BB_RANK_ATTACKS,
    BB_RAYS,
)
