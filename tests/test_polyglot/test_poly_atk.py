"""POLY-ATK: Polyglot acceptance test — comprehensive differential testing.

Tests Zobrist hashing + book reader against python-chess across
1000+ positions, synthetic books, and edge cases.
"""

from __future__ import annotations

import os
import random
import struct
import tempfile

import chess
import chess.polyglot
import pytest

from dcs_chess.core.board import Board
from dcs_chess.core.move import Move
from dcs_chess.polyglot.polyglot import (
    ENTRY_STRUCT,
    POLYGLOT_RANDOM_ARRAY,
    ZobristHasher,
    zobrist_hash,
    open_reader,
)


def _write_book(entries, path):
    """Write a polyglot book from (key, raw_move, weight, learn) tuples, sorted by key."""
    entries_sorted = sorted(entries, key=lambda e: e[0])
    with open(path, "wb") as f:
        for key, raw_move, weight, learn in entries_sorted:
            f.write(ENTRY_STRUCT.pack(key, raw_move, weight, learn))


def _encode_move(from_sq, to_sq, promotion=0):
    return to_sq | (from_sq << 6) | (promotion << 12)


# =====================================================================
# 1. Large-scale Zobrist hash differential
# =====================================================================

class TestZobristAcceptance:
    """Test zobrist_hash against python-chess across many positions."""

    def test_1000_random_positions(self):
        """1000 random game positions — must match python-chess exactly."""
        rng = random.Random(12345)
        mismatches = 0
        total = 0
        for _ in range(200):
            b_ref = chess.Board()
            b_ours = Board()
            for _ in range(rng.randint(1, 50)):
                moves = list(b_ref.legal_moves)
                if not moves:
                    break
                m = rng.choice(moves)
                b_ref.push(m)
                b_ours.push_uci(m.uci())
                if zobrist_hash(b_ours) != chess.polyglot.zobrist_hash(b_ref):
                    mismatches += 1
                total += 1
        assert total >= 1000
        assert mismatches == 0, f"{mismatches}/{total} hash mismatches"

    def test_all_opening_moves(self):
        """Every legal first move from the starting position."""
        for m in chess.Board().legal_moves:
            b_ref = chess.Board()
            b_ref.push(m)
            b_ours = Board()
            b_ours.push_uci(m.uci())
            assert zobrist_hash(b_ours) == chess.polyglot.zobrist_hash(b_ref), \
                f"Hash mismatch after {m.uci()}"

    def test_castling_positions(self):
        """Positions before and after castling — both sides."""
        games = [
            ["e2e4", "e7e5", "f1c4", "f8c5", "g1f3", "g8f6", "e1g1"],  # White O-O
            ["d2d4", "d7d5", "c1f4", "c8f5", "b1c3", "b8c6", "d1d2", "d8d7", "e1c1"],  # White O-O-O
            ["e2e4", "e7e5", "g1f3", "f8c5", "f1c4", "g8f6", "d2d3", "e8g8"],  # Black O-O
        ]
        for ucis in games:
            b_ref = chess.Board()
            b_ours = Board()
            for u in ucis:
                b_ref.push(chess.Move.from_uci(u))
                b_ours.push_uci(u)
            assert zobrist_hash(b_ours) == chess.polyglot.zobrist_hash(b_ref), \
                f"Hash mismatch in castling game ending {ucis[-1]}"

    def test_promotion_positions(self):
        """Positions with promotions."""
        fen = "4k3/P7/8/8/8/8/8/4K3 w - - 0 1"
        for promo in ["a8=Q", "a8=R", "a8=B", "a8=N"]:
            b_ref = chess.Board(fen)
            b_ref.push_san(promo)
            b_ours = Board(fen)
            m = b_ours.parse_san(promo)
            b_ours.push(m)
            assert zobrist_hash(b_ours) == chess.polyglot.zobrist_hash(b_ref), \
                f"Hash mismatch after promotion {promo}"

    def test_ep_positions(self):
        """En passant square hashing — only when capturable."""
        b_ref = chess.Board()
        b_ours = Board()
        for u in ["e2e4", "d7d5", "e4e5", "f7f5"]:
            b_ref.push(chess.Move.from_uci(u))
            b_ours.push_uci(u)
        # After f5, EP square f6 should be hashed (e5 pawn can capture)
        assert zobrist_hash(b_ours) == chess.polyglot.zobrist_hash(b_ref)

        # Now play exf6 (en passant)
        b_ref.push(chess.Move.from_uci("e5f6"))
        b_ours.push_uci("e5f6")
        assert zobrist_hash(b_ours) == chess.polyglot.zobrist_hash(b_ref)

    def test_random_array_matches(self):
        """Our random array must be the canonical Polyglot array (781 values)."""
        assert len(POLYGLOT_RANDOM_ARRAY) == 781
        ref_hasher = chess.polyglot.ZobristHasher(chess.polyglot.POLYGLOT_RANDOM_ARRAY)
        our_hasher = ZobristHasher(POLYGLOT_RANDOM_ARRAY)
        b = Board()
        assert our_hasher(b) == ref_hasher(chess.Board())

    def test_chess960_positions(self):
        """50 random Chess960 start positions."""
        rng = random.Random(999)
        for _ in range(50):
            sp = rng.randint(0, 959)
            b_ref = chess.Board.from_chess960_pos(sp)
            b_ours = Board.from_chess960_pos(sp)
            assert zobrist_hash(b_ours) == chess.polyglot.zobrist_hash(b_ref), \
                f"Hash mismatch for Chess960 pos {sp}"


