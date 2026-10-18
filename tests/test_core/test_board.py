"""Tests for dcs_chess.core.Board (FR-C7) — basic smoke tests."""


class TestBoardInit:
    def test_starting_position_fen(self):
        from dcs_chess.core import Board, STARTING_FEN
        b = Board()
        assert b.fen() == STARTING_FEN

    def test_turn_white(self):
        from dcs_chess.core import Board, WHITE
        b = Board()
        assert b.turn == WHITE

    def test_legal_moves_starting(self):
        from dcs_chess.core import Board
        b = Board()
        assert len(list(b.legal_moves)) == 20


class TestBoardMoves:
    def test_push_pop(self):
        from dcs_chess.core import Board, Move
        b = Board()
        m = Move.from_uci("e2e4")
        b.push(m)
        assert b.turn is False  # BLACK
        b.pop()
        assert b.turn is True  # WHITE

    def test_is_checkmate_fools_mate(self):
        from dcs_chess.core import Board
        b = Board()
        for uci in ["f2f3", "e7e5", "g2g4", "d8h4"]:
            from dcs_chess.core import Move
            b.push(Move.from_uci(uci))
        assert b.is_checkmate()

    def test_is_game_over_fools_mate(self):
        from dcs_chess.core import Board
        b = Board()
        for uci in ["f2f3", "e7e5", "g2g4", "d8h4"]:
            from dcs_chess.core import Move
            b.push(Move.from_uci(uci))
        assert b.is_game_over()


class TestBoardFen:
    def test_set_fen_roundtrip(self):
        from dcs_chess.core import Board
        fen = "rnbqkbnr/pp1ppppp/8/2p5/4P3/8/PPPP1PPP/RNBQKBNR w KQkq - 0 2"
        b = Board(fen)
        assert b.fen() == fen

    def test_set_fen_roundtrip_with_ep(self):
        from dcs_chess.core import Board
        fen = "rnbqkbnr/pp1ppppp/8/2p5/4P3/8/PPPP1PPP/RNBQKBNR w KQkq c6 0 2"
        b = Board(fen)
        assert b.fen(en_passant="fen") == fen


class TestBoardSan:
    def test_san_e4(self):
        from dcs_chess.core import Board, Move
        b = Board()
        m = Move.from_uci("e2e4")
        assert b.san(m) == "e4"
