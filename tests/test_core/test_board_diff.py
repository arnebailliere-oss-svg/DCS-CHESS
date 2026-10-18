"""ADV differential tests for CORE-007 (BaseBoard) and CORE-008 (Board).

Tests: perft, FEN roundtrip, SAN/LAN, piece operations, game-over,
repetition, board status, copy, mirror, castling.
"""

from __future__ import annotations

import chess
import pytest

from dcs_chess.core.board import Board
from dcs_chess.core.baseboard import BaseBoard
from dcs_chess.core.piece import Piece
from dcs_chess.core.move import Move
from dcs_chess.core.constants import (
    WHITE, BLACK, PAWN, KNIGHT, BISHOP, ROOK, QUEEN, KING,
    BB_ALL, BB_EMPTY, BB_SQUARES,
    STARTING_FEN, STARTING_BOARD_FEN,
)


# =====================================================================
# Perft
# =====================================================================

def _perft(board, depth):
    if depth == 0:
        return 1
    nodes = 0
    for move in board.generate_legal_moves():
        board.push(move)
        nodes += _perft(board, depth - 1)
        board.pop()
    return nodes


PERFT_POSITIONS = [
    ("start", STARTING_FEN, [(1, 20), (2, 400), (3, 8902), (4, 197281)]),
    ("kiwipete", "r3k2r/p1ppqpb1/bn2pnp1/3PN3/1p2P3/2N2Q1p/PPPBBPPP/R3K2R w KQkq - 0 1",
     [(1, 48), (2, 2039), (3, 97862)]),
    ("pos3", "8/2p5/3p4/KP5r/1R3p1k/8/4P1P1/8 w - - 0 1",
     [(1, 14), (2, 191), (3, 2812), (4, 43238)]),
    ("pos4", "r3k2r/Pppp1ppp/1b3nbN/nP6/BBP1P3/q4N2/Pp1P2PP/R2Q1RK1 w kq - 0 1",
     [(1, 6), (2, 264), (3, 9467)]),
    ("pos5", "rnbq1k1r/pp1Pbppp/2p5/8/2B5/8/PPP1NnPP/RNBQK2R w KQ - 1 8",
     [(1, 44), (2, 1486), (3, 62379)]),
]


@pytest.mark.parametrize("name,fen,depths", PERFT_POSITIONS, ids=[p[0] for p in PERFT_POSITIONS])
def test_perft(name, fen, depths):
    for depth, expected in depths:
        b = Board(fen)
        nodes = _perft(b, depth)
        assert nodes == expected, f"{name} depth {depth}: got {nodes}, expected {expected}"


# =====================================================================
# FEN roundtrip
# =====================================================================

_FEN_POSITIONS = [
    STARTING_FEN,
    "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq e3 0 1",
    "rnbqkbnr/pp1ppppp/8/2p5/4P3/5N2/PPPP1PPP/RNBQKB1R b KQkq - 1 2",
    "r3k2r/p1ppqpb1/bn2pnp1/3PN3/1p2P3/2N2Q1p/PPPBBPPP/R3K2R w KQkq - 0 1",
    "8/8/8/8/8/8/8/4K2R w K - 0 1",
    "r3k2r/8/8/8/8/8/8/R3K2R w KQkq - 0 1",
    "8/2p5/3p4/KP5r/1R3p1k/8/4P1P1/8 w - - 0 1",
]


@pytest.mark.parametrize("fen", _FEN_POSITIONS)
def test_fen_roundtrip(fen):
    b = Board(fen)
    r = chess.Board(fen)
    assert b.fen() == r.fen()


@pytest.mark.parametrize("fen", _FEN_POSITIONS)
def test_fen_roundtrip_en_passant_fen(fen):
    b = Board(fen)
    r = chess.Board(fen)
    assert b.fen(en_passant="fen") == r.fen(en_passant="fen")


# =====================================================================
# Legal move set comparison
# =====================================================================

_MOVE_POSITIONS = [
    STARTING_FEN,
    "r3k2r/p1ppqpb1/bn2pnp1/3PN3/1p2P3/2N2Q1p/PPPBBPPP/R3K2R w KQkq - 0 1",
    "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq e3 0 1",
    "8/2p5/3p4/KP5r/1R3p1k/8/4P1P1/8 w - - 0 1",
    "rnbq1k1r/pp1Pbppp/2p5/8/2B5/8/PPP1NnPP/RNBQK2R w KQ - 1 8",
    "r3k2r/Pppp1ppp/1b3nbN/nP6/BBP1P3/q4N2/Pp1P2PP/R2Q1RK1 w kq - 0 1",
    "8/8/1k6/2b5/2pP4/8/5K2/8 b - d3 0 1",  # EP capture
    "8/5k2/8/2Pp4/2B5/1K6/8/8 w - d6 0 1",  # EP capture
]


