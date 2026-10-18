"""ENG-ATE: Engine acceptance test suite — full engine stack differential testing.

Tests the complete engine stack (protocol + uci + xboard + scores + results + simple)
against python-chess. Since we can't run actual engines, focuses on:
- Parsing parity (UCI info, bestmove, XBoard post, options)
- Score/WDL model parity
- API completeness across all engine modules
- Integration between modules
"""

from __future__ import annotations

import inspect

import chess
import chess.engine
import pytest

from dcs_chess.engine.uci import (
    UciProtocol,
    _parse_uci_info,
    _parse_uci_bestmove,
    popen_uci,
)
from dcs_chess.engine.xboard import (
    XBoardProtocol,
    _parse_xboard_post,
    _parse_xboard_option,
    popen_xboard,
    XBOARD_ERROR_REGEX,
)
from dcs_chess.engine.protocol import Protocol, BaseCommand
from dcs_chess.engine.simple import SimpleEngine, SimpleAnalysisResult
from dcs_chess.engine.results import (
    AnalysisResult,
    BestMove,
    EngineError,
    EngineTerminatedError,
    Info,
    InfoDict,
    Limit,
    Option,
    Opponent,
    PlayResult,
    UciOptionMap,
    INFO_ALL,
    INFO_NONE,
    INFO_SCORE,
    INFO_PV,
    INFO_BASIC,
)
from dcs_chess.engine.scores import Cp, Mate, MateGiven, PovScore, Wdl, PovWdl
from dcs_chess.core.board import Board


# =====================================================================
# 1. UCI info parsing — comprehensive
# =====================================================================

class TestUciInfoAcceptance:
    """Full-range UCI info line parsing against python-chess."""

    @pytest.fixture
    def boards(self):
        return Board(), chess.Board()

    INFO_LINES = [
        "depth 1",
        "depth 20 seldepth 30",
        "score cp 0",
        "score cp 35",
        "score cp -150",
        "score mate 3",
        "score mate -2",
        "score mate 0",
        "score cp 50 lowerbound",
        "score cp 100 upperbound",
        "nodes 1234567 time 5000 nps 246913",
        "hashfull 750 tbhits 42 cpuload 500",
        "multipv 1 depth 25 score cp 35",
        "multipv 2 depth 25 score cp -10",
        "currmove e2e4 currmovenumber 1",
        "wdl 500 300 200",
        "wdl 1000 0 0",
        "wdl 0 0 1000",
        "wdl 333 334 333",
        "string engine is thinking",
        "string hello world with many spaces",
        "pv e2e4 e7e5 g1f3",
        "pv e2e4",
        "depth 25 seldepth 32 multipv 1 score cp 35 nodes 12345678 nps 2000000 hashfull 800 tbhits 5 time 6173 pv e2e4 e7e5 g1f3",
        "ebf 3.14",
    ]

    @pytest.mark.parametrize("line", INFO_LINES)
    def test_info_line(self, boards, line):
        ours_b, ref_b = boards
        ours = _parse_uci_info(line, ours_b)
        theirs = chess.engine._parse_uci_info(line, ref_b)
        for key in set(ours) | set(theirs):
            if key == "pv":
                our_pv = [str(m) for m in ours.get("pv", [])]
                ref_pv = [str(m) for m in theirs.get("pv", [])]
                assert our_pv == ref_pv, f"PV mismatch on '{line}'"
            elif key in ("score", "wdl", "currmove"):
                assert str(ours.get(key)) == str(theirs.get(key)), (
                    f"{key} mismatch on '{line}': {ours.get(key)} vs {theirs.get(key)}"
                )
            else:
                assert ours.get(key) == theirs.get(key), (
                    f"{key} mismatch on '{line}': {ours.get(key)} vs {theirs.get(key)}"
                )


# =====================================================================
# 2. UCI bestmove parsing — comprehensive
# =====================================================================

class TestUciBestmoveAcceptance:
    BESTMOVE_CASES = [
        ("e2e4", "startpos"),
        ("e2e4 ponder e7e5", "startpos"),
        ("(none)", "startpos"),
        ("NULL", "startpos"),
        ("a7a8q", "4k3/P7/8/8/8/8/8/4K3 w - - 0 1"),
        ("e2e4 ponder (none)", "startpos"),
        ("g1f3 ponder d7d5", "startpos"),
    ]

    @pytest.mark.parametrize("line,fen", BESTMOVE_CASES,
                             ids=[c[0].split()[0] for c in BESTMOVE_CASES])
    def test_bestmove(self, line, fen):
        if fen == "startpos":
            ref_b, ours_b = chess.Board(), Board()
        else:
            ref_b, ours_b = chess.Board(fen), Board(fen)
        ref = chess.engine._parse_uci_bestmove(ref_b, line)
        ours = _parse_uci_bestmove(ours_b, line)
        assert str(ours.move) == str(ref.move), f"Move mismatch: {ours.move} vs {ref.move}"
        assert str(ours.ponder) == str(ref.ponder), f"Ponder mismatch: {ours.ponder} vs {ref.ponder}"