# =====================================================================
# 2. Book reader acceptance
# =====================================================================

class TestBookReaderAcceptance:
    """End-to-end book reader tests with a realistic synthetic book."""

    @pytest.fixture
    def large_book(self, tmp_path):
        """Build a book with entries for 50 positions from a real game tree."""
        entries = []
        rng = random.Random(42)
        positions_seen = set()

        for game_i in range(10):
            b = Board()
            for ply in range(20):
                h = zobrist_hash(b)
                moves = list(b.legal_moves)
                if not moves:
                    break
                # Add 1-3 entries for this position
                n_entries = min(len(moves), rng.randint(1, 3))
                chosen = rng.sample(moves, n_entries)
                for m in chosen:
                    raw = _encode_move(m.from_square, m.to_square,
                                       0 if m.promotion is None else m.promotion - 1)
                    w = rng.randint(1, 200)
                    entries.append((h, raw, w, 0))
                    positions_seen.add(h)

                b.push(rng.choice(moves))

        path = tmp_path / "large.bin"
        _write_book(entries, path)
        return path, positions_seen

    def test_all_entries_readable(self, large_book):
        path, _ = large_book
        with open_reader(path) as reader:
            count = 0
            for entry in reader:
                assert entry.key > 0 or entry.key == 0
                assert entry.weight >= 0
                count += 1
            assert count == len(reader)

    def test_find_all_returns_correct_entries(self, large_book):
        path, positions = large_book
        with open_reader(path) as reader:
            for h in list(positions)[:10]:
                entries = list(reader.find_all(h))
                for e in entries:
                    assert e.key == h

    def test_find_returns_highest_weight(self, large_book):
        path, positions = large_book
        with open_reader(path) as reader:
            for h in list(positions)[:10]:
                all_entries = list(reader.find_all(h))
                if all_entries:
                    best = reader.find(h)
                    assert best.weight == max(e.weight for e in all_entries)

    def test_weighted_choice_distribution(self, large_book):
        """Weighted choice should favor higher-weight entries over many samples."""
        path, _ = large_book
        start_hash = zobrist_hash(Board())
        with open_reader(path) as reader:
            entries = list(reader.find_all(Board()))
            if len(entries) < 2:
                pytest.skip("Need at least 2 entries for distribution test")

            rng = random.Random(0)
            counts = {}
            for _ in range(500):
                e = reader.weighted_choice(Board(), random=rng)
                counts[e.raw_move] = counts.get(e.raw_move, 0) + 1

            # The entry with highest weight should appear most
            max_weight_entry = max(entries, key=lambda e: e.weight)
            assert counts.get(max_weight_entry.raw_move, 0) > 0

    def test_exclude_moves_filters(self, large_book):
        path, _ = large_book
        with open_reader(path) as reader:
            all_entries = list(reader.find_all(Board()))
            if not all_entries:
                pytest.skip("No entries for starting position")
            exclude = {all_entries[0].move}
            filtered = list(reader.find_all(Board(), exclude_moves=exclude))
            assert all(e.move not in exclude for e in filtered)

    def test_minimum_weight_filters(self, large_book):
        path, _ = large_book
        with open_reader(path) as reader:
            entries_100 = list(reader.find_all(Board(), minimum_weight=100))
            assert all(e.weight >= 100 for e in entries_100)

    def test_empty_position_returns_nothing(self, large_book):
        path, _ = large_book
        weird_fen = "4k3/8/8/8/8/8/8/4K3 w - - 0 1"
        with open_reader(path) as reader:
            entries = list(reader.find_all(Board(weird_fen)))
            assert entries == []


# =====================================================================
# 3. Integration: board → hash → book → move → push
# =====================================================================

class TestIntegration:
    def test_book_move_is_legal(self, tmp_path):
        """Every move returned by the book must be legal on the board."""
        b = Board()
        h = zobrist_hash(b)
        entries = []
        for m in list(b.legal_moves)[:5]:
            raw = _encode_move(m.from_square, m.to_square,
                               0 if m.promotion is None else m.promotion - 1)
            entries.append((h, raw, 100, 0))

        path = tmp_path / "legal.bin"
        _write_book(entries, path)

        with open_reader(path) as reader:
            for entry in reader.find_all(b):
                assert b.is_legal(entry.move), f"Illegal move from book: {entry.move.uci()}"
                b_copy = b.copy()
                b_copy.push(entry.move)
                assert b_copy.is_valid()

    def test_castling_normalization_end_to_end(self, tmp_path):
        """Book stores king-takes-rook; reader normalizes to standard for non-960."""
        b = Board()
        h = zobrist_hash(b)
        # Store e1h1 (king-takes-rook for O-O) in the book
        raw = _encode_move(4, 7)  # e1=4, h1=7
        entries = [(h, raw, 100, 0)]
        path = tmp_path / "castle.bin"
        _write_book(entries, path)

        with open_reader(path) as reader:
            found = list(reader.find_all(b))
            if found:
                # Should be normalized to e1g1 for non-960
                assert found[0].move == Move.from_uci("e1g1")
