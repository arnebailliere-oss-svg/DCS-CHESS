"""PGN-ATP: PGN acceptance test suite — full pipeline differential testing.

Tests the complete PGN stack (model + reader + visitors + writer) against
python-chess. Every test reads/writes/round-trips PGN through both libraries
and asserts identical results.
"""

from __future__ import annotations

import io
import textwrap

import chess
import chess.pgn as ref
import pytest

from dcs_chess.pgn import (
    read_game,
    read_headers,
    skip_game,
    StringExporter,
    FileExporter,
)


# =====================================================================
# Helpers
# =====================================================================

def _read_both(pgn_str: str):
    """Read same PGN with both libraries, return (ours, ref)."""
    ours = read_game(io.StringIO(pgn_str))
    theirs = ref.read_game(io.StringIO(pgn_str))
    return ours, theirs


def _assert_game_equal(ours, theirs, msg=""):
    """Assert two games produce identical PGN output."""
    our_pgn = str(ours) if ours else None
    ref_pgn = str(theirs) if theirs else None
    assert our_pgn == ref_pgn, f"PGN mismatch{' (' + msg + ')' if msg else ''}"


def _assert_moves_equal(ours, theirs, msg=""):
    """Assert mainline move lists are identical."""
    if ours is None and theirs is None:
        return
    our_moves = [str(m) for m in ours.mainline_moves()]
    ref_moves = [str(m) for m in theirs.mainline_moves()]
    assert our_moves == ref_moves, f"Moves mismatch{' (' + msg + ')' if msg else ''}"


def _assert_headers_equal(ours, theirs, msg=""):
    """Assert headers match."""
    if ours is None and theirs is None:
        return
    our_headers = dict(ours.headers)
    ref_headers = dict(theirs.headers)
    assert our_headers == ref_headers, f"Headers mismatch{' (' + msg + ')' if msg else ''}"


# =====================================================================
# 1. Standard game parsing — mainline
# =====================================================================

class TestStandardGames:
    GAMES = [
        ("Italian Game", '[Event "Match"]\n[Result "1-0"]\n\n1. e4 e5 2. Nf3 Nc6 3. Bc4 Bc5 1-0\n'),
        ("Sicilian", '[Event "Tourney"]\n[Result "0-1"]\n\n1. e4 c5 2. Nf3 d6 3. d4 cxd4 4. Nxd4 Nf6 5. Nc3 a6 0-1\n'),
        ("Queen's Gambit", '[Result "1/2-1/2"]\n\n1. d4 d5 2. c4 e6 3. Nc3 Nf6 4. Bg5 Be7 5. e3 O-O 6. Nf3 Nbd7 1/2-1/2\n'),
        ("Castling Both", '[Result "*"]\n\n1. e4 e5 2. Nf3 Nc6 3. Bb5 a6 4. Ba4 Nf6 5. O-O Be7 6. Re1 b5 7. Bb3 d6 8. c3 O-O *\n'),
        ("Long Ruy Lopez", '[Result "1-0"]\n\n1. e4 e5 2. Nf3 Nc6 3. Bb5 a6 4. Ba4 Nf6 5. O-O Be7 6. Re1 b5 7. Bb3 d6 8. c3 O-O 9. h3 Nb8 10. d4 Nbd7 11. Nbd2 Bb7 12. Bc2 Re8 13. Nf1 Bf8 14. Ng3 g6 1-0\n'),
    ]

    @pytest.mark.parametrize("name,pgn", GAMES, ids=[g[0] for g in GAMES])
    def test_mainline_moves(self, name, pgn):
        ours, theirs = _read_both(pgn)
        _assert_moves_equal(ours, theirs, name)

    @pytest.mark.parametrize("name,pgn", GAMES, ids=[g[0] for g in GAMES])
    def test_headers(self, name, pgn):
        ours, theirs = _read_both(pgn)
        _assert_headers_equal(ours, theirs, name)

    @pytest.mark.parametrize("name,pgn", GAMES, ids=[g[0] for g in GAMES])
    def test_str_output(self, name, pgn):
        ours, theirs = _read_both(pgn)
        _assert_game_equal(ours, theirs, name)


# =====================================================================
# 2. Variations
# =====================================================================

