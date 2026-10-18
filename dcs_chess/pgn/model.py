"""FR-P1: PGN game tree model — GameNode, ChildNode, Game, Mainline."""

from __future__ import annotations

import enum
import re
from typing import (
    Any,
    Callable,
    Dict,
    Generic,
    Iterable,
    Iterator,
    List,
    Mapping,
    Optional,
    Set,
    Tuple,
    TypeVar,
    Union,
)

ResultT = TypeVar("ResultT")
MainlineMapT = TypeVar("MainlineMapT")

_EVAL_REGEX = re.compile(
    r"\[%eval\s+(#[+-]?\d+|[+-]?\d+(?:\.\d+)?)(?:,(\d+))?\]"
)
_CLK_REGEX = re.compile(r"\[%clk\s+(\d+):(\d+):(\d+(?:\.\d+)?)\]")
_EMT_REGEX = re.compile(r"\[%emt\s+(\d+):(\d+):(\d+(?:\.\d+)?)\]")
_ARROWS_REGEX = re.compile(r"\[%(?:csl|cal)\s+([^\]]+)\]")


class SkipType(enum.Enum):
    SKIP = enum.auto()


SKIP = SkipType.SKIP


class Mainline(Generic[MainlineMapT]):
    """Iterable over mainline nodes or moves."""

    def __init__(
        self, start: "GameNode", f: Callable[["ChildNode"], MainlineMapT]
    ) -> None:
        self.start = start
        self.f = f

    def __bool__(self) -> bool:
        return bool(self.start.variations)

    def __iter__(self) -> Iterator[MainlineMapT]:
        node = self.start
        while node.variations:
            node = node.variations[0]
            yield self.f(node)

    def accept(self, visitor: Any) -> Any:
        return visitor.result()


