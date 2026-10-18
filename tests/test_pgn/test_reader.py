"""Differential tests for PGN-003/004: reader + visitors."""

from __future__ import annotations

import io

import chess
import chess.pgn as ref
import pytest

from dcs_chess.pgn import (
    read_game,
    read_headers,
    skip_game,
    BaseVisitor,
    GameBuilder,
    HeadersBuilder,
    SkipVisitor,
)


def _moves_uci(game) -> list[str]:
    return [m.uci() for m in game.mainline_moves()]


def _read_both(pgn_str: str):
    """Read the same PGN with both libraries."""
    ours = read_game(io.StringIO(pgn_str))
    theirs = ref.read_game(io.StringIO(pgn_str))
    return ours, theirs


class TestReadGameBasic:
    def test_simple_game(self):
        pgn = '[Event "Test"]\n[Result "1-0"]\n\n1. e4 e5 2. Nf3 Nc6 1-0\n'
        ours, theirs = _read_both(pgn)
        assert _moves_uci(ours) == _moves_uci(theirs)
        assert ours.headers["Event"] == theirs.headers["Event"]
        assert ours.headers["Result"] == theirs.headers["Result"]

    def test_empty_input(self):
        assert read_game(io.StringIO("")) is None
        assert ref.read_game(io.StringIO("")) is None

    def test_whitespace_only(self):
        assert read_game(io.StringIO("   \n  ")) is None
        assert ref.read_game(io.StringIO("   \n  ")) is None

    def test_no_moves(self):
        pgn = '[Event "Empty"]\n[Result "*"]\n\n*\n'
        ours, theirs = _read_both(pgn)
        assert _moves_uci(ours) == _moves_uci(theirs) == []
        assert ours.headers["Result"] == theirs.headers["Result"]

    def test_headers_preserved(self):
        pgn = '[Event "Match"]\n[Site "London"]\n[White "A"]\n[Black "B"]\n[Result "1/2-1/2"]\n\n1. d4 d5 1/2-1/2\n'
        ours, theirs = _read_both(pgn)
        for key in ("Event", "Site", "White", "Black", "Result"):
            assert ours.headers[key] == theirs.headers[key]


class TestReadGameComments:
    def test_inline_comment(self):
        pgn = '[Result "*"]\n\n1. e4 {Best move} e5 *\n'
        ours, theirs = _read_both(pgn)
        assert ours.next().comment == theirs.next().comment

    def test_root_comment(self):
        pgn = '[Result "*"]\n\n{Root comment} 1. e4 *\n'
        ours, theirs = _read_both(pgn)
        assert ours.comment == theirs.comment

    def test_nag(self):
        pgn = '[Result "*"]\n\n1. e4 $1 e5 $2 *\n'
        ours, theirs = _read_both(pgn)
        assert ours.next().nags == theirs.next().nags
        assert ours.next().next().nags == theirs.next().next().nags


class TestReadGameVariations:
    def test_single_variation(self):
        pgn = '[Result "*"]\n\n1. e4 (1. d4) 1... e5 *\n'
        ours, theirs = _read_both(pgn)
        assert len(ours.variations) == len(theirs.variations)
        assert _moves_uci(ours) == _moves_uci(theirs)
        if len(ours.variations) > 1:
            assert ours.variations[1].move.uci() == theirs.variations[1].move.uci()

    def test_variation_with_comment(self):
        pgn = '[Result "*"]\n\n1. e4 e5 2. Nf3 (2. Bc4 {Italian}) Nc6 *\n'
        ours, theirs = _read_both(pgn)
        assert _moves_uci(ours) == _moves_uci(theirs)
        n_e5 = ours.next().next()
        rn_e5 = theirs.next().next()
        assert len(n_e5.variations) == len(rn_e5.variations)
        if len(n_e5.variations) > 1:
            assert n_e5.variations[1].comment == rn_e5.variations[1].comment

    def test_nested_variations(self):
        pgn = '[Result "*"]\n\n1. e4 (1. d4 d5 (1... Nf6 2. c4) 2. c4) 1... e5 *\n'
        ours, theirs = _read_both(pgn)
        assert _moves_uci(ours) == _moves_uci(theirs)
        assert len(ours.variations) == len(theirs.variations)

    def test_multiple_sidelines(self):
        pgn = '[Result "*"]\n\n1. e4 (1. d4) (1. c4) (1. Nf3) 1... e5 *\n'
        ours, theirs = _read_both(pgn)
        assert len(ours.variations) == len(theirs.variations)
        our_alts = [v.move.uci() for v in ours.variations]
        ref_alts = [v.move.uci() for v in theirs.variations]
        assert our_alts == ref_alts