class TestVariations:
    def test_single_variation(self):
        pgn = '[Result "*"]\n\n1. e4 (1. d4) 1... e5 *\n'
        ours, theirs = _read_both(pgn)
        _assert_game_equal(ours, theirs)

    def test_multiple_sidelines(self):
        pgn = '[Result "*"]\n\n1. e4 (1. d4) (1. c4) (1. Nf3) 1... e5 *\n'
        ours, theirs = _read_both(pgn)
        _assert_game_equal(ours, theirs)

    def test_nested_variations(self):
        pgn = '[Result "*"]\n\n1. e4 (1. d4 d5 (1... Nf6 2. c4)) 1... e5 *\n'
        ours, theirs = _read_both(pgn)
        _assert_game_equal(ours, theirs)

    def test_deep_nesting(self):
        pgn = '[Result "*"]\n\n1. e4 e5 (1... d5 2. exd5 Qxd5 (2... Nf6 3. d4)) 2. Nf3 *\n'
        ours, theirs = _read_both(pgn)
        _assert_game_equal(ours, theirs)

    def test_variation_after_black(self):
        pgn = '[Result "*"]\n\n1. e4 e5 (1... c5 2. Nf3 d6) 2. Nf3 Nc6 *\n'
        ours, theirs = _read_both(pgn)
        _assert_game_equal(ours, theirs)

    def test_variation_count_match(self):
        pgn = '[Result "*"]\n\n1. e4 (1. d4) (1. c4) 1... e5 (1... d5) *\n'
        ours, theirs = _read_both(pgn)
        our_root_vars = len(list(ours.variations))
        ref_root_vars = len(list(theirs.variations))
        assert our_root_vars == ref_root_vars


# =====================================================================
# 3. Comments and NAGs
# =====================================================================

class TestCommentsAndNags:
    def test_brace_comment(self):
        pgn = '[Result "*"]\n\n1. e4 {Best move!} e5 *\n'
        ours, theirs = _read_both(pgn)
        _assert_game_equal(ours, theirs)

    def test_multiline_brace_comment(self):
        pgn = '[Result "*"]\n\n1. e4 {This is\na multi-line\ncomment} e5 *\n'
        ours, theirs = _read_both(pgn)
        _assert_game_equal(ours, theirs)

    def test_semicolon_comment(self):
        pgn = '[Result "*"]\n\n1. e4 ;a comment\ne5 *\n'
        ours, theirs = _read_both(pgn)
        _assert_moves_equal(ours, theirs)

    def test_root_comment(self):
        pgn = '[Result "*"]\n\n{Root comment} 1. e4 e5 *\n'
        ours, theirs = _read_both(pgn)
        _assert_game_equal(ours, theirs)

    def test_nags(self):
        pgn = '[Result "*"]\n\n1. e4 $1 $3 e5 $2 $146 *\n'
        ours, theirs = _read_both(pgn)
        _assert_game_equal(ours, theirs)

    def test_comment_then_nag(self):
        pgn = '[Result "*"]\n\n1. e4 {brilliant} $3 e5 *\n'
        ours, theirs = _read_both(pgn)
        _assert_game_equal(ours, theirs)

    def test_comment_in_variation(self):
        pgn = '[Result "*"]\n\n1. e4 (1. d4 {queen pawn}) 1... e5 *\n'
        ours, theirs = _read_both(pgn)
        _assert_game_equal(ours, theirs)


# =====================================================================
# 4. Multi-game streaming
# =====================================================================

class TestMultiGame:
    def test_two_games(self):
        pgn = '[Result "1-0"]\n\n1. e4 e5 1-0\n\n[Result "0-1"]\n\n1. d4 d5 0-1\n'
        handle = io.StringIO(pgn)
        ref_handle = io.StringIO(pgn)

        g1 = read_game(handle)
        r1 = ref.read_game(ref_handle)
        _assert_game_equal(g1, r1, "game 1")

        g2 = read_game(handle)
        r2 = ref.read_game(ref_handle)
        _assert_game_equal(g2, r2, "game 2")

        g3 = read_game(handle)
        r3 = ref.read_game(ref_handle)
        assert g3 is None and r3 is None

    def test_three_games(self):
        games = [
            '[Result "1-0"]\n\n1. e4 e5 1-0\n',
            '[Result "0-1"]\n\n1. d4 d5 0-1\n',
            '[Result "*"]\n\n1. c4 c5 *\n',
        ]
        pgn = "\n".join(games)
        handle = io.StringIO(pgn)
        ref_handle = io.StringIO(pgn)

        for i in range(3):
            ours = read_game(handle)
            theirs = ref.read_game(ref_handle)
            _assert_game_equal(ours, theirs, f"game {i+1}")

    def test_skip_then_read(self):
        pgn = '[Result "1-0"]\n\n1. e4 e5 1-0\n\n[Result "0-1"]\n\n1. d4 d5 0-1\n'
        handle = io.StringIO(pgn)
        ref_handle = io.StringIO(pgn)

        skip_game(handle)
        ref.skip_game(ref_handle)

        g = read_game(handle)
        r = ref.read_game(ref_handle)
        _assert_game_equal(g, r, "after skip")


