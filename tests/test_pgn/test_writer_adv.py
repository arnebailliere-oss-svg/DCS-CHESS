"""ADV adversarial differential tests for PGN-005: writer module."""

from __future__ import annotations

import io
import inspect

import chess
import chess.pgn as ref

import dcs_chess.pgn as dcs_pgn
from dcs_chess.pgn import (
    read_game,
    StringExporter,
    StringExporterMixin,
    FileExporter,
)
import dcs_chess.pgn.writer as dcs_writer


# =====================================================================
# Helper
# =====================================================================

def _export(pgn_str: str, **kwargs) -> tuple[str, str]:
    game = read_game(io.StringIO(pgn_str))
    ours = game.accept(StringExporter(**kwargs))
    rg = ref.read_game(io.StringIO(pgn_str))
    theirs = rg.accept(ref.StringExporter(**kwargs))
    return ours, theirs


def _file_export(pgn_str: str, **kwargs) -> tuple[str, int, str, int]:
    game = read_game(io.StringIO(pgn_str))
    buf = io.StringIO()
    count = game.accept(FileExporter(buf, **kwargs))
    rg = ref.read_game(io.StringIO(pgn_str))
    rbuf = io.StringIO()
    rcount = rg.accept(ref.FileExporter(rbuf, **kwargs))
    return buf.getvalue(), count, rbuf.getvalue(), rcount


# =====================================================================
# 1. Line wrapping edge cases
# =====================================================================

class TestLineWrapping:
    def test_token_exactly_at_column_boundary(self):
        """Token that would make line exactly == columns."""
        pgn = '[Result "*"]\n\n1. e4 e5 2. Nf3 Nc6 3. Bb5 a6 4. Ba4 Nf6 5. O-O Be7 6. Re1 b5 7. Bb3 d6 8. c3 O-O 9. h3 Nb8 10. d4 Nbd7 *\n'
        ours, theirs = _export(pgn, columns=80)
        assert ours == theirs

    def test_columns_zero(self):
        pgn = '[Result "*"]\n\n1. e4 e5 2. Nf3 Nc6 *\n'
        ours, theirs = _export(pgn, columns=0)
        assert ours == theirs

    def test_columns_negative(self):
        pgn = '[Result "*"]\n\n1. e4 e5 *\n'
        ours, theirs = _export(pgn, columns=-1)
        assert ours == theirs

    def test_columns_very_narrow(self):
        pgn = '[Result "*"]\n\n1. e4 e5 2. Nf3 *\n'
        ours, theirs = _export(pgn, columns=10)
        assert ours == theirs

    def test_columns_1(self):
        pgn = '[Result "*"]\n\n1. e4 e5 *\n'
        ours, theirs = _export(pgn, columns=1)
        assert ours == theirs

    def test_very_long_game(self):
        """Long game to exercise wrapping multiple times."""
        moves = "1. e4 e5 2. Nf3 Nc6 3. Bb5 a6 4. Ba4 Nf6 5. O-O Be7 6. Re1 b5 7. Bb3 d6 8. c3 O-O 9. h3 Nb8 10. d4 Nbd7 11. Nbd2 Bb7 12. Bc2 Re8 13. Nf1 Bf8 14. Ng3 g6 15. Bg5 h6 16. Bd2 Bg7"
        pgn = f'[Result "*"]\n\n{moves} *\n'
        ours, theirs = _export(pgn, columns=80)
        assert ours == theirs

    def test_single_long_token(self):
        """A comment longer than columns is still placed on its own line."""
        pgn = '[Result "*"]\n\n1. e4 {This is a very very very very very very very very very very long comment that exceeds eighty columns for sure} e5 *\n'
        ours, theirs = _export(pgn, columns=80)
        assert ours == theirs

    def test_no_wrap_none_columns(self):
        """columns=None should produce a single long movetext line."""
        pgn = '[Result "*"]\n\n1. e4 e5 2. Nf3 Nc6 3. Bb5 a6 4. Ba4 Nf6 5. O-O Be7 6. Re1 b5 7. Bb3 d6 8. c3 O-O 9. h3 Nb8 10. d4 Nbd7 *\n'
        ours, theirs = _export(pgn, columns=None)
        assert ours == theirs


# =====================================================================
# 2. Move number formatting
# =====================================================================

