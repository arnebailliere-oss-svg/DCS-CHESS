"""Chess variant boards: Suicide, Atomic, KotH, Racing Kings, Horde, Three-Check, Crazyhouse."""

from __future__ import annotations

__all__ = [
    "AntichessBoard", "AtomicBoard", "CrazyhouseBoard", "CrazyhouseBoardT",
    "CrazyhousePocket", "CrazyhousePocketT", "GiveawayBoard", "HordeBoard",
    "KingOfTheHillBoard", "RacingKingsBoard", "SuicideBoard",
    "ThreeCheckBoard", "ThreeCheckBoardT", "VARIANTS", "find_variant",
]

import itertools
import typing
from typing import Dict, Generic, Hashable, Iterable, Iterator, List, Optional, Type, TypeVar, Union

from dcs_chess.core.constants import (
    WHITE, BLACK, COLORS,
    PAWN, KNIGHT, BISHOP, ROOK, QUEEN, KING, PIECE_TYPES,
    BB_EMPTY, BB_ALL,
    BB_A1, BB_E1, BB_H1, BB_A8, BB_E8, BB_H8,
    BB_RANK_1, BB_RANK_2, BB_RANK_3, BB_RANK_6, BB_RANK_7, BB_RANK_8,
    BB_FILE_A, BB_FILE_H,
    BB_CENTER,
    BB_SQUARES,
    SQUARES,
    SQUARE_NAMES,
    FILE_NAMES, RANK_NAMES,
    STARTING_FEN,
    STATUS_VALID,
    STATUS_NO_WHITE_KING, STATUS_NO_BLACK_KING,
    STATUS_TOO_MANY_KINGS,
    STATUS_TOO_MANY_WHITE_PAWNS, STATUS_TOO_MANY_BLACK_PAWNS,
    STATUS_PAWNS_ON_BACKRANK,
    STATUS_TOO_MANY_WHITE_PIECES, STATUS_TOO_MANY_BLACK_PIECES,
    STATUS_BAD_CASTLING_RIGHTS, STATUS_INVALID_EP_SQUARE,
    STATUS_OPPOSITE_CHECK, STATUS_EMPTY,
    STATUS_RACE_CHECK, STATUS_RACE_OVER, STATUS_RACE_MATERIAL,
    STATUS_TOO_MANY_CHECKERS, STATUS_IMPOSSIBLE_CHECK,
    BB_KING_ATTACKS, BB_KNIGHT_ATTACKS, BB_PAWN_ATTACKS,
    A1, B1, C1, D1, E1, F1, G1, H1,
    A8, B8, C8, D8, E8, F8, G8, H8,
    D4, E4, D5, E5,
)
from dcs_chess.core.piece import Piece
from dcs_chess.core.move import Move
from dcs_chess.core.baseboard import BaseBoard
from dcs_chess.core.board import Board, _BoardState
from dcs_chess.core.status import Outcome, Termination
from dcs_chess.core.functions import (
    popcount, scan_forward, scan_reversed, msb, lsb,
    square_file, square_rank, square_distance, square_mirror,
    shift_up, between,
)
from dcs_chess.core.squareset import SquareSet


# =========================================================================
# King of the Hill
# =========================================================================

class KingOfTheHillBoard(Board):

    aliases: List[str] = ["King of the Hill", "KOTH", "kingOfTheHill"]
    uci_variant: Optional[str] = "kingofthehill"
    xboard_variant: Optional[str] = "kingofthehill"
    starting_fen: str = STARTING_FEN

    tbw_suffix: Optional[str] = None
    tbz_suffix: Optional[str] = None

    def is_variant_end(self) -> bool:
        return bool(self.kings & self.occupied_co[WHITE] & BB_CENTER) or \
               bool(self.kings & self.occupied_co[BLACK] & BB_CENTER)

    def is_variant_win(self) -> bool:
        return bool(self.kings & self.occupied_co[self.turn] & BB_CENTER)

    def is_variant_loss(self) -> bool:
        return bool(self.kings & self.occupied_co[not self.turn] & BB_CENTER)

    def generate_legal_moves(self, from_mask=BB_ALL, to_mask=BB_ALL):
        if self.is_variant_end():
            return
        yield from super().generate_legal_moves(from_mask, to_mask)

    def has_insufficient_material(self, color: bool) -> bool:
        return False


# =========================================================================
# Suicide / Giveaway / Antichess
# =========================================================================

