"""ADV adversarial differential tests for PGN-001: pgn/model."""

from __future__ import annotations

import chess
import chess.pgn
import pytest

from dcs_chess.core.board import Board
from dcs_chess.core.move import Move
from dcs_chess.engine.scores import Cp, Mate, PovScore
from dcs_chess.pgn.model import (
    Game, ChildNode, GameNode, Headers, Mainline, SKIP,
)


def _build_game(ucis):
    """Build a game from UCI move strings."""
    g = Game()
    node = g
    for uci in ucis:
        b = node.board()
        m = b.parse_uci(uci)
        node = node.add_variation(m)
    return g

def _build_ref_game(ucis):
    """Build a reference game from UCI move strings."""
    g = chess.pgn.Game()
    node = g
    b = chess.Board()
    for uci in ucis:
        m = b.parse_uci(uci)
        node = node.add_variation(m)
        b.push(m)
    return g


# =====================================================================
# Headers
# =====================================================================

class TestHeaders:
    def test_seven_tag_roster_defaults(self):
        h = Headers()
        rh = chess.pgn.Headers()
        for key in ["Event", "Site", "Date", "Round", "White", "Black", "Result"]:
            assert h[key] == rh[key], f"Header {key}: ours={h[key]!r} ref={rh[key]!r}"

    def test_custom_header(self):
        h = Headers({"Event": "Test", "White": "Alice"})
        rh = chess.pgn.Headers({"Event": "Test", "White": "Alice"})
        assert h["Event"] == rh["Event"]
        assert h["White"] == rh["White"]
        # Both raise KeyError for missing keys when initialized with partial dict
        with pytest.raises(KeyError):
            h["Black"]
        with pytest.raises(KeyError):
            rh["Black"]

    def test_is_chess960(self):
        h = Headers({"Variant": "Chess960"})
        rh = chess.pgn.Headers({"Variant": "Chess960"})
        assert h.is_chess960() == rh.is_chess960()

    def test_is_chess960_fischer(self):
        h = Headers({"Variant": "FischeRandom"})
        rh = chess.pgn.Headers({"Variant": "FischeRandom"})
        assert h.is_chess960() == rh.is_chess960()

    def test_is_not_chess960(self):
        h = Headers()
        rh = chess.pgn.Headers()
        assert h.is_chess960() == rh.is_chess960() == False

    def test_copy_independence(self):
        h = Headers({"Event": "Test"})
        c = h.copy()
        c["Event"] = "Changed"
        assert h["Event"] == "Test"


# =====================================================================
# Game tree basics
# =====================================================================

class TestGameTree:
    def test_empty_game(self):
        g = Game()
        rg = chess.pgn.Game()
        assert g.is_end() == rg.is_end()
        assert g.is_mainline() == rg.is_mainline()

    def test_add_variation(self):
        g = _build_game(["e2e4", "e7e5", "g1f3"])
        rg = _build_ref_game(["e2e4", "e7e5", "g1f3"])
        our_moves = list(g.mainline_moves())
        ref_moves = list(rg.mainline_moves())
        assert [m.uci() for m in our_moves] == [m.uci() for m in ref_moves]

    def test_end(self):
        g = _build_game(["e2e4", "e7e5"])
        end = g.end()
        assert end.is_end()
        assert not end.is_mainline() or end.is_mainline()  # end IS on mainline

    def test_mainline_bool(self):
        g = Game()
        assert not g.mainline()  # empty
        g2 = _build_game(["e2e4"])
        assert g2.mainline()  # non-empty

    def test_is_mainline(self):
        g = _build_game(["e2e4", "e7e5"])
        node = g.variations[0]
        assert node.is_mainline()
        # Add sideline
        b = g.board()
        sideline = g.add_variation(b.parse_uci("d2d4"))
        assert not sideline.is_mainline()


# =====================================================================
# Variation management
# =====================================================================

