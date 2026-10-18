"""Differential tests for CORE-003: functions (FR-C2).

Every function in dcs_chess.core.functions must match the reference library
output for all inputs.
"""

from __future__ import annotations

import chess as ref
import pytest

import dcs_chess.core as dcs


# ---------------------------------------------------------------------------
# Square functions
# ---------------------------------------------------------------------------

class TestSquareFunctions:
    @pytest.mark.parametrize("f", range(8))
    @pytest.mark.parametrize("r", range(8))
    def test_square(self, f: int, r: int):
        assert dcs.square(f, r) == ref.square(f, r)

    @pytest.mark.parametrize("sq", range(64))
    def test_square_file(self, sq: int):
        assert dcs.square_file(sq) == ref.square_file(sq)

    @pytest.mark.parametrize("sq", range(64))
    def test_square_rank(self, sq: int):
        assert dcs.square_rank(sq) == ref.square_rank(sq)

    @pytest.mark.parametrize("sq", range(64))
    def test_square_name(self, sq: int):
        assert dcs.square_name(sq) == ref.square_name(sq)

    @pytest.mark.parametrize("name", ref.SQUARE_NAMES)
    def test_parse_square(self, name: str):
        assert dcs.parse_square(name) == ref.parse_square(name)

    @pytest.mark.parametrize("bad", ["", "i1", "a9", "a0", "xx", "abc"])
    def test_parse_square_errors(self, bad: str):
        with pytest.raises(ValueError):
            dcs.parse_square(bad)

    @pytest.mark.parametrize("a", range(64))
    @pytest.mark.parametrize("b", [0, 7, 27, 35, 56, 63])
    def test_square_distance(self, a: int, b: int):
        assert dcs.square_distance(a, b) == ref.square_distance(a, b)

    @pytest.mark.parametrize("a", range(64))
    @pytest.mark.parametrize("b", [0, 7, 27, 35, 56, 63])
    def test_square_manhattan_distance(self, a: int, b: int):
        assert dcs.square_manhattan_distance(a, b) == ref.square_manhattan_distance(a, b)

    @pytest.mark.parametrize("a", range(64))
    @pytest.mark.parametrize("b", range(64))
    def test_square_knight_distance(self, a: int, b: int):
        assert dcs.square_knight_distance(a, b) == ref.square_knight_distance(a, b)

    @pytest.mark.parametrize("sq", range(64))
    def test_square_mirror(self, sq: int):
        assert dcs.square_mirror(sq) == ref.square_mirror(sq)


# ---------------------------------------------------------------------------
# Piece symbol/name
# ---------------------------------------------------------------------------

class TestPieceSymbolName:
    @pytest.mark.parametrize("pt", range(1, 7))
    def test_piece_symbol(self, pt: int):
        assert dcs.piece_symbol(pt) == ref.piece_symbol(pt)

    @pytest.mark.parametrize("pt", range(1, 7))
    def test_piece_name(self, pt: int):
        assert dcs.piece_name(pt) == ref.piece_name(pt)


# ---------------------------------------------------------------------------
# Bitboard scan functions
# ---------------------------------------------------------------------------

class TestScanFunctions:
    _TEST_MASKS = [
        0, 1, 0x8000000000000000, 0xFF, 0xFF00, 0xFFFFFFFFFFFFFFFF,
        0x0101010101010101, 0x8040201008040201, 0xAAAAAAAAAAAAAAAA,
    ]

    @pytest.mark.parametrize("bb", _TEST_MASKS)
    def test_lsb(self, bb: int):
        assert dcs.lsb(bb) == ref.lsb(bb)

    @pytest.mark.parametrize("bb", _TEST_MASKS)
    def test_msb(self, bb: int):
        assert dcs.msb(bb) == ref.msb(bb)

    @pytest.mark.parametrize("bb", _TEST_MASKS)
    def test_scan_forward(self, bb: int):
        assert list(dcs.scan_forward(bb)) == list(ref.scan_forward(bb))

    @pytest.mark.parametrize("bb", _TEST_MASKS)
    def test_scan_reversed(self, bb: int):
        assert list(dcs.scan_reversed(bb)) == list(ref.scan_reversed(bb))

    @pytest.mark.parametrize("bb", _TEST_MASKS)
    def test_popcount(self, bb: int):
        assert dcs.popcount(bb) == ref.popcount(bb)


# ---------------------------------------------------------------------------
# Shift functions
# ---------------------------------------------------------------------------

_SHIFT_FUNCS = [
    "shift_up", "shift_down", "shift_left", "shift_right",
    "shift_2_up", "shift_2_down", "shift_2_left", "shift_2_right",
    "shift_up_left", "shift_up_right", "shift_down_left", "shift_down_right",
]

_SHIFT_TEST_MASKS = [
    0x0000000000000001,  # a1
    0x8000000000000000,  # h8
    0x0000000000000080,  # h1
    0x0100000000000000,  # a8
    0x0000001818000000,  # center 4 squares
    0xFF000000000000FF,  # rank 1 + rank 8
    0x0101010101010101,  # file a
    0x8080808080808080,  # file h
    0xFFFFFFFFFFFFFFFF,  # all squares
    0,                   # empty
]


class TestShiftFunctions:
    @pytest.mark.parametrize("fn_name", _SHIFT_FUNCS)
    @pytest.mark.parametrize("bb", _SHIFT_TEST_MASKS)
    def test_shift(self, fn_name: str, bb: int):
        dcs_fn = getattr(dcs, fn_name)
        ref_fn = getattr(ref, fn_name)
        assert dcs_fn(bb) == ref_fn(bb), f"{fn_name}(0x{bb:016x}) mismatch"


# ---------------------------------------------------------------------------
# Flip functions
# ---------------------------------------------------------------------------

_FLIP_FUNCS = [
    "flip_vertical", "flip_horizontal", "flip_diagonal", "flip_anti_diagonal",
]


class TestFlipFunctions:
    @pytest.mark.parametrize("fn_name", _FLIP_FUNCS)
    @pytest.mark.parametrize("bb", _SHIFT_TEST_MASKS + [
        0x00000000000000FF,  # rank 1
        0x0000000000008040,  # two diagonal squares
        0x0102040810204080,  # main diagonal
    ])
    def test_flip(self, fn_name: str, bb: int):
        dcs_fn = getattr(dcs, fn_name)
        ref_fn = getattr(ref, fn_name)
        assert dcs_fn(bb) == ref_fn(bb), f"{fn_name}(0x{bb:016x}) mismatch"


# ---------------------------------------------------------------------------
# Ray and between
# ---------------------------------------------------------------------------

class TestRayBetween:
    @pytest.mark.parametrize("a", range(64))
    @pytest.mark.parametrize("b", [0, 7, 9, 27, 36, 54, 56, 63])
    def test_ray(self, a: int, b: int):
        assert dcs.ray(a, b) == ref.ray(a, b)

    @pytest.mark.parametrize("a", range(64))
    @pytest.mark.parametrize("b", [0, 7, 9, 27, 36, 54, 56, 63])
    def test_between(self, a: int, b: int):
        assert dcs.between(a, b) == ref.between(a, b)

    def test_between_same_square(self):
        for sq in range(64):
            assert dcs.between(sq, sq) == ref.between(sq, sq)

    def test_between_adjacent(self):
        for a in range(64):
            for b in range(64):
                if ref.square_distance(a, b) == 1:
                    assert dcs.between(a, b) == ref.between(a, b)
