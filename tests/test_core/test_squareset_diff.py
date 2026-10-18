"""Differential tests for CORE-006: SquareSet class (FR-C5)."""

from __future__ import annotations

import random

import chess as ref
import pytest

from dcs_chess.core.squareset import SquareSet as DcsSquareSet


_TEST_MASKS = [
    0, 1, 0xFF, 0xFF00, 0x0101010101010101,
    0x8040201008040201, 0xAAAAAAAAAAAAAAAA,
    0x5555555555555555, 0xFFFFFFFFFFFFFFFF,
    0x00000000000000FF, 0xFF00000000000000,
    0x8000000000000001,
]


class TestSquareSetConstruction:
    @pytest.mark.parametrize("mask", _TEST_MASKS)
    def test_from_mask(self, mask: int):
        d = DcsSquareSet(mask)
        r = ref.SquareSet(mask)
        assert int(d) == int(r)

    def test_from_iterable(self):
        squares = [0, 7, 27, 63]
        d = DcsSquareSet(squares)
        r = ref.SquareSet(squares)
        assert int(d) == int(r)


class TestSquareSetContainer:
    @pytest.mark.parametrize("mask", _TEST_MASKS)
    def test_len(self, mask: int):
        assert len(DcsSquareSet(mask)) == len(ref.SquareSet(mask))

    @pytest.mark.parametrize("mask", _TEST_MASKS)
    def test_bool(self, mask: int):
        assert bool(DcsSquareSet(mask)) == bool(ref.SquareSet(mask))

    @pytest.mark.parametrize("mask", _TEST_MASKS)
    def test_contains(self, mask: int):
        d = DcsSquareSet(mask)
        r = ref.SquareSet(mask)
        for sq in range(64):
            assert (sq in d) == (sq in r), f"sq={sq} mask=0x{mask:x}"

    @pytest.mark.parametrize("mask", _TEST_MASKS)
    def test_iter(self, mask: int):
        assert list(DcsSquareSet(mask)) == list(ref.SquareSet(mask))

    @pytest.mark.parametrize("mask", _TEST_MASKS)
    def test_reversed(self, mask: int):
        assert list(reversed(DcsSquareSet(mask))) == list(reversed(ref.SquareSet(mask)))


class TestSquareSetBitwise:
    @pytest.mark.parametrize("a", _TEST_MASKS[:6])
    @pytest.mark.parametrize("b", _TEST_MASKS[:6])
    def test_and(self, a: int, b: int):
        assert int(DcsSquareSet(a) & DcsSquareSet(b)) == int(ref.SquareSet(a) & ref.SquareSet(b))

    @pytest.mark.parametrize("a", _TEST_MASKS[:6])
    @pytest.mark.parametrize("b", _TEST_MASKS[:6])
    def test_or(self, a: int, b: int):
        assert int(DcsSquareSet(a) | DcsSquareSet(b)) == int(ref.SquareSet(a) | ref.SquareSet(b))

    @pytest.mark.parametrize("a", _TEST_MASKS[:6])
    @pytest.mark.parametrize("b", _TEST_MASKS[:6])
    def test_xor(self, a: int, b: int):
        assert int(DcsSquareSet(a) ^ DcsSquareSet(b)) == int(ref.SquareSet(a) ^ ref.SquareSet(b))

    @pytest.mark.parametrize("a", _TEST_MASKS[:6])
    @pytest.mark.parametrize("b", _TEST_MASKS[:6])
    def test_sub(self, a: int, b: int):
        assert int(DcsSquareSet(a) - DcsSquareSet(b)) == int(ref.SquareSet(a) - ref.SquareSet(b))

    @pytest.mark.parametrize("mask", _TEST_MASKS)
    def test_invert(self, mask: int):
        assert int(~DcsSquareSet(mask)) == int(~ref.SquareSet(mask))

    @pytest.mark.parametrize("mask", _TEST_MASKS)
    @pytest.mark.parametrize("shift", [0, 1, 8, 16, 63])
    def test_lshift(self, mask: int, shift: int):
        assert int(DcsSquareSet(mask) << shift) == int(ref.SquareSet(mask) << shift)

    @pytest.mark.parametrize("mask", _TEST_MASKS)
    @pytest.mark.parametrize("shift", [0, 1, 8, 16, 63])
    def test_rshift(self, mask: int, shift: int):
        assert int(DcsSquareSet(mask) >> shift) == int(ref.SquareSet(mask) >> shift)


