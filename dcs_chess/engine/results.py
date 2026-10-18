"""FR-E5: Engine result types — PlayResult, BestMove, AnalysisResult, etc."""

from __future__ import annotations

import asyncio
import dataclasses
import enum
from typing import (
    Any,
    Callable,
    Dict,
    List,
    Optional,
    TypedDict,
    Union,
)


ConfigValue = Union[str, int, bool, None]


class EngineError(RuntimeError):
    """An unexpected engine error."""


class EngineTerminatedError(EngineError):
    """The engine process has terminated."""


class Info(enum.IntFlag):
    """Selects which information to retrieve from the engine."""

    NONE = 0
    BASIC = 1
    SCORE = 2
    PV = 4
    REFUTATION = 8
    CURRLINE = 16
    ALL = BASIC | SCORE | PV | REFUTATION | CURRLINE


INFO_NONE = Info.NONE
INFO_BASIC = Info.BASIC
INFO_SCORE = Info.SCORE
INFO_PV = Info.PV
INFO_REFUTATION = Info.REFUTATION
INFO_CURRLINE = Info.CURRLINE
INFO_ALL = Info.ALL


class InfoDict(TypedDict, total=False):
    """Information sent by the engine."""

    score: Any  # PovScore
    pv: Any  # List[Move]
    depth: int
    seldepth: int
    time: float
    nodes: int
    nps: int
    tbhits: int
    multipv: int
    currmove: Any  # Move
    currmovenumber: int
    hashfull: int
    cpuload: int
    refutation: Any  # Dict[Move, List[Move]]
    currline: Any  # Dict[int, List[Move]]
    ebf: float
    wdl: Any  # PovWdl
    string: str


class PlayResult:
    """Returned by :meth:`play`. Holds the engine's chosen move."""

    def __init__(
        self,
        move: Optional[Any],
        ponder: Optional[Any],
        info: Optional[InfoDict] = None,
        *,
        draw_offered: bool = False,
        resigned: bool = False,
    ) -> None:
        self.move = move
        self.ponder = ponder
        self.info: InfoDict = info if info is not None else {}
        self.draw_offered = draw_offered
        self.resigned = resigned

    def __repr__(self) -> str:
        return (
            f"<PlayResult at {id(self):#x} "
            f"(move={self.move}, ponder={self.ponder}, "
            f"info={self.info}, "
            f"draw_offered={self.draw_offered}, "
            f"resigned={self.resigned})>"
        )


class BestMove:
    """Returned with the ``bestmove`` token."""

    def __init__(self, move: Optional[Any], ponder: Optional[Any]) -> None:
        self.move = move
        self.ponder = ponder

    def __repr__(self) -> str:
        return f"<BestMove at {id(self):#x} (move={self.move}, ponder={self.ponder}>"


class AnalysisComplete(Exception):
    """Raised when trying to read from a finished analysis."""


