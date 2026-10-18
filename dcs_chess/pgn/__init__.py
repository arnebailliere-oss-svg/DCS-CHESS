"""PGN reading, writing, and game tree model."""

from __future__ import annotations

import dataclasses
import enum
import logging
import re
from typing import List, Optional, TypeVar

from .model import (
    GameNode,
    ChildNode,
    Game,
    Headers,
    Mainline,
    SKIP,
    SkipType,
)

from .visitor import (
    BaseVisitor,
    GameBuilder,
    HeadersBuilder,
    SkipVisitor,
)

from .reader import (
    read_game,
    read_headers,
    skip_game,
)

from .writer import (
    StringExporter,
    FileExporter,
    StringExporterMixin,
    NAG_NULL,
    NAG_GOOD_MOVE,
    NAG_MISTAKE,
    NAG_BRILLIANT_MOVE,
    NAG_BLUNDER,
    NAG_SPECULATIVE_MOVE,
    NAG_DUBIOUS_MOVE,
    NAG_FORCED_MOVE,
    NAG_SINGULAR_MOVE,
    NAG_WORST_MOVE,
    NAG_DRAWISH_POSITION,
    NAG_QUIET_POSITION,
    NAG_ACTIVE_POSITION,
    NAG_UNCLEAR_POSITION,
    NAG_WHITE_SLIGHT_ADVANTAGE,
    NAG_BLACK_SLIGHT_ADVANTAGE,
    NAG_WHITE_MODERATE_ADVANTAGE,
    NAG_BLACK_MODERATE_ADVANTAGE,
    NAG_WHITE_DECISIVE_ADVANTAGE,
    NAG_BLACK_DECISIVE_ADVANTAGE,
    NAG_WHITE_ZUGZWANG,
    NAG_BLACK_ZUGZWANG,
    NAG_WHITE_MODERATE_COUNTERPLAY,
    NAG_BLACK_MODERATE_COUNTERPLAY,
    NAG_WHITE_DECISIVE_COUNTERPLAY,
    NAG_BLACK_DECISIVE_COUNTERPLAY,
    NAG_WHITE_MODERATE_TIME_PRESSURE,
    NAG_BLACK_MODERATE_TIME_PRESSURE,
    NAG_WHITE_SEVERE_TIME_PRESSURE,
    NAG_BLACK_SEVERE_TIME_PRESSURE,
    NAG_NOVELTY,
)

# Type variables (match python-chess public API)
GameT = TypeVar("GameT", bound=Game)
HeadersT = TypeVar("HeadersT", bound=Headers)
ResultT = TypeVar("ResultT")
MainlineMapT = TypeVar("MainlineMapT")

# Logger
LOGGER = logging.getLogger("chess.pgn")

# Seven Tag Roster
TAG_ROSTER = ["Event", "Site", "Date", "Round", "White", "Black", "Result"]

# Regex patterns (public API, matching python-chess)
TAG_REGEX = re.compile(
    r"""^\[([A-Za-z0-9][A-Za-z0-9_+#=:-]*)\s+"([^\r]*)"\]\s*$"""
)

TAG_NAME_REGEX = re.compile(
    r"^[A-Za-z0-9][A-Za-z0-9_+#=:-]*\Z"
)

MOVETEXT_REGEX = re.compile(
    r"""
    (
        [NBKRQ]?[a-h]?[1-8]?[\-x]?[a-h][1-8](?:=?[nbrqkNBRQK])?
        |[PNBRQK]?@[a-h][1-8]
        |O-O-O|O-O|0-0-0|0-0
        |--
    )
    """,
    re.VERBOSE,
)

SKIP_MOVETEXT_REGEX = re.compile(r";|\{|\}")

ARROWS_REGEX = re.compile(
    r"""
    (?P<prefix>\s?)
    \[%(?:csl|cal)\s(?P<arrows>
        [RGYB][a-h][1-8](?:[a-h][1-8])?
        (?:,[RGYB][a-h][1-8](?:[a-h][1-8])?)*
    )\]
    (?P<suffix>\s?)
    """,
    re.VERBOSE,
)

CLOCK_REGEX = re.compile(
    r"(?P<prefix>\s?)\[%clk\s(?P<hours>\d+):(?P<minutes>\d+):"
    r"(?P<seconds>\d+(?:\.\d*)?)\](?P<suffix>\s?)"
)

EMT_REGEX = re.compile(
    r"(?P<prefix>\s?)\[%emt\s(?P<hours>\d+):(?P<minutes>\d+):"
    r"(?P<seconds>\d+(?:\.\d*)?)\](?P<suffix>\s?)"
)

EVAL_REGEX = re.compile(
    r"""
    (?P<prefix>\s?)
    \[%eval\s(?:
        \#(?P<mate>[+-]?\d+)
        |(?P<cp>[+-]?(?:\d{0,10}\.\d{1,2}|\d{1,10}\.?))
    )(?:
        ,(?P<depth>\d+)
    )?\]
    (?P<suffix>\s?)
    """,
    re.VERBOSE,
)


# TimeControl support
class TimeControlType(enum.IntEnum):
    UNKNOWN = 0
    UNLIMITED = 1
    STANDARD = 2
    RAPID = 3
    BLITZ = 4
    BULLET = 5


@dataclasses.dataclass
class TimeControlPart:
    moves: int = 0
    time: int = 0
    increment: float = 0
    delay: float = 0


@dataclasses.dataclass
class TimeControl:
    parts: List[TimeControlPart] = dataclasses.field(default_factory=list)
    type: TimeControlType = TimeControlType.UNKNOWN


def parse_time_control(tc_str: str) -> TimeControl:
    """Parse a PGN TimeControl header value."""
    tc_str = tc_str.strip()

    if tc_str == "-":
        return TimeControl(parts=[], type=TimeControlType.UNLIMITED)
    if tc_str in ("?", ""):
        return TimeControl(parts=[], type=TimeControlType.UNKNOWN)

    parts: List[TimeControlPart] = []
    for segment in tc_str.split(":"):
        part = TimeControlPart()
        main = segment

        if "+" in main:
            main, inc_str = main.split("+", 1)
            try:
                part.increment = float(inc_str)
            except ValueError:
                pass

        if "/" in main:
            moves_str, time_str = main.split("/", 1)
            try:
                part.moves = int(moves_str)
            except ValueError:
                pass
            main = time_str

        try:
            part.time = int(main)
        except ValueError:
            pass

        parts.append(part)

    total_time = sum(p.time for p in parts)
    total_inc = sum(p.increment for p in parts)
    has_moves = any(p.moves > 0 for p in parts)

    if has_moves or total_time >= 3600:
        tc_type = TimeControlType.STANDARD
    elif total_time + total_inc * 40 >= 600:
        tc_type = TimeControlType.RAPID
    elif total_time + total_inc * 40 >= 180:
        tc_type = TimeControlType.BLITZ
    else:
        tc_type = TimeControlType.BULLET

    return TimeControl(parts=parts, type=tc_type)


# BoardBuilder visitor
class BoardBuilder(BaseVisitor):
    """Visitor that returns the final Board position instead of a Game tree."""

    def __init__(self) -> None:
        self._board = None

    def begin_game(self) -> None:
        pass

    def end_headers(self) -> None:
        pass

    def visit_board(self, board: "dcs_chess.core.board.Board") -> None:
        self._board = board

    def result(self) -> "dcs_chess.core.board.Board":
        if self._board is not None:
            return self._board
        from dcs_chess.core.board import Board
        return Board()