class TestSquareSetEquality:
    def test_eq_squareset(self):
        a = DcsSquareSet(0xFF)
        b = DcsSquareSet(0xFF)
        assert a == b

    @pytest.mark.parametrize("mask", _TEST_MASKS)
    def test_eq_int(self, mask: int):
        assert DcsSquareSet(mask) == mask
        assert mask == DcsSquareSet(mask)

    def test_not_hashable(self):
        """python-chess SquareSet is mutable and NOT hashable."""
        with pytest.raises(TypeError):
            hash(ref.SquareSet(0xFF))
        # Our SquareSet should also be unhashable for parity
        with pytest.raises(TypeError):
            hash(DcsSquareSet(0xFF))


class TestSquareSetMutableMethods:
    def test_add_discard_remove(self):
        d = DcsSquareSet(0)
        r = ref.SquareSet(0)
        for sq in [0, 27, 63]:
            d.add(sq)
            r.add(sq)
        assert int(d) == int(r)
        d.discard(27)
        r.discard(27)
        assert int(d) == int(r)
        d.remove(0)
        r.remove(0)
        assert int(d) == int(r)

    def test_remove_missing_raises(self):
        d = DcsSquareSet(0)
        with pytest.raises(KeyError):
            d.remove(0)

    def test_pop(self):
        d = DcsSquareSet(0xFF)
        r = ref.SquareSet(0xFF)
        d_popped = []
        r_popped = []
        while d:
            d_popped.append(d.pop())
        while r:
            r_popped.append(r.pop())
        assert d_popped == r_popped

    def test_pop_empty_raises(self):
        with pytest.raises(KeyError):
            DcsSquareSet(0).pop()

    def test_clear(self):
        d = DcsSquareSet(0xFFFF)
        d.clear()
        assert int(d) == 0


class TestSquareSetAlgebra:
    def test_union(self):
        a, b = 0xFF, 0xFF00
        assert int(DcsSquareSet(a).union(b)) == int(ref.SquareSet(a).union(b))

    def test_intersection(self):
        a, b = 0xFFFF, 0xFF00
        assert int(DcsSquareSet(a).intersection(b)) == int(ref.SquareSet(a).intersection(b))

    def test_difference(self):
        a, b = 0xFFFF, 0xFF00
        assert int(DcsSquareSet(a).difference(b)) == int(ref.SquareSet(a).difference(b))

    def test_symmetric_difference(self):
        a, b = 0xFFFF, 0xFF00
        assert int(DcsSquareSet(a).symmetric_difference(b)) == int(ref.SquareSet(a).symmetric_difference(b))

    def test_issubset(self):
        assert DcsSquareSet(0xFF).issubset(0xFFFF)
        assert not DcsSquareSet(0xFFFF).issubset(0xFF)

    def test_issuperset(self):
        assert DcsSquareSet(0xFFFF).issuperset(0xFF)
        assert not DcsSquareSet(0xFF).issuperset(0xFFFF)

    def test_isdisjoint(self):
        assert DcsSquareSet(0xFF).isdisjoint(0xFF00)
        assert not DcsSquareSet(0xFF).isdisjoint(0x0F)


class TestSquareSetOther:
    def test_copy(self):
        s = DcsSquareSet(0xABCD)
        c = s.copy()
        assert int(c) == int(s)
        c.add(4)  # bit 4 is NOT set in 0xABCD
        assert int(c) != int(s), "copy() should return an independent object"

    def test_tolist(self):
        """python-chess tolist() returns 64 booleans, not a list of square indices."""
        d = DcsSquareSet(0xFF)
        r = ref.SquareSet(0xFF)
        assert d.tolist() == r.tolist()
        assert len(d.tolist()) == 64
        assert all(isinstance(v, bool) for v in d.tolist())

    @pytest.mark.parametrize("mask", _TEST_MASKS)
    def test_mirror(self, mask: int):
        assert int(DcsSquareSet(mask).mirror()) == int(ref.SquareSet(mask).mirror())

    def test_carry_rippler_count(self):
        mask = 0x0F
        d_subsets = list(DcsSquareSet(mask).carry_rippler())
        r_subsets = list(ref.SquareSet(mask).carry_rippler())
        assert len(d_subsets) == len(r_subsets)
        assert [int(s) for s in d_subsets] == [int(s) for s in r_subsets]

    def test_class_methods(self):
        d_ray = DcsSquareSet.ray(0, 63)
        r_ray = ref.SquareSet.ray(0, 63)
        assert int(d_ray) == int(r_ray)

        d_between = DcsSquareSet.between(0, 63)
        r_between = ref.SquareSet.between(0, 63)
        assert int(d_between) == int(r_between)

        d_sq = DcsSquareSet.from_square(27)
        r_sq = ref.SquareSet.from_square(27)
        assert int(d_sq) == int(r_sq)


class TestSquareSetStr:
    @pytest.mark.parametrize("mask", [0, 0xFF, 0x0101010101010101, 0xFFFFFFFFFFFFFFFF])
    def test_str_matches(self, mask: int):
        assert str(DcsSquareSet(mask)) == str(ref.SquareSet(mask))
