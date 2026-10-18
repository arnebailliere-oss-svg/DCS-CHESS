"""Differential tests for CORE-001: constants (FR-C1).

Every constant, square name, piece type, status flag, bitboard table, and
regex pattern in dcs_chess.core.constants must match the reference library
value exactly.
"""

from __future__ import annotations

import re

import chess as ref
import pytest

import dcs_chess.core as dcs


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _public_names(module) -> set[str]:
    """Return the set of uppercase / ALL_CAPS public names in *module*."""
    return {
        n for n in dir(module)
        if not n.startswith("_") and (n[0].isupper() or n.isupper())
    }


# ---------------------------------------------------------------------------
# Colours
# ---------------------------------------------------------------------------

class TestColours:
    def test_white(self):
        assert dcs.WHITE is ref.WHITE

    def test_black(self):
        assert dcs.BLACK is ref.BLACK

    def test_colors(self):
        assert dcs.COLORS == ref.COLORS

    def test_color_names(self):
        assert dcs.COLOR_NAMES == ref.COLOR_NAMES


# ---------------------------------------------------------------------------
# Piece types
# ---------------------------------------------------------------------------

class TestPieceTypes:
    @pytest.mark.parametrize("name", ["PAWN", "KNIGHT", "BISHOP", "ROOK", "QUEEN", "KING"])
    def test_piece_type_value(self, name: str):
        assert getattr(dcs, name) == getattr(ref, name)

    def test_piece_types_list(self):
        assert dcs.PIECE_TYPES == ref.PIECE_TYPES

    def test_piece_symbols(self):
        assert dcs.PIECE_SYMBOLS == ref.PIECE_SYMBOLS

    def test_piece_names(self):
        assert dcs.PIECE_NAMES == ref.PIECE_NAMES

    def test_unicode_piece_symbols(self):
        assert dcs.UNICODE_PIECE_SYMBOLS == ref.UNICODE_PIECE_SYMBOLS


# ---------------------------------------------------------------------------
# Squares
# ---------------------------------------------------------------------------

class TestSquares:
    @pytest.mark.parametrize("sq", range(64))
    def test_square_constant(self, sq: int):
        name = ref.SQUARE_NAMES[sq].upper()
        assert getattr(dcs, name) == getattr(ref, name)

    def test_squares_list(self):
        assert dcs.SQUARES == ref.SQUARES

    def test_square_names(self):
        assert dcs.SQUARE_NAMES == ref.SQUARE_NAMES

    def test_file_names(self):
        assert dcs.FILE_NAMES == ref.FILE_NAMES

    def test_rank_names(self):
        assert dcs.RANK_NAMES == ref.RANK_NAMES


# ---------------------------------------------------------------------------
# FEN constants
# ---------------------------------------------------------------------------

class TestFEN:
    def test_starting_fen(self):
        assert dcs.STARTING_FEN == ref.STARTING_FEN

    def test_starting_board_fen(self):
        assert dcs.STARTING_BOARD_FEN == ref.STARTING_BOARD_FEN


# ---------------------------------------------------------------------------
# Regex patterns
# ---------------------------------------------------------------------------

class TestRegex:
    def test_san_regex_pattern(self):
        assert dcs.SAN_REGEX.pattern == ref.SAN_REGEX.pattern

    def test_fen_castling_regex_pattern(self):
        assert dcs.FEN_CASTLING_REGEX.pattern == ref.FEN_CASTLING_REGEX.pattern

    @pytest.mark.parametrize("san", [
        "e4", "Nf3", "Bxe5", "O-O", "Qh4+", "Rxa1", "exd5",
        "e8=Q", "bxa1=N", "Kd2", "Nbd2", "R1a3", "Qh4#",
    ])
    def test_san_regex_matches(self, san: str):
        ref_match = ref.SAN_REGEX.match(san)
        dcs_match = dcs.SAN_REGEX.match(san)
        if ref_match:
            assert dcs_match is not None, f"DCS failed to match '{san}'"
            assert ref_match.groups() == dcs_match.groups()
        else:
            assert dcs_match is None, f"DCS matched '{san}' but ref did not"

    @pytest.mark.parametrize("castling", [
        "-", "K", "Qk", "KQkq", "Bq", "ACac", "INVALID_NOT_MATCHING",
    ])
    def test_fen_castling_regex_matches(self, castling: str):
        ref_match = ref.FEN_CASTLING_REGEX.match(castling)
        dcs_match = dcs.FEN_CASTLING_REGEX.match(castling)
        if ref_match:
            assert dcs_match is not None
        else:
            assert dcs_match is None


