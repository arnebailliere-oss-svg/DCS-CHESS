"""FR-C10: Exception classes for the DCS Chess Toolkit."""

from __future__ import annotations


class IllegalMoveError(ValueError):
    """Raised when an illegal move is attempted on a board."""

    def __init__(self, move: object = None, board: object = None) -> None:
        if move is not None and board is not None:
            msg = f"illegal move {move} in position {board.fen()}"
        elif move is not None:
            msg = f"illegal move {move}"
        else:
            msg = "illegal move"
        super().__init__(msg)
        self.move = move
        self.board = board


class InvalidMoveError(ValueError):
    """Raised when a move string cannot be parsed."""

    def __init__(self, msg: str = "invalid move") -> None:
        super().__init__(msg)


class AmbiguousMoveError(ValueError):
    """Raised when a SAN string matches multiple legal moves."""

    def __init__(self, msg: str = "ambiguous move") -> None:
        super().__init__(msg)
