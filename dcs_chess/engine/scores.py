"""FR-E6: Score, PovScore, Wdl, and WDL model classes.

Implements the full score hierarchy and win-draw-loss conversion models
(Stockfish sf12..sf16.1 and Lichess) from their published formulas.
"""

from __future__ import annotations

import abc
import math
from typing import Optional


# ---------------------------------------------------------------------------
# Wdl / PovWdl
# ---------------------------------------------------------------------------

class Wdl:
    """Win-draw-loss statistics out of 1000."""

    __slots__ = ("wins", "draws", "losses")

    def __init__(self, wins: int, draws: int, losses: int) -> None:
        self.wins = wins
        self.draws = draws
        self.losses = losses

    def total(self) -> int:
        return self.wins + self.draws + self.losses

    def winning_chance(self) -> float:
        return self.wins / self.total()

    def drawing_chance(self) -> float:
        return self.draws / self.total()

    def losing_chance(self) -> float:
        return self.losses / self.total()

    def expectation(self) -> float:
        t = self.total()
        return (self.wins + self.draws / 2) / t

    def __neg__(self) -> Wdl:
        return Wdl(self.losses, self.draws, self.wins)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Wdl):
            return NotImplemented
        return (
            self.wins == other.wins
            and self.draws == other.draws
            and self.losses == other.losses
        )

    def __iter__(self):
        yield self.wins
        yield self.draws
        yield self.losses

    def __repr__(self) -> str:
        return f"Wdl(wins={self.wins}, draws={self.draws}, losses={self.losses})"


class PovWdl:
    """A Wdl from the point of view of one side."""

    __slots__ = ("relative", "turn")

    def __init__(self, relative: Wdl, turn: bool) -> None:
        self.relative = relative
        self.turn = turn

    def white(self) -> Wdl:
        return self.relative if self.turn else -self.relative

    def black(self) -> Wdl:
        return self.relative if not self.turn else -self.relative

    def pov(self, color: bool) -> Wdl:
        return self.relative if color == self.turn else -self.relative

    def __iter__(self):
        return iter(self.relative)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, PovWdl):
            return NotImplemented
        return self.white() == other.white()

    def __repr__(self) -> str:
        color = "WHITE" if self.turn else "BLACK"
        return f"PovWdl({self.relative!r}, {color})"


# ---------------------------------------------------------------------------
# WDL conversion models (published Stockfish and Lichess formulas)
# ---------------------------------------------------------------------------

def _sf_wins(cp: float, a: float, b: float) -> int:
    """Single-sided win rate from the Stockfish WDL sigmoid."""
    return int(0.5 + 1000 / (1 + math.exp((a - cp) / b)))


def _sf12_wins(cp: int, *, ply: int) -> int:
    m = min(240, max(ply, 0)) / 64
    a = (((-8.24404295 * m + 64.23892342) * m + -95.73056462) * m) + 153.86478679
    b = (((-3.37154371 * m + 28.44489198) * m + -56.67657741) * m) + 72.05858751
    x = min(1000, max(cp, -1000))
    return int(0.5 + 1000 / (1 + math.exp((a - x) / b)))


def _sf14_wins(cp: int, *, ply: int) -> int:
    m = min(240, max(ply, 0)) / 64
    a = (((-3.68389304 * m + 30.07065921) * m + -60.52878723) * m) + 149.53378557
    b = (((-2.01818570 * m + 15.85685038) * m + -29.83452023) * m) + 47.59078827
    x = min(2000, max(cp, -2000))
    return int(0.5 + 1000 / (1 + math.exp((a - x) / b)))


def _sf15_wins(cp: int, *, ply: int) -> int:
    m = min(240, max(ply, 0)) / 64
    a = (((-1.17202460e-1 * m + 5.94729104e-1) * m + 1.12065546e+1) * m) + 1.22606222e+2
    b = (((-1.79066759 * m + 11.30759193) * m + -17.43677612) * m) + 36.47147479
    x = min(2000, max(cp, -2000))
    return int(0.5 + 1000 / (1 + math.exp((a - x) / b)))


def _sf15_1_wins(cp: int, *, ply: int) -> int:
    NormalizeToPawnValue = 361
    m = min(240, max(ply, 0)) / 64
    a = (((-0.58270499 * m + 2.68512549) * m + 15.24638015) * m) + 344.49745382
    b = (((-2.65734562 * m + 15.96509799) * m + -20.69040836) * m) + 73.61029937
    x = min(4000, max(cp * NormalizeToPawnValue / 100, -4000))
    return int(0.5 + 1000 / (1 + math.exp((a - x) / b)))