# ---------------------------------------------------------------------------
# Status flags
# ---------------------------------------------------------------------------

_STATUS_NAMES = [
    "STATUS_VALID",
    "STATUS_NO_WHITE_KING",
    "STATUS_NO_BLACK_KING",
    "STATUS_TOO_MANY_KINGS",
    "STATUS_TOO_MANY_WHITE_PAWNS",
    "STATUS_TOO_MANY_BLACK_PAWNS",
    "STATUS_PAWNS_ON_BACKRANK",
    "STATUS_TOO_MANY_WHITE_PIECES",
    "STATUS_TOO_MANY_BLACK_PIECES",
    "STATUS_BAD_CASTLING_RIGHTS",
    "STATUS_INVALID_EP_SQUARE",
    "STATUS_OPPOSITE_CHECK",
    "STATUS_EMPTY",
    "STATUS_RACE_CHECK",
    "STATUS_RACE_OVER",
    "STATUS_RACE_MATERIAL",
    "STATUS_TOO_MANY_CHECKERS",
    "STATUS_IMPOSSIBLE_CHECK",
]


class TestStatusFlags:
    @pytest.mark.parametrize("name", _STATUS_NAMES)
    def test_status_flag_value(self, name: str):
        assert getattr(dcs, name) == getattr(ref, name), (
            f"{name}: dcs={getattr(dcs, name)}, ref={getattr(ref, name)}"
        )


# ---------------------------------------------------------------------------
# Bitboard constants (will be tested when CORE-002 lands)
# ---------------------------------------------------------------------------

_BB_SCALAR_NAMES = [
    "BB_EMPTY", "BB_ALL",
    "BB_LIGHT_SQUARES", "BB_DARK_SQUARES",
    "BB_CORNERS", "BB_CENTER", "BB_BACKRANKS",
]

_BB_FILE_NAMES = [f"BB_FILE_{c}" for c in "ABCDEFGH"]
_BB_RANK_NAMES = [f"BB_RANK_{n}" for n in range(1, 9)]


class TestBitboardConstants:
    """These tests will pass once CORE-002 is implemented."""

    @pytest.mark.parametrize("name", _BB_SCALAR_NAMES)
    def test_bb_scalar(self, name: str):
        dcs_val = getattr(dcs, name, None)
        if dcs_val is None:
            pytest.skip(f"{name} not yet implemented")
        assert dcs_val == getattr(ref, name), f"{name} mismatch"

    @pytest.mark.parametrize("name", _BB_FILE_NAMES + _BB_RANK_NAMES)
    def test_bb_file_rank(self, name: str):
        dcs_val = getattr(dcs, name, None)
        if dcs_val is None:
            pytest.skip(f"{name} not yet implemented")
        assert dcs_val == getattr(ref, name), f"{name} mismatch"

    def test_bb_squares(self):
        bb_sq = getattr(dcs, "BB_SQUARES", None)
        if bb_sq is None:
            pytest.skip("BB_SQUARES not yet implemented")
        assert len(bb_sq) == 64
        for i in range(64):
            assert bb_sq[i] == ref.BB_SQUARES[i], f"BB_SQUARES[{i}] mismatch"

    def test_bb_files(self):
        bb = getattr(dcs, "BB_FILES", None)
        if bb is None:
            pytest.skip("BB_FILES not yet implemented")
        for i in range(8):
            assert bb[i] == ref.BB_FILES[i], f"BB_FILES[{i}] mismatch"

    def test_bb_ranks(self):
        bb = getattr(dcs, "BB_RANKS", None)
        if bb is None:
            pytest.skip("BB_RANKS not yet implemented")
        for i in range(8):
            assert bb[i] == ref.BB_RANKS[i], f"BB_RANKS[{i}] mismatch"


# ---------------------------------------------------------------------------
# Bitboard attack tables (CORE-002)
# ---------------------------------------------------------------------------