class SuicideBoard(Board):

    aliases: List[str] = ["Suicide", "Suicide chess"]
    uci_variant: Optional[str] = "suicide"
    xboard_variant: Optional[str] = "suicide"
    starting_fen: str = STARTING_FEN

    tbw_suffix: Optional[str] = ".stbw"
    tbz_suffix: Optional[str] = ".stbz"

    def _promote(self, from_sq: int, to_sq: int) -> Iterator[Move]:
        yield Move(from_sq, to_sq, promotion=QUEEN)
        yield Move(from_sq, to_sq, promotion=ROOK)
        yield Move(from_sq, to_sq, promotion=BISHOP)
        yield Move(from_sq, to_sq, promotion=KNIGHT)
        yield Move(from_sq, to_sq, promotion=KING)

    def _is_pseudo_legal_pawn(self, move: Move) -> bool:
        if move.promotion == KING:
            to_bb = BB_SQUARES[move.to_square]
            if self.turn == WHITE:
                promo_rank = 7
            else:
                promo_rank = 0
            if square_rank(move.to_square) != promo_rank:
                return False
            if to_bb & self.occupied_co[not self.turn]:
                return bool(BB_PAWN_ATTACKS[self.turn][move.from_square] & to_bb)
            if move.to_square == self.ep_square:
                return bool(BB_PAWN_ATTACKS[self.turn][move.from_square] & to_bb)
            diff = move.to_square - move.from_square
            single = 8 if self.turn == WHITE else -8
            if diff == single and not (self.occupied & to_bb):
                return True
            return False
        return super()._is_pseudo_legal_pawn(move)

    def pin_mask(self, color: bool, square: int) -> int:
        return BB_ALL

    def checkers_mask(self) -> int:
        return BB_EMPTY

    def gives_check(self, move: Move) -> bool:
        return False

    def is_into_check(self, move: Move) -> bool:
        return False

    def was_into_check(self) -> bool:
        return False

    def _attacked_for_king(self, path: int, occupied: int) -> bool:
        return False

    def push(self, move: Move) -> None:
        piece = self.piece_type_at(move.from_square)
        backrank = BB_RANK_1 if self.turn == WHITE else BB_RANK_8
        if piece == KING and not (BB_SQUARES[move.from_square] & backrank):
            saved_backrank = self.castling_rights & backrank
            super().push(move)
            self.castling_rights |= saved_backrank
        else:
            super().push(move)

    def generate_pseudo_legal_moves(
        self,
        from_mask: int = BB_ALL,
        to_mask: int = BB_ALL,
    ) -> Iterator[Move]:
        pseudo = list(super().generate_pseudo_legal_moves(from_mask, to_mask))
        our_pieces = self.occupied_co[self.turn]
        primary_king = self.king(self.turn)
        extra_kings = self.kings & our_pieces & from_mask
        if primary_king is not None:
            extra_kings &= ~BB_SQUARES[primary_king]
        for king_sq in scan_reversed(extra_kings):
            targets = BB_KING_ATTACKS[king_sq] & ~our_pieces & to_mask
            for to_sq in scan_reversed(targets):
                pseudo.append(Move(king_sq, to_sq))
        captures = [m for m in pseudo if self.is_capture(m)]
        if captures:
            yield from captures
        else:
            yield from pseudo

    def generate_legal_moves(
        self,
        from_mask: int = BB_ALL,
        to_mask: int = BB_ALL,
    ) -> Iterator[Move]:
        return self.generate_pseudo_legal_moves(from_mask, to_mask)

    def is_legal(self, move: Move) -> bool:
        return move in self.generate_pseudo_legal_moves()

    def is_variant_end(self) -> bool:
        return not bool(self.occupied_co[WHITE]) or not bool(self.occupied_co[BLACK])

    def is_variant_win(self) -> bool:
        if not self.occupied_co[self.turn]:
            return True
        return self.is_stalemate() and self._material_balance() < 0

    def is_variant_loss(self) -> bool:
        if not self.occupied_co[self.turn]:
            return False
        return self.is_stalemate() and self._material_balance() > 0

    def is_variant_draw(self) -> bool:
        if not self.occupied_co[self.turn]:
            return False
        return self.is_stalemate() and self._material_balance() == 0

    def outcome(self, *, claim_draw: bool = False) -> typing.Optional[Outcome]:
        if self.is_variant_win():
            return Outcome(Termination.VARIANT_WIN, self.turn)
        if self.is_variant_loss():
            return Outcome(Termination.VARIANT_LOSS, not self.turn)
        if self.is_variant_draw():
            return Outcome(Termination.VARIANT_DRAW, None)
        return super().outcome(claim_draw=claim_draw)

    def _material_balance(self) -> int:
        return popcount(self.occupied_co[self.turn]) - popcount(self.occupied_co[not self.turn])

    def has_insufficient_material(self, color: bool) -> bool:
        if not self.occupied_co[color]:
            return False
        if self.pawns or self.knights or self.rooks or self.queens or self.kings:
            return False
        our_bishops = self.bishops & self.occupied_co[color]
        their_bishops = self.bishops & self.occupied_co[not color]
        if not our_bishops or not their_bishops:
            return not bool(self.occupied_co[not color])
        our_light = 0
        our_dark = 0
        for sq in scan_forward(our_bishops):
            if (square_file(sq) + square_rank(sq)) % 2:
                our_light += 1
            else:
                our_dark += 1
        their_light = 0
        their_dark = 0
        for sq in scan_forward(their_bishops):
            if (square_file(sq) + square_rank(sq)) % 2:
                their_light += 1
            else:
                their_dark += 1
        if our_light and their_light:
            return False
        if our_dark and their_dark:
            return False
        return True

    def status(self) -> int:
        errors = STATUS_VALID
        if not self.occupied:
            errors |= STATUS_EMPTY
        if popcount(self.pawns & self.occupied_co[WHITE]) > 8:
            errors |= STATUS_TOO_MANY_WHITE_PAWNS
        if popcount(self.pawns & self.occupied_co[BLACK]) > 8:
            errors |= STATUS_TOO_MANY_BLACK_PAWNS
        if self.pawns & (BB_RANK_1 | BB_RANK_8):
            errors |= STATUS_PAWNS_ON_BACKRANK
        return errors

    def _transposition_key(self) -> Hashable:
        return (super()._transposition_key(), self._material_balance())


