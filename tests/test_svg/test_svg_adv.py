"""SVG-001 adversarial test suite — SVG module differential testing.

Tests all rendering paths, constants, Arrow API, and edge cases
against python-chess. Byte-identical comparison where expected.
"""

from __future__ import annotations

import inspect

import chess
import chess.svg
import pytest

from dcs_chess.svg import (
    board as our_board,
    piece as our_piece,
    Arrow as OurArrow,
    SvgWrapper,
    DEFAULT_COLORS,
    PIECES,
    COORDS,
    SQUARE_SIZE,
    XX,
    CHECK_GRADIENT,
)
from dcs_chess.core.board import Board
from dcs_chess.core.piece import Piece
from dcs_chess.core.move import Move


# =====================================================================
# 1. Constants — exact match
# =====================================================================

class TestConstants:
    def test_square_size(self):
        assert SQUARE_SIZE == chess.svg.SQUARE_SIZE

    def test_default_colors(self):
        assert DEFAULT_COLORS == chess.svg.DEFAULT_COLORS

    def test_pieces_dict(self):
        assert set(PIECES.keys()) == set(chess.svg.PIECES.keys())
        for key in PIECES:
            assert PIECES[key] == chess.svg.PIECES[key], f"PIECES[{key!r}] mismatch"

    def test_coords_dict(self):
        assert set(COORDS.keys()) == set(chess.svg.COORDS.keys())
        for key in COORDS:
            assert COORDS[key] == chess.svg.COORDS[key], f"COORDS[{key!r}] mismatch"

    def test_check_gradient(self):
        assert CHECK_GRADIENT == chess.svg.CHECK_GRADIENT

    def test_xx_marker(self):
        assert XX == chess.svg.XX


# =====================================================================
# 2. Piece rendering — all 12 symbols
# =====================================================================

class TestPieceRendering:
    @pytest.mark.parametrize("sym", list("PNBRQKpnbrqk"))
    def test_piece_default(self, sym):
        ref = str(chess.svg.piece(chess.Piece.from_symbol(sym)))
        ours = str(our_piece(Piece.from_symbol(sym)))
        assert ours == ref, f"piece({sym}) mismatch"

    @pytest.mark.parametrize("size", [None, 50, 100, 200])
    def test_piece_sizes(self, size):
        ref = str(chess.svg.piece(chess.Piece.from_symbol("K"), size=size))
        ours = str(our_piece(Piece.from_symbol("K"), size=size))
        assert ours == ref

    def test_svg_wrapper_type(self):
        result = our_piece(Piece.from_symbol("K"))
        assert isinstance(result, SvgWrapper)
        assert hasattr(result, "_repr_svg_")


# =====================================================================
# 3. Board rendering — basic options
# =====================================================================

class TestBoardRendering:
    def test_empty_board(self):
        assert our_board() == chess.svg.board()

    def test_startpos(self):
        assert our_board(Board()) == chess.svg.board(chess.Board())

    def test_flipped(self):
        assert our_board(Board(), flipped=True) == chess.svg.board(chess.Board(), flipped=True)

    def test_no_coordinates(self):
        assert our_board(Board(), coordinates=False) == chess.svg.board(chess.Board(), coordinates=False)

    def test_borders(self):
        assert our_board(Board(), borders=True) == chess.svg.board(chess.Board(), borders=True)

    def test_borders_with_coords(self):
        assert our_board(Board(), borders=True, coordinates=True) == \
               chess.svg.board(chess.Board(), borders=True, coordinates=True)

    def test_borders_no_coords(self):
        assert our_board(Board(), borders=True, coordinates=False) == \
               chess.svg.board(chess.Board(), borders=True, coordinates=False)

    def test_orientation_black(self):
        assert our_board(Board(), orientation=False) == \
               chess.svg.board(chess.Board(), orientation=chess.BLACK)

    def test_size(self):
        assert our_board(Board(), size=400) == chess.svg.board(chess.Board(), size=400)

    def test_style(self):
        s = ".square { opacity: 0.5; }"
        assert our_board(Board(), style=s) == chess.svg.board(chess.Board(), style=s)

    def test_check(self):
        assert our_board(Board(), check=4) == chess.svg.board(chess.Board(), check=chess.E1)

    def test_lastmove(self):
        ref_move = chess.Move.from_uci("e2e4")
        our_move = Move.from_uci("e2e4")
        assert our_board(Board(), lastmove=our_move) == \
               chess.svg.board(chess.Board(), lastmove=ref_move)


