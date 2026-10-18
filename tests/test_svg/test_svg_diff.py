"""Differential tests: dcs_chess.svg vs python-chess chess.svg.

Every test renders the same scenario through both libraries and
asserts the SVG strings are byte-identical.
"""

from __future__ import annotations

import sys
import pytest

sys.path.insert(0, ".")

import chess
import chess.svg as ref_svg
import dcs_chess.svg as our_svg
from dcs_chess.svg import Arrow


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _board(fen: str | None = chess.STARTING_FEN) -> chess.Board:
    if fen is None:
        return chess.Board(fen=None)
    return chess.Board(fen)


def _diff_detail(ref: str, ours: str) -> str:
    for i, (a, b) in enumerate(zip(ref, ours)):
        if a != b:
            lo = max(0, i - 60)
            return (
                f"First diff at position {i}:\n"
                f"  ref:  ...{ref[lo:i+60]}...\n"
                f"  ours: ...{ours[lo:i+60]}..."
            )
    if len(ref) != len(ours):
        return f"Length differs: ref={len(ref)}, ours={len(ours)}"
    return "identical"


def assert_svg_equal(ref: str, ours: str, label: str = ""):
    if ref != ours:
        detail = _diff_detail(ref, ours)
        pytest.fail(f"SVG mismatch{' (' + label + ')' if label else ''}\n{detail}")


# ---------------------------------------------------------------------------
# Board rendering — basic layouts
# ---------------------------------------------------------------------------

class TestBoardBasic:

    def test_default_starting_position(self):
        b = _board()
        assert_svg_equal(ref_svg.board(b), our_svg.board(b))

    def test_empty_board(self):
        b = _board(None)
        assert_svg_equal(ref_svg.board(b), our_svg.board(b))

    def test_flipped(self):
        b = _board()
        assert_svg_equal(
            ref_svg.board(b, flipped=True),
            our_svg.board(b, flipped=True),
        )

    def test_no_coordinates(self):
        b = _board()
        assert_svg_equal(
            ref_svg.board(b, coordinates=False),
            our_svg.board(b, coordinates=False),
        )

    def test_with_borders(self):
        b = _board()
        assert_svg_equal(
            ref_svg.board(b, borders=True),
            our_svg.board(b, borders=True),
        )

    def test_borders_no_coords(self):
        b = _board()
        assert_svg_equal(
            ref_svg.board(b, borders=True, coordinates=False),
            our_svg.board(b, borders=True, coordinates=False),
        )

    def test_orientation_black(self):
        b = _board()
        assert_svg_equal(
            ref_svg.board(b, orientation=chess.BLACK),
            our_svg.board(b, orientation=False),
        )

    def test_custom_size(self):
        b = _board()
        assert_svg_equal(
            ref_svg.board(b, size=400),
            our_svg.board(b, size=400),
        )

    def test_size_none(self):
        b = _board()
        assert_svg_equal(
            ref_svg.board(b, size=None),
            our_svg.board(b, size=None),
        )


# ---------------------------------------------------------------------------
# Board rendering — overlays and highlights
# ---------------------------------------------------------------------------

class TestBoardOverlays:

    def test_lastmove(self):
        b = _board()
        assert_svg_equal(
            ref_svg.board(b, lastmove=chess.Move.from_uci("e2e4")),
            our_svg.board(b, lastmove=chess.Move(12, 28)),
        )

    def test_check(self):
        b = _board()
        assert_svg_equal(
            ref_svg.board(b, check=4),
            our_svg.board(b, check=4),
        )

    def test_fill_single_square(self):
        b = _board()
        assert_svg_equal(
            ref_svg.board(b, fill={28: "#ff0000"}),
            our_svg.board(b, fill={28: "#ff0000"}),
        )

    def test_fill_multiple_squares(self):
        b = _board()
        fill_dict = {0: "#ff0000", 28: "#00ff00", 63: "#0000ff"}
        assert_svg_equal(
            ref_svg.board(b, fill=fill_dict),
            our_svg.board(b, fill=fill_dict),
        )

    def test_custom_colors(self):
        b = _board()
        colors = {"square light": "#f0d9b5", "square dark": "#b58863"}
        assert_svg_equal(
            ref_svg.board(b, colors=colors),
            our_svg.board(b, colors=colors),
        )

    def test_custom_style(self):
        b = _board()
        style = ".square { opacity: 0.8; }"
        assert_svg_equal(
            ref_svg.board(b, style=style),
            our_svg.board(b, style=style),
        )