class GiveawayBoard(SuicideBoard):

    aliases: List[str] = ["Giveaway", "Giveaway chess", "Give away", "Give away chess"]
    uci_variant: Optional[str] = "giveaway"
    xboard_variant: Optional[str] = "giveaway"

    tbw_suffix: Optional[str] = ".gtbw"
    tbz_suffix: Optional[str] = ".gtbz"

    def is_variant_win(self) -> bool:
        if not self.occupied_co[self.turn]:
            return True
        if not any(self.generate_legal_moves()):
            return True
        return False

    def is_variant_loss(self) -> bool:
        if not self.occupied_co[not self.turn]:
            return True
        return False

    def is_variant_draw(self) -> bool:
        return False


class AntichessBoard(GiveawayBoard):

    aliases: List[str] = ["Antichess", "Anti chess", "Anti"]
    uci_variant: Optional[str] = "antichess"
    xboard_variant: Optional[str] = "giveaway"
    starting_fen: str = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w - - 0 1"

    def reset(self) -> None:
        super().reset()
        self.castling_rights = BB_EMPTY


# =========================================================================
# Atomic
# =========================================================================

class AtomicBoard(Board):

    aliases: List[str] = ["Atomic", "Atom", "Atomic chess"]
    uci_variant: Optional[str] = "atomic"
    xboard_variant: Optional[str] = "atomic"
    starting_fen: str = STARTING_FEN

    tbw_suffix: Optional[str] = ".atbw"
    tbz_suffix: Optional[str] = ".atbz"

    def _kings_connected(self) -> bool:
        white_king_sq = self.king(WHITE)
        black_king_sq = self.king(BLACK)
        if white_king_sq is None or black_king_sq is None:
            return False
        return bool(BB_KING_ATTACKS[white_king_sq] & BB_SQUARES[black_king_sq])

    def _attacked_for_king(self, path: int, occupied: int) -> bool:
        if self._kings_connected():
            return False
        return super()._attacked_for_king(path, occupied)

    def checkers_mask(self) -> int:
        if self._kings_connected():
            return BB_EMPTY
        return super().checkers_mask()

    def is_into_check(self, move: Move) -> bool:
        self.push(move)
        try:
            was = self.was_into_check()
        finally:
            self.pop()
        return was

    def was_into_check(self) -> bool:
        king_sq = self.king(not self.turn)
        if king_sq is None:
            return False
        if self._kings_connected():
            return False
        return super().was_into_check()

    def is_legal(self, move: Move) -> bool:
        if self.is_capture(move):
            return move in self.generate_pseudo_legal_moves() and \
                   not self._is_atomic_illegal(move)
        return super().is_legal(move)

    def _is_atomic_illegal(self, move: Move) -> bool:
        self.push(move)
        try:
            own_king = self.king(not self.turn)
            if own_king is None:
                return True
            opp_king = self.king(self.turn)
            if opp_king is None:
                return False
            if self._kings_connected():
                return False
            return self.was_into_check()
        finally:
            self.pop()

    def generate_legal_moves(
        self,
        from_mask: int = BB_ALL,
        to_mask: int = BB_ALL,
    ) -> Iterator[Move]:
        if self.is_variant_end():
            return
        for move in self.generate_pseudo_legal_moves(from_mask, to_mask):
            if self.is_capture(move):
                if not self._is_atomic_illegal(move):
                    yield move
            elif not self.is_into_check(move):
                yield move

    def generate_legal_ep(
        self,
        from_mask: int = BB_ALL,
        to_mask: int = BB_ALL,
    ) -> Iterator[Move]:
        for move in self.generate_pseudo_legal_ep(from_mask, to_mask):
            if not self._is_atomic_illegal(move):
                yield move

    def push(self, move: Move) -> None:
        was_capture = self.is_capture(move)
        capture_square = move.to_square
        if self.is_en_passant(move):
            if self.turn == WHITE:
                capture_square = move.to_square - 8
            else:
                capture_square = move.to_square + 8
        super().push(move)
        if was_capture:
            explosion_mask = BB_KING_ATTACKS[move.to_square] & ~self.pawns
            explosion_mask |= BB_SQUARES[capture_square]
            explosion_mask |= BB_SQUARES[move.to_square]
            for sq in scan_forward(explosion_mask):
                self.remove_piece_at(sq)
            self.castling_rights &= ~explosion_mask
            self.occupied = self.occupied_co[WHITE] | self.occupied_co[BLACK]

    def is_stalemate(self) -> bool:
        if self.is_variant_end():
            return False
        if self.is_check():
            return False
        return not any(self.generate_legal_moves())

    def is_variant_end(self) -> bool:
        return not bool(self.kings & self.occupied_co[WHITE]) or \
               not bool(self.kings & self.occupied_co[BLACK])

    def is_variant_win(self) -> bool:
        return bool(self.kings & self.occupied_co[self.turn]) and \
               not bool(self.kings & self.occupied_co[not self.turn])

    def is_variant_loss(self) -> bool:
        return not bool(self.kings & self.occupied_co[self.turn]) and \
               bool(self.kings & self.occupied_co[not self.turn])

    def has_insufficient_material(self, color: bool) -> bool:
        if self.occupied_co[color] & (self.pawns | self.knights | self.rooks | self.queens):
            return False
        if not (self.occupied_co[color] & self.bishops):
            return popcount(self.occupied_co[color]) == 1
        own_bishops = self.bishops & self.occupied_co[color]
        opp_bishops = self.bishops & self.occupied_co[not color]
        if not opp_bishops:
            return False
        own_light = own_bishops & 0x55AA55AA55AA55AA
        own_dark = own_bishops & 0xAA55AA55AA55AA55
        opp_light = opp_bishops & 0x55AA55AA55AA55AA
        opp_dark = opp_bishops & 0xAA55AA55AA55AA55
        if own_light and own_dark:
            return False
        if (own_light and opp_dark) or (own_dark and opp_light):
            return False
        return self.occupied_co[color] == (self.kings & self.occupied_co[color]) | own_bishops and \
               self.occupied_co[not color] == (self.kings & self.occupied_co[not color]) | opp_bishops

    def status(self) -> int:
        errors = super().status()
        if self.is_variant_end() and not (errors & STATUS_EMPTY):
            if not (self.kings & self.occupied_co[WHITE]):
                errors &= ~STATUS_NO_WHITE_KING
            if not (self.kings & self.occupied_co[BLACK]):
                errors &= ~STATUS_NO_BLACK_KING
        return errors