@pytest.mark.parametrize("fen", _MOVE_POSITIONS)
def test_legal_moves_match(fen):
    b = Board(fen)
    r = chess.Board(fen)
    our_moves = sorted(m.uci() for m in b.generate_legal_moves())
    ref_moves = sorted(m.uci() for m in r.generate_legal_moves())
    assert our_moves == ref_moves, f"Move mismatch in {fen}"


# =====================================================================
# SAN / LAN notation
# =====================================================================

class TestSanNotation:
    _GAMES = [
        # (starting_fen, uci_moves)
        (STARTING_FEN, ["e2e4", "e7e5", "g1f3", "b8c6", "f1b5"]),  # Ruy Lopez
        (STARTING_FEN, ["e2e4", "c7c5", "g1f3", "d7d6", "d2d4", "c5d4", "f3d4"]),  # Sicilian
        (STARTING_FEN, ["d2d4", "g8f6", "c2c4", "e7e6", "b1c3", "f8b4"]),  # Nimzo-Indian
        (STARTING_FEN, ["e2e4", "e7e5", "d1h5", "b8c6", "f1c4", "g8f6", "h5f7"]),  # Scholar's mate
    ]

    @pytest.mark.parametrize("fen,ucis", _GAMES)
    def test_san_matches_reference(self, fen, ucis):
        b = Board(fen)
        r = chess.Board(fen)
        for uci in ucis:
            our_move = b.parse_uci(uci)
            ref_move = r.parse_uci(uci)
            assert b.san(our_move) == r.san(ref_move), f"SAN mismatch at {uci} in {b.fen()}"
            b.push(our_move)
            r.push(ref_move)

    @pytest.mark.parametrize("fen,ucis", _GAMES)
    def test_lan_matches_reference(self, fen, ucis):
        b = Board(fen)
        r = chess.Board(fen)
        for uci in ucis:
            our_move = b.parse_uci(uci)
            ref_move = r.parse_uci(uci)
            assert b.lan(our_move) == r.lan(ref_move), f"LAN mismatch at {uci}"
            b.push(our_move)
            r.push(ref_move)

    def test_san_castling(self):
        fen = "r3k2r/pppppppp/8/8/8/8/PPPPPPPP/R3K2R w KQkq - 0 1"
        b = Board(fen)
        r = chess.Board(fen)
        ks = b.parse_uci("e1g1")
        qs = b.parse_uci("e1c1")
        rks = r.parse_uci("e1g1")
        rqs = r.parse_uci("e1c1")
        assert b.san(ks) == r.san(rks)
        assert b.san(qs) == r.san(rqs)

    def test_san_promotion(self):
        fen = "8/P7/8/8/8/8/8/4K2k w - - 0 1"
        b = Board(fen)
        r = chess.Board(fen)
        m = b.parse_uci("a7a8q")
        rm = r.parse_uci("a7a8q")
        assert b.san(m) == r.san(rm)


# =====================================================================
# BaseBoard operations
# =====================================================================

class TestBaseBoard:
    def test_starting_board_fen(self):
        bb = BaseBoard()
        r = chess.BaseBoard()
        assert bb.board_fen() == r.board_fen()

    def test_piece_at(self):
        bb = BaseBoard()
        r = chess.BaseBoard()
        for sq in range(64):
            our_p = bb.piece_at(sq)
            ref_p = r.piece_at(sq)
            if our_p is None:
                assert ref_p is None, f"sq {sq}: ours=None, ref={ref_p}"
            else:
                assert ref_p is not None
                assert our_p.piece_type == ref_p.piece_type
                assert our_p.color == ref_p.color

    def test_piece_map(self):
        bb = BaseBoard()
        r = chess.BaseBoard()
        our_map = bb.piece_map()
        ref_map = r.piece_map()
        assert set(our_map.keys()) == set(ref_map.keys())
        for sq in our_map:
            assert our_map[sq].symbol() == ref_map[sq].symbol()

    def test_attacks(self):
        bb = BaseBoard()
        r = chess.BaseBoard()
        for sq in range(64):
            if bb.piece_at(sq) is not None:
                assert int(bb.attacks(sq)) == int(r.attacks(sq)), f"attacks differ at sq {sq}"

    @pytest.mark.parametrize("pos", range(0, 960, 96))
    def test_chess960_roundtrip(self, pos):
        bb = BaseBoard.from_chess960_pos(pos)
        r = chess.BaseBoard.from_chess960_pos(pos)
        assert bb.board_fen() == r.board_fen()

    def test_mirror(self):
        bb = BaseBoard()
        r = chess.BaseBoard()
        assert bb.mirror().board_fen() == r.mirror().board_fen()

    def test_copy(self):
        bb = BaseBoard()
        c = bb.copy()
        assert bb.board_fen() == c.board_fen()
        c.remove_piece_at(0)
        assert bb.board_fen() != c.board_fen()


