"""FR-E2: UCI protocol implementation."""

from __future__ import annotations

import copy
import logging
import re
import time
from typing import (
    Any, Callable, Dict, Iterator, List,
    Literal, Optional, Iterable, Tuple, Union,
)

from ..core.constants import STARTING_FEN, WHITE
from ..core.move import Move

from .protocol import (
    BaseCommand, CommandState, ConfigMapping, Protocol, T,
    ProtocolT,
)
from .results import (
    AnalysisResult, BestMove, ConfigValue, EngineError,
    Info, InfoDict, Limit, MANAGED_OPTIONS, Option,
    Opponent, PlayResult, UciOptionMap,
    INFO_NONE, INFO_ALL, INFO_SCORE, INFO_PV,
    INFO_REFUTATION, INFO_CURRLINE,
)
from .scores import Cp, Mate, PovScore, Wdl, PovWdl

import asyncio

LOGGER = logging.getLogger(__name__)

UCI_REGEX = re.compile(r"^[a-h][1-8][a-h][1-8][pnbrqk]?|[PNBRQK]@[a-h][1-8]|0000\Z")


def _next_token(line: str) -> Tuple[str, str]:
    parts = line.split(maxsplit=1)
    return parts[0] if parts else "", parts[1] if len(parts) == 2 else ""


def _chain_config(a: ConfigMapping, b: ConfigMapping) -> Iterator[Tuple[str, ConfigValue]]:
    for name, value in a.items():
        yield name, value
    for name, value in b.items():
        if name not in a:
            yield name, value


def _create_variation_line(root_board: Any, line: str) -> Tuple[List[Move], str]:
    board = root_board.copy(stack=False)
    currline: List[Move] = []
    while True:
        next_move, remaining = _next_token(line)
        if UCI_REGEX.match(next_move):
            currline.append(board.push_uci(next_move))
            line = remaining
        else:
            return currline, line


def _parse_uci_info(arg: str, root_board: Any, selector: Info = INFO_ALL) -> InfoDict:
    info: InfoDict = {}
    if not selector:
        return info

    remaining_line = arg
    while remaining_line:
        parameter, remaining_line = _next_token(remaining_line)

        if parameter == "string":
            info["string"] = remaining_line
            break
        elif parameter in [
            "depth", "seldepth", "nodes", "multipv",
            "currmovenumber", "hashfull", "nps", "tbhits", "cpuload",
        ]:
            try:
                number, remaining_line = _next_token(remaining_line)
                info[parameter] = int(number)  # type: ignore
            except (ValueError, IndexError):
                LOGGER.error("Exception parsing %s from info: %r", parameter, arg)
        elif parameter == "time":
            try:
                time_ms, remaining_line = _next_token(remaining_line)
                info["time"] = int(time_ms) / 1000.0
            except (ValueError, IndexError):
                LOGGER.error("Exception parsing %s from info: %r", parameter, arg)
        elif parameter == "ebf":
            try:
                number, remaining_line = _next_token(remaining_line)
                info["ebf"] = float(number)
            except (ValueError, IndexError):
                LOGGER.error("Exception parsing %s from info: %r", parameter, arg)
        elif parameter == "score" and selector & INFO_SCORE:
            try:
                kind, remaining_line = _next_token(remaining_line)
                value, remaining_line = _next_token(remaining_line)
                token, remaining_after_token = _next_token(remaining_line)
                if token in ["lowerbound", "upperbound"]:
                    info[token] = True  # type: ignore
                    remaining_line = remaining_after_token
                if kind == "cp":
                    info["score"] = PovScore(Cp(int(value)), root_board.turn)
                elif kind == "mate":
                    info["score"] = PovScore(Mate(int(value)), root_board.turn)
                else:
                    LOGGER.error("Unknown score kind %r in info (expected cp or mate): %r", kind, arg)
            except (ValueError, IndexError):
                LOGGER.error("Exception parsing score from info: %r", arg)
        elif parameter == "currmove":
            try:
                current_move, remaining_line = _next_token(remaining_line)
                info["currmove"] = Move.from_uci(current_move)
            except (ValueError, IndexError):
                LOGGER.error("Exception parsing currmove from info: %r", arg)
        elif parameter == "currline" and selector & INFO_CURRLINE:
            try:
                if "currline" not in info:
                    info["currline"] = {}

                cpunr_text, remaining_line = _next_token(remaining_line)
                cpunr = int(cpunr_text)
                currline, remaining_line = _create_variation_line(root_board, remaining_line)
                info["currline"][cpunr] = currline
            except (ValueError, IndexError):
                LOGGER.error(
                    "Exception parsing currline from info: %r, position at root: %s",
                    arg, root_board.fen(),
                )
        elif parameter == "refutation" and selector & INFO_REFUTATION:
            try:
                if "refutation" not in info:
                    info["refutation"] = {}

                board = root_board.copy(stack=False)
                refuted_text, remaining_line = _next_token(remaining_line)
                refuted = board.push_uci(refuted_text)

                refuted_by, remaining_line = _create_variation_line(board, remaining_line)
                info["refutation"][refuted] = refuted_by
            except (ValueError, IndexError):
                LOGGER.error(
                    "Exception parsing refutation from info: %r, position at root: %s",
                    arg, root_board.fen(),
                )
        elif parameter == "pv" and selector & INFO_PV:
            try:
                pv, remaining_line = _create_variation_line(root_board, remaining_line)
                info["pv"] = pv
            except (ValueError, IndexError):
                LOGGER.error(
                    "Exception parsing pv from info: %r, position at root: %s",
                    arg, root_board.fen(),
                )
        elif parameter == "wdl":
            try:
                wins, remaining_line = _next_token(remaining_line)
                draws, remaining_line = _next_token(remaining_line)
                losses, remaining_line = _next_token(remaining_line)
                info["wdl"] = PovWdl(Wdl(int(wins), int(draws), int(losses)), root_board.turn)
            except (ValueError, IndexError):
                LOGGER.error("Exception parsing wdl from info: %r", arg)

    return info