# =========================================================================
# Racing Kings
# =========================================================================

class RacingKingsBoard(Board):

    aliases: List[str] = ["Racing Kings", "Racing", "Race", "racingkings"]
    uci_variant: Optional[str] = "racingkings"
    xboard_variant: Optional[str] = "racingkings"
    starting_fen: str = "8/8/8/8/8/8/krbnNBRK/qrbnNBRQ w - - 0 1"

    tbw_suffix: Optional[str] = None
    tbz_suffix: Optional[str] = None

    def reset(self) -> None:
        self.set_fen(type(self).starting_fen)

    def is_legal(self, move: Move) -> bool:
        if not super().is_legal(move):
            return False
        self.push(move)
        try:
            if self.is_check():
                return False
            if self.was_into_check():
                return False
        finally:
            self.pop()
        return True

    def generate_legal_moves(
        self,
        from_mask: int = BB_ALL,
        to_mask: int = BB_ALL,
    ) -> Iterator[Move]:
        if self.is_variant_end():
            return
        for move in super().generate_legal_moves(from_mask, to_mask):
            self.push(move)
            try:
                if not self.is_check():
                    yield move
            finally:
                self.pop()

    def is_variant_end(self) -> bool:
        if self.kings & self.occupied_co[BLACK] & BB_RANK_8:
            return True
        if not (self.kings & self.occupied_co[WHITE] & BB_RANK_8):
            return False
        if self.turn == WHITE:
            return True
        return not bool(self.kings & self.occupied_co[BLACK] & BB_RANK_7)

    def is_variant_win(self) -> bool:
        if not self.is_variant_end():
            return False
        wk = self.king(WHITE)
        bk = self.king(BLACK)
        if wk is None or bk is None:
            return False
        w_on_8 = square_rank(wk) == 7
        b_on_8 = square_rank(bk) == 7
        if self.turn == WHITE:
            return w_on_8 and not b_on_8
        else:
            return b_on_8 and not w_on_8

    def is_variant_loss(self) -> bool:
        if not self.is_variant_end():
            return False
        wk = self.king(WHITE)
        bk = self.king(BLACK)
        if wk is None or bk is None:
            return False
        w_on_8 = square_rank(wk) == 7
        b_on_8 = square_rank(bk) == 7
        if self.turn == WHITE:
            return not w_on_8 and b_on_8
        else:
            return w_on_8 and not b_on_8

    def is_variant_draw(self) -> bool:
        if not self.is_variant_end():
            return False
        wk = self.king(WHITE)
        bk = self.king(BLACK)
        if wk is None or bk is None:
            return False
        return square_rank(wk) == 7 and square_rank(bk) == 7

    def has_insufficient_material(self, color: bool) -> bool:
        return False

    def status(self) -> int:
        errors = super().status()
        if self.is_check():
            errors |= STATUS_RACE_CHECK
        if self.kings & self.occupied_co[WHITE] & BB_RANK_8:
            if self.turn == WHITE or (self.kings & self.occupied_co[BLACK] & BB_RANK_8):
                errors |= STATUS_RACE_OVER
        if popcount(self.occupied) < 2:
            errors |= STATUS_RACE_MATERIAL
        return errors