class GameNode:
    """A node in the game tree. Either a :class:`Game` (root) or a :class:`ChildNode`."""

    def __init__(self) -> None:
        self.parent: Optional[GameNode] = None
        self.move: Optional[Any] = None  # chess.Move
        self.variations: List[ChildNode] = []
        self.comment: str = ""
        self.starting_comment: str = ""
        self.nags: Set[int] = set()

    def board(self) -> Any:
        """Reconstruct the board at this node by replaying from the root."""
        board = self.game()._board()
        for node in self._path():
            if node.move is not None:
                board.push(node.move)
        return board

    def _board(self) -> Any:
        """Return the start board for this game."""
        from dcs_chess.core.board import Board
        return Board()

    def _path(self) -> List[GameNode]:
        """Return the path from root to this node (excluding root)."""
        path: List[GameNode] = []
        node: Optional[GameNode] = self
        while node is not None and node.parent is not None:
            path.append(node)
            node = node.parent
        path.reverse()
        return path

    def ply(self) -> int:
        board = self.game()._board()
        ply = board.fullmove_number * 2 - (2 if board.turn else 1)
        ply += len(self._path())
        return ply

    def turn(self) -> bool:
        return self.ply() % 2 == 0

    def root(self) -> GameNode:
        node: GameNode = self
        while node.parent is not None:
            node = node.parent
        return node

    def game(self) -> Game:
        root = self.root()
        assert isinstance(root, Game)
        return root

    def end(self) -> GameNode:
        node: GameNode = self
        while node.variations:
            node = node.variations[0]
        return node

    def is_end(self) -> bool:
        return not self.variations

    def starts_variation(self) -> bool:
        if self.parent is None:
            return False
        return (
            bool(self.parent.variations)
            and self.parent.variations[0] is not self
        )

    def is_mainline(self) -> bool:
        node: GameNode = self
        while node.parent is not None:
            if node.parent.variations[0] is not node:
                return False
            node = node.parent
        return True

    def is_main_variation(self) -> bool:
        if self.parent is None:
            return True
        return bool(self.parent.variations) and self.parent.variations[0] is self

    def variation(self, move: Union[int, Any, "GameNode"]) -> ChildNode:
        if isinstance(move, int):
            return self.variations[move]
        if isinstance(move, GameNode):
            for v in self.variations:
                if v is move:
                    return v
            raise ValueError(f"variation not found: {move!r}")
        for v in self.variations:
            if v.move == move:
                return v
        raise ValueError(f"variation not found: {move!r}")

    def has_variation(self, move: Union[int, Any, "GameNode"]) -> bool:
        try:
            self.variation(move)
            return True
        except (ValueError, IndexError):
            return False

    def promote_to_main(self, move: Union[int, Any, "GameNode"]) -> None:
        variation = self.variation(move)
        idx = self.variations.index(variation)
        if idx > 0:
            self.variations.remove(variation)
            self.variations.insert(0, variation)

    def promote(self, move: Union[int, Any, "GameNode"]) -> None:
        variation = self.variation(move)
        idx = self.variations.index(variation)
        if idx > 0:
            self.variations[idx] = self.variations[idx - 1]
            self.variations[idx - 1] = variation

    def demote(self, move: Union[int, Any, "GameNode"]) -> None:
        variation = self.variation(move)
        idx = self.variations.index(variation)
        if idx < len(self.variations) - 1:
            self.variations[idx] = self.variations[idx + 1]
            self.variations[idx + 1] = variation

    def remove_variation(self, move: Union[int, Any, "GameNode"]) -> None:
        if isinstance(move, int):
            del self.variations[move]
            return
        variation = self.variation(move)
        self.variations.remove(variation)

    def add_variation(
        self,
        move: Any,
        *,
        comment: str = "",
        starting_comment: str = "",
        nags: Iterable[int] = (),
    ) -> ChildNode:
        node = ChildNode(self, move, comment=comment,
                         starting_comment=starting_comment, nags=nags)
        self.variations.append(node)
        return node

    def add_main_variation(
        self,
        move: Any,
        *,
        comment: str = "",
        nags: Iterable[int] = (),
    ) -> ChildNode:
        node = ChildNode(self, move, comment=comment, nags=nags)
        self.variations.insert(0, node)
        return node

    def next(self) -> Optional[ChildNode]:
        if self.variations:
            return self.variations[0]
        return None

    def mainline(self) -> Mainline[ChildNode]:
        return Mainline(self, lambda node: node)

    def mainline_moves(self) -> Mainline[Any]:
        return Mainline(self, lambda node: node.move)

    def add_line(
        self,
        moves: Iterable[Any],
        *,
        comment: str = "",
        starting_comment: str = "",
        nags: Iterable[int] = (),
    ) -> GameNode:
        node: GameNode = self
        moves_list = list(moves)
        for i, move in enumerate(moves_list):
            if i == len(moves_list) - 1:
                node = node.add_variation(
                    move,
                    comment=comment,
                    starting_comment=starting_comment,
                    nags=nags,
                )
            else:
                node = node.add_variation(move)
        return node

    # --- Comment annotations ---

    def eval(self) -> Optional[Any]:
        m = _EVAL_REGEX.search(self.comment)
        if m is None:
            return None
        from dcs_chess.engine.scores import Cp, Mate, PovScore
        raw = m.group(1)
        if raw.startswith("#"):
            score = Mate(int(raw[1:]))
        else:
            score = Cp(int(round(float(raw) * 100)))
        turn = self.turn()
        return PovScore(score if turn else -score, turn)

    def eval_depth(self) -> Optional[int]:
        m = _EVAL_REGEX.search(self.comment)
        if m is None or m.group(2) is None:
            return None
        return int(m.group(2))

    def set_eval(
        self, score: Optional[Any], depth: Optional[int] = None
    ) -> None:
        self.comment = _EVAL_REGEX.sub("", self.comment).strip()
        if score is None:
            return
        white = score.white() if hasattr(score, "white") else score
        cp_val = white.score()
        if cp_val is not None:
            val_str = f"{cp_val / 100:.2f}"
        else:
            mate_val = white.mate()
            if mate_val is not None:
                val_str = f"#{mate_val}"
            else:
                return
        if depth is not None:
            tag = f"[%eval {val_str},{depth}]"
        else:
            tag = f"[%eval {val_str}]"
        if self.comment:
            self.comment = tag + " " + self.comment
        else:
            self.comment = tag

    def clock(self) -> Optional[float]:
        m = _CLK_REGEX.search(self.comment)
        if m is None:
            return None
        h, mi, s = int(m.group(1)), int(m.group(2)), float(m.group(3))
        return h * 3600 + mi * 60 + s

    def set_clock(self, seconds: Optional[float]) -> None:
        self.comment = _CLK_REGEX.sub("", self.comment).strip()
        if seconds is None:
            return
        h = int(seconds) // 3600
        m = (int(seconds) % 3600) // 60
        s = int(seconds) % 60
        tag = f"[%clk {h}:{m:02d}:{s:02d}]"
        if self.comment:
            self.comment = self.comment + " " + tag
        else:
            self.comment = tag

    def emt(self) -> Optional[float]:
        m = _EMT_REGEX.search(self.comment)
        if m is None:
            return None
        h, mi, s = int(m.group(1)), int(m.group(2)), float(m.group(3))
        return h * 3600 + mi * 60 + s

    def set_emt(self, seconds: Optional[float]) -> None:
        self.comment = _EMT_REGEX.sub("", self.comment).strip()
        if seconds is None:
            return
        h = int(seconds) // 3600
        m = (int(seconds) % 3600) // 60
        s = int(seconds) % 60
        tag = f"[%emt {h}:{m:02d}:{s:02d}]"
        if self.comment:
            self.comment = self.comment + " " + tag
        else:
            self.comment = tag

    def arrows(self) -> List[Any]:
        result: List[Any] = []
        for m in _ARROWS_REGEX.finditer(self.comment):
            for arrow_str in m.group(1).split(","):
                arrow_str = arrow_str.strip()
                if len(arrow_str) >= 2:
                    result.append(arrow_str)
        return result

    def set_arrows(self, arrows: Iterable[Any]) -> None:
        self.comment = _ARROWS_REGEX.sub("", self.comment).strip()
        arrow_strs = [str(a) for a in arrows]
        if not arrow_strs:
            return
        tag = f"[%cal {','.join(arrow_strs)}]"
        if self.comment:
            self.comment = self.comment + " " + tag
        else:
            self.comment = tag

    def accept(self, visitor: Any) -> Any:
        """Walk the game tree with a visitor."""
        return self._accept(visitor, sideline=False)

    def accept_subgame(self, visitor: Any) -> Any:
        """Walk this node as a subgame with a visitor."""
        return self._accept(visitor, sideline=True)

    def _accept(self, visitor: Any, sideline: bool) -> Any:
        if not sideline:
            skip = visitor.begin_game()
            if skip is SKIP:
                visitor.end_game()
                return visitor.result()

            game = self.game()
            skip = visitor.begin_headers()
            if skip is not SKIP:
                if isinstance(game, Game):
                    for key, value in game.headers.items():
                        visitor.visit_header(key, value)
            skip_body = visitor.end_headers()
            if skip_body is SKIP:
                visitor.end_game()
                return visitor.result()

        board = self.board() if sideline else self.game()._board()

        if self.comment:
            visitor.visit_comment(self.comment)

        self._accept_node(visitor, board)
        if not sideline:
            visitor.visit_result(self.game().headers.get("Result", "*"))
            visitor.end_game()
        return visitor.result()

    def _accept_node(self, visitor: Any, board: Any) -> None:
        if not self.variations:
            return

        node = self.variations[0]

        if node.starting_comment:
            visitor.visit_comment(node.starting_comment)

        skip = visitor.begin_parse_san(board, "")
        if skip is not SKIP:
            try:
                san = board.san(node.move)
            except Exception:
                san = str(node.move)
            visitor.parse_san(board, san)

        visitor.visit_move(board, node.move)
        board.push(node.move)
        visitor.visit_board(board)

        if node.nags:
            for nag in sorted(node.nags):
                visitor.visit_nag(nag)

        if node.comment:
            visitor.visit_comment(node.comment)

        for sideline in self.variations[1:]:
            skip = visitor.begin_variation()
            if skip is SKIP:
                continue
            sideline_board = board.copy()
            sideline_board.pop()
            _accept_variation(sideline, visitor, sideline_board)
            visitor.end_variation()

        if node.variations:
            node._accept_node(visitor, board)


