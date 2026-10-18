"""ADV adversarial differential tests for ENG-002: engine/uci — UciProtocol."""

from __future__ import annotations

import inspect

import chess
import chess.engine
import pytest

from dcs_chess.core.board import Board
from dcs_chess.core.move import Move
from dcs_chess.engine.uci import (
    UciProtocol,
    _parse_uci_info,
    _parse_uci_bestmove,
    popen_uci,
)
from dcs_chess.engine.results import (
    EngineError,
    INFO_ALL,
    INFO_NONE,
    INFO_SCORE,
    INFO_PV,
    Limit,
    Option,
)
from dcs_chess.engine.scores import Cp, Mate, PovScore


# =====================================================================
# 1. _parse_uci_info — differential against python-chess
# =====================================================================

class TestParseUciInfo:
    @pytest.fixture
    def boards(self):
        return Board(), chess.Board()

    def test_score_cp(self, boards):
        ours_b, ref_b = boards
        ref = chess.engine._parse_uci_info("score cp 35", ref_b)
        ours = _parse_uci_info("score cp 35", ours_b)
        assert str(ours["score"]) == str(ref["score"])

    def test_score_mate_positive(self, boards):
        ours_b, ref_b = boards
        ref = chess.engine._parse_uci_info("score mate 3", ref_b)
        ours = _parse_uci_info("score mate 3", ours_b)
        assert str(ours["score"]) == str(ref["score"])

    def test_score_mate_negative(self, boards):
        ours_b, ref_b = boards
        ref = chess.engine._parse_uci_info("score mate -2", ref_b)
        ours = _parse_uci_info("score mate -2", ours_b)
        assert str(ours["score"]) == str(ref["score"])

    def test_score_with_lowerbound(self, boards):
        ours_b, ref_b = boards
        ref = chess.engine._parse_uci_info("score cp 50 lowerbound", ref_b)
        ours = _parse_uci_info("score cp 50 lowerbound", ours_b)
        assert ours.get("lowerbound") == ref.get("lowerbound") == True
        assert str(ours["score"]) == str(ref["score"])

    def test_score_with_upperbound(self, boards):
        ours_b, ref_b = boards
        ref = chess.engine._parse_uci_info("score cp 100 upperbound", ref_b)
        ours = _parse_uci_info("score cp 100 upperbound", ours_b)
        assert ours.get("upperbound") == ref.get("upperbound") == True

    def test_depth_seldepth(self, boards):
        ours_b, ref_b = boards
        ref = chess.engine._parse_uci_info("depth 20 seldepth 30", ref_b)
        ours = _parse_uci_info("depth 20 seldepth 30", ours_b)
        assert ours["depth"] == ref["depth"] == 20
        assert ours["seldepth"] == ref["seldepth"] == 30

    def test_nodes_time_nps(self, boards):
        ours_b, ref_b = boards
        ref = chess.engine._parse_uci_info("nodes 1234567 time 5000 nps 246913", ref_b)
        ours = _parse_uci_info("nodes 1234567 time 5000 nps 246913", ours_b)
        assert ours["nodes"] == ref["nodes"] == 1234567
        assert ours["time"] == ref["time"] == 5.0
        assert ours["nps"] == ref["nps"] == 246913

    def test_hashfull_tbhits_cpuload(self, boards):
        ours_b, ref_b = boards
        ref = chess.engine._parse_uci_info("hashfull 750 tbhits 42 cpuload 500", ref_b)
        ours = _parse_uci_info("hashfull 750 tbhits 42 cpuload 500", ours_b)
        assert ours["hashfull"] == ref["hashfull"] == 750
        assert ours["tbhits"] == ref["tbhits"] == 42
        assert ours["cpuload"] == ref["cpuload"] == 500

    def test_multipv(self, boards):
        ours_b, ref_b = boards
        ref = chess.engine._parse_uci_info("multipv 2 depth 15", ref_b)
        ours = _parse_uci_info("multipv 2 depth 15", ours_b)
        assert ours["multipv"] == ref["multipv"] == 2

    def test_currmove(self, boards):
        ours_b, ref_b = boards
        ref = chess.engine._parse_uci_info("currmove e2e4 currmovenumber 1", ref_b)
        ours = _parse_uci_info("currmove e2e4 currmovenumber 1", ours_b)
        assert str(ours["currmove"]) == str(ref["currmove"])
        assert ours["currmovenumber"] == ref["currmovenumber"]

    def test_pv(self, boards):
        ours_b, ref_b = boards
        ref = chess.engine._parse_uci_info("pv e2e4 e7e5 g1f3", ref_b)
        ours = _parse_uci_info("pv e2e4 e7e5 g1f3", ours_b)
        ref_pv = [str(m) for m in ref["pv"]]
        our_pv = [str(m) for m in ours["pv"]]
        assert our_pv == ref_pv

    def test_wdl(self, boards):
        ours_b, ref_b = boards
        ref = chess.engine._parse_uci_info("wdl 500 300 200", ref_b)
        ours = _parse_uci_info("wdl 500 300 200", ours_b)
        assert str(ours["wdl"]) == str(ref["wdl"])

    def test_string_info(self, boards):
        ours_b, ref_b = boards
        ref = chess.engine._parse_uci_info("string some engine message with spaces", ref_b)
        ours = _parse_uci_info("string some engine message with spaces", ours_b)
        assert ours["string"] == ref["string"]

    def test_ebf(self, boards):
        ours_b, ref_b = boards
        ref = chess.engine._parse_uci_info("ebf 3.14", ref_b)
        ours = _parse_uci_info("ebf 3.14", ours_b)
        assert ours["ebf"] == ref["ebf"]

    def test_empty_info(self, boards):
        ours_b, ref_b = boards
        ref = chess.engine._parse_uci_info("", ref_b)
        ours = _parse_uci_info("", ours_b)
        assert ours == ref == {}

    def test_info_none_selector(self, boards):
        ours_b, ref_b = boards
        ref = chess.engine._parse_uci_info("score cp 35 pv e2e4", ref_b, chess.engine.INFO_NONE)
        ours = _parse_uci_info("score cp 35 pv e2e4", ours_b, INFO_NONE)
        assert ours == ref == {}

    def test_score_only_selector(self, boards):
        ours_b, ref_b = boards
        ref = chess.engine._parse_uci_info("score cp 35 pv e2e4", ref_b, chess.engine.INFO_SCORE)
        ours = _parse_uci_info("score cp 35 pv e2e4", ours_b, INFO_SCORE)
        assert "score" in ours and "score" in ref
        assert "pv" not in ours and "pv" not in ref

    def test_complex_info_line(self, boards):
        ours_b, ref_b = boards
        line = "depth 25 seldepth 32 multipv 1 score cp 35 nodes 12345678 nps 2000000 hashfull 800 tbhits 5 time 6173 pv e2e4 e7e5 g1f3"
        ref = chess.engine._parse_uci_info(line, ref_b)
        ours = _parse_uci_info(line, ours_b)
        for key in ("depth", "seldepth", "multipv", "nodes", "nps", "hashfull", "tbhits", "time"):
            assert ours[key] == ref[key], f"Mismatch on {key}: {ours[key]} vs {ref[key]}"
        assert str(ours["score"]) == str(ref["score"])

    def test_score_cp_negative(self, boards):
        ours_b, ref_b = boards
        ref = chess.engine._parse_uci_info("score cp -150", ref_b)
        ours = _parse_uci_info("score cp -150", ours_b)
        assert str(ours["score"]) == str(ref["score"])

    def test_score_mate_zero(self, boards):
        ours_b, ref_b = boards
        ref = chess.engine._parse_uci_info("score mate 0", ref_b)
        ours = _parse_uci_info("score mate 0", ours_b)
        assert str(ours["score"]) == str(ref["score"])