# =========================================================================
# Horde
# =========================================================================

class HordeBoard(Board):

    aliases: List[str] = ["Horde", "Horde chess"]
    uci_variant: Optional[str] = "horde"
    xboard_variant: Optional[str] = "horde"
    starting_fen: str = "rnbqkbnr/pppppppp/8/1PP2PP1/PPPPPPPP/PPPPPPPP/PPPPPPPP/PPPPPPPP w kq - 0 1"

    tbw_suffix: Optional[str] = None
    tbz_suffix: Optional[str] = None

    def reset(self) -> None:
        self.set_fen(type(self).starting_fen)

    def generate_pseudo_legal_moves(
        self,
        from_mask: int = BB_ALL,
        to_mask: int = BB_ALL,
    ) -> Iterator[Move]:
        yield from super().generate_pseudo_legal_moves(from_mask, to_mask)
        if self.turn == WHITE:
            our_pawns = self.pawns & self.occupied_co[WHITE] & from_mask & BB_RANK_1
            if our_pawns:
                single = shift_up(our_pawns) & ~self.occupied
                double = shift_up(single) & ~self.occupied & BB_RANK_3 & to_mask
                for to_sq in scan_reversed(double):
                    yield Move(to_sq - 16, to_sq)

    def is_pseudo_legal(self, move: Move) -> bool:
        if (self.turn == WHITE and
            self.piece_type_at(move.from_square) == PAWN and
            not move.promotion and
            square_rank(move.from_square) == 0 and
            move.to_square - move.from_square == 16):
            mid = move.from_square + 8
            return (not (self.occupied & BB_SQUARES[mid]) and
                    not (self.occupied & BB_SQUARES[move.to_square]))
        return super().is_pseudo_legal(move)

    def push(self, move: Move) -> None:
        super().push(move)
        if (self.ep_square is not None and
            move.to_square - move.from_square == 16 and
            square_rank(move.from_square) == 0):
            self.ep_square = None

    def is_variant_end(self) -> bool:
        return not bool(self.occupied_co[WHITE])

    def is_variant_win(self) -> bool:
        if self.occupied_co[WHITE]:
            return False
        return self.turn == BLACK

    def is_variant_loss(self) -> bool:
        if self.occupied_co[WHITE]:
            return False
        return self.turn == WHITE

    def is_variant_draw(self) -> bool:
        return False

    def has_insufficient_material(self, color: bool) -> bool:
        if color == WHITE:
            return not bool(self.occupied_co[WHITE])
        return super().has_insufficient_material(color)

    def status(self) -> int:
        status = super().status()
        status &= ~STATUS_NO_WHITE_KING
        if popcount(self.occupied_co[WHITE]) <= 36:
            status &= ~STATUS_TOO_MANY_WHITE_PIECES
            status &= ~STATUS_TOO_MANY_WHITE_PAWNS
        if not self.pawns & BB_RANK_8 and not self.occupied_co[BLACK] & self.pawns & BB_RANK_1:
            status &= ~STATUS_PAWNS_ON_BACKRANK
        if self.occupied_co[WHITE] & self.kings:
            status |= STATUS_TOO_MANY_KINGS
        return status


# =========================================================================
# Three-Check
# =========================================================================

ThreeCheckBoardT = TypeVar("ThreeCheckBoardT", bound="ThreeCheckBoard")


