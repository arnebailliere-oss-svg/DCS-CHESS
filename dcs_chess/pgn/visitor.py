"""FR-P4: PGN visitor classes — BaseVisitor, GameBuilder, HeadersBuilder, SkipVisitor."""

from __future__ import annotations

import abc
from typing import Any, Generic, Optional, TypeVar

from dcs_chess.pgn.model import (
    ChildNode,
    Game,
    GameNode,
    Headers,
    SKIP,
    SkipType,
)

ResultT = TypeVar("ResultT")
GameT = TypeVar("GameT", bound=Game)
HeadersT = TypeVar("HeadersT", bound=Headers)


class BaseVisitor(abc.ABC, Generic[ResultT]):

    def begin_game(self) -> Optional[SkipType]:
        pass

    def begin_headers(self) -> Optional[Headers]:
        pass

    def visit_header(self, tagname: str, tagvalue: str) -> None:
        pass

    def end_headers(self) -> Optional[SkipType]:
        pass

    def begin_parse_san(self, board: Any, san: str) -> Optional[SkipType]:
        pass

    def parse_san(self, board: Any, san: str) -> Any:
        return board.parse_san(san)

    def visit_move(self, board: Any, move: Any) -> None:
        pass

    def visit_board(self, board: Any) -> None:
        pass

    def visit_nag(self, nag: int) -> None:
        pass

    def visit_comment(self, comment: str) -> None:
        pass

    def begin_variation(self) -> Optional[SkipType]:
        return SKIP

    def end_variation(self) -> None:
        pass

    def visit_result(self, result: str) -> None:
        pass

    def end_game(self) -> None:
        pass

    @abc.abstractmethod
    def result(self) -> ResultT:
        ...

    def handle_error(self, error: Exception) -> None:
        pass


class GameBuilder(BaseVisitor[GameT], Generic[GameT]):

    @classmethod
    def GameClass(cls) -> type:
        return Game

    def __init__(self) -> None:
        self.game: GameT = None  # type: ignore[assignment]
        self._node_stack: list[GameNode] = []
        self._skip_rest = False

    def begin_game(self) -> None:
        self.game = self.GameClass()()  # type: ignore[assignment]
        self._node_stack = [self.game]

    def begin_headers(self) -> Headers:
        return self.game.headers

    def visit_header(self, tagname: str, tagvalue: str) -> None:
        self.game.headers[tagname] = tagvalue

    def end_headers(self) -> None:
        pass

    def begin_variation(self) -> None:
        parent = self._node_stack[-1].parent
        if parent is not None:
            self._node_stack.append(parent)

    def end_variation(self) -> None:
        if len(self._node_stack) > 1:
            self._node_stack.pop()

    def visit_move(self, board: Any, move: Any) -> None:
        node = self._node_stack[-1].add_variation(move)
        self._node_stack[-1] = node

    def visit_nag(self, nag: int) -> None:
        node = self._node_stack[-1]
        node.nags.add(nag)

    def visit_comment(self, comment: str) -> None:
        node = self._node_stack[-1]
        if node.comment:
            node.comment += " " + comment
        else:
            node.comment = comment

    def visit_result(self, result: str) -> None:
        if self.game.headers.get("Result", "*") == "*":
            self.game.headers["Result"] = result

    def begin_parse_san(self, board: Any, san: str) -> Optional[SkipType]:
        if self._skip_rest:
            return SKIP
        return None

    def handle_error(self, error: Exception) -> None:
        self.game.errors.append(error)
        self._skip_rest = True

    def result(self) -> GameT:
        return self.game


class HeadersBuilder(BaseVisitor[HeadersT], Generic[HeadersT]):

    @classmethod
    def HeadersClass(cls) -> type:
        return Headers

    def __init__(self) -> None:
        self.headers: HeadersT = None  # type: ignore[assignment]

    def begin_headers(self) -> HeadersT:
        self.headers = self.HeadersClass()({})  # type: ignore[assignment]
        return self.headers

    def visit_header(self, tagname: str, tagvalue: str) -> None:
        self.headers[tagname] = tagvalue

    def end_headers(self) -> SkipType:
        return SKIP

    def result(self) -> HeadersT:
        return self.headers


class SkipVisitor(BaseVisitor[bool]):

    def begin_game(self) -> SkipType:
        return SKIP

    def end_headers(self) -> SkipType:
        return SKIP

    def result(self) -> bool:
        return True
