"""ADV adversarial differential tests for PGN-003/004: reader + visitors."""

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
from dcs_chess.pgn.model import SKIP, SkipType


def _moves_uci(game) -> list[str]:
    return [m.uci() for m in game.mainline_moves()]


def _read_both(pgn_str: str):
    ours = read_game(io.StringIO(pgn_str))
    theirs = ref.read_game(io.StringIO(pgn_str))
    return ours, theirs


# =====================================================================
# 1. Semicolon comments (line-terminating)
# =====================================================================

class TestSemicolonComments:
    def test_semicolon_does_not_eat_next_line(self):
        pgn = '[Result "*"]\n\n1. e4 ;this is a comment\ne5 *\n'
        ours, theirs = _read_both(pgn)
        assert _moves_uci(ours) == _moves_uci(theirs)

    def test_semicolon_mid_movetext(self):
        pgn = '[Result "*"]\n\n1. e4 e5 ;comment\n2. Nf3 Nc6 *\n'
        ours, theirs = _read_both(pgn)
        assert _moves_uci(ours) == _moves_uci(theirs)

    def test_semicolon_comment_content(self):
        pgn = '[Result "*"]\n\n1. e4 ;my annotation\ne5 *\n'
        ours, theirs = _read_both(pgn)
        our_comments = []
        ref_comments = []
        node = ours
        while node.variations:
            node = node.variations[0]
            if node.comment:
                our_comments.append(node.comment)
        node = theirs
        while node.variations:
            node = node.variations[0]
            if node.comment:
                ref_comments.append(node.comment)
        assert our_comments == ref_comments

    def test_multiple_semicolon_comments(self):
        pgn = '[Result "*"]\n\n1. e4 ;first\ne5 ;second\n2. d4 *\n'
        ours, theirs = _read_both(pgn)
        assert _moves_uci(ours) == _moves_uci(theirs)

    def test_semicolon_only_line(self):
        pgn = '[Result "*"]\n\n;entire line comment\n1. e4 e5 *\n'
        ours, theirs = _read_both(pgn)
        assert _moves_uci(ours) == _moves_uci(theirs)


# =====================================================================
# 2. Brace comments — multi-line
# =====================================================================

class TestBraceComments:
    def test_multiline_comment_preserves_newlines(self):
        pgn = '[Result "*"]\n\n1. e4 {This is\na multi-line\ncomment} e5 *\n'
        ours, theirs = _read_both(pgn)
        assert ours.next().comment == theirs.next().comment

    def test_multiline_comment_moves_still_parse(self):
        pgn = '[Result "*"]\n\n1. e4 {line1\nline2} e5 *\n'
        ours, theirs = _read_both(pgn)
        assert _moves_uci(ours) == _moves_uci(theirs)

    def test_empty_comment(self):
        pgn = '[Result "*"]\n\n1. e4 {} e5 *\n'
        ours, theirs = _read_both(pgn)
        assert _moves_uci(ours) == _moves_uci(theirs)

    def test_comment_with_braces_in_string(self):
        pgn = '[Result "*"]\n\n1. e4 {a comment} e5 {another} *\n'
        ours, theirs = _read_both(pgn)
        our_n1 = ours.next()
        ref_n1 = theirs.next()
        assert our_n1.comment == ref_n1.comment
        our_n2 = our_n1.next()
        ref_n2 = ref_n1.next()
        assert our_n2.comment == ref_n2.comment


# =====================================================================
# 3. Variation nesting
# =====================================================================

class TestVariationNesting:
    def test_deep_nesting_5_levels(self):
        pgn = '[Result "*"]\n\n1. e4 (1. d4 (1. c4 (1. Nf3 (1. g3)))) 1... e5 *\n'
        ours, theirs = _read_both(pgn)
        assert _moves_uci(ours) == _moves_uci(theirs)
        assert len(ours.variations) == len(theirs.variations)

    def test_variation_after_variation(self):
        pgn = '[Result "*"]\n\n1. e4 (1. d4) (1. c4) 1... e5 *\n'
        ours, theirs = _read_both(pgn)
        assert len(ours.variations) == len(theirs.variations)
        our_alts = sorted(v.move.uci() for v in ours.variations)
        ref_alts = sorted(v.move.uci() for v in theirs.variations)
        assert our_alts == ref_alts

    def test_empty_variation(self):
        pgn = '[Result "*"]\n\n1. e4 () e5 *\n'
        ours, theirs = _read_both(pgn)
        assert _moves_uci(ours) == _moves_uci(theirs)
        assert len(ours.variations) == len(theirs.variations)

    def test_variation_with_sub_variation(self):
        pgn = '[Result "*"]\n\n1. e4 e5 2. Nf3 (2. Bc4 Bc5 (2... Nf6)) 2... Nc6 *\n'
        ours, theirs = _read_both(pgn)
        assert _moves_uci(ours) == _moves_uci(theirs)

    def test_variation_comment_inside(self):
        pgn = '[Result "*"]\n\n1. e4 (1. d4 {Queen pawn}) e5 *\n'
        ours, theirs = _read_both(pgn)
        assert len(ours.variations) == len(theirs.variations)
        if len(ours.variations) > 1:
            assert ours.variations[1].comment == theirs.variations[1].comment