def _sf16_wins(cp: int, *, ply: int) -> int:
    NormalizeToPawnValue = 328
    m = min(240, max(ply, 0)) / 64
    a = (((0.38036525 * m + -2.82015070) * m + 23.17882135) * m) + 307.36768407
    b = (((-2.29434733 * m + 13.27689788) * m + -14.26828904) * m) + 63.45318330
    x = min(4000, max(cp * NormalizeToPawnValue / 100, -4000))
    return int(0.5 + 1000 / (1 + math.exp((a - x) / b)))


def _sf16_1_wins(cp: int, *, ply: int) -> int:
    NormalizeToPawnValue = 356
    m = min(120, max(8, ply / 2 + 1)) / 32
    a = (((-1.06249702 * m + 7.42016937) * m + 0.89425629) * m) + 348.60356174
    b = (((-5.33122190 * m + 39.57831533) * m + -90.84473771) * m) + 123.40620748
    x = min(4000, max(cp * NormalizeToPawnValue / 100, -4000))
    return int(0.5 + 1000 / (1 + math.exp((a - x) / b)))


_SF_WIN_FUNCS = {
    "sf12": _sf12_wins,
    "sf14": _sf14_wins,
    "sf15": _sf15_wins,
    "sf15.1": _sf15_1_wins,
    "sf16": _sf16_wins,
    "sf16.1": _sf16_1_wins,
    "sf": _sf16_1_wins,
}


def _lichess_raw_wins(cp: int) -> int:
    return round(1000 / (1 + math.exp(-0.00368208 * cp)))


def compute_wdl(cp: int, *, model: str = "sf", ply: int = 30) -> Wdl:
    """Convert a centipawn score to Wdl using the named model."""
    if model == "lichess":
        wins = _lichess_raw_wins(max(-1000, min(cp, 1000)))
        losses = 1000 - wins
        return Wdl(wins, 0, losses)

    win_func = _SF_WIN_FUNCS.get(model)
    if win_func is None:
        raise ValueError(f"Unknown WDL model: {model!r}")

    wins = win_func(cp, ply=ply)
    losses = win_func(-cp, ply=ply)
    draws = 1000 - wins - losses
    return Wdl(wins, draws, losses)


# ---------------------------------------------------------------------------
# Score hierarchy
# ---------------------------------------------------------------------------

class Score(abc.ABC):
    """Abstract base for engine evaluation scores."""

    @abc.abstractmethod
    def score(self, *, mate_score: Optional[int] = None) -> Optional[int]:
        """Return the centipawn value, or None if this is a mate score.

        With *mate_score*, a Mate(n) returns mate_score - abs(n) (positive
        for the winning side).
        """

    @abc.abstractmethod
    def mate(self) -> Optional[int]:
        """Return the number of moves to mate, or None for centipawn scores.

        Positive = the side to move mates; negative = the side to move is mated.
        """

    def is_mate(self) -> bool:
        return self.mate() is not None

    def wdl(self, *, model: str = "sf", ply: int = 30) -> Wdl:
        m = self.mate()
        if m is not None:
            if m > 0:
                return Wdl(1000, 0, 0)
            elif m < 0:
                return Wdl(0, 0, 1000)
            else:
                return Wdl(1000, 0, 0)
        cp = self.score()
        if cp is None:
            raise ValueError("Score has neither cp nor mate value")
        return compute_wdl(cp, model=model, ply=ply)

    @abc.abstractmethod
    def __neg__(self) -> Score: ...

    @abc.abstractmethod
    def __eq__(self, other: object) -> bool: ...

    @abc.abstractmethod
    def __lt__(self, other: object) -> bool: ...

    def __le__(self, other: object) -> bool:
        if not isinstance(other, Score):
            return NotImplemented
        return self == other or self < other

    def __gt__(self, other: object) -> bool:
        if not isinstance(other, Score):
            return NotImplemented
        return other < self

    def __ge__(self, other: object) -> bool:
        if not isinstance(other, Score):
            return NotImplemented
        return other == self or other < self

    @abc.abstractmethod
    def __repr__(self) -> str: ...

    @abc.abstractmethod
    def __str__(self) -> str: ...