# =====================================================================
# 2. _parse_uci_bestmove — differential
# =====================================================================

class TestParseUciBestmove:
    def test_basic_move(self):
        ref_b = chess.Board()
        ours_b = Board()
        ref = chess.engine._parse_uci_bestmove(ref_b, "e2e4")
        ours = _parse_uci_bestmove(ours_b, "e2e4")
        assert str(ours.move) == str(ref.move)
        assert ours.ponder is None

    def test_move_with_ponder(self):
        ref_b = chess.Board()
        ours_b = Board()
        ref = chess.engine._parse_uci_bestmove(ref_b, "e2e4 ponder e7e5")
        ours = _parse_uci_bestmove(ours_b, "e2e4 ponder e7e5")
        assert str(ours.move) == str(ref.move)
        assert str(ours.ponder) == str(ref.ponder)

    def test_none_bestmove(self):
        ref_b = chess.Board()
        ours_b = Board()
        ref = chess.engine._parse_uci_bestmove(ref_b, "(none)")
        ours = _parse_uci_bestmove(ours_b, "(none)")
        assert ours.move is None
        assert ref.move is None

    def test_null_bestmove(self):
        ref_b = chess.Board()
        ours_b = Board()
        ref = chess.engine._parse_uci_bestmove(ref_b, "NULL")
        ours = _parse_uci_bestmove(ours_b, "NULL")
        assert ours.move is None
        assert ref.move is None

    def test_promotion_bestmove(self):
        fen = "4k3/P7/8/8/8/8/8/4K3 w - - 0 1"
        ref_b = chess.Board(fen)
        ours_b = Board(fen)
        ref = chess.engine._parse_uci_bestmove(ref_b, "a7a8q")
        ours = _parse_uci_bestmove(ours_b, "a7a8q")
        assert str(ours.move) == str(ref.move)

    def test_ponder_none(self):
        ref_b = chess.Board()
        ours_b = Board()
        ref = chess.engine._parse_uci_bestmove(ref_b, "e2e4 ponder (none)")
        ours = _parse_uci_bestmove(ours_b, "e2e4 ponder (none)")
        assert str(ours.move) == str(ref.move)
        assert ours.ponder is None and ref.ponder is None


