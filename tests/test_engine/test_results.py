"""Differential tests for ENG-005: PlayResult, BestMove, AnalysisResult, etc. (FR-E5)."""

from __future__ import annotations

import asyncio
import dataclasses

import chess
import chess.engine as ref
import pytest

from dcs_chess.engine.results import (
    EngineError,
    EngineTerminatedError,
    Info,
    INFO_NONE,
    INFO_BASIC,
    INFO_SCORE,
    INFO_PV,
    INFO_REFUTATION,
    INFO_CURRLINE,
    INFO_ALL,
    InfoDict,
    PlayResult,
    BestMove,
    AnalysisResult,
    AnalysisComplete,
    Opponent,
    Limit,
    Option,
    UciOptionMap,
    MANAGED_OPTIONS,
    MockTransport,
)


class TestEngineErrors:
    def test_engine_error_is_runtime_error(self):
        assert issubclass(EngineError, RuntimeError)
        assert issubclass(ref.EngineError, RuntimeError)

    def test_engine_terminated_error_is_engine_error(self):
        assert issubclass(EngineTerminatedError, EngineError)
        assert issubclass(ref.EngineTerminatedError, ref.EngineError)

    def test_engine_error_message(self):
        e = EngineError("test")
        assert str(e) == "test"

    def test_engine_terminated_error_message(self):
        e = EngineTerminatedError("process died")
        assert str(e) == "process died"


class TestInfo:
    def test_info_none_value(self):
        assert INFO_NONE == ref.INFO_NONE

    def test_info_basic_value(self):
        assert INFO_BASIC == ref.INFO_BASIC

    def test_info_score_value(self):
        assert INFO_SCORE == ref.INFO_SCORE

    def test_info_pv_value(self):
        assert INFO_PV == ref.INFO_PV

    def test_info_refutation_value(self):
        assert INFO_REFUTATION == ref.INFO_REFUTATION

    def test_info_currline_value(self):
        assert INFO_CURRLINE == ref.INFO_CURRLINE

    def test_info_all_value(self):
        assert INFO_ALL == ref.INFO_ALL

    def test_info_is_intflag(self):
        assert issubclass(Info, int)
        assert issubclass(ref.Info, int)

    def test_info_combination(self):
        combined = INFO_BASIC | INFO_SCORE | INFO_PV
        ref_combined = ref.INFO_BASIC | ref.INFO_SCORE | ref.INFO_PV
        assert combined == ref_combined

    def test_info_all_is_combination(self):
        assert INFO_ALL == (INFO_BASIC | INFO_SCORE | INFO_PV | INFO_REFUTATION | INFO_CURRLINE)


class TestPlayResult:
    def test_basic_construction(self):
        move = chess.Move.from_uci("e2e4")
        ponder = chess.Move.from_uci("e7e5")
        pr = PlayResult(move, ponder)
        rpr = ref.PlayResult(move, ponder)
        assert pr.move == rpr.move
        assert pr.ponder == rpr.ponder
        assert pr.draw_offered == rpr.draw_offered
        assert pr.resigned == rpr.resigned

    def test_none_move(self):
        pr = PlayResult(None, None)
        rpr = ref.PlayResult(None, None)
        assert pr.move == rpr.move
        assert pr.ponder == rpr.ponder

    def test_default_info_is_empty_dict(self):
        pr = PlayResult(None, None)
        rpr = ref.PlayResult(None, None)
        assert pr.info == rpr.info
        assert pr.info == {}

    def test_draw_offered(self):
        pr = PlayResult(None, None, draw_offered=True)
        rpr = ref.PlayResult(None, None, draw_offered=True)
        assert pr.draw_offered == rpr.draw_offered is True

    def test_resigned(self):
        pr = PlayResult(None, None, resigned=True)
        rpr = ref.PlayResult(None, None, resigned=True)
        assert pr.resigned == rpr.resigned is True

    def test_with_info(self):
        info: InfoDict = {"depth": 20, "nodes": 1000}
        pr = PlayResult(None, None, info)
        assert pr.info == info

    def test_repr_contains_fields(self):
        move = chess.Move.from_uci("e2e4")
        pr = PlayResult(move, None)
        r = repr(pr)
        assert "PlayResult" in r
        assert "e2e4" in r
        assert "ponder=None" in r