def _score_key(s: Score) -> tuple[bool, int]:
    """Sort key: (is_winning_mate_or_cp, value).

    Ordering: Mate(-1) < Mate(-N) < Cp(-inf) < ... < Cp(inf) < Mate(N) < Mate(1)
    """
    m = s.mate()
    if m is not None:
        if m > 0:
            return (True, 1_000_000 - m)
        elif m < 0:
            return (False, -1_000_000 - m)
        else:
            return (True, 1_000_000)
    cp = s.score()
    if cp is not None:
        return (False, cp) if cp < 0 else (True, cp) if cp > 0 else (False, 0)
    raise ValueError("Score has neither cp nor mate value")


class Cp(Score):
    """A centipawn score."""

    __slots__ = ("cp",)

    def __init__(self, cp: int) -> None:
        self.cp = cp

    def score(self, *, mate_score: Optional[int] = None) -> Optional[int]:
        return self.cp

    def mate(self) -> Optional[int]:
        return None

    def __neg__(self) -> Cp:
        return Cp(-self.cp)

    def __eq__(self, other: object) -> bool:
        if isinstance(other, Cp):
            return self.cp == other.cp
        if isinstance(other, Score):
            return False
        return NotImplemented

    def __lt__(self, other: object) -> bool:
        if not isinstance(other, Score):
            return NotImplemented
        return _score_key(self) < _score_key(other)

    def __repr__(self) -> str:
        return f"Cp({'+' if self.cp > 0 else ''}{self.cp})"

    def __str__(self) -> str:
        return f"{'+' if self.cp > 0 else ''}{self.cp}"


class Mate(Score):
    """A mate-in-N score."""

    __slots__ = ("moves",)

    def __init__(self, moves: int) -> None:
        self.moves = moves

    def score(self, *, mate_score: Optional[int] = None) -> Optional[int]:
        if mate_score is None:
            return None
        if self.moves > 0:
            return mate_score - self.moves
        else:
            return -mate_score - self.moves

    def mate(self) -> Optional[int]:
        return self.moves

    def __neg__(self) -> Mate:
        return Mate(-self.moves)

    def __eq__(self, other: object) -> bool:
        if isinstance(other, Mate):
            return self.moves == other.moves
        if isinstance(other, Score):
            return False
        return NotImplemented

    def __lt__(self, other: object) -> bool:
        if not isinstance(other, Score):
            return NotImplemented
        return _score_key(self) < _score_key(other)

    def __repr__(self) -> str:
        if self.moves > 0:
            return f"Mate(+{self.moves})"
        elif self.moves == 0:
            return "Mate(-0)"
        else:
            return f"Mate({self.moves})"

    def __str__(self) -> str:
        if self.moves > 0:
            return f"#+{self.moves}"
        elif self.moves == 0:
            return "#-0"
        else:
            return f"#{self.moves}"


class _MateGivenType(Score):
    """Singleton: mate has been delivered (mate in 0 from the winning side)."""

    _instance: Optional[_MateGivenType] = None

    def __new__(cls) -> _MateGivenType:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def score(self, *, mate_score: Optional[int] = None) -> Optional[int]:
        if mate_score is None:
            return None
        return mate_score

    def mate(self) -> Optional[int]:
        return 0

    def __neg__(self) -> Mate:
        return Mate(0)

    def __eq__(self, other: object) -> bool:
        if isinstance(other, _MateGivenType):
            return True
        if isinstance(other, Score):
            return False
        return NotImplemented

    def __lt__(self, other: object) -> bool:
        if not isinstance(other, Score):
            return NotImplemented
        return _score_key(self) < _score_key(other)

    def __repr__(self) -> str:
        return "MateGiven"

    def __str__(self) -> str:
        return "#+0"


MateGiven: Score = _MateGivenType()


# ---------------------------------------------------------------------------
# PovScore
# ---------------------------------------------------------------------------

class PovScore:
    """A score from the point of view of one side."""

    __slots__ = ("relative", "turn")

    def __init__(self, relative: Score, turn: bool) -> None:
        self.relative = relative
        self.turn = turn

    def white(self) -> Score:
        return self.relative if self.turn else -self.relative

    def black(self) -> Score:
        return self.relative if not self.turn else -self.relative

    def pov(self, color: bool) -> Score:
        return self.relative if color == self.turn else -self.relative

    def is_mate(self) -> bool:
        return self.relative.is_mate()

    def wdl(self, *, model: str = "sf", ply: int = 30) -> PovWdl:
        return PovWdl(self.relative.wdl(model=model, ply=ply), self.turn)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, PovScore):
            return NotImplemented
        return self.white() == other.white()

    def __repr__(self) -> str:
        color = "WHITE" if self.turn else "BLACK"
        return f"PovScore({self.relative!r}, {color})"

    def __str__(self) -> str:
        return repr(self)
