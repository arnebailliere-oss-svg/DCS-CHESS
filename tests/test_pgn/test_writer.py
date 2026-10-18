"""Differential tests for PGN-005: writer (StringExporter, FileExporter, NAG constants)."""

from __future__ import annotations

import io

import chess
import chess.pgn as ref
import pytest

from dcs_chess.pgn import (
    read_game,
    StringExporter,
    FileExporter,
    StringExporterMixin,
)
import dcs_chess.pgn as dcs_pgn
import chess.pgn as ref_pgn


def _export(pgn_str: str, **kwargs) -> tuple[str, str]:
    """Export the same PGN with both libraries and return (ours, theirs)."""
    game = read_game(io.StringIO(pgn_str))
    our = game.accept(StringExporter(**kwargs))
    rg = ref.read_game(io.StringIO(pgn_str))
    theirs = rg.accept(ref.StringExporter(**kwargs))
    return our, theirs


class TestStringExporterBasic:
    def test_simple_game(self):
        pgn = '[Event "Test"]\n[Result "1-0"]\n\n1. e4 e5 2. Nf3 Nc6 1-0\n'
        ours, theirs = _export(pgn)
        assert ours == theirs

    def test_empty_game(self):
        pgn = '[Event "Empty"]\n[Result "*"]\n\n*\n'
        ours, theirs = _export(pgn)
        assert ours == theirs

    def test_str_uses_exporter(self):
        pgn = '[Event "X"]\n[Result "*"]\n\n1. e4 e5 *\n'
        game = read_game(io.StringIO(pgn))
        rg = ref.read_game(io.StringIO(pgn))
        assert str(game) == str(rg)

    def test_headers_output(self):
        pgn = '[Event "Match"]\n[Site "London"]\n[White "A"]\n[Black "B"]\n[Result "1/2-1/2"]\n\n1. d4 d5 1/2-1/2\n'
        ours, theirs = _export(pgn)
        assert ours == theirs

    def test_all_results(self):
        for result in ("1-0", "0-1", "1/2-1/2", "*"):
            pgn = f'[Result "{result}"]\n\n1. e4 {result}\n'
            ours, theirs = _export(pgn)
            assert ours == theirs, f"Failed for result {result}"


class TestStringExporterOptions:
    def test_no_headers(self):
        pgn = '[Event "Test"]\n[Result "*"]\n\n1. e4 e5 *\n'
        ours, theirs = _export(pgn, headers=False)
        assert ours == theirs

    def test_no_comments(self):
        pgn = '[Result "*"]\n\n1. e4 {Best} e5 $1 *\n'
        ours, theirs = _export(pgn, comments=False)
        assert ours == theirs

    def test_no_variations(self):
        pgn = '[Result "*"]\n\n1. e4 (1. d4) 1... e5 *\n'
        ours, theirs = _export(pgn, variations=False)
        assert ours == theirs

    def test_columns_none(self):
        pgn = '[Result "*"]\n\n1. e4 e5 2. Nf3 Nc6 3. Bb5 a6 4. Ba4 Nf6 5. O-O *\n'
        ours, theirs = _export(pgn, columns=None)
        assert ours == theirs

    def test_columns_40(self):
        pgn = '[Result "*"]\n\n1. e4 e5 2. Nf3 Nc6 3. Bb5 a6 4. Ba4 Nf6 5. O-O Be7 6. Re1 *\n'
        ours, theirs = _export(pgn, columns=40)
        assert ours == theirs

    def test_all_options_false(self):
        pgn = '[Result "*"]\n\n1. e4 {blah} e5 $2 (1... d5) *\n'
        ours, theirs = _export(pgn, headers=False, comments=False, variations=False)
        assert ours == theirs


class TestStringExporterComments:
    def test_inline_comment(self):
        pgn = '[Result "*"]\n\n1. e4 {Good move} e5 *\n'
        ours, theirs = _export(pgn)
        assert ours == theirs

    def test_root_comment(self):
        pgn = '[Result "*"]\n\n{Root comment} 1. e4 *\n'
        ours, theirs = _export(pgn)
        assert ours == theirs

    def test_nag(self):
        pgn = '[Result "*"]\n\n1. e4 $1 $3 e5 $2 *\n'
        ours, theirs = _export(pgn)
        assert ours == theirs

    def test_comment_forces_move_number(self):
        pgn = '[Result "*"]\n\n1. e4 {blah} e5 *\n'
        ours, theirs = _export(pgn)
        assert ours == theirs
        assert "1..." in ours

    def test_nag_no_move_number(self):
        pgn = '[Result "*"]\n\n1. e4 $1 e5 *\n'
        ours, theirs = _export(pgn)
        assert ours == theirs
        assert "1..." not in ours


class TestStringExporterVariations:
    def test_single_variation(self):
        pgn = '[Result "*"]\n\n1. e4 (1. d4) 1... e5 *\n'
        ours, theirs = _export(pgn)
        assert ours == theirs

    def test_variation_with_comment(self):
        pgn = '[Result "*"]\n\n1. e4 e5 2. Nf3 (2. Bc4 {Italian}) Nc6 *\n'
        ours, theirs = _export(pgn)
        assert ours == theirs

    def test_nested_variations(self):
        pgn = '[Result "*"]\n\n1. e4 (1. d4 d5 (1... Nf6 2. c4) 2. c4) 1... e5 *\n'
        ours, theirs = _export(pgn)
        assert ours == theirs

    def test_multiple_sidelines(self):
        pgn = '[Result "*"]\n\n1. e4 (1. d4) (1. c4) (1. Nf3) 1... e5 *\n'
        ours, theirs = _export(pgn)
        assert ours == theirs

    def test_variation_after_black(self):
        pgn = '[Result "*"]\n\n1. e4 e5 (1... c5) 2. Nf3 *\n'
        ours, theirs = _export(pgn)
        assert ours == theirs

    def test_deep_variation(self):
        pgn = '[Result "*"]\n\n1. e4 e5 (1... d5 2. exd5 Qxd5) 2. Nf3 *\n'
        ours, theirs = _export(pgn)
        assert ours == theirs

    def test_move_number_after_variation(self):
        pgn = '[Result "*"]\n\n1. e4 (1. d4) 1... e5 *\n'
        ours, theirs = _export(pgn)
        assert ours == theirs
        assert "1..." in ours