class TestMoveNumberFormatting:
    def test_black_move_after_comment(self):
        """Comment forces move number on Black's next move."""
        pgn = '[Result "*"]\n\n1. e4 {best move} e5 *\n'
        ours, theirs = _export(pgn)
        assert ours == theirs
        assert "1..." in ours

    def test_black_move_after_variation(self):
        """Variation forces move number on continuation."""
        pgn = '[Result "*"]\n\n1. e4 (1. d4) 1... e5 *\n'
        ours, theirs = _export(pgn)
        assert ours == theirs
        assert "1..." in ours

    def test_no_spurious_move_number(self):
        """Normal Black move should NOT get move number."""
        pgn = '[Result "*"]\n\n1. e4 e5 2. Nf3 Nc6 *\n'
        ours, theirs = _export(pgn)
        assert ours == theirs
        assert "1..." not in ours

    def test_black_move_after_nag_no_move_number(self):
        """NAG does NOT force move number (only comment does)."""
        pgn = '[Result "*"]\n\n1. e4 $1 e5 *\n'
        ours, theirs = _export(pgn)
        assert ours == theirs
        assert "1..." not in ours

    def test_variation_starting_with_black_move(self):
        """Variation that starts with Black's move."""
        pgn = '[Result "*"]\n\n1. e4 e5 (1... d5) 2. Nf3 *\n'
        ours, theirs = _export(pgn)
        assert ours == theirs

    def test_multiple_variations_move_numbers(self):
        """Multiple sidelines each get correct move numbers."""
        pgn = '[Result "*"]\n\n1. e4 (1. d4) (1. c4) (1. Nf3) 1... e5 *\n'
        ours, theirs = _export(pgn)
        assert ours == theirs

    def test_high_move_number(self):
        """Move number >100 formats correctly."""
        pgn = '[Result "*"]\n\n'
        rg = chess.pgn.Game()
        b = chess.Board()
        moves = []
        for san in ["e4", "e5", "Nf3", "Nc6", "Bb5", "a6", "Ba4", "Nf6", "O-O", "Be7", "Re1", "b5", "Bb3", "d6"]:
            m = b.parse_san(san)
            moves.append(m)
            b.push(m)
        node = rg
        for m in moves:
            node = node.add_variation(m)
        pgn_str = str(rg)
        ours, theirs = _export(pgn_str)
        assert ours == theirs


# =====================================================================
# 3. FileExporter accuracy
# =====================================================================

class TestFileExporterAccuracy:
    def test_char_count_matches_content(self):
        pgn = '[Event "Test"]\n[Result "*"]\n\n1. e4 e5 2. Nf3 Nc6 *\n'
        text, count, rtext, rcount = _file_export(pgn)
        assert text == rtext
        assert count == rcount
        assert count == len(text)

    def test_file_exporter_trailing_newlines(self):
        pgn = '[Result "*"]\n\n1. e4 *\n'
        text, _, rtext, _ = _file_export(pgn)
        assert text == rtext
        assert text.endswith('\n\n')

    def test_file_exporter_no_headers(self):
        pgn = '[Event "X"]\n[Result "*"]\n\n1. e4 e5 *\n'
        text, count, rtext, rcount = _file_export(pgn, headers=False)
        assert text == rtext
        assert count == rcount

    def test_file_exporter_no_comments(self):
        pgn = '[Result "*"]\n\n1. e4 {blah} e5 $1 *\n'
        text, count, rtext, rcount = _file_export(pgn, comments=False)
        assert text == rtext
        assert count == rcount

    def test_file_exporter_no_variations(self):
        pgn = '[Result "*"]\n\n1. e4 (1. d4) 1... e5 *\n'
        text, count, rtext, rcount = _file_export(pgn, variations=False)
        assert text == rtext
        assert count == rcount

    def test_file_exporter_narrow_columns(self):
        pgn = '[Result "*"]\n\n1. e4 e5 2. Nf3 Nc6 3. Bb5 a6 *\n'
        text, count, rtext, rcount = _file_export(pgn, columns=30)
        assert text == rtext
        assert count == rcount

    def test_file_exporter_no_columns(self):
        pgn = '[Result "*"]\n\n1. e4 e5 2. Nf3 Nc6 *\n'
        text, count, rtext, rcount = _file_export(pgn, columns=None)
        assert text == rtext
        assert count == rcount


# =====================================================================
# 4. NAG constants completeness
# =====================================================================

