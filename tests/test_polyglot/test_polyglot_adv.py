"""ADV adversarial differential tests for POLY-001: polyglot."""

from __future__ import annotations

import os
import random
import struct
import tempfile
from pathlib import Path

import chess
import chess.polyglot
import pytest

from dcs_chess.core.board import Board
from dcs_chess.core.move import Move
from dcs_chess.core import E1, G1, C1, H1, A1, E8, G8, C8, H8, A8
from dcs_chess.polyglot.polyglot import (
    ENTRY_STRUCT,
    Entry,
    ZobristHasher,
    MemoryMappedReader,
    POLYGLOT_RANDOM_ARRAY,
    open_reader,
    zobrist_hash,
    _from_chess960,
)


# =====================================================================
# Helpers
# =====================================================================

def _write_book(entries, path):
    """Write a synthetic polyglot book file from (key, raw_move, weight, learn) tuples."""
    entries_sorted = sorted(entries, key=lambda e: e[0])
    with open(path, "wb") as f:
        for key, raw_move, weight, learn in entries_sorted:
            f.write(ENTRY_STRUCT.pack(key, raw_move, weight, learn))


def _encode_move(from_sq, to_sq, promotion=0):
    """Encode a move into polyglot raw_move format."""
    return to_sq | (from_sq << 6) | (promotion << 12)


# =====================================================================
# Zobrist hash differential
# =====================================================================

class TestZobristHash:
    def test_starting_position(self):
        ref = chess.polyglot.zobrist_hash(chess.Board())
        ours = zobrist_hash(Board())
        assert ours == ref

    def test_after_e4(self):
        b_ref = chess.Board()
        b_ref.push_uci("e2e4")
        b_ours = Board()
        b_ours.push_uci("e2e4")
        assert zobrist_hash(b_ours) == chess.polyglot.zobrist_hash(b_ref)

    def test_ep_square_with_adjacent_pawn(self):
        fen = "rnbqkbnr/pppp1ppp/8/3Pp3/8/8/PPP1PPPP/RNBQKBNR w KQkq e6 0 3"
        assert zobrist_hash(Board(fen)) == chess.polyglot.zobrist_hash(chess.Board(fen))

    def test_ep_square_without_adjacent_pawn(self):
        fen = "rnbqkbnr/pppp1ppp/8/4p3/4P3/8/PPPP1PPP/RNBQKBNR w KQkq - 0 2"
        assert zobrist_hash(Board(fen)) == chess.polyglot.zobrist_hash(chess.Board(fen))

    def test_partial_castling_rights(self):
        fen = "r3k2r/pppppppp/8/8/8/8/PPPPPPPP/R3K2R w Kq - 0 1"
        assert zobrist_hash(Board(fen)) == chess.polyglot.zobrist_hash(chess.Board(fen))

    def test_black_to_move(self):
        fen = "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq - 0 1"
        assert zobrist_hash(Board(fen)) == chess.polyglot.zobrist_hash(chess.Board(fen))

    def test_bare_kings(self):
        fen = "4k3/8/8/8/8/8/8/4K3 w - - 0 1"
        assert zobrist_hash(Board(fen)) == chess.polyglot.zobrist_hash(chess.Board(fen))

    def test_random_games_differential(self):
        rng = random.Random(42)
        mismatches = 0
        total = 0
        for _ in range(50):
            b_ref = chess.Board()
            b_ours = Board()
            for _ in range(40):
                moves = list(b_ref.legal_moves)
                if not moves:
                    break
                m = rng.choice(moves)
                b_ref.push(m)
                b_ours.push_uci(m.uci())
                if zobrist_hash(b_ours) != chess.polyglot.zobrist_hash(b_ref):
                    mismatches += 1
                total += 1
        assert mismatches == 0, f"{mismatches}/{total} mismatches"

    def test_random_array_length(self):
        assert len(POLYGLOT_RANDOM_ARRAY) == 781

    def test_hasher_custom_array(self):
        custom = [i * 123456789 for i in range(781)]
        hasher = ZobristHasher(custom)
        h = hasher(Board())
        assert isinstance(h, int)


# =====================================================================
# Castling normalization
# =====================================================================

class TestCastlingNormalization:
    def test_white_kingside(self):
        b = Board()
        m = _from_chess960(b, False, E1, H1)
        assert m == Move(E1, G1)

    def test_white_queenside(self):
        b = Board()
        m = _from_chess960(b, False, E1, A1)
        assert m == Move(E1, C1)

    def test_black_kingside(self):
        b = Board("r3k2r/pppppppp/8/8/8/8/PPPPPPPP/R3K2R b KQkq - 0 1")
        m = _from_chess960(b, False, E8, H8)
        assert m == Move(E8, G8)

    def test_black_queenside(self):
        b = Board("r3k2r/pppppppp/8/8/8/8/PPPPPPPP/R3K2R b KQkq - 0 1")
        m = _from_chess960(b, False, E8, A8)
        assert m == Move(E8, C8)

    def test_chess960_passthrough(self):
        b = Board()
        m = _from_chess960(b, True, E1, H1)
        assert m == Move(E1, H1)

    def test_non_castling_passthrough(self):
        b = Board()
        m = _from_chess960(b, False, 12, 28)  # e2e4
        assert m.from_square == 12
        assert m.to_square == 28


# =====================================================================
# MemoryMappedReader with synthetic book
# =====================================================================

