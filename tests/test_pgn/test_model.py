"""Differential tests for PGN-001: GameNode, ChildNode, Game, Mainline (FR-P1)."""

from __future__ import annotations

import chess
import chess.pgn as ref
import pytest

from dcs_chess.pgn.model import (
    GameNode,
    ChildNode,
    Game,
    Headers,
    Mainline,
    SKIP,
    SkipType,
)
from dcs_chess.core.board import Board
from dcs_chess.core.move import Move


class TestHeaders:
    def test_default_seven_tag_roster(self):
        h = Headers()
        rh = ref.Headers()
        assert dict(h) == dict(rh)

    def test_custom_headers(self):
        h = Headers({"Event": "Test", "White": "Alice"})
        rh = ref.Headers({"Event": "Test", "White": "Alice"})
        assert h["Event"] == rh["Event"]
        assert h["White"] == rh["White"]

    def test_is_chess960(self):
        h = Headers({"Variant": "Chess960"})
        rh = ref.Headers({"Variant": "Chess960"})
        assert h.is_chess960() == rh.is_chess960()

    def test_is_chess960_false(self):
        h = Headers()
        rh = ref.Headers()
        assert h.is_chess960() == rh.is_chess960() == False

    def test_is_wild(self):
        h = Headers({"Variant": "wild/1"})
        rh = ref.Headers({"Variant": "wild/1"})
        assert h.is_wild() == rh.is_wild() == True

    def test_is_wild_false_for_atomic(self):
        h = Headers({"Variant": "Atomic"})
        rh = ref.Headers({"Variant": "Atomic"})
        assert h.is_wild() == rh.is_wild() == False

    def test_is_wild_false_for_chess960(self):
        h = Headers({"Variant": "Chess960"})
        rh = ref.Headers({"Variant": "Chess960"})
        assert h.is_wild() == rh.is_wild() == False

    def test_copy(self):
        h = Headers({"Event": "Test"})
        h2 = h.copy()
        h2["Event"] = "Changed"
        assert h["Event"] == "Test"
        assert h2["Event"] == "Changed"


class TestGame:
    def test_default_construction(self):
        g = Game()
        rg = ref.Game()
        assert dict(g.headers) == dict(rg.headers)

    def test_repr_format(self):
        g = Game()
        rg = ref.Game()
        # Both should have the same structure
        assert "?" in repr(g)
        assert "vs." in repr(g)

    def test_errors_default_empty(self):
        g = Game()
        rg = ref.Game()
        assert g.errors == rg.errors == []

    def test_without_tag_roster(self):
        g = Game.without_tag_roster()
        rg = ref.Game.without_tag_roster()
        assert dict(g.headers) == dict(rg.headers) == {}


class TestGameTree:
    def _make_tree(self):
        """Build identical trees in both dcs and ref."""
        g = Game()
        e4 = chess.Move.from_uci("e2e4")
        e5 = chess.Move.from_uci("e7e5")
        nf3 = chess.Move.from_uci("g1f3")
        n1 = g.add_variation(e4)
        n2 = n1.add_variation(e5)
        n3 = n2.add_variation(nf3)

        rg = ref.Game()
        rn1 = rg.add_variation(e4)
        rn2 = rn1.add_variation(e5)
        rn3 = rn2.add_variation(nf3)

        return (g, n1, n2, n3), (rg, rn1, rn2, rn3)

    def test_mainline_moves(self):
        (g, *_), (rg, *_) = self._make_tree()
        ours = list(g.mainline_moves())
        theirs = list(rg.mainline_moves())
        assert ours == theirs

    def test_mainline_nodes_count(self):
        (g, *_), (rg, *_) = self._make_tree()
        assert len(list(g.mainline())) == len(list(rg.mainline()))

    def test_ply(self):
        (g, n1, n2, n3), (rg, rn1, rn2, rn3) = self._make_tree()
        assert g.ply() == rg.ply()
        assert n1.ply() == rn1.ply()
        assert n2.ply() == rn2.ply()
        assert n3.ply() == rn3.ply()

    def test_turn(self):
        (g, n1, n2, n3), (rg, rn1, rn2, rn3) = self._make_tree()
        assert g.turn() == rg.turn()
        assert n1.turn() == rn1.turn()
        assert n2.turn() == rn2.turn()
        assert n3.turn() == rn3.turn()

    def test_is_end(self):
        (g, n1, n2, n3), (rg, rn1, rn2, rn3) = self._make_tree()
        assert g.is_end() == rg.is_end() == False
        assert n3.is_end() == rn3.is_end() == True

    def test_end(self):
        (g, n1, n2, n3), (rg, rn1, rn2, rn3) = self._make_tree()
        assert g.end() is n3
        assert rg.end() is rn3

    def test_is_mainline(self):
        (g, n1, n2, n3), (rg, rn1, rn2, rn3) = self._make_tree()
        assert n1.is_mainline() == rn1.is_mainline() == True
        assert n3.is_mainline() == rn3.is_mainline() == True

    def test_is_main_variation(self):
        (g, n1, n2, n3), (rg, rn1, rn2, rn3) = self._make_tree()
        assert n1.is_main_variation() == rn1.is_main_variation() == True

    def test_next(self):
        (g, n1, n2, n3), (rg, rn1, rn2, rn3) = self._make_tree()
        assert g.next() is n1
        assert n3.next() is None
        assert rg.next() is rn1
        assert rn3.next() is None


