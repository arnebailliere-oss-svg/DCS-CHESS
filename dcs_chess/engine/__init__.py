"""Engine communication: UCI and XBoard protocols, async and sync wrappers."""

from .scores import (
    Score, Cp, Mate, MateGiven,
    PovScore, Wdl, PovWdl,
)

from .results import (
    ConfigValue,
    EngineError, EngineTerminatedError,
    Info, INFO_NONE, INFO_BASIC, INFO_SCORE, INFO_PV,
    INFO_REFUTATION, INFO_CURRLINE, INFO_ALL,
    InfoDict,
    PlayResult, BestMove,
    AnalysisResult, AnalysisComplete,
    Opponent, Limit,
    Option, UciOptionMap, MANAGED_OPTIONS,
    MockTransport,
)

from .protocol import (
    EventLoopPolicy,
    CommandState,
    BaseCommand,
    Protocol,
    ConfigMapping,
    run_in_background,
)

from .uci import UciProtocol, popen_uci
from .xboard import XBoardProtocol, popen_xboard
from .simple import SimpleEngine, SimpleAnalysisResult