# =====================================================================
# 3. XBoard post parsing — comprehensive
# =====================================================================

class TestXboardPostAcceptance:
    @pytest.fixture
    def boards(self):
        return Board(), chess.Board()

    POST_LINES = [
        "  9  135  1084 35000  e2e4 e7e5 g1f3",
        "  10  50  500 100000  e2e4 e7e5 g1f3 b8c6",
        "  15  100001  500 100000  e2e4",
        "  15  -100001  500 100000  e2e4",
        "  15  100000  500 100000  e2e4",
        "  12  -50  1000 200000  d7d5",
        "  10  0  500 100000  e2e4",
        "  20  100002  1000 500000  e2e4",
        "  20  -100002  1000 500000  e2e4",
        "  5  10  100 5000",
        "  20  50  3000 500000 25 166666 42  e2e4 e7e5",
    ]

    @pytest.mark.parametrize("line", POST_LINES)
    def test_post_line(self, boards, line):
        ours_b, ref_b = boards
        ours = _parse_xboard_post(line, ours_b)
        theirs = chess.engine._parse_xboard_post(line, ref_b)
        for key in ("depth", "time", "nodes"):
            if key in theirs:
                assert ours.get(key) == theirs.get(key), f"{key} mismatch"
        if "score" in theirs:
            assert str(ours["score"]) == str(theirs["score"]), "Score mismatch"
        if "pv" in theirs:
            our_pv = [str(m) for m in ours.get("pv", [])]
            ref_pv = [str(m) for m in theirs.get("pv", [])]
            assert our_pv == ref_pv, "PV mismatch"


# =====================================================================
# 4. Score models — comprehensive
# =====================================================================

class TestScoreModels:
    def test_cp_basic(self):
        ours = Cp(35)
        theirs = chess.engine.Cp(35)
        assert ours.score() == theirs.score()
        assert str(ours) == str(theirs)

    def test_cp_negative(self):
        ours = Cp(-150)
        theirs = chess.engine.Cp(-150)
        assert ours.score() == theirs.score()

    def test_mate_positive(self):
        ours = Mate(3)
        theirs = chess.engine.Mate(3)
        assert str(ours) == str(theirs)
        assert ours.score(mate_score=100000) == theirs.score(mate_score=100000)

    def test_mate_negative(self):
        ours = Mate(-2)
        theirs = chess.engine.Mate(-2)
        assert str(ours) == str(theirs)
        assert ours.score(mate_score=100000) == theirs.score(mate_score=100000)

    def test_mate_zero(self):
        ours = Mate(0)
        theirs = chess.engine.Mate(0)
        assert ours.score(mate_score=100000) == theirs.score(mate_score=100000)

    def test_pov_score_white(self):
        ours = PovScore(Cp(35), True)
        theirs = chess.engine.PovScore(chess.engine.Cp(35), True)
        assert str(ours.relative) == str(theirs.relative)
        assert str(ours.white()) == str(theirs.white())
        assert str(ours.black()) == str(theirs.black())

    def test_pov_score_black(self):
        ours = PovScore(Cp(35), False)
        theirs = chess.engine.PovScore(chess.engine.Cp(35), False)
        assert str(ours.relative) == str(theirs.relative)
        assert str(ours.white()) == str(theirs.white())

    def test_wdl_basic(self):
        ours = Wdl(500, 300, 200)
        theirs = chess.engine.Wdl(500, 300, 200)
        assert ours.wins == theirs.wins
        assert ours.draws == theirs.draws
        assert ours.losses == theirs.losses
        assert ours.expectation() == pytest.approx(theirs.expectation())

    def test_pov_wdl(self):
        ours = PovWdl(Wdl(600, 300, 100), True)
        theirs = chess.engine.PovWdl(chess.engine.Wdl(600, 300, 100), True)
        assert str(ours.white()) == str(theirs.white())
        assert str(ours.black()) == str(theirs.black())

    def test_mate_given(self):
        ours = MateGiven
        theirs = chess.engine.MateGiven
        assert str(ours) == str(theirs)


# =====================================================================
# 5. Limit parity
# =====================================================================

class TestLimitAcceptance:
    def test_limit_time(self):
        ours = Limit(time=5.0)
        theirs = chess.engine.Limit(time=5.0)
        assert ours.time == theirs.time

    def test_limit_depth(self):
        ours = Limit(depth=20)
        theirs = chess.engine.Limit(depth=20)
        assert ours.depth == theirs.depth

    def test_limit_nodes(self):
        ours = Limit(nodes=1000000)
        theirs = chess.engine.Limit(nodes=1000000)
        assert ours.nodes == theirs.nodes

    def test_limit_all_params(self):
        ours = Limit(time=5.0, depth=20, nodes=1000000, mate=5)
        theirs = chess.engine.Limit(time=5.0, depth=20, nodes=1000000, mate=5)
        assert ours.time == theirs.time
        assert ours.depth == theirs.depth
        assert ours.nodes == theirs.nodes
        assert ours.mate == theirs.mate

    def test_limit_signature(self):
        ref_params = list(inspect.signature(chess.engine.Limit.__init__).parameters.keys())
        our_params = list(inspect.signature(Limit.__init__).parameters.keys())
        assert our_params == ref_params

    def test_limit_repr(self):
        ours = Limit(time=5.0, depth=20)
        theirs = chess.engine.Limit(time=5.0, depth=20)
        assert repr(ours) == repr(theirs)