class TestBitboardAttackTables:
    def test_bb_knight_attacks(self):
        tbl = getattr(dcs, "BB_KNIGHT_ATTACKS", None)
        if tbl is None:
            pytest.skip("BB_KNIGHT_ATTACKS not yet implemented")
        assert len(tbl) == 64
        for sq in range(64):
            assert tbl[sq] == ref.BB_KNIGHT_ATTACKS[sq], f"knight attacks[{sq}] mismatch"

    def test_bb_king_attacks(self):
        tbl = getattr(dcs, "BB_KING_ATTACKS", None)
        if tbl is None:
            pytest.skip("BB_KING_ATTACKS not yet implemented")
        assert len(tbl) == 64
        for sq in range(64):
            assert tbl[sq] == ref.BB_KING_ATTACKS[sq], f"king attacks[{sq}] mismatch"

    @pytest.mark.parametrize("color", [True, False])
    def test_bb_pawn_attacks(self, color: bool):
        tbl = getattr(dcs, "BB_PAWN_ATTACKS", None)
        if tbl is None:
            pytest.skip("BB_PAWN_ATTACKS not yet implemented")
        for sq in range(64):
            assert tbl[color][sq] == ref.BB_PAWN_ATTACKS[color][sq], (
                f"pawn attacks[{color}][{sq}] mismatch"
            )

    def test_bb_rays(self):
        tbl = getattr(dcs, "BB_RAYS", None)
        if tbl is None:
            pytest.skip("BB_RAYS not yet implemented")
        for a in range(64):
            for b in range(64):
                assert tbl[a][b] == ref.BB_RAYS[a][b], f"rays[{a}][{b}] mismatch"

    @pytest.mark.parametrize("table_name", [
        "BB_DIAG_MASKS", "BB_FILE_MASKS", "BB_RANK_MASKS",
    ])
    def test_bb_masks(self, table_name: str):
        tbl = getattr(dcs, table_name, None)
        if tbl is None:
            pytest.skip(f"{table_name} not yet implemented")
        ref_tbl = getattr(ref, table_name)
        assert len(tbl) == 64
        for sq in range(64):
            assert tbl[sq] == ref_tbl[sq], f"{table_name}[{sq}] mismatch"

    @pytest.mark.parametrize("table_name", [
        "BB_DIAG_ATTACKS", "BB_FILE_ATTACKS", "BB_RANK_ATTACKS",
    ])
    def test_bb_sliding_attacks(self, table_name: str):
        tbl = getattr(dcs, table_name, None)
        if tbl is None:
            pytest.skip(f"{table_name} not yet implemented")
        ref_tbl = getattr(ref, table_name)
        assert len(tbl) == 64
        for sq in range(64):
            assert set(tbl[sq].keys()) == set(ref_tbl[sq].keys()), (
                f"{table_name}[{sq}] key set mismatch"
            )
            for occ, attacks in ref_tbl[sq].items():
                assert tbl[sq][occ] == attacks, (
                    f"{table_name}[{sq}][0x{occ:016x}] mismatch"
                )


# ---------------------------------------------------------------------------
# Completeness: every FR-C1 constant in the spec must exist
# ---------------------------------------------------------------------------

_REQUIRED_FR_C1_NAMES = {
    "WHITE", "BLACK", "COLORS", "COLOR_NAMES",
    "PAWN", "KNIGHT", "BISHOP", "ROOK", "QUEEN", "KING",
    "PIECE_TYPES", "PIECE_SYMBOLS", "PIECE_NAMES", "UNICODE_PIECE_SYMBOLS",
    "STARTING_FEN", "STARTING_BOARD_FEN",
    "SAN_REGEX", "FEN_CASTLING_REGEX",
    "FILE_NAMES", "RANK_NAMES", "SQUARE_NAMES", "SQUARES",
    *[f"{c}{r}" for r in "12345678" for c in "ABCDEFGH"],
    *_STATUS_NAMES,
    *_BB_SCALAR_NAMES,
    *_BB_FILE_NAMES,
    *_BB_RANK_NAMES,
    "BB_SQUARES", "BB_FILES", "BB_RANKS",
    "BB_KNIGHT_ATTACKS", "BB_KING_ATTACKS", "BB_PAWN_ATTACKS",
    "BB_DIAG_MASKS", "BB_FILE_MASKS", "BB_RANK_MASKS",
    "BB_DIAG_ATTACKS", "BB_FILE_ATTACKS", "BB_RANK_ATTACKS",
    "BB_RAYS",
}


class TestCompleteness:
    @pytest.mark.parametrize("name", sorted(_REQUIRED_FR_C1_NAMES))
    def test_constant_exists(self, name: str):
        assert hasattr(dcs, name), f"Missing constant: {name}"
