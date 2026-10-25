"""BaseBoard class (FR-C6) — piece placement without game state."""

from __future__ import annotations

import copy
import typing

from .constants import (
    WHITE, BLACK, COLORS,
    PAWN, KNIGHT, BISHOP, ROOK, QUEEN, KING,
    PIECE_TYPES, PIECE_SYMBOLS,
    BB_EMPTY, BB_ALL, BB_SQUARES,
    BB_FILES, BB_RANKS,
    BB_FILE_A, BB_FILE_B, BB_FILE_C, BB_FILE_D,
    BB_FILE_E, BB_FILE_F, BB_FILE_G, BB_FILE_H,
    BB_RANK_1, BB_RANK_2, BB_RANK_7, BB_RANK_8,
    BB_LIGHT_SQUARES, BB_DARK_SQUARES,
    BB_BACKRANKS,
    BB_KNIGHT_ATTACKS, BB_KING_ATTACKS, BB_PAWN_ATTACKS,
    BB_DIAG_MASKS, BB_DIAG_ATTACKS,
    BB_FILE_MASKS, BB_FILE_ATTACKS,
    BB_RANK_MASKS, BB_RANK_ATTACKS,
    BB_RAYS,
    STARTING_BOARD_FEN,
    SQUARE_NAMES, FILE_NAMES, RANK_NAMES,
)
from .piece import Piece
from .squareset import SquareSet
from .functions import (
    square_file, square_rank, square_name, scan_forward, scan_reversed,
    lsb, msb, popcount,
    flip_vertical, flip_horizontal, flip_diagonal, flip_anti_diagonal,
    between,
)


