"""ADV adversarial differential tests for ENG-001: engine/protocol."""

from __future__ import annotations

import asyncio
import sys

import chess.engine
import pytest

from dcs_chess.engine.protocol import (
    BaseCommand,
    CommandState,
    EventLoopPolicy,
    Protocol,
    run_in_background,
)
from dcs_chess.engine.results import (
    EngineError,
    EngineTerminatedError,
    INFO_ALL,
    INFO_NONE,
    Limit,
    Option,
    PlayResult,
    UciOptionMap,
)


# =====================================================================
# CommandState
# =====================================================================

class TestCommandState:
    def test_members(self):
        assert list(CommandState) == [
            CommandState.NEW,
            CommandState.ACTIVE,
            CommandState.CANCELLING,
            CommandState.DONE,
        ]

    def test_member_values_match_ref(self):
        for ours, ref in zip(CommandState, chess.engine.CommandState):
            assert ours.name == ref.name
            assert ours.value == ref.value


# =====================================================================
# EventLoopPolicy
# =====================================================================

class TestEventLoopPolicy:
    def test_matches_reference(self):
        assert EventLoopPolicy is chess.engine.EventLoopPolicy


# =====================================================================
# BaseCommand state machine
# =====================================================================

class _DummyProtocol:
    """Minimal Protocol mock for BaseCommand tests."""
    def __init__(self, loop):
        self.loop = loop
        self.transport = None
        self.initialized = True


class _NoopCommand(BaseCommand):
    """Concrete command that does nothing on start."""
    def start(self):
        pass

    def check_initialized(self):
        pass


class TestBaseCommandStateMachine:
    @pytest.fixture
    def loop_and_cmd(self):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        proto = _DummyProtocol(loop)
        cmd = _NoopCommand(proto)
        yield loop, cmd
        loop.close()

    def test_initial_state(self, loop_and_cmd):
        _, cmd = loop_and_cmd
        assert cmd.state == CommandState.NEW

    def test_start_transitions_to_active(self, loop_and_cmd):
        _, cmd = loop_and_cmd
        cmd._start()
        assert cmd.state == CommandState.ACTIVE

    def test_cancel_transitions_to_cancelling(self, loop_and_cmd):
        _, cmd = loop_and_cmd
        cmd._start()
        cmd._cancel()
        assert cmd.state == CommandState.CANCELLING

    def test_set_finished_transitions_to_done(self, loop_and_cmd):
        _, cmd = loop_and_cmd
        cmd._start()
        cmd.set_finished()
        assert cmd.state == CommandState.DONE

    def test_set_finished_from_cancelling(self, loop_and_cmd):
        _, cmd = loop_and_cmd
        cmd._start()
        cmd._cancel()
        assert cmd.state == CommandState.CANCELLING
        cmd.set_finished()
        assert cmd.state == CommandState.DONE

    def test_engine_terminated_active(self, loop_and_cmd):
        _, cmd = loop_and_cmd
        cmd._start()
        cmd._engine_terminated(1)
        assert cmd.result.done()
        assert isinstance(cmd.result.exception(), EngineTerminatedError)

    def test_engine_terminated_cancelling(self, loop_and_cmd):
        _, cmd = loop_and_cmd
        cmd._start()
        cmd._cancel()
        cmd._engine_terminated(1)
        assert cmd.finished.done()

    def test_engine_terminated_new(self, loop_and_cmd):
        _, cmd = loop_and_cmd
        cmd._engine_terminated(1)
        assert cmd.result.done()
        assert isinstance(cmd.result.exception(), EngineTerminatedError)

    def test_finished_callback(self, loop_and_cmd):
        _, cmd = loop_and_cmd
        called = []
        cmd.add_finished_callback(lambda: called.append(True))
        assert called == []
        cmd._start()
        cmd.set_finished()
        assert called == [True]

    def test_result_future_exception_on_early_finish(self, loop_and_cmd):
        _, cmd = loop_and_cmd
        cmd._start()
        cmd.set_finished()
        assert cmd.result.done()
        assert isinstance(cmd.result.exception(), EngineError)

    def test_handle_exception_sets_result(self, loop_and_cmd):
        _, cmd = loop_and_cmd
        exc = EngineError("test")
        cmd._handle_exception(exc)
        assert cmd.result.exception() is exc
        assert cmd.finished.done()


