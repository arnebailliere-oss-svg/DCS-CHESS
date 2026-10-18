"""FR-P5: PGN writer — StringExporter, FileExporter, NAG constants."""

from __future__ import annotations

from typing import Any, Optional, TextIO

from dcs_chess.pgn.model import SKIP, SkipType
from dcs_chess.pgn.visitor import BaseVisitor


# ---------------------------------------------------------------------------
# NAG constants (Numeric Annotation Glyphs — PGN standard)
# ---------------------------------------------------------------------------

NAG_NULL = 0
NAG_GOOD_MOVE = 1
NAG_MISTAKE = 2
NAG_BRILLIANT_MOVE = 3
NAG_BLUNDER = 4
NAG_SPECULATIVE_MOVE = 5
NAG_DUBIOUS_MOVE = 6
NAG_FORCED_MOVE = 7
NAG_SINGULAR_MOVE = 8
NAG_WORST_MOVE = 9
NAG_DRAWISH_POSITION = 10
NAG_QUIET_POSITION = 11
NAG_ACTIVE_POSITION = 12
NAG_UNCLEAR_POSITION = 13
NAG_WHITE_SLIGHT_ADVANTAGE = 14
NAG_BLACK_SLIGHT_ADVANTAGE = 15
NAG_WHITE_MODERATE_ADVANTAGE = 16
NAG_BLACK_MODERATE_ADVANTAGE = 17
NAG_WHITE_DECISIVE_ADVANTAGE = 18
NAG_BLACK_DECISIVE_ADVANTAGE = 19
NAG_WHITE_ZUGZWANG = 22
NAG_BLACK_ZUGZWANG = 23
NAG_WHITE_MODERATE_COUNTERPLAY = 132
NAG_BLACK_MODERATE_COUNTERPLAY = 133
NAG_WHITE_DECISIVE_COUNTERPLAY = 134
NAG_BLACK_DECISIVE_COUNTERPLAY = 135
NAG_WHITE_MODERATE_TIME_PRESSURE = 136
NAG_BLACK_MODERATE_TIME_PRESSURE = 137
NAG_WHITE_SEVERE_TIME_PRESSURE = 138
NAG_BLACK_SEVERE_TIME_PRESSURE = 139
NAG_NOVELTY = 146


# ---------------------------------------------------------------------------
# StringExporterMixin — shared visitor logic for both exporters
# ---------------------------------------------------------------------------

class StringExporterMixin:

    def __init__(
        self,
        *,
        columns: Optional[int] = 80,
        headers: bool = True,
        comments: bool = True,
        variations: bool = True,
    ) -> None:
        self.columns = columns
        self.headers = headers
        self.comments = comments
        self.variations = variations
        self._lines: list[str] = []
        self._current_line = ""
        self._after_variation = False
        self._force_move_number = False

    def write_token(self, token: str) -> None:
        if self.columns is None:
            if self._current_line:
                self._current_line += " " + token
            else:
                self._current_line = token
        else:
            if not self._current_line:
                self._current_line = token
            elif len(self._current_line) + 1 + len(token) >= self.columns:
                self._lines.append(self._current_line)
                self._current_line = token
            else:
                self._current_line += " " + token

    def write_line(self, line: str = "") -> None:
        if self._current_line:
            self._lines.append(self._current_line)
            self._current_line = ""
        self._lines.append(line)

    def flush_current_line(self) -> None:
        if self._current_line:
            self._lines.append(self._current_line)
            self._current_line = ""

    # -- Visitor method implementations --

    def begin_headers(self) -> None:
        return None

    def visit_header(self, tagname: str, tagvalue: str) -> None:
        if self.headers:
            self.write_line(f'[{tagname} "{tagvalue}"]')

    def end_headers(self) -> None:
        if self.headers:
            self.write_line()
        self._force_move_number = True
        return None

    def visit_comment(self, comment: str) -> None:
        if self.comments:
            self.write_token("{ " + comment + " }")
            self._force_move_number = True

    def visit_nag(self, nag: int) -> None:
        if self.comments:
            self.write_token(f"${nag}")

    def visit_move(self, board: Any, move: Any) -> None:
        from dcs_chess.core.constants import WHITE
        if board.turn == WHITE:
            self.write_token(f"{board.fullmove_number}.")
        elif self._after_variation or self._force_move_number:
            self.write_token(f"{board.fullmove_number}...")
        self._after_variation = False
        self._force_move_number = False
        try:
            san = board.san(move)
        except Exception:
            san = str(move)
        self.write_token(san)

    def begin_variation(self) -> Optional[SkipType]:
        if not self.variations:
            return SKIP
        self.write_token("(")
        self._after_variation = False
        self._force_move_number = True
        return None

    def end_variation(self) -> None:
        self.write_token(")")
        self._after_variation = True

    def visit_result(self, result: str) -> None:
        self.write_token(result)

    def end_game(self) -> None:
        self.flush_current_line()


# ---------------------------------------------------------------------------
# StringExporter — accumulates PGN text, result() returns str
# ---------------------------------------------------------------------------

class StringExporter(StringExporterMixin, BaseVisitor):

    def __init__(
        self,
        *,
        columns: Optional[int] = 80,
        headers: bool = True,
        comments: bool = True,
        variations: bool = True,
    ) -> None:
        StringExporterMixin.__init__(
            self,
            columns=columns,
            headers=headers,
            comments=comments,
            variations=variations,
        )
        BaseVisitor.__init__(self)

    def result(self) -> str:
        return "\n".join(self._lines + ([self._current_line] if self._current_line else []))


# ---------------------------------------------------------------------------
# FileExporter — writes PGN to a file handle, result() returns char count
# ---------------------------------------------------------------------------

class FileExporter(StringExporterMixin, BaseVisitor):

    def __init__(
        self,
        handle: TextIO,
        *,
        columns: Optional[int] = 80,
        headers: bool = True,
        comments: bool = True,
        variations: bool = True,
    ) -> None:
        StringExporterMixin.__init__(
            self,
            columns=columns,
            headers=headers,
            comments=comments,
            variations=variations,
        )
        BaseVisitor.__init__(self)
        self._handle = handle
        self._bytes_written = 0

    def write_token(self, token: str) -> None:
        if self.columns is None:
            if self._current_line:
                self._current_line += " " + token
            else:
                self._current_line = token
        else:
            if not self._current_line:
                self._current_line = token
            elif len(self._current_line) + 1 + len(token) >= self.columns:
                text = self._current_line + "\n"
                self._handle.write(text)
                self._bytes_written += len(text)
                self._current_line = token
            else:
                self._current_line += " " + token

    def write_line(self, line: str = "") -> None:
        if self._current_line:
            text = self._current_line + "\n"
            self._handle.write(text)
            self._bytes_written += len(text)
            self._current_line = ""
        text = line + "\n"
        self._handle.write(text)
        self._bytes_written += len(text)

    def flush_current_line(self) -> None:
        if self._current_line:
            text = self._current_line + "\n"
            self._handle.write(text)
            self._bytes_written += len(text)
            self._current_line = ""

    def end_game(self) -> None:
        self.flush_current_line()
        self._handle.write("\n")
        self._bytes_written += 1

    def result(self) -> int:
        return self._bytes_written