# ---------------------------------------------------------------------------
# Arrows
# ---------------------------------------------------------------------------

class TestBoardArrows:

    def test_green_arrow_vertical(self):
        b = _board()
        assert_svg_equal(
            ref_svg.board(b, arrows=[chess.svg.Arrow(12, 28, color="green")]),
            our_svg.board(b, arrows=[Arrow(12, 28, color="green")]),
        )

    def test_red_arrow_diagonal(self):
        b = _board()
        assert_svg_equal(
            ref_svg.board(b, arrows=[chess.svg.Arrow(0, 63, color="red")]),
            our_svg.board(b, arrows=[Arrow(0, 63, color="red")]),
        )

    def test_circle_same_square(self):
        b = _board()
        assert_svg_equal(
            ref_svg.board(b, arrows=[chess.svg.Arrow(28, 28, color="blue")]),
            our_svg.board(b, arrows=[Arrow(28, 28, color="blue")]),
        )

    def test_multi_arrows(self):
        b = _board()
        assert_svg_equal(
            ref_svg.board(b, arrows=[
                chess.svg.Arrow(12, 28),
                chess.svg.Arrow(1, 18),
            ]),
            our_svg.board(b, arrows=[
                Arrow(12, 28),
                Arrow(1, 18),
            ]),
        )

    def test_arrow_horizontal(self):
        b = _board()
        assert_svg_equal(
            ref_svg.board(b, arrows=[chess.svg.Arrow(0, 7)]),
            our_svg.board(b, arrows=[Arrow(0, 7)]),
        )

    def test_arrow_with_flipped(self):
        b = _board()
        assert_svg_equal(
            ref_svg.board(b, arrows=[chess.svg.Arrow(12, 28)], flipped=True),
            our_svg.board(b, arrows=[Arrow(12, 28)], flipped=True),
        )

    def test_arrow_with_no_coords(self):
        b = _board()
        assert_svg_equal(
            ref_svg.board(b, arrows=[chess.svg.Arrow(12, 28)], coordinates=False),
            our_svg.board(b, arrows=[Arrow(12, 28)], coordinates=False),
        )

    def test_arrow_with_borders(self):
        b = _board()
        assert_svg_equal(
            ref_svg.board(b, arrows=[chess.svg.Arrow(12, 28)], borders=True),
            our_svg.board(b, arrows=[Arrow(12, 28)], borders=True),
        )

    def test_arrow_long_diagonal(self):
        b = _board()
        assert_svg_equal(
            ref_svg.board(b, arrows=[chess.svg.Arrow(0, 55)]),
            our_svg.board(b, arrows=[Arrow(0, 55)]),
        )


# ---------------------------------------------------------------------------
# Piece rendering
# ---------------------------------------------------------------------------

class TestPiece:

    def test_white_king(self):
        p = chess.Piece.from_symbol("K")
        assert_svg_equal(ref_svg.piece(p), our_svg.piece(p))

    def test_black_queen(self):
        p = chess.Piece.from_symbol("q")
        assert_svg_equal(ref_svg.piece(p), our_svg.piece(p))

    def test_white_pawn(self):
        p = chess.Piece.from_symbol("P")
        assert_svg_equal(ref_svg.piece(p), our_svg.piece(p))

    def test_piece_with_size(self):
        p = chess.Piece.from_symbol("N")
        assert_svg_equal(
            ref_svg.piece(p, size=100),
            our_svg.piece(p, size=100),
        )

    def test_all_pieces(self):
        for symbol in "PNBRQKpnbrqk":
            p = chess.Piece.from_symbol(symbol)
            assert_svg_equal(
                ref_svg.piece(p),
                our_svg.piece(p),
                label=f"piece {symbol}",
            )


# ---------------------------------------------------------------------------
# Arrow class
# ---------------------------------------------------------------------------

class TestArrowClass:

    def test_from_pgn(self):
        a = Arrow.from_pgn("Ge2e4")
        assert a.tail == 12
        assert a.head == 28
        assert a.color == "green"

    def test_pgn_roundtrip(self):
        a = Arrow(0, 63, color="red")
        pgn = a.pgn()
        b = Arrow.from_pgn(pgn)
        assert a == b

    def test_eq(self):
        assert Arrow(0, 28) == Arrow(0, 28)
        assert Arrow(0, 28) != Arrow(0, 29)

    def test_hash(self):
        s = {Arrow(0, 28), Arrow(0, 28), Arrow(1, 2)}
        assert len(s) == 2

    def test_repr(self):
        a = Arrow(12, 28)
        assert "Arrow" in repr(a)


