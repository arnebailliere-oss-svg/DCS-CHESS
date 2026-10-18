"""Board class (FR-C7) — full game state, move generation, FEN/EPD, notation."""

from __future__ import annotations

import copy
import re
import typing

from .constants import (
    WHITE, BLACK, COLORS, COLOR_NAMES,
    PAWN, KNIGHT, BISHOP, ROOK, QUEEN, KING,
    PIECE_TYPES, PIECE_SYMBOLS, PIECE_NAMES,
    BB_EMPTY, BB_ALL, BB_SQUARES,
    BB_FILES, BB_RANKS,
    BB_FILE_A, BB_FILE_B, BB_FILE_C, BB_FILE_D,
    BB_FILE_E, BB_FILE_F, BB_FILE_G, BB_FILE_H,
    BB_RANK_1, BB_RANK_2, BB_RANK_3, BB_RANK_4,
    BB_RANK_5, BB_RANK_6, BB_RANK_7, BB_RANK_8,
    BB_LIGHT_SQUARES, BB_DARK_SQUARES,
    BB_BACKRANKS,
    BB_KNIGHT_ATTACKS, BB_KING_ATTACKS, BB_PAWN_ATTACKS,
    BB_DIAG_MASKS, BB_DIAG_ATTACKS,
    BB_FILE_MASKS, BB_FILE_ATTACKS,
    BB_RANK_MASKS, BB_RANK_ATTACKS,
    BB_RAYS,
    STARTING_FEN, STARTING_BOARD_FEN,
    SQUARE_NAMES, FILE_NAMES, RANK_NAMES,
    SAN_REGEX, FEN_CASTLING_REGEX,
    STATUS_VALID, STATUS_NO_WHITE_KING, STATUS_NO_BLACK_KING,
    STATUS_TOO_MANY_KINGS, STATUS_TOO_MANY_WHITE_PAWNS,
    STATUS_TOO_MANY_BLACK_PAWNS, STATUS_PAWNS_ON_BACKRANK,
    STATUS_TOO_MANY_WHITE_PIECES, STATUS_TOO_MANY_BLACK_PIECES,
    STATUS_BAD_CASTLING_RIGHTS, STATUS_INVALID_EP_SQUARE,
    STATUS_OPPOSITE_CHECK, STATUS_EMPTY,
    STATUS_TOO_MANY_CHECKERS, STATUS_IMPOSSIBLE_CHECK,
)
from .piece import Piece
from .move import Move
from .squareset import SquareSet
from .baseboard import BaseBoard
from .status import Status, Termination, Outcome
from .errors import IllegalMoveError, InvalidMoveError, AmbiguousMoveError
from .functions import (
    square, square_file, square_rank, square_name, parse_square,
    square_distance, square_mirror,
    lsb, msb, scan_forward, scan_reversed, popcount,
    shift_up, shift_down,
    flip_vertical, flip_horizontal, flip_diagonal, flip_anti_diagonal,
    ray, between,
)


# ======================================================================
# Board
# ======================================================================