def _parse_uci_bestmove(board: Any, args: str) -> BestMove:
    tokens = args.split()

    move = None
    ponder = None

    if tokens and tokens[0] not in ["(none)", "NULL"]:
        try:
            move = board.push_uci(tokens[0].lower())
        except ValueError as err:
            raise EngineError(err)

        try:
            if len(tokens) >= 3 and tokens[1] == "ponder" and tokens[2] not in ["(none)", "NULL"]:
                ponder = board.parse_uci(tokens[2].lower())
        except ValueError:
            LOGGER.exception("Engine sent invalid ponder move")
        finally:
            board.pop()

    return BestMove(move, ponder)


class UciProtocol(Protocol):
    """An implementation of the
    `Universal Chess Interface <https://backscattering.de/chess/uci/>`_
    protocol."""

    def __init__(self) -> None:
        super().__init__()
        self.options: UciOptionMap[Option] = UciOptionMap()
        self.config: UciOptionMap[ConfigValue] = UciOptionMap()
        self.target_config: UciOptionMap[ConfigValue] = UciOptionMap()
        self.id: Dict[str, str] = {}
        self.board = self._make_board()
        self.game: object = None
        self.first_game = True
        self.may_ponderhit: Optional[Any] = None
        self.ponderhit = False

    @staticmethod
    def _make_board() -> Any:
        from ..core.board import Board
        return Board()

    def _isready(self) -> None:
        self.send_line("isready")

    def _opponent_info(self) -> None:
        opponent_info = self.config.get("UCI_Opponent") or self.target_config.get("UCI_Opponent")
        if opponent_info:
            self.send_line(f"setoption name UCI_Opponent value {opponent_info}")

    def _ucinewgame(self) -> None:
        self.send_line("ucinewgame")
        self._opponent_info()
        self.first_game = False
        self.ponderhit = False

    def debug(self, on: bool = True) -> None:
        if on:
            self.send_line("debug on")
        else:
            self.send_line("debug off")

    async def initialize(self) -> None:
        class UciInitializeCommand(BaseCommand[None]):
            def __init__(cmd, engine: UciProtocol):
                super().__init__(engine)
                cmd.engine = engine

            def check_initialized(cmd) -> None:
                if cmd.engine.initialized:
                    raise EngineError("engine already initialized")

            def start(cmd) -> None:
                cmd.engine.send_line("uci")

            def line_received(cmd, line: str) -> None:
                token, remaining = _next_token(line)
                if line.strip() == "uciok" and not cmd.result.done():
                    cmd.engine.initialized = True
                    cmd.result.set_result(None)
                    cmd.set_finished()
                elif token == "option":
                    cmd._option(remaining)
                elif token == "id":
                    cmd._id(remaining)

            def _option(cmd, arg: str) -> None:
                current_parameter: Optional[str] = None
                option_parts: Dict[str, str] = {
                    k: "" for k in ["name", "type", "default", "min", "max"]
                }
                var: List[str] = []

                parameters = list(option_parts.keys()) + ["var"]
                inner_regex = "|".join(
                    [rf"\b{parameter}\b" for parameter in parameters]
                )
                option_regex = rf"\s*({inner_regex})\s*"
                for token in re.split(option_regex, arg.strip()):
                    if token == "var" or (
                        token in option_parts and not option_parts[token]
                    ):
                        current_parameter = token
                    elif current_parameter == "var":
                        var.append(token)
                    elif current_parameter:
                        option_parts[current_parameter] = token

                def parse_min_max(
                    parts: Dict[str, str], which: str
                ) -> Optional[int]:
                    try:
                        number = parts[which]
                        return int(number) if number else None
                    except ValueError:
                        LOGGER.exception("Exception parsing option %s", which)
                        return None

                name = option_parts["name"]
                type_ = option_parts["type"]
                default = option_parts["default"]
                min_val = parse_min_max(option_parts, "min")
                max_val = parse_min_max(option_parts, "max")

                without_default = Option(name, type_, None, min_val, max_val, var or None)
                option = Option(
                    without_default.name,
                    without_default.type,
                    without_default.parse(default),
                    min_val,
                    max_val,
                    var or None,
                )
                cmd.engine.options[option.name] = option

                if option.default is not None:
                    cmd.engine.config[option.name] = option.default
                if (
                    option.default is not None
                    and not option.is_managed()
                    and option.name.lower() != "uci_analysemode"
                ):
                    cmd.engine.target_config[option.name] = option.default

            def _id(cmd, arg: str) -> None:
                key, value = _next_token(arg)
                cmd.engine.id[key] = value.strip()

        return await self.communicate(UciInitializeCommand)

    async def ping(self) -> None:
        class UciPingCommand(BaseCommand[None]):
            def __init__(cmd, engine: UciProtocol) -> None:
                super().__init__(engine)
                cmd.engine = engine

            def start(cmd) -> None:
                cmd.engine._isready()

            def line_received(cmd, line: str) -> None:
                if line.strip() == "readyok":
                    cmd.result.set_result(None)
                    cmd.set_finished()
                else:
                    LOGGER.warning("%s: Unexpected engine output: %r", cmd.engine, line)

        return await self.communicate(UciPingCommand)

    def _changed_options(self, options: ConfigMapping) -> bool:
        return any(
            value is None or value != self.config.get(name)
            for name, value in _chain_config(options, self.target_config)
        )

    def _setoption(self, name: str, value: ConfigValue) -> None:
        try:
            value = self.options[name].parse(value)
        except KeyError:
            raise EngineError(
                "engine does not support option {} (available options: {})".format(
                    name, ", ".join(self.options)
                )
            )

        if value is None or value != self.config.get(name):
            builder = ["setoption name", name]
            if value is False:
                builder.append("value false")
            elif value is True:
                builder.append("value true")
            elif value is not None:
                builder.append("value")
                builder.append(str(value))

            if name != "UCI_Opponent":
                self.send_line(" ".join(builder))
            self.config[name] = value

    def _configure(self, options: ConfigMapping) -> None:
        for name, value in _chain_config(options, self.target_config):
            if name.lower() in MANAGED_OPTIONS:
                raise EngineError(
                    "cannot set {} which is automatically managed".format(name)
                )
            self._setoption(name, value)

    async def configure(self, options: ConfigMapping) -> None:
        class UciConfigureCommand(BaseCommand[None]):
            def __init__(cmd, engine: UciProtocol):
                super().__init__(engine)
                cmd.engine = engine

            def start(cmd) -> None:
                cmd.engine._configure(options)
                cmd.engine.target_config.update(
                    {name: value for name, value in options.items() if value is not None}
                )
                cmd.result.set_result(None)
                cmd.set_finished()

        return await self.communicate(UciConfigureCommand)

    def _opponent_configuration(
        self, *, opponent: Optional[Opponent] = None
    ) -> ConfigMapping:
        if opponent and opponent.name and "UCI_Opponent" in self.options:
            rating = opponent.rating or "none"
            title = opponent.title or "none"
            player_type = "computer" if opponent.is_engine else "human"
            return {"UCI_Opponent": f"{title} {rating} {player_type} {opponent.name}"}
        else:
            return {}

    async def send_opponent_information(
        self,
        *,
        opponent: Optional[Opponent] = None,
        engine_rating: Optional[int] = None,
    ) -> None:
        return await self.configure(self._opponent_configuration(opponent=opponent))

    def _position(self, board: Any) -> None:
        uci_variant = type(board).uci_variant
        if "UCI_Variant" in self.options:
            self._setoption("UCI_Variant", uci_variant)
        elif uci_variant != "chess":
            raise EngineError("engine does not support UCI_Variant")

        if "UCI_Chess960" in self.options:
            self._setoption("UCI_Chess960", board.chess960)
        elif board.chess960:
            raise EngineError("engine does not support UCI_Chess960")

        builder = ["position"]
        safe_history = all(board.move_stack)
        root = board.root() if safe_history else board
        fen = root.fen(shredder=board.chess960, en_passant="fen")
        if uci_variant == "chess" and fen == STARTING_FEN:
            builder.append("startpos")
        else:
            builder.append("fen")
            builder.append(fen)

        if not safe_history:
            LOGGER.warning("Not transmitting history with null moves to UCI engine")
        elif board.move_stack:
            builder.append("moves")
            builder.extend(move.uci() for move in board.move_stack)

        self.send_line(" ".join(builder))
        self.board = board.copy(stack=False)

    def _go(
        self,
        limit: Limit,
        *,
        root_moves: Optional[Iterable[Any]] = None,
        ponder: bool = False,
        infinite: bool = False,
    ) -> None:
        builder = ["go"]
        if ponder:
            builder.append("ponder")
        if limit.white_clock is not None:
            builder.append("wtime")
            builder.append(str(max(1, round(limit.white_clock * 1000))))
        if limit.black_clock is not None:
            builder.append("btime")
            builder.append(str(max(1, round(limit.black_clock * 1000))))
        if limit.white_inc is not None:
            builder.append("winc")
            builder.append(str(round(limit.white_inc * 1000)))
        if limit.black_inc is not None:
            builder.append("binc")
            builder.append(str(round(limit.black_inc * 1000)))
        if limit.remaining_moves is not None and int(limit.remaining_moves) > 0:
            builder.append("movestogo")
            builder.append(str(int(limit.remaining_moves)))
        if limit.depth is not None:
            builder.append("depth")
            builder.append(str(max(1, int(limit.depth))))
        if limit.nodes is not None:
            builder.append("nodes")
            builder.append(str(max(1, int(limit.nodes))))
        if limit.mate is not None:
            builder.append("mate")
            builder.append(str(max(1, int(limit.mate))))
        if limit.time is not None:
            builder.append("movetime")
            builder.append(str(max(1, round(limit.time * 1000))))
        if infinite:
            builder.append("infinite")
        if root_moves is not None:
            builder.append("searchmoves")
            if root_moves:
                builder.extend(move.uci() for move in root_moves)
            else:
                builder.append("0000")
        self.send_line(" ".join(builder))

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
        new_options: Dict[str, ConfigValue] = {}
        for name, value in options.items():
            new_options[name] = value
        new_options.update(self._opponent_configuration(opponent=opponent))

        engine = self

        class UciPlayCommand(BaseCommand[PlayResult]):
            def __init__(cmd, eng: UciProtocol):
                super().__init__(eng)
                cmd.engine = eng

                eng.may_ponderhit = (
                    board
                    if ponder
                    and not eng.first_game
                    and game == eng.game
                    and not eng._changed_options(new_options)
                    else None
                )

            def start(cmd) -> None:
                cmd.info: InfoDict = {}
                cmd.pondering: Optional[Any] = None
                cmd.sent_isready = False
                cmd.start_time = time.perf_counter()

                if cmd.engine.ponderhit:
                    cmd.engine.ponderhit = False
                    cmd.engine.send_line("ponderhit")
                    return

                if (
                    "UCI_AnalyseMode" in cmd.engine.options
                    and "UCI_AnalyseMode" not in cmd.engine.target_config
                    and all(
                        name.lower() != "uci_analysemode" for name in new_options
                    )
                ):
                    cmd.engine._setoption("UCI_AnalyseMode", False)
                if "Ponder" in cmd.engine.options:
                    cmd.engine._setoption("Ponder", ponder)
                if "MultiPV" in cmd.engine.options:
                    cmd.engine._setoption(
                        "MultiPV", cmd.engine.options["MultiPV"].default
                    )

                new_opponent = new_options.get("UCI_Opponent") or cmd.engine.target_config.get("UCI_Opponent")
                opponent_changed = new_opponent != cmd.engine.config.get("UCI_Opponent")
                cmd.engine._configure(new_options)

                if cmd.engine.first_game or cmd.engine.game != game or opponent_changed:
                    cmd.engine.game = game
                    cmd.engine._ucinewgame()
                    cmd.sent_isready = True
                    cmd.engine._isready()
                else:
                    cmd._readyok()

            def line_received(cmd, line: str) -> None:
                token, remaining = _next_token(line)
                if token == "info":
                    cmd._info(remaining)
                elif token == "bestmove":
                    cmd._bestmove(remaining)
                elif line.strip() == "readyok" and cmd.sent_isready:
                    cmd._readyok()
                else:
                    LOGGER.warning("%s: Unexpected engine output: %r", cmd.engine, line)

            def _readyok(cmd) -> None:
                cmd.sent_isready = False
                engine._position(board)
                engine._go(limit, root_moves=root_moves)

            def _info(cmd, arg: str) -> None:
                if not cmd.pondering:
                    cmd.info.update(_parse_uci_info(arg, cmd.engine.board, info))

            def _bestmove(cmd, arg: str) -> None:
                if cmd.pondering:
                    cmd.pondering = None
                elif not cmd.result.cancelled():
                    best = _parse_uci_bestmove(cmd.engine.board, arg)
                    cmd.result.set_result(PlayResult(best.move, best.ponder, cmd.info))

                    if ponder and best.move and best.ponder:
                        cmd.pondering = board.copy()
                        cmd.pondering.push(best.move)
                        cmd.pondering.push(best.ponder)
                        cmd.engine._position(cmd.pondering)

                        time_used = time.perf_counter() - cmd.start_time
                        ponder_limit = copy.copy(limit)
                        if ponder_limit.white_clock is not None:
                            ponder_limit.white_clock += ponder_limit.white_inc or 0.0
                            if cmd.pondering.turn == WHITE:
                                ponder_limit.white_clock -= time_used
                        if ponder_limit.black_clock is not None:
                            ponder_limit.black_clock += ponder_limit.black_inc or 0.0
                            if not cmd.pondering.turn == WHITE:
                                ponder_limit.black_clock -= time_used
                        if ponder_limit.remaining_moves:
                            ponder_limit.remaining_moves -= 1

                        cmd.engine._go(ponder_limit, ponder=True)

                if not cmd.pondering:
                    cmd.end()

            def end(cmd) -> None:
                engine.may_ponderhit = None
                cmd.set_finished()

            def cancel(cmd) -> None:
                if (
                    cmd.engine.may_ponderhit
                    and cmd.pondering
                    and cmd.engine.may_ponderhit.move_stack == cmd.pondering.move_stack
                    and cmd.engine.may_ponderhit == cmd.pondering
                ):
                    cmd.engine.ponderhit = True
                    cmd.end()
                else:
                    cmd.engine.send_line("stop")

            def engine_terminated(cmd, exc: Exception) -> None:
                if not cmd.result.done():
                    super(UciPlayCommand, cmd).engine_terminated(exc)

        return await self.communicate(UciPlayCommand)

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
        engine = self

        class UciAnalysisCommand(BaseCommand[AnalysisResult]):
            def __init__(cmd, eng: UciProtocol):
                super().__init__(eng)
                cmd.engine = eng

            def start(cmd) -> None:
                cmd.analysis = AnalysisResult(stop=lambda: cmd.cancel())
                cmd.sent_isready = False

                if "Ponder" in cmd.engine.options:
                    cmd.engine._setoption("Ponder", False)
                if (
                    "UCI_AnalyseMode" in cmd.engine.options
                    and "UCI_AnalyseMode" not in cmd.engine.target_config
                    and all(name.lower() != "uci_analysemode" for name in options)
                ):
                    cmd.engine._setoption("UCI_AnalyseMode", True)
                if "MultiPV" in cmd.engine.options or (multipv and multipv > 1):
                    cmd.engine._setoption("MultiPV", 1 if multipv is None else multipv)

                cmd.engine._configure(options)

                if cmd.engine.first_game or cmd.engine.game != game:
                    cmd.engine.game = game
                    cmd.engine._ucinewgame()
                    cmd.sent_isready = True
                    cmd.engine._isready()
                else:
                    cmd._readyok()

            def line_received(cmd, line: str) -> None:
                token, remaining = _next_token(line)
                if token == "info":
                    cmd._info(remaining)
                elif token == "bestmove":
                    cmd._bestmove(remaining)
                elif line.strip() == "readyok" and cmd.sent_isready:
                    cmd._readyok()
                else:
                    LOGGER.warning("%s: Unexpected engine output: %r", cmd.engine, line)

            def _readyok(cmd) -> None:
                cmd.sent_isready = False
                cmd.engine._position(board)

                if limit:
                    cmd.engine._go(limit, root_moves=root_moves)
                else:
                    cmd.engine._go(Limit(), root_moves=root_moves, infinite=True)

                cmd.result.set_result(cmd.analysis)

            def _info(cmd, arg: str) -> None:
                cmd.analysis.post(_parse_uci_info(arg, cmd.engine.board, info))

            def _bestmove(cmd, arg: str) -> None:
                if not cmd.result.done():
                    raise EngineError("was not searching, but engine sent bestmove")
                best = _parse_uci_bestmove(cmd.engine.board, arg)
                cmd.set_finished()
                cmd.analysis.set_finished(best)

            def cancel(cmd) -> None:
                cmd.engine.send_line("stop")

            def engine_terminated(cmd, exc: Exception) -> None:
                LOGGER.debug(
                    "%s: Closing analysis because engine has been terminated (error: %s)",
                    cmd.engine, exc,
                )
                cmd.analysis.set_exception(exc)

        return await self.communicate(UciAnalysisCommand)

    async def send_game_result(
        self,
        board: Any,
        winner: Optional[bool] = None,
        game_ending: Optional[str] = None,
        game_complete: bool = True,
    ) -> None:
        pass

    async def quit(self) -> None:
        self.send_line("quit")
        await asyncio.shield(self.returncode)


async def popen_uci(
    command: Union[str, List[str]],
    *,
    setpgrp: bool = False,
    **popen_args: Any,
) -> Tuple[asyncio.SubprocessTransport, UciProtocol]:
    transport, protocol = await UciProtocol.popen(command, setpgrp=setpgrp, **popen_args)
    try:
        await protocol.initialize()
    except:
        transport.close()
        raise
    return transport, protocol