class TestVariations:
    def test_add_variation(self):
        g = Game()
        rg = ref.Game()
        e4 = chess.Move.from_uci("e2e4")
        d4 = chess.Move.from_uci("d2d4")
        g.add_variation(e4)
        g.add_variation(d4)
        rg.add_variation(e4)
        rg.add_variation(d4)
        assert len(g.variations) == len(rg.variations) == 2

    def test_has_variation(self):
        g = Game()
        rg = ref.Game()
        e4 = chess.Move.from_uci("e2e4")
        c4 = chess.Move.from_uci("c2c4")
        g.add_variation(e4)
        rg.add_variation(e4)
        assert g.has_variation(e4) == rg.has_variation(e4) == True
        assert g.has_variation(c4) == rg.has_variation(c4) == False

    def test_starts_variation(self):
        g = Game()
        rg = ref.Game()
        e4 = chess.Move.from_uci("e2e4")
        d4 = chess.Move.from_uci("d2d4")
        n1 = g.add_variation(e4)
        n2 = g.add_variation(d4)
        rn1 = rg.add_variation(e4)
        rn2 = rg.add_variation(d4)
        assert n1.starts_variation() == rn1.starts_variation() == False
        assert n2.starts_variation() == rn2.starts_variation() == True

    def test_remove_variation(self):
        g = Game()
        rg = ref.Game()
        e4 = chess.Move.from_uci("e2e4")
        d4 = chess.Move.from_uci("d2d4")
        g.add_variation(e4)
        g.add_variation(d4)
        rg.add_variation(e4)
        rg.add_variation(d4)
        g.remove_variation(e4)
        rg.remove_variation(e4)
        assert len(g.variations) == len(rg.variations) == 1
        assert g.variations[0].move == rg.variations[0].move == d4

    def test_promote_to_main(self):
        g = Game()
        rg = ref.Game()
        e4 = chess.Move.from_uci("e2e4")
        d4 = chess.Move.from_uci("d2d4")
        g.add_variation(e4)
        n2 = g.add_variation(d4)
        rg.add_variation(e4)
        rn2 = rg.add_variation(d4)
        g.promote_to_main(d4)
        rg.promote_to_main(d4)
        assert g.variations[0].move == rg.variations[0].move == d4
        assert g.variations[1].move == rg.variations[1].move == e4

    def test_promote(self):
        g = Game()
        rg = ref.Game()
        e4 = chess.Move.from_uci("e2e4")
        d4 = chess.Move.from_uci("d2d4")
        c4 = chess.Move.from_uci("c2c4")
        g.add_variation(e4)
        g.add_variation(d4)
        g.add_variation(c4)
        rg.add_variation(e4)
        rg.add_variation(d4)
        rg.add_variation(c4)
        g.promote(c4)
        rg.promote(c4)
        ours = [v.move for v in g.variations]
        theirs = [v.move for v in rg.variations]
        assert ours == theirs

    def test_demote(self):
        g = Game()
        rg = ref.Game()
        e4 = chess.Move.from_uci("e2e4")
        d4 = chess.Move.from_uci("d2d4")
        g.add_variation(e4)
        g.add_variation(d4)
        rg.add_variation(e4)
        rg.add_variation(d4)
        g.demote(e4)
        rg.demote(e4)
        ours = [v.move for v in g.variations]
        theirs = [v.move for v in rg.variations]
        assert ours == theirs

    def test_add_main_variation(self):
        g = Game()
        rg = ref.Game()
        e4 = chess.Move.from_uci("e2e4")
        d4 = chess.Move.from_uci("d2d4")
        g.add_variation(e4)
        g.add_main_variation(d4)
        rg.add_variation(e4)
        rg.add_main_variation(d4)
        assert g.variations[0].move == rg.variations[0].move == d4
        assert g.variations[1].move == rg.variations[1].move == e4