class TestBestMove:
    def test_basic_construction(self):
        move = chess.Move.from_uci("e2e4")
        ponder = chess.Move.from_uci("e7e5")
        bm = BestMove(move, ponder)
        rbm = ref.BestMove(move, ponder)
        assert bm.move == rbm.move
        assert bm.ponder == rbm.ponder

    def test_none_move(self):
        bm = BestMove(None, None)
        rbm = ref.BestMove(None, None)
        assert bm.move == rbm.move
        assert bm.ponder == rbm.ponder

    def test_repr_contains_fields(self):
        move = chess.Move.from_uci("d2d4")
        bm = BestMove(move, None)
        r = repr(bm)
        assert "BestMove" in r
        assert "d2d4" in r


class TestAnalysisComplete:
    def test_is_exception(self):
        assert issubclass(AnalysisComplete, Exception)
        assert issubclass(ref.AnalysisComplete, Exception)

    def test_can_raise(self):
        with pytest.raises(AnalysisComplete):
            raise AnalysisComplete()


class TestAnalysisResult:
    def test_default_multipv(self):
        ar = AnalysisResult()
        rar = ref.AnalysisResult()
        assert ar.multipv == rar.multipv

    def test_default_info(self):
        ar = AnalysisResult()
        rar = ref.AnalysisResult()
        assert ar.info == rar.info

    def test_post_updates_info(self):
        ar = AnalysisResult()
        ar.post({"depth": 10, "nodes": 100})
        assert ar.info == {"depth": 10, "nodes": 100}

    def test_post_updates_multipv(self):
        ar = AnalysisResult()
        ar.post({"depth": 10, "multipv": 1})
        ar.post({"depth": 10, "multipv": 2})
        rar = ref.AnalysisResult()
        rar.post({"depth": 10, "multipv": 1})
        rar.post({"depth": 10, "multipv": 2})
        assert ar.multipv == rar.multipv

    def test_would_block_empty(self):
        ar = AnalysisResult()
        assert ar.would_block() is True

    def test_would_block_after_post(self):
        ar = AnalysisResult()
        ar.post({"depth": 5})
        assert ar.would_block() is False

    def test_empty_initially(self):
        ar = AnalysisResult()
        assert ar.empty() is True

    def test_empty_after_post(self):
        ar = AnalysisResult()
        ar.post({"depth": 5})
        assert ar.empty() is False

    def test_get_returns_posted_info(self):
        async def _test():
            ar = AnalysisResult()
            ar.post({"depth": 10})
            info = await ar.get()
            assert info == {"depth": 10}
        asyncio.run(_test())

    def test_next_returns_posted_info(self):
        async def _test():
            ar = AnalysisResult()
            ar.post({"depth": 5})
            ar.post({"depth": 10})
            r1 = await ar.next()
            r2 = await ar.next()
            assert r1 == {"depth": 5}
            assert r2 == {"depth": 10}
        asyncio.run(_test())

    def test_set_finished(self):
        async def _test():
            ar = AnalysisResult()
            bm = BestMove(None, None)
            ar.set_finished(bm)
            result = await ar.wait()
            assert result.move is None
            assert result.ponder is None
        asyncio.run(_test())

    def test_set_exception(self):
        async def _test():
            ar = AnalysisResult()
            ar.set_exception(RuntimeError("engine died"))
            with pytest.raises(RuntimeError, match="engine died"):
                await ar.wait()
        asyncio.run(_test())

    def test_async_iteration(self):
        async def _test():
            ar = AnalysisResult()
            ar.post({"depth": 1})
            ar.post({"depth": 2})
            ar.post({"depth": 3})
            ar.set_finished(BestMove(None, None))
            results = []
            async for info in ar:
                results.append(info)
            assert len(results) == 3
            assert results[0] == {"depth": 1}
            assert results[2] == {"depth": 3}
        asyncio.run(_test())

    def test_next_returns_none_after_finished(self):
        async def _test():
            ar = AnalysisResult()
            ar.set_finished(BestMove(None, None))
            result = await ar.next()
            assert result is None
        asyncio.run(_test())

    def test_stop_calls_callback(self):
        called = []
        ar = AnalysisResult(stop=lambda: called.append(True))
        ar.stop()
        assert called == [True]

    def test_stop_no_callback(self):
        ar = AnalysisResult()
        ar.stop()  # should not raise