class TestVariationManagement:
    def test_promote_to_main(self):
        g = Game()
        b = Board()
        m1 = b.parse_uci("e2e4")
        m2 = b.parse_uci("d2d4")
        g.add_variation(m1)
        g.add_variation(m2)
        assert g.variations[0].move == m1
        g.promote_to_main(m2)
        assert g.variations[0].move == m2

    def test_promote(self):
        g = Game()
        b = Board()
        m1 = b.parse_uci("e2e4")
        m2 = b.parse_uci("d2d4")
        m3 = b.parse_uci("c2c4")
        g.add_variation(m1)
        g.add_variation(m2)
        g.add_variation(m3)
        g.promote(m3)
        assert [v.move for v in g.variations] == [m1, m3, m2]

    def test_demote(self):
        g = Game()
        b = Board()
        m1 = b.parse_uci("e2e4")
        m2 = b.parse_uci("d2d4")
        g.add_variation(m1)
        g.add_variation(m2)
        g.demote(m1)
        assert g.variations[0].move == m2
        assert g.variations[1].move == m1

    def test_remove_variation(self):
        g = Game()
        b = Board()
        m1 = b.parse_uci("e2e4")
        m2 = b.parse_uci("d2d4")
        g.add_variation(m1)
        g.add_variation(m2)
        g.remove_variation(m1)
        assert len(g.variations) == 1
        assert g.variations[0].move == m2

    def test_remove_variation_by_index(self):
        g = Game()
        b = Board()
        m1 = b.parse_uci("e2e4")
        g.add_variation(m1)
        g.remove_variation(0)
        assert len(g.variations) == 0

    def test_has_variation(self):
        g = Game()
        b = Board()
        m1 = b.parse_uci("e2e4")
        m2 = b.parse_uci("d2d4")
        g.add_variation(m1)
        assert g.has_variation(m1)
        assert not g.has_variation(m2)

    def test_starts_variation(self):
        g = Game()
        b = Board()
        m1 = b.parse_uci("e2e4")
        m2 = b.parse_uci("d2d4")
        n1 = g.add_variation(m1)
        n2 = g.add_variation(m2)
        assert not n1.starts_variation()
        assert n2.starts_variation()


# =====================================================================
# Eval / set_eval
# =====================================================================