# =====================================================================
# 5. Headers
# =====================================================================

class TestHeaders:
    def test_read_headers(self):
        pgn = '[Event "Match"]\n[Site "London"]\n[Date "2024.01.01"]\n[Round "1"]\n[White "A"]\n[Black "B"]\n[Result "1-0"]\n\n1. e4 1-0\n'
        ours = read_headers(io.StringIO(pgn))
        theirs = ref.read_headers(io.StringIO(pgn))
        assert dict(ours) == dict(theirs)

    def test_headers_streaming(self):
        pgn = '[Event "G1"]\n[Result "*"]\n\n1. e4 *\n\n[Event "G2"]\n[Result "*"]\n\n1. d4 *\n'
        handle = io.StringIO(pgn)
        ref_handle = io.StringIO(pgn)

        h1 = read_headers(handle)
        rh1 = ref.read_headers(ref_handle)
        assert dict(h1) == dict(rh1)

        h2 = read_headers(handle)
        rh2 = ref.read_headers(ref_handle)
        assert dict(h2) == dict(rh2)

    def test_seven_tag_roster_defaults(self):
        pgn = '[Result "*"]\n\n*\n'
        ours, theirs = _read_both(pgn)
        _assert_headers_equal(ours, theirs, "STR defaults")

    def test_custom_headers_preserved(self):
        pgn = '[Event "X"]\n[CustomTag "CustomValue"]\n[Result "*"]\n\n*\n'
        ours, theirs = _read_both(pgn)
        _assert_headers_equal(ours, theirs)


# =====================================================================
# 6. FEN / SetUp positions
# =====================================================================

class TestFENPositions:
    def test_custom_fen(self):
        fen = "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq e3 0 1"
        pgn = f'[FEN "{fen}"]\n[SetUp "1"]\n[Result "*"]\n\n1... e5 *\n'
        ours, theirs = _read_both(pgn)
        _assert_moves_equal(ours, theirs)
        _assert_game_equal(ours, theirs)

    def test_endgame_fen(self):
        fen = "8/8/4k3/8/8/4K3/4P3/8 w - - 0 1"
        pgn = f'[FEN "{fen}"]\n[SetUp "1"]\n[Result "*"]\n\n1. Kd4 Kd6 *\n'
        ours, theirs = _read_both(pgn)
        _assert_moves_equal(ours, theirs)

    def test_promotion_from_fen(self):
        fen = "4k3/P7/8/8/8/8/8/4K3 w - - 0 1"
        pgn = f'[FEN "{fen}"]\n[SetUp "1"]\n[Result "1-0"]\n\n1. a8=Q+ Kd7 1-0\n'
        ours, theirs = _read_both(pgn)
        _assert_moves_equal(ours, theirs)


# =====================================================================
# 7. Roundtrip: read → write → read
# =====================================================================

class TestRoundtrip:
    ROUNDTRIP_PGNS = [
        ("simple", '[Event "X"]\n[Result "1-0"]\n\n1. e4 e5 2. Nf3 Nc6 1-0\n'),
        ("with_variation", '[Result "*"]\n\n1. e4 e5 (1... d5) 2. Nf3 *\n'),
        ("with_comments", '[Result "*"]\n\n1. e4 {best} e5 $1 2. Nf3 {knight} *\n'),
        ("complex", '[Event "Big"]\n[Result "*"]\n\n1. e4 e5 (1... c5 2. Nf3 d6 {Sicilian}) 2. Nf3 {knight out} Nc6 $1 3. Bb5 a6 *\n'),
        ("castling", '[Result "1-0"]\n\n1. e4 e5 2. Nf3 Nc6 3. Bb5 a6 4. Ba4 Nf6 5. O-O Be7 6. Re1 b5 7. Bb3 d6 8. c3 O-O 1-0\n'),
    ]

    @pytest.mark.parametrize("name,pgn", ROUNDTRIP_PGNS, ids=[g[0] for g in ROUNDTRIP_PGNS])
    def test_roundtrip_stability(self, name, pgn):
        game = read_game(io.StringIO(pgn))
        text1 = str(game)
        game2 = read_game(io.StringIO(text1))
        text2 = str(game2)
        assert text1 == text2, f"Roundtrip not stable for: {name}"

    @pytest.mark.parametrize("name,pgn", ROUNDTRIP_PGNS, ids=[g[0] for g in ROUNDTRIP_PGNS])
    def test_roundtrip_matches_ref(self, name, pgn):
        game = read_game(io.StringIO(pgn))
        rg = ref.read_game(io.StringIO(pgn))
        our_rt = str(read_game(io.StringIO(str(game))))
        ref_rt = str(ref.read_game(io.StringIO(str(rg))))
        assert our_rt == ref_rt, f"Roundtrip diverges from ref for: {name}"