class BaseBoard:
    """Piece placement on a chessboard, without game state.

    The board tracks which squares hold which pieces via per-type and
    per-colour bitboard masks.
    """

    def __init__(self, board_fen: typing.Optional[str] = STARTING_BOARD_FEN) -> None:
        self.pawns: int = BB_EMPTY
        self.knights: int = BB_EMPTY
        self.bishops: int = BB_EMPTY
        self.rooks: int = BB_EMPTY
        self.queens: int = BB_EMPTY
        self.kings: int = BB_EMPTY

        self.occupied_co: typing.List[int] = [BB_EMPTY, BB_EMPTY]
        self.occupied: int = BB_EMPTY
        self.promoted: int = BB_EMPTY

        if board_fen is None:
            self.clear_board()
        elif board_fen == STARTING_BOARD_FEN:
            self.reset_board()
        else:
            self.set_board_fen(board_fen)

    def reset_board(self) -> None:
        """Set up the standard starting position."""
        self.pawns = BB_RANK_2 | BB_RANK_7
        self.knights = BB_SQUARES[1] | BB_SQUARES[6] | BB_SQUARES[57] | BB_SQUARES[62]
        self.bishops = BB_SQUARES[2] | BB_SQUARES[5] | BB_SQUARES[58] | BB_SQUARES[61]
        self.rooks = BB_SQUARES[0] | BB_SQUARES[7] | BB_SQUARES[56] | BB_SQUARES[63]
        self.queens = BB_SQUARES[3] | BB_SQUARES[59]
        self.kings = BB_SQUARES[4] | BB_SQUARES[60]

        self.occupied_co[WHITE] = BB_RANK_1 | BB_RANK_2
        self.occupied_co[BLACK] = BB_RANK_7 | BB_RANK_8
        self.occupied = BB_RANK_1 | BB_RANK_2 | BB_RANK_7 | BB_RANK_8
        self.promoted = BB_EMPTY

    def clear_board(self) -> None:
        """Remove all pieces."""
        self.pawns = BB_EMPTY
        self.knights = BB_EMPTY
        self.bishops = BB_EMPTY
        self.rooks = BB_EMPTY
        self.queens = BB_EMPTY
        self.kings = BB_EMPTY
        self.occupied_co = [BB_EMPTY, BB_EMPTY]
        self.occupied = BB_EMPTY
        self.promoted = BB_EMPTY

    # ------------------------------------------------------------------
    # Piece queries
    # ------------------------------------------------------------------

    def pieces_mask(self, piece_type: int, color: bool) -> int:
        """Mask of all pieces of the given type and colour."""
        bb = self._piece_mask(piece_type)
        return bb & self.occupied_co[color]

    def pieces(self, piece_type: int, color: bool) -> SquareSet:
        """SquareSet of all pieces of the given type and colour."""
        return SquareSet(self.pieces_mask(piece_type, color))

    def piece_at(self, square: int) -> typing.Optional[Piece]:
        """Return the :class:`Piece` at *square*, or ``None``."""
        pt = self.piece_type_at(square)
        if pt is None:
            return None
        color = bool(self.occupied_co[WHITE] & BB_SQUARES[square])
        return Piece(pt, color)

    def piece_type_at(self, square: int) -> typing.Optional[int]:
        """Return the piece type at *square* (1–6), or ``None``."""
        mask = BB_SQUARES[square]
        if not (self.occupied & mask):
            return None
        if self.pawns & mask:
            return PAWN
        if self.knights & mask:
            return KNIGHT
        if self.bishops & mask:
            return BISHOP
        if self.rooks & mask:
            return ROOK
        if self.queens & mask:
            return QUEEN
        return KING

    def color_at(self, square: int) -> typing.Optional[bool]:
        """Return the colour of the piece at *square*, or ``None``."""
        mask = BB_SQUARES[square]
        if self.occupied_co[WHITE] & mask:
            return WHITE
        if self.occupied_co[BLACK] & mask:
            return BLACK
        return None

    def king(self, color: bool) -> typing.Optional[int]:
        """Return the king square for *color*, or ``None``."""
        bb = self.occupied_co[color] & self.kings
        if bb:
            return msb(bb)
        return None

    # ------------------------------------------------------------------
    # Attack computation
    # ------------------------------------------------------------------

    def attacks_mask(self, square: int) -> int:
        """Attack mask for the piece on *square*."""
        bb_square = BB_SQUARES[square]
        if bb_square & self.pawns:
            color = bool(bb_square & self.occupied_co[WHITE])
            return BB_PAWN_ATTACKS[color][square]
        if bb_square & self.knights:
            return BB_KNIGHT_ATTACKS[square]
        if bb_square & self.kings:
            return BB_KING_ATTACKS[square]
        attacks = BB_EMPTY
        if bb_square & (self.bishops | self.queens):
            attacks = BB_DIAG_ATTACKS[square][self.occupied & BB_DIAG_MASKS[square]]
        if bb_square & (self.rooks | self.queens):
            attacks |= (
                BB_FILE_ATTACKS[square][self.occupied & BB_FILE_MASKS[square]]
                | BB_RANK_ATTACKS[square][self.occupied & BB_RANK_MASKS[square]]
            )
        return attacks

    def attacks(self, square: int) -> SquareSet:
        """SquareSet of squares attacked by the piece on *square*."""
        return SquareSet(self.attacks_mask(square))

    def _attackers_mask(self, color: bool, square: int, occupied: int) -> int:
        rank_pieces = BB_RANK_ATTACKS[square][occupied & BB_RANK_MASKS[square]]
        file_pieces = BB_FILE_ATTACKS[square][occupied & BB_FILE_MASKS[square]]
        diag_pieces = BB_DIAG_ATTACKS[square][occupied & BB_DIAG_MASKS[square]]

        attackers = (
            (BB_KING_ATTACKS[square] & self.kings)
            | (BB_KNIGHT_ATTACKS[square] & self.knights)
            | (rank_pieces & (self.rooks | self.queens))
            | (file_pieces & (self.rooks | self.queens))
            | (diag_pieces & (self.bishops | self.queens))
            | (BB_PAWN_ATTACKS[not color][square] & self.pawns)
        )
        return attackers & self.occupied_co[color]

    def attackers_mask(self, color: bool, square: int) -> int:
        """Mask of *color* pieces that attack *square*."""
        return self._attackers_mask(color, square, self.occupied)

    def attackers(self, color: bool, square: int) -> SquareSet:
        """SquareSet of *color* pieces that attack *square*."""
        return SquareSet(self.attackers_mask(color, square))

    def is_attacked_by(self, color: bool, square: int) -> bool:
        """Whether *square* is attacked by any piece of *color*."""
        return bool(self.attackers_mask(color, square))

    def pin_mask(self, color: bool, square: int) -> int:
        """Mask of the ray pinning *square* to the king of *color*, or BB_ALL."""
        king_sq = self.king(color)
        if king_sq is None:
            return BB_ALL

        for attacks, masks, sliders in [
            (BB_FILE_ATTACKS, BB_FILE_MASKS, self.rooks | self.queens),
            (BB_RANK_ATTACKS, BB_RANK_MASKS, self.rooks | self.queens),
            (BB_DIAG_ATTACKS, BB_DIAG_MASKS, self.bishops | self.queens),
        ]:
            ray = BB_RAYS[king_sq][square]
            if not ray:
                continue
            enemy_sliders = sliders & self.occupied_co[not color] & ray
            if not enemy_sliders:
                continue

            occ_without = self.occupied & ~BB_SQUARES[square]
            ray_attacks = attacks[king_sq][occ_without & masks[king_sq]]
            pinners = ray_attacks & enemy_sliders
            for pinner_sq in scan_reversed(pinners):
                if between(king_sq, pinner_sq) & BB_SQUARES[square]:
                    return ray

        return BB_ALL

    def pin(self, color: bool, square: int) -> SquareSet:
        """SquareSet of the pin ray for *square*, or all squares if not pinned."""
        return SquareSet(self.pin_mask(color, square))

    def is_pinned(self, color: bool, square: int) -> bool:
        """Whether the piece on *square* is pinned to the *color* king."""
        return self.pin_mask(color, square) != BB_ALL

    # ------------------------------------------------------------------
    # Piece placement
    # ------------------------------------------------------------------

    def remove_piece_at(self, square: int) -> typing.Optional[int]:
        """Remove the piece at *square*; return its type, or ``None``."""
        pt = self.piece_type_at(square)
        if pt is None:
            return None
        mask = BB_SQUARES[square]
        self._remove_piece_mask(pt, mask)
        return pt

    def set_piece_at(
        self,
        square: int,
        piece: typing.Optional[Piece],
        promoted: bool = False,
    ) -> None:
        """Place *piece* on *square* (removing any piece already there)."""
        self.remove_piece_at(square)
        if piece is None:
            return
        mask = BB_SQUARES[square]
        self._set_piece_type_mask(piece.piece_type, mask)
        self.occupied_co[piece.color] |= mask
        self.occupied |= mask
        if promoted:
            self.promoted |= mask
        else:
            self.promoted &= ~mask

    def _remove_piece_mask(self, piece_type: int, mask: int) -> None:
        inv = ~mask
        if piece_type == PAWN:
            self.pawns &= inv
        elif piece_type == KNIGHT:
            self.knights &= inv
        elif piece_type == BISHOP:
            self.bishops &= inv
        elif piece_type == ROOK:
            self.rooks &= inv
        elif piece_type == QUEEN:
            self.queens &= inv
        elif piece_type == KING:
            self.kings &= inv
        self.occupied_co[WHITE] &= inv
        self.occupied_co[BLACK] &= inv
        self.occupied &= inv
        self.promoted &= inv

    def _set_piece_type_mask(self, piece_type: int, mask: int) -> None:
        if piece_type == PAWN:
            self.pawns |= mask
        elif piece_type == KNIGHT:
            self.knights |= mask
        elif piece_type == BISHOP:
            self.bishops |= mask
        elif piece_type == ROOK:
            self.rooks |= mask
        elif piece_type == QUEEN:
            self.queens |= mask
        elif piece_type == KING:
            self.kings |= mask

    def _piece_mask(self, piece_type: int) -> int:
        if piece_type == PAWN:
            return self.pawns
        elif piece_type == KNIGHT:
            return self.knights
        elif piece_type == BISHOP:
            return self.bishops
        elif piece_type == ROOK:
            return self.rooks
        elif piece_type == QUEEN:
            return self.queens
        elif piece_type == KING:
            return self.kings
        return BB_EMPTY

    # ------------------------------------------------------------------
    # FEN
    # ------------------------------------------------------------------

    def board_fen(self, *, promoted: bool = False) -> str:
        """Return the board part of a FEN string."""
        builder: typing.List[str] = []
        for rank in range(7, -1, -1):
            empty = 0
            for file in range(8):
                sq = rank * 8 + file
                pt = self.piece_type_at(sq)
                if pt is None:
                    empty += 1
                else:
                    if empty:
                        builder.append(str(empty))
                        empty = 0
                    sym = PIECE_SYMBOLS[pt]
                    assert sym is not None
                    if self.occupied_co[WHITE] & BB_SQUARES[sq]:
                        sym = sym.upper()
                    builder.append(sym)
                    if promoted and self.promoted & BB_SQUARES[sq]:
                        builder.append("~")
            if empty:
                builder.append(str(empty))
            if rank > 0:
                builder.append("/")
        return "".join(builder)

    def set_board_fen(self, fen: str) -> None:
        """Set the board from the board part of a FEN string."""
        self.clear_board()

        fen = fen.strip()
        if " " in fen:
            raise ValueError(f"Expected board FEN without spaces, got: {fen!r}")

        rows = fen.split("/")
        if len(rows) != 8:
            raise ValueError(f"Expected 8 rows in board FEN, got {len(rows)}: {fen!r}")

        for rank_idx, row in enumerate(reversed(rows)):
            file_idx = 0
            prev_was_digit = False
            prev_was_piece = False
            for char in row:
                if char in "12345678":
                    if prev_was_digit:
                        raise ValueError(f"Consecutive digits in board FEN: {fen!r}")
                    file_idx += int(char)
                    prev_was_digit = True
                    prev_was_piece = False
                elif char == "~":
                    if not prev_was_piece:
                        raise ValueError(f"Unexpected '~' in board FEN: {fen!r}")
                    self.promoted |= BB_SQUARES[(rank_idx) * 8 + file_idx - 1]
                    prev_was_digit = False
                    prev_was_piece = False
                elif char.lower() in "pnbrqk":
                    if file_idx >= 8:
                        raise ValueError(f"Too many pieces in rank in board FEN: {fen!r}")
                    sq = rank_idx * 8 + file_idx
                    pt = PIECE_SYMBOLS.index(char.lower())
                    mask = BB_SQUARES[sq]
                    self._set_piece_type_mask(pt, mask)
                    color = char.isupper()
                    self.occupied_co[color] |= mask
                    self.occupied |= mask
                    file_idx += 1
                    prev_was_digit = False
                    prev_was_piece = True
                else:
                    raise ValueError(f"Invalid character {char!r} in board FEN: {fen!r}")

            if file_idx != 8:
                raise ValueError(
                    f"Expected 8 files in rank {rank_idx + 1}, got {file_idx}: {fen!r}"
                )

    # ------------------------------------------------------------------
    # Piece map
    # ------------------------------------------------------------------

    def piece_map(self, *, mask: int = BB_ALL) -> typing.Dict[int, Piece]:
        """Return a dict mapping occupied squares to :class:`Piece` objects."""
        result: typing.Dict[int, Piece] = {}
        for sq in scan_reversed(self.occupied & mask):
            result[sq] = self.piece_at(sq)  # type: ignore[assignment]
        return result

    def set_piece_map(self, pieces: typing.Mapping[int, Piece]) -> None:
        """Set the board from a square-to-Piece mapping."""
        self.clear_board()
        for sq, piece in pieces.items():
            self.set_piece_at(sq, piece)

    # ------------------------------------------------------------------
    # Chess960 position setup
    # ------------------------------------------------------------------

    def set_chess960_pos(self, scharnagl: int) -> None:
        """Set the board to Chess960 starting position *scharnagl* (0–959)."""
        if not (0 <= scharnagl <= 959):
            raise ValueError(f"Scharnagl number must be 0..959, got {scharnagl}")

        self.clear_board()

        # Decode the Scharnagl number
        n, bw = divmod(scharnagl, 4)
        n, bb = divmod(n, 4)
        n, q = divmod(n, 6)

        # Light-square bishop: files 1,3,5,7 → index bw
        bishop1_file = bw * 2 + 1
        # Dark-square bishop: files 0,2,4,6 → index bb
        bishop2_file = bb * 2

        # Queen goes in the q-th empty square
        remaining = [f for f in range(8) if f != bishop1_file and f != bishop2_file]
        queen_file = remaining[q]
        remaining.remove(queen_file)

        # Two knights in the remaining 5 squares, encoded by n (0–9)
        _knight_table = [
            (0, 1), (0, 2), (0, 3), (0, 4),
            (1, 2), (1, 3), (1, 4),
            (2, 3), (2, 4),
            (3, 4),
        ]
        k1_idx, k2_idx = _knight_table[n]
        knight1_file = remaining[k1_idx]
        knight2_file = remaining[k2_idx]

        # Remaining 3 squares get R, K, R (left to right)
        rk_files = [f for f in remaining if f != knight1_file and f != knight2_file]
        rook1_file, king_file, rook2_file = rk_files[0], rk_files[1], rk_files[2]

        # Place white pieces on rank 1, black on rank 8
        for color, rank in [(WHITE, 0), (BLACK, 56)]:
            self.set_piece_at(rank + bishop1_file, Piece(BISHOP, color))
            self.set_piece_at(rank + bishop2_file, Piece(BISHOP, color))
            self.set_piece_at(rank + queen_file, Piece(QUEEN, color))
            self.set_piece_at(rank + knight1_file, Piece(KNIGHT, color))
            self.set_piece_at(rank + knight2_file, Piece(KNIGHT, color))
            self.set_piece_at(rank + rook1_file, Piece(ROOK, color))
            self.set_piece_at(rank + king_file, Piece(KING, color))
            self.set_piece_at(rank + rook2_file, Piece(ROOK, color))

        # Pawns on ranks 2 and 7
        for sq in range(8, 16):
            self.set_piece_at(sq, Piece(PAWN, WHITE))
        for sq in range(48, 56):
            self.set_piece_at(sq, Piece(PAWN, BLACK))

    def chess960_pos(self) -> typing.Optional[int]:
        """Return the Scharnagl number of the current position, or ``None``."""
        if self.occupied_co[WHITE] != (BB_RANK_1 | BB_RANK_2):
            return None
        if self.occupied_co[BLACK] != (BB_RANK_7 | BB_RANK_8):
            return None
        if self.pawns != (BB_RANK_2 | BB_RANK_7):
            return None
        if self.promoted:
            return None

        # Check symmetry: same piece types on same files for both colours
        for file in range(8):
            w_pt = self.piece_type_at(file)
            b_pt = self.piece_type_at(56 + file)
            if w_pt != b_pt:
                return None

        # Extract white back rank pieces
        back_rank = [self.piece_type_at(f) for f in range(8)]

        # Find bishop files
        bishop_files = [f for f in range(8) if back_rank[f] == BISHOP]
        if len(bishop_files) != 2:
            return None
        # One must be light, one dark
        if bishop_files[0] % 2 == bishop_files[1] % 2:
            return None

        light_bishop = [f for f in bishop_files if f % 2 == 1]
        dark_bishop = [f for f in bishop_files if f % 2 == 0]
        if len(light_bishop) != 1 or len(dark_bishop) != 1:
            return None

        bw = light_bishop[0] // 2  # index 0-3
        bb_idx = dark_bishop[0] // 2  # index 0-3

        # Queen file among remaining squares
        remaining = [f for f in range(8) if f not in bishop_files]
        queen_files = [f for f in remaining if back_rank[f] == QUEEN]
        if len(queen_files) != 1:
            return None
        q = remaining.index(queen_files[0])
        remaining.remove(queen_files[0])

        # Knight indices among remaining 5 squares
        knight_files = [f for f in remaining if back_rank[f] == KNIGHT]
        if len(knight_files) != 2:
            return None

        _knight_table = [
            (0, 1), (0, 2), (0, 3), (0, 4),
            (1, 2), (1, 3), (1, 4),
            (2, 3), (2, 4),
            (3, 4),
        ]
        k1_idx = remaining.index(knight_files[0])
        k2_idx = remaining.index(knight_files[1])
        try:
            n = _knight_table.index((k1_idx, k2_idx))
        except ValueError:
            return None

        # Remaining must be R, K, R
        rk_remaining = [f for f in remaining if f not in knight_files]
        if len(rk_remaining) != 3:
            return None
        if [back_rank[f] for f in rk_remaining] != [ROOK, KING, ROOK]:
            return None

        return 96 * n + 16 * q + 4 * bb_idx + bw

    # ------------------------------------------------------------------
    # Text rendering
    # ------------------------------------------------------------------

    def unicode(
        self,
        *,
        invert_color: bool = False,
        borders: bool = False,
        empty_square: str = "⭘",
        orientation: bool = WHITE,
    ) -> str:
        """Render the board as a Unicode string."""
        builder: typing.List[str] = []
        if orientation:
            ranks = range(7, -1, -1)
        else:
            ranks = range(8)

        for rank in ranks:
            if borders:
                builder.append(" ")
                builder.append("-" * 17)
                builder.append("\n")
                builder.append(RANK_NAMES[rank])
                builder.append(" ")

            if orientation:
                files = range(8)
            else:
                files = range(7, -1, -1)

            for file in files:
                sq = rank * 8 + file
                piece = self.piece_at(sq)
                if borders:
                    builder.append("|")
                elif file > 0:
                    builder.append(" ")

                if piece:
                    builder.append(piece.unicode_symbol(invert_color=invert_color))
                else:
                    builder.append(empty_square)

            if borders:
                builder.append("|")
            builder.append("\n")

        if borders:
            builder.append(" ")
            builder.append("-" * 17)
            builder.append("\n")
            builder.append("  ")
            if orientation:
                builder.append(" ".join(FILE_NAMES))
            else:
                builder.append(" ".join(reversed(FILE_NAMES)))
            builder.append("\n")

        return "".join(builder).rstrip("\n")

    # ------------------------------------------------------------------
    # Transforms
    # ------------------------------------------------------------------

    def apply_transform(self, f: typing.Callable[[int], int]) -> None:
        """Apply a bitboard transform function in place."""
        self.pawns = f(self.pawns)
        self.knights = f(self.knights)
        self.bishops = f(self.bishops)
        self.rooks = f(self.rooks)
        self.queens = f(self.queens)
        self.kings = f(self.kings)
        self.occupied_co[WHITE] = f(self.occupied_co[WHITE])
        self.occupied_co[BLACK] = f(self.occupied_co[BLACK])
        self.occupied = f(self.occupied)
        self.promoted = f(self.promoted)

    def transform(self, f: typing.Callable[[int], int]) -> BaseBoard:
        """Return a new board with transform *f* applied."""
        board = self.copy()
        board.apply_transform(f)
        return board

    def apply_mirror(self) -> None:
        """Mirror the board vertically (swap ranks)."""
        self.apply_transform(flip_vertical)
        # Swap colours
        self.occupied_co[WHITE], self.occupied_co[BLACK] = (
            self.occupied_co[BLACK],
            self.occupied_co[WHITE],
        )

    def mirror(self) -> BaseBoard:
        """Return a vertically mirrored copy."""
        board = self.copy()
        board.apply_mirror()
        return board

    # ------------------------------------------------------------------
    # Copy, class methods, dunder
    # ------------------------------------------------------------------

    def copy(self) -> BaseBoard:
        """Return a copy of this board."""
        board = BaseBoard(None)
        board.pawns = self.pawns
        board.knights = self.knights
        board.bishops = self.bishops
        board.rooks = self.rooks
        board.queens = self.queens
        board.kings = self.kings
        board.occupied_co = list(self.occupied_co)
        board.occupied = self.occupied
        board.promoted = self.promoted
        return board

    def __copy__(self) -> BaseBoard:
        return self.copy()

    def __deepcopy__(self, memo: typing.Dict[int, typing.Any]) -> BaseBoard:
        return self.copy()

    @classmethod
    def empty(cls) -> BaseBoard:
        """Return an empty board."""
        return cls(None)

    @classmethod
    def from_chess960_pos(cls, scharnagl: int) -> BaseBoard:
        """Return a board set to Chess960 position *scharnagl*."""
        board = cls(None)
        board.set_chess960_pos(scharnagl)
        return board

    def __eq__(self, other: object) -> bool:
        if isinstance(other, BaseBoard):
            return (
                self.pawns == other.pawns
                and self.knights == other.knights
                and self.bishops == other.bishops
                and self.rooks == other.rooks
                and self.queens == other.queens
                and self.kings == other.kings
                and self.occupied_co[WHITE] == other.occupied_co[WHITE]
                and self.occupied_co[BLACK] == other.occupied_co[BLACK]
                and self.promoted == other.promoted
            )
        return NotImplemented

    def __repr__(self) -> str:
        return f"{type(self).__name__}({self.board_fen()!r})"

    def __str__(self) -> str:
        builder: typing.List[str] = []
        for rank in range(7, -1, -1):
            for file in range(8):
                sq = rank * 8 + file
                if file > 0:
                    builder.append(" ")
                piece = self.piece_at(sq)
                if piece:
                    builder.append(piece.symbol())
                else:
                    builder.append(".")
            if rank > 0:
                builder.append("\n")
        return "".join(builder)
