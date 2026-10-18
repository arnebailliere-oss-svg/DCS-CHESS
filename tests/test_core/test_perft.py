"""Perft suite for CORE-AT1: 6 standard + 10 Chess960 positions.

These tests will run once Board with full move generation is implemented
(CORE-008).  Until then they are skipped.
"""

from __future__ import annotations

import typing

import pytest

from tests.conftest import PERFT_POSITIONS

try:
    from dcs_chess.core.board import Board
    _BOARD_AVAILABLE = True
except ImportError:
    _BOARD_AVAILABLE = False


def _perft(board, depth: int) -> int:
    """Count leaf nodes at *depth* from *board*."""
    if depth == 0:
        return 1
    count = 0
    for move in board.legal_moves:
        board.push(move)
        count += _perft(board, depth - 1)
        board.pop()
    return count


# ---------------------------------------------------------------------------
# Standard perft (6 positions)
# ---------------------------------------------------------------------------

_STANDARD_CASES: typing.List[typing.Tuple[str, int, int]] = []
for fen, depths in PERFT_POSITIONS:
    for d, expected in depths.items():
        _STANDARD_CASES.append((fen, d, expected))


@pytest.mark.skipif(not _BOARD_AVAILABLE, reason="Board not yet implemented")
class TestStandardPerft:
    @pytest.mark.parametrize("fen,depth,expected", _STANDARD_CASES, ids=[
        f"pos{i // 5}-d{d}" for i, (_, d, _) in enumerate(_STANDARD_CASES)
    ])
    def test_perft(self, fen: str, depth: int, expected: int):
        board = Board(fen)
        result = _perft(board, depth)
        assert result == expected, (
            f"Perft({depth}) for {fen}: got {result}, expected {expected}"
        )


# ---------------------------------------------------------------------------
# Chess960 perft (10 positions — to be populated with published counts)
# ---------------------------------------------------------------------------

CHESS960_PERFT_POSITIONS: typing.List[typing.Tuple[str, typing.Dict[int, int]]] = [
    ("rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w HAha - 0 1",
     {1: 20, 2: 400, 3: 8902, 4: 197281}),
    ("bbqnnrkr/pppppppp/8/8/8/8/PPPPPPPP/BBQNNRKR w HFhf - 0 1",
     {1: 20, 2: 400, 3: 9006, 4: 201143}),
    ("rkqbbnrn/pppppppp/8/8/8/8/PPPPPPPP/RKQBBNRN w GAga - 0 1",
     {1: 19, 2: 361, 3: 7756, 4: 166115}),
    ("rqnbbknr/pppppppp/8/8/8/8/PPPPPPPP/RQNBBKNR w HAha - 0 1",
     {1: 20, 2: 400, 3: 9040, 4: 203673}),
    ("rnknbbrq/pppppppp/8/8/8/8/PPPPPPPP/RNKNBBRQ w GAga - 0 1",
     {1: 20, 2: 400, 3: 8934, 4: 197976}),
    ("nrkrnbbq/pppppppp/8/8/8/8/PPPPPPPP/NRKRNBBQ w DBdb - 0 1",
     {1: 19, 2: 361, 3: 7761, 4: 165206}),
    ("brkqnrbn/pppppppp/8/8/8/8/PPPPPPPP/BRKQNRBN w FCfc - 0 1",
     {1: 19, 2: 361, 3: 7786, 4: 167203}),
    ("rknnqrbb/pppppppp/8/8/8/8/PPPPPPPP/RKNNQRBB w FAfa - 0 1",
     {1: 20, 2: 400, 3: 8986, 4: 200327}),
    ("bnnrkqrb/pppppppp/8/8/8/8/PPPPPPPP/BNNRKQRB w GDgd - 0 1",
     {1: 20, 2: 400, 3: 8878, 4: 196163}),
    ("qrnbknrb/pppppppp/8/8/8/8/PPPPPPPP/QRNBKNRB w GBgb - 0 1",
     {1: 20, 2: 400, 3: 9022, 4: 202495}),
]

_CHESS960_CASES: typing.List[typing.Tuple[str, int, int]] = []
for fen, depths in CHESS960_PERFT_POSITIONS:
    for d, expected in depths.items():
        _CHESS960_CASES.append((fen, d, expected))


@pytest.mark.skipif(not _BOARD_AVAILABLE, reason="Board not yet implemented")
class TestChess960Perft:
    @pytest.mark.parametrize("fen,depth,expected", _CHESS960_CASES, ids=[
        f"c960-{i // 4}-d{d}" for i, (_, d, _) in enumerate(_CHESS960_CASES)
    ])
    def test_perft(self, fen: str, depth: int, expected: int):
        board = Board(fen, chess960=True)
        result = _perft(board, depth)
        assert result == expected, (
            f"Chess960 Perft({depth}) for {fen}: got {result}, expected {expected}"
        )