# =====================================================================
# 8. Writer options
# =====================================================================

class TestWriterOptions:
    PGN = '[Event "Test"]\n[Result "*"]\n\n1. e4 {brilliant} $3 e5 (1... d5) *\n'

    @pytest.mark.parametrize("kwargs", [
        {"headers": False},
        {"comments": False},
        {"variations": False},
        {"columns": None},
        {"columns": 40},
        {"headers": False, "comments": False, "variations": False},
    ])
    def test_string_exporter_options(self, kwargs):
        game = read_game(io.StringIO(self.PGN))
        rg = ref.read_game(io.StringIO(self.PGN))
        ours = game.accept(StringExporter(**kwargs))
        theirs = rg.accept(ref.StringExporter(**kwargs))
        assert ours == theirs, f"Mismatch with {kwargs}"

    @pytest.mark.parametrize("kwargs", [
        {"headers": False},
        {"comments": False},
        {"variations": False},
        {"columns": None},
        {"columns": 40},
    ])
    def test_file_exporter_options(self, kwargs):
        game = read_game(io.StringIO(self.PGN))
        rg = ref.read_game(io.StringIO(self.PGN))
        buf = io.StringIO()
        count = game.accept(FileExporter(buf, **kwargs))
        rbuf = io.StringIO()
        rcount = rg.accept(ref.FileExporter(rbuf, **kwargs))
        assert buf.getvalue() == rbuf.getvalue(), f"File content mismatch with {kwargs}"
        assert count == rcount, f"Char count mismatch with {kwargs}"


# =====================================================================
# 9. Error recovery
# =====================================================================

class TestErrorRecovery:
    def test_illegal_move_stops_mainline(self):
        pgn = '[Result "*"]\n\n1. e4 Ke7 e5 2. Nf3 *\n'
        ours, theirs = _read_both(pgn)
        _assert_moves_equal(ours, theirs, "illegal move recovery")

    def test_empty_pgn(self):
        ours = read_game(io.StringIO(""))
        theirs = ref.read_game(io.StringIO(""))
        assert ours is None and theirs is None

    def test_only_result(self):
        pgn = '[Result "1-0"]\n\n1-0\n'
        ours, theirs = _read_both(pgn)
        _assert_game_equal(ours, theirs)


# =====================================================================
# 10. Edge cases
# =====================================================================

class TestEdgeCases:
    def test_zero_o_castling(self):
        """0-0 notation (zero) should parse like O-O."""
        pgn = '[Result "*"]\n\n1. e4 e5 2. Nf3 Nc6 3. Bb5 a6 4. Ba4 Nf6 5. 0-0 *\n'
        ours, theirs = _read_both(pgn)
        _assert_moves_equal(ours, theirs)

    def test_null_move(self):
        pgn = '[Result "*"]\n\n1. e4 -- 2. d4 *\n'
        ours, theirs = _read_both(pgn)
        _assert_moves_equal(ours, theirs)

    def test_game_with_eval(self):
        pgn = '[Result "*"]\n\n1. e4 {[%eval 0.50]} e5 {[%eval -0.10]} *\n'
        ours, theirs = _read_both(pgn)
        _assert_game_equal(ours, theirs)

    def test_game_with_clock(self):
        pgn = '[Result "*"]\n\n1. e4 {[%clk 1:30:00]} e5 {[%clk 1:29:55]} *\n'
        ours, theirs = _read_both(pgn)
        _assert_game_equal(ours, theirs)

    def test_all_results(self):
        for result in ("1-0", "0-1", "1/2-1/2", "*"):
            pgn = f'[Result "{result}"]\n\n1. e4 {result}\n'
            ours, theirs = _read_both(pgn)
            _assert_game_equal(ours, theirs, f"result={result}")

    def test_queenside_castling(self):
        pgn = '[Result "*"]\n\n1. d4 d5 2. c4 e6 3. Nc3 Nf6 4. Bg5 Be7 5. e3 O-O 6. Nf3 Nbd7 7. Qc2 c5 8. O-O-O *\n'
        ours, theirs = _read_both(pgn)
        _assert_moves_equal(ours, theirs)