# =====================================================================
# 4. Board rendering — FEN positions
# =====================================================================

class TestBoardFEN:
    FENS = [
        "8/8/8/8/8/8/8/KQk5 w - - 0 1",
        "r1bqkbnr/pppppppp/2n5/8/4P3/8/PPPP1PPP/RNBQKBNR w KQkq - 1 2",
        "8/8/8/4k3/8/8/4K3/4R3 w - - 0 1",
        "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq e3 0 1",
        "r3k2r/pppppppp/8/8/8/8/PPPPPPPP/R3K2R w KQkq - 0 1",
        "8/2p5/3p4/KP5r/1R3p1k/8/4P1P1/8 w - - 0 1",
    ]

    @pytest.mark.parametrize("fen", FENS)
    def test_fen_board(self, fen):
        assert our_board(Board(fen)) == chess.svg.board(chess.Board(fen)), \
            f"Board SVG mismatch for {fen}"


# =====================================================================
# 5. Fill overlay — BUG: RGBA parsing
# =====================================================================

class TestFillOverlay:
    def test_fill_solid_color(self):
        """Solid fill (no alpha) should match."""
        ref = chess.svg.board(chess.Board(), fill={chess.E4: "#ff0000"})
        ours = our_board(Board(), fill={28: "#ff0000"})
        assert ours == ref

    def test_fill_rgba_hex(self):
        """BUG: 8-char RGBA hex should be split into fill + opacity."""
        ref = chess.svg.board(chess.Board(), fill={chess.E4: "#ff000080"})
        ours = our_board(Board(), fill={28: "#ff000080"})
        assert ours == ref, "Fill with RGBA hex not parsed into color + opacity"

    def test_fill_multiple_squares(self):
        ref_fill = {chess.E4: "#ff0000", chess.D5: "#0000ff"}
        our_fill = {28: "#ff0000", 35: "#0000ff"}
        ref = chess.svg.board(chess.Board(), fill=ref_fill)
        ours = our_board(Board(), fill=our_fill)
        assert ours == ref


# =====================================================================
# 6. Arrows
# =====================================================================

class TestArrows:
    def test_straight_arrow(self):
        ref = chess.svg.board(chess.Board(), arrows=[chess.svg.Arrow(chess.E2, chess.E4)])
        ours = our_board(Board(), arrows=[OurArrow(12, 28)])
        assert ours == ref

    def test_diagonal_arrow(self):
        ref = chess.svg.board(chess.Board(), arrows=[chess.svg.Arrow(chess.E2, chess.G4)])
        ours = our_board(Board(), arrows=[OurArrow(12, 30)])
        assert ours == ref

    def test_long_diagonal_arrow(self):
        ref = chess.svg.board(chess.Board(), arrows=[chess.svg.Arrow(chess.A1, chess.H8)])
        ours = our_board(Board(), arrows=[OurArrow(0, 63)])
        assert ours == ref

    def test_circle_arrow(self):
        ref = chess.svg.board(chess.Board(), arrows=[chess.svg.Arrow(chess.E4, chess.E4)])
        ours = our_board(Board(), arrows=[OurArrow(28, 28)])
        assert ours == ref

    def test_tuple_arrow(self):
        ref = chess.svg.board(chess.Board(), arrows=[(chess.E2, chess.E4)])
        ours = our_board(Board(), arrows=[(12, 28)])
        assert ours == ref

    def test_colored_arrows(self):
        colors = ["green", "red", "yellow", "blue"]
        for color in colors:
            ref = chess.svg.board(chess.Board(),
                                  arrows=[chess.svg.Arrow(chess.E2, chess.E4, color=color)])
            ours = our_board(Board(), arrows=[OurArrow(12, 28, color=color)])
            assert ours == ref, f"Arrow color={color} mismatch"

    def test_multiple_arrows(self):
        ref = chess.svg.board(chess.Board(), arrows=[
            chess.svg.Arrow(chess.E2, chess.E4),
            chess.svg.Arrow(chess.D7, chess.D5, color="red"),
        ])
        ours = our_board(Board(), arrows=[
            OurArrow(12, 28),
            OurArrow(51, 35, color="red"),
        ])
        assert ours == ref


# =====================================================================
# 7. Arrow class API
# =====================================================================