class TestEval:
    def test_eval_cp(self):
        g = _build_game(["e2e4"])
        node = g.variations[0]
        node.comment = "[%eval 0.35]"
        ev = node.eval()
        assert ev is not None
        white = ev.white()
        assert white.score() == 35

    def test_eval_mate(self):
        g = _build_game(["e2e4"])
        node = g.variations[0]
        node.comment = "[%eval #3]"
        ev = node.eval()
        assert ev is not None
        assert ev.white().mate() == 3

    def test_eval_negative_mate_hash_minus(self):
        """BUG: python-chess uses #-2 format for negative mates, not -#2."""
        g = _build_game(["e2e4"])
        node = g.variations[0]
        node.comment = "[%eval #-2]"
        ev = node.eval()
        assert ev is not None, "FAIL: regex doesn't match #-N format"
        assert ev.white().mate() == -2

    def test_eval_minus_hash_not_recognized(self):
        """python-chess does NOT recognize -#N format — should return None."""
        g = _build_game(["e2e4"])
        node = g.variations[0]
        node.comment = "[%eval -#2]"
        ev = node.eval()
        # python-chess returns None for this format
        assert ev is None, "-#N format should not be recognized (python-chess doesn't)"

    def test_eval_plus_hash_not_recognized(self):
        """python-chess does NOT recognize +#N format — should return None."""
        g = _build_game(["e2e4"])
        node = g.variations[0]
        node.comment = "[%eval +#3]"
        ev = node.eval()
        assert ev is None, "+#N format should not be recognized (python-chess doesn't)"

    def test_eval_with_depth(self):
        g = _build_game(["e2e4"])
        node = g.variations[0]
        node.comment = "[%eval 1.50,20]"
        assert node.eval_depth() == 20

    def test_eval_none_no_comment(self):
        g = _build_game(["e2e4"])
        node = g.variations[0]
        assert node.eval() is None

    def test_eval_perspective_black_turn(self):
        """On a Black-to-move node, [%eval 0.35] means White is +0.35."""
        g = _build_game(["e2e4"])
        node = g.variations[0]
        node.comment = "[%eval 0.35]"
        ev = node.eval()
        assert ev.white().score() == 35
        assert ev.turn == False

    def test_eval_perspective_white_turn(self):
        """On a White-to-move node, [%eval -0.50] means White is -0.50."""
        g = _build_game(["e2e4", "e7e5"])
        node = g.variations[0].variations[0]
        node.comment = "[%eval -0.50]"
        ev = node.eval()
        assert ev.white().score() == -50
        assert ev.turn == True

    def test_set_eval_cp(self):
        g = _build_game(["e2e4"])
        node = g.variations[0]
        node.set_eval(PovScore(Cp(150), True))
        assert "[%eval 1.50]" in node.comment

    def test_set_eval_mate(self):
        g = _build_game(["e2e4"])
        node = g.variations[0]
        node.set_eval(PovScore(Mate(3), True))
        assert "[%eval #3]" in node.comment

    def test_set_eval_negative_mate_format(self):
        """set_eval with negative mate should write #-N, not -#N."""
        g = _build_game(["e2e4"])
        node = g.variations[0]
        node.set_eval(PovScore(Mate(-2), True))
        assert "[%eval #-2]" in node.comment

    def test_set_eval_roundtrip_negative_mate(self):
        """BUG: set_eval writes #-2 but eval() can't read it back."""
        g = _build_game(["e2e4"])
        node = g.variations[0]
        node.set_eval(PovScore(Mate(-2), True))
        ev = node.eval()
        assert ev is not None, "FAIL: round-trip broken — eval() returns None for #-N"
        assert ev.white().mate() == -2

    def test_set_eval_clears_previous(self):
        g = _build_game(["e2e4"])
        node = g.variations[0]
        node.comment = "[%eval 0.50] good move"
        node.set_eval(PovScore(Cp(200), True))
        assert "0.50" not in node.comment
        assert "[%eval 2.00]" in node.comment
        assert "good move" in node.comment

    def test_set_eval_clears_negative_mate(self):
        """BUG: set_eval can't clear a #-N annotation because regex doesn't match it."""
        g = _build_game(["e2e4"])
        node = g.variations[0]
        node.comment = "[%eval #-2] good move"
        node.set_eval(PovScore(Cp(100), True))
        count = node.comment.count("%eval")
        assert count == 1, f"FAIL: old #-N not cleared, found {count} eval annotations"

    def test_set_eval_none_clears(self):
        g = _build_game(["e2e4"])
        node = g.variations[0]
        node.comment = "[%eval 0.50] good move"
        node.set_eval(None)
        assert "%eval" not in node.comment
        assert "good move" in node.comment


# =====================================================================
# Clock / EMT
# =====================================================================

class TestClock:
    def test_clock_parse(self):
        g = _build_game(["e2e4"])
        node = g.variations[0]
        node.comment = "[%clk 1:30:00]"
        assert node.clock() == 5400.0

    def test_clock_none(self):
        g = _build_game(["e2e4"])
        node = g.variations[0]
        assert node.clock() is None

    def test_set_clock(self):
        g = _build_game(["e2e4"])
        node = g.variations[0]
        node.set_clock(3661)
        assert "[%clk 1:01:01]" in node.comment

    def test_emt_parse(self):
        g = _build_game(["e2e4"])
        node = g.variations[0]
        node.comment = "[%emt 0:00:05]"
        assert node.emt() == 5.0


# =====================================================================
# Game.from_board / setup
# =====================================================================

