"""Unit tests for dcs_chess.core.bitboards (CORE-002)."""

from dcs_chess.core.constants import (
    A1, B1, C1, D1, E1, F1, G1, H1,
    A2, B3, B7, C3, E4, D4, D5, E5, H8,
    A8, B8, C6, F3, G5,
    SQUARES, WHITE, BLACK,
)
from dcs_chess.core.bitboards import (
    BB_EMPTY, BB_ALL, BB_SQUARES,
    BB_A1, BB_H8, BB_E4,
    BB_FILE_A, BB_FILE_H, BB_FILES,
    BB_RANK_1, BB_RANK_8, BB_RANKS,
    BB_LIGHT_SQUARES, BB_DARK_SQUARES,
    BB_CORNERS, BB_CENTER, BB_BACKRANKS,
    BB_KNIGHT_ATTACKS, BB_KING_ATTACKS, BB_PAWN_ATTACKS,
    BB_DIAG_MASKS, BB_DIAG_ATTACKS,
    BB_FILE_MASKS, BB_FILE_ATTACKS,
    BB_RANK_MASKS, BB_RANK_ATTACKS,
    BB_RAYS,
)


def popcount(bb: int) -> int:
    return bin(bb).count("1")


class TestFundamentalMasks:
    def test_bb_empty(self):
        assert BB_EMPTY == 0

    def test_bb_all(self):
        assert BB_ALL == (1 << 64) - 1

    def test_bb_squares(self):
        assert len(BB_SQUARES) == 64
        assert BB_SQUARES[0] == 1
        assert BB_SQUARES[63] == 1 << 63

    def test_per_square_constants(self):
        assert BB_A1 == 1
        assert BB_H8 == 1 << 63


class TestFileRankMasks:
    def test_file_masks(self):
        assert len(BB_FILES) == 8
        assert BB_FILE_A == 0x0101_0101_0101_0101
        assert BB_FILE_H == 0x8080_8080_8080_8080

    def test_rank_masks(self):
        assert len(BB_RANKS) == 8
        assert BB_RANK_1 == 0xFF
        assert BB_RANK_8 == 0xFF << 56

    def test_files_are_disjoint(self):
        union = 0
        for f in BB_FILES:
            assert union & f == 0
            union |= f
        assert union == BB_ALL

    def test_ranks_are_disjoint(self):
        union = 0
        for r in BB_RANKS:
            assert union & r == 0
            union |= r
        assert union == BB_ALL


class TestAreaMasks:
    def test_light_dark(self):
        assert BB_LIGHT_SQUARES & BB_DARK_SQUARES == 0
        assert BB_LIGHT_SQUARES | BB_DARK_SQUARES == BB_ALL

    def test_corners(self):
        assert popcount(BB_CORNERS) == 4

    def test_center(self):
        assert popcount(BB_CENTER) == 4
        assert BB_CENTER & BB_SQUARES[D4]
        assert BB_CENTER & BB_SQUARES[E5]

    def test_backranks(self):
        assert BB_BACKRANKS == BB_RANK_1 | BB_RANK_8


class TestKnightAttacks:
    def test_table_size(self):
        assert len(BB_KNIGHT_ATTACKS) == 64

    def test_center(self):
        assert popcount(BB_KNIGHT_ATTACKS[E4]) == 8

    def test_corner(self):
        assert popcount(BB_KNIGHT_ATTACKS[A1]) == 2

    def test_edge(self):
        assert popcount(BB_KNIGHT_ATTACKS[A2]) == 3


class TestKingAttacks:
    def test_table_size(self):
        assert len(BB_KING_ATTACKS) == 64

    def test_center(self):
        assert popcount(BB_KING_ATTACKS[E4]) == 8

    def test_corner(self):
        assert popcount(BB_KING_ATTACKS[A1]) == 3

    def test_edge(self):
        assert popcount(BB_KING_ATTACKS[E1]) == 5


class TestPawnAttacks:
    def test_white_center(self):
        assert popcount(BB_PAWN_ATTACKS[WHITE][E4]) == 2

    def test_white_a_file(self):
        assert popcount(BB_PAWN_ATTACKS[WHITE][A2]) == 1

    def test_black_center(self):
        assert popcount(BB_PAWN_ATTACKS[BLACK][E4]) == 2

    def test_black_h_file(self):
        assert popcount(BB_PAWN_ATTACKS[BLACK][H8]) == 1


class TestSlidingAttacks:
    def test_bishop_e4_empty(self):
        attacks = BB_DIAG_ATTACKS[E4][BB_EMPTY & BB_DIAG_MASKS[E4]]
        assert popcount(attacks) == 13

    def test_rook_e4_empty_file(self):
        attacks = BB_FILE_ATTACKS[E4][BB_EMPTY & BB_FILE_MASKS[E4]]
        assert popcount(attacks) == 7

    def test_rook_e4_empty_rank(self):
        attacks = BB_RANK_ATTACKS[E4][BB_EMPTY & BB_RANK_MASKS[E4]]
        assert popcount(attacks) == 7

    def test_bishop_blocked(self):
        occ = BB_SQUARES[C6] | BB_SQUARES[G5]
        masked = occ & BB_DIAG_MASKS[E4]
        attacks = BB_DIAG_ATTACKS[E4][masked]
        assert attacks & BB_SQUARES[C6]
        assert not (attacks & BB_SQUARES[B7])

    def test_rook_file_blocked(self):
        occ = BB_SQUARES[E1]
        masked = occ & BB_FILE_MASKS[E4]
        attacks = BB_FILE_ATTACKS[E4][masked]
        assert attacks & BB_SQUARES[E1]  # blocker is included
        # Squares below the blocker should not be attacked
        # E1 is on rank 1 (the edge), so nothing below it to test;
        # instead verify that e5..e8 are all attacked (no blocker above)
        for sq in [36, 44, 52, 60]:  # e5, e6, e7, e8
            assert attacks & BB_SQUARES[sq]


class TestRays:
    def test_diagonal(self):
        ray = BB_RAYS[A1][H8]
        assert ray != 0
        assert popcount(ray) == 8

    def test_file(self):
        ray = BB_RAYS[E1][E4]
        assert ray != 0
        for sq in [E1, 12, 20, E4, 36, 44, 52, 60]:  # e-file
            assert ray & BB_SQUARES[sq], f"Square {sq} should be on e-file ray"

    def test_rank(self):
        ray = BB_RAYS[A1][H1]
        assert ray == BB_RANK_1

    def test_non_aligned(self):
        assert BB_RAYS[A1][B3] == 0

    def test_symmetric(self):
        for a in [A1, E4, H8, D1, A8]:
            for b in SQUARES:
                assert BB_RAYS[a][b] == BB_RAYS[b][a]