# =====================================================================
# Protocol line buffering
# =====================================================================

class _TestProtocol(Protocol):
    """Concrete protocol for testing line buffering."""

    def __init__(self):
        super().__init__()
        self.received_lines: list = []
        self.error_lines: list = []

    def _line_received(self, line):
        self.received_lines.append(line)

    def error_line_received(self, line):
        self.error_lines.append(line)

    async def initialize(self):
        pass

    async def ping(self):
        pass

    async def configure(self, options):
        pass

    async def send_opponent_information(self, *, opponent=None, engine_rating=None):
        pass

    async def play(self, board, limit, **kwargs):
        pass

    async def analysis(self, board, limit=None, **kwargs):
        pass

    async def send_game_result(self, board, winner=None, game_ending=None, game_complete=True):
        pass

    async def quit(self):
        pass


class TestLineBuffering:
    @pytest.fixture
    def proto(self):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(self._make_proto(loop))
        yield self._proto
        loop.close()

    async def _make_proto(self, loop):
        self._proto = _TestProtocol()

    def test_complete_line_lf(self, proto):
        proto.pipe_data_received(1, b"hello\n")
        assert proto.received_lines == ["hello"]

    def test_complete_line_crlf(self, proto):
        proto.pipe_data_received(1, b"hello\r\n")
        assert proto.received_lines == ["hello"]

    def test_partial_then_complete(self, proto):
        proto.pipe_data_received(1, b"hel")
        assert proto.received_lines == []
        proto.pipe_data_received(1, b"lo\n")
        assert proto.received_lines == ["hello"]

    def test_multiple_lines(self, proto):
        proto.pipe_data_received(1, b"line1\nline2\nline3\n")
        assert proto.received_lines == ["line1", "line2", "line3"]

    def test_stderr_goes_to_error(self, proto):
        proto.pipe_data_received(2, b"error msg\n")
        assert proto.error_lines == ["error msg"]
        assert proto.received_lines == []

    def test_unicode_error_logged(self, proto):
        proto.pipe_data_received(1, b"\xff\xfe invalid\n")
        assert proto.received_lines == []

    def test_empty_line(self, proto):
        proto.pipe_data_received(1, b"\n")
        assert proto.received_lines == [""]


# =====================================================================
# Protocol abstract methods match reference
# =====================================================================

class TestProtocolAPI:
    def test_abstract_methods(self):
        ref_abstracts = {m for m in dir(chess.engine.UciProtocol.__mro__[1])
                         if hasattr(getattr(chess.engine.UciProtocol.__mro__[1], m, None), '__isabstractmethod__')
                         and getattr(chess.engine.UciProtocol.__mro__[1], m).__isabstractmethod__}
        our_abstracts = {m for m in dir(Protocol)
                         if hasattr(getattr(Protocol, m, None), '__isabstractmethod__')
                         and getattr(Protocol, m).__isabstractmethod__}
        assert our_abstracts == ref_abstracts, (
            f"Missing: {ref_abstracts - our_abstracts}, Extra: {our_abstracts - ref_abstracts}"
        )

    def test_analyse_overloads_exist(self):
        assert hasattr(Protocol, 'analyse')
        assert hasattr(Protocol, 'analysis')

    def test_popen_is_classmethod(self):
        assert isinstance(Protocol.__dict__['popen'], classmethod)

    def test_send_line_signature(self):
        import inspect
        sig = inspect.signature(Protocol.send_line)
        assert 'line' in sig.parameters


# =====================================================================
# Protocol repr
# =====================================================================

class TestProtocolRepr:
    def test_repr_no_transport(self):
        loop = asyncio.new_event_loop()

        async def _test():
            p = _TestProtocol()
            r = repr(p)
            assert "pid=?" in r

        loop.run_until_complete(_test())
        loop.close()


# =====================================================================
# run_in_background signature
# =====================================================================

class TestRunInBackground:
    def test_callable(self):
        assert callable(run_in_background)

    def test_accepts_name_and_debug(self):
        import inspect
        sig = inspect.signature(run_in_background)
        assert 'name' in sig.parameters
        assert 'debug' in sig.parameters
