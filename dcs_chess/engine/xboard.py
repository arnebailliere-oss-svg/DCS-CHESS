"""FR-E3: XBoard/CECP protocol implementation."""

from __future__ import annotations

import asyncio
import copy
import logging
import re
import shlex
from typing import (
    Any, Callable, Dict, Iterable, List, Optional,
    Tuple, Union,
)

from ..core.constants import STARTING_FEN, WHITE, BLACK
from ..core.move import Move
from ..core.status import Termination

from .protocol import BaseCommand, ConfigMapping, Protocol, T, ProtocolT
from .results import (
    AnalysisResult, BestMove, ConfigValue, EngineError,
    Info, InfoDict, Limit, MANAGED_OPTIONS, Option,
    Opponent, PlayResult,
    INFO_NONE, INFO_ALL, INFO_PV,
)
from .scores import Cp, Mate, MateGiven, PovScore, Score

LOGGER = logging.getLogger(__name__)

XBOARD_ERROR_REGEX = re.compile(r"^\s*(Error|Illegal move)(\s*\([^()]+\))?\s*:")


def _next_token(line: str) -> Tuple[str, str]:
    parts = line.split(maxsplit=1)
    return parts[0] if parts else "", parts[1] if len(parts) == 2 else ""


def _chain_config(a: ConfigMapping, b: ConfigMapping):
    for name, value in a.items():
        yield name, value
    for name, value in b.items():
        if name not in a:
            yield name, value


def _parse_xboard_option(feature: str) -> Option:
    params = feature.split()

    name = params[0]
    type_ = params[1][1:]
    default: Optional[ConfigValue] = None
    min_val = None
    max_val = None
    var = None

    if type_ == "combo":
        var = []
        choices = params[2:]
        for choice in choices:
            if choice == "///":
                continue
            elif choice[0] == "*":
                default = choice[1:]
                var.append(choice[1:])
            else:
                var.append(choice)
    elif type_ == "check":
        default = int(params[2])
    elif type_ in ["string", "file", "path"]:
        if len(params) > 2:
            default = params[2]
        else:
            default = ""
    elif type_ == "spin":
        default = int(params[2])
        min_val = int(params[3])
        max_val = int(params[4])

    return Option(name, type_, default, min_val, max_val, var)


def _parse_xboard_post(line: str, root_board: Any, selector: Info = INFO_ALL) -> InfoDict:
    info: InfoDict = {}

    pv_tokens = line.split()
    integer_tokens: List[int] = []
    while pv_tokens:
        token = pv_tokens.pop(0)
        try:
            integer_tokens.append(int(token))
        except ValueError:
            pv_tokens.insert(0, token)
            break

    if len(integer_tokens) < 4:
        return info

    info["depth"] = integer_tokens.pop(0)
    cp = integer_tokens.pop(0)
    info["time"] = int(integer_tokens.pop(0)) / 100
    info["nodes"] = int(integer_tokens.pop(0))

    if cp <= -100000:
        score: Score = Mate(cp + 100000)
    elif cp == 100000:
        score = MateGiven
    elif cp >= 100000:
        score = Mate(cp - 100000)
    else:
        score = Cp(cp)
    info["score"] = PovScore(score, root_board.turn)

    if integer_tokens:
        info["seldepth"] = integer_tokens.pop(0)
    if integer_tokens:
        info["nps"] = integer_tokens.pop(0)

    while len(integer_tokens) > 1:
        integer_tokens.pop(0)

    if integer_tokens:
        info["tbhits"] = integer_tokens.pop(0)

    pv: List[Move] = []
    board = root_board.copy(stack=False)
    for token in pv_tokens:
        if token.rstrip(".").isdigit():
            continue

        try:
            pv.append(board.push_xboard(token))
        except ValueError:
            break

        if not (selector & INFO_PV):
            break
    info["pv"] = pv

    return info


