"""Tests for dcs_chess.core functions (FR-C2)."""


class TestSquareFunctions:
    def test_square_from_file_rank(self):
        from dcs_chess.core import square
        assert square(0, 0) == 0  # a1
        assert square(7, 7) == 63  # h8
        assert square(4, 3) == 28  # e4

    def test_square_file(self):
        from dcs_chess.core import square_file
        assert square_file(0) == 0  # a1 -> file a
        assert square_file(63) == 7  # h8 -> file h

    def test_square_rank(self):
        from dcs_chess.core import square_rank
        assert square_rank(0) == 0  # a1 -> rank 1
        assert square_rank(63) == 7  # h8 -> rank 8

    def test_square_name(self):
        from dcs_chess.core import square_name
        assert square_name(0) == "a1"
        assert square_name(63) == "h8"

    def test_parse_square(self):
        from dcs_chess.core import parse_square
        assert parse_square("a1") == 0
        assert parse_square("h8") == 63
        assert parse_square("e4") == 28

    def test_square_distance(self):
        from dcs_chess.core import square_distance
        assert square_distance(0, 63) == 7  # a1 to h8: king steps
        assert square_distance(0, 0) == 0

    def test_square_mirror(self):
        from dcs_chess.core import square_mirror
        assert square_mirror(0) == 56  # a1 -> a8
        assert square_mirror(63) == 7  # h8 -> h1


class TestBitboardFunctions:
    def test_lsb(self):
        from dcs_chess.core import lsb
        assert lsb(0b1010) == 1

    def test_msb(self):
        from dcs_chess.core import msb
        assert msb(0b1010) == 3

    def test_scan_forward(self):
        from dcs_chess.core import scan_forward
        assert list(scan_forward(0b1010)) == [1, 3]

    def test_scan_reversed(self):
        from dcs_chess.core import scan_reversed
        assert list(scan_reversed(0b1010)) == [3, 1]

    def test_flip_vertical(self):
        from dcs_chess.core import flip_vertical, BB_RANK_1, BB_RANK_8
        assert flip_vertical(BB_RANK_1) == BB_RANK_8