class TestNAGConstants:
    def test_complete_nag_set(self):
        """Our NAG_* set matches python-chess exactly."""
        ours = {k: getattr(dcs_writer, k) for k in dir(dcs_writer) if k.startswith("NAG_")}
        theirs = {k: getattr(ref, k) for k in dir(ref) if k.startswith("NAG_")}
        assert ours == theirs, f"Missing: {set(theirs) - set(ours)}, Extra: {set(ours) - set(theirs)}"

    def test_nag_module_level_export(self):
        """NAGs are accessible from dcs_chess.pgn."""
        ours = {k for k in dir(dcs_pgn) if k.startswith("NAG_")}
        theirs = {k for k in dir(ref) if k.startswith("NAG_")}
        assert ours == theirs

    def test_nag_specific_values(self):
        """Spot-check specific NAG values."""
        pairs = [
            ("NAG_NULL", 0),
            ("NAG_GOOD_MOVE", 1),
            ("NAG_MISTAKE", 2),
            ("NAG_BRILLIANT_MOVE", 3),
            ("NAG_BLUNDER", 4),
            ("NAG_SPECULATIVE_MOVE", 5),
            ("NAG_DUBIOUS_MOVE", 6),
            ("NAG_FORCED_MOVE", 7),
            ("NAG_SINGULAR_MOVE", 8),
            ("NAG_WORST_MOVE", 9),
            ("NAG_DRAWISH_POSITION", 10),
            ("NAG_WHITE_SLIGHT_ADVANTAGE", 14),
            ("NAG_BLACK_SLIGHT_ADVANTAGE", 15),
            ("NAG_WHITE_DECISIVE_ADVANTAGE", 18),
            ("NAG_BLACK_DECISIVE_ADVANTAGE", 19),
            ("NAG_WHITE_ZUGZWANG", 22),
            ("NAG_BLACK_ZUGZWANG", 23),
            ("NAG_NOVELTY", 146),
        ]
        for name, value in pairs:
            assert getattr(dcs_writer, name) == value, f"{name} should be {value}"
            assert getattr(ref, name) == value, f"ref {name} should be {value}"


# =====================================================================
# 5. Options interaction
# =====================================================================

class TestOptionsInteraction:
    def test_comments_false_suppresses_nags(self):
        pgn = '[Result "*"]\n\n1. e4 $1 $3 e5 $2 *\n'
        ours, theirs = _export(pgn, comments=False)
        assert ours == theirs
        assert "$" not in ours

    def test_comments_false_suppresses_comments(self):
        pgn = '[Result "*"]\n\n1. e4 {brilliant!} e5 *\n'
        ours, theirs = _export(pgn, comments=False)
        assert ours == theirs
        assert "{" not in ours

    def test_variations_false_suppresses_sidelines(self):
        pgn = '[Result "*"]\n\n1. e4 (1. d4) (1. c4) 1... e5 *\n'
        ours, theirs = _export(pgn, variations=False)
        assert ours == theirs
        assert "(" not in ours

    def test_headers_false_no_tags(self):
        pgn = '[Event "Test"]\n[Site "NYC"]\n[Result "*"]\n\n1. e4 *\n'
        ours, theirs = _export(pgn, headers=False)
        assert ours == theirs
        assert "[" not in ours

    def test_all_options_false(self):
        pgn = '[Event "X"]\n[Result "*"]\n\n1. e4 {wow} $3 (1. d4) 1... e5 *\n'
        ours, theirs = _export(pgn, headers=False, comments=False, variations=False)
        assert ours == theirs

    def test_headers_only(self):
        """headers=True, rest False, minimal game."""
        pgn = '[Event "Y"]\n[Result "*"]\n\n1. e4 {hi} e5 $1 (1... d5) *\n'
        ours, theirs = _export(pgn, comments=False, variations=False)
        assert ours == theirs


# =====================================================================
# 6. Roundtrip stability
# =====================================================================

class TestRoundtrip:
    def test_simple_roundtrip(self):
        pgn = '[Event "RT"]\n[Result "1-0"]\n\n1. e4 e5 2. Nf3 Nc6 1-0\n'
        game = read_game(io.StringIO(pgn))
        text1 = str(game)
        game2 = read_game(io.StringIO(text1))
        text2 = str(game2)
        assert text1 == text2

    def test_roundtrip_with_variations(self):
        pgn = '[Result "*"]\n\n1. e4 e5 (1... d5 2. exd5 Qxd5 (2... Nf6)) 2. Nf3 Nc6 (2... d6) *\n'
        game = read_game(io.StringIO(pgn))
        text1 = str(game)
        game2 = read_game(io.StringIO(text1))
        text2 = str(game2)
        assert text1 == text2

    def test_roundtrip_with_comments_and_nags(self):
        pgn = '[Result "*"]\n\n1. e4 $1 {Best move} e5 $2 2. Nf3 {knight} *\n'
        game = read_game(io.StringIO(pgn))
        text1 = str(game)
        game2 = read_game(io.StringIO(text1))
        text2 = str(game2)
        assert text1 == text2

    def test_roundtrip_matches_ref(self):
        """Our roundtrip output matches python-chess roundtrip output."""
        pgn = '[Event "Big"]\n[Result "*"]\n\n1. e4 e5 (1... c5 2. Nf3 d6 {Sicilian}) 2. Nf3 {knight out} Nc6 $1 3. Bb5 a6 *\n'
        game = read_game(io.StringIO(pgn))
        our_rt = str(read_game(io.StringIO(str(game))))

        rg = ref.read_game(io.StringIO(pgn))
        ref_rt = str(ref.read_game(io.StringIO(str(rg))))

        assert our_rt == ref_rt