# =====================================================================
# 4. Error recovery
# =====================================================================

class TestErrorRecovery:
    def test_illegal_move_stops_mainline(self):
        pgn = '[Result "*"]\n\n1. e4 Ke7 e5 2. Nf3 *\n'
        ours, theirs = _read_both(pgn)
        assert _moves_uci(ours) == _moves_uci(theirs)

    def test_error_count_matches(self):
        pgn = '[Result "*"]\n\n1. e4 e4 *\n'
        ours, theirs = _read_both(pgn)
        assert len(ours.errors) == len(theirs.errors)
        assert _moves_uci(ours) == _moves_uci(theirs)

    def test_error_mid_game(self):
        pgn = '[Result "*"]\n\n1. e4 e5 2. Ke3 d5 *\n'
        ours, theirs = _read_both(pgn)
        assert _moves_uci(ours) == _moves_uci(theirs)
        assert len(ours.errors) == len(theirs.errors)

    def test_multiple_errors(self):
        pgn = '[Result "*"]\n\n1. e4 Qd1 Ke7 e5 *\n'
        ours, theirs = _read_both(pgn)
        assert _moves_uci(ours) == _moves_uci(theirs)


# =====================================================================
# 5. Multi-game streaming
# =====================================================================

class TestMultiGameStreaming:
    def test_three_games(self):
        pgn = (
            '[Event "A"]\n[Result "1-0"]\n\n1. e4 e5 1-0\n\n'
            '[Event "B"]\n[Result "0-1"]\n\n1. d4 d5 0-1\n\n'
            '[Event "C"]\n[Result "*"]\n\n1. c4 *\n'
        )
        oh = io.StringIO(pgn)
        rh = io.StringIO(pgn)
        for expected_event in ("A", "B", "C"):
            og = read_game(oh)
            rg = ref.read_game(rh)
            assert og is not None and rg is not None
            assert og.headers["Event"] == rg.headers["Event"] == expected_event
            assert _moves_uci(og) == _moves_uci(rg)

        assert read_game(oh) is None
        assert ref.read_game(rh) is None

    def test_skip_read_interleave(self):
        pgn = (
            '[Event "A"]\n[Result "*"]\n\n1. e4 *\n\n'
            '[Event "B"]\n[Result "*"]\n\n1. d4 *\n\n'
            '[Event "C"]\n[Result "*"]\n\n1. c4 *\n'
        )
        oh = io.StringIO(pgn)
        rh = io.StringIO(pgn)
        skip_game(oh)
        ref.skip_game(rh)
        og = read_game(oh)
        rg = ref.read_game(rh)
        assert og.headers["Event"] == rg.headers["Event"] == "B"
        skip_game(oh)
        ref.skip_game(rh)
        assert read_game(oh) is None
        assert ref.read_game(rh) is None

    def test_read_skip_read(self):
        pgn = (
            '[Event "A"]\n[Result "*"]\n\n1. e4 *\n\n'
            '[Event "B"]\n[Result "*"]\n\n1. d4 *\n\n'
            '[Event "C"]\n[Result "*"]\n\n1. c4 *\n'
        )
        oh = io.StringIO(pgn)
        rh = io.StringIO(pgn)
        g1 = read_game(oh)
        rg1 = ref.read_game(rh)
        assert g1.headers["Event"] == "A"
        skip_game(oh)
        ref.skip_game(rh)
        g3 = read_game(oh)
        rg3 = ref.read_game(rh)
        assert g3.headers["Event"] == rg3.headers["Event"] == "C"