class Board(BaseBoard):
    """A chess board with full game state, move generation, and notation."""

    aliases: typing.ClassVar[typing.List[str]] = [
        "Standard", "Chess", "Classical", "Normal", "Illegal", "From Position",
    ]
    uci_variant: typing.ClassVar[typing.Optional[str]] = "chess"
    xboard_variant: typing.ClassVar[typing.Optional[str]] = "normal"
    starting_fen: typing.ClassVar[str] = STARTING_FEN
    tbw_suffix: typing.ClassVar[typing.Optional[str]] = ".rtbw"
    tbz_suffix: typing.ClassVar[typing.Optional[str]] = ".rtbz"
    connected_kings: typing.ClassVar[bool] = False
    one_king: typing.ClassVar[bool] = True
    captures_compulsory: typing.ClassVar[bool] = False

    def __init__(
        self,
        fen: typing.Optional[str] = STARTING_FEN,
        *,
        chess960: bool = False,
    ) -> None:
        super().__init__(None)

        self.chess960: bool = chess960
        self.turn: bool = WHITE
        self.castling_rights: int = BB_EMPTY
        self.ep_square: typing.Optional[int] = None
        self.halfmove_clock: int = 0
        self.fullmove_number: int = 1
        self.move_stack: typing.List[Move] = []
        self._stack: typing.List[_BoardState] = []

        if fen is None:
            self.clear()
        elif fen == STARTING_FEN:
            self.reset()
        else:
            self.set_fen(fen)

    def reset(self) -> None:
        """Reset to the starting position."""
        self.reset_board()
        self.turn = WHITE
        self.castling_rights = BB_SQUARES[0] | BB_SQUARES[7] | BB_SQUARES[56] | BB_SQUARES[63]
        self.ep_square = None
        self.halfmove_clock = 0
        self.fullmove_number = 1
        self.clear_stack()

    def clear(self) -> None:
        """Clear the board and game state."""
        self.clear_board()
        self.turn = WHITE
        self.castling_rights = BB_EMPTY
        self.ep_square = None
        self.halfmove_clock = 0
        self.fullmove_number = 1
        self.clear_stack()

    def clear_stack(self) -> None:
        self.move_stack.clear()
        self._stack.clear()

    def root(self) -> Board:
        """Return a copy at the root position (no moves played)."""
        if self._stack:
            board = self.copy()
            while board.move_stack:
                board.pop()
            return board
        return self.copy(stack=False)

    def ply(self) -> int:
        """Number of half-moves since the start of the game."""
        return 2 * (self.fullmove_number - 1) + (0 if self.turn else 1)

    # ------------------------------------------------------------------
    # Checkers and check detection
    # ------------------------------------------------------------------

    def checkers_mask(self) -> int:
        king_sq = self.king(self.turn)
        if king_sq is None:
            return BB_EMPTY
        return self.attackers_mask(not self.turn, king_sq)

    def checkers(self) -> SquareSet:
        return SquareSet(self.checkers_mask())

    def is_check(self) -> bool:
        return bool(self.checkers_mask())

    def gives_check(self, move: Move) -> bool:
        """Whether *move* gives check to the opponent."""
        self.push(move)
        try:
            return self.is_check()
        finally:
            self.pop()

    def is_into_check(self, move: Move) -> bool:
        """Whether *move* leaves our own king in check (illegal)."""
        self.push(move)
        try:
            king_sq = self.king(not self.turn)
            if king_sq is None:
                return False
            return bool(self.attackers_mask(self.turn, king_sq))
        finally:
            self.pop()

    def was_into_check(self) -> bool:
        king_sq = self.king(not self.turn)
        if king_sq is None:
            return False
        return self.is_attacked_by(self.turn, king_sq)

    # ------------------------------------------------------------------
    # Pseudo-legal move generation
    # ------------------------------------------------------------------

    def generate_pseudo_legal_moves(
        self,
        from_mask: int = BB_ALL,
        to_mask: int = BB_ALL,
    ) -> typing.Iterator[Move]:
        our_pieces = self.occupied_co[self.turn]

        # Non-pawn pieces (including king), from-square descending
        for from_sq in scan_reversed(our_pieces & ~self.pawns & from_mask):
            targets = self.attacks_mask(from_sq) & ~our_pieces & to_mask
            for to_sq in scan_reversed(targets):
                yield Move(from_sq, to_sq)

        # Castling
        yield from self.generate_castling_moves(from_mask, to_mask)

        # Pawn moves (captures, single pushes, double pushes)
        yield from self._generate_pawn_moves(from_mask & our_pieces, to_mask)

        # En passant
        yield from self.generate_pseudo_legal_ep(from_mask, to_mask)

    def _generate_pawn_moves(self, from_mask: int, to_mask: int) -> typing.Iterator[Move]:
        our_pawns = self.pawns & self.occupied_co[self.turn] & from_mask
        enemy = self.occupied_co[not self.turn]

        if self.turn == WHITE:
            # Captures (from-square descending, targets descending per pawn)
            for from_sq in scan_reversed(our_pawns):
                for to_sq in scan_reversed(BB_PAWN_ATTACKS[WHITE][from_sq] & enemy & to_mask):
                    if to_sq >= 56:
                        yield from self._promote(from_sq, to_sq)
                    else:
                        yield Move(from_sq, to_sq)

            # Single pushes (targets descending)
            single = shift_up(our_pawns) & ~self.occupied
            for to_sq in scan_reversed(single & to_mask):
                from_sq = to_sq - 8
                if to_sq >= 56:
                    yield from self._promote(from_sq, to_sq)
                else:
                    yield Move(from_sq, to_sq)

            # Double pushes (targets descending)
            double = shift_up(single & BB_RANK_3) & ~self.occupied & to_mask
            for to_sq in scan_reversed(double):
                yield Move(to_sq - 16, to_sq)
        else:
            # Captures (from-square descending, targets descending per pawn)
            for from_sq in scan_reversed(our_pawns):
                for to_sq in scan_reversed(BB_PAWN_ATTACKS[BLACK][from_sq] & enemy & to_mask):
                    if to_sq <= 7:
                        yield from self._promote(from_sq, to_sq)
                    else:
                        yield Move(from_sq, to_sq)

            # Single pushes (targets descending)
            single = (our_pawns >> 8) & ~self.occupied
            for to_sq in scan_reversed(single & to_mask):
                from_sq = to_sq + 8
                if to_sq <= 7:
                    yield from self._promote(from_sq, to_sq)
                else:
                    yield Move(from_sq, to_sq)

            # Double pushes (targets descending)
            double = ((single & BB_RANK_6) >> 8) & ~self.occupied & to_mask
            for to_sq in scan_reversed(double):
                yield Move(to_sq + 16, to_sq)

    def _promote(self, from_sq: int, to_sq: int) -> typing.Iterator[Move]:
        yield Move(from_sq, to_sq, promotion=QUEEN)
        yield Move(from_sq, to_sq, promotion=ROOK)
        yield Move(from_sq, to_sq, promotion=BISHOP)
        yield Move(from_sq, to_sq, promotion=KNIGHT)

    def generate_pseudo_legal_ep(
        self,
        from_mask: int = BB_ALL,
        to_mask: int = BB_ALL,
    ) -> typing.Iterator[Move]:
        if self.ep_square is None:
            return
        if not (BB_SQUARES[self.ep_square] & to_mask):
            return

        if self.turn == WHITE:
            capturers = self.pawns & self.occupied_co[WHITE] & from_mask
            capturers &= BB_PAWN_ATTACKS[BLACK][self.ep_square]
        else:
            capturers = self.pawns & self.occupied_co[BLACK] & from_mask
            capturers &= BB_PAWN_ATTACKS[WHITE][self.ep_square]

        for from_sq in scan_reversed(capturers):
            yield Move(from_sq, self.ep_square)

    def generate_pseudo_legal_captures(
        self,
        from_mask: int = BB_ALL,
        to_mask: int = BB_ALL,
    ) -> typing.Iterator[Move]:
        yield from self.generate_pseudo_legal_moves(from_mask, to_mask & self.occupied_co[not self.turn])
        yield from self.generate_pseudo_legal_ep(from_mask, to_mask)

    def _attacked_for_king(self, path: int, occupied: int) -> bool:
        enemy = not self.turn
        return any(self._attackers_mask(enemy, sq, occupied) for sq in scan_reversed(path))

    def generate_castling_moves(
        self,
        from_mask: int = BB_ALL,
        to_mask: int = BB_ALL,
    ) -> typing.Iterator[Move]:
        if not self.castling_rights:
            return

        king_sq = self.king(self.turn)
        if king_sq is None:
            return
        if not (BB_SQUARES[king_sq] & from_mask):
            return

        backrank = BB_RANK_1 if self.turn == WHITE else BB_RANK_8
        bb_king = BB_SQUARES[king_sq]

        for rook_sq in scan_reversed(self.castling_rights & backrank & self.rooks):
            rook_bb = BB_SQUARES[rook_sq]
            a_side = rook_sq < king_sq

            if a_side:
                king_to = square(2, square_rank(king_sq))  # c1 or c8
                rook_to = square(3, square_rank(king_sq))  # d1 or d8
            else:
                king_to = square(6, square_rank(king_sq))  # g1 or g8
                rook_to = square(5, square_rank(king_sq))  # f1 or f8

            if not (BB_SQUARES[king_to] & to_mask or BB_SQUARES[rook_sq] & to_mask):
                # For chess960 compatibility, castling 'to' can be the rook square
                if not self.chess960:
                    if not (BB_SQUARES[king_to] & to_mask):
                        continue

            king_to_bb = BB_SQUARES[king_to]
            rook_to_bb = BB_SQUARES[rook_to]

            king_path = between(king_sq, king_to)
            rook_path = between(rook_sq, rook_to)

            if (self.occupied ^ bb_king ^ rook_bb) & (king_path | rook_path | king_to_bb | rook_to_bb):
                continue

            if self._attacked_for_king(king_path | bb_king, self.occupied ^ bb_king):
                continue
            if self._attacked_for_king(king_to_bb, self.occupied ^ bb_king ^ rook_bb ^ rook_to_bb):
                continue

            if self.chess960:
                yield Move(king_sq, rook_sq)
            else:
                yield Move(king_sq, king_to)

    # ------------------------------------------------------------------
    # Legal move generation
    # ------------------------------------------------------------------

    def generate_legal_moves(
        self,
        from_mask: int = BB_ALL,
        to_mask: int = BB_ALL,
    ) -> typing.Iterator[Move]:
        king_sq = self.king(self.turn)
        if king_sq is None:
            yield from self.generate_pseudo_legal_moves(from_mask, to_mask)
            return

        checkers = self.checkers_mask()
        if checkers:
            yield from self._generate_evasions(king_sq, checkers, from_mask, to_mask)
        else:
            yield from self._generate_non_evasions(from_mask, to_mask)

    def _generate_evasions(
        self,
        king_sq: int,
        checkers: int,
        from_mask: int,
        to_mask: int,
    ) -> typing.Iterator[Move]:
        # King moves always allowed (will be legality-checked)
        sliders = checkers & (self.bishops | self.rooks | self.queens)
        attacked = BB_EMPTY
        for checker_sq in scan_reversed(sliders):
            attacked |= BB_RAYS[king_sq][checker_sq] & ~BB_SQUARES[checker_sq]

        if BB_SQUARES[king_sq] & from_mask:
            for to_sq in scan_reversed(BB_KING_ATTACKS[king_sq] & ~self.occupied_co[self.turn] & ~attacked & to_mask):
                if not self._attackers_mask(not self.turn, to_sq, self.occupied & ~BB_SQUARES[king_sq]):
                    yield Move(king_sq, to_sq)

        # If double check, only king moves
        checker_count = popcount(checkers)
        if checker_count > 1:
            return

        # Single check: block or capture the checker
        checker_sq = lsb(checkers)
        target = between(king_sq, checker_sq) | BB_SQUARES[checker_sq]
        target &= to_mask

        yield from self._generate_legal_piece_moves(from_mask, target)
        yield from self._generate_legal_pawn_moves(from_mask, target)
        yield from self.generate_legal_ep(from_mask, to_mask)

    def _generate_non_evasions(
        self,
        from_mask: int,
        to_mask: int,
    ) -> typing.Iterator[Move]:
        king_sq = self.king(self.turn)
        assert king_sq is not None
        our_pieces = self.occupied_co[self.turn]

        # Non-pawn pieces (including king), from-square descending
        for from_sq in scan_reversed(our_pieces & ~self.pawns & from_mask):
            if from_sq == king_sq:
                for to_sq in scan_reversed(BB_KING_ATTACKS[king_sq] & ~our_pieces & to_mask):
                    if not self._attackers_mask(not self.turn, to_sq, self.occupied & ~BB_SQUARES[king_sq]):
                        yield Move(king_sq, to_sq)
            else:
                pin = self.pin_mask(self.turn, from_sq)
                targets = self.attacks_mask(from_sq) & ~our_pieces & to_mask & pin
                for to_sq in scan_reversed(targets):
                    yield Move(from_sq, to_sq)

        # Castling
        yield from self.generate_castling_moves(from_mask, to_mask)

        # Pawn moves (captures, single pushes, double pushes)
        yield from self._generate_legal_pawn_moves(from_mask, to_mask)

        # En passant
        yield from self.generate_legal_ep(from_mask, to_mask)

    def _generate_legal_piece_moves(
        self,
        from_mask: int,
        to_mask: int,
    ) -> typing.Iterator[Move]:
        """Legal non-pawn, non-king piece moves, from-square descending."""
        our_pieces = self.occupied_co[self.turn]
        non_pawns_non_king = our_pieces & ~self.pawns & ~self.kings & from_mask
        for from_sq in scan_reversed(non_pawns_non_king):
            pin = self.pin_mask(self.turn, from_sq)
            targets = self.attacks_mask(from_sq) & ~our_pieces & to_mask & pin
            for to_sq in scan_reversed(targets):
                yield Move(from_sq, to_sq)

    def _generate_legal_pawn_moves(
        self,
        from_mask: int,
        to_mask: int,
    ) -> typing.Iterator[Move]:
        """Legal pawn moves: captures first, then single pushes, then double pushes."""
        our_pieces = self.occupied_co[self.turn]
        enemy = self.occupied_co[not self.turn]
        our_pawns = self.pawns & our_pieces & from_mask

        if self.turn == WHITE:
            for from_sq in scan_reversed(our_pawns):
                pin = self.pin_mask(self.turn, from_sq)
                for to_sq in scan_reversed(BB_PAWN_ATTACKS[WHITE][from_sq] & enemy & to_mask & pin):
                    if to_sq >= 56:
                        yield from self._promote(from_sq, to_sq)
                    else:
                        yield Move(from_sq, to_sq)

            single = shift_up(our_pawns) & ~self.occupied
            for to_sq in scan_reversed(single & to_mask):
                from_sq = to_sq - 8
                if BB_SQUARES[to_sq] & self.pin_mask(self.turn, from_sq):
                    if to_sq >= 56:
                        yield from self._promote(from_sq, to_sq)
                    else:
                        yield Move(from_sq, to_sq)

            double = shift_up(single & BB_RANK_3) & ~self.occupied & to_mask
            for to_sq in scan_reversed(double):
                from_sq = to_sq - 16
                if BB_SQUARES[to_sq] & self.pin_mask(self.turn, from_sq):
                    yield Move(from_sq, to_sq)
        else:
            for from_sq in scan_reversed(our_pawns):
                pin = self.pin_mask(self.turn, from_sq)
                for to_sq in scan_reversed(BB_PAWN_ATTACKS[BLACK][from_sq] & enemy & to_mask & pin):
                    if to_sq <= 7:
                        yield from self._promote(from_sq, to_sq)
                    else:
                        yield Move(from_sq, to_sq)

            single = (our_pawns >> 8) & ~self.occupied
            for to_sq in scan_reversed(single & to_mask):
                from_sq = to_sq + 8
                if BB_SQUARES[to_sq] & self.pin_mask(self.turn, from_sq):
                    if to_sq <= 7:
                        yield from self._promote(from_sq, to_sq)
                    else:
                        yield Move(from_sq, to_sq)

            double = ((single & BB_RANK_6) >> 8) & ~self.occupied & to_mask
            for to_sq in scan_reversed(double):
                from_sq = to_sq + 16
                if BB_SQUARES[to_sq] & self.pin_mask(self.turn, from_sq):
                    yield Move(from_sq, to_sq)

    def generate_legal_ep(
        self,
        from_mask: int = BB_ALL,
        to_mask: int = BB_ALL,
    ) -> typing.Iterator[Move]:
        for move in self.generate_pseudo_legal_ep(from_mask, to_mask):
            if not self.is_into_check(move):
                yield move

    def generate_legal_captures(
        self,
        from_mask: int = BB_ALL,
        to_mask: int = BB_ALL,
    ) -> typing.Iterator[Move]:
        yield from self.generate_legal_moves(from_mask, to_mask & self.occupied_co[not self.turn])
        yield from self.generate_legal_ep(from_mask, to_mask)

    # ------------------------------------------------------------------
    # Move legality
    # ------------------------------------------------------------------

    def is_pseudo_legal(self, move: Move) -> bool:
        if not move:
            return False
        if move.drop:
            return False  # standard chess has no drops

        piece = self.piece_type_at(move.from_square)
        if piece is None:
            return False
        if not (self.occupied_co[self.turn] & BB_SQUARES[move.from_square]):
            return False

        to_bb = BB_SQUARES[move.to_square]

        if piece == KING and self._is_castling_move(move):
            return any(m == move for m in self.generate_castling_moves())

        if self.occupied_co[self.turn] & to_bb:
            return False

        if piece == PAWN:
            return self._is_pseudo_legal_pawn(move)

        if move.promotion:
            return False

        if piece == KING:
            return bool(BB_KING_ATTACKS[move.from_square] & to_bb)

        attacks = self.attacks_mask(move.from_square)
        return bool(attacks & to_bb)

    def _is_pseudo_legal_pawn(self, move: Move) -> bool:
        diff = move.to_square - move.from_square
        our_rank = square_rank(move.from_square)
        to_bb = BB_SQUARES[move.to_square]

        if self.turn == WHITE:
            promo_rank = 7
            start_rank = 1
            single = 8
            double = 16
        else:
            promo_rank = 0
            start_rank = 6
            single = -8
            double = -16

        is_promo = square_rank(move.to_square) == promo_rank
        if is_promo != bool(move.promotion):
            return False
        if move.promotion and move.promotion not in [KNIGHT, BISHOP, ROOK, QUEEN]:
            return False

        # Capture
        if to_bb & self.occupied_co[not self.turn]:
            return bool(BB_PAWN_ATTACKS[self.turn][move.from_square] & to_bb)
        # En passant
        if move.to_square == self.ep_square:
            return bool(BB_PAWN_ATTACKS[self.turn][move.from_square] & to_bb)
        # Single push
        if diff == single and not (self.occupied & to_bb):
            return True
        # Double push
        if diff == double and our_rank == start_rank:
            mid = move.from_square + single
            return not (self.occupied & BB_SQUARES[mid]) and not (self.occupied & to_bb)
        return False

    def _is_castling_move(self, move: Move) -> bool:
        if self.chess960:
            # In chess960, castling is king captures own rook
            return bool(
                BB_SQUARES[move.to_square] & self.rooks & self.occupied_co[self.turn]
            )
        # Standard: king moves 2 squares
        return abs(square_file(move.from_square) - square_file(move.to_square)) > 1

    def is_legal(self, move: Move) -> bool:
        return not self.is_variant_end() and self.is_pseudo_legal(move) and not self.is_into_check(move)

    # ------------------------------------------------------------------
    # Push / pop
    # ------------------------------------------------------------------

    def push(self, move: Move) -> None:
        """Play a move on the board."""
        # Save state
        self._stack.append(_BoardState(self))
        self.move_stack.append(move)

        ep_square = self.ep_square
        self.ep_square = None
        self.halfmove_clock += 1

        from_bb = BB_SQUARES[move.from_square]
        to_bb = BB_SQUARES[move.to_square]
        piece_type = self.piece_type_at(move.from_square)
        assert piece_type is not None
        captured_piece_type = self.piece_type_at(move.to_square)

        # Castling
        castling = piece_type == KING and bool(self.castling_rights) and self._is_castling_move(move)

        if castling:
            self._do_castling(move)
        else:
            # Remove captured piece
            if captured_piece_type is not None:
                self._remove_piece_mask(captured_piece_type, to_bb)
                self.halfmove_clock = 0

            # En passant capture
            if piece_type == PAWN and move.to_square == ep_square:
                if self.turn == WHITE:
                    captured_sq = ep_square - 8
                else:
                    captured_sq = ep_square + 8
                self._remove_piece_mask(PAWN, BB_SQUARES[captured_sq])
                self.halfmove_clock = 0

            # Move the piece
            from_was_promoted = bool(self.promoted & from_bb)
            self._remove_piece_mask(piece_type, from_bb)
            if move.promotion:
                self._set_piece_type_mask(move.promotion, to_bb)
                self.promoted |= to_bb
            else:
                self._set_piece_type_mask(piece_type, to_bb)
                if from_was_promoted:
                    self.promoted |= to_bb

            self.occupied_co[self.turn] = (self.occupied_co[self.turn] & ~from_bb) | to_bb
            self.occupied_co[not self.turn] &= ~to_bb
            self.occupied = self.occupied_co[WHITE] | self.occupied_co[BLACK]

        # Pawn: reset clock, set EP square
        if piece_type == PAWN:
            self.halfmove_clock = 0
            diff = move.to_square - move.from_square
            if abs(diff) == 16:
                self.ep_square = move.from_square + (8 if self.turn == WHITE else -8)

        # Update castling rights
        self.castling_rights &= ~from_bb & ~to_bb
        if piece_type == KING:
            backrank = BB_RANK_1 if self.turn == WHITE else BB_RANK_8
            self.castling_rights &= ~backrank

        # Switch turn
        if self.turn == BLACK:
            self.fullmove_number += 1
        self.turn = not self.turn

    def _do_castling(self, move: Move) -> None:
        king_sq = move.from_square
        if self.chess960:
            rook_sq = move.to_square
        else:
            # Determine rook square from king destination
            if square_file(move.to_square) > square_file(king_sq):
                # Kingside
                rook_sq = self._find_rook_for_castling(king_sq, kingside=True)
            else:
                rook_sq = self._find_rook_for_castling(king_sq, kingside=False)

        backrank_base = 0 if self.turn == WHITE else 56

        if rook_sq is not None and rook_sq > king_sq:
            king_to = backrank_base + 6
            rook_to = backrank_base + 5
        else:
            king_to = backrank_base + 2
            rook_to = backrank_base + 3

        # Remove king and rook
        self._remove_piece_mask(KING, BB_SQUARES[king_sq])
        if rook_sq is not None:
            self._remove_piece_mask(ROOK, BB_SQUARES[rook_sq])

        # Place king and rook
        self._set_piece_type_mask(KING, BB_SQUARES[king_to])
        self._set_piece_type_mask(ROOK, BB_SQUARES[rook_to])

        # Update occupancy
        occ = BB_EMPTY
        if rook_sq is not None:
            occ = BB_SQUARES[rook_sq]
        self.occupied_co[self.turn] = (
            (self.occupied_co[self.turn] & ~BB_SQUARES[king_sq] & ~occ)
            | BB_SQUARES[king_to] | BB_SQUARES[rook_to]
        )
        self.occupied = self.occupied_co[WHITE] | self.occupied_co[BLACK]

        # Clear castling rights for this side
        self.castling_rights &= ~(BB_RANK_1 if self.turn == WHITE else BB_RANK_8)

    def _find_rook_for_castling(self, king_sq: int, kingside: bool) -> typing.Optional[int]:
        backrank = BB_RANK_1 if self.turn == WHITE else BB_RANK_8
        rooks = self.rooks & self.occupied_co[self.turn] & self.castling_rights & backrank
        if kingside:
            for sq in scan_forward(rooks):
                if sq > king_sq:
                    return sq
        else:
            for sq in scan_reversed(rooks):
                if sq < king_sq:
                    return sq
        return None

    def pop(self) -> Move:
        """Undo the last move and return it."""
        move = self.move_stack.pop()
        state = self._stack.pop()
        state.restore(self)
        return move

    def peek(self) -> Move:
        """Return the last move without undoing it."""
        return self.move_stack[-1]

    # ------------------------------------------------------------------
    # Move properties
    # ------------------------------------------------------------------

    def is_en_passant(self, move: Move) -> bool:
        return (
            self.ep_square == move.to_square
            and bool(self.pawns & BB_SQUARES[move.from_square])
            and abs(move.to_square - move.from_square) in (7, 9)
        )

    def is_capture(self, move: Move) -> bool:
        return bool(self.occupied_co[not self.turn] & BB_SQUARES[move.to_square]) or self.is_en_passant(move)

    def is_zeroing(self, move: Move) -> bool:
        return bool(self.pawns & BB_SQUARES[move.from_square]) or self.is_capture(move) or bool(move.drop)

    def is_irreversible(self, move: Move) -> bool:
        return self.is_zeroing(move) or self._is_castling_move(move) or bool(
            self.castling_rights & (BB_SQUARES[move.from_square] | BB_SQUARES[move.to_square])
        )

    def is_castling(self, move: Move) -> bool:
        if self.piece_type_at(move.from_square) != KING:
            return False
        return self._is_castling_move(move)

    def is_kingside_castling(self, move: Move) -> bool:
        return self.is_castling(move) and square_file(move.to_square) > square_file(move.from_square)

    def is_queenside_castling(self, move: Move) -> bool:
        return self.is_castling(move) and square_file(move.to_square) < square_file(move.from_square)

    # ------------------------------------------------------------------
    # Castling rights helpers
    # ------------------------------------------------------------------

    @property
    def clean_castling_rights(self) -> int:
        if self._stack:
            return self.castling_rights
        return self.castling_rights & self.rooks & (BB_RANK_1 | BB_RANK_8)

    def has_castling_rights(self, color: bool) -> bool:
        backrank = BB_RANK_1 if color == WHITE else BB_RANK_8
        return bool(self.castling_rights & backrank)

    def has_kingside_castling_rights(self, color: bool) -> bool:
        king_sq = self.king(color)
        if king_sq is None:
            return False
        backrank = BB_RANK_1 if color == WHITE else BB_RANK_8
        for sq in scan_forward(self.castling_rights & backrank):
            if sq > king_sq:
                return True
        return False

    def has_queenside_castling_rights(self, color: bool) -> bool:
        king_sq = self.king(color)
        if king_sq is None:
            return False
        backrank = BB_RANK_1 if color == WHITE else BB_RANK_8
        for sq in scan_reversed(self.castling_rights & backrank):
            if sq < king_sq:
                return True
        return False

    def has_chess960_castling_rights(self) -> bool:
        return bool(self.castling_rights)

    # ------------------------------------------------------------------
    # FEN
    # ------------------------------------------------------------------

    def fen(
        self,
        *,
        shredder: bool = False,
        en_passant: str = "legal",
        promoted: typing.Optional[bool] = None,
    ) -> str:
        return " ".join([
            self.board_fen(promoted=bool(promoted)),
            "w" if self.turn == WHITE else "b",
            self.castling_shredder_fen() if shredder else self.castling_xfen(),
            SQUARE_NAMES[self.ep_square] if self.ep_square is not None and (
                en_passant == "fen" or self.has_legal_en_passant() if en_passant == "legal"
                else True
            ) else "-",
            str(self.halfmove_clock),
            str(self.fullmove_number),
        ])

    @property
    def shredder_fen(self) -> str:
        return self.fen(shredder=True)

    def set_fen(self, fen: str) -> None:
        parts = fen.split()
        if len(parts) not in (1, 2, 3, 4, 5, 6):
            raise ValueError(f"Invalid FEN: {fen!r}")

        # Board
        self.set_board_fen(parts[0])

        # Turn
        if len(parts) >= 2:
            if parts[1] == "w":
                self.turn = WHITE
            elif parts[1] == "b":
                self.turn = BLACK
            else:
                raise ValueError(f"Invalid turn in FEN: {parts[1]!r}")
        else:
            self.turn = WHITE

        # Castling
        if len(parts) >= 3:
            self.set_castling_fen(parts[2])
        else:
            self.castling_rights = BB_EMPTY

        # EP square
        if len(parts) >= 4 and parts[3] != "-":
            self.ep_square = parse_square(parts[3])
        else:
            self.ep_square = None

        # Halfmove clock
        if len(parts) >= 5:
            self.halfmove_clock = int(parts[4])
        else:
            self.halfmove_clock = 0

        # Fullmove number
        if len(parts) >= 6:
            self.fullmove_number = max(1, int(parts[5]))
        else:
            self.fullmove_number = 1

        self.clear_stack()

    def set_castling_fen(self, castling_fen: str) -> None:
        if castling_fen == "-":
            self.castling_rights = BB_EMPTY
            return

        self.castling_rights = BB_EMPTY
        for char in castling_fen:
            color = WHITE if char.isupper() else BLACK
            backrank = BB_RANK_1 if color == WHITE else BB_RANK_8
            king_sq = self.king(color)

            if char.upper() == "K":
                # Kingside
                if king_sq is not None:
                    for sq in scan_reversed(self.rooks & self.occupied_co[color] & backrank):
                        if sq > king_sq:
                            self.castling_rights |= BB_SQUARES[sq]
                            break
            elif char.upper() == "Q":
                # Queenside
                if king_sq is not None:
                    for sq in scan_forward(self.rooks & self.occupied_co[color] & backrank):
                        if sq < king_sq:
                            self.castling_rights |= BB_SQUARES[sq]
                            break
            elif char.upper() in "ABCDEFGH":
                # File-based (Shredder-FEN / X-FEN)
                file_idx = ord(char.upper()) - ord("A")
                sq_rank = 0 if color == WHITE else 7
                sq = sq_rank * 8 + file_idx
                self.castling_rights |= BB_SQUARES[sq]

    def castling_shredder_fen(self) -> str:
        if not self.castling_rights:
            return "-"
        builder: typing.List[str] = []
        for color in [WHITE, BLACK]:
            backrank = BB_RANK_1 if color == WHITE else BB_RANK_8
            king_sq = self.king(color)
            for sq in scan_reversed(self.castling_rights & backrank):
                ch = FILE_NAMES[square_file(sq)]
                builder.append(ch.upper() if color == WHITE else ch)
        return "".join(builder) or "-"

    def castling_xfen(self) -> str:
        if not self.castling_rights:
            return "-"
        builder: typing.List[str] = []
        for color in [WHITE, BLACK]:
            backrank = BB_RANK_1 if color == WHITE else BB_RANK_8
            king_sq = self.king(color)
            rights = self.castling_rights & backrank

            h_side: typing.Optional[int] = None
            a_side: typing.Optional[int] = None
            if king_sq is not None:
                for sq in scan_reversed(rights):
                    if sq > king_sq:
                        if h_side is None:
                            h_side = sq
                    else:
                        a_side = sq

            our_rooks = self.rooks & self.occupied_co[color] & backrank
            if h_side is not None:
                outermost_h = msb(our_rooks & ~((1 << (king_sq + 1)) - 1)) if our_rooks & ~((1 << (king_sq + 1)) - 1) else None
                if not self.chess960 or h_side == outermost_h:
                    builder.append("K" if color == WHITE else "k")
                else:
                    ch = FILE_NAMES[square_file(h_side)]
                    builder.append(ch.upper() if color == WHITE else ch)
            if a_side is not None:
                outermost_a = lsb(our_rooks & ((1 << king_sq) - 1)) if our_rooks & ((1 << king_sq) - 1) else None
                if not self.chess960 or a_side == outermost_a:
                    builder.append("Q" if color == WHITE else "q")
                else:
                    ch = FILE_NAMES[square_file(a_side)]
                    builder.append(ch.upper() if color == WHITE else ch)

        return "".join(builder) or "-"

    def has_pseudo_legal_en_passant(self) -> bool:
        return self.ep_square is not None and any(self.generate_pseudo_legal_ep())

    def has_legal_en_passant(self) -> bool:
        return self.ep_square is not None and any(self.generate_legal_ep())

    # ------------------------------------------------------------------
    # SAN / LAN notation
    # ------------------------------------------------------------------

    def san(self, move: Move) -> str:
        return self._algebraic(move, long=False)

    def lan(self, move: Move) -> str:
        return self._algebraic(move, long=True)

    def san_and_push(self, move: Move) -> str:
        san_str = self.san(move)
        self.push(move)
        return san_str

    def variation_san(self, moves: typing.Iterable[Move]) -> str:
        board = self.copy(stack=False)
        parts: typing.List[str] = []
        for i, move in enumerate(moves):
            if board.turn == WHITE:
                parts.append(f"{board.fullmove_number}.")
            elif i == 0:
                parts.append(f"{board.fullmove_number}...")
            parts.append(board.san(move))
            board.push(move)
        return " ".join(parts)

    def _algebraic(self, move: Move, *, long: bool) -> str:
        if not move:
            return "--"

        # Castling
        if self.is_castling(move):
            if self.is_kingside_castling(move):
                san = "O-O"
            else:
                san = "O-O-O"
        elif move.drop:
            san = PIECE_SYMBOLS[move.drop].upper() + "@" + SQUARE_NAMES[move.to_square]  # type: ignore
        else:
            piece = self.piece_type_at(move.from_square)
            assert piece is not None
            san = ""

            if piece != PAWN:
                san = PIECE_SYMBOLS[piece].upper()  # type: ignore

            if long:
                san += SQUARE_NAMES[move.from_square]
                if self.is_capture(move):
                    san += "x"
                else:
                    san += "-"
            else:
                # Disambiguation for non-pawn pieces
                if piece != PAWN:
                    san += self._disambiguate(piece, move)

                if self.is_capture(move):
                    if piece == PAWN:
                        san += FILE_NAMES[square_file(move.from_square)]
                    san += "x"

            san += SQUARE_NAMES[move.to_square]

            if move.promotion:
                san += "=" + PIECE_SYMBOLS[move.promotion].upper()  # type: ignore

        # Check / checkmate
        self.push(move)
        try:
            if self.is_check():
                if self.is_checkmate():
                    san += "#"
                else:
                    san += "+"
        finally:
            self.pop()

        return san

    def _disambiguate(self, piece_type: int, move: Move) -> str:
        same_piece_moves = []
        for m in self.generate_legal_moves():
            if (
                m.from_square != move.from_square
                and m.to_square == move.to_square
                and self.piece_type_at(m.from_square) == piece_type
            ):
                same_piece_moves.append(m)

        if not same_piece_moves:
            return ""

        same_file = any(
            square_file(m.from_square) == square_file(move.from_square)
            for m in same_piece_moves
        )
        same_rank = any(
            square_rank(m.from_square) == square_rank(move.from_square)
            for m in same_piece_moves
        )

        if same_file and same_rank:
            return SQUARE_NAMES[move.from_square]
        elif same_file:
            return RANK_NAMES[square_rank(move.from_square)]
        else:
            return FILE_NAMES[square_file(move.from_square)]

    def parse_san(self, san: str) -> Move:
        if san in ("O-O", "O-O+", "O-O#", "0-0", "0-0+", "0-0#"):
            for move in self.generate_castling_moves():
                if self.is_kingside_castling(move) and self.is_legal(move):
                    return move
            raise IllegalMoveError(f"Illegal SAN: {san!r}")

        if san in ("O-O-O", "O-O-O+", "O-O-O#", "0-0-0", "0-0-0+", "0-0-0#"):
            for move in self.generate_castling_moves():
                if self.is_queenside_castling(move) and self.is_legal(move):
                    return move
            raise IllegalMoveError(f"Illegal SAN: {san!r}")

        # Null move
        if san in ("--", "Z0", "0000", "@@@@"):
            return Move.null()

        # Drop move
        if len(san) >= 4 and san[1] == "@":
            drop_symbol = san[0].lower()
            if drop_symbol in PIECE_SYMBOLS and PIECE_SYMBOLS.index(drop_symbol) > 0:
                drop = PIECE_SYMBOLS.index(drop_symbol)
                to_sq = parse_square(san[2:4])
                return Move(to_sq, to_sq, drop=drop)

        # Standard SAN
        match = SAN_REGEX.match(san)
        if not match:
            raise InvalidMoveError(f"Invalid SAN: {san!r}")

        piece_char, from_file, from_rank, to_sq_str, promo_str = match.groups()

        to_sq = parse_square(to_sq_str)
        promotion = None
        if promo_str:
            promo_char = promo_str.lstrip("=").lower()
            if promo_char in PIECE_SYMBOLS:
                promotion = PIECE_SYMBOLS.index(promo_char)

        if piece_char:
            piece_type = PIECE_SYMBOLS.index(piece_char.lower())
        else:
            piece_type = PAWN

        to_mask = BB_SQUARES[to_sq]

        our = self.occupied_co[self.turn]
        piece_bbs = (0, self.pawns, self.knights, self.bishops,
                     self.rooks, self.queens, self.kings)
        from_mask = piece_bbs[piece_type] & our
        if from_file:
            from_mask &= BB_FILES[FILE_NAMES.index(from_file)]
        if from_rank:
            from_mask &= BB_RANKS[int(from_rank) - 1]

        if KNIGHT <= piece_type <= QUEEN:
            candidates = self.attackers_mask(self.turn, to_sq) & from_mask
            if not candidates or BB_SQUARES[to_sq] & our:
                raise IllegalMoveError(f"Illegal SAN: {san!r}")

            king_sq = self.king(self.turn)
            checkers = self.attackers_mask(not self.turn, king_sq) if king_sq is not None else BB_EMPTY

            matched_move = None
            for from_sq in scan_reversed(candidates):
                pin = self.pin_mask(self.turn, from_sq) if king_sq is not None else BB_ALL
                if pin != BB_ALL and not (BB_SQUARES[to_sq] & pin):
                    continue
                if checkers:
                    if popcount(checkers) > 1:
                        continue
                    checker_sq = lsb(checkers)
                    if not (BB_SQUARES[to_sq] & (between(king_sq, checker_sq) | BB_SQUARES[checker_sq])):
                        continue
                if matched_move is not None:
                    raise AmbiguousMoveError(f"Ambiguous SAN: {san!r}")
                matched_move = Move(from_sq, to_sq)
        else:
            matched_move = None
            for move in self.generate_legal_moves(from_mask, to_mask):
                if move.promotion != promotion:
                    continue
                if matched_move is not None:
                    raise AmbiguousMoveError(f"Ambiguous SAN: {san!r}")
                matched_move = move

        if matched_move is None:
            raise IllegalMoveError(f"Illegal SAN: {san!r}")
        return matched_move

    def push_san(self, san: str) -> Move:
        move = self.parse_san(san)
        self.push(move)
        return move

    # ------------------------------------------------------------------
    # UCI notation
    # ------------------------------------------------------------------

    def uci(self, move: Move, *, chess960: typing.Optional[bool] = None) -> str:
        if chess960 is None:
            chess960 = self.chess960
        if self.is_castling(move):
            if chess960:
                king_sq = move.from_square
                if self.chess960:
                    rook_sq = move.to_square
                else:
                    if square_file(move.to_square) > square_file(king_sq):
                        rook_sq = self._find_rook_for_castling(king_sq, kingside=True)
                    else:
                        rook_sq = self._find_rook_for_castling(king_sq, kingside=False)
                    if rook_sq is None:
                        rook_sq = move.to_square
                return Move(king_sq, rook_sq, move.promotion).uci()
            else:
                king_sq = move.from_square
                if self.chess960:
                    rook_sq = move.to_square
                else:
                    rook_sq = move.to_square
                if square_file(rook_sq) > square_file(king_sq):
                    king_to = square(6, square_rank(king_sq))
                else:
                    king_to = square(2, square_rank(king_sq))
                return Move(king_sq, king_to, move.promotion).uci()
        return move.uci()

    def parse_uci(self, uci_str: str) -> Move:
        move = Move.from_uci(uci_str)

        # Handle castling: standard form -> possibly king-takes-rook
        if self.piece_type_at(move.from_square) == KING:
            if not self.chess960 and abs(square_file(move.from_square) - square_file(move.to_square)) > 1:
                # Standard castling notation, find the rook
                if square_file(move.to_square) > square_file(move.from_square):
                    rook_sq = self._find_rook_for_castling(move.from_square, kingside=True)
                else:
                    rook_sq = self._find_rook_for_castling(move.from_square, kingside=False)
                if rook_sq is not None and self.chess960:
                    move = Move(move.from_square, rook_sq)

        if not self.is_pseudo_legal(move):
            raise InvalidMoveError(f"Invalid UCI move: {uci_str!r}")
        if not self.is_legal(move):
            raise IllegalMoveError(f"Illegal UCI move: {uci_str!r}")
        return move

    def push_uci(self, uci_str: str) -> Move:
        move = self.parse_uci(uci_str)
        self.push(move)
        return move

    # XBoard notation
    def xboard(self, move: Move) -> str:
        return self.uci(move, chess960=False)

    def parse_xboard(self, xboard_str: str) -> Move:
        return self.parse_uci(xboard_str)

    def push_xboard(self, xboard_str: str) -> Move:
        return self.push_uci(xboard_str)

    def find_move(
        self,
        from_square: int,
        to_square: int,
        promotion: typing.Optional[int] = None,
    ) -> Move:
        if promotion is None and square_rank(to_square) in (0, 7) and self.piece_type_at(from_square) == PAWN:
            raise InvalidMoveError(
                f"Missing promotion: {SQUARE_NAMES[from_square]}{SQUARE_NAMES[to_square]}"
            )
        move = Move(from_square, to_square, promotion)
        if not self.is_pseudo_legal(move):
            raise InvalidMoveError(
                f"Invalid move: {move.uci()} in {self.fen()}"
            )
        if not self.is_legal(move):
            raise IllegalMoveError(
                f"Illegal move: {move.uci()} in {self.fen()}"
            )
        return move

    # ------------------------------------------------------------------
    # Game-over predicates
    # ------------------------------------------------------------------

    def is_checkmate(self) -> bool:
        if not self.is_check():
            return False
        return not any(self.generate_legal_moves())

    def is_stalemate(self) -> bool:
        if self.is_check():
            return False
        return not any(self.generate_legal_moves())

    def is_insufficient_material(self) -> bool:
        return self.has_insufficient_material(WHITE) and self.has_insufficient_material(BLACK)

    def has_insufficient_material(self, color: bool) -> bool:
        if self.occupied_co[color] & (self.pawns | self.rooks | self.queens):
            return False

        our_non_king = self.occupied_co[color] & ~self.kings
        if not our_non_king:
            return True

        if self.pawns:
            return False

        opp_non_king = self.occupied_co[not color] & ~self.kings

        if our_non_king & self.knights:
            if our_non_king & self.bishops:
                return False
            if popcount(our_non_king) >= 2:
                return False
            return not bool(opp_non_king & ~self.queens)

        if self.knights:
            return False
        if not (self.bishops & BB_DARK_SQUARES) or not (self.bishops & BB_LIGHT_SQUARES):
            return True
        return False

    def is_seventyfive_moves(self) -> bool:
        return self.halfmove_clock >= 150

    def is_fivefold_repetition(self) -> bool:
        return self.is_repetition(5)

    def can_claim_draw(self) -> bool:
        return self.can_claim_fifty_moves() or self.can_claim_threefold_repetition()

    def is_fifty_moves(self) -> bool:
        return self.halfmove_clock >= 100

    def can_claim_fifty_moves(self) -> bool:
        if self.is_fifty_moves():
            if any(self.generate_legal_moves()):
                return True
            return not self.is_checkmate()
        if self.halfmove_clock >= 99:
            for move in self.generate_legal_moves():
                if not self.is_zeroing(move):
                    return True
        return False

    def can_claim_threefold_repetition(self) -> bool:
        if self.is_repetition(3):
            return True
        for move in self.generate_legal_moves():
            self.push(move)
            if self.is_repetition(3):
                self.pop()
                return True
            self.pop()
        return False

    def is_repetition(self, count: int = 3) -> bool:
        maybe_dominated = 0
        for state in reversed(self._stack):
            if (
                state.pawns == self.pawns
                and state.knights == self.knights
                and state.bishops == self.bishops
                and state.rooks == self.rooks
                and state.queens == self.queens
                and state.kings == self.kings
                and state.occupied_co_w == self.occupied_co[WHITE]
                and state.occupied_co_b == self.occupied_co[BLACK]
                and state.turn == self.turn
                and state.castling_rights == self.castling_rights
                and state.ep_square == self.ep_square
            ):
                maybe_dominated += 1
                if maybe_dominated + 1 >= count:
                    return True
            if state.halfmove_clock == 0:
                break
        return False

    def is_game_over(self, *, claim_draw: bool = False) -> bool:
        if self.is_variant_end():
            return True
        if self.is_checkmate() or self.is_stalemate():
            return True
        if self.is_seventyfive_moves() or self.is_fivefold_repetition():
            return True
        if self.is_insufficient_material():
            return True
        if claim_draw:
            return self.can_claim_draw()
        return False

    def result(self, *, claim_draw: bool = False) -> str:
        outcome = self.outcome(claim_draw=claim_draw)
        if outcome is None:
            return "*"
        return outcome.result()

    def outcome(self, *, claim_draw: bool = False) -> typing.Optional[Outcome]:
        if self.is_variant_end():
            if self.is_variant_win():
                return Outcome(Termination.VARIANT_WIN, self.turn)
            if self.is_variant_loss():
                return Outcome(Termination.VARIANT_LOSS, not self.turn)
            if self.is_variant_draw():
                return Outcome(Termination.VARIANT_DRAW, None)
        if self.is_checkmate():
            return Outcome(Termination.CHECKMATE, not self.turn)
        if self.is_stalemate():
            return Outcome(Termination.STALEMATE, None)
        if self.is_insufficient_material():
            return Outcome(Termination.INSUFFICIENT_MATERIAL, None)
        if self.is_seventyfive_moves():
            return Outcome(Termination.SEVENTYFIVE_MOVES, None)
        if self.is_fivefold_repetition():
            return Outcome(Termination.FIVEFOLD_REPETITION, None)
        if claim_draw:
            if self.can_claim_fifty_moves():
                return Outcome(Termination.FIFTY_MOVES, None)
            if self.can_claim_threefold_repetition():
                return Outcome(Termination.THREEFOLD_REPETITION, None)
        return None

    # Variant hooks (standard chess returns False for all)
    def is_variant_end(self) -> bool:
        return False

    def is_variant_win(self) -> bool:
        return False

    def is_variant_loss(self) -> bool:
        return False

    def is_variant_draw(self) -> bool:
        return False

    # ------------------------------------------------------------------
    # Board validity
    # ------------------------------------------------------------------

    def status(self) -> int:
        errors = STATUS_VALID

        if not self.occupied:
            errors |= STATUS_EMPTY

        if popcount(self.occupied_co[WHITE] & self.kings) != 1:
            if not (self.occupied_co[WHITE] & self.kings):
                errors |= STATUS_NO_WHITE_KING
            else:
                errors |= STATUS_TOO_MANY_KINGS
        if popcount(self.occupied_co[BLACK] & self.kings) != 1:
            if not (self.occupied_co[BLACK] & self.kings):
                errors |= STATUS_NO_BLACK_KING
            else:
                errors |= STATUS_TOO_MANY_KINGS

        if popcount(self.occupied_co[WHITE] & self.pawns) > 8:
            errors |= STATUS_TOO_MANY_WHITE_PAWNS
        if popcount(self.occupied_co[BLACK] & self.pawns) > 8:
            errors |= STATUS_TOO_MANY_BLACK_PAWNS

        if self.pawns & BB_BACKRANKS:
            errors |= STATUS_PAWNS_ON_BACKRANK

        if popcount(self.occupied_co[WHITE]) > 16:
            errors |= STATUS_TOO_MANY_WHITE_PIECES
        if popcount(self.occupied_co[BLACK]) > 16:
            errors |= STATUS_TOO_MANY_BLACK_PIECES

        # Castling rights check
        if self.castling_rights:
            # Rights must be on actual rook squares
            if self.castling_rights & ~(self.rooks & (BB_RANK_1 | BB_RANK_8)):
                errors |= STATUS_BAD_CASTLING_RIGHTS

        # EP square check
        if self.ep_square is not None:
            ep_rank = square_rank(self.ep_square)
            if self.turn == WHITE and ep_rank != 5:
                errors |= STATUS_INVALID_EP_SQUARE
            elif self.turn == BLACK and ep_rank != 2:
                errors |= STATUS_INVALID_EP_SQUARE

        # Opposite check
        if self.was_into_check():
            errors |= STATUS_OPPOSITE_CHECK

        # Too many checkers
        checkers = self.checkers_mask()
        checker_count = popcount(checkers)
        if checker_count > 2:
            errors |= STATUS_TOO_MANY_CHECKERS

        # Impossible check (backrank pawns giving check, etc.)
        if checker_count > 0 and errors & STATUS_OPPOSITE_CHECK:
            errors |= STATUS_IMPOSSIBLE_CHECK

        return errors

    def is_valid(self) -> bool:
        return self.status() == STATUS_VALID

    # ------------------------------------------------------------------
    # EPD
    # ------------------------------------------------------------------

    def epd(
        self,
        *,
        shredder: bool = False,
        en_passant: str = "legal",
        promoted: typing.Optional[bool] = None,
        **operations: typing.Any,
    ) -> str:
        epd_str = " ".join([
            self.board_fen(promoted=bool(promoted)),
            "w" if self.turn == WHITE else "b",
            self.castling_shredder_fen() if shredder else self.castling_xfen(),
            SQUARE_NAMES[self.ep_square] if self.ep_square is not None and (
                en_passant == "fen" or (self.has_legal_en_passant() if en_passant == "legal" else True)
            ) else "-",
        ])

        for opcode, operand in operations.items():
            epd_str += " " + self._format_epd_operand(opcode, operand)

        return epd_str

    def _format_epd_operand(self, opcode: str, operand: typing.Any) -> str:
        if operand is None:
            return f"{opcode};"
        if isinstance(operand, Move):
            return f"{opcode} {self.san(operand)};"
        if isinstance(operand, int):
            return f"{opcode} {operand};"
        if isinstance(operand, float):
            return f"{opcode} {operand};"
        if isinstance(operand, list):
            # List of moves
            sans = " ".join(self.san(m) for m in operand)
            return f"{opcode} {sans};"
        # String
        escaped = str(operand).replace("\\", "\\\\").replace('"', '\\"')
        return f'{opcode} "{escaped}";'

    def set_epd(self, epd: str) -> typing.Dict[str, typing.Any]:
        parts = epd.strip().rstrip(";").split(None, 4)
        if len(parts) < 4:
            raise ValueError(f"Invalid EPD: {epd!r}")

        # Set position
        self.set_board_fen(parts[0])
        self.turn = WHITE if parts[1] == "w" else BLACK
        self.set_castling_fen(parts[2])
        if parts[3] == "-":
            self.ep_square = None
        else:
            self.ep_square = parse_square(parts[3])
        self.halfmove_clock = 0
        self.fullmove_number = 1
        self.clear_stack()

        # Parse operations
        operations: typing.Dict[str, typing.Any] = {}
        if len(parts) > 4:
            ops_str = parts[4]
            # Simple parsing of EPD operations
            for op in ops_str.split(";"):
                op = op.strip()
                if not op:
                    continue
                tokens = op.split(None, 1)
                opcode = tokens[0]
                if len(tokens) == 1:
                    operations[opcode] = None
                else:
                    operand = tokens[1].strip()
                    if operand.startswith('"') and operand.endswith('"'):
                        operations[opcode] = operand[1:-1].replace('\\"', '"').replace("\\\\", "\\")
                    else:
                        # Try int, float, move list
                        try:
                            operations[opcode] = int(operand)
                        except ValueError:
                            try:
                                operations[opcode] = float(operand)
                            except ValueError:
                                # Try as move(s)
                                try:
                                    moves = []
                                    for san_str in operand.split():
                                        moves.append(self.parse_san(san_str))
                                    if len(moves) == 1:
                                        operations[opcode] = moves[0]
                                    else:
                                        operations[opcode] = moves
                                except (ValueError, IllegalMoveError):
                                    operations[opcode] = operand

        return operations

    @classmethod
    def from_epd(cls, epd: str, *, chess960: bool = False) -> typing.Tuple[Board, typing.Dict[str, typing.Any]]:
        board = cls(None, chess960=chess960)
        ops = board.set_epd(epd)
        return board, ops

    # ------------------------------------------------------------------
    # Transforms
    # ------------------------------------------------------------------

    def apply_mirror(self) -> None:
        super().apply_mirror()
        self.turn = not self.turn
        # Mirror castling rights
        self.castling_rights = flip_vertical(self.castling_rights)
        # Mirror EP square
        if self.ep_square is not None:
            self.ep_square = square_mirror(self.ep_square)
        self.clear_stack()

    def mirror(self) -> Board:
        board = self.copy(stack=False)
        board.apply_mirror()
        return board

    # ------------------------------------------------------------------
    # Move generators as objects
    # ------------------------------------------------------------------

    @property
    def legal_moves(self) -> LegalMoveGenerator:
        return LegalMoveGenerator(self)

    @property
    def pseudo_legal_moves(self) -> PseudoLegalMoveGenerator:
        return PseudoLegalMoveGenerator(self)

    # ------------------------------------------------------------------
    # Copy
    # ------------------------------------------------------------------

    def copy(self, *, stack: typing.Union[bool, int] = True) -> Board:
        board = Board(None, chess960=self.chess960)
        board.pawns = self.pawns
        board.knights = self.knights
        board.bishops = self.bishops
        board.rooks = self.rooks
        board.queens = self.queens
        board.kings = self.kings
        board.occupied_co = list(self.occupied_co)
        board.occupied = self.occupied
        board.promoted = self.promoted
        board.turn = self.turn
        board.castling_rights = self.castling_rights
        board.ep_square = self.ep_square
        board.halfmove_clock = self.halfmove_clock
        board.fullmove_number = self.fullmove_number

        if stack is True:
            board.move_stack = list(self.move_stack)
            board._stack = [s.copy() for s in self._stack]
        elif stack is False or stack == 0:
            board.move_stack = []
            board._stack = []
        else:
            board.move_stack = list(self.move_stack[-stack:])
            board._stack = [s.copy() for s in self._stack[-stack:]]

        return board

    def __copy__(self) -> Board:
        return self.copy()

    def __deepcopy__(self, memo: typing.Dict[int, typing.Any]) -> Board:
        return self.copy()

    @classmethod
    def empty(cls, *, chess960: bool = False) -> Board:
        return cls(None, chess960=chess960)

    @classmethod
    def from_chess960_pos(cls, scharnagl: int) -> Board:
        board = cls(None, chess960=True)
        board.set_chess960_pos(scharnagl)
        # Set castling rights for all rooks
        board.castling_rights = board.rooks & (BB_RANK_1 | BB_RANK_8)
        return board

    def __eq__(self, other: object) -> bool:
        if isinstance(other, Board):
            return (
                super().__eq__(other)
                and self.turn == other.turn
                and self.castling_rights == other.castling_rights
                and self.ep_square == other.ep_square
            )
        return NotImplemented

    def __repr__(self) -> str:
        return f"{type(self).__name__}({self.fen()!r})"

    def __str__(self) -> str:
        return super().__str__()