class TestMemoryMappedReader:
    @pytest.fixture
    def book_path(self, tmp_path):
        """Create a small synthetic polyglot book."""
        path = tmp_path / "test.bin"
        start_hash = zobrist_hash(Board())
        after_e4_hash = zobrist_hash(Board("rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq - 0 1"))
        entries = [
            (start_hash, _encode_move(12, 28), 100, 0),   # e2e4 weight=100
            (start_hash, _encode_move(12, 20), 50, 0),    # e2e3 weight=50
            (start_hash, _encode_move(6, 21), 80, 0),     # g1f3 weight=80
            (after_e4_hash, _encode_move(52, 36), 90, 0), # e7e5 weight=90
        ]
        _write_book(entries, path)
        return path

    @pytest.fixture
    def empty_book_path(self, tmp_path):
        path = tmp_path / "empty.bin"
        path.write_bytes(b"")
        return path

    def test_open_close(self, book_path):
        reader = open_reader(book_path)
        assert len(reader) == 4
        reader.close()

    def test_context_manager(self, book_path):
        with open_reader(book_path) as reader:
            assert len(reader) == 4

    def test_getitem(self, book_path):
        with open_reader(book_path) as reader:
            entry = reader[0]
            assert isinstance(entry, Entry)
            assert isinstance(entry.key, int)
            assert isinstance(entry.weight, int)

    def test_negative_index(self, book_path):
        with open_reader(book_path) as reader:
            last = reader[-1]
            also_last = reader[len(reader) - 1]
            assert last == also_last

    def test_index_out_of_range(self, book_path):
        with open_reader(book_path) as reader:
            with pytest.raises(IndexError):
                reader[100]

    def test_iter(self, book_path):
        with open_reader(book_path) as reader:
            entries = list(reader)
            assert len(entries) == 4

    def test_find_all_by_board(self, book_path):
        with open_reader(book_path) as reader:
            entries = list(reader.find_all(Board()))
            assert len(entries) == 3  # e2e4, g1f3, e2e3

    def test_find_all_by_hash(self, book_path):
        with open_reader(book_path) as reader:
            h = zobrist_hash(Board())
            entries = list(reader.find_all(h))
            assert len(entries) == 3

    def test_find_best(self, book_path):
        with open_reader(book_path) as reader:
            best = reader.find(Board())
            assert best.weight == 100  # e2e4 has highest weight

    def test_find_missing_raises(self, book_path):
        with open_reader(book_path) as reader:
            fen = "4k3/8/8/8/8/8/8/4K3 w - - 0 1"
            with pytest.raises(IndexError):
                reader.find(Board(fen))

    def test_get_default(self, book_path):
        with open_reader(book_path) as reader:
            fen = "4k3/8/8/8/8/8/8/4K3 w - - 0 1"
            result = reader.get(Board(fen))
            assert result is None

    def test_get_found(self, book_path):
        with open_reader(book_path) as reader:
            result = reader.get(Board())
            assert result is not None
            assert result.weight == 100

    def test_minimum_weight(self, book_path):
        with open_reader(book_path) as reader:
            entries = list(reader.find_all(Board(), minimum_weight=80))
            assert all(e.weight >= 80 for e in entries)
            assert len(entries) == 2  # e2e4 (100) and g1f3 (80)

    def test_exclude_moves(self, book_path):
        with open_reader(book_path) as reader:
            excluded = {Move.from_uci("e2e4")}
            entries = list(reader.find_all(Board(), exclude_moves=excluded))
            assert all(e.move != Move.from_uci("e2e4") for e in entries)

    def test_empty_book(self, empty_book_path):
        with open_reader(empty_book_path) as reader:
            assert len(reader) == 0
            entries = list(reader.find_all(Board()))
            assert entries == []

    def test_invalid_file_size(self, tmp_path):
        path = tmp_path / "bad.bin"
        path.write_bytes(b"\x00" * 5)  # not a multiple of entry size
        with pytest.raises(IOError):
            open_reader(path)

    def test_choice_deterministic(self, book_path):
        with open_reader(book_path) as reader:
            rng = random.Random(123)
            entry = reader.choice(Board(), random=rng)
            assert isinstance(entry, Entry)

    def test_weighted_choice(self, book_path):
        with open_reader(book_path) as reader:
            rng = random.Random(42)
            counts = {}
            for _ in range(1000):
                e = reader.weighted_choice(Board(), random=rng)
                counts[e.move.uci()] = counts.get(e.move.uci(), 0) + 1
            # e2e4 (weight=100) should appear most often
            assert counts.get("e2e4", 0) > counts.get("e2e3", 0)

    def test_contains(self, book_path):
        with open_reader(book_path) as reader:
            entries = list(reader)
            assert entries[0] in reader


# =====================================================================
# Promotion encoding
# =====================================================================

class TestPromotionEncoding:
    def test_promotion_knight(self):
        raw = _encode_move(48, 56, 1)  # knight promotion
        to_sq = raw & 0x3f
        from_sq = (raw >> 6) & 0x3f
        promo = (raw >> 12) & 0x7
        assert promo == 1
        assert promo + 1 == 2  # KNIGHT

    def test_promotion_queen(self):
        raw = _encode_move(48, 56, 4)  # queen promotion
        promo = (raw >> 12) & 0x7
        assert promo == 4
        assert promo + 1 == 5  # QUEEN

    def test_no_promotion(self):
        raw = _encode_move(12, 28, 0)
        promo = (raw >> 12) & 0x7
        assert promo == 0