class AnalysisResult:
    """Async queue of ``InfoDict`` updates from a running analysis."""

    def __init__(self, stop: Optional[Callable[[], None]] = None) -> None:
        self._stop = stop
        self._queue: asyncio.Queue[Any] = asyncio.Queue()
        self._posted_kork = False
        self._seen_kork = False
        self._finished: Optional[asyncio.Future[BestMove]] = None
        self.multipv: List[InfoDict] = [{}]

    def _ensure_future(self) -> asyncio.Future[BestMove]:
        if self._finished is None:
            loop = asyncio.get_event_loop()
            self._finished = loop.create_future()
        return self._finished

    def post(self, info: InfoDict) -> None:
        multipv_idx = info.get("multipv", 1) - 1
        while len(self.multipv) <= multipv_idx:
            self.multipv.append({})
        self.multipv[multipv_idx].update(info)
        self._queue.put_nowait(info)

    def _kork(self) -> None:
        if not self._posted_kork:
            self._posted_kork = True
            self._queue.put_nowait(None)

    def set_finished(self, best: BestMove) -> None:
        self._kork()
        fut = self._ensure_future()
        if not fut.done():
            fut.set_result(best)

    def set_exception(self, exc: Exception) -> None:
        self._kork()
        fut = self._ensure_future()
        if not fut.done():
            fut.set_exception(exc)

    @property
    def info(self) -> InfoDict:
        return self.multipv[0]

    def stop(self) -> None:
        if self._stop is not None:
            self._stop()

    async def wait(self) -> BestMove:
        return await asyncio.shield(self._ensure_future())

    async def get(self) -> InfoDict:
        item = await self._queue.get()
        if self._seen_kork:
            raise AnalysisComplete()
        if item is None:
            self._seen_kork = True
            raise AnalysisComplete()
        return item

    def would_block(self) -> bool:
        return self._queue.empty()

    def empty(self) -> bool:
        return self._queue.empty()

    async def next(self) -> Optional[InfoDict]:
        item = await self._queue.get()
        if item is None:
            self._seen_kork = True
            return None
        if self._seen_kork:
            return None
        return item

    def __enter__(self) -> AnalysisResult:
        return self

    def __exit__(self, exc_type: Any, exc_value: Any, traceback: Any) -> None:
        self.stop()

    def __aiter__(self) -> AnalysisResult:
        return self

    async def __anext__(self) -> InfoDict:
        item = await self.next()
        if item is None:
            raise StopAsyncIteration
        return item


@dataclasses.dataclass
class Opponent:
    """Information about the opponent to send to the engine."""

    name: Optional[str]
    title: Optional[str]
    rating: Optional[int]
    is_engine: Optional[bool]


@dataclasses.dataclass
class Limit:
    """Search limits for :meth:`play` and :meth:`analyse`."""

    time: Optional[float] = None
    depth: Optional[int] = None
    nodes: Optional[int] = None
    mate: Optional[int] = None
    white_clock: Optional[float] = None
    black_clock: Optional[float] = None
    white_inc: Optional[float] = None
    black_inc: Optional[float] = None
    remaining_moves: Optional[int] = None
    clock_id: object = None

    def __repr__(self) -> str:
        params = []
        for field in dataclasses.fields(self):
            if field.name == "clock_id":
                continue
            value = getattr(self, field.name)
            if value is not None:
                params.append(f"{field.name}={value!r}")
        return f"Limit({', '.join(params)})"


class Option:
    """An engine option as reported by the engine."""

    def __init__(
        self,
        name: str,
        type: str,
        default: ConfigValue,
        min: Optional[int],
        max: Optional[int],
        var: Optional[List[str]],
    ) -> None:
        self.name = name
        self.type = type
        self.default = default
        self.min = min
        self.max = max
        self.var = var

    def is_managed(self) -> bool:
        return self.name.lower() in MANAGED_OPTIONS

    def parse(self, value: ConfigValue) -> ConfigValue:
        if self.type == "check":
            return value and value != "false"
        elif self.type == "spin":
            try:
                value = int(value)  # type: ignore
            except ValueError:
                raise EngineError(
                    f"expected integer for spin option {self.name!r}, got: {value!r}"
                )
            if self.min is not None and value < self.min:
                raise EngineError(
                    f"expected value for option {self.name!r} to be at least {self.min}, got: {value}"
                )
            if self.max is not None and self.max < value:
                raise EngineError(
                    f"expected value for option {self.name!r} to be at most {self.max}, got: {value}"
                )
            return value
        elif self.type == "combo":
            value = str(value)
            if value not in (self.var or []):
                raise EngineError(
                    "invalid value for combo option {!r}, got: {} (available: {})".format(
                        self.name, value, ", ".join(self.var) if self.var else "-"
                    )
                )
            return value
        elif self.type in ["button", "reset", "save"]:
            return None
        elif self.type in ["string", "file", "path"]:
            value = str(value)
            if "\n" in value or "\r" in value:
                raise EngineError(
                    f"invalid line-break in string option {self.name!r}: {value!r}"
                )
            return value
        else:
            raise EngineError(f"unknown option type: {self.type!r}")

    def __repr__(self) -> str:
        return (
            f"Option(name={self.name!r}, type={self.type!r}, "
            f"default={self.default!r}, min={self.min!r}, "
            f"max={self.max!r}, var={self.var!r})"
        )