# =====================================================================
# 6. FEN starting positions
# =====================================================================

class TestFENStarting:
    def test_black_to_move(self):
        pgn = '[FEN "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq - 0 1"]\n[Result "*"]\n\n1... e5 *\n'
        ours, theirs = _read_both(pgn)
        assert _moves_uci(ours) == _moves_uci(theirs)

    def test_custom_position(self):
        pgn = '[FEN "r1bqkbnr/pppppppp/2n5/8/4P3/8/PPPP1PPP/RNBQKBNR w KQkq - 1 2"]\n[Result "*"]\n\n2. d4 *\n'
        ours, theirs = _read_both(pgn)
        assert _moves_uci(ours) == _moves_uci(theirs)

    def test_endgame_fen(self):
        pgn = '[FEN "4k3/8/8/8/8/8/4P3/4K3 w - - 0 1"]\n[Result "*"]\n\n1. e4 *\n'
        ours, theirs = _read_both(pgn)
        assert _moves_uci(ours) == _moves_uci(theirs)


# =====================================================================
# 7. Castling notation (O-O vs 0-0)
# =====================================================================

class TestCastlingNotation:
    def test_uppercase_o_kingside(self):
        pgn = '[Result "*"]\n\n1. e4 e5 2. Nf3 Nc6 3. Bc4 Bc5 4. O-O *\n'
        ours, theirs = _read_both(pgn)
        assert _moves_uci(ours) == _moves_uci(theirs)

    def test_zero_kingside(self):
        pgn = '[Result "*"]\n\n1. e4 e5 2. Nf3 Nc6 3. Bc4 Bc5 4. 0-0 *\n'
        ours, theirs = _read_both(pgn)
        assert _moves_uci(ours) == _moves_uci(theirs)

    def test_uppercase_o_queenside(self):
        pgn = '[Result "*"]\n\n1. d4 d5 2. c4 e6 3. Nc3 Nf6 4. Bg5 Be7 5. e3 O-O 6. Nf3 Nbd7 7. Qc2 c5 8. O-O-O *\n'
        ours, theirs = _read_both(pgn)
        assert _moves_uci(ours) == _moves_uci(theirs)

    def test_zero_queenside(self):
        pgn = '[Result "*"]\n\n1. d4 d5 2. c4 e6 3. Nc3 Nf6 4. Bg5 Be7 5. e3 O-O 6. Nf3 Nbd7 7. Qc2 c5 8. 0-0-0 *\n'
        ours, theirs = _read_both(pgn)
        assert _moves_uci(ours) == _moves_uci(theirs)


# =====================================================================
# 8. Null move (--)
# =====================================================================

class TestNullMove:
    def test_null_move_parsed(self):
        pgn = '[Result "*"]\n\n1. e4 -- 2. d4 *\n'
        ours, theirs = _read_both(pgn)
        assert _moves_uci(ours) == _moves_uci(theirs)


# =====================================================================
# 9. Edge cases
# =====================================================================

class TestEdgeCases:
    def test_no_headers(self):
        pgn = '1. e4 e5 *\n'
        ours, theirs = _read_both(pgn)
        assert _moves_uci(ours) == _moves_uci(theirs)

    def test_only_result(self):
        pgn = '[Result "1-0"]\n\n1-0\n'
        ours, theirs = _read_both(pgn)
        assert _moves_uci(ours) == _moves_uci(theirs) == []
        assert ours.headers["Result"] == theirs.headers["Result"]

    def test_no_final_newline(self):
        pgn = '[Result "*"]\n\n1. e4 e5 *'
        ours, theirs = _read_both(pgn)
        assert _moves_uci(ours) == _moves_uci(theirs)

    def test_extra_whitespace(self):
        pgn = '[Result  "*"]\n\n  1.   e4    e5   *\n'
        ours, theirs = _read_both(pgn)
        assert _moves_uci(ours) == _moves_uci(theirs)

    def test_promotion(self):
        pgn = '[FEN "4k3/P7/8/8/8/8/8/4K3 w - - 0 1"]\n[Result "*"]\n\n1. a8=Q *\n'
        ours, theirs = _read_both(pgn)
        assert _moves_uci(ours) == _moves_uci(theirs)

    def test_long_game(self):
        pgn = '[Result "1/2-1/2"]\n\n1. e4 e5 2. Nf3 Nc6 3. Bb5 a6 4. Ba4 Nf6 5. O-O Be7 6. Re1 b5 7. Bb3 d6 8. c3 O-O 1/2-1/2\n'
        ours, theirs = _read_both(pgn)
        assert _moves_uci(ours) == _moves_uci(theirs)