class XBoardProtocol(Protocol):
    """An implementation of the
    `XBoard protocol <http://hgm.nubati.net/CECP.html>`__ (CECP)."""

    def __init__(self) -> None:
        super().__init__()
        self.features: Dict[str, Union[int, str]] = {}
        self.id: Dict[str, str] = {}
        self.options: Dict[str, Option] = {
            "random": Option("random", "check", False, None, None, None),
            "computer": Option("computer", "check", False, None, None, None),
            "name": Option("name", "string", "", None, None, None),
            "engine_rating": Option("engine_rating", "spin", 0, None, None, None),
            "opponent_rating": Option("opponent_rating", "spin", 0, None, None, None),
        }
        self.config: Dict[str, ConfigValue] = {}
        self.target_config: Dict[str, ConfigValue] = {}
        self.board = self._make_board()
        self.game: object = None
        self.clock_id: object = None
        self.first_game = True

    @staticmethod
    def _make_board() -> Any:
        from ..core.board import Board
        return Board()

    async def initialize(self) -> None:
        class XBoardInitializeCommand(BaseCommand[None]):
            def __init__(cmd, engine: XBoardProtocol):
                super().__init__(engine)
                cmd.engine = engine

            def check_initialized(cmd) -> None:
                if cmd.engine.initialized:
                    raise EngineError("engine already initialized")

            def start(cmd) -> None:
                cmd.engine.send_line("xboard")
                cmd.engine.send_line("protover 2")
                cmd.timeout_handle = cmd.engine.loop.call_later(
                    2.0, lambda: cmd.timeout()
                )

            def timeout(cmd) -> None:
                LOGGER.error("%s: Timeout during initialization", cmd.engine)
                cmd.end()

            def line_received(cmd, line: str) -> None:
                token, remaining = _next_token(line)
                if token.startswith("#"):
                    pass
                elif token == "feature":
                    cmd._feature(remaining)
                elif XBOARD_ERROR_REGEX.match(line):
                    raise EngineError(line)

            def _feature(cmd, arg: str) -> None:
                for feature in shlex.split(arg):
                    key, value = feature.split("=", 1)
                    if key == "option":
                        option = _parse_xboard_option(value)
                        if option.name not in [
                            "random", "computer", "cores", "memory",
                        ]:
                            cmd.engine.options[option.name] = option
                    else:
                        try:
                            cmd.engine.features[key] = int(value)
                        except ValueError:
                            cmd.engine.features[key] = value

                if "done" in cmd.engine.features:
                    cmd.timeout_handle.cancel()
                if cmd.engine.features.get("done"):
                    cmd.end()

            def end(cmd) -> None:
                if not cmd.engine.features.get("ping", 0):
                    cmd.result.set_exception(
                        EngineError(
                            "xboard engine did not declare required feature: ping"
                        )
                    )
                    cmd.set_finished()
                    return
                if not cmd.engine.features.get("setboard", 0):
                    cmd.result.set_exception(
                        EngineError(
                            "xboard engine did not declare required feature: setboard"
                        )
                    )
                    cmd.set_finished()
                    return

                if not cmd.engine.features.get("reuse", 1):
                    LOGGER.warning("%s: Rejecting feature reuse=0", cmd.engine)
                    cmd.engine.send_line("rejected reuse")
                if not cmd.engine.features.get("sigterm", 1):
                    LOGGER.warning(
                        "%s: Rejecting feature sigterm=0", cmd.engine
                    )
                    cmd.engine.send_line("rejected sigterm")
                if cmd.engine.features.get("san", 0):
                    LOGGER.warning(
                        "%s: Rejecting feature san=1", cmd.engine
                    )
                    cmd.engine.send_line("rejected san")

                if "myname" in cmd.engine.features:
                    cmd.engine.id["name"] = str(
                        cmd.engine.features["myname"]
                    )

                if cmd.engine.features.get("memory", 0):
                    cmd.engine.options["memory"] = Option(
                        "memory", "spin", 16, 1, None, None
                    )
                    cmd.engine.send_line("accepted memory")
                if cmd.engine.features.get("smp", 0):
                    cmd.engine.options["cores"] = Option(
                        "cores", "spin", 1, 1, None, None
                    )
                    cmd.engine.send_line("accepted smp")
                if cmd.engine.features.get("egt"):
                    for egt in str(cmd.engine.features["egt"]).split(","):
                        name = f"egtpath {egt}"
                        cmd.engine.options[name] = Option(
                            name, "path", None, None, None, None
                        )
                    cmd.engine.send_line("accepted egt")

                for option in cmd.engine.options.values():
                    if option.default is not None:
                        cmd.engine.config[option.name] = option.default
                    if option.default is not None and not option.is_managed():
                        cmd.engine.target_config[option.name] = option.default

                cmd.engine.initialized = True
                cmd.result.set_result(None)
                cmd.set_finished()

        return await self.communicate(XBoardInitializeCommand)

    def _ping(self, n: int) -> None:
        self.send_line(f"ping {n}")

    def _variant(self, variant: Optional[str]) -> None:
        variants = str(self.features.get("variants", "")).split(",")
        if not variant or variant not in variants:
            raise EngineError(
                "unsupported xboard variant: {} (available: {})".format(
                    variant, ", ".join(variants)
                )
            )
        self.send_line(f"variant {variant}")

    def _new(
        self,
        board: Any,
        game: object,
        options: ConfigMapping,
        opponent: Optional[Opponent] = None,
    ) -> None:
        self._configure(options)
        self._configure(self._opponent_configuration(opponent=opponent))

        root = board.root()
        new_options = any(
            param in options for param in ("random", "computer")
        )
        new_game = (
            self.first_game
            or self.game != game
            or new_options
            or opponent
            or root != self.board.root()
        )
        self.game = game
        self.first_game = False
        if new_game:
            self.board = root
            self.send_line("new")

            variant = type(board).xboard_variant
            if variant == "normal" and board.chess960:
                self._variant("fischerandom")
            elif variant != "normal":
                self._variant(variant)

            if self.config.get("random"):
                self.send_line("random")

            opponent_name = self.config.get("name")
            if opponent_name and self.features.get("name", True):
                self.send_line(f"name {opponent_name}")

            opponent_rating = self.config.get("opponent_rating")
            engine_rating = self.config.get("engine_rating")
            if engine_rating or opponent_rating:
                self.send_line(
                    f"rating {engine_rating or 0} {opponent_rating or 0}"
                )

            if self.config.get("computer"):
                self.send_line("computer")

            self.send_line("force")

            fen = root.fen(shredder=board.chess960, en_passant="fen")
            if variant != "normal" or fen != STARTING_FEN or board.chess960:
                self.send_line(f"setboard {fen}")
        else:
            self.send_line("force")

        common_stack_len = 0
        if not new_game:
            for left, right in zip(self.board.move_stack, board.move_stack):
                if left == right:
                    common_stack_len += 1
                else:
                    break

            while len(self.board.move_stack) > common_stack_len + 1:
                self.send_line("remove")
                self.board.pop()
                self.board.pop()

            while len(self.board.move_stack) > common_stack_len:
                self.send_line("undo")
                self.board.pop()

        for move in board.move_stack[common_stack_len:]:
            if not move:
                LOGGER.warning(
                    "Null move (in %s) may not be supported by all XBoard engines",
                    self.board.fen(),
                )
            prefix = (
                "usermove " if self.features.get("usermove", 0) else ""
            )
            self.send_line(prefix + self.board.xboard(move))
            self.board.push(move)

    async def ping(self) -> None:
        class XBoardPingCommand(BaseCommand[None]):
            def __init__(cmd, engine: XBoardProtocol):
                super().__init__(engine)
                cmd.engine = engine

            def start(cmd) -> None:
                n = id(cmd) & 0xFFFF
                cmd.pong = f"pong {n}"
                cmd.engine._ping(n)

            def line_received(cmd, line: str) -> None:
                if line == cmd.pong:
                    cmd.result.set_result(None)
                    cmd.set_finished()
                elif not line.startswith("#"):
                    LOGGER.warning(
                        "%s: Unexpected engine output: %r",
                        cmd.engine,
                        line,
                    )
                elif XBOARD_ERROR_REGEX.match(line):
                    raise EngineError(line)

        return await self.communicate(XBoardPingCommand)

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
        if root_moves is not None:
            raise EngineError(
                "play with root_moves, but xboard supports 'include' only in analysis mode"
            )

        engine = self

        class XBoardPlayCommand(BaseCommand[PlayResult]):
            def __init__(cmd, eng: XBoardProtocol):
                super().__init__(eng)
                cmd.engine = eng

            def start(cmd) -> None:
                cmd.play_result = PlayResult(None, None)
                cmd.stopped = False
                cmd.pong_after_move: Optional[str] = None
                cmd.pong_after_ponder: Optional[str] = None

                cmd.engine._new(board, game, options, opponent)

                clock = (
                    limit.white_clock if board.turn else limit.black_clock
                )
                increment = (
                    limit.white_inc if board.turn else limit.black_inc
                )
                if (
                    limit.clock_id is None
                    or limit.clock_id != cmd.engine.clock_id
                ):
                    cmd._send_time_control(clock, increment)
                cmd.engine.clock_id = limit.clock_id
                if limit.nodes is not None:
                    if (
                        limit.time is not None
                        or limit.white_clock is not None
                        or limit.black_clock is not None
                        or increment is not None
                    ):
                        raise EngineError(
                            "xboard does not support mixing node limits with time limits"
                        )

                    if "nps" not in cmd.engine.features:
                        LOGGER.warning(
                            "%s: Engine did not explicitly declare support for node limits (feature nps=?)",
                            cmd.engine,
                        )
                    elif not cmd.engine.features["nps"]:
                        raise EngineError(
                            "xboard engine does not support node limits (feature nps=0)"
                        )

                    cmd.engine.send_line("nps 1")
                    cmd.engine.send_line(
                        f"st {max(1, int(limit.nodes))}"
                    )
                if limit.depth is not None:
                    cmd.engine.send_line(
                        f"sd {max(1, int(limit.depth))}"
                    )
                if limit.white_clock is not None:
                    cmd.engine.send_line(
                        "{} {}".format(
                            "time" if board.turn else "otim",
                            max(1, round(limit.white_clock * 100)),
                        )
                    )
                if limit.black_clock is not None:
                    cmd.engine.send_line(
                        "{} {}".format(
                            "otim" if board.turn else "time",
                            max(1, round(limit.black_clock * 100)),
                        )
                    )

                if draw_offered and cmd.engine.features.get("draw", 1):
                    cmd.engine.send_line("draw")

                cmd.engine.send_line("post" if info else "nopost")
                cmd.engine.send_line("hard" if ponder else "easy")
                cmd.engine.send_line("go")

            def line_received(cmd, line: str) -> None:
                token, remaining = _next_token(line)
                if token == "move":
                    cmd._move(remaining.strip())
                elif token == "Hint:":
                    cmd._hint(remaining.strip())
                elif token == "pong":
                    pong_line = f"{token} {remaining.strip()}"
                    if pong_line == cmd.pong_after_move:
                        if not cmd.result.done():
                            cmd.result.set_result(cmd.play_result)
                        if not ponder:
                            cmd.set_finished()
                    elif pong_line == cmd.pong_after_ponder:
                        if not cmd.result.done():
                            cmd.result.set_result(cmd.play_result)
                        cmd.set_finished()
                elif f"{token} {remaining.strip()}" == "offer draw":
                    if not cmd.result.done():
                        cmd.play_result.draw_offered = True
                    cmd._ping_after_move()
                elif line.strip() == "resign":
                    if not cmd.result.done():
                        cmd.play_result.resigned = True
                    cmd._ping_after_move()
                elif token in ["1-0", "0-1", "1/2-1/2"]:
                    if "resign" in line and not cmd.result.done():
                        cmd.play_result.resigned = True
                    cmd._ping_after_move()
                elif token.startswith("#"):
                    pass
                elif XBOARD_ERROR_REGEX.match(line):
                    cmd.engine.first_game = True
                    raise EngineError(line)
                elif (
                    len(line.split()) >= 4 and line.lstrip()[0].isdigit()
                ):
                    cmd._post(line)
                else:
                    LOGGER.warning(
                        "%s: Unexpected engine output: %r",
                        cmd.engine,
                        line,
                    )

            def _send_time_control(
                cmd, clock: Optional[float], increment: Optional[float]
            ) -> None:
                if (
                    limit.remaining_moves
                    or clock is not None
                    or increment is not None
                ):
                    base_mins, base_secs = divmod(int(clock or 0), 60)
                    cmd.engine.send_line(
                        f"level {limit.remaining_moves or 0} {base_mins}:{base_secs:02d} {increment or 0}"
                    )
                if limit.time is not None:
                    cmd.engine.send_line(
                        f"st {max(0.01, limit.time)}"
                    )

            def _post(cmd, line: str) -> None:
                if not cmd.result.done():
                    cmd.play_result.info = _parse_xboard_post(
                        line, cmd.engine.board, info
                    )

            def _move(cmd, arg: str) -> None:
                if (
                    not cmd.result.done()
                    and cmd.play_result.move is None
                ):
                    try:
                        cmd.play_result.move = (
                            cmd.engine.board.push_xboard(arg)
                        )
                    except ValueError as err:
                        cmd.result.set_exception(EngineError(err))
                    else:
                        cmd._ping_after_move()
                else:
                    try:
                        cmd.engine.board.push_xboard(arg)
                    except ValueError:
                        LOGGER.exception(
                            "Exception playing unexpected move"
                        )

            def _hint(cmd, arg: str) -> None:
                if (
                    not cmd.result.done()
                    and cmd.play_result.move is not None
                    and cmd.play_result.ponder is None
                ):
                    try:
                        cmd.play_result.ponder = (
                            cmd.engine.board.parse_xboard(arg)
                        )
                    except ValueError:
                        LOGGER.exception("Exception parsing hint")
                else:
                    LOGGER.warning("Unexpected hint: %r", arg)

            def _ping_after_move(cmd) -> None:
                if cmd.pong_after_move is None:
                    n = id(cmd) & 0xFFFF
                    cmd.pong_after_move = f"pong {n}"
                    cmd.engine._ping(n)

            def cancel(cmd) -> None:
                if cmd.stopped:
                    return
                cmd.stopped = True

                if cmd.result.cancelled():
                    cmd.engine.send_line("?")

                if ponder:
                    cmd.engine.send_line("easy")

                    n = (id(cmd) + 1) & 0xFFFF
                    cmd.pong_after_ponder = f"pong {n}"
                    cmd.engine._ping(n)

            def engine_terminated(cmd, exc: Exception) -> None:
                if not cmd.result.done():
                    super(XBoardPlayCommand, cmd).engine_terminated(exc)

        return await self.communicate(XBoardPlayCommand)

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
        if multipv is not None:
            raise EngineError("xboard engine does not support multipv")

        if limit is not None and (
            limit.white_clock is not None or limit.black_clock is not None
        ):
            raise EngineError(
                "xboard analysis does not support clock limits"
            )

        engine = self

        class XBoardAnalysisCommand(BaseCommand[AnalysisResult]):
            def __init__(cmd, eng: XBoardProtocol):
                super().__init__(eng)
                cmd.engine = eng

            def start(cmd) -> None:
                cmd.stopped = False
                cmd.best_move: Optional[Move] = None
                cmd.analysis = AnalysisResult(stop=lambda: cmd.cancel())
                cmd.final_pong: Optional[str] = None

                cmd.engine._new(board, game, options)

                if root_moves is not None:
                    if not cmd.engine.features.get("exclude", 0):
                        raise EngineError(
                            "xboard engine does not support root_moves (feature exclude=0)"
                        )

                    cmd.engine.send_line("exclude all")
                    for move in root_moves:
                        cmd.engine.send_line(
                            f"include {cmd.engine.board.xboard(move)}"
                        )

                cmd.engine.send_line("post")
                cmd.engine.send_line("analyze")

                cmd.result.set_result(cmd.analysis)

                if limit is not None and limit.time is not None:
                    cmd.time_limit_handle: Optional[asyncio.Handle] = (
                        cmd.engine.loop.call_later(
                            limit.time, lambda: cmd.cancel()
                        )
                    )
                else:
                    cmd.time_limit_handle = None

            def line_received(cmd, line: str) -> None:
                token, remaining = _next_token(line)
                if token.startswith("#"):
                    pass
                elif (
                    len(line.split()) >= 4 and line.lstrip()[0].isdigit()
                ):
                    cmd._post(line)
                elif (
                    f"{token} {remaining.strip()}" == cmd.final_pong
                ):
                    cmd.end()
                elif XBOARD_ERROR_REGEX.match(line):
                    cmd.engine.first_game = True
                    raise EngineError(line)
                else:
                    LOGGER.warning(
                        "%s: Unexpected engine output: %r",
                        cmd.engine,
                        line,
                    )

            def _post(cmd, line: str) -> None:
                post_info = _parse_xboard_post(
                    line, cmd.engine.board, info
                )
                cmd.analysis.post(post_info)

                pv = post_info.get("pv")
                if pv:
                    cmd.best_move = pv[0]

                if limit is not None:
                    if (
                        limit.time is not None
                        and post_info.get("time", 0) >= limit.time
                    ):
                        cmd.cancel()
                    elif (
                        limit.nodes is not None
                        and post_info.get("nodes", 0) >= limit.nodes
                    ):
                        cmd.cancel()
                    elif (
                        limit.depth is not None
                        and post_info.get("depth", 0) >= limit.depth
                    ):
                        cmd.cancel()
                    elif limit.mate is not None and "score" in post_info:
                        if post_info["score"].relative >= Mate(limit.mate):
                            cmd.cancel()

            def end(cmd) -> None:
                if cmd.time_limit_handle:
                    cmd.time_limit_handle.cancel()

                cmd.set_finished()
                cmd.analysis.set_finished(BestMove(cmd.best_move, None))

            def cancel(cmd) -> None:
                if cmd.stopped:
                    return
                cmd.stopped = True

                cmd.engine.send_line(".")
                cmd.engine.send_line("exit")

                n = id(cmd) & 0xFFFF
                cmd.final_pong = f"pong {n}"
                cmd.engine._ping(n)

            def engine_terminated(cmd, exc: Exception) -> None:
                LOGGER.debug(
                    "%s: Closing analysis because engine has been terminated (error: %s)",
                    cmd.engine,
                    exc,
                )

                if cmd.time_limit_handle:
                    cmd.time_limit_handle.cancel()

                cmd.analysis.set_exception(exc)

        return await self.communicate(XBoardAnalysisCommand)

    def _setoption(self, name: str, value: ConfigValue) -> None:
        if value is not None and value == self.config.get(name):
            return

        try:
            option = self.options[name]
        except KeyError:
            raise EngineError(f"unsupported xboard option or command: {name}")

        self.config[name] = value = option.parse(value)

        if name in [
            "random", "computer", "name",
            "engine_rating", "opponent_rating",
        ]:
            pass
        elif name in ["memory", "cores"] or name.startswith("egtpath "):
            self.send_line(f"{name} {value}")
        elif value is None:
            self.send_line(f"option {name}")
        elif value is True:
            self.send_line(f"option {name}=1")
        elif value is False:
            self.send_line(f"option {name}=0")
        else:
            self.send_line(f"option {name}={value}")

    def _configure(self, options: ConfigMapping) -> None:
        for name, value in _chain_config(options, self.target_config):
            if name.lower() in MANAGED_OPTIONS:
                raise EngineError(
                    f"cannot set {name} which is automatically managed"
                )
            self._setoption(name, value)

    async def configure(self, options: ConfigMapping) -> None:
        class XBoardConfigureCommand(BaseCommand[None]):
            def __init__(cmd, engine: XBoardProtocol):
                super().__init__(engine)
                cmd.engine = engine

            def start(cmd) -> None:
                cmd.engine._configure(options)
                cmd.engine.target_config.update(
                    {
                        name: value
                        for name, value in options.items()
                        if value is not None
                    }
                )
                cmd.result.set_result(None)
                cmd.set_finished()

        return await self.communicate(XBoardConfigureCommand)

    def _opponent_configuration(
        self,
        *,
        opponent: Optional[Opponent] = None,
        engine_rating: Optional[int] = None,
    ) -> ConfigMapping:
        if opponent is None:
            return {}

        opponent_info: Dict[str, Union[int, bool, str]] = {
            "engine_rating": (
                engine_rating
                or self.target_config.get("engine_rating")
                or 0
            ),
            "opponent_rating": opponent.rating or 0,
            "computer": opponent.is_engine or False,
        }

        if opponent.name and self.features.get("name", True):
            opponent_info["name"] = (
                f"{opponent.title or ''} {opponent.name}".strip()
            )

        return opponent_info

    async def send_opponent_information(
        self,
        *,
        opponent: Optional[Opponent] = None,
        engine_rating: Optional[int] = None,
    ) -> None:
        return await self.configure(
            self._opponent_configuration(
                opponent=opponent, engine_rating=engine_rating
            )
        )

    async def send_game_result(
        self,
        board: Any,
        winner: Optional[bool] = None,
        game_ending: Optional[str] = None,
        game_complete: bool = True,
    ) -> None:
        engine = self

        class XBoardGameResultCommand(BaseCommand[None]):
            def __init__(cmd, eng: XBoardProtocol):
                super().__init__(eng)
                cmd.engine = eng

            def start(cmd) -> None:
                if game_ending and any(
                    c in game_ending for c in "{}\n\r"
                ):
                    raise EngineError(
                        f"invalid line break or curly braces in game ending message: {game_ending!r}"
                    )

                cmd.engine._new(board, cmd.engine.game, {})

                outcome = board.outcome(claim_draw=True)

                if not game_complete:
                    result = "*"
                    ending = game_ending or ""
                elif winner is not None or game_ending:
                    result = (
                        "1-0"
                        if winner == WHITE
                        else "0-1"
                        if winner == BLACK
                        else "1/2-1/2"
                    )
                    ending = game_ending or ""
                elif outcome is not None and outcome.winner is not None:
                    result = outcome.result()
                    winning_color = (
                        "White" if outcome.winner == WHITE else "Black"
                    )
                    is_checkmate = (
                        outcome.termination == Termination.CHECKMATE
                    )
                    ending = "{} {}".format(
                        winning_color,
                        "mates" if is_checkmate else "variant win",
                    )
                elif outcome is not None:
                    result = outcome.result()
                    ending = (
                        outcome.termination.name.capitalize().replace(
                            "_", " "
                        )
                    )
                else:
                    result = "*"
                    ending = ""

                ending_text = f"{{{ending}}}" if ending else ""
                cmd.engine.send_line(
                    f"result {result} {ending_text}".strip()
                )
                cmd.result.set_result(None)
                cmd.set_finished()

        return await self.communicate(XBoardGameResultCommand)

    async def quit(self) -> None:
        self.send_line("quit")
        await asyncio.shield(self.returncode)


async def popen_xboard(
    command: Union[str, List[str]],
    *,
    setpgrp: bool = False,
    **popen_args: Any,
) -> Tuple[asyncio.SubprocessTransport, XBoardProtocol]:
    transport, protocol = await XBoardProtocol.popen(
        command, setpgrp=setpgrp, **popen_args
    )
    try:
        await protocol.initialize()
    except:
        transport.close()
        raise
    return transport, protocol
