"""Tests for dcs_chess.core.Piece (FR-C3)."""


class TestPiece:
    def test_symbol_white_pawn(self):
        from dcs_chess.core import Piece, PAWN, WHITE
        p = Piece(PAWN, WHITE)
        assert p.symbol() == "P"

    def test_symbol_black_queen(self):
        from dcs_chess.core import Piece, QUEEN, BLACK
        p = Piece(QUEEN, BLACK)
        assert p.symbol() == "q"

    def test_from_symbol(self):
        from dcs_chess.core import Piece
        p = Piece.from_symbol("N")
        assert p.symbol() == "N"

    def test_equality(self):
        from dcs_chess.core import Piece, ROOK, WHITE
        assert Piece(ROOK, WHITE) == Piece(ROOK, WHITE)

    def test_hashable(self):
        from dcs_chess.core import Piece, BISHOP, BLACK
        s = {Piece(BISHOP, BLACK)}
        assert len(s) == 1
