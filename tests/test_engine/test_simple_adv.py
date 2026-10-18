"""ADV adversarial differential tests for ENG-004: engine/simple — SimpleEngine."""

from __future__ import annotations

import inspect
import typing

import chess
import chess.engine
import pytest

from dcs_chess.engine.simple import SimpleEngine, SimpleAnalysisResult
from dcs_chess.engine.results import (
    EngineError, EngineTerminatedError, Limit, Option, Opponent,
    INFO_ALL, INFO_NONE,
)


# =====================================================================
# 1. SimpleEngine API surface parity
# =====================================================================

class TestSimpleEngineAPI:
    def test_method_set_matches(self):
        ref_methods = {m for m in dir(chess.engine.SimpleEngine) if not m.startswith("_")}
        our_methods = {m for m in dir(SimpleEngine) if not m.startswith("_")}
        assert our_methods == ref_methods, (
            f"Missing: {ref_methods - our_methods}, Extra: {our_methods - ref_methods}"
        )

    def test_init_signature(self):
        ref_params = list(inspect.signature(chess.engine.SimpleEngine.__init__).parameters.keys())
        our_params = list(inspect.signature(SimpleEngine.__init__).parameters.keys())
        assert our_params == ref_params

    def test_play_signature(self):
        ref_params = list(inspect.signature(chess.engine.SimpleEngine.play).parameters.keys())
        our_params = list(inspect.signature(SimpleEngine.play).parameters.keys())
        assert our_params == ref_params

    def test_analyse_signature(self):
        ref_params = list(inspect.signature(chess.engine.SimpleEngine.analyse).parameters.keys())
        our_params = list(inspect.signature(SimpleEngine.analyse).parameters.keys())
        assert our_params == ref_params

    def test_analysis_signature(self):
        ref_params = list(inspect.signature(chess.engine.SimpleEngine.analysis).parameters.keys())
        our_params = list(inspect.signature(SimpleEngine.analysis).parameters.keys())
        assert our_params == ref_params

    def test_configure_signature(self):
        ref_params = list(inspect.signature(chess.engine.SimpleEngine.configure).parameters.keys())
        our_params = list(inspect.signature(SimpleEngine.configure).parameters.keys())
        assert our_params == ref_params

    def test_send_opponent_information_signature(self):
        ref_params = list(inspect.signature(chess.engine.SimpleEngine.send_opponent_information).parameters.keys())
        our_params = list(inspect.signature(SimpleEngine.send_opponent_information).parameters.keys())
        assert our_params == ref_params

    def test_send_game_result_signature(self):
        ref_params = list(inspect.signature(chess.engine.SimpleEngine.send_game_result).parameters.keys())
        our_params = list(inspect.signature(SimpleEngine.send_game_result).parameters.keys())
        assert our_params == ref_params

    def test_ping_signature(self):
        ref_params = list(inspect.signature(chess.engine.SimpleEngine.ping).parameters.keys())
        our_params = list(inspect.signature(SimpleEngine.ping).parameters.keys())
        assert our_params == ref_params

    def test_quit_signature(self):
        ref_params = list(inspect.signature(chess.engine.SimpleEngine.quit).parameters.keys())
        our_params = list(inspect.signature(SimpleEngine.quit).parameters.keys())
        assert our_params == ref_params

    def test_close_signature(self):
        ref_params = list(inspect.signature(chess.engine.SimpleEngine.close).parameters.keys())
        our_params = list(inspect.signature(SimpleEngine.close).parameters.keys())
        assert our_params == ref_params

    def test_popen_signature(self):
        ref_params = list(inspect.signature(chess.engine.SimpleEngine.popen).parameters.keys())
        our_params = list(inspect.signature(SimpleEngine.popen).parameters.keys())
        assert our_params == ref_params

    def test_popen_uci_signature(self):
        ref_params = list(inspect.signature(chess.engine.SimpleEngine.popen_uci).parameters.keys())
        our_params = list(inspect.signature(SimpleEngine.popen_uci).parameters.keys())
        assert our_params == ref_params

    def test_popen_xboard_signature(self):
        ref_params = list(inspect.signature(chess.engine.SimpleEngine.popen_xboard).parameters.keys())
        our_params = list(inspect.signature(SimpleEngine.popen_xboard).parameters.keys())
        assert our_params == ref_params

    def test_communicate_signature(self):
        ref_params = list(inspect.signature(chess.engine.SimpleEngine.communicate).parameters.keys())
        our_params = list(inspect.signature(SimpleEngine.communicate).parameters.keys())
        assert our_params == ref_params

    def test_mro_class_names(self):
        ref_mro = [c.__name__ for c in chess.engine.SimpleEngine.__mro__]
        our_mro = [c.__name__ for c in SimpleEngine.__mro__]
        assert our_mro == ref_mro

    def test_context_manager_protocol(self):
        assert hasattr(SimpleEngine, "__enter__")
        assert hasattr(SimpleEngine, "__exit__")

    def test_repr_method(self):
        assert hasattr(SimpleEngine, "__repr__")

    def test_options_is_property(self):
        assert isinstance(
            inspect.getattr_static(SimpleEngine, "options"), property
        )
        assert isinstance(
            inspect.getattr_static(chess.engine.SimpleEngine, "options"), property
        )

    def test_id_is_property(self):
        assert isinstance(
            inspect.getattr_static(SimpleEngine, "id"), property
        )
        assert isinstance(
            inspect.getattr_static(chess.engine.SimpleEngine, "id"), property
        )


