"""ADV adversarial differential tests for ENG-005: engine/results types."""

from __future__ import annotations

import chess.engine as ref
import pytest

from dcs_chess.engine.results import (
    EngineError,
    EngineTerminatedError,
    AnalysisComplete,
    Info,
    Limit,
    Option,
    PlayResult,
    BestMove,
    UciOptionMap,
    MANAGED_OPTIONS,
)


# =====================================================================
# Info IntFlag
# =====================================================================

class TestInfoFlags:
    @pytest.mark.parametrize("name", ["NONE", "BASIC", "SCORE", "PV", "REFUTATION", "CURRLINE", "ALL"])
    def test_flag_value_matches(self, name: str):
        assert int(getattr(Info, name)) == int(getattr(ref.Info, name))

    def test_all_is_combination(self):
        assert Info.ALL == (Info.BASIC | Info.SCORE | Info.PV | Info.REFUTATION | Info.CURRLINE)

    def test_bitwise_or(self):
        combined = Info.BASIC | Info.SCORE
        ref_combined = ref.Info.BASIC | ref.Info.SCORE
        assert int(combined) == int(ref_combined)

    def test_bitwise_and(self):
        result = Info.ALL & Info.SCORE
        ref_result = ref.Info.ALL & ref.Info.SCORE
        assert int(result) == int(ref_result)


# =====================================================================
# Exception hierarchies
# =====================================================================

class TestExceptions:
    def test_engine_error_is_runtime_error(self):
        assert issubclass(EngineError, RuntimeError)
        assert issubclass(ref.EngineError, RuntimeError)

    def test_engine_terminated_is_engine_error(self):
        assert issubclass(EngineTerminatedError, EngineError)
        assert issubclass(ref.EngineTerminatedError, ref.EngineError)

    def test_analysis_complete_is_exception(self):
        assert issubclass(AnalysisComplete, Exception)
        assert issubclass(ref.AnalysisComplete, Exception)

    def test_engine_error_catchable_as_runtime_error(self):
        with pytest.raises(RuntimeError):
            raise EngineError("test")

    def test_terminated_catchable_as_engine_error(self):
        with pytest.raises(EngineError):
            raise EngineTerminatedError("test")


# =====================================================================
# Limit
# =====================================================================

class TestLimit:
    _CONFIGS = [
        {},
        {"time": 5.0},
        {"depth": 20},
        {"nodes": 1000000},
        {"mate": 3},
        {"time": 5.0, "depth": 20, "nodes": 1000000, "mate": 3},
        {"white_clock": 120.0, "black_clock": 100.0, "white_inc": 2.0, "black_inc": 2.0},
        {"remaining_moves": 30},
    ]

    @pytest.mark.parametrize("kwargs", _CONFIGS)
    def test_repr_matches(self, kwargs):
        ours = repr(Limit(**kwargs))
        theirs = repr(ref.Limit(**kwargs))
        assert ours == theirs, f"kwargs={kwargs}: {ours!r} != {theirs!r}"

    def test_clock_id_excluded_from_repr(self):
        l = Limit(time=5.0, clock_id=object())
        assert "clock_id" not in repr(l)

    def test_defaults_are_none(self):
        l = Limit()
        rl = ref.Limit()
        assert l.time is None and rl.time is None
        assert l.depth is None and rl.depth is None
        assert l.nodes is None and rl.nodes is None


# =====================================================================
# PlayResult
# =====================================================================

class TestPlayResult:
    def test_defaults(self):
        pr = PlayResult(None, None)
        assert pr.move is None
        assert pr.ponder is None
        assert pr.info == {}
        assert pr.draw_offered is False
        assert pr.resigned is False

    def test_info_default_is_dict(self):
        pr = PlayResult(None, None)
        assert isinstance(pr.info, dict)

    def test_draw_offered(self):
        pr = PlayResult(None, None, draw_offered=True)
        assert pr.draw_offered is True

    def test_resigned(self):
        pr = PlayResult(None, None, resigned=True)
        assert pr.resigned is True


