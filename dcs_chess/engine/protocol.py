"""Engine protocol base class and command lifecycle (FR-E1)."""

from __future__ import annotations

import abc
import asyncio
import concurrent.futures
import enum
import logging
import subprocess
import sys
import threading
import typing
from typing import (
    Any, Callable, Coroutine, Dict, Generic, Iterable, List,
    Mapping, MutableMapping, Optional, Tuple, Type, TypeVar, Union,
)

if typing.TYPE_CHECKING:
    from types import TracebackType
    from typing_extensions import Self

from .results import (
    AnalysisResult, BestMove, ConfigValue, EngineError, EngineTerminatedError,
    Info, InfoDict, Limit, MANAGED_OPTIONS, MockTransport,
    Opponent, Option, PlayResult, UciOptionMap,
    INFO_NONE, INFO_ALL,
)

T = TypeVar("T")
ProtocolT = TypeVar("ProtocolT", bound="Protocol")

ConfigMapping = Mapping[str, ConfigValue]

LOGGER = logging.getLogger(__name__)

EventLoopPolicy = asyncio.DefaultEventLoopPolicy


def run_in_background(
    coroutine: Callable[[concurrent.futures.Future[T]], Coroutine[Any, Any, None]],
    *,
    name: Optional[str] = None,
    debug: Optional[bool] = None,
) -> T:
    """Runs ``coroutine(future)`` in a new event loop on a background thread."""
    assert asyncio.iscoroutinefunction(coroutine)

    future: concurrent.futures.Future[T] = concurrent.futures.Future()

    def background() -> None:
        try:
            asyncio.run(coroutine(future), debug=debug)
            future.cancel()
        except Exception as exc:
            future.set_exception(exc)

    threading.Thread(target=background, name=name).start()
    return future.result()


class CommandState(enum.Enum):
    NEW = enum.auto()
    ACTIVE = enum.auto()
    CANCELLING = enum.auto()
    DONE = enum.auto()


class BaseCommand(Generic[T]):
    """Lifecycle wrapper for a single engine command."""

    def __init__(self, engine: Protocol) -> None:
        self._engine = engine
        self.state = CommandState.NEW
        self.result: asyncio.Future[T] = asyncio.Future()
        self.finished: asyncio.Future[None] = asyncio.Future()
        self._finished_callbacks: List[Callable[[], None]] = []

    def add_finished_callback(self, callback: Callable[[], None]) -> None:
        self._finished_callbacks.append(callback)
        self._dispatch_finished()

    def _dispatch_finished(self) -> None:
        if self.finished.done():
            while self._finished_callbacks:
                self._finished_callbacks.pop()()

    def _engine_terminated(self, code: int) -> None:
        hint = ", binary not compatible with cpu?" if code in [-4, 0xc000001d] else ""
        exc = EngineTerminatedError(
            f"engine process died unexpectedly (exit code: {code}{hint})"
        )
        if self.state == CommandState.ACTIVE:
            self.engine_terminated(exc)
        elif self.state == CommandState.CANCELLING:
            self.finished.set_result(None)
            self._dispatch_finished()
        elif self.state == CommandState.NEW:
            self._handle_exception(exc)

    def _handle_exception(self, exc: Exception) -> None:
        if not self.result.done():
            self.result.set_exception(exc)
        else:
            self._engine.loop.call_exception_handler({
                "message": f"{type(self).__name__} failed after returning preliminary result ({self.result!r})",
                "exception": exc,
                "protocol": self._engine,
                "transport": self._engine.transport,
            })

        if not self.finished.done():
            self.finished.set_result(None)
            self._dispatch_finished()

    def set_finished(self) -> None:
        assert self.state in [CommandState.ACTIVE, CommandState.CANCELLING], self.state
        if not self.result.done():
            self.result.set_exception(
                EngineError(f"engine command finished before returning result: {self!r}")
            )
        self.state = CommandState.DONE
        self.finished.set_result(None)
        self._dispatch_finished()

    def _cancel(self) -> None:
        if self.state != CommandState.CANCELLING and self.state != CommandState.DONE:
            assert self.state == CommandState.ACTIVE, self.state
            self.state = CommandState.CANCELLING
            self.cancel()

    def _start(self) -> None:
        assert self.state == CommandState.NEW, self.state
        self.state = CommandState.ACTIVE
        try:
            self.check_initialized()
            self.start()
        except EngineError as err:
            self._handle_exception(err)

    def _line_received(self, line: str) -> None:
        assert self.state in [CommandState.ACTIVE, CommandState.CANCELLING], self.state
        try:
            self.line_received(line)
        except EngineError as err:
            self._handle_exception(err)

    def cancel(self) -> None:
        pass

    def check_initialized(self) -> None:
        if not self._engine.initialized:
            raise EngineError("tried to run command, but engine is not initialized")

    def start(self) -> None:
        raise NotImplementedError

    def line_received(self, line: str) -> None:
        pass

    def engine_terminated(self, exc: Exception) -> None:
        self._handle_exception(exc)

    def __repr__(self) -> str:
        return "<{} at {:#x} (state={}, result={}, finished={}>".format(
            type(self).__name__, id(self), self.state, self.result, self.finished
        )