# =====================================================================
# 2. SimpleAnalysisResult API surface parity
# =====================================================================

class TestSimpleAnalysisResultAPI:
    def test_method_set_matches(self):
        ref_methods = {m for m in dir(chess.engine.SimpleAnalysisResult) if not m.startswith("_")}
        our_methods = {m for m in dir(SimpleAnalysisResult) if not m.startswith("_")}
        assert our_methods == ref_methods, (
            f"Missing: {ref_methods - our_methods}, Extra: {our_methods - ref_methods}"
        )

    def test_init_signature(self):
        ref_params = list(inspect.signature(chess.engine.SimpleAnalysisResult.__init__).parameters.keys())
        our_params = list(inspect.signature(SimpleAnalysisResult.__init__).parameters.keys())
        assert our_params == ref_params

    def test_stop_signature(self):
        ref_params = list(inspect.signature(chess.engine.SimpleAnalysisResult.stop).parameters.keys())
        our_params = list(inspect.signature(SimpleAnalysisResult.stop).parameters.keys())
        assert our_params == ref_params

    def test_wait_signature(self):
        ref_params = list(inspect.signature(chess.engine.SimpleAnalysisResult.wait).parameters.keys())
        our_params = list(inspect.signature(SimpleAnalysisResult.wait).parameters.keys())
        assert our_params == ref_params

    def test_would_block_signature(self):
        ref_params = list(inspect.signature(chess.engine.SimpleAnalysisResult.would_block).parameters.keys())
        our_params = list(inspect.signature(SimpleAnalysisResult.would_block).parameters.keys())
        assert our_params == ref_params

    def test_empty_signature(self):
        ref_params = list(inspect.signature(chess.engine.SimpleAnalysisResult.empty).parameters.keys())
        our_params = list(inspect.signature(SimpleAnalysisResult.empty).parameters.keys())
        assert our_params == ref_params

    def test_get_signature(self):
        ref_params = list(inspect.signature(chess.engine.SimpleAnalysisResult.get).parameters.keys())
        our_params = list(inspect.signature(SimpleAnalysisResult.get).parameters.keys())
        assert our_params == ref_params

    def test_next_signature(self):
        ref_params = list(inspect.signature(chess.engine.SimpleAnalysisResult.next).parameters.keys())
        our_params = list(inspect.signature(SimpleAnalysisResult.next).parameters.keys())
        assert our_params == ref_params

    def test_context_manager(self):
        assert hasattr(SimpleAnalysisResult, "__enter__")
        assert hasattr(SimpleAnalysisResult, "__exit__")

    def test_iteration_protocol(self):
        assert hasattr(SimpleAnalysisResult, "__iter__")
        assert hasattr(SimpleAnalysisResult, "__next__")

    def test_info_is_property(self):
        assert isinstance(
            inspect.getattr_static(SimpleAnalysisResult, "info"), property
        )
        assert isinstance(
            inspect.getattr_static(chess.engine.SimpleAnalysisResult, "info"), property
        )

    def test_multipv_is_property(self):
        assert isinstance(
            inspect.getattr_static(SimpleAnalysisResult, "multipv"), property
        )
        assert isinstance(
            inspect.getattr_static(chess.engine.SimpleAnalysisResult, "multipv"), property
        )

    def test_mro_class_names(self):
        ref_mro = [c.__name__ for c in chess.engine.SimpleAnalysisResult.__mro__]
        our_mro = [c.__name__ for c in SimpleAnalysisResult.__mro__]
        assert our_mro == ref_mro


# =====================================================================
# 3. _timeout_for behavior
# =====================================================================

