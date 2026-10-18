"""Differential tests for CORE-004: Piece class (FR-C3)."""

from __future__ import annotations

import copy

import chess as ref
import pytest

from dcs_chess.core.piece import Piece as DcsPiece


class TestPiece:
    @pytest.mark.parametrize("pt", range(1, 7))
    @pytest.mark.parametrize("color", [True, False])
    def test_symbol(self, pt: int, color: bool):
        d = DcsPiece(pt, color)
        r = ref.Piece(pt, color)
        assert d.symbol() == r.symbol()

    @pytest.mark.parametrize("pt", range(1, 7))
    @pytest.mark.parametrize("color", [True, False])
    def test_unicode_symbol(self, pt: int, color: bool):
        d = DcsPiece(pt, color)
        r = ref.Piece(pt, color)
        assert d.unicode_symbol() == r.unicode_symbol()

    @pytest.mark.parametrize("pt", range(1, 7))
    @pytest.mark.parametrize("color", [True, False])
    def test_unicode_symbol_inverted(self, pt: int, color: bool):
        d = DcsPiece(pt, color)
        r = ref.Piece(pt, color)
        assert d.unicode_symbol(invert_color=True) == r.unicode_symbol(invert_color=True)

    @pytest.mark.parametrize("sym", ["P", "N", "B", "R", "Q", "K", "p", "n", "b", "r", "q", "k"])
    def test_from_symbol(self, sym: str):
        d = DcsPiece.from_symbol(sym)
        r = ref.Piece.from_symbol(sym)
        assert d.piece_type == r.piece_type
        assert d.color == r.color
        assert d.symbol() == r.symbol()

    @pytest.mark.parametrize("bad", ["x", "1", "", "PP", " "])
    def test_from_symbol_errors(self, bad: str):
        with pytest.raises(ValueError):
            DcsPiece.from_symbol(bad)

    def test_equality(self):
        for pt in range(1, 7):
            for color in [True, False]:
                a = DcsPiece(pt, color)
                b = DcsPiece(pt, color)
                assert a == b
                assert not (a != b)

    def test_inequality(self):
        assert DcsPiece(1, True) != DcsPiece(1, False)
        assert DcsPiece(1, True) != DcsPiece(2, True)

    def test_hash_consistency(self):
        seen = set()
        for pt in range(1, 7):
            for color in [True, False]:
                d = DcsPiece(pt, color)
                r = ref.Piece(pt, color)
                assert hash(d) == hash(r)
                seen.add(hash(d))
        assert len(seen) == 12

    def test_copy(self):
        p = DcsPiece(5, True)
        c = copy.copy(p)
        assert c == p
        assert c is not p

    def test_deepcopy(self):
        p = DcsPiece(3, False)
        c = copy.deepcopy(p)
        assert c == p
        assert c is not p

    def test_str(self):
        for pt in range(1, 7):
            for color in [True, False]:
                d = DcsPiece(pt, color)
                r = ref.Piece(pt, color)
                assert str(d) == str(r)
