"""ADV adversarial differential tests for ENG-006: Score/PovScore/Wdl/WDL models.

These tests go beyond ENG2's 580-test suite, targeting edge cases in:
- MateGiven vs Mate(0) semantics (they are distinct!)
- Mate(0).score(mate_score=X) sign
- Wdl/PovWdl iteration protocol
- Score ordering completeness
- Hash behavior
- Extreme WDL model inputs
"""

from __future__ import annotations

import chess.engine as ref
import pytest

from dcs_chess.engine.scores import (
    Score, Cp, Mate, MateGiven, PovScore, Wdl, PovWdl, compute_wdl,
)


# =========================================================================
# MateGiven vs Mate(0) — distinct semantics
# =========================================================================

class TestMateGivenVsMateZero:
    """MateGiven means 'you just delivered checkmate' (best outcome).
    Mate(0) means 'you are checkmated' (worst outcome).
    They must NOT be equal."""

    def test_mategiven_not_equal_mate_zero(self):
        assert (MateGiven == Mate(0)) == (ref.MateGiven == ref.Mate(0))

    def test_mate_zero_not_equal_mategiven(self):
        assert (Mate(0) == MateGiven) == (ref.Mate(0) == ref.MateGiven)

    def test_mategiven_not_isinstance_mate(self):
        assert isinstance(MateGiven, Mate) == isinstance(ref.MateGiven, ref.Mate)

    def test_mategiven_isinstance_score(self):
        assert isinstance(MateGiven, Score) == isinstance(ref.MateGiven, ref.Score)


class TestMateZeroScore:
    """Mate(0).score(mate_score=X) must return -X (you are mated),
    while MateGiven.score(mate_score=X) returns +X (you delivered mate)."""

    @pytest.mark.parametrize("ms", [100, 10000, 100000, 1])
    def test_mate_zero_score_with_mate_score(self, ms: int):
        assert Mate(0).score(mate_score=ms) == ref.Mate(0).score(mate_score=ms)

    @pytest.mark.parametrize("ms", [100, 10000, 100000, 1])
    def test_mategiven_score_with_mate_score(self, ms: int):
        assert MateGiven.score(mate_score=ms) == ref.MateGiven.score(mate_score=ms)

    def test_mate_zero_score_none(self):
        assert Mate(0).score() is None
        assert ref.Mate(0).score() is None

    def test_mategiven_score_none(self):
        assert MateGiven.score() is None
        assert ref.MateGiven.score() is None


# =========================================================================
# Wdl iteration protocol
# =========================================================================

class TestWdlIteration:
    """python-chess Wdl supports iteration (yields wins, draws, losses)."""

    def test_wdl_is_iterable(self):
        w = Wdl(500, 300, 200)
        rw = ref.Wdl(500, 300, 200)
        assert list(w) == list(rw)

    def test_wdl_destructure(self):
        w = Wdl(500, 300, 200)
        a, b, c = w
        ra, rb, rc = ref.Wdl(500, 300, 200)
        assert (a, b, c) == (ra, rb, rc)

    @pytest.mark.parametrize("vals", [(0, 0, 1000), (1000, 0, 0), (333, 334, 333)])
    def test_wdl_list_parametric(self, vals: tuple[int, int, int]):
        w, d, l = vals
        assert list(Wdl(w, d, l)) == list(ref.Wdl(w, d, l))


class TestPovWdlIteration:
    """python-chess PovWdl also supports iteration."""

    def test_povwdl_is_iterable(self):
        pw = PovWdl(Wdl(500, 300, 200), True)
        rpw = ref.PovWdl(ref.Wdl(500, 300, 200), True)
        assert list(pw) == list(rpw)

    def test_povwdl_black_iterable(self):
        pw = PovWdl(Wdl(500, 300, 200), False)
        rpw = ref.PovWdl(ref.Wdl(500, 300, 200), False)
        assert list(pw) == list(rpw)


# =========================================================================
# Score hashability
# =========================================================================

class TestScoreHashability:
    """All Score subclasses define __eq__ and must be unhashable."""

    def test_cp_not_hashable(self):
        with pytest.raises(TypeError):
            hash(Cp(100))

    def test_mate_not_hashable(self):
        with pytest.raises(TypeError):
            hash(Mate(1))

    def test_mategiven_not_hashable(self):
        with pytest.raises(TypeError):
            hash(MateGiven)


# =========================================================================
# Score ordering — comprehensive
# =========================================================================

