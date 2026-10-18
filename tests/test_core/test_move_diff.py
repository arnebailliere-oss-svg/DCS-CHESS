"""Differential tests for CORE-005: Move class (FR-C4)."""

from __future__ import annotations

import chess as ref
import pytest

from dcs_chess.core.move import Move as DcsMove


class TestMoveUci:
    @pytest.mark.parametrize("uci", [
        "e2e4", "e7e5", "g1f3", "b8c6", "e1g1", "e7e8q", "a7a8n",
        "b2b1r", "h7h8b", "0000",
    ])
    def test_from_uci_roundtrip(self, uci: str):
        d = DcsMove.from_uci(uci)
        r = ref.Move.from_uci(uci)
        assert d.from_square == r.from_square
        assert d.to_square == r.to_square
        assert d.promotion == r.promotion
        assert d.drop == r.drop
        assert d.uci() == r.uci()

    @pytest.mark.parametrize("uci", ["P@e4", "N@d5", "Q@a1"])
    def test_drop_moves(self, uci: str):
        d = DcsMove.from_uci(uci)
        r = ref.Move.from_uci(uci)
        assert d.drop == r.drop
        assert d.uci() == r.uci()

    def test_null_move(self):
        d = DcsMove.null()
        r = ref.Move.null()
        assert not d
        assert not r
        assert d.uci() == r.uci()
        assert d.uci() == "0000"

    def test_xboard_null(self):
        d = DcsMove.null()
        r = ref.Move.null()
        assert d.xboard() == r.xboard()
        assert d.xboard() == "@@@@"

    @pytest.mark.parametrize("uci", ["e2e4", "g1f3", "e7e8q"])
    def test_xboard_regular(self, uci: str):
        d = DcsMove.from_uci(uci)
        r = ref.Move.from_uci(uci)
        assert d.xboard() == r.xboard()


class TestMoveEquality:
    def test_equal_moves(self):
        a = DcsMove.from_uci("e2e4")
        b = DcsMove.from_uci("e2e4")
        assert a == b
        assert hash(a) == hash(b)

    def test_unequal_moves(self):
        a = DcsMove.from_uci("e2e4")
        b = DcsMove.from_uci("d2d4")
        assert a != b

    def test_promotion_inequality(self):
        a = DcsMove.from_uci("e7e8q")
        b = DcsMove.from_uci("e7e8r")
        assert a != b

    def test_bool_regular(self):
        m = DcsMove.from_uci("e2e4")
        assert bool(m)

    def test_bool_null(self):
        m = DcsMove.null()
        assert not bool(m)


class TestMoveHash:
    @pytest.mark.parametrize("uci", [
        "e2e4", "d2d4", "g1f3", "e7e8q", "a7a8n", "0000", "P@e4",
    ])
    def test_hash_matches_ref(self, uci: str):
        d = DcsMove.from_uci(uci)
        r = ref.Move.from_uci(uci)
        assert hash(d) == hash(r), f"hash mismatch for {uci}"


class TestMoveErrors:
    @pytest.mark.parametrize("bad", ["", "e", "e2e", "x1y2", "e2e4zz"])
    def test_invalid_uci(self, bad: str):
        with pytest.raises(ValueError):
            DcsMove.from_uci(bad)