# =====================================================================
# 3. UciProtocol API surface parity
# =====================================================================

class TestUciProtocolAPI:
    def test_method_set_matches(self):
        ref_methods = {m for m in dir(chess.engine.UciProtocol) if not m.startswith("_")}
        our_methods = {m for m in dir(UciProtocol) if not m.startswith("_")}
        assert our_methods == ref_methods, (
            f"Missing: {ref_methods - our_methods}, Extra: {our_methods - ref_methods}"
        )

    def test_play_signature(self):
        ref_params = list(inspect.signature(chess.engine.UciProtocol.play).parameters.keys())
        our_params = list(inspect.signature(UciProtocol.play).parameters.keys())
        assert our_params == ref_params

    def test_analysis_signature(self):
        ref_params = list(inspect.signature(chess.engine.UciProtocol.analysis).parameters.keys())
        our_params = list(inspect.signature(UciProtocol.analysis).parameters.keys())
        assert our_params == ref_params

    def test_configure_signature(self):
        ref_params = list(inspect.signature(chess.engine.UciProtocol.configure).parameters.keys())
        our_params = list(inspect.signature(UciProtocol.configure).parameters.keys())
        assert our_params == ref_params

    def test_debug_signature(self):
        ref_sig = inspect.signature(chess.engine.UciProtocol.debug)
        our_sig = inspect.signature(UciProtocol.debug)
        assert str(our_sig) == str(ref_sig)

    def test_popen_uci_signature(self):
        ref_params = list(inspect.signature(chess.engine.popen_uci).parameters.keys())
        our_params = list(inspect.signature(popen_uci).parameters.keys())
        assert our_params == ref_params

    def test_mro_class_names(self):
        ref_mro = [c.__name__ for c in chess.engine.UciProtocol.__mro__]
        our_mro = [c.__name__ for c in UciProtocol.__mro__]
        assert our_mro == ref_mro

    def test_inherits_protocol(self):
        from dcs_chess.engine.protocol import Protocol
        assert issubclass(UciProtocol, Protocol)


# =====================================================================
# 4. Option.parse differential
# =====================================================================

class TestOptionParse:
    def test_spin_valid(self):
        ref = chess.engine.Option("Threads", "spin", 1, 1, 128, None)
        ours = Option("Threads", "spin", 1, 1, 128, None)
        assert ours.parse("4") == ref.parse("4") == 4

    def test_spin_below_min_raises(self):
        ref = chess.engine.Option("Threads", "spin", 1, 1, 128, None)
        ours = Option("Threads", "spin", 1, 1, 128, None)
        with pytest.raises(chess.engine.EngineError):
            ref.parse("0")
        with pytest.raises(EngineError):
            ours.parse("0")

    def test_spin_above_max_raises(self):
        ref = chess.engine.Option("Threads", "spin", 1, 1, 128, None)
        ours = Option("Threads", "spin", 1, 1, 128, None)
        with pytest.raises(chess.engine.EngineError):
            ref.parse("200")
        with pytest.raises(EngineError):
            ours.parse("200")

    def test_check_true(self):
        ref = chess.engine.Option("Ponder", "check", True, None, None, None)
        ours = Option("Ponder", "check", True, None, None, None)
        assert ours.parse("true") == ref.parse("true") == True

    def test_check_false(self):
        ref = chess.engine.Option("Ponder", "check", False, None, None, None)
        ours = Option("Ponder", "check", False, None, None, None)
        assert ours.parse("false") == ref.parse("false") == False

    def test_combo_valid(self):
        ref = chess.engine.Option("Style", "combo", "Normal", None, None, ["Normal", "Aggressive"])
        ours = Option("Style", "combo", "Normal", None, None, ["Normal", "Aggressive"])
        assert ours.parse("Normal") == ref.parse("Normal") == "Normal"

    def test_combo_invalid_raises(self):
        ref = chess.engine.Option("Style", "combo", "Normal", None, None, ["Normal", "Aggressive"])
        ours = Option("Style", "combo", "Normal", None, None, ["Normal", "Aggressive"])
        with pytest.raises(chess.engine.EngineError):
            ref.parse("Invalid")
        with pytest.raises(EngineError):
            ours.parse("Invalid")

    def test_button_returns_none(self):
        ref = chess.engine.Option("Clear Hash", "button", None, None, None, None)
        ours = Option("Clear Hash", "button", None, None, None, None)
        assert ours.parse("") == ref.parse("") == None

    def test_string_type(self):
        ref = chess.engine.Option("SyzygyPath", "string", "", None, None, None)
        ours = Option("SyzygyPath", "string", "", None, None, None)
        assert ours.parse("/path/to/tb") == ref.parse("/path/to/tb") == "/path/to/tb"

    def test_option_is_managed(self):
        ref = chess.engine.Option("UCI_Chess960", "check", False, None, None, None)
        ours = Option("UCI_Chess960", "check", False, None, None, None)
        assert ours.is_managed() == ref.is_managed()