class TestAddLine:
    def test_add_line(self):
        g = Game()
        rg = ref.Game()
        moves = [
            chess.Move.from_uci("e2e4"),
            chess.Move.from_uci("e7e5"),
            chess.Move.from_uci("g1f3"),
        ]
        g.add_line(moves, comment="Italian Game")
        rg.add_line(moves, comment="Italian Game")
        ours = list(g.mainline_moves())
        theirs = list(rg.mainline_moves())
        assert ours == theirs
        assert g.end().comment == rg.end().comment == "Italian Game"


class TestMainline:
    def test_bool_nonempty(self):
        g = Game()
        rg = ref.Game()
        g.add_variation(chess.Move.from_uci("e2e4"))
        rg.add_variation(chess.Move.from_uci("e2e4"))
        assert bool(g.mainline()) == bool(rg.mainline()) == True

    def test_bool_empty(self):
        g = Game()
        rg = ref.Game()
        assert bool(g.mainline()) == bool(rg.mainline()) == False

    def test_mainline_moves_match(self):
        g = Game()
        rg = ref.Game()
        moves = [
            chess.Move.from_uci("e2e4"),
            chess.Move.from_uci("e7e5"),
            chess.Move.from_uci("g1f3"),
            chess.Move.from_uci("b8c6"),
        ]
        node = g
        rnode = rg
        for m in moves:
            node = node.add_variation(m)
            rnode = rnode.add_variation(m)
        assert list(g.mainline_moves()) == list(rg.mainline_moves())


class TestChildNode:
    def test_san(self):
        g = Game()
        rg = ref.Game()
        e4 = chess.Move.from_uci("e2e4")
        n1 = g.add_variation(e4)
        rn1 = rg.add_variation(e4)
        assert n1.san() == rn1.san() == "e4"

    def test_uci(self):
        g = Game()
        rg = ref.Game()
        e4 = chess.Move.from_uci("e2e4")
        n1 = g.add_variation(e4)
        rn1 = rg.add_variation(e4)
        assert n1.uci() == rn1.uci() == "e2e4"

    def test_nags(self):
        g = Game()
        rg = ref.Game()
        e4 = chess.Move.from_uci("e2e4")
        n1 = g.add_variation(e4, nags=[1, 3])
        rn1 = rg.add_variation(e4, nags=[1, 3])
        assert n1.nags == rn1.nags

    def test_comment(self):
        g = Game()
        rg = ref.Game()
        e4 = chess.Move.from_uci("e2e4")
        n1 = g.add_variation(e4, comment="best move")
        rn1 = rg.add_variation(e4, comment="best move")
        assert n1.comment == rn1.comment == "best move"


class TestCommentAnnotations:
    def test_clock_parse(self):
        g = Game()
        rg = ref.Game()
        e4 = chess.Move.from_uci("e2e4")
        n1 = g.add_variation(e4, comment="[%clk 1:30:00]")
        rn1 = rg.add_variation(e4, comment="[%clk 1:30:00]")
        assert n1.clock() == rn1.clock()

    def test_clock_none(self):
        g = Game()
        rg = ref.Game()
        e4 = chess.Move.from_uci("e2e4")
        n1 = g.add_variation(e4, comment="no clock")
        rn1 = rg.add_variation(e4, comment="no clock")
        assert n1.clock() == rn1.clock() == None

    def test_set_clock(self):
        g = Game()
        rg = ref.Game()
        e4 = chess.Move.from_uci("e2e4")
        n1 = g.add_variation(e4)
        rn1 = rg.add_variation(e4)
        n1.set_clock(3600.0)
        rn1.set_clock(3600.0)
        assert n1.clock() == rn1.clock() == 3600.0

    def test_emt_parse(self):
        g = Game()
        rg = ref.Game()
        e4 = chess.Move.from_uci("e2e4")
        n1 = g.add_variation(e4, comment="[%emt 0:00:30]")
        rn1 = rg.add_variation(e4, comment="[%emt 0:00:30]")
        assert n1.emt() == rn1.emt()

    def test_emt_none(self):
        g = Game()
        n1 = g.add_variation(chess.Move.from_uci("e2e4"))
        assert n1.emt() is None


class TestGameSetup:
    def test_setup_standard(self):
        g = Game()
        rg = ref.Game()
        assert "FEN" not in g.headers
        assert "FEN" not in rg.headers

    def test_setup_custom_fen(self):
        fen = "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq - 0 1"
        g = Game()
        rg = ref.Game()
        g.setup(fen)
        rg.setup(fen)
        assert g.headers["FEN"] == rg.headers["FEN"]
        assert g.headers["SetUp"] == rg.headers["SetUp"] == "1"

    def test_from_board_standard(self):
        b = chess.Board()
        b.push_san("e4")
        b.push_san("e5")
        g = Game.from_board(b)
        rg = ref.Game.from_board(b)
        assert list(g.mainline_moves()) == list(rg.mainline_moves())