# =====================================================================
# Game-over predicates
# =====================================================================

class TestGameOver:
    def test_checkmate(self):
        b = Board()
        r = chess.Board()
        for uci in ["f2f3", "e7e5", "g2g4", "d8h4"]:
            b.push_uci(uci)
            r.push_uci(uci)
        assert b.is_checkmate() == r.is_checkmate()
        assert b.is_game_over() == r.is_game_over()

    def test_stalemate(self):
        fen = "k7/8/1K6/8/8/8/8/8 b - - 0 1"
        b = Board(fen)
        r = chess.Board(fen)
        assert b.is_stalemate() == r.is_stalemate()

    def test_insufficient_material(self):
        fens = [
            "4k3/8/8/8/8/8/8/4K3 w - - 0 1",   # K vs K
            "4k3/8/8/8/8/8/8/4KB2 w - - 0 1",  # K+B vs K
            "4k3/8/8/8/8/8/8/4KN2 w - - 0 1",  # K+N vs K
            "4k3/8/8/8/8/8/4P3/4K3 w - - 0 1",  # K+P vs K (NOT insufficient)
        ]
        for fen in fens:
            b = Board(fen)
            r = chess.Board(fen)
            assert b.is_insufficient_material() == r.is_insufficient_material(), f"Insufficient material mismatch: {fen}"


# =====================================================================
# Board status / validity
# =====================================================================

class TestBoardStatus:
    def test_starting_valid(self):
        b = Board()
        r = chess.Board()
        assert b.status() == r.status()
        assert b.is_valid() == r.is_valid()

    def test_no_kings(self):
        b = Board(None)
        r = chess.Board(None)
        assert b.status() == r.status()

    def test_pawns_on_backrank(self):
        b = Board(None)
        b.set_piece_at(0, Piece(PAWN, WHITE))
        b.set_piece_at(4, Piece(KING, WHITE))
        b.set_piece_at(60, Piece(KING, BLACK))
        r = chess.Board(None)
        r.set_piece_at(0, chess.Piece(PAWN, WHITE))
        r.set_piece_at(4, chess.Piece(KING, WHITE))
        r.set_piece_at(60, chess.Piece(KING, BLACK))
        assert b.status() == r.status()


# =====================================================================
# Board copy / equality
# =====================================================================

class TestBoardCopy:
    def test_copy_eq(self):
        b = Board()
        c = b.copy()
        r = chess.Board()
        assert b.fen() == c.fen()
        assert b == c

    def test_copy_independence(self):
        b = Board()
        c = b.copy()
        c.push_uci("e2e4")
        assert b.fen() != c.fen()

    def test_copy_stack(self):
        b = Board()
        b.push_uci("e2e4")
        b.push_uci("e7e5")
        c = b.copy(stack=True)
        assert len(c.move_stack) == 2

    def test_copy_no_stack(self):
        b = Board()
        b.push_uci("e2e4")
        c = b.copy(stack=False)
        assert len(c.move_stack) == 0
        assert c.fen() == b.fen()


# =====================================================================
# Repetition detection
# =====================================================================

class TestRepetition:
    def test_threefold_repetition(self):
        b = Board()
        r = chess.Board()
        for uci in ["g1f3", "g8f6", "f3g1", "f6g8", "g1f3", "g8f6", "f3g1", "f6g8"]:
            b.push_uci(uci)
            r.push_uci(uci)
        assert b.is_repetition(3) == r.is_repetition(3)

    def test_no_repetition(self):
        b = Board()
        r = chess.Board()
        b.push_uci("e2e4")
        r.push_uci("e2e4")
        assert b.is_repetition(3) == r.is_repetition(3)


# =====================================================================
# Castling
# =====================================================================

class TestCastling:
    def test_castling_after_push(self):
        b = Board()
        r = chess.Board()
        for uci in ["e2e4", "e7e5", "g1f3", "b8c6", "f1e2", "g8f6", "e1g1"]:
            b.push_uci(uci)
            r.push_uci(uci)
        assert b.fen() == r.fen()

    def test_queenside_castling(self):
        b = Board()
        r = chess.Board()
        for uci in ["d2d4", "d7d5", "b1c3", "b8c6", "c1f4", "c8f5", "d1d2", "d8d7", "e1c1"]:
            b.push_uci(uci)
            r.push_uci(uci)
        assert b.fen() == r.fen()

    def test_castling_rights_lost_after_king_move(self):
        b = Board()
        r = chess.Board()
        for uci in ["e2e4", "e7e5", "e1e2"]:
            b.push_uci(uci)
            r.push_uci(uci)
        assert b.has_castling_rights(WHITE) == r.has_castling_rights(WHITE)
        assert not b.has_castling_rights(WHITE)