class UciOptionMap(dict):
    """A case-insensitive dictionary for UCI option names."""

    def __init__(self, data: Optional[Any] = None, **kwargs: Any) -> None:
        super().__init__()
        self._store: Dict[str, Any] = {}
        if data:
            if hasattr(data, "items"):
                for k, v in data.items():
                    self[k] = v
            else:
                for k, v in data:
                    self[k] = v
        for k, v in kwargs.items():
            self[k] = v

    def __setitem__(self, key: str, value: Any) -> None:
        self._store[key.lower()] = (key, value)

    def __getitem__(self, key: str) -> Any:
        return self._store[key.lower()][1]

    def __delitem__(self, key: str) -> None:
        del self._store[key.lower()]

    def __contains__(self, key: object) -> bool:
        if isinstance(key, str):
            return key.lower() in self._store
        return False

    def __iter__(self):
        return (k for k, _ in self._store.values())

    def __len__(self) -> int:
        return len(self._store)

    def __eq__(self, other: object) -> bool:
        if isinstance(other, UciOptionMap):
            if len(self._store) != len(other._store):
                return False
            return all(
                k in other._store and self._store[k][1] == other._store[k][1]
                for k in self._store
            )
        return NotImplemented

    def __repr__(self) -> str:
        items = ", ".join(f"{k!r}: {v!r}" for k, v in self._store.values())
        return f"UciOptionMap({{{items}}})"

    def keys(self):
        return [k for k, _ in self._store.values()]

    def values(self):
        return [v for _, v in self._store.values()]

    def items(self):
        return list(self._store.values())

    def get(self, key: str, default: Any = None) -> Any:
        try:
            return self[key]
        except KeyError:
            return default

    def copy(self) -> UciOptionMap:
        new = UciOptionMap()
        new._store = self._store.copy()
        return new


MANAGED_OPTIONS = ["uci_chess960", "uci_variant", "multipv", "ponder"]


class MockTransport(asyncio.SubprocessTransport, asyncio.WriteTransport):
    """A mock transport for testing engine protocols without a real process."""

    def __init__(self, protocol: Any) -> None:
        super().__init__()
        self._protocol = protocol
        self._expectations: List[Any] = []
        self._is_closing = False

    def set_protocol(self, protocol: Any) -> None:
        self._protocol = protocol

    def get_protocol(self) -> Any:
        return self._protocol

    def expect(self, expectation: str, responses: Optional[List[str]] = None) -> None:
        if responses is None:
            responses = []
        self._expectations.append((expectation, responses))

    def expect_ping(self) -> None:
        pass

    def assert_done(self) -> None:
        assert not self._expectations, f"Pending expectations: {self._expectations}"

    def write(self, data: bytes) -> None:
        line = data.decode().strip()
        if not self._expectations:
            return
        expected, responses = self._expectations[0]
        if line == expected:
            self._expectations.pop(0)
            for response in responses:
                self._protocol.pipe_data_received(1, (response + "\n").encode())

    def get_pid(self) -> int:
        return 0

    def get_returncode(self) -> Optional[int]:
        return None

    def get_pipe_transport(self, fd: int) -> Optional[asyncio.BaseTransport]:
        if fd == 0:
            return self
        return None

    def is_closing(self) -> bool:
        return self._is_closing

    def close(self) -> None:
        self._is_closing = True

    def get_extra_info(self, name: str, default: Any = None) -> Any:
        return default

    def abort(self) -> None:
        self._is_closing = True

    def kill(self) -> None:
        pass

    def send_signal(self, signal: int) -> None:
        pass

    def terminate(self) -> None:
        pass

    def can_write_eof(self) -> bool:
        return False

    def write_eof(self) -> None:
        raise NotImplementedError

    def get_write_buffer_size(self) -> int:
        return 0

    def get_write_buffer_limits(self) -> tuple:
        return (0, 0)

    def set_write_buffer_limits(self, high: Optional[int] = None, low: Optional[int] = None) -> None:
        pass

    def writelines(self, data: Any) -> None:
        for d in data:
            self.write(d)