# =====================================================================
# UciOptionMap
# =====================================================================

class TestUciOptionMap:
    def test_case_insensitive_get(self):
        m = UciOptionMap({"Hash": 64})
        rm = ref.UciOptionMap({"Hash": 64})
        assert m["hash"] == rm["hash"]
        assert m["HASH"] == rm["HASH"]
        assert m["Hash"] == rm["Hash"]

    def test_overwrite_case_insensitive(self):
        m = UciOptionMap()
        m["Hash"] = 64
        m["HASH"] = 128
        rm = ref.UciOptionMap()
        rm["Hash"] = 64
        rm["HASH"] = 128
        assert m["hash"] == rm["hash"] == 128
        assert len(m) == len(rm) == 1

    def test_contains_case_insensitive(self):
        m = UciOptionMap({"Hash": 64})
        rm = ref.UciOptionMap({"Hash": 64})
        assert ("hash" in m) == ("hash" in rm)
        assert ("HASH" in m) == ("HASH" in rm)
        assert ("missing" in m) == ("missing" in rm)

    def test_delete(self):
        m = UciOptionMap({"Hash": 64})
        del m["hash"]
        assert len(m) == 0

    def test_repr_matches(self):
        m = UciOptionMap({"Hash": 64, "Threads": 4})
        rm = ref.UciOptionMap({"Hash": 64, "Threads": 4})
        assert repr(m) == repr(rm)

    def test_keys_values_items(self):
        m = UciOptionMap({"Hash": 64, "Threads": 4})
        rm = ref.UciOptionMap({"Hash": 64, "Threads": 4})
        assert sorted(m.keys()) == sorted(rm.keys())
        assert sorted(m.values()) == sorted(rm.values())
        assert sorted(m.items()) == sorted(rm.items())

    def test_copy_independence(self):
        m = UciOptionMap({"Hash": 64})
        c = m.copy()
        c["Hash"] = 128
        assert m["Hash"] == 64
        assert c["Hash"] == 128

    def test_equality(self):
        a = UciOptionMap({"Hash": 64})
        b = UciOptionMap({"hash": 64})
        ra = ref.UciOptionMap({"Hash": 64})
        rb = ref.UciOptionMap({"hash": 64})
        assert (a == b) == (ra == rb)

    def test_iter_preserves_original_case(self):
        m = UciOptionMap({"Hash": 64, "Threads": 4})
        rm = ref.UciOptionMap({"Hash": 64, "Threads": 4})
        assert sorted(list(m)) == sorted(list(rm))

    def test_get_default(self):
        m = UciOptionMap()
        rm = ref.UciOptionMap()
        assert m.get("missing", 42) == rm.get("missing", 42) == 42

    def test_empty_map(self):
        m = UciOptionMap()
        rm = ref.UciOptionMap()
        assert len(m) == len(rm) == 0
        assert repr(m) == repr(rm)


# =====================================================================
# Option
# =====================================================================

class TestOption:
    def test_spin_parse(self):
        o = Option("Hash", "spin", 16, 1, 1048576, None)
        assert o.parse("64") == 64
        assert isinstance(o.parse("64"), int)

    def test_check_parse(self):
        o = Option("UCI_Chess960", "check", True, None, None, None)
        assert o.parse("true") is True
        assert o.parse("false") is False

    def test_string_parse(self):
        o = Option("SyzygyPath", "string", "", None, None, None)
        assert o.parse("/path/to/tb") == "/path/to/tb"

    def test_is_managed(self):
        for name in MANAGED_OPTIONS:
            o = Option(name, "check", False, None, None, None)
            assert o.is_managed(), f"{name} should be managed"

    def test_not_managed(self):
        o = Option("Hash", "spin", 16, 1, 1048576, None)
        assert not o.is_managed()


# =====================================================================
# MANAGED_OPTIONS
# =====================================================================

class TestManagedOptions:
    def test_matches_reference(self):
        assert MANAGED_OPTIONS == ref.MANAGED_OPTIONS