def _accept_variation(node: ChildNode, visitor: Any, board: Any) -> None:
    if node.starting_comment:
        visitor.visit_comment(node.starting_comment)

    skip = visitor.begin_parse_san(board, "")
    if skip is not SKIP:
        try:
            san = board.san(node.move)
        except Exception:
            san = str(node.move)
        visitor.parse_san(board, san)

    visitor.visit_move(board, node.move)
    board.push(node.move)
    visitor.visit_board(board)

    if node.nags:
        for nag in sorted(node.nags):
            visitor.visit_nag(nag)

    if node.comment:
        visitor.visit_comment(node.comment)

    node._accept_node(visitor, board)


class ChildNode(GameNode):
    """A node within a game tree that has a parent and a move."""

    def __init__(
        self,
        parent: GameNode,
        move: Any,
        *,
        comment: str = "",
        starting_comment: str = "",
        nags: Iterable[int] = (),
    ) -> None:
        super().__init__()
        self.parent = parent
        self.move = move
        self.comment = comment
        self.starting_comment = starting_comment
        self.nags = set(nags)

    def san(self) -> str:
        parent_board = self.parent.board()
        return parent_board.san(self.move)

    def uci(self, *, chess960: Optional[bool] = None) -> str:
        if chess960 and self.parent is not None:
            board = self.parent.board()
            return board.uci(self.move, chess960=True)
        return self.move.uci()

    def __repr__(self) -> str:
        try:
            san = self.san()
        except Exception:
            san = str(self.move)
        return f"<ChildNode at {id(self):#x} ({san})>"