class Protocol(asyncio.SubprocessProtocol, metaclass=abc.ABCMeta):
    """Protocol for communicating with a chess engine process."""

    options: MutableMapping[str, Option]
    id: Dict[str, str]
    returncode: asyncio.Future[int]

    def __init__(self) -> None:
        self.loop = asyncio.get_running_loop()
        self.transport: Optional[asyncio.SubprocessTransport] = None

        self.buffer: Dict[int, bytearray] = {
            1: bytearray(),
            2: bytearray(),
        }

        self.command: Optional[BaseCommand[Any]] = None
        self.next_command: Optional[BaseCommand[Any]] = None

        self.initialized = False
        self.returncode: asyncio.Future[int] = asyncio.Future()

    def connection_made(self, transport: asyncio.BaseTransport) -> None:
        self.transport = transport  # type: ignore
        LOGGER.debug("%s: Connection made", self)

    def connection_lost(self, exc: Optional[Exception]) -> None:
        assert self.transport is not None
        code = self.transport.get_returncode()
        assert code is not None, "connection lost, but got no returncode"
        LOGGER.debug("%s: Connection lost (exit code: %d, error: %s)", self, code, exc)

        command, self.command = self.command, None
        next_command, self.next_command = self.next_command, None
        if command:
            command._engine_terminated(code)
        if next_command:
            next_command._engine_terminated(code)

        self.returncode.set_result(code)

    def process_exited(self) -> None:
        LOGGER.debug("%s: Process exited", self)

    def send_line(self, line: str) -> None:
        LOGGER.debug("%s: << %s", self, line)
        assert self.transport is not None, "cannot send line before connection is made"
        stdin = self.transport.get_pipe_transport(0)
        stdin.write((line + "\n").encode("utf-8"))  # type: ignore

    def pipe_data_received(self, fd: int, data: Union[bytes, str]) -> None:
        self.buffer[fd].extend(data)  # type: ignore
        while b"\n" in self.buffer[fd]:
            line_bytes, self.buffer[fd] = self.buffer[fd].split(b"\n", 1)
            if line_bytes.endswith(b"\r"):
                line_bytes = line_bytes[:-1]
            try:
                line = line_bytes.decode("utf-8")
            except UnicodeDecodeError as err:
                LOGGER.warning("%s: >> %r (%s)", self, bytes(line_bytes), err)
            else:
                if fd == 1:
                    self._line_received(line)
                else:
                    self.error_line_received(line)

    def error_line_received(self, line: str) -> None:
        LOGGER.warning("%s: stderr >> %s", self, line)

    def _line_received(self, line: str) -> None:
        LOGGER.debug("%s: >> %s", self, line)
        self.line_received(line)
        if self.command:
            self.command._line_received(line)

    def line_received(self, line: str) -> None:
        pass

    async def communicate(self, command_factory: Callable[["Protocol"], BaseCommand[T]]) -> T:
        command = command_factory(self)

        if self.returncode.done():
            raise EngineTerminatedError(
                f"engine process dead (exit code: {self.returncode.result()})"
            )

        assert command.state == CommandState.NEW, command.state

        if self.next_command is not None:
            self.next_command.result.cancel()
            self.next_command.finished.cancel()
            self.next_command.set_finished()

        self.next_command = command

        def previous_command_finished() -> None:
            self.command, self.next_command = self.next_command, None
            if self.command is not None:
                cmd = self.command

                def cancel_if_cancelled(result: asyncio.Future[T]) -> None:
                    if result.cancelled():
                        cmd._cancel()

                cmd.result.add_done_callback(cancel_if_cancelled)
                cmd._start()
                cmd.add_finished_callback(previous_command_finished)

        if self.command is None:
            previous_command_finished()
        elif not self.command.result.done():
            self.command.result.cancel()
        elif not self.command.result.cancelled():
            self.command._cancel()

        return await command.result

    def __repr__(self) -> str:
        pid = self.transport.get_pid() if self.transport is not None else "?"
        return f"<{type(self).__name__} (pid={pid})>"

    @abc.abstractmethod
    async def initialize(self) -> None:
        """Initializes the engine."""

    @abc.abstractmethod
    async def ping(self) -> None:
        """Pings the engine and waits for a response."""

    @abc.abstractmethod
    async def configure(self, options: ConfigMapping) -> None:
        """Configures global engine options."""

    @abc.abstractmethod
    async def send_opponent_information(
        self,
        *,
        opponent: Optional[Opponent] = None,
        engine_rating: Optional[int] = None,
    ) -> None:
        """Sends the engine information about its opponent."""

    @abc.abstractmethod
    async def play(
        self,
        board: Any,
        limit: Limit,
        *,
        game: object = None,
        info: Info = INFO_NONE,
        ponder: bool = False,
        draw_offered: bool = False,
        root_moves: Optional[Iterable[Any]] = None,
        options: ConfigMapping = {},
        opponent: Optional[Opponent] = None,
    ) -> PlayResult:
        """Plays a position."""

    @typing.overload
    async def analyse(
        self, board: Any, limit: Limit, *,
        game: object = None, info: Info = INFO_ALL,
        root_moves: Optional[Iterable[Any]] = None,
        options: ConfigMapping = {},
    ) -> InfoDict: ...

    @typing.overload
    async def analyse(
        self, board: Any, limit: Limit, *, multipv: int,
        game: object = None, info: Info = INFO_ALL,
        root_moves: Optional[Iterable[Any]] = None,
        options: ConfigMapping = {},
    ) -> List[InfoDict]: ...

    @typing.overload
    async def analyse(
        self, board: Any, limit: Limit, *, multipv: Optional[int] = None,
        game: object = None, info: Info = INFO_ALL,
        root_moves: Optional[Iterable[Any]] = None,
        options: ConfigMapping = {},
    ) -> Union[List[InfoDict], InfoDict]: ...

    async def analyse(
        self,
        board: Any,
        limit: Limit,
        *,
        multipv: Optional[int] = None,
        game: object = None,
        info: Info = INFO_ALL,
        root_moves: Optional[Iterable[Any]] = None,
        options: ConfigMapping = {},
    ) -> Union[List[InfoDict], InfoDict]:
        """Analyses a position."""
        analysis = await self.analysis(
            board, limit, multipv=multipv, game=game,
            info=info, root_moves=root_moves, options=options,
        )
        with analysis:
            await analysis.wait()
        return analysis.info if multipv is None else analysis.multipv

    @abc.abstractmethod
    async def analysis(
        self,
        board: Any,
        limit: Optional[Limit] = None,
        *,
        multipv: Optional[int] = None,
        game: object = None,
        info: Info = INFO_ALL,
        root_moves: Optional[Iterable[Any]] = None,
        options: ConfigMapping = {},
    ) -> AnalysisResult:
        """Starts analysing a position."""

    @abc.abstractmethod
    async def send_game_result(
        self,
        board: Any,
        winner: Optional[bool] = None,
        game_ending: Optional[str] = None,
        game_complete: bool = True,
    ) -> None:
        """Sends the engine the result of the game."""

    @abc.abstractmethod
    async def quit(self) -> None:
        """Asks the engine to shut down."""

    @classmethod
    async def popen(
        cls: Type[ProtocolT],
        command: Union[str, List[str]],
        *,
        setpgrp: bool = False,
        **popen_args: Any,
    ) -> Tuple[asyncio.SubprocessTransport, ProtocolT]:
        if not isinstance(command, list):
            command = [command]

        if setpgrp:
            try:
                popen_args["creationflags"] = (
                    popen_args.get("creationflags", 0)
                    | subprocess.CREATE_NEW_PROCESS_GROUP
                )
            except AttributeError:
                if sys.version_info >= (3, 11):
                    popen_args["process_group"] = 0
                else:
                    popen_args["start_new_session"] = True

        return await asyncio.get_running_loop().subprocess_exec(
            cls, *command, **popen_args
        )


async def _async(sync: Callable[[], T]) -> T:
    return sync()