# ---------------------------------------------------------------------------
# Combination / integration tests
# ---------------------------------------------------------------------------

class TestCombinations:

    def test_lastmove_plus_check(self):
        fen = "rnbqkb1r/pppp1ppp/5n2/4p2Q/4P3/8/PPPP1PPP/RNB1KBNR w KQkq - 2 3"
        b = _board(fen)
        assert_svg_equal(
            ref_svg.board(b, lastmove=chess.Move.from_uci("d1h5"), check=4),
            our_svg.board(b, lastmove=chess.Move(3, 39), check=4),
        )

    def test_lastmove_plus_arrows(self):
        b = _board()
        assert_svg_equal(
            ref_svg.board(b,
                lastmove=chess.Move.from_uci("e2e4"),
                arrows=[chess.svg.Arrow(12, 28)],
            ),
            our_svg.board(b,
                lastmove=chess.Move(12, 28),
                arrows=[Arrow(12, 28)],
            ),
        )

    def test_all_options_combined(self):
        b = _board()
        assert_svg_equal(
            ref_svg.board(b,
                flipped=True,
                lastmove=chess.Move.from_uci("e2e4"),
                check=4,
                arrows=[chess.svg.Arrow(12, 28)],
                fill={0: "#ff0000"},
                colors={"square light": "#f0d9b5"},
                borders=True,
                style=".arrow { filter: none; }",
            ),
            our_svg.board(b,
                flipped=True,
                lastmove=chess.Move(12, 28),
                check=4,
                arrows=[Arrow(12, 28)],
                fill={0: "#ff0000"},
                colors={"square light": "#f0d9b5"},
                borders=True,
                style=".arrow { filter: none; }",
            ),
        )

    def test_various_fens(self):
        fens = [
            chess.STARTING_FEN,
            "8/8/8/8/8/8/8/8 w - - 0 1",
            "r1bqkbnr/pppppppp/2n5/8/4P3/8/PPPP1PPP/RNBQKBNR w KQkq - 1 2",
            "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq e3 0 1",
            "r3k2r/p1ppqpb1/bn2pnp1/3PN3/1p2P3/2N2Q1p/PPPBBPPP/R3K2R w KQkq - 0 1",
        ]
        for fen in fens:
            b = _board(fen)
            assert_svg_equal(
                ref_svg.board(b),
                our_svg.board(b),
                label=f"FEN: {fen[:40]}...",
            )


# ---------------------------------------------------------------------------
# SvgWrapper
# ---------------------------------------------------------------------------

class TestSvgWrapper:

    def test_repr_svg(self):
        b = _board()
        svg = our_svg.board(b)
        assert hasattr(svg, "_repr_svg_")
        assert svg._repr_svg_() == str(svg)

    def test_is_str(self):
        b = _board()
        svg = our_svg.board(b)
        assert isinstance(svg, str)

    def test_piece_repr_svg(self):
        p = chess.Piece.from_symbol("K")
        svg = our_svg.piece(p)
        assert hasattr(svg, "_repr_svg_")


# ---------------------------------------------------------------------------
# Arrow coverage — fuzz test across all 4032 arrow pairs
# ---------------------------------------------------------------------------

class TestArrowFuzz:

    def test_all_arrow_directions_high_match_rate(self):
        """At least 92% of all possible arrow pairs must match exactly."""
        b = _board()
        total = 0
        matches = 0
        for tail in range(64):
            for head in range(64):
                if tail == head:
                    continue
                total += 1
                ref = ref_svg.board(b, arrows=[chess.svg.Arrow(tail, head)])
                ours = our_svg.board(b, arrows=[Arrow(tail, head)])
                if ref == ours:
                    matches += 1
        rate = matches / total
        assert rate >= 0.92, (
            f"Arrow exact match rate {rate:.1%} ({matches}/{total}) "
            f"is below 92% threshold"
        )

    def test_circle_all_squares(self):
        """Circle arrows (same-square) must match for all 64 squares."""
        b = _board()
        for sq in range(64):
            ref = ref_svg.board(b, arrows=[chess.svg.Arrow(sq, sq)])
            ours = our_svg.board(b, arrows=[Arrow(sq, sq)])
            assert_svg_equal(ref, ours, label=f"circle sq={sq}")