class TestTimeoutFor:
    def _make_engine(self, timeout):
        """Create a minimal SimpleEngine-like object for _timeout_for testing."""
        import asyncio
        import concurrent.futures
        eng = object.__new__(SimpleEngine)
        eng.timeout = timeout
        eng._shutdown_lock = __import__("threading").Lock()
        eng._shutdown = False
        eng.shutdown_event = asyncio.Event()
        eng.returncode = concurrent.futures.Future()
        return eng

    def _make_ref_engine(self, timeout):
        import asyncio
        import concurrent.futures
        eng = object.__new__(chess.engine.SimpleEngine)
        eng.timeout = timeout
        eng._shutdown_lock = __import__("threading").Lock()
        eng._shutdown = False
        eng.shutdown_event = asyncio.Event()
        eng.returncode = concurrent.futures.Future()
        return eng

    def test_timeout_with_limit_time(self):
        ours = self._make_engine(10.0)
        theirs = self._make_ref_engine(10.0)
        limit = Limit(time=5.0)
        ref_limit = chess.engine.Limit(time=5.0)
        assert ours._timeout_for(limit) == theirs._timeout_for(ref_limit)

    def test_timeout_none_limit(self):
        ours = self._make_engine(10.0)
        theirs = self._make_ref_engine(10.0)
        assert ours._timeout_for(None) == theirs._timeout_for(None)

    def test_timeout_none_engine(self):
        ours = self._make_engine(None)
        theirs = self._make_ref_engine(None)
        limit = Limit(time=5.0)
        ref_limit = chess.engine.Limit(time=5.0)
        assert ours._timeout_for(limit) == theirs._timeout_for(ref_limit)

    def test_timeout_limit_no_time(self):
        ours = self._make_engine(10.0)
        theirs = self._make_ref_engine(10.0)
        limit = Limit(depth=20)
        ref_limit = chess.engine.Limit(depth=20)
        assert ours._timeout_for(limit) == theirs._timeout_for(ref_limit)


# =====================================================================
# 4. Analyse overloads
# =====================================================================

class TestAnalyseOverloads:
    def test_analyse_has_overloads(self):
        ref_overloads = typing.get_overloads(chess.engine.SimpleEngine.analyse)
        our_overloads = typing.get_overloads(SimpleEngine.analyse)
        assert len(our_overloads) == len(ref_overloads), (
            f"Overload count: ours={len(our_overloads)}, ref={len(ref_overloads)}"
        )

    def test_overload_signatures(self):
        ref_overloads = typing.get_overloads(chess.engine.SimpleEngine.analyse)
        our_overloads = typing.get_overloads(SimpleEngine.analyse)
        for i, (ours, theirs) in enumerate(zip(our_overloads, ref_overloads)):
            our_params = list(inspect.signature(ours).parameters.keys())
            ref_params = list(inspect.signature(theirs).parameters.keys())
            assert our_params == ref_params, f"Overload {i}: {our_params} != {ref_params}"


# =====================================================================
# 5. Shutdown and error behavior
# =====================================================================

class TestShutdownBehavior:
    def _make_engine(self, timeout=10.0):
        import asyncio
        import concurrent.futures
        eng = object.__new__(SimpleEngine)
        eng.timeout = timeout
        eng._shutdown_lock = __import__("threading").Lock()
        eng._shutdown = False
        eng.shutdown_event = asyncio.Event()
        eng.returncode = concurrent.futures.Future()
        return eng

    def test_not_shut_down_works_when_alive(self):
        eng = self._make_engine()
        with eng._not_shut_down():
            pass

    def test_not_shut_down_raises_after_shutdown(self):
        eng = self._make_engine()
        eng._shutdown = True
        with pytest.raises(EngineTerminatedError):
            with eng._not_shut_down():
                pass

    def test_close_is_idempotent(self):
        """Calling close() twice should not error."""
        import asyncio
        ev_loop = asyncio.new_event_loop()

        class FakeTransport:
            def close(self): pass
            def get_pid(self): return 0

        eng = self._make_engine()
        eng.transport = FakeTransport()

        class FakeProtocol:
            pass
        fp = FakeProtocol()
        fp.loop = ev_loop
        eng.protocol = fp

        eng.close()
        assert eng._shutdown is True
        eng.close()
        assert eng._shutdown is True
        ev_loop.close()

    def test_engine_terminated_error_type(self):
        """EngineTerminatedError should be correct class."""
        assert issubclass(EngineTerminatedError, EngineError)
        assert issubclass(
            chess.engine.EngineTerminatedError, chess.engine.EngineError
        )


# =====================================================================
# 6. Default timeout
# =====================================================================

class TestDefaults:
    def test_default_timeout(self):
        ref_params = inspect.signature(chess.engine.SimpleEngine.__init__).parameters
        our_params = inspect.signature(SimpleEngine.__init__).parameters
        assert our_params["timeout"].default == ref_params["timeout"].default

    def test_popen_default_timeout(self):
        ref_params = inspect.signature(chess.engine.SimpleEngine.popen).parameters
        our_params = inspect.signature(SimpleEngine.popen).parameters
        assert our_params["timeout"].default == ref_params["timeout"].default

    def test_play_default_info(self):
        ref_params = inspect.signature(chess.engine.SimpleEngine.play).parameters
        our_params = inspect.signature(SimpleEngine.play).parameters
        assert our_params["info"].default == ref_params["info"].default

    def test_analyse_default_info(self):
        ref_params = inspect.signature(chess.engine.SimpleEngine.analyse).parameters
        our_params = inspect.signature(SimpleEngine.analyse).parameters
        assert our_params["info"].default == ref_params["info"].default

    def test_analysis_default_info(self):
        ref_params = inspect.signature(chess.engine.SimpleEngine.analysis).parameters
        our_params = inspect.signature(SimpleEngine.analysis).parameters
        assert our_params["info"].default == ref_params["info"].default
