"""FR-P3: PGN reader — read_game, read_headers, skip_game."""

from __future__ import annotations

import re
from typing import Any, Optional, TextIO

from dcs_chess.pgn.model import SKIP, SkipType
from dcs_chess.pgn.visitor import BaseVisitor, GameBuilder, HeadersBuilder, SkipVisitor

_TAG_REGEX = re.compile(
    r"\[(\w+)\s+\"([^\"]*)\"\]"
)

_MOVETEXT_TOKEN = re.compile(
    r"""
    (\{[^}]*\})           |  # comment
    (\$\d+)               |  # NAG
    (\()                  |  # begin variation
    (\))                  |  # end variation
    (;[^\n]*)             |  # line comment
    (\d+\.+\s*)           |  # move number (consumed and ignored)
    ([KQRBNP]?[a-h]?[1-8]?x?[a-h][1-8](?:=[QRBN])?[+#]?  # SAN move
     |O-O-O[+#]?
     |O-O[+#]?
     |0-0-0[+#]?
     |0-0[+#]?
     |--
    )                     |
    (1-0|0-1|1/2-1/2|\*) |  # result
    (\S+)                    # unknown token (skip)
    """,
    re.VERBOSE,
)


def read_game(
    handle: TextIO,
    *,
    Visitor: Any = GameBuilder,
) -> Any:
    visitor = Visitor()

    managed_headers = None
    found_game = False
    in_headers = False
    board_stack: list[Any] = []
    skip_variation_depth = 0
    first_movetext_line: Optional[str] = None

    # Phase 1: Find and parse headers
    while True:
        line = handle.readline()
        if not line:
            if not found_game:
                return None
            break

        stripped = line.strip()
        if not stripped:
            if in_headers:
                break
            continue

        tag_match = _TAG_REGEX.match(stripped)
        if tag_match:
            if not found_game:
                found_game = True
                skip_game_result = visitor.begin_game()
                if skip_game_result is SKIP:
                    _skip_movetext(handle)
                    visitor.end_game()
                    return visitor.result()
                managed_headers = visitor.begin_headers()
                in_headers = True
            visitor.visit_header(tag_match.group(1), tag_match.group(2))
        else:
            if not found_game:
                found_game = True
                skip_game_result = visitor.begin_game()
                if skip_game_result is SKIP:
                    _skip_movetext(handle)
                    visitor.end_game()
                    return visitor.result()
                managed_headers = visitor.begin_headers()
                in_headers = True
            first_movetext_line = stripped
            break

    if not found_game:
        return None

    if not in_headers:
        skip_game_result = visitor.begin_game()
        if skip_game_result is SKIP:
            _skip_movetext(handle)
            visitor.end_game()
            return visitor.result()
        managed_headers = visitor.begin_headers()

    skip_headers = visitor.end_headers()

    # Build the starting board
    from dcs_chess.core.board import Board

    if managed_headers is not None:
        fen = managed_headers.get("FEN") if hasattr(managed_headers, "get") else None
        if fen:
            board = Board(fen)
        else:
            board = Board()
        is_chess960 = (
            managed_headers.get("Variant", "").lower()
            in ("chess960", "fischerandom")
            if hasattr(managed_headers, "get")
            else False
        )
        if is_chess960:
            board.chess960 = True
    else:
        board = Board()

    board_stack = [board.copy()]
    visitor.visit_board(board_stack[-1])

    if skip_headers is SKIP:
        _skip_movetext(handle)
        visitor.end_game()
        return visitor.result()

    # Phase 2: Parse movetext
    movetext_lines: list[str] = []
    if first_movetext_line:
        movetext_lines.append(first_movetext_line)
    while True:
        line = handle.readline()
        if not line:
            break
        stripped = line.strip()
        if not stripped:
            continue
        if _TAG_REGEX.match(stripped):
            handle.seek(handle.tell() - len(line))
            break
        movetext_lines.append(stripped)

    movetext = "\n".join(movetext_lines)
    _parse_movetext(movetext, visitor, board_stack)

    visitor.end_game()
    return visitor.result()


def _parse_movetext(
    movetext: str,
    visitor: BaseVisitor,
    board_stack: list[Any],
) -> None:
    skip_variation_depth = 0

    for m in _MOVETEXT_TOKEN.finditer(movetext):
        comment = m.group(1)
        nag = m.group(2)
        open_paren = m.group(3)
        close_paren = m.group(4)
        line_comment = m.group(5)
        move_number = m.group(6)
        san = m.group(7)
        result = m.group(8)
        unknown = m.group(9)

        if skip_variation_depth > 0:
            if open_paren:
                skip_variation_depth += 1
            elif close_paren:
                skip_variation_depth -= 1
                if skip_variation_depth == 0:
                    visitor.end_variation()
                    if board_stack:
                        board_stack.pop()
            continue

        if comment:
            text = comment[1:-1].strip()
            if text:
                visitor.visit_comment(text)
        elif nag:
            visitor.visit_nag(int(nag[1:]))
        elif open_paren:
            if board_stack:
                parent_board = board_stack[-1].copy()
                if parent_board.move_stack:
                    parent_board.pop()
                skip = visitor.begin_variation()
                if skip is SKIP:
                    skip_variation_depth = 1
                else:
                    board_stack.append(parent_board)
        elif close_paren:
            visitor.end_variation()
            if len(board_stack) > 1:
                board_stack.pop()
        elif line_comment:
            pass
        elif move_number:
            pass
        elif san:
            if not board_stack:
                continue
            board = board_stack[-1]
            skip = visitor.begin_parse_san(board, san)
            if skip is SKIP:
                continue
            try:
                move = visitor.parse_san(board, san)
            except Exception as e:
                visitor.handle_error(e)
                continue
            visitor.visit_move(board, move)
            board.push(move)
            visitor.visit_board(board)
        elif result:
            visitor.visit_result(result)


def read_headers(handle: TextIO) -> Any:
    game = read_game(handle, Visitor=HeadersBuilder)
    return game


def skip_game(handle: TextIO) -> bool:
    result = read_game(handle, Visitor=SkipVisitor)
    return result is not None and result is not False


def _skip_movetext(handle: TextIO) -> None:
    in_headers = True
    found_blank = False
    while True:
        line = handle.readline()
        if not line:
            break
        stripped = line.strip()

        if not stripped:
            if in_headers:
                in_headers = False
                found_blank = True
            continue

        if in_headers:
            if _TAG_REGEX.match(stripped):
                continue
            else:
                in_headers = False

        if not in_headers:
            if _TAG_REGEX.match(stripped) and found_blank:
                handle.seek(handle.tell() - len(line))
                break
            result_tokens = ("1-0", "0-1", "1/2-1/2", "*")
            if any(stripped.endswith(r) for r in result_tokens):
                break