class TestStringExporterLineWrap:
    def test_long_game_wraps(self):
        pgn = '[Result "1-0"]\n\n1. e4 e5 2. Nf3 Nc6 3. Bb5 a6 4. Ba4 Nf6 5. O-O Be7 6. Re1 b5 7. Bb3 d6 8. c3 O-O 9. h3 Nb8 10. d4 Nbd7 1-0\n'
        ours, theirs = _export(pgn, columns=80)
        assert ours == theirs

    def test_narrow_columns(self):
        pgn = '[Result "*"]\n\n1. e4 e5 2. Nf3 Nc6 3. Bb5 a6 4. Ba4 Nf6 5. O-O Be7 6. Re1 *\n'
        ours, theirs = _export(pgn, columns=40)
        assert ours == theirs
        for line in ours.split('\n'):
            if line and not line.startswith('['):
                assert len(line) <= 40 or ' ' not in line


class TestFileExporter:
    def test_basic(self):
        pgn = '[Event "Test"]\n[Result "*"]\n\n1. e4 e5 *\n'
        game = read_game(io.StringIO(pgn))
        buf = io.StringIO()
        count = game.accept(FileExporter(buf))

        rg = ref.read_game(io.StringIO(pgn))
        rbuf = io.StringIO()
        rcount = rg.accept(ref.FileExporter(rbuf))

        assert buf.getvalue() == rbuf.getvalue()
        assert count == rcount

    def test_trailing_newlines(self):
        pgn = '[Result "*"]\n\n1. e4 *\n'
        game = read_game(io.StringIO(pgn))
        buf = io.StringIO()
        game.accept(FileExporter(buf))
        assert buf.getvalue().endswith('\n\n')

    def test_returns_int(self):
        pgn = '[Result "*"]\n\n1. e4 *\n'
        game = read_game(io.StringIO(pgn))
        buf = io.StringIO()
        result = game.accept(FileExporter(buf))
        assert isinstance(result, int)
        assert result == len(buf.getvalue())

    def test_with_variations(self):
        pgn = '[Result "*"]\n\n1. e4 (1. d4) 1... e5 *\n'
        game = read_game(io.StringIO(pgn))
        buf = io.StringIO()
        game.accept(FileExporter(buf))

        rg = ref.read_game(io.StringIO(pgn))
        rbuf = io.StringIO()
        rg.accept(ref.FileExporter(rbuf))

        assert buf.getvalue() == rbuf.getvalue()

    def test_options(self):
        pgn = '[Result "*"]\n\n1. e4 {blah} e5 $1 (1... d5) *\n'
        for kwargs in [
            {"headers": False},
            {"comments": False},
            {"variations": False},
        ]:
            game = read_game(io.StringIO(pgn))
            buf = io.StringIO()
            game.accept(FileExporter(buf, **kwargs))

            rg = ref.read_game(io.StringIO(pgn))
            rbuf = io.StringIO()
            rg.accept(ref.FileExporter(rbuf, **kwargs))

            assert buf.getvalue() == rbuf.getvalue(), f"Failed with {kwargs}"


class TestNAGConstants:
    def test_all_nags_match(self):
        our_nags = {k: getattr(dcs_pgn, k) for k in dir(dcs_pgn) if k.startswith("NAG_")}
        ref_nags = {k: getattr(ref_pgn, k) for k in dir(ref_pgn) if k.startswith("NAG_")}
        assert our_nags == ref_nags

    def test_nag_values(self):
        assert dcs_pgn.NAG_NULL == 0
        assert dcs_pgn.NAG_GOOD_MOVE == 1
        assert dcs_pgn.NAG_BLUNDER == 4
        assert dcs_pgn.NAG_NOVELTY == 146

    def test_nag_roundtrip(self):
        pgn = '[Result "*"]\n\n1. e4 $1 $3 $146 e5 $4 *\n'
        ours, theirs = _export(pgn)
        assert ours == theirs


class TestStringExporterMixinExists:
    def test_mixin_class(self):
        assert hasattr(dcs_pgn, "StringExporterMixin")
        assert issubclass(StringExporter, StringExporterMixin)
        assert issubclass(FileExporter, StringExporterMixin)


class TestRoundtrip:
    def test_read_write_read(self):
        pgn = '[Event "Test"]\n[Result "*"]\n\n1. e4 e5 (1... d5 2. exd5) 2. Nf3 {knight} Nc6 $1 *\n'
        game = read_game(io.StringIO(pgn))
        exported = str(game)
        game2 = read_game(io.StringIO(exported))
        exported2 = str(game2)
        assert exported == exported2

    def test_ref_roundtrip_match(self):
        pgn = '[Event "Match"]\n[Result "1-0"]\n\n1. e4 e5 2. Nf3 Nc6 3. Bb5 a6 1-0\n'
        game = read_game(io.StringIO(pgn))
        rg = ref.read_game(io.StringIO(pgn))
        assert str(game) == str(rg)