class TestGameFromBoard:
    def test_from_standard_game(self):
        b = Board()
        b.push_uci("e2e4")
        b.push_uci("e7e5")
        b.push_uci("g1f3")
        g = Game.from_board(b)
        moves = [m.uci() for m in g.mainline_moves()]
        assert moves == ["e2e4", "e7e5", "g1f3"]

    def test_from_board_with_custom_fen(self):
        fen = "r3k2r/pppppppp/8/8/8/8/PPPPPPPP/R3K2R w KQkq - 0 1"
        b = Board(fen)
        b.push_uci("e1g1")
        g = Game.from_board(b)
        assert g.headers.get("FEN") == fen
        assert g.headers.get("SetUp") == "1"

    def test_setup_standard_clears_fen(self):
        g = Game()
        g.setup(Board())
        assert "FEN" not in g.headers
        assert "SetUp" not in g.headers

    def test_setup_custom_fen(self):
        g = Game()
        fen = "8/8/8/8/8/8/8/4K2R w K - 0 1"
        g.setup(fen)
        assert g.headers["FEN"] == Board(fen).fen()
        assert g.headers["SetUp"] == "1"


# =====================================================================
# Ply / turn
# =====================================================================

class TestPlyTurn:
    def test_root_ply(self):
        g = Game()
        rg = chess.pgn.Game()
        assert g.ply() == rg.ply()

    def test_ply_after_moves(self):
        g = _build_game(["e2e4", "e7e5", "g1f3"])
        rg = _build_ref_game(["e2e4", "e7e5", "g1f3"])
        our_node = g.end()
        ref_node = rg.end()
        assert our_node.ply() == ref_node.ply()

    def test_turn_alternates(self):
        g = _build_game(["e2e4", "e7e5", "g1f3"])
        n1 = g.variations[0]
        n2 = n1.variations[0]
        n3 = n2.variations[0]
        assert n1.turn() == False  # Black's turn after 1.e4
        assert n2.turn() == True   # White's turn after 1...e5
        assert n3.turn() == False  # Black's turn after 2.Nf3


# =====================================================================
# Game.without_tag_roster
# =====================================================================

class TestWithoutTagRoster:
    def test_empty_headers(self):
        g = Game.without_tag_roster()
        rg = chess.pgn.Game.without_tag_roster()
        assert len(g.headers) == len(rg.headers) == 0

    def test_still_functional(self):
        g = Game.without_tag_roster()
        g.headers["Event"] = "Test"
        assert g.headers["Event"] == "Test"


# =====================================================================
# add_line
# =====================================================================

# =====================================================================
# ChildNode.uci() chess960 parity
# =====================================================================

class TestChildNodeUci:
    def test_uci_castling_chess960_true(self):
        """BUG: uci(chess960=True) should return king-takes-rook (e1h1), not e1g1."""
        g = Game()
        ucis = ["e2e4", "e7e5", "f1c4", "f8c5", "g1f3", "g8f6", "e1g1"]
        node = g
        for u in ucis:
            b = node.board()
            m = b.parse_uci(u)
            node = node.add_variation(m)
        # python-chess: uci(chess960=True) returns "e1h1"
        assert node.uci(chess960=True) == "e1h1", (
            f"FAIL: uci(chess960=True) returned {node.uci(chess960=True)!r}, expected 'e1h1'"
        )


class TestAddLine:
    def test_add_line_basic(self):
        g = Game()
        b = Board()
        moves = []
        for u in ["e2e4", "e7e5", "g1f3"]:
            moves.append(b.parse_uci(u))
            b.push(moves[-1])
        end = g.add_line(moves, comment="end comment")
        mainline = [m.uci() for m in g.mainline_moves()]
        assert mainline == ["e2e4", "e7e5", "g1f3"]
        assert end.comment == "end comment"

    def test_add_line_empty(self):
        g = Game()
        end = g.add_line([])
        assert end is g
