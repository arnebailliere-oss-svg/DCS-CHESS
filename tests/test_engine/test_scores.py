"""Differential tests for ENG-006: Score, PovScore, Wdl, WDL models (FR-E6)."""

from __future__ import annotations

import chess.engine as ref
import pytest

from dcs_chess.engine.scores import (
    Score, Cp, Mate, MateGiven, PovScore, Wdl, PovWdl, compute_wdl,
)


class TestCp:
    def test_score(self):
        assert Cp(150).score() == ref.Cp(150).score()

    def test_mate_is_none(self):
        assert Cp(100).mate() is None
        assert ref.Cp(100).mate() is None

    def test_is_mate_false(self):
        assert Cp(0).is_mate() is False

    def test_negation(self):
        assert (-Cp(100)).score() == (-ref.Cp(100)).score()

    @pytest.mark.parametrize("cp", [0, 100, 150, -100, -200, 1, -1])
    def test_repr(self, cp: int):
        assert repr(Cp(cp)) == repr(ref.Cp(cp))

    @pytest.mark.parametrize("cp", [0, 100, 150, -100, -200, 1, -1])
    def test_str(self, cp: int):
        assert str(Cp(cp)) == str(ref.Cp(cp))

    def test_equality(self):
        assert Cp(100) == Cp(100)
        assert not (Cp(100) == Cp(200))

    def test_inequality_with_mate(self):
        assert not (Cp(100) == Mate(1))


class TestMate:
    @pytest.mark.parametrize("moves", [1, 3, -1, -3, 0])
    def test_mate_value(self, moves: int):
        assert Mate(moves).mate() == ref.Mate(moves).mate()

    def test_score_none(self):
        assert Mate(3).score() is None

    @pytest.mark.parametrize("moves,ms", [(3, 100000), (-3, 100000), (1, 50000), (-1, 50000)])
    def test_score_with_mate_score(self, moves: int, ms: int):
        assert Mate(moves).score(mate_score=ms) == ref.Mate(moves).score(mate_score=ms)

    def test_negation(self):
        assert (-Mate(3)).mate() == (-ref.Mate(3)).mate()

    @pytest.mark.parametrize("moves", [1, 3, -1, -3, 0])
    def test_repr(self, moves: int):
        assert repr(Mate(moves)) == repr(ref.Mate(moves))

    @pytest.mark.parametrize("moves", [1, 3, -1, -3, 0])
    def test_str(self, moves: int):
        assert str(Mate(moves)) == str(ref.Mate(moves))


class TestMateGiven:
    def test_mate_zero(self):
        assert MateGiven.mate() == 0

    def test_score_none(self):
        assert MateGiven.score() is None

    def test_repr(self):
        assert repr(MateGiven) == repr(ref.MateGiven)

    def test_str(self):
        assert str(MateGiven) == str(ref.MateGiven)

    def test_is_mate(self):
        assert MateGiven.is_mate() is True


class TestScoreOrdering:
    def test_cp_less_than_mate(self):
        assert (Cp(10000) < Mate(1)) == (ref.Cp(10000) < ref.Mate(1))

    def test_mate_negative_less_than_cp(self):
        assert (Mate(-1) < Cp(-10000)) == (ref.Mate(-1) < ref.Cp(-10000))

    def test_mate1_greater_than_mate3(self):
        assert (Mate(1) > Mate(3)) == (ref.Mate(1) > ref.Mate(3))

    def test_mate_neg1_less_than_mate_neg3(self):
        assert (Mate(-1) < Mate(-3)) == (ref.Mate(-1) < ref.Mate(-3))

    def test_cp_ordering(self):
        assert (Cp(100) < Cp(200)) == (ref.Cp(100) < ref.Cp(200))
        assert (Cp(-100) < Cp(100)) == (ref.Cp(-100) < ref.Cp(100))


class TestPovScore:
    def test_white(self):
        ps = PovScore(Cp(150), True)
        rps = ref.PovScore(ref.Cp(150), True)
        assert ps.white().score() == rps.white().score()

    def test_black(self):
        ps = PovScore(Cp(150), True)
        rps = ref.PovScore(ref.Cp(150), True)
        assert ps.black().score() == rps.black().score()

    def test_pov(self):
        ps = PovScore(Cp(150), True)
        rps = ref.PovScore(ref.Cp(150), True)
        assert ps.pov(False).score() == rps.pov(False).score()

    def test_repr(self):
        assert repr(PovScore(Cp(150), True)) == repr(ref.PovScore(ref.Cp(150), True))

    def test_is_mate(self):
        assert PovScore(Mate(3), True).is_mate() is True
        assert PovScore(Cp(100), True).is_mate() is False


class TestWdl:
    def test_total(self):
        w = Wdl(500, 300, 200)
        assert w.total() == 1000

    def test_winning_chance(self):
        w = Wdl(500, 300, 200)
        rw = ref.Wdl(500, 300, 200)
        assert w.winning_chance() == rw.winning_chance()

    def test_drawing_chance(self):
        w = Wdl(500, 300, 200)
        rw = ref.Wdl(500, 300, 200)
        assert w.drawing_chance() == rw.drawing_chance()

    def test_losing_chance(self):
        w = Wdl(500, 300, 200)
        rw = ref.Wdl(500, 300, 200)
        assert w.losing_chance() == rw.losing_chance()

    def test_expectation(self):
        w = Wdl(500, 300, 200)
        rw = ref.Wdl(500, 300, 200)
        assert w.expectation() == rw.expectation()

    def test_negation(self):
        w = -Wdl(500, 300, 200)
        rw = -ref.Wdl(500, 300, 200)
        assert (w.wins, w.draws, w.losses) == (rw.wins, rw.draws, rw.losses)

    def test_equality(self):
        assert Wdl(500, 300, 200) == Wdl(500, 300, 200)
        assert not (Wdl(500, 300, 200) == Wdl(400, 300, 300))

    def test_repr(self):
        assert repr(Wdl(500, 300, 200)) == repr(ref.Wdl(500, 300, 200))


class TestWdlModels:
    @pytest.mark.parametrize("model", ["sf", "sf12", "sf14", "sf15", "sf15.1", "sf16", "sf16.1"])
    @pytest.mark.parametrize("ply", [1, 8, 16, 30, 50, 100, 200, 240])
    @pytest.mark.parametrize("cp", [-500, -200, -100, -50, 0, 50, 100, 200, 500])
    def test_sf_model_matches_reference(self, model: str, ply: int, cp: int):
        ours = compute_wdl(cp, model=model, ply=ply)
        theirs = ref.Cp(cp).wdl(model=model, ply=ply)
        assert (ours.wins, ours.draws, ours.losses) == (theirs.wins, theirs.draws, theirs.losses), (
            f"{model} ply={ply} cp={cp}: ours=({ours.wins},{ours.draws},{ours.losses}) "
            f"ref=({theirs.wins},{theirs.draws},{theirs.losses})"
        )

    @pytest.mark.parametrize("cp", [-1000, -500, -200, -100, -50, 0, 50, 100, 200, 500, 1000])
    def test_lichess_model_matches_reference(self, cp: int):
        ours = compute_wdl(cp, model="lichess")
        theirs = ref.Cp(cp).wdl(model="lichess")
        assert (ours.wins, ours.draws, ours.losses) == (theirs.wins, theirs.draws, theirs.losses)

    def test_mate_wdl(self):
        assert Mate(1).wdl() == Wdl(1000, 0, 0)
        assert Mate(-1).wdl() == Wdl(0, 0, 1000)
        assert MateGiven.wdl() == Wdl(1000, 0, 0)
