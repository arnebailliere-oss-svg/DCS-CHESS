"""Tests for dcs_chess.core.Move (FR-C4)."""


class TestMove:
    def test_uci_normal(self):
        from dcs_chess.core import Move
        m = Move.from_uci("e2e4")
        assert m.uci() == "e2e4"
        assert m.from_square == 12  # e2
        assert m.to_square == 28  # e4

    def test_uci_promotion(self):
        from dcs_chess.core import Move
        m = Move.from_uci("e7e8q")
        assert m.uci() == "e7e8q"
        assert m.promotion is not None

    def test_null_move(self):
        from dcs_chess.core import Move
        null = Move.null()
        assert null.uci() == "0000"
        assert not null  # falsy

    def test_equality_and_hash(self):
        from dcs_chess.core import Move
        a = Move.from_uci("e2e4")
        b = Move.from_uci("e2e4")
        assert a == b
        assert hash(a) == hash(b)

    def test_xboard_null(self):
        from dcs_chess.core import Move
        null = Move.null()
        assert null.xboard() == "@@@@"