class TestScoreOrderingComprehensive:
    """Every pair in the score total order must match python-chess."""

    _OUR_SCORES = [
        Mate(-1), Mate(-3), Cp(-1000), Cp(-100), Cp(0),
        Cp(100), Cp(1000), Mate(3), Mate(1), MateGiven,
    ]
    _REF_SCORES = [
        ref.Mate(-1), ref.Mate(-3), ref.Cp(-1000), ref.Cp(-100), ref.Cp(0),
        ref.Cp(100), ref.Cp(1000), ref.Mate(3), ref.Mate(1), ref.MateGiven,
    ]

    @pytest.mark.parametrize("i", range(10))
    @pytest.mark.parametrize("j", range(10))
    def test_lt(self, i: int, j: int):
        ours = self._OUR_SCORES[i] < self._OUR_SCORES[j]
        theirs = self._REF_SCORES[i] < self._REF_SCORES[j]
        assert ours == theirs, (
            f"{self._OUR_SCORES[i]!r} < {self._OUR_SCORES[j]!r}: ours={ours}, ref={theirs}"
        )

    @pytest.mark.parametrize("i", range(10))
    @pytest.mark.parametrize("j", range(10))
    def test_eq(self, i: int, j: int):
        ours = self._OUR_SCORES[i] == self._OUR_SCORES[j]
        theirs = self._REF_SCORES[i] == self._REF_SCORES[j]
        assert ours == theirs, (
            f"{self._OUR_SCORES[i]!r} == {self._OUR_SCORES[j]!r}: ours={ours}, ref={theirs}"
        )

    @pytest.mark.parametrize("i", range(10))
    @pytest.mark.parametrize("j", range(10))
    def test_le(self, i: int, j: int):
        ours = self._OUR_SCORES[i] <= self._OUR_SCORES[j]
        theirs = self._REF_SCORES[i] <= self._REF_SCORES[j]
        assert ours == theirs

    @pytest.mark.parametrize("i", range(10))
    @pytest.mark.parametrize("j", range(10))
    def test_gt(self, i: int, j: int):
        ours = self._OUR_SCORES[i] > self._OUR_SCORES[j]
        theirs = self._REF_SCORES[i] > self._REF_SCORES[j]
        assert ours == theirs

    @pytest.mark.parametrize("i", range(10))
    @pytest.mark.parametrize("j", range(10))
    def test_ge(self, i: int, j: int):
        ours = self._OUR_SCORES[i] >= self._OUR_SCORES[j]
        theirs = self._REF_SCORES[i] >= self._REF_SCORES[j]
        assert ours == theirs


# =========================================================================
# Score negation roundtrip
# =========================================================================

class TestScoreNegation:

    @pytest.mark.parametrize("cp", [-1000, -1, 0, 1, 1000])
    def test_cp_neg_neg(self, cp: int):
        assert (--Cp(cp)).score() == (--ref.Cp(cp)).score()

    @pytest.mark.parametrize("moves", [-3, -1, 0, 1, 3])
    def test_mate_neg_neg(self, moves: int):
        assert (--Mate(moves)).mate() == (--ref.Mate(moves)).mate()

    def test_mategiven_neg(self):
        neg = -MateGiven
        rneg = -ref.MateGiven
        assert repr(neg) == repr(rneg)
        assert type(neg).__name__ == type(rneg).__name__


# =========================================================================
# WDL models — extreme and boundary inputs
# =========================================================================

class TestWdlModelExtremes:

    @pytest.mark.parametrize("model", ["sf", "sf12", "sf14", "sf15", "sf15.1", "sf16", "sf16.1"])
    def test_extreme_positive_cp(self, model: str):
        ours = compute_wdl(10000, model=model, ply=30)
        theirs = ref.Cp(10000).wdl(model=model, ply=30)
        assert (ours.wins, ours.draws, ours.losses) == (theirs.wins, theirs.draws, theirs.losses)

    @pytest.mark.parametrize("model", ["sf", "sf12", "sf14", "sf15", "sf15.1", "sf16", "sf16.1"])
    def test_extreme_negative_cp(self, model: str):
        ours = compute_wdl(-10000, model=model, ply=30)
        theirs = ref.Cp(-10000).wdl(model=model, ply=30)
        assert (ours.wins, ours.draws, ours.losses) == (theirs.wins, theirs.draws, theirs.losses)

    @pytest.mark.parametrize("model", ["sf", "sf12", "sf14", "sf15", "sf15.1", "sf16", "sf16.1"])
    def test_zero_ply(self, model: str):
        ours = compute_wdl(100, model=model, ply=0)
        theirs = ref.Cp(100).wdl(model=model, ply=0)
        assert (ours.wins, ours.draws, ours.losses) == (theirs.wins, theirs.draws, theirs.losses)

    @pytest.mark.parametrize("model", ["sf", "sf12", "sf14", "sf15", "sf15.1", "sf16", "sf16.1"])
    def test_negative_ply(self, model: str):
        ours = compute_wdl(100, model=model, ply=-10)
        theirs = ref.Cp(100).wdl(model=model, ply=-10)
        assert (ours.wins, ours.draws, ours.losses) == (theirs.wins, theirs.draws, theirs.losses)

    @pytest.mark.parametrize("model", ["sf", "sf12", "sf14", "sf15", "sf15.1", "sf16", "sf16.1"])
    def test_ply_500(self, model: str):
        ours = compute_wdl(100, model=model, ply=500)
        theirs = ref.Cp(100).wdl(model=model, ply=500)
        assert (ours.wins, ours.draws, ours.losses) == (theirs.wins, theirs.draws, theirs.losses)

    def test_unknown_model_raises(self):
        with pytest.raises(ValueError):
            compute_wdl(100, model="unknown")