class ThreeCheckBoard(Board):

    aliases: List[str] = [
        "Three-check", "Three check", "Threecheck",
        "Three check chess", "3-check", "3 check", "3check",
    ]
    uci_variant: Optional[str] = "3check"
    xboard_variant: Optional[str] = "3check"
    starting_fen: str = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 3+3 0 1"

    tbw_suffix: Optional[str] = None
    tbz_suffix: Optional[str] = None

    def __init__(
        self,
        fen: Optional[str] = None,
        *,
        chess960: bool = False,
    ) -> None:
        self.remaining_checks = [3, 3]
        if fen is None:
            super().__init__(type(self).starting_fen, chess960=chess960)
        else:
            super().__init__(fen, chess960=chess960)

    def reset_board(self) -> None:
        super().reset_board()
        self.remaining_checks = [3, 3]

    def clear_board(self) -> None:
        super().clear_board()
        self.remaining_checks = [3, 3]

    def push(self, move: Move) -> None:
        super().push(move)
        if self.is_check():
            self.remaining_checks[not self.turn] -= 1

    def pop(self) -> Move:
        was_check = self.is_check()
        move = super().pop()
        if was_check:
            self.remaining_checks[self.turn] += 1
        return move

    def has_insufficient_material(self, color: bool) -> bool:
        return self.occupied == (self.kings & self.occupied)

    def set_fen(self, fen: str) -> None:
        parts = fen.split()
        if len(parts) >= 5:
            check_part = parts[4]
            if "+" in check_part:
                check_counts = check_part.split("+")
                if len(check_counts) == 2:
                    try:
                        self.remaining_checks = [int(check_counts[0]), int(check_counts[1])]
                    except ValueError:
                        self.remaining_checks = [3, 3]
                    new_parts = parts[:4] + parts[5:]
                    fen = " ".join(new_parts)
        super().set_fen(fen)

    def fen(
        self,
        *,
        shredder: bool = False,
        en_passant: str = "legal",
        promoted: typing.Optional[bool] = None,
    ) -> str:
        base = super().fen(shredder=shredder, en_passant=en_passant, promoted=promoted)
        parts = base.split()
        checks = f"{self.remaining_checks[WHITE]}+{self.remaining_checks[BLACK]}"
        parts.insert(4, checks)
        return " ".join(parts)

    def epd(
        self,
        *,
        shredder: bool = False,
        en_passant: str = "legal",
        promoted: typing.Optional[bool] = None,
        **operations: typing.Union[None, str, int, float, Move, typing.List[Move]],
    ) -> str:
        epd = super().epd(shredder=shredder, en_passant=en_passant, promoted=promoted, **operations)
        return epd

    def is_variant_end(self) -> bool:
        return any(c <= 0 for c in self.remaining_checks)

    def is_variant_win(self) -> bool:
        return self.remaining_checks[self.turn] <= 0 < self.remaining_checks[not self.turn]

    def is_variant_loss(self) -> bool:
        return self.remaining_checks[not self.turn] <= 0 < self.remaining_checks[self.turn]

    def is_variant_draw(self) -> bool:
        return self.remaining_checks[WHITE] <= 0 and self.remaining_checks[BLACK] <= 0

    def generate_legal_moves(self, from_mask=BB_ALL, to_mask=BB_ALL):
        if self.is_variant_end():
            return
        yield from super().generate_legal_moves(from_mask, to_mask)

    def is_irreversible(self, move: Move) -> bool:
        return super().is_irreversible(move) or self.gives_check(move)

    def _transposition_key(self) -> Hashable:
        return (super()._transposition_key(), tuple(self.remaining_checks))

    def copy(self, *, stack: typing.Union[bool, int] = True) -> ThreeCheckBoard:
        board = super().copy(stack=stack)
        board.__class__ = type(self)
        board.remaining_checks = list(self.remaining_checks)
        return board  # type: ignore[return-value]

    def mirror(self) -> ThreeCheckBoard:
        board = super().mirror()
        board.remaining_checks = list(reversed(self.remaining_checks))
        return board  # type: ignore[return-value]

    def clear_stack(self) -> None:
        super().clear_stack()

    def root(self) -> ThreeCheckBoard:
        root = super().root()
        root.remaining_checks = [3, 3]
        return root  # type: ignore[return-value]

    def set_epd(self, epd: str, **kwargs: typing.Any) -> typing.Dict[str, typing.Any]:
        return super().set_epd(epd, **kwargs)


# =========================================================================
# Crazyhouse
# =========================================================================

CrazyhousePocketT = TypeVar("CrazyhousePocketT", bound="CrazyhousePocket")
CrazyhouseBoardT = TypeVar("CrazyhouseBoardT", bound="CrazyhouseBoard")


class CrazyhousePocket:

    def __init__(self, symbols: str = "") -> None:
        self._pieces: Dict[int, int] = {}
        for ch in symbols:
            p = Piece.from_symbol(ch)
            self.add(p.piece_type)

    def add(self, piece_type: int) -> None:
        self._pieces[piece_type] = self._pieces.get(piece_type, 0) + 1

    def remove(self, piece_type: int) -> None:
        count = self._pieces.get(piece_type, 0)
        if count > 1:
            self._pieces[piece_type] = count - 1
        elif count == 1:
            del self._pieces[piece_type]

    def count(self, piece_type: int) -> int:
        return self._pieces.get(piece_type, 0)

    def reset(self) -> None:
        self._pieces.clear()

    def copy(self) -> CrazyhousePocket:
        pocket = CrazyhousePocket()
        pocket._pieces = dict(self._pieces)
        return pocket

    def __str__(self) -> str:
        result: list[str] = []
        for pt in [QUEEN, ROOK, BISHOP, KNIGHT, PAWN]:
            count = self.count(pt)
            if count:
                symbol = Piece(pt, WHITE).symbol().lower()
                result.append(symbol * count)
        return "".join(result)

    def __repr__(self) -> str:
        return f"CrazyhousePocket('{self}')"

    def __bool__(self) -> bool:
        return bool(self._pieces)

    def __eq__(self, other: object) -> bool:
        if isinstance(other, CrazyhousePocket):
            return self._pieces == other._pieces
        return NotImplemented

    def __hash__(self) -> int:
        return hash(tuple(sorted(self._pieces.items())))

    def __iter__(self) -> Iterator[Piece]:
        for pt, count in self._pieces.items():
            for _ in range(count):
                yield Piece(pt, WHITE)


