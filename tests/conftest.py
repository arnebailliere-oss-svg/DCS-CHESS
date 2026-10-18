"""Shared fixtures and helpers for DCS Chess Toolkit differential tests.

The reference library (python-chess) is imported here and ONLY here in the
test suite.  Production code never imports it.
"""

from __future__ import annotations

import random
import typing

import chess as _ref
import pytest


@pytest.fixture(scope="session")
def ref():
    """Return the reference python-chess module for differential comparison."""
    return _ref


# ---------------------------------------------------------------------------
# Standard perft positions (AT-1)
# ---------------------------------------------------------------------------

PERFT_POSITIONS: typing.List[typing.Tuple[str, typing.Dict[int, int]]] = [
    (
        "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
        {1: 20, 2: 400, 3: 8902, 4: 197281, 5: 4865609},
    ),
    (
        "r3k2r/p1ppqpb1/bn2pnp1/3PN3/1p2P3/2N2Q1p/PPPBBPPP/R3K2R w KQkq - 0 1",
        {1: 48, 2: 2039, 3: 97862, 4: 4085603},
    ),
    (
        "8/2p5/3p4/KP5r/1R3p1k/8/4P1P1/8 w - - 0 1",
        {1: 14, 2: 191, 3: 2812, 4: 43238, 5: 674624},
    ),
    (
        "r3k2r/Pppp1ppp/1b3nbN/nP6/BBP1P3/q4N2/Pp1P2PP/R2Q1RK1 w kq - 0 1",
        {1: 6, 2: 264, 3: 9467, 4: 422333, 5: 15833292},
    ),
    (
        "rnbq1k1r/pp1Pbppp/2p5/8/2B5/8/PPP1NnPP/RNBQK2R w KQ - 1 8",
        {1: 44, 2: 1486, 3: 62379, 4: 2103487},
    ),
    (
        "r4rk1/1pp1qppp/p1np1n2/2b1p1B1/2B1P1b1/P1NP1N2/1PP1QPPP/R4RK1 w - - 0 10",
        {1: 46, 2: 2079, 3: 89890, 4: 3894594},
    ),
]


def generate_random_positions(
    n: int = 100,
    seed: int = 42,
    max_moves: int = 80,
) -> typing.List[str]:
    """Generate *n* FEN strings by playing random legal moves from the start.

    Uses the reference library to guarantee legality.  The seed is fixed so
    the corpus is reproducible across runs.
    """
    rng = random.Random(seed)
    fens: typing.List[str] = []
    for _ in range(n):
        board = _ref.Board()
        depth = rng.randint(1, max_moves)
        for _ in range(depth):
            moves = list(board.legal_moves)
            if not moves:
                break
            board.push(rng.choice(moves))
        fens.append(board.fen())
    return fens


@pytest.fixture(scope="session")
def random_positions_100() -> typing.List[str]:
    """100 reproducible random positions for quick differential checks."""
    return generate_random_positions(100, seed=42)


@pytest.fixture(scope="session")
def random_positions_1000() -> typing.List[str]:
    """1 000 reproducible random positions for heavier differential runs."""
    return generate_random_positions(1000, seed=123)