# =========================================================================
# Wdl edge cases
# =========================================================================

class TestWdlEdgeCases:

    def test_zero_total_division(self):
        w = Wdl(0, 0, 0)
        rw = ref.Wdl(0, 0, 0)
        assert w.total() == rw.total() == 0

    def test_repr_matches_reference(self):
        for vals in [(0, 0, 0), (1000, 0, 0), (0, 0, 1000), (333, 334, 333)]:
            assert repr(Wdl(*vals)) == repr(ref.Wdl(*vals))


# =========================================================================
# PovScore edge cases
# =========================================================================

class TestPovScoreEdgeCases:

    def test_povscore_mate_white_from_black(self):
        ps = PovScore(Mate(3), False)
        rps = ref.PovScore(ref.Mate(3), False)
        assert ps.white().mate() == rps.white().mate()
        assert ps.black().mate() == rps.black().mate()

    def test_povscore_pov_flip(self):
        ps = PovScore(Cp(200), True)
        rps = ref.PovScore(ref.Cp(200), True)
        assert ps.pov(True).score() == rps.pov(True).score()
        assert ps.pov(False).score() == rps.pov(False).score()

    def test_povscore_equality(self):
        a = PovScore(Cp(100), True)
        b = PovScore(Cp(-100), False)
        ra = ref.PovScore(ref.Cp(100), True)
        rb = ref.PovScore(ref.Cp(-100), False)
        assert (a == b) == (ra == rb)

    def test_povscore_wdl_returns_povwdl(self):
        ps = PovScore(Cp(100), True)
        rps = ref.PovScore(ref.Cp(100), True)
        ours = ps.wdl()
        theirs = rps.wdl()
        assert type(ours).__name__ == type(theirs).__name__
        ow = ours.white()
        tw = theirs.white()
        assert (ow.wins, ow.draws, ow.losses) == (tw.wins, tw.draws, tw.losses)

    def test_povscore_repr(self):
        for turn in [True, False]:
            for score_args in [(Cp, 100), (Mate, 3), (Mate, -1)]:
                cls, val = score_args
                ours = repr(PovScore(cls(val), turn))
                ref_cls = getattr(ref, cls.__name__)
                theirs = repr(ref.PovScore(ref_cls(val), turn))
                assert ours == theirs, f"PovScore({cls.__name__}({val}), {turn}): {ours!r} != {theirs!r}"


# =========================================================================
# PovWdl edge cases
# =========================================================================

class TestPovWdlEdgeCases:

    def test_povwdl_white(self):
        pw = PovWdl(Wdl(600, 200, 200), True)
        rpw = ref.PovWdl(ref.Wdl(600, 200, 200), True)
        w = pw.white()
        rw = rpw.white()
        assert (w.wins, w.draws, w.losses) == (rw.wins, rw.draws, rw.losses)

    def test_povwdl_black(self):
        pw = PovWdl(Wdl(600, 200, 200), True)
        rpw = ref.PovWdl(ref.Wdl(600, 200, 200), True)
        b = pw.black()
        rb = rpw.black()
        assert (b.wins, b.draws, b.losses) == (rb.wins, rb.draws, rb.losses)

    def test_povwdl_equality(self):
        a = PovWdl(Wdl(600, 200, 200), True)
        b = PovWdl(Wdl(200, 200, 600), False)
        ra = ref.PovWdl(ref.Wdl(600, 200, 200), True)
        rb = ref.PovWdl(ref.Wdl(200, 200, 600), False)
        assert (a == b) == (ra == rb)

    def test_povwdl_repr(self):
        for turn in [True, False]:
            ours = repr(PovWdl(Wdl(500, 300, 200), turn))
            theirs = repr(ref.PovWdl(ref.Wdl(500, 300, 200), turn))
            assert ours == theirs, f"turn={turn}: {ours!r} != {theirs!r}"