class Headers(dict):
    """An ordered mapping of PGN header tags."""

    _SEVEN_TAG_ROSTER = [
        ("Event", "?"),
        ("Site", "?"),
        ("Date", "????.??.??"),
        ("Round", "?"),
        ("White", "?"),
        ("Black", "?"),
        ("Result", "*"),
    ]

    def __init__(
        self,
        data: Optional[Union[Mapping[str, str], Iterable[Tuple[str, str]]]] = None,
        **kwargs: str,
    ) -> None:
        super().__init__()
        if data is None and not kwargs:
            for key, value in self._SEVEN_TAG_ROSTER:
                self[key] = value
        elif data is not None:
            if hasattr(data, "items"):
                for key, value in data.items():
                    self[key] = value
            else:
                for key, value in data:
                    self[key] = value
        for key, value in kwargs.items():
            self[key] = value

    def is_chess960(self) -> bool:
        return self.get("Variant", "").lower() in ("chess960", "fischerandom")

    def is_wild(self) -> bool:
        return self.get("Variant", "").lower() in [
            "wild/0", "wild/1", "wild/2", "wild/3", "wild/4", "wild/5",
            "wild/6", "wild/7", "wild/8", "wild/8a"]

    def variant(self) -> type:
        from dcs_chess.core.board import Board
        return Board

    def board(self) -> Any:
        from dcs_chess.core.board import Board
        fen = self.get("FEN")
        if fen:
            return Board(fen)
        return Board()

    def copy(self) -> Headers:
        new = Headers.__new__(Headers)
        dict.__init__(new)
        for key, value in self.items():
            dict.__setitem__(new, key, value)
        return new

    def __repr__(self) -> str:
        items = ", ".join(f"{k}={v!r}" for k, v in self.items())
        return f"Headers({items})"

    def builder(self) -> Any:
        return _get_headers_builder()()


def _get_headers_builder():
    from dcs_chess.pgn.visitor import HeadersBuilder
    return HeadersBuilder


class Game(GameNode):
    """The root of a PGN game tree."""

    def __init__(
        self,
        headers: Optional[
            Union[Mapping[str, str], Iterable[Tuple[str, str]]]
        ] = None,
    ) -> None:
        super().__init__()
        self.headers = Headers(headers)
        self.errors: List[Exception] = []

    def _board(self) -> Any:
        return self.headers.board()

    def setup(self, board: Union[Any, str]) -> None:
        from dcs_chess.core.board import Board
        if isinstance(board, str):
            board = Board(board)
        fen = board.fen()
        if fen == Board().fen():
            self.headers.pop("SetUp", None)
            self.headers.pop("FEN", None)
        else:
            self.headers["SetUp"] = "1"
            self.headers["FEN"] = fen

    @classmethod
    def from_board(cls, board: Any) -> Game:
        game = cls()
        setup_board = board.root()
        from dcs_chess.core.board import Board
        if setup_board.fen() != Board().fen():
            game.setup(setup_board)
        node: GameNode = game
        for move in board.move_stack:
            node = node.add_variation(move)
        return game

    @classmethod
    def without_tag_roster(cls) -> Game:
        game = cls.__new__(cls)
        GameNode.__init__(game)
        game.headers = Headers.__new__(Headers)
        dict.__init__(game.headers)
        game.errors = []
        return game

    @classmethod
    def builder(cls) -> Any:
        return _get_game_builder()()

    def __repr__(self) -> str:
        white = self.headers.get("White", "?")
        black = self.headers.get("Black", "?")
        date = self.headers.get("Date", "????.??.??")
        site = self.headers.get("Site", "?")
        return (
            f"<Game at {id(self):#x} "
            f"('{white}' vs. '{black}', '{date}' at '{site}')>"
        )

    def __str__(self) -> str:
        from dcs_chess.pgn.writer import StringExporter
        exporter = StringExporter(columns=None)
        self.accept(exporter)
        return exporter.result()


def _get_game_builder():
    from dcs_chess.pgn.visitor import GameBuilder
    return GameBuilder