class TestArrowAPI:
    def test_init_signature(self):
        ref_sig = inspect.signature(chess.svg.Arrow.__init__)
        our_sig = inspect.signature(OurArrow.__init__)
        assert list(our_sig.parameters.keys()) == list(ref_sig.parameters.keys())

    def test_from_pgn_arrow(self):
        ref = chess.svg.Arrow.from_pgn("Ge2e4")
        ours = OurArrow.from_pgn("Ge2e4")
        assert ours.tail == ref.tail
        assert ours.head == ref.head
        assert ours.color == ref.color

    def test_from_pgn_circle(self):
        ref = chess.svg.Arrow.from_pgn("Re4")
        ours = OurArrow.from_pgn("Re4")
        assert ours.tail == ref.tail
        assert ours.head == ref.head
        assert ours.color == ref.color

    def test_from_pgn_no_color_prefix(self):
        ref = chess.svg.Arrow.from_pgn("e2e4")
        ours = OurArrow.from_pgn("e2e4")
        assert ours.tail == ref.tail
        assert ours.head == ref.head
        assert ours.color == ref.color

    def test_pgn_roundtrip(self):
        for pgn in ["Ge2e4", "Re4", "Yb1f5", "Ba1h8"]:
            ref = chess.svg.Arrow.from_pgn(pgn).pgn()
            ours = OurArrow.from_pgn(pgn).pgn()
            assert ours == ref, f"pgn roundtrip {pgn}"

    def test_equality(self):
        a1 = OurArrow(12, 28, color="green")
        a2 = OurArrow(12, 28, color="green")
        a3 = OurArrow(12, 28, color="red")
        assert a1 == a2
        assert a1 != a3

    def test_hash(self):
        a1 = OurArrow(12, 28, color="green")
        a2 = OurArrow(12, 28, color="green")
        assert hash(a1) == hash(a2)
        s = {a1, a2}
        assert len(s) == 1


# =====================================================================
# 8. Squares (XX markers)
# =====================================================================

class TestSquaresMarker:
    def test_squares_bitboard(self):
        bb = 0x0000001818000000  # center 4 squares
        ref = chess.svg.board(chess.Board(), squares=bb)
        ours = our_board(Board(), squares=bb)
        assert ours == ref

    def test_squares_iterable(self):
        sqs = [0, 7, 56, 63]
        ref = chess.svg.board(chess.Board(), squares=chess.SquareSet(sqs))
        ours = our_board(Board(), squares=sqs)
        assert ours == ref


# =====================================================================
# 9. board() signature parity
# =====================================================================

class TestSignatures:
    def test_board_signature(self):
        ref_params = list(inspect.signature(chess.svg.board).parameters.keys())
        our_params = list(inspect.signature(our_board).parameters.keys())
        assert our_params == ref_params

    def test_piece_signature(self):
        ref_params = list(inspect.signature(chess.svg.piece).parameters.keys())
        our_params = list(inspect.signature(our_piece).parameters.keys())
        assert our_params == ref_params


# =====================================================================
# 10. SvgWrapper
# =====================================================================

class TestSvgWrapper:
    def test_is_str(self):
        assert issubclass(SvgWrapper, str)

    def test_repr_svg(self):
        w = SvgWrapper("<svg></svg>")
        assert w._repr_svg_() == "<svg></svg>"


# =====================================================================
# 11. Combined options (stress test)
# =====================================================================

class TestCombinedOptions:
    def test_all_options_together(self):
        ref_move = chess.Move.from_uci("e2e4")
        our_move = Move.from_uci("e2e4")
        ref = chess.svg.board(
            chess.Board(),
            orientation=chess.BLACK,
            lastmove=ref_move,
            check=chess.E1,
            arrows=[chess.svg.Arrow(chess.D7, chess.D5)],
            squares=chess.SquareSet([0, 63]),
            size=500,
            coordinates=True,
            flipped=False,
            borders=True,
            style=".test {}",
        )
        ours = our_board(
            Board(),
            orientation=False,
            lastmove=our_move,
            check=4,
            arrows=[OurArrow(51, 35)],
            squares=[0, 63],
            size=500,
            coordinates=True,
            flipped=False,
            borders=True,
            style=".test {}",
        )
        assert ours == ref

    def test_empty_board_no_options(self):
        assert our_board() == chess.svg.board()

    def test_none_board_with_coords(self):
        assert our_board(None, coordinates=True) == chess.svg.board(None, coordinates=True)