class TestOpponent:
    def test_construction(self):
        op = Opponent("Stockfish", "GM", 3000, True)
        rop = ref.Opponent("Stockfish", "GM", 3000, True)
        assert op.name == rop.name
        assert op.title == rop.title
        assert op.rating == rop.rating
        assert op.is_engine == rop.is_engine

    def test_repr(self):
        op = Opponent("Stockfish", "GM", 3000, True)
        rop = ref.Opponent("Stockfish", "GM", 3000, True)
        assert repr(op) == repr(rop)

    def test_none_fields(self):
        op = Opponent(None, None, None, None)
        rop = ref.Opponent(None, None, None, None)
        assert repr(op) == repr(rop)

    def test_equality(self):
        o1 = Opponent("SF", None, 3000, True)
        o2 = Opponent("SF", None, 3000, True)
        assert o1 == o2

    def test_inequality(self):
        o1 = Opponent("SF", None, 3000, True)
        o2 = Opponent("LC0", None, 3000, True)
        assert o1 != o2

    @pytest.mark.parametrize(
        "name,title,rating,is_engine",
        [
            ("Stockfish", "GM", 3500, True),
            (None, None, None, None),
            ("Human", None, 1500, False),
            ("Engine", "IM", 2800, True),
        ],
    )
    def test_repr_matches_reference(self, name, title, rating, is_engine):
        op = Opponent(name, title, rating, is_engine)
        rop = ref.Opponent(name, title, rating, is_engine)
        assert repr(op) == repr(rop)


class TestLimit:
    def test_empty_limit(self):
        lim = Limit()
        rlim = ref.Limit()
        assert repr(lim) == repr(rlim)

    def test_time_only(self):
        lim = Limit(time=5.0)
        rlim = ref.Limit(time=5.0)
        assert repr(lim) == repr(rlim)

    def test_depth_only(self):
        lim = Limit(depth=20)
        rlim = ref.Limit(depth=20)
        assert repr(lim) == repr(rlim)

    def test_multiple_fields(self):
        lim = Limit(time=5.0, depth=20, nodes=1000000)
        rlim = ref.Limit(time=5.0, depth=20, nodes=1000000)
        assert repr(lim) == repr(rlim)

    def test_clock_fields(self):
        lim = Limit(white_clock=300.0, black_clock=300.0, white_inc=5.0, black_inc=5.0)
        rlim = ref.Limit(white_clock=300.0, black_clock=300.0, white_inc=5.0, black_inc=5.0)
        assert repr(lim) == repr(rlim)

    def test_remaining_moves(self):
        lim = Limit(remaining_moves=40)
        rlim = ref.Limit(remaining_moves=40)
        assert repr(lim) == repr(rlim)

    def test_clock_id_not_in_repr(self):
        lim = Limit(clock_id="game1")
        rlim = ref.Limit(clock_id="game1")
        assert repr(lim) == repr(rlim)

    def test_equality(self):
        l1 = Limit(time=5.0)
        l2 = Limit(time=5.0)
        assert l1 == l2

    def test_inequality(self):
        l1 = Limit(time=5.0)
        l2 = Limit(time=10.0)
        assert l1 != l2

    @pytest.mark.parametrize(
        "kwargs",
        [
            {},
            {"time": 0},
            {"time": 5.0},
            {"depth": 20},
            {"nodes": 1000000},
            {"mate": 5},
            {"time": 5.0, "depth": 20},
            {"white_clock": 300.0, "black_clock": 300.0},
            {"remaining_moves": 40},
            {"time": 10.0, "depth": 30, "nodes": 5000000},
        ],
    )
    def test_repr_matches_reference(self, kwargs):
        lim = Limit(**kwargs)
        rlim = ref.Limit(**kwargs)
        assert repr(lim) == repr(rlim)

    def test_is_dataclass(self):
        assert dataclasses.is_dataclass(Limit)
        assert dataclasses.is_dataclass(ref.Limit)

    def test_field_names_match(self):
        ours = {f.name for f in dataclasses.fields(Limit)}
        theirs = {f.name for f in dataclasses.fields(ref.Limit)}
        assert ours == theirs