# =====================================================================
# 7. Root comments
# =====================================================================

class TestRootComments:
    def test_root_comment_before_moves(self):
        pgn = '[Result "*"]\n\n{This is a root comment} 1. e4 e5 *\n'
        ours, theirs = _export(pgn)
        assert ours == theirs

    def test_multiple_root_comments(self):
        """Multiple comments at root level."""
        pgn = '[Result "*"]\n\n{Comment 1} {Comment 2} 1. e4 *\n'
        ours, theirs = _export(pgn)
        assert ours == theirs

    def test_empty_game_with_root_comment(self):
        pgn = '[Result "*"]\n\n{Just a comment} *\n'
        ours, theirs = _export(pgn)
        assert ours == theirs

    def test_root_comment_with_nag(self):
        pgn = '[Result "*"]\n\n{comment} $1 1. e4 *\n'
        ours, theirs = _export(pgn)
        assert ours == theirs


# =====================================================================
# 8. API surface parity
# =====================================================================

class TestAPIParity:
    def test_string_exporter_signature(self):
        ref_params = list(inspect.signature(ref.StringExporter.__init__).parameters.keys())
        our_params = list(inspect.signature(StringExporter.__init__).parameters.keys())
        assert our_params == ref_params

    def test_file_exporter_signature(self):
        ref_params = list(inspect.signature(ref.FileExporter.__init__).parameters.keys())
        our_params = list(inspect.signature(FileExporter.__init__).parameters.keys())
        assert our_params == ref_params

    def test_string_exporter_mro(self):
        ref_mro = [c.__name__ for c in ref.StringExporter.__mro__]
        our_mro = [c.__name__ for c in StringExporter.__mro__]
        assert our_mro == ref_mro

    def test_file_exporter_mro(self):
        ref_mro = [c.__name__ for c in ref.FileExporter.__mro__]
        our_mro = [c.__name__ for c in FileExporter.__mro__]
        assert our_mro == ref_mro

    def test_string_exporter_result_type(self):
        pgn = '[Result "*"]\n\n1. e4 *\n'
        game = read_game(io.StringIO(pgn))
        result = game.accept(StringExporter())
        assert isinstance(result, str)

    def test_file_exporter_result_type(self):
        pgn = '[Result "*"]\n\n1. e4 *\n'
        game = read_game(io.StringIO(pgn))
        buf = io.StringIO()
        result = game.accept(FileExporter(buf))
        assert isinstance(result, int)


# =====================================================================
# 9. Edge cases
# =====================================================================

class TestEdgeCases:
    def test_game_with_only_result(self):
        pgn = '[Result "1-0"]\n\n1-0\n'
        ours, theirs = _export(pgn)
        assert ours == theirs

    def test_game_with_star_result(self):
        pgn = '[Result "*"]\n\n*\n'
        ours, theirs = _export(pgn)
        assert ours == theirs

    def test_draw_result(self):
        pgn = '[Result "1/2-1/2"]\n\n1. e4 e5 1/2-1/2\n'
        ours, theirs = _export(pgn)
        assert ours == theirs

    def test_castling_kingside(self):
        pgn = '[Result "*"]\n\n1. e4 e5 2. Nf3 Nc6 3. Bb5 a6 4. Ba4 Nf6 5. O-O *\n'
        ours, theirs = _export(pgn)
        assert ours == theirs

    def test_castling_queenside(self):
        pgn = '[Result "*"]\n\n1. d4 d5 2. c4 e6 3. Nc3 Nf6 4. Bg5 Be7 5. e3 O-O 6. Nf3 Nbd7 7. Qc2 c5 8. O-O-O *\n'
        ours, theirs = _export(pgn)
        assert ours == theirs

    def test_promotion(self):
        fen = "4k3/P7/8/8/8/8/8/4K3 w - - 0 1"
        pgn = f'[FEN "{fen}"]\n[SetUp "1"]\n[Result "*"]\n\n1. a8=Q *\n'
        ours, theirs = _export(pgn)
        assert ours == theirs

    def test_many_headers(self):
        headers = '\n'.join([
            '[Event "Test"]',
            '[Site "London"]',
            '[Date "2024.01.01"]',
            '[Round "1"]',
            '[White "A"]',
            '[Black "B"]',
            '[Result "1-0"]',
        ])
        pgn = f'{headers}\n\n1. e4 e5 1-0\n'
        ours, theirs = _export(pgn)
        assert ours == theirs

    def test_empty_comment(self):
        pgn = '[Result "*"]\n\n1. e4 {} e5 *\n'
        ours, theirs = _export(pgn)
        assert ours == theirs