# =====================================================================
# 10. Visitor protocol
# =====================================================================

class TestVisitorProtocol:
    def test_base_visitor_begin_variation_returns_skip(self):
        class _Concrete(BaseVisitor):
            def result(self):
                return None
        v = _Concrete()
        assert v.begin_variation() is SKIP

    def test_game_builder_game_class(self):
        from dcs_chess.pgn.model import Game
        assert GameBuilder.GameClass()() is not None
        assert isinstance(GameBuilder.GameClass()(), Game)

    def test_headers_builder_end_headers_returns_skip(self):
        hb = HeadersBuilder()
        hb.begin_headers()
        result = hb.end_headers()
        assert result is SKIP

    def test_skip_visitor_begin_game_returns_skip(self):
        sv = SkipVisitor()
        assert sv.begin_game() is SKIP

    def test_skip_visitor_result_is_true(self):
        sv = SkipVisitor()
        assert sv.result() is True

    def test_custom_visitor_move_counting(self):
        class MoveCounter(BaseVisitor):
            def __init__(self):
                self.count = 0
            def visit_move(self, board, move):
                self.count += 1
            def result(self):
                return self.count

        pgn = '[Result "*"]\n\n1. e4 e5 2. Nf3 Nc6 *\n'
        count = read_game(io.StringIO(pgn), Visitor=MoveCounter)
        assert count == 4


# =====================================================================
# 11. read_headers differential
# =====================================================================

class TestReadHeadersDiff:
    def test_basic_headers(self):
        pgn = '[Event "Test"]\n[White "Alice"]\n[Black "Bob"]\n[Result "1-0"]\n\n1. e4 1-0\n'
        ours = read_headers(io.StringIO(pgn))
        theirs = ref.read_headers(io.StringIO(pgn))
        for key in ("Event", "White", "Black", "Result"):
            assert ours[key] == theirs[key]

    def test_read_headers_skips_moves(self):
        pgn = '[Event "A"]\n[Result "*"]\n\n1. e4 e5 *\n\n[Event "B"]\n[Result "*"]\n\n1. d4 *\n'
        oh = io.StringIO(pgn)
        rh = io.StringIO(pgn)
        h1 = read_headers(oh)
        rh1 = ref.read_headers(rh)
        assert h1["Event"] == rh1["Event"] == "A"
        h2 = read_headers(oh)
        rh2 = ref.read_headers(rh)
        assert h2["Event"] == rh2["Event"] == "B"

    def test_read_headers_returns_none_on_empty(self):
        assert read_headers(io.StringIO("")) is None
        assert ref.read_headers(io.StringIO("")) is None


# =====================================================================
# 12. skip_game differential
# =====================================================================

class TestSkipGameDiff:
    def test_skip_returns_true_for_game(self):
        pgn = '[Event "A"]\n[Result "*"]\n\n1. e4 *\n'
        assert skip_game(io.StringIO(pgn)) == True

    def test_skip_returns_false_for_empty(self):
        assert skip_game(io.StringIO("")) == False

    def test_skip_positions_handle_correctly(self):
        pgn = '[Event "A"]\n[Result "*"]\n\n1. e4 *\n\n[Event "B"]\n[Result "*"]\n\n1. d4 *\n'
        oh = io.StringIO(pgn)
        rh = io.StringIO(pgn)
        assert skip_game(oh) == True
        assert ref.skip_game(rh) == True
        g = read_game(oh)
        rg = ref.read_game(rh)
        assert g.headers["Event"] == rg.headers["Event"] == "B"


# =====================================================================
# 13. Result token handling
# =====================================================================

class TestResultTokens:
    def test_all_result_types(self):
        for result in ("1-0", "0-1", "1/2-1/2", "*"):
            pgn = f'[Result "{result}"]\n\n1. e4 e5 {result}\n'
            ours, theirs = _read_both(pgn)
            assert ours.headers["Result"] == theirs.headers["Result"] == result
            assert _moves_uci(ours) == _moves_uci(theirs)

    def test_result_without_header(self):
        pgn = '[Result "*"]\n\n1. e4 e5 1-0\n'
        ours, theirs = _read_both(pgn)
        assert ours.headers["Result"] == theirs.headers["Result"]