class CrazyhouseBoard(Board):

    aliases: List[str] = ["Crazyhouse", "Crazy House", "House", "ZH"]
    uci_variant: Optional[str] = "crazyhouse"
    xboard_variant: Optional[str] = "crazyhouse"
    starting_fen: str = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR[] w KQkq - 0 1"

    tbw_suffix: Optional[str] = None
    tbz_suffix: Optional[str] = None

    def __init__(
        self,
        fen: Optional[str] = None,
        *,
        chess960: bool = False,
    ) -> None:
        self.pockets = [CrazyhousePocket(), CrazyhousePocket()]
        self._pocket_stack: list = []
        if fen is None:
            super().__init__(type(self).starting_fen, chess960=chess960)
        else:
            super().__init__(fen, chess960=chess960)

    def reset_board(self) -> None:
        super().reset_board()
        self.pockets = [CrazyhousePocket(), CrazyhousePocket()]
        self._pocket_stack = []

    def clear_board(self) -> None:
        super().clear_board()
        self.pockets = [CrazyhousePocket(), CrazyhousePocket()]
        self._pocket_stack = []

    def push(self, move: Move) -> None:
        saved_pockets = [p.copy() for p in self.pockets]

        if getattr(move, 'drop', None):
            self._stack.append(_BoardState(self))
            self.move_stack.append(move)
            self.pockets[self.turn].remove(move.drop)
            self.set_piece_at(move.to_square, Piece(move.drop, self.turn))
            if self.turn == BLACK:
                self.fullmove_number += 1
            self.turn = not self.turn
            self.ep_square = None
            self.halfmove_clock += 1
        else:
            captured_pt = self.piece_type_at(move.to_square)
            is_ep = (self.piece_type_at(move.from_square) == PAWN and
                     move.to_square == self.ep_square)
            if is_ep:
                captured_pt = PAWN
            was_promoted = bool(self.promoted & BB_SQUARES[move.to_square]) if captured_pt else False
            capturing_color = self.turn
            super().push(move)
            if captured_pt is not None:
                if was_promoted:
                    self.pockets[capturing_color].add(PAWN)
                else:
                    self.pockets[capturing_color].add(captured_pt)

        self._pocket_stack.append(saved_pockets)

    def pop(self) -> Move:
        saved_pockets = self._pocket_stack.pop()
        self.pockets = saved_pockets
        move = self.move_stack[-1]
        if getattr(move, 'drop', None):
            self.move_stack.pop()
            state = self._stack.pop()
            state.restore(self)
            return move
        return super().pop()

    def board_fen(self, *, promoted: bool = False) -> str:
        base = super().board_fen(promoted=True)
        pocket_str = str(self.pockets[WHITE]).upper() + str(self.pockets[BLACK])
        return base + "[" + pocket_str + "]"

    def set_fen(self, fen: str) -> None:
        parts = fen.split()
        if parts:
            board_part = parts[0]
            bracket_start = board_part.find("[")
            if bracket_start >= 0:
                bracket_end = board_part.find("]", bracket_start)
                pocket_str = board_part[bracket_start + 1:bracket_end] if bracket_end > bracket_start else ""
                board_part = board_part[:bracket_start] + board_part[bracket_end + 1:] if bracket_end >= 0 else board_part[:bracket_start]
                parts[0] = board_part
                fen = " ".join(parts)
                super().set_fen(fen)
                self.pockets = [CrazyhousePocket(), CrazyhousePocket()]
                for ch in pocket_str:
                    if ch.isupper():
                        p = Piece.from_symbol(ch)
                        self.pockets[WHITE].add(p.piece_type)
                    elif ch.islower():
                        p = Piece.from_symbol(ch)
                        self.pockets[BLACK].add(p.piece_type)
                return
        super().set_fen(fen)

    def generate_pseudo_legal_drops(self, to_mask: int = BB_ALL) -> Iterator[Move]:
        empty = ~self.occupied & to_mask
        no_pawn_ranks = ~(BB_RANK_1 | BB_RANK_8)
        pocket = self.pockets[self.turn]

        for piece_type in PIECE_TYPES:
            if piece_type == KING:
                continue
            if pocket.count(piece_type) <= 0:
                continue
            if piece_type == PAWN:
                squares = empty & no_pawn_ranks
            else:
                squares = empty
            for sq in scan_forward(squares):
                yield Move(sq, sq, drop=piece_type)

    def legal_drop_squares_mask(self) -> int:
        return ~self.occupied & BB_ALL

    def legal_drop_squares(self) -> SquareSet:
        return SquareSet(self.legal_drop_squares_mask())

    def generate_legal_drops(self, to_mask: int = BB_ALL) -> Iterator[Move]:
        if not self.is_check():
            yield from self.generate_pseudo_legal_drops(to_mask)
            return

        king_sq = self.king(self.turn)
        if king_sq is None:
            return

        checkers = self.attackers_mask(not self.turn, king_sq)
        if popcount(checkers) != 1:
            return

        checker_sq = msb(checkers)
        blocking = between(king_sq, checker_sq)
        if not blocking:
            return

        yield from self.generate_pseudo_legal_drops(to_mask & blocking)

    def generate_legal_moves(
        self,
        from_mask: int = BB_ALL,
        to_mask: int = BB_ALL,
    ) -> Iterator[Move]:
        yield from super().generate_legal_moves(from_mask, to_mask)
        yield from self.generate_legal_drops(to_mask)

    def is_legal(self, move: Move) -> bool:
        if getattr(move, "drop", None):
            return move in self.generate_pseudo_legal_drops()
        return super().is_legal(move)

    def is_pseudo_legal(self, move: Move) -> bool:
        if getattr(move, "drop", None):
            return move in self.generate_pseudo_legal_drops()
        return super().is_pseudo_legal(move)

    def has_insufficient_material(self, color: bool) -> bool:
        if self.pockets[color]:
            return False
        return super().has_insufficient_material(color)

    def is_irreversible(self, move: Move) -> bool:
        return self._is_halfmoves(move)

    def _is_halfmoves(self, move: Move) -> bool:
        return False

    def _transposition_key(self) -> Hashable:
        return (
            super()._transposition_key(),
            str(self.pockets[WHITE]),
            str(self.pockets[BLACK]),
        )

    def copy(self, *, stack: typing.Union[bool, int] = True) -> CrazyhouseBoard:
        board = super().copy(stack=stack)
        board.__class__ = type(self)
        board.pockets = [p.copy() for p in self.pockets]
        if stack is True:
            board._pocket_stack = [
                [p.copy() for p in saved] for saved in self._pocket_stack
            ]
        elif stack is False or stack == 0:
            board._pocket_stack = []
        else:
            board._pocket_stack = [
                [p.copy() for p in saved] for saved in self._pocket_stack[-stack:]
            ]
        return board  # type: ignore[return-value]

    def mirror(self) -> CrazyhouseBoard:
        board = super().mirror()
        board.pockets = [self.pockets[1].copy(), self.pockets[0].copy()]
        return board  # type: ignore[return-value]

    def clear_stack(self) -> None:
        super().clear_stack()

    def root(self) -> CrazyhouseBoard:
        root = super().root()
        root.pockets = [CrazyhousePocket(), CrazyhousePocket()]
        return root  # type: ignore[return-value]

    def parse_san(self, san: str) -> Move:
        if "@" in san:
            parts = san.replace("+", "").replace("#", "")
            if len(parts) >= 3 and parts[1] == "@":
                piece_ch = parts[0]
                sq_name = parts[2:]
                piece_type = {"P": PAWN, "N": KNIGHT, "B": BISHOP, "R": ROOK, "Q": QUEEN, "K": KING}.get(piece_ch.upper())
                if piece_type is None:
                    raise ValueError(f"Invalid drop piece: {piece_ch}")
                try:
                    sq = SQUARE_NAMES.index(sq_name.lower())
                except ValueError:
                    raise ValueError(f"Invalid square: {sq_name}")
                return Move(sq, sq, drop=piece_type)
        return super().parse_san(san)

    def status(self) -> int:
        errors = super().status()
        return errors

    def epd(
        self,
        *,
        shredder: bool = False,
        en_passant: str = "legal",
        promoted: typing.Optional[bool] = None,
        **operations: typing.Union[None, str, int, float, Move, typing.List[Move]],
    ) -> str:
        return super().epd(shredder=shredder, en_passant=en_passant, promoted=promoted, **operations)


# =========================================================================
# VARIANTS list and find_variant
# =========================================================================

VARIANTS: List[Type[Board]] = [
    Board,
    SuicideBoard,
    GiveawayBoard,
    AntichessBoard,
    AtomicBoard,
    KingOfTheHillBoard,
    RacingKingsBoard,
    HordeBoard,
    ThreeCheckBoard,
    CrazyhouseBoard,
]


def find_variant(name: str) -> Type[Board]:
    for variant in VARIANTS:
        if name.lower() in [a.lower() for a in getattr(variant, "aliases", [])] or \
           name.lower() == getattr(variant, "uci_variant", "").lower() or \
           name.lower() == getattr(variant, "xboard_variant", "").lower():
            return variant
    for variant in VARIANTS:
        cls_name = variant.__name__.replace("Board", "").lower()
        if name.lower() == cls_name or name.lower() == "chess":
            return variant
    raise ValueError(f"Unsupported variant: {name}")
