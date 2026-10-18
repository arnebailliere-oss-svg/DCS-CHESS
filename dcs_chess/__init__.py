"""DCS Chess Toolkit — a proprietary chess library for DCS Analytics."""

import typing
from typing import Iterable, Union

Color = bool
PieceType = int
Square = int
Bitboard = int

from .core import (
    WHITE, BLACK, COLORS, COLOR_NAMES,
    PAWN, KNIGHT, BISHOP, ROOK, QUEEN, KING,
    PIECE_TYPES, PIECE_SYMBOLS, PIECE_NAMES, UNICODE_PIECE_SYMBOLS,
    A1, B1, C1, D1, E1, F1, G1, H1,
    A2, B2, C2, D2, E2, F2, G2, H2,
    A3, B3, C3, D3, E3, F3, G3, H3,
    A4, B4, C4, D4, E4, F4, G4, H4,
    A5, B5, C5, D5, E5, F5, G5, H5,
    A6, B6, C6, D6, E6, F6, G6, H6,
    A7, B7, C7, D7, E7, F7, G7, H7,
    A8, B8, C8, D8, E8, F8, G8, H8,
    SQUARES, SQUARE_NAMES, FILE_NAMES, RANK_NAMES,
    STARTING_FEN, STARTING_BOARD_FEN,
    SAN_REGEX, FEN_CASTLING_REGEX,
    STATUS_VALID, STATUS_NO_WHITE_KING, STATUS_NO_BLACK_KING,
    STATUS_TOO_MANY_KINGS, STATUS_TOO_MANY_WHITE_PAWNS,
    STATUS_TOO_MANY_BLACK_PAWNS, STATUS_PAWNS_ON_BACKRANK,
    STATUS_TOO_MANY_WHITE_PIECES, STATUS_TOO_MANY_BLACK_PIECES,
    STATUS_BAD_CASTLING_RIGHTS, STATUS_INVALID_EP_SQUARE,
    STATUS_OPPOSITE_CHECK, STATUS_EMPTY,
    STATUS_RACE_CHECK, STATUS_RACE_OVER, STATUS_RACE_MATERIAL,
    STATUS_TOO_MANY_CHECKERS, STATUS_IMPOSSIBLE_CHECK,
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
    square, square_file, square_rank, square_name, parse_square,
    square_distance, square_manhattan_distance, square_knight_distance,
    square_mirror,
    piece_symbol, piece_name,
    lsb, msb, scan_forward, scan_reversed, popcount,
    shift_up, shift_down, shift_left, shift_right,
    shift_2_up, shift_2_down, shift_2_left, shift_2_right,
    shift_up_left, shift_up_right, shift_down_left, shift_down_right,
    flip_vertical, flip_horizontal, flip_diagonal, flip_anti_diagonal,
    ray, between,
    Piece, Move, SquareSet, BaseBoard,
    Board, LegalMoveGenerator, PseudoLegalMoveGenerator,
    Status, Termination, Outcome,
    IllegalMoveError, InvalidMoveError, AmbiguousMoveError,
)

SQUARES_180: typing.List[int] = [square_mirror(sq) for sq in SQUARES]

IntoSquareSet = Union[SquareSet, Iterable[Square]]