class TestOption:
    def test_basic_construction(self):
        opt = Option("Hash", "spin", 16, 1, 1048576, None)
        ropt = ref.Option("Hash", "spin", 16, 1, 1048576, None)
        assert opt.name == ropt.name
        assert opt.type == ropt.type
        assert opt.default == ropt.default
        assert opt.min == ropt.min
        assert opt.max == ropt.max
        assert opt.var == ropt.var

    def test_is_managed(self):
        opt = Option("MultiPV", "spin", 1, 1, 500, None)
        ropt = ref.Option("MultiPV", "spin", 1, 1, 500, None)
        assert opt.is_managed() == ropt.is_managed()

    def test_not_managed(self):
        opt = Option("Hash", "spin", 16, 1, 1048576, None)
        ropt = ref.Option("Hash", "spin", 16, 1, 1048576, None)
        assert opt.is_managed() == ropt.is_managed()

    @pytest.mark.parametrize(
        "name",
        ["MultiPV", "Ponder", "UCI_Chess960", "UCI_Variant"],
    )
    def test_managed_options_match(self, name):
        opt = Option(name, "check", True, None, None, None)
        ropt = ref.Option(name, "check", True, None, None, None)
        assert opt.is_managed() == ropt.is_managed()

    @pytest.mark.parametrize("name", ["Hash", "Threads", "SyzygyPath"])
    def test_not_managed_match(self, name):
        opt = Option(name, "spin", 16, 1, 1024, None)
        ropt = ref.Option(name, "spin", 16, 1, 1024, None)
        assert opt.is_managed() == ropt.is_managed() == False

    def test_parse_check_true(self):
        opt = Option("Ponder", "check", False, None, None, None)
        assert opt.parse("true") is True

    def test_parse_check_false(self):
        opt = Option("Ponder", "check", True, None, None, None)
        assert opt.parse("false") is False

    def test_parse_spin(self):
        opt = Option("Hash", "spin", 16, 1, 1048576, None)
        assert opt.parse("128") == 128


class TestUciOptionMap:
    def test_case_insensitive_get(self):
        uom = UciOptionMap()
        uom["Hash"] = 128
        assert uom["hash"] == 128
        assert uom["HASH"] == 128
        assert uom["Hash"] == 128

    def test_preserves_original_key(self):
        uom = UciOptionMap()
        uom["Hash"] = 128
        assert list(uom.keys()) == ["Hash"]

    def test_case_insensitive_contains(self):
        uom = UciOptionMap()
        uom["Hash"] = 128
        assert "hash" in uom
        assert "HASH" in uom

    def test_len(self):
        uom = UciOptionMap()
        uom["Hash"] = 128
        uom["Threads"] = 4
        assert len(uom) == 2

    def test_overwrite_same_key_different_case(self):
        uom = UciOptionMap()
        uom["Hash"] = 128
        uom["hash"] = 256
        assert len(uom) == 1
        assert uom["Hash"] == 256

    def test_matches_reference_case_insensitivity(self):
        uom = UciOptionMap()
        ruom = ref.UciOptionMap()
        uom["Hash"] = "value"
        ruom["Hash"] = "value"
        assert uom["hash"] == ruom["hash"]
        assert uom["HASH"] == ruom["HASH"]


class TestManagedOptions:
    def test_managed_options_match(self):
        assert sorted(MANAGED_OPTIONS) == sorted(ref.MANAGED_OPTIONS)


class TestMockTransport:
    def test_get_pid(self):
        mt = MockTransport(None)
        assert mt.get_pid() == 0

    def test_get_returncode(self):
        mt = MockTransport(None)
        assert mt.get_returncode() is None

    def test_get_pipe_transport_stdin(self):
        mt = MockTransport(None)
        result = mt.get_pipe_transport(0)
        assert result is mt

    def test_get_pipe_transport_other(self):
        mt = MockTransport(None)
        result = mt.get_pipe_transport(1)
        assert result is None

    def test_assert_done_no_expectations(self):
        mt = MockTransport(None)
        mt.assert_done()  # should not raise

    def test_assert_done_with_expectations(self):
        mt = MockTransport(None)
        mt.expect("uci")
        with pytest.raises(AssertionError):
            mt.assert_done()

    def test_expect_and_write(self):
        received = []

        class FakeProtocol:
            def pipe_data_received(self, fd, data):
                received.append(data.decode().strip())

        mt = MockTransport(FakeProtocol())
        mt.expect("uci", ["id name TestEngine", "uciok"])
        mt.write(b"uci\n")
        assert received == ["id name TestEngine", "uciok"]
        mt.assert_done()

    def test_is_closing_default(self):
        mt = MockTransport(None)
        assert mt.is_closing() is False

    def test_close_sets_closing(self):
        mt = MockTransport(None)
        mt.close()
        assert mt.is_closing() is True