class TestReadGameErrors:
    def test_illegal_move(self):
        pgn = '[Result "*"]\n\n1. e4 e4 *\n'
        ours, theirs = _read_both(pgn)
        assert len(ours.errors) >= 1
        assert len(theirs.errors) >= 1
        assert _moves_uci(ours) == _moves_uci(theirs)


class TestMultipleGames:
    def test_two_games(self):
        pgn = '[Event "A"]\n[Result "1-0"]\n\n1. e4 e5 1-0\n\n[Event "B"]\n[Result "0-1"]\n\n1. d4 d5 0-1\n'
        our_h = io.StringIO(pgn)
        ref_h = io.StringIO(pgn)
        g1 = read_game(our_h)
        rg1 = ref.read_game(ref_h)
        assert g1.headers["Event"] == rg1.headers["Event"] == "A"
        assert _moves_uci(g1) == _moves_uci(rg1)

        g2 = read_game(our_h)
        rg2 = ref.read_game(ref_h)
        assert g2.headers["Event"] == rg2.headers["Event"] == "B"
        assert _moves_uci(g2) == _moves_uci(rg2)

        assert read_game(our_h) is None
        assert ref.read_game(ref_h) is None


class TestReadHeaders:
    def test_basic(self):
        pgn = '[Event "Test"]\n[White "Alice"]\n[Result "*"]\n\n1. e4 *\n'
        ours = read_headers(io.StringIO(pgn))
        theirs = ref.read_headers(io.StringIO(pgn))
        assert ours["Event"] == theirs["Event"]
        assert ours["White"] == theirs["White"]

    def test_eof(self):
        assert read_headers(io.StringIO("")) is None
        assert ref.read_headers(io.StringIO("")) is None


class TestSkipGame:
    def test_skip_returns_true(self):
        pgn = '[Event "A"]\n[Result "*"]\n\n1. e4 *\n'
        assert skip_game(io.StringIO(pgn)) == True
        assert ref.skip_game(io.StringIO(pgn)) == True

    def test_skip_eof(self):
        assert skip_game(io.StringIO("")) == False
        assert ref.skip_game(io.StringIO("")) == False

    def test_skip_then_read(self):
        pgn = '[Event "A"]\n[Result "*"]\n\n1. e4 *\n\n[Event "B"]\n[Result "*"]\n\n1. d4 *\n'
        our_h = io.StringIO(pgn)
        ref_h = io.StringIO(pgn)
        skip_game(our_h)
        ref.skip_game(ref_h)
        g = read_game(our_h)
        rg = ref.read_game(ref_h)
        assert g.headers["Event"] == rg.headers["Event"] == "B"


class TestVisitorClasses:
    def test_game_builder(self):
        gb = GameBuilder()
        rgb = ref.GameBuilder()
        assert type(gb).__name__ == type(rgb).__name__

    def test_headers_builder(self):
        hb = HeadersBuilder()
        rhb = ref.HeadersBuilder()
        assert type(hb).__name__ == type(rhb).__name__

    def test_skip_visitor(self):
        sv = SkipVisitor()
        rsv = ref.SkipVisitor()
        assert sv.begin_game().name == rsv.begin_game().name == "SKIP"
        assert sv.result() == rsv.result() == True


class TestResultParsing:
    def test_white_wins(self):
        pgn = '[Result "1-0"]\n\n1. e4 e5 1-0\n'
        ours, theirs = _read_both(pgn)
        assert ours.headers["Result"] == theirs.headers["Result"] == "1-0"

    def test_black_wins(self):
        pgn = '[Result "0-1"]\n\n1. d4 d5 0-1\n'
        ours, theirs = _read_both(pgn)
        assert ours.headers["Result"] == theirs.headers["Result"] == "0-1"

    def test_draw(self):
        pgn = '[Result "1/2-1/2"]\n\n1. e4 e5 1/2-1/2\n'
        ours, theirs = _read_both(pgn)
        assert ours.headers["Result"] == theirs.headers["Result"] == "1/2-1/2"

    def test_ongoing(self):
        pgn = '[Result "*"]\n\n1. e4 *\n'
        ours, theirs = _read_both(pgn)
        assert ours.headers["Result"] == theirs.headers["Result"] == "*"