# ======================================================================
# Board state for push/pop
# ======================================================================

class _BoardState:
    __slots__ = (
        "pawns", "knights", "bishops", "rooks", "queens", "kings",
        "occupied_co_w", "occupied_co_b", "occupied", "promoted",
        "turn", "castling_rights", "ep_square",
        "halfmove_clock", "fullmove_number",
    )

    def __init__(self, board: Board) -> None:
        self.pawns = board.pawns
        self.knights = board.knights
        self.bishops = board.bishops
        self.rooks = board.rooks
        self.queens = board.queens
        self.kings = board.kings
        self.occupied_co_w = board.occupied_co[WHITE]
        self.occupied_co_b = board.occupied_co[BLACK]
        self.occupied = board.occupied
        self.promoted = board.promoted
        self.turn = board.turn
        self.castling_rights = board.castling_rights
        self.ep_square = board.ep_square
        self.halfmove_clock = board.halfmove_clock
        self.fullmove_number = board.fullmove_number

    def restore(self, board: Board) -> None:
        board.pawns = self.pawns
        board.knights = self.knights
        board.bishops = self.bishops
        board.rooks = self.rooks
        board.queens = self.queens
        board.kings = self.kings
        board.occupied_co[WHITE] = self.occupied_co_w
        board.occupied_co[BLACK] = self.occupied_co_b
        board.occupied = self.occupied
        board.promoted = self.promoted
        board.turn = self.turn
        board.castling_rights = self.castling_rights
        board.ep_square = self.ep_square
        board.halfmove_clock = self.halfmove_clock
        board.fullmove_number = self.fullmove_number

    def copy(self) -> _BoardState:
        s = object.__new__(_BoardState)
        s.pawns = self.pawns
        s.knights = self.knights
        s.bishops = self.bishops
        s.rooks = self.rooks
        s.queens = self.queens
        s.kings = self.kings
        s.occupied_co_w = self.occupied_co_w
        s.occupied_co_b = self.occupied_co_b
        s.occupied = self.occupied
        s.promoted = self.promoted
        s.turn = self.turn
        s.castling_rights = self.castling_rights
        s.ep_square = self.ep_square
        s.halfmove_clock = self.halfmove_clock
        s.fullmove_number = self.fullmove_number
        return s


