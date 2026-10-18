"""Tests for dcs_chess.core constants (FR-C1)."""


class TestSquareConstants:
    """Squares A1..H8 as integers 0..63."""

    def test_a1_is_zero(self):
        from dcs_chess.core import A1
        assert A1 == 0

    def test_h8_is_63(self):
        from dcs_chess.core import H8
        assert H8 == 63

    def test_squares_length(self):
        from dcs_chess.core import SQUARES
        assert len(SQUARES) == 64


class TestColorConstants:
    """WHITE = True, BLACK = False."""

    def test_white_is_true(self):
        from dcs_chess.core import WHITE
        assert WHITE is True

    def test_black_is_false(self):
        from dcs_chess.core import BLACK
        assert BLACK is False


class TestPieceTypeConstants:
    """PAWN=1 .. KING=6."""

    def test_pawn_is_one(self):
        from dcs_chess.core import PAWN
        assert PAWN == 1

    def test_king_is_six(self):
        from dcs_chess.core import KING
        assert KING == 6

    def test_piece_types_length(self):
        from dcs_chess.core import PIECE_TYPES
        assert len(PIECE_TYPES) == 6


class TestStartingFen:
    def test_starting_fen_value(self):
        from dcs_chess.core import STARTING_FEN
        assert STARTING_FEN == "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"


class TestBitboardConstants:
    def test_bb_empty(self):
        from dcs_chess.core import BB_EMPTY
        assert BB_EMPTY == 0

    def test_bb_all(self):
        from dcs_chess.core import BB_ALL
        assert BB_ALL == (1 << 64) - 1