# =====================================================================
# 6. Option parity
# =====================================================================

class TestOptionAcceptance:
    OPTIONS = [
        ("Threads", "spin", 1, 1, 128, None),
        ("Ponder", "check", True, None, None, None),
        ("Style", "combo", "Normal", None, None, ["Normal", "Aggressive", "Passive"]),
        ("Clear Hash", "button", None, None, None, None),
        ("SyzygyPath", "string", "", None, None, None),
    ]

    @pytest.mark.parametrize("args", OPTIONS, ids=[o[0] for o in OPTIONS])
    def test_option_creation(self, args):
        ours = Option(*args)
        theirs = chess.engine.Option(*args)
        assert ours.name == theirs.name
        assert ours.type == theirs.type
        assert ours.default == theirs.default

    def test_spin_parse(self):
        ours = Option("Threads", "spin", 1, 1, 128, None)
        theirs = chess.engine.Option("Threads", "spin", 1, 1, 128, None)
        assert ours.parse("4") == theirs.parse("4")

    def test_check_parse(self):
        ours = Option("Ponder", "check", True, None, None, None)
        theirs = chess.engine.Option("Ponder", "check", True, None, None, None)
        assert ours.parse("true") == theirs.parse("true")
        assert ours.parse("false") == theirs.parse("false")

    def test_is_managed(self):
        managed_names = ["UCI_Chess960", "UCI_Variant", "UCI_AnalyseMode",
                         "UCI_Opponent", "UCI_EngineAbout", "UCI_SetPositionValue",
                         "Ponder", "MultiPV"]
        for name in managed_names:
            ours = Option(name, "check", False, None, None, None)
            theirs = chess.engine.Option(name, "check", False, None, None, None)
            assert ours.is_managed() == theirs.is_managed(), f"is_managed mismatch for {name}"


# =====================================================================
# 7. Info flags parity
# =====================================================================

class TestInfoFlags:
    def test_info_all(self):
        assert INFO_ALL == chess.engine.INFO_ALL

    def test_info_none(self):
        assert INFO_NONE == chess.engine.INFO_NONE

    def test_info_score(self):
        assert INFO_SCORE == chess.engine.INFO_SCORE

    def test_info_pv(self):
        assert INFO_PV == chess.engine.INFO_PV

    def test_info_basic(self):
        assert INFO_BASIC == chess.engine.INFO_BASIC


# =====================================================================
# 8. Full module export parity
# =====================================================================

class TestModuleExports:
    def test_engine_public_api(self):
        """Check that all user-facing classes/functions are exported."""
        import dcs_chess.engine as ours
        PUBLIC_API = {
            "SimpleEngine", "SimpleAnalysisResult",
            "UciProtocol", "XBoardProtocol", "Protocol",
            "AnalysisResult", "BestMove", "PlayResult",
            "Cp", "Mate", "MateGiven", "PovScore", "Wdl", "PovWdl",
            "Limit", "Option", "UciOptionMap", "Opponent",
            "EngineError", "EngineTerminatedError",
            "INFO_ALL", "INFO_NONE", "INFO_SCORE", "INFO_PV", "INFO_BASIC",
            "popen_uci", "popen_xboard",
        }
        for name in PUBLIC_API:
            assert hasattr(ours, name), f"Missing export: {name}"
            assert hasattr(chess.engine, name), f"Not in ref: {name}"

    def test_opponent_signature(self):
        ref_params = list(inspect.signature(chess.engine.Opponent.__init__).parameters.keys())
        our_params = list(inspect.signature(Opponent.__init__).parameters.keys())
        assert our_params == ref_params

    def test_play_result_attributes(self):
        ref_attrs = {a for a in dir(chess.engine.PlayResult) if not a.startswith("_")}
        our_attrs = {a for a in dir(PlayResult) if not a.startswith("_")}
        assert our_attrs == ref_attrs, f"Missing: {ref_attrs - our_attrs}"

    def test_uci_option_map_case_insensitive(self):
        ours = UciOptionMap()
        theirs = chess.engine.UciOptionMap()
        ours["Threads"] = Option("Threads", "spin", 1, 1, 128, None)
        theirs["Threads"] = chess.engine.Option("Threads", "spin", 1, 1, 128, None)
        assert "threads" in ours and "threads" in theirs
        assert "THREADS" in ours and "THREADS" in theirs