# ======================================================================
# Move generators
# ======================================================================

class LegalMoveGenerator:
    def __init__(self, board: Board) -> None:
        self.board = board

    def __iter__(self) -> typing.Iterator[Move]:
        return self.board.generate_legal_moves()

    def __contains__(self, move: object) -> bool:
        if isinstance(move, Move):
            return self.board.is_legal(move)
        return False

    def __len__(self) -> int:
        return sum(1 for _ in self)

    def count(self) -> int:
        return sum(1 for _ in self)

    def __bool__(self) -> bool:
        return any(self.board.generate_legal_moves())

    def __repr__(self) -> str:
        sans = ", ".join(self.board.san(m) for m in self)
        return f"<LegalMoveGenerator at {id(self):#x} ({sans})>"

    def __str__(self) -> str:
        return ", ".join(self.board.san(m) for m in self)


class PseudoLegalMoveGenerator:
    def __init__(self, board: Board) -> None:
        self.board = board

    def __iter__(self) -> typing.Iterator[Move]:
        return self.board.generate_pseudo_legal_moves()

    def __contains__(self, move: object) -> bool:
        if isinstance(move, Move):
            return self.board.is_pseudo_legal(move)
        return False

    def __len__(self) -> int:
        return sum(1 for _ in self)

    def count(self) -> int:
        return sum(1 for _ in self)

    def __bool__(self) -> bool:
        return any(self.board.generate_pseudo_legal_moves())

    def __repr__(self) -> str:
        sans: typing.List[str] = []
        for m in self:
            try:
                sans.append(self.board.san(m))
            except Exception:
                sans.append(m.uci())
        return f"<PseudoLegalMoveGenerator at {id(self):#x} ({', '.join(sans)})>"


# ======================================================================
# Helpers
# ======================================================================

def _between_incl(a: int, b: int) -> int:
    """Between a and b, inclusive of both endpoints."""
    if a == b:
        return BB_SQUARES[a]
    return between(a, b) | BB_SQUARES[a] | BB_SQUARES[b]