class TestBoard:
    def test_root_board(self):
        g = Game()
        rg = ref.Game()
        assert g.board().fen() == rg.board().fen()

    def test_node_board(self):
        g = Game()
        rg = ref.Game()
        e4 = chess.Move.from_uci("e2e4")
        e5 = chess.Move.from_uci("e7e5")
        n1 = g.add_variation(e4)
        n2 = n1.add_variation(e5)
        rn1 = rg.add_variation(e4)
        rn2 = rn1.add_variation(e5)
        assert n1.board().fen() == rn1.board().fen()
        assert n2.board().fen() == rn2.board().fen()


class TestVariationLookup:
    def test_variation_by_move(self):
        g = Game()
        rg = ref.Game()
        e4 = chess.Move.from_uci("e2e4")
        d4 = chess.Move.from_uci("d2d4")
        n1 = g.add_variation(e4)
        n2 = g.add_variation(d4)
        rn1 = rg.add_variation(e4)
        rn2 = rg.add_variation(d4)
        assert g.variation(e4) is n1
        assert g.variation(d4) is n2
        assert rg.variation(e4) is rn1
        assert rg.variation(d4) is rn2


class TestGameNavigation:
    def test_game_root(self):
        g = Game()
        rg = ref.Game()
        e4 = chess.Move.from_uci("e2e4")
        n = g.add_variation(e4)
        rn = rg.add_variation(e4)
        assert n.game() is g
        assert rn.game() is rg

    def test_parent(self):
        g = Game()
        rg = ref.Game()
        e4 = chess.Move.from_uci("e2e4")
        n = g.add_variation(e4)
        rn = rg.add_variation(e4)
        assert n.parent is g
        assert rn.parent is rg

    def test_root_is_own_game(self):
        g = Game()
        rg = ref.Game()
        assert g.game() is g
        assert rg.game() is rg


class TestSetEval:
    def test_set_eval_and_read(self):
        from dcs_chess.engine.scores import Cp, PovScore
        from chess.engine import Cp as RefCp, PovScore as RefPovScore
        g = Game()
        rg = ref.Game()
        e4 = chess.Move.from_uci("e2e4")
        n = g.add_variation(e4)
        rn = rg.add_variation(e4)
        score = PovScore(Cp(50), chess.WHITE)
        ref_score = RefPovScore(RefCp(50), chess.WHITE)
        n.set_eval(score)
        rn.set_eval(ref_score)
        our_eval = n.eval()
        ref_eval = rn.eval()
        assert our_eval.relative.score() == ref_eval.relative.score()

    def test_set_eval_with_depth(self):
        from dcs_chess.engine.scores import Cp, PovScore
        from chess.engine import Cp as RefCp, PovScore as RefPovScore
        g = Game()
        rg = ref.Game()
        e4 = chess.Move.from_uci("e2e4")
        n = g.add_variation(e4)
        rn = rg.add_variation(e4)
        score = PovScore(Cp(150), chess.WHITE)
        ref_score = RefPovScore(RefCp(150), chess.WHITE)
        n.set_eval(score, depth=20)
        rn.set_eval(ref_score, depth=20)
        assert "[%eval" in n.comment
        assert "[%eval" in rn.comment


class TestHeadersRepr:
    def test_repr_format(self):
        h = Headers({"Event": "Test", "White": "Alice"})
        rh = ref.Headers({"Event": "Test", "White": "Alice"})
        assert repr(h) == repr(rh)

    def test_repr_default(self):
        h = Headers()
        rh = ref.Headers()
        assert repr(h) == repr(rh)


class TestHeadersVariant:
    def test_variant_default_returns_board_class(self):
        h = Headers()
        rh = ref.Headers()
        assert isinstance(h.variant(), type)
        assert isinstance(rh.variant(), type)

    def test_variant_chess960_returns_board_class(self):
        h = Headers({"Variant": "Chess960"})
        rh = ref.Headers({"Variant": "Chess960"})
        assert isinstance(h.variant(), type)
        assert isinstance(rh.variant(), type)


class TestHeadersBuilder:
    def test_builder_returns_headers_builder(self):
        h = Headers()
        rh = ref.Headers()
        assert type(h.builder()).__name__ == type(rh.builder()).__name__


class TestSkip:
    def test_skip_is_singleton(self):
        assert SKIP is SkipType.SKIP
        assert SKIP is ref.SKIP or SKIP.name == ref.SKIP.name