# =====================================================================
# En passant
# =====================================================================

class TestEnPassant:
    def test_en_passant_capture(self):
        b = Board()
        r = chess.Board()
        for uci in ["e2e4", "d7d5", "e4e5", "f7f5"]:
            b.push_uci(uci)
            r.push_uci(uci)
        assert b.ep_square == r.ep_square
        ep_move = b.parse_uci("e5f6")
        assert b.is_en_passant(ep_move)
        b.push(ep_move)
        r.push_uci("e5f6")
        assert b.fen() == r.fen()

    def test_ep_not_legal_if_pinned(self):
        fen = "8/8/8/8/k2Pp2Q/8/8/3K4 b - d3 0 1"
        b = Board(fen)
        r = chess.Board(fen)
        our_moves = sorted(m.uci() for m in b.generate_legal_moves())
        ref_moves = sorted(m.uci() for m in r.generate_legal_moves())
        assert our_moves == ref_moves


# =====================================================================
# Promotion
# =====================================================================

class TestPromotion:
    def test_promotion_moves(self):
        fen = "8/P4k2/8/8/8/8/8/4K3 w - - 0 1"
        b = Board(fen)
        r = chess.Board(fen)
        our_moves = sorted(m.uci() for m in b.generate_legal_moves())
        ref_moves = sorted(m.uci() for m in r.generate_legal_moves())
        assert our_moves == ref_moves


# =====================================================================
# Ply (FR-C7 parity)
# =====================================================================

class TestPly:
    """ply() must be derived from position state, not move_stack length."""

    PLY_FENS = [
        # (fen, description)
        ("rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq - 0 1",
         "after 1.e4, Black to move"),
        ("rnbqkbnr/pppp1ppp/8/4p3/4P3/5N2/PPPP1PPP/RNBQKB1R b KQkq - 1 2",
         "after 1.e4 e5 2.Nf3, Black to move"),
        ("rnbqkb1r/pppp1ppp/5n2/4p3/4P3/5N2/PPPP1PPP/RNBQKB1R w KQkq - 2 3",
         "after 1.e4 e5 2.Nf3 Nf6, White to move"),
        ("r1bqkbnr/pppppppp/2n5/8/4P3/8/PPPP1PPP/RNBQKBNR w KQkq - 1 2",
         "after 1.e4 Nc6, White to move"),
        ("8/8/8/8/8/5k2/8/4K2R w K - 0 50",
         "endgame, fullmove 50, White to move"),
        ("8/8/8/8/8/5k2/8/4K2R b K - 0 50",
         "endgame, fullmove 50, Black to move"),
    ]

    @pytest.mark.parametrize("fen,desc", PLY_FENS, ids=[f[1] for f in PLY_FENS])
    def test_ply_from_fen(self, fen, desc):
        b = Board(fen)
        r = chess.Board(fen)
        assert b.ply() == r.ply(), f"ply mismatch on FEN load: {desc}"

    @pytest.mark.parametrize("fen,desc", PLY_FENS, ids=[f[1] for f in PLY_FENS])
    def test_ply_after_push(self, fen, desc):
        b = Board(fen)
        r = chess.Board(fen)
        ref_move = list(r.legal_moves)[0]
        our_move = Move.from_uci(ref_move.uci())
        b.push(our_move)
        r.push(ref_move)
        assert b.ply() == r.ply(), f"ply mismatch after push: {desc}"

    @pytest.mark.parametrize("fen,desc", PLY_FENS, ids=[f[1] for f in PLY_FENS])
    def test_ply_after_push_pop(self, fen, desc):
        b = Board(fen)
        r = chess.Board(fen)
        ref_move = list(r.legal_moves)[0]
        our_move = Move.from_uci(ref_move.uci())
        b.push(our_move)
        r.push(ref_move)
        b.pop()
        r.pop()
        assert b.ply() == r.ply(), f"ply mismatch after push+pop: {desc}"

    def test_ply_initial_position(self):
        b = Board()
        r = chess.Board()
        assert b.ply() == r.ply() == 0

    def test_ply_multi_move_sequence(self):
        b = Board()
        r = chess.Board()
        moves = ["e2e4", "e7e5", "g1f3", "b8c6", "f1b5"]
        for uci in moves:
            b.push(Move.from_uci(uci))
            r.push(chess.Move.from_uci(uci))
            assert b.ply() == r.ply(), f"ply mismatch after {uci}"
        for _ in range(len(moves)):
            b.pop()
            r.pop()
            assert b.ply() == r.ply(), f"ply mismatch during pop sequence"
