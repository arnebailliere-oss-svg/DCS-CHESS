"""Gaviota endgame tablebase probing (native and pure Python)."""

from __future__ import annotations

import ctypes
import ctypes.util
import functools
import logging
import lzma
import os
import struct
import threading
import typing
from typing import (
    Any, BinaryIO, Callable, Dict, List, Optional, Sequence, Tuple, Type, Union,
)

if typing.TYPE_CHECKING:
    from types import TracebackType

from ..core.constants import (
    KING, QUEEN, ROOK, BISHOP, KNIGHT, PAWN,
    WHITE, BLACK,
    SQUARES, SQUARE_NAMES,
    PIECE_TYPES,
)
from ..core.board import Board as _Board

LOGGER = logging.getLogger("dcs_chess.gaviota")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

tb_DRAW = 0
tb_WMATE = 1
tb_BMATE = 2
tb_FORBID = 3
tb_UNKNOWN = 7

iDRAW = 0
iWMATE = 1
iBMATE = 2
iFORBID = 3
iDRAWt = 4
iWMATEt = 5
iBMATEt = 6

PLYSHIFT = 3
INFOMASK = 7

NOINDEX = -1
NOSQUARE = 64

EGTB_MAXBLOCKSIZE = 65536
ENTRIES_PER_BLOCK = 16384

WE_FLAG = 1
NS_FLAG = 2
NW_SE_FLAG = 4

MAX_KKINDEX = 462
MAX_AAINDEX = 2016
MAX_AAAINDEX = 41664

MAX_PPINDEX = 576
MAX_PpINDEX = 1152
MAX_PP48_INDEX = 1128
MAX_PPP48_INDEX = 8648

EGKEY_PIECE_ORDER = {KING: 0, QUEEN: 1, ROOK: 2, BISHOP: 3, KNIGHT: 4, PAWN: 5}
PIECE_FROM_CHAR = {"K": KING, "Q": QUEEN, "R": ROOK, "B": BISHOP, "N": KNIGHT, "P": PAWN}
CHAR_FROM_PIECE = {v: k for k, v in PIECE_FROM_CHAR.items()}


# ---------------------------------------------------------------------------
# Square manipulation
# ---------------------------------------------------------------------------

def flip_ns(sq: int) -> int:
    return sq ^ 56

def flip_we(sq: int) -> int:
    return sq ^ 7

def flip_nw_se(sq: int) -> int:
    return ((sq & 7) << 3) | (sq >> 3)

def map88(sq: int) -> int:
    return sq + (sq & ~7)

def opp(side: int) -> int:
    return 1 - side


# ---------------------------------------------------------------------------
# ITOSQ mapping (pawn index ↔ square)
# ---------------------------------------------------------------------------

def _build_itosq() -> List[int]:
    itosq: List[int] = []
    for rank in range(6, 0, -1):
        for file in range(7, 3, -1):
            itosq.append(rank * 8 + file)
    for rank in range(6, 0, -1):
        for file in range(3, -1, -1):
            itosq.append(rank * 8 + file)
    return itosq

ITOSQ = _build_itosq()

_SQ_TO_ITOSQ: Dict[int, int] = {sq: idx for idx, sq in enumerate(ITOSQ)}

_FILE24 = [0, 1, 2, 3, 2, 3, 4, 5]

def wsq_to_pidx24(sq: int) -> int:
    return (6 - (sq >> 3)) * 4 + _FILE24[sq & 7]

def wsq_to_pidx48(sq: int) -> int:
    return (6 - (sq >> 3)) * 8 + (sq & 7)


def map24_b(sq: int) -> int:
    sq -= 8
    return ((sq & 3) + sq) >> 1


MAX_PP48_INDEX = 1128


# ---------------------------------------------------------------------------
# Initialisation — FLIPT, KKIDX
# ---------------------------------------------------------------------------

def _init_flipt() -> List[List[int]]:
    flipt = [[0] * 64 for _ in range(64)]
    for wk in range(64):
        for bk in range(64):
            f = 0
            wf, wr = wk & 7, wk >> 3
            bf, br = bk & 7, bk >> 3
            if wf > 3:
                f |= WE_FLAG
                wf = 7 - wf
                bf = 7 - bf
            if wr > 3:
                f |= NS_FLAG
                wr = 7 - wr
                br = 7 - br
            if wr > wf:
                f |= NW_SE_FLAG
                wf, wr = wr, wf
                bf, br = br, bf
            elif wr == wf and br > bf:
                f |= NW_SE_FLAG
            flipt[wk][bk] = f
    return flipt

FLIPT = _init_flipt()


def _init_kkidx() -> Tuple[List[List[int]], List[int], List[int]]:
    TRIANGLE = [0, 1, 2, 3, 9, 10, 11, 18, 19, 27]
    kkidx = [[-1] * 64 for _ in range(64)]
    wk_list: List[int] = []
    bk_list: List[int] = []
    idx = 0
    for wk in TRIANGLE:
        wf, wr = wk & 7, wk >> 3
        on_diag = (wf == wr)
        for bk in range(64):
            if wk == bk:
                continue
            bf, br = bk & 7, bk >> 3
            if abs(wf - bf) <= 1 and abs(wr - br) <= 1:
                continue
            if on_diag and br > bf:
                continue
            kkidx[wk][bk] = idx
            wk_list.append(wk)
            bk_list.append(bk)
            idx += 1
    return kkidx, wk_list, bk_list

KKIDX, _KKIDX_WK, _KKIDX_BK = _init_kkidx()


# ---------------------------------------------------------------------------
# Initialisation — AAIDX (two identical pieces), AAA (three identical pieces)
# ---------------------------------------------------------------------------

def _init_aaidx() -> Tuple[List[int], List[List[int]]]:
    aabase: List[int] = []
    aaidx = [[-1] * 64 for _ in range(64)]
    for i in range(64):
        for j in range(i + 1, 64):
            aaidx[i][j] = len(aabase)
            aaidx[j][i] = len(aabase)
            aabase.append(i)
    return aabase, aaidx

AABASE, AAIDX = _init_aaidx()


def _init_aaa() -> Tuple[List[int], List[List[int]]]:
    aaa_base: List[int] = []
    for n in range(64):
        aaa_base.append(n * (n - 1) * (n - 2) // 6 if n >= 3 else 0)
    aaa_xyz: List[List[int]] = []
    for i in range(64):
        for j in range(i + 1, 64):
            for k in range(j + 1, 64):
                aaa_xyz.append([i, j, k])
    return aaa_base, aaa_xyz

AAA_BASE, AAA_XYZ = _init_aaa()


# ---------------------------------------------------------------------------
# Initialisation — PPIDX (two-pawn pair indexing)
# ---------------------------------------------------------------------------

def _init_ppidx() -> Tuple[List[List[int]], List[int], List[int]]:
    ppidx = [[-1] * 48 for _ in range(24)]
    pp_hi: List[int] = []
    pp_lo: List[int] = []

    excluded: set[int] = {0}
    idx = 0

    for l in range(48):
        if l not in excluded:
            ppidx[0][l] = idx
            pp_hi.append(0)
            pp_lo.append(l)
            idx += 1

    for h in range(1, 24):
        s = (h - 1) // 4
        p = (h - 1) % 4
        base = 2 * s
        if p == 0:
            excluded.add(base * 4 + 1)
            excluded.add((base + 1) * 4 + 3)
        elif p == 1:
            excluded.add(base * 4 + 2)
            excluded.add((base + 1) * 4 + 2)
        elif p == 2:
            excluded.add(base * 4 + 3)
            excluded.add((base + 1) * 4 + 1)
        else:
            excluded.add((base + 1) * 4)
            excluded.add((base + 2) * 4)

        for l in range(48):
            if l not in excluded:
                ppidx[h][l] = idx
                pp_hi.append(h)
                pp_lo.append(l)
                idx += 1

    return ppidx, pp_hi, pp_lo

PPIDX, _PP_HI, _PP_LO = _init_ppidx()


def _init_pp48_idx() -> List[List[int]]:
    pp48 = [[-1] * 48 for _ in range(48)]
    idx = 0
    for h in range(48):
        for l in range(h + 1, 48):
            pp48[h][l] = idx
            pp48[l][h] = idx
            idx += 1
    return pp48

PP48_IDX = _init_pp48_idx()


def _init_ppp48_idx() -> List[List[List[int]]]:
    ppp = [[[-1] * 48 for _ in range(48)] for _ in range(48)]
    idx = 0
    for x in range(48):
        for y in range(x + 1, 48):
            for z in range(y + 1, 48):
                a = ITOSQ[x]
                b = ITOSQ[y]
                c = ITOSQ[z]
                if (b & 4) != 0 or (c & 4) != 0:
                    continue
                i = a - 8
                j = b - 8
                k = c - 8
                if ppp[i][j][k] == -1:
                    for p0, p1, p2 in [(i, j, k), (i, k, j), (j, i, k),
                                        (j, k, i), (k, i, j), (k, j, i)]:
                        ppp[p0][p1][p2] = idx
                    idx += 1
    return ppp

PPP48_IDX = _init_ppp48_idx()


# ---------------------------------------------------------------------------
# Flip helpers
# ---------------------------------------------------------------------------

def _apply_flip(sq: int, flags: int) -> int:
    if flags & WE_FLAG:
        sq = flip_we(sq)
    if flags & NS_FLAG:
        sq = flip_ns(sq)
    if flags & NW_SE_FLAG:
        sq = flip_nw_se(sq)
    return sq


def pp_putanchorfirst(a: int, b: int) -> Tuple[int, int]:
    row_b = b & 56
    row_a = a & 56

    anchor = a
    loosen = b

    if row_b > row_a:
        anchor = b
        loosen = a
    elif row_b == row_a:
        col_a = a & 7
        inv_a = col_a ^ 7
        x = (1 << col_a) | (1 << inv_a)
        x &= (x - 1)
        hi_a = x

        col_b = b & 7
        inv_b = col_b ^ 7
        x = (1 << col_b) | (1 << inv_b)
        x &= (x - 1)
        hi_b = x

        if hi_b > hi_a:
            anchor = b
            loosen = a
        elif hi_b < hi_a:
            anchor = a
            loosen = b
        else:
            if a < b:
                anchor = a
                loosen = b
            else:
                anchor = b
                loosen = a

    return anchor, loosen


# ---------------------------------------------------------------------------
# Request & helper classes
# ---------------------------------------------------------------------------

class MissingTableError(KeyError):
    """Can not probe position because a required table is missing."""
    pass


class Request:
    __slots__ = (
        "white_squares", "white_types",
        "black_squares", "black_types",
        "side", "realside",
        "white_piece_squares", "black_piece_squares",
    )

    def __init__(
        self,
        white_squares: List[int],
        white_types: List[int],
        black_squares: List[int],
        black_types: List[int],
        side: int,
    ) -> None:
        self.white_squares = white_squares
        self.white_types = white_types
        self.black_squares = black_squares
        self.black_types = black_types
        self.side = side
        self.realside = side
        self.white_piece_squares: List[int] = []
        self.black_piece_squares: List[int] = []


class EndgameKey:
    __slots__ = ("maxindex", "slice_n", "pctoi")

    def __init__(self, maxindex: int, slice_n: int, pctoi: Any) -> None:
        self.maxindex = maxindex
        self.slice_n = slice_n
        self.pctoi = pctoi


class TableBlock:
    __slots__ = ("egkey", "side", "offset", "age")

    def __init__(self, egkey: str, side: int, offset: int, age: int) -> None:
        self.egkey = egkey
        self.side = side
        self.offset = offset
        self.age = age


class ZipInfo:
    __slots__ = ("extraoffset", "totalblocks", "blockindex")

    def __init__(self, extraoffset: int, totalblocks: int, blockindex: List[int]) -> None:
        self.extraoffset = extraoffset
        self.totalblocks = totalblocks
        self.blockindex = blockindex


# ---------------------------------------------------------------------------
# pctoindex — piece-only endgames (no pawns)
# ---------------------------------------------------------------------------
#
# Convention: white_piece_squares[0] = wk, [1:] = pieces.
#             black_piece_squares[0] = bk, [1:] = pieces.
#   Normalization: ft = FLIPT[bk][wk]; apply to all; ki = KKIDX[bk'][wk'].

def _normalize_piece(ws: List[int], bs: List[int]) -> Tuple[int, List[int], List[int]]:
    ft = FLIPT[bs[0]][ws[0]]

    if ft:
        ws = list(ws)
        bs = list(bs)
        for i in range(len(ws)):
            ws[i] = _apply_flip(ws[i], ft)
        for i in range(len(bs)):
            bs[i] = _apply_flip(bs[i], ft)

    ki = KKIDX[bs[0]][ws[0]]
    return ki, ws, bs


def idx_is_empty(v: int) -> bool:
    return v == -1


def kxk_pctoindex(req: Request) -> int:
    ws = req.white_piece_squares
    bs = req.black_piece_squares
    ki, ws, bs = _normalize_piece(ws, bs)
    if idx_is_empty(ki):
        return NOINDEX
    return ki * 64 + ws[1]


def kakb_pctoindex(req: Request) -> int:
    ws = req.white_piece_squares
    bs = req.black_piece_squares
    ki, ws, bs = _normalize_piece(ws, bs)
    if idx_is_empty(ki):
        return NOINDEX
    return ki * 64 * 64 + ws[1] * 64 + bs[1]


def kabk_pctoindex(req: Request) -> int:
    ws = req.white_piece_squares
    bs = req.black_piece_squares
    ki, ws, bs = _normalize_piece(ws, bs)
    if idx_is_empty(ki):
        return NOINDEX
    return ki * 64 * 64 + ws[1] * 64 + ws[2]


def kaak_pctoindex(req: Request) -> int:
    ws = req.white_piece_squares
    bs = req.black_piece_squares
    ki, ws, bs = _normalize_piece(ws, bs)
    if idx_is_empty(ki):
        return NOINDEX
    ai = AAIDX[ws[1]][ws[2]]
    if idx_is_empty(ai):
        return NOINDEX
    return ki * MAX_AAINDEX + ai


def kabck_pctoindex(req: Request) -> int:
    ws = req.white_piece_squares
    bs = req.black_piece_squares
    ki, ws, bs = _normalize_piece(ws, bs)
    if idx_is_empty(ki):
        return NOINDEX
    return ki * 64 * 64 * 64 + ws[1] * 64 * 64 + ws[2] * 64 + ws[3]


def kabkc_pctoindex(req: Request) -> int:
    ws = req.white_piece_squares
    bs = req.black_piece_squares
    ki, ws, bs = _normalize_piece(ws, bs)
    if idx_is_empty(ki):
        return NOINDEX
    return ki * 64 * 64 * 64 + ws[1] * 64 * 64 + ws[2] * 64 + bs[1]


def kaabk_pctoindex(req: Request) -> int:
    ws = req.white_piece_squares
    bs = req.black_piece_squares
    ki, ws, bs = _normalize_piece(ws, bs)
    if idx_is_empty(ki):
        return NOINDEX
    ai = AAIDX[ws[1]][ws[2]]
    if idx_is_empty(ai):
        return NOINDEX
    return ki * MAX_AAINDEX * 64 + ai * 64 + ws[3]


def kaakb_pctoindex(req: Request) -> int:
    ws = req.white_piece_squares
    bs = req.black_piece_squares
    ki, ws, bs = _normalize_piece(ws, bs)
    if idx_is_empty(ki):
        return NOINDEX
    ai = AAIDX[ws[1]][ws[2]]
    if idx_is_empty(ai):
        return NOINDEX
    return ki * MAX_AAINDEX * 64 + ai * 64 + bs[1]


def kabbk_pctoindex(req: Request) -> int:
    ws = req.white_piece_squares
    bs = req.black_piece_squares
    ki, ws, bs = _normalize_piece(ws, bs)
    if idx_is_empty(ki):
        return NOINDEX
    ai = AAIDX[ws[2]][ws[3]]
    if idx_is_empty(ai):
        return NOINDEX
    return ki * MAX_AAINDEX * 64 + ai * 64 + ws[1]


def kaaak_pctoindex(req: Request) -> int:
    ws = req.white_piece_squares
    bs = req.black_piece_squares
    ki, ws, bs = _normalize_piece(ws, bs)
    if idx_is_empty(ki):
        return NOINDEX
    a, b, c = sorted([ws[1], ws[2], ws[3]])
    idx = AAA_BASE[c] + b * (b - 1) // 2 + a
    return ki * MAX_AAAINDEX + idx


# ---------------------------------------------------------------------------
# pctoindex — pawn endgames
# ---------------------------------------------------------------------------

def _pawn_pslice(pawn: int) -> int:
    sq = pawn ^ 56
    sq -= 8
    return ((sq + (sq & 3)) >> 1)


def kpk_pctoindex(req: Request) -> int:
    wk = req.white_piece_squares[0]
    bk = req.black_piece_squares[0]
    pawn = req.white_piece_squares[1]

    if (pawn & 7) > 3:
        pawn = flip_we(pawn)
        wk = flip_we(wk)
        bk = flip_we(bk)

    pslice = _pawn_pslice(pawn)
    return pslice * 64 * 64 + wk * 64 + bk


def kpkp_pctoindex(req: Request) -> int:
    wk = req.white_piece_squares[0]
    bk = req.black_piece_squares[0]
    wpawn = req.white_piece_squares[1]
    bpawn = req.black_piece_squares[1]

    if (wpawn & 7) > 3:
        wk = flip_we(wk)
        bk = flip_we(bk)
        wpawn = flip_we(wpawn)
        bpawn = flip_we(bpawn)

    widx = _pawn_pslice(wpawn)
    bidx = bpawn - 8
    return widx * 48 * 64 * 64 + bidx * 64 * 64 + wk * 64 + bk


def kppk_pctoindex(req: Request) -> int:
    wk = req.white_piece_squares[0]
    bk = req.black_piece_squares[0]
    pawn_a = req.white_piece_squares[1]
    pawn_b = req.white_piece_squares[2]

    anchor, loosen = pp_putanchorfirst(pawn_a, pawn_b)

    if (anchor & 7) > 3:
        anchor = flip_we(anchor)
        loosen = flip_we(loosen)
        wk = flip_we(wk)
        bk = flip_we(bk)

    i = wsq_to_pidx24(anchor)
    j = wsq_to_pidx48(loosen)
    pp_slice = PPIDX[i][j]
    if pp_slice == -1:
        return NOINDEX
    return pp_slice * 64 * 64 + wk * 64 + bk


def kpppk_pctoindex(req: Request) -> int:
    wk = req.white_piece_squares[0]
    pawn_a = req.white_piece_squares[1]
    pawn_b = req.white_piece_squares[2]
    pawn_c = req.white_piece_squares[3]
    bk = req.black_piece_squares[0]

    i = pawn_a - 8
    j = pawn_b - 8
    k = pawn_c - 8

    ppp_slice = PPP48_IDX[i][j][k]

    if ppp_slice == -1:
        wk = flip_we(wk)
        pawn_a = flip_we(pawn_a)
        pawn_b = flip_we(pawn_b)
        pawn_c = flip_we(pawn_c)
        bk = flip_we(bk)
        i = pawn_a - 8
        j = pawn_b - 8
        k = pawn_c - 8
        ppp_slice = PPP48_IDX[i][j][k]

    if ppp_slice == -1:
        return NOINDEX
    return ppp_slice * 64 * 64 + wk * 64 + bk


def kakp_pctoindex(req: Request) -> int:
    wk = req.white_piece_squares[0]
    wa = req.white_piece_squares[1]
    bk = req.black_piece_squares[0]
    pawn = req.black_piece_squares[1]

    if (pawn & 7) > 3:
        pawn = flip_we(pawn)
        wk = flip_we(wk)
        bk = flip_we(bk)
        wa = flip_we(wa)

    pslice = map24_b(pawn)
    return pslice * 64 * 64 * 64 + wk * 64 * 64 + bk * 64 + wa


def kapk_pctoindex(req: Request) -> int:
    wk = req.white_piece_squares[0]
    wa = req.white_piece_squares[1]
    pawn = req.white_piece_squares[2]
    bk = req.black_piece_squares[0]

    if (pawn & 7) > 3:
        pawn = flip_we(pawn)
        wk = flip_we(wk)
        bk = flip_we(bk)
        wa = flip_we(wa)

    pslice = _pawn_pslice(pawn)
    return pslice * 64 * 64 * 64 + wk * 64 * 64 + bk * 64 + wa


def kabpk_pctoindex(req: Request) -> int:
    wk = req.white_piece_squares[0]
    wa = req.white_piece_squares[1]
    wb = req.white_piece_squares[2]
    pawn = req.white_piece_squares[3]
    bk = req.black_piece_squares[0]

    if (pawn & 7) > 3:
        pawn = flip_we(pawn)
        wk = flip_we(wk)
        bk = flip_we(bk)
        wa = flip_we(wa)
        wb = flip_we(wb)

    pslice = wsq_to_pidx24(pawn)
    return pslice * 64 * 64 * 64 * 64 + wk * 64 * 64 * 64 + bk * 64 * 64 + wa * 64 + wb


def kabkp_pctoindex(req: Request) -> int:
    wk = req.white_piece_squares[0]
    bk = req.black_piece_squares[0]
    pa = req.white_piece_squares[1]
    pb = req.white_piece_squares[2]
    bpawn = req.black_piece_squares[1]

    if (bpawn & 7) > 3:
        wk = flip_we(wk)
        bk = flip_we(bk)
        pa = flip_we(pa)
        pb = flip_we(pb)
        bpawn = flip_we(bpawn)

    bidx = _pawn_pslice(bpawn ^ 56)
    return bidx * 64 * 64 * 64 * 64 + wk * 64 * 64 * 64 + bk * 64 * 64 + pa * 64 + pb


def kaakp_pctoindex(req: Request) -> int:
    wk = req.white_piece_squares[0]
    wa = req.white_piece_squares[1]
    wa2 = req.white_piece_squares[2]
    bk = req.black_piece_squares[0]
    pawn = req.black_piece_squares[1]

    if (pawn & 7) > 3:
        pawn = flip_we(pawn)
        wk = flip_we(wk)
        bk = flip_we(bk)
        wa = flip_we(wa)
        wa2 = flip_we(wa2)

    pawn = flip_ns(pawn)
    pslice = wsq_to_pidx24(pawn)
    aa_combo = AAIDX[wa][wa2]
    if aa_combo == -1:
        return NOINDEX
    return pslice * 64 * 64 * MAX_AAINDEX + wk * 64 * MAX_AAINDEX + bk * MAX_AAINDEX + aa_combo


def kaapk_pctoindex(req: Request) -> int:
    wk = req.white_piece_squares[0]
    wa = req.white_piece_squares[1]
    wa2 = req.white_piece_squares[2]
    pawn = req.white_piece_squares[3]
    bk = req.black_piece_squares[0]

    if (pawn & 7) > 3:
        pawn = flip_we(pawn)
        wk = flip_we(wk)
        bk = flip_we(bk)
        wa = flip_we(wa)
        wa2 = flip_we(wa2)

    pslice = wsq_to_pidx24(pawn)
    aa_combo = AAIDX[wa][wa2]
    if aa_combo == -1:
        return NOINDEX
    return pslice * 64 * 64 * MAX_AAINDEX + wk * 64 * MAX_AAINDEX + bk * MAX_AAINDEX + aa_combo


def kapkb_pctoindex(req: Request) -> int:
    wk = req.white_piece_squares[0]
    wa = req.white_piece_squares[1]
    pawn = req.white_piece_squares[2]
    bk = req.black_piece_squares[0]
    ba = req.black_piece_squares[1]

    if (pawn & 7) > 3:
        pawn = flip_we(pawn)
        wk = flip_we(wk)
        bk = flip_we(bk)
        wa = flip_we(wa)
        ba = flip_we(ba)

    pslice = _pawn_pslice(pawn)
    return (pslice * 64 * 64 * 64 * 64
            + wk * 64 * 64 * 64
            + bk * 64 * 64
            + wa * 64 + ba)


def kapkp_pctoindex(req: Request) -> int:
    wk = req.white_piece_squares[0]
    bk = req.black_piece_squares[0]
    piece = req.white_piece_squares[1]
    wpawn = req.white_piece_squares[2]
    bpawn = req.black_piece_squares[1]

    if (wpawn & 7) > 3:
        wk = flip_we(wk)
        bk = flip_we(bk)
        piece = flip_we(piece)
        wpawn = flip_we(wpawn)
        bpawn = flip_we(bpawn)

    widx = _pawn_pslice(wpawn)
    bidx = bpawn - 8
    return (widx * 48 * 64 * 64 * 64
            + bidx * 64 * 64 * 64
            + wk * 64 * 64
            + bk * 64 + piece)


def kappk_pctoindex(req: Request) -> int:
    wk = req.white_piece_squares[0]
    wa = req.white_piece_squares[1]
    pawn_a = req.white_piece_squares[2]
    pawn_b = req.white_piece_squares[3]
    bk = req.black_piece_squares[0]

    anchor, loosen = pp_putanchorfirst(pawn_a, pawn_b)

    if (anchor & 7) > 3:
        anchor = flip_we(anchor)
        loosen = flip_we(loosen)
        wk = flip_we(wk)
        bk = flip_we(bk)
        wa = flip_we(wa)

    i = wsq_to_pidx24(anchor)
    j = wsq_to_pidx48(loosen)
    pp_slice = PPIDX[i][j]
    if pp_slice == -1:
        return NOINDEX
    return pp_slice * 64 * 64 * 64 + wk * 64 * 64 + bk * 64 + wa


def kppka_pctoindex(req: Request) -> int:
    wk = req.white_piece_squares[0]
    pawn_a = req.white_piece_squares[1]
    pawn_b = req.white_piece_squares[2]
    bk = req.black_piece_squares[0]
    ba = req.black_piece_squares[1]

    anchor, loosen = pp_putanchorfirst(pawn_a, pawn_b)

    if (anchor & 7) > 3:
        anchor = flip_we(anchor)
        loosen = flip_we(loosen)
        wk = flip_we(wk)
        bk = flip_we(bk)
        ba = flip_we(ba)

    i = wsq_to_pidx24(anchor)
    j = wsq_to_pidx48(loosen)
    pp_slice = PPIDX[i][j]
    if pp_slice == -1:
        return NOINDEX
    return pp_slice * 64 * 64 * 64 + wk * 64 * 64 + bk * 64 + ba


def kppkp_pctoindex(req: Request) -> int:
    wk = req.white_piece_squares[0]
    pawn_a = req.white_piece_squares[1]
    pawn_b = req.white_piece_squares[2]
    bk = req.black_piece_squares[0]
    pawn_c = req.black_piece_squares[1]

    if (pawn_c & 7) > 3:
        wk = flip_we(wk)
        pawn_a = flip_we(pawn_a)
        pawn_b = flip_we(pawn_b)
        bk = flip_we(bk)
        pawn_c = flip_we(pawn_c)

    i = (pawn_a ^ 63) - 8
    j = (pawn_b ^ 63) - 8
    k = map24_b(pawn_c)

    pp48_slice = PP48_IDX[i][j]
    if pp48_slice == -1:
        return NOINDEX

    return k * MAX_PP48_INDEX * 64 * 64 + pp48_slice * 64 * 64 + wk * 64 + bk


# ---------------------------------------------------------------------------
# DTM unpacking tables
# ---------------------------------------------------------------------------

_DTM_UNPACK_WTM = [
    iDRAW, iDRAW, iDRAW, iDRAW, iDRAW, iDRAW, iDRAW, iDRAW,
    iWMATE, iBMATE, iDRAW, iDRAW, iDRAW, iDRAW, iDRAW, iDRAW,
    iWMATE, iBMATE, iDRAW, iDRAW, iDRAW, iDRAW, iDRAW, iDRAW,
    iWMATE, iBMATE, iDRAW, iDRAW, iDRAW, iDRAW, iDRAW, iDRAW,
    iWMATE, iBMATE, iDRAW, iDRAW, iDRAW, iDRAW, iDRAW, iDRAW,
    iWMATE, iBMATE, iDRAW, iDRAW, iDRAW, iDRAW, iDRAW, iDRAW,
    iWMATE, iBMATE, iDRAW, iDRAW, iDRAW, iDRAW, iDRAW, iDRAW,
    iWMATE, iBMATE, iDRAW, iDRAW, iDRAW, iDRAW, iDRAW, iDRAW,
    iWMATE, iBMATE, iDRAW, iDRAW, iDRAW, iDRAW, iDRAW, iDRAW,
    iWMATE, iBMATE, iDRAW, iDRAW, iDRAW, iDRAW, iDRAW, iDRAW,
    iWMATE, iBMATE, iDRAW, iDRAW, iDRAW, iDRAW, iDRAW, iDRAW,
    iWMATE, iBMATE, iDRAW, iDRAW, iDRAW, iDRAW, iDRAW, iDRAW,
    iWMATE, iBMATE, iDRAW, iDRAW, iDRAW, iDRAW, iDRAW, iDRAW,
    iWMATE, iBMATE, iDRAW, iDRAW, iDRAW, iDRAW, iDRAW, iDRAW,
    iWMATE, iBMATE, iDRAW, iDRAW, iDRAW, iDRAW, iDRAW, iDRAW,
    iWMATE, iBMATE, iDRAW, iDRAW, iDRAW, iDRAW, iDRAW, iDRAW,
    iWMATE, iBMATE, iDRAW, iDRAW, iDRAW, iDRAW, iDRAW, iDRAW,
    iWMATE, iBMATE, iDRAW, iDRAW, iDRAW, iDRAW, iDRAW, iDRAW,
    iWMATE, iBMATE, iDRAW, iDRAW, iDRAW, iDRAW, iDRAW, iDRAW,
    iWMATE, iBMATE, iDRAW, iDRAW, iDRAW, iDRAW, iDRAW, iDRAW,
    iWMATE, iBMATE, iDRAW, iDRAW, iDRAW, iDRAW, iDRAW, iDRAW,
    iWMATE, iBMATE, iDRAW, iDRAW, iDRAW, iDRAW, iDRAW, iDRAW,
    iWMATE, iBMATE, iDRAW, iDRAW, iDRAW, iDRAW, iDRAW, iDRAW,
    iWMATE, iBMATE, iDRAW, iDRAW, iDRAW, iDRAW, iDRAW, iDRAW,
    iWMATE, iBMATE, iDRAW, iDRAW, iDRAW, iDRAW, iDRAW, iDRAW,
    iWMATE, iBMATE, iDRAW, iDRAW, iDRAW, iDRAW, iDRAW, iDRAW,
    iWMATE, iBMATE, iDRAW, iDRAW, iDRAW, iDRAW, iDRAW, iDRAW,
    iWMATE, iBMATE, iDRAW, iDRAW, iDRAW, iDRAW, iDRAW, iDRAW,
    iWMATE, iBMATE, iDRAW, iDRAW, iDRAW, iDRAW, iDRAW, iDRAW,
    iWMATE, iBMATE, iDRAW, iDRAW, iDRAW, iDRAW, iDRAW, iDRAW,
    iWMATE, iBMATE, iDRAW, iDRAW, iDRAW, iDRAW, iDRAW, iDRAW,
    iWMATE, iBMATE, iFORBID, iFORBID, iFORBID, iFORBID, iFORBID, iFORBID,
]

_DTM_UNPACK_BTM = [
    iDRAW, iDRAW, iDRAW, iDRAW, iDRAW, iDRAW, iDRAW, iDRAW,
    iBMATE, iWMATE, iDRAW, iDRAW, iDRAW, iDRAW, iDRAW, iDRAW,
    iBMATE, iWMATE, iDRAW, iDRAW, iDRAW, iDRAW, iDRAW, iDRAW,
    iBMATE, iWMATE, iDRAW, iDRAW, iDRAW, iDRAW, iDRAW, iDRAW,
    iBMATE, iWMATE, iDRAW, iDRAW, iDRAW, iDRAW, iDRAW, iDRAW,
    iBMATE, iWMATE, iDRAW, iDRAW, iDRAW, iDRAW, iDRAW, iDRAW,
    iBMATE, iWMATE, iDRAW, iDRAW, iDRAW, iDRAW, iDRAW, iDRAW,
    iBMATE, iWMATE, iDRAW, iDRAW, iDRAW, iDRAW, iDRAW, iDRAW,
    iBMATE, iWMATE, iDRAW, iDRAW, iDRAW, iDRAW, iDRAW, iDRAW,
    iBMATE, iWMATE, iDRAW, iDRAW, iDRAW, iDRAW, iDRAW, iDRAW,
    iBMATE, iWMATE, iDRAW, iDRAW, iDRAW, iDRAW, iDRAW, iDRAW,
    iBMATE, iWMATE, iDRAW, iDRAW, iDRAW, iDRAW, iDRAW, iDRAW,
    iBMATE, iWMATE, iDRAW, iDRAW, iDRAW, iDRAW, iDRAW, iDRAW,
    iBMATE, iWMATE, iDRAW, iDRAW, iDRAW, iDRAW, iDRAW, iDRAW,
    iBMATE, iWMATE, iDRAW, iDRAW, iDRAW, iDRAW, iDRAW, iDRAW,
    iBMATE, iWMATE, iDRAW, iDRAW, iDRAW, iDRAW, iDRAW, iDRAW,
    iBMATE, iWMATE, iDRAW, iDRAW, iDRAW, iDRAW, iDRAW, iDRAW,
    iBMATE, iWMATE, iDRAW, iDRAW, iDRAW, iDRAW, iDRAW, iDRAW,
    iBMATE, iWMATE, iDRAW, iDRAW, iDRAW, iDRAW, iDRAW, iDRAW,
    iBMATE, iWMATE, iDRAW, iDRAW, iDRAW, iDRAW, iDRAW, iDRAW,
    iBMATE, iWMATE, iDRAW, iDRAW, iDRAW, iDRAW, iDRAW, iDRAW,
    iBMATE, iWMATE, iDRAW, iDRAW, iDRAW, iDRAW, iDRAW, iDRAW,
    iBMATE, iWMATE, iDRAW, iDRAW, iDRAW, iDRAW, iDRAW, iDRAW,
    iBMATE, iWMATE, iDRAW, iDRAW, iDRAW, iDRAW, iDRAW, iDRAW,
    iBMATE, iWMATE, iDRAW, iDRAW, iDRAW, iDRAW, iDRAW, iDRAW,
    iBMATE, iWMATE, iDRAW, iDRAW, iDRAW, iDRAW, iDRAW, iDRAW,
    iBMATE, iWMATE, iDRAW, iDRAW, iDRAW, iDRAW, iDRAW, iDRAW,
    iBMATE, iWMATE, iDRAW, iDRAW, iDRAW, iDRAW, iDRAW, iDRAW,
    iBMATE, iWMATE, iDRAW, iDRAW, iDRAW, iDRAW, iDRAW, iDRAW,
    iBMATE, iWMATE, iDRAW, iDRAW, iDRAW, iDRAW, iDRAW, iDRAW,
    iBMATE, iWMATE, iDRAW, iDRAW, iDRAW, iDRAW, iDRAW, iDRAW,
    iBMATE, iWMATE, iFORBID, iFORBID, iFORBID, iFORBID, iFORBID, iFORBID,
]


def unpackdist(d: int) -> Tuple[int, int]:
    return d >> PLYSHIFT, d & ((1 << PLYSHIFT) - 1)


_DTM_BASES_WTM = (1017, 9, 2, 1010, 1033, 25, 18, 1026)
_DTM_BASES_BTM = (1018, 1, 10, 1009, 1034, 17, 26, 1025)


def dtm_unpack(stm: int, packed: int) -> int:
    plies = packed >> PLYSHIFT
    info = packed & ((1 << PLYSHIFT) - 1)
    if plies == 0:
        if info == iDRAW:
            return 0
        if info == iFORBID:
            return 3
    if stm and packed == 252:
        return 2033
    bases = _DTM_BASES_BTM if stm else _DTM_BASES_WTM
    return bases[info] + (plies << 5)


# ---------------------------------------------------------------------------
# EGKEY dictionary
# ---------------------------------------------------------------------------

def _build_egkeys() -> Dict[str, EndgameKey]:
    eg: Dict[str, EndgameKey] = {}

    def _add(name: str, maxindex: int, slices: int, fn: Any) -> None:
        eg[name] = EndgameKey(maxindex, slices, fn)

    k64 = 64 * 64
    k643 = 64 * 64 * 64
    k644 = 64 * 64 * 64 * 64
    ki = MAX_KKINDEX
    aa = MAX_AAINDEX
    aaa = MAX_AAAINDEX
    pp = MAX_PPINDEX
    pp48 = MAX_PP48_INDEX
    ppp48 = MAX_PPP48_INDEX

    for p in ("q", "r", "b", "n"):
        _add(f"k{p}k", ki * 64, 1, kxk_pctoindex)

    for p1, p2 in [("q","q"),("q","r"),("q","b"),("q","n"),("r","r"),("r","b"),("r","n"),("b","b"),("b","n"),("n","n")]:
        _add(f"k{p1}k{p2}", ki * k64, 1, kakb_pctoindex)

    for p in ("qq", "rr", "bb", "nn"):
        _add(f"k{p}k", ki * aa, 1, kaak_pctoindex)

    for p1, p2 in [("q","r"),("q","b"),("q","n"),("r","b"),("r","n"),("b","n")]:
        _add(f"k{p1}{p2}k", ki * k64, 1, kabk_pctoindex)

    _add("kpk", 24 * k64, 24, kpk_pctoindex)
    _add("kpkp", 24 * 48 * k64, 24 * 48, kpkp_pctoindex)

    for p in ("q", "r", "b", "n"):
        _add(f"k{p}kp", 24 * k643, 24, kakp_pctoindex)

    for p in ("q", "r", "b", "n"):
        _add(f"k{p}pk", 24 * k643, 24, kapk_pctoindex)

    for aa_str in ("qq", "rr", "bb", "nn"):
        for p in ("q", "r", "b", "n"):
            _add(f"k{aa_str}k{p}", ki * aa * 64, 1, kaakb_pctoindex)

    for p1, p2 in [("q","r"),("q","b"),("q","n"),("r","b"),("r","n"),("b","n")]:
        for p3 in ("q", "r", "b", "n"):
            _add(f"k{p1}{p2}k{p3}", ki * k643, 1, kabkc_pctoindex)

    for p in ("qqq", "rrr", "bbb", "nnn"):
        _add(f"k{p}k", ki * aaa, 1, kaaak_pctoindex)

    for aa_str, b in [("qq","r"),("qq","b"),("qq","n"),("rr","b"),("rr","n"),("bb","n")]:
        _add(f"k{aa_str}{b}k", ki * aa * 64, 1, kaabk_pctoindex)

    for p1, p2, p3 in [("q","r","b"),("q","r","n"),("q","b","n"),("r","b","n")]:
        _add(f"k{p1}{p2}{p3}k", ki * k643, 1, kabck_pctoindex)

    for a, bb in [("q","rr"),("q","bb"),("q","nn"),("r","bb"),("r","nn"),("b","nn")]:
        _add(f"k{a}{bb}k", ki * aa * 64, 1, kabbk_pctoindex)

    for aa_str in ("qq", "rr", "bb", "nn"):
        _add(f"k{aa_str}kp", 24 * k64 * aa, 24, kaakp_pctoindex)

    for aa_str in ("qq", "rr", "bb", "nn"):
        _add(f"k{aa_str}pk", 24 * k64 * aa, 24, kaapk_pctoindex)

    for p1, p2 in [("q","r"),("q","b"),("q","n"),("r","b"),("r","n"),("b","n")]:
        _add(f"k{p1}{p2}kp", 24 * k644, 24, kabkp_pctoindex)

    for p1, p2 in [("q","r"),("q","b"),("q","n"),("r","b"),("r","n"),("b","n")]:
        _add(f"k{p1}{p2}pk", 24 * k644, 24, kabpk_pctoindex)

    for p1 in ("q", "r", "b", "n"):
        for p2 in ("q", "r", "b", "n"):
            _add(f"k{p1}pk{p2}", 24 * k644, 24, kapkb_pctoindex)

    for p in ("q", "r", "b", "n"):
        _add(f"k{p}pkp", 24 * 48 * k643, 24 * 48, kapkp_pctoindex)

    _add("kppk", pp * k64, pp, kppk_pctoindex)

    for p in ("q", "r", "b", "n"):
        _add(f"kppk{p}", pp * 64 * k64, pp, kppka_pctoindex)

    _add("kppkp", 24 * pp48 * k64, 24 * pp48, kppkp_pctoindex)

    _add("kpppk", ppp48 * k64, ppp48, kpppk_pctoindex)

    for p in ("q", "r", "b", "n"):
        _add(f"k{p}ppk", pp * 64 * k64, pp, kappk_pctoindex)

    return eg

EGKEY: Dict[str, EndgameKey] = _build_egkeys()


# ---------------------------------------------------------------------------
# Board → Request conversion
# ---------------------------------------------------------------------------

def _board_to_request(board: _Board) -> Tuple[str, Request]:
    white_squares: List[int] = []
    white_types: List[int] = []
    black_squares: List[int] = []
    black_types: List[int] = []

    for sq in range(64):
        piece = board.piece_at(sq)
        if piece is None:
            continue
        if piece.color:
            white_squares.append(sq)
            white_types.append(piece.piece_type)
        else:
            black_squares.append(sq)
            black_types.append(piece.piece_type)

    _sort_key = lambda i, types=white_types: EGKEY_PIECE_ORDER.get(types[i], 9)
    order_w = sorted(range(len(white_squares)), key=lambda i: EGKEY_PIECE_ORDER.get(white_types[i], 9))
    white_squares = [white_squares[i] for i in order_w]
    white_types = [white_types[i] for i in order_w]

    order_b = sorted(range(len(black_squares)), key=lambda i: EGKEY_PIECE_ORDER.get(black_types[i], 9))
    black_squares = [black_squares[i] for i in order_b]
    black_types = [black_types[i] for i in order_b]

    w_chars = "".join(CHAR_FROM_PIECE[t] for t in white_types)
    b_chars = "".join(CHAR_FROM_PIECE[t] for t in black_types)
    egkey = w_chars.lower() + b_chars.lower()

    side = 0 if board.turn else 1
    req = Request(white_squares, white_types, black_squares, black_types, side)
    req.realside = side

    req.white_piece_squares = list(white_squares)
    req.black_piece_squares = list(black_squares)

    return egkey, req


def _egkey_mirror(egkey: str) -> str:
    parts = egkey.split("k")
    if len(parts) == 3:
        return "k" + parts[2] + "k" + parts[1]
    return egkey


def _request_mirror(req: Request) -> Request:
    new_req = Request(
        [flip_ns(s) for s in req.black_squares],
        list(req.black_types),
        [flip_ns(s) for s in req.white_squares],
        list(req.white_types),
        opp(req.side),
    )
    new_req.realside = req.realside
    new_req.white_piece_squares = [flip_ns(s) for s in req.black_piece_squares]
    new_req.black_piece_squares = [flip_ns(s) for s in req.white_piece_squares]
    return new_req


# ---------------------------------------------------------------------------
# PythonTablebase — pure-Python tablebase probing
# ---------------------------------------------------------------------------

class PythonTablebase:
    """Pure-Python Gaviota tablebase probing."""

    def __init__(self) -> None:
        self._paths: Dict[str, str] = {}
        self._zipinfo: Dict[str, ZipInfo] = {}
        self._block_cache: Dict[Tuple[str, int, int], bytes] = {}
        self._cache_age = 0
        self._max_cache = 32
        self._lock = threading.Lock()

    def add_directory(self, directory: str) -> None:
        for filename in os.listdir(directory):
            if filename.endswith(".gtb.cp4"):
                name = filename[:-8]
                path = os.path.join(directory, filename)
                self._paths[name] = path

    def close(self) -> None:
        self._paths.clear()
        self._zipinfo.clear()
        self._block_cache.clear()

    def __enter__(self) -> PythonTablebase:
        return self

    def __exit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[TracebackType],
    ) -> None:
        self.close()

    def _get_zipinfo(self, path: str) -> ZipInfo:
        if path in self._zipinfo:
            return self._zipinfo[path]

        with open(path, "rb") as f:
            f.seek(0, 2)
            filesize = f.tell()

            f.seek(0)
            header = f.read(4)
            n_blocks_bytes = f.read(4)
            reserved = f.read(4)

            n_blocks = struct.unpack("<I", n_blocks_bytes)[0]

            blockindex: List[int] = []
            for _ in range(n_blocks + 1):
                val = struct.unpack("<I", f.read(4))[0]
                blockindex.append(val)

            extraoffset = 12 + 4 * (n_blocks + 1)

        zi = ZipInfo(extraoffset, n_blocks, blockindex)
        self._zipinfo[path] = zi
        return zi

    def _read_block(self, path: str, block: int) -> bytes:
        zi = self._get_zipinfo(path)

        start = zi.extraoffset + zi.blockindex[block]
        end = zi.extraoffset + zi.blockindex[block + 1]
        comp_size = end - start

        with open(path, "rb") as f:
            f.seek(start)
            compressed = f.read(comp_size)

        return lzma.decompress(compressed)

    def _get_block_data(self, egkey_str: str, side: int, block: int) -> bytes:
        cache_key = (egkey_str, side, block)

        with self._lock:
            if cache_key in self._block_cache:
                return self._block_cache[cache_key]

        path = self._paths.get(egkey_str)
        if path is None:
            raise MissingTableError(egkey_str)

        n_sides = 2
        zi = self._get_zipinfo(path)
        actual_block = side * (zi.totalblocks // n_sides) + block

        data = self._read_block(path, actual_block)

        with self._lock:
            self._cache_age += 1
            if len(self._block_cache) >= self._max_cache:
                self._block_cache.clear()
            self._block_cache[cache_key] = data

        return data

    def _probe_index(self, egkey_str: str, side: int, index: int) -> int:
        block = index // ENTRIES_PER_BLOCK
        offset = index % ENTRIES_PER_BLOCK

        data = self._get_block_data(egkey_str, side, block)
        if offset >= len(data):
            return tb_FORBID
        return data[offset]

    def egtb_block_getnumber(self, req: Request, idx: int) -> int:
        return idx // ENTRIES_PER_BLOCK

    def egtb_block_getsize(self, req: Request, idx: int) -> int:
        egkey_str = self._req_to_egkey(req)
        if egkey_str not in EGKEY:
            return ENTRIES_PER_BLOCK
        ek = EGKEY[egkey_str]
        maxindex = ek.maxindex
        block = idx // ENTRIES_PER_BLOCK
        n_blocks = (maxindex + ENTRIES_PER_BLOCK - 1) // ENTRIES_PER_BLOCK
        if block >= n_blocks - 1:
            remainder = maxindex % ENTRIES_PER_BLOCK
            return remainder if remainder else ENTRIES_PER_BLOCK
        return ENTRIES_PER_BLOCK

    def egtb_block_getsize_zipped(self, egkey: str, block: int) -> int:
        path = self._paths.get(egkey)
        if path is None:
            raise MissingTableError(egkey)
        zi = self._get_zipinfo(path)
        return zi.blockindex[block + 1] - zi.blockindex[block]

    def egtb_block_park(self, egkey: str, block: int, stream: BinaryIO) -> int:
        path = self._paths.get(egkey)
        if path is None:
            raise MissingTableError(egkey)
        zi = self._get_zipinfo(path)
        offset = zi.extraoffset + zi.blockindex[block]
        stream.seek(offset)
        return offset

    def egtb_loadindexes(self, egkey: str, stream: BinaryIO) -> ZipInfo:
        stream.seek(0)
        header = stream.read(4)
        n_blocks_bytes = stream.read(4)
        reserved = stream.read(4)
        n_blocks = struct.unpack("<I", n_blocks_bytes)[0]
        blockindex: List[int] = []
        for _ in range(n_blocks + 1):
            val = struct.unpack("<I", stream.read(4))[0]
            blockindex.append(val)
        extraoffset = 12 + 4 * (n_blocks + 1)
        zi = ZipInfo(extraoffset, n_blocks, blockindex)
        self._zipinfo[self._paths.get(egkey, "")] = zi
        return zi

    def _req_to_egkey(self, req: Request) -> str:
        w_chars = "".join(CHAR_FROM_PIECE.get(t, "?") for t in req.white_types)
        b_chars = "".join(CHAR_FROM_PIECE.get(t, "?") for t in req.black_types)
        return w_chars.lower() + b_chars.lower()

    def probe_dtm(self, board: _Board) -> int:
        egkey_str, req = _board_to_request(board)

        mirrored = False
        if egkey_str not in EGKEY:
            egkey_str = _egkey_mirror(egkey_str)
            req = _request_mirror(req)
            mirrored = True

        if egkey_str not in EGKEY:
            raise MissingTableError(egkey_str)

        ek = EGKEY[egkey_str]

        if egkey_str not in self._paths:
            raise MissingTableError(egkey_str)

        index = ek.pctoi(req)
        if index == NOINDEX or index < 0:
            return 0

        side = req.side
        packed = self._probe_index(egkey_str, side, index)

        table = _DTM_UNPACK_BTM if side else _DTM_UNPACK_WTM
        info = table[packed]
        plies = packed >> PLYSHIFT

        if info == iWMATE:
            dtm = plies + 1
        elif info == iBMATE:
            dtm = -(plies + 1)
        else:
            dtm = 0

        if mirrored:
            dtm = -dtm

        return dtm

    def get_dtm(self, board: _Board, default: Optional[int] = None) -> Optional[int]:
        try:
            return self.probe_dtm(board)
        except MissingTableError:
            return default

    def probe_wdl(self, board: _Board) -> int:
        dtm = self.probe_dtm(board)
        if dtm > 0:
            return 2
        elif dtm < 0:
            return -2
        return 0

    def get_wdl(self, board: _Board, default: Optional[int] = None) -> Optional[int]:
        try:
            return self.probe_wdl(board)
        except MissingTableError:
            return default


# ---------------------------------------------------------------------------
# NativeTablebase — ctypes wrapper around libgtb
# ---------------------------------------------------------------------------

class NativeTablebase:
    """Gaviota tablebase probing via native libgtb."""

    def __init__(self, libgtb: ctypes.CDLL) -> None:
        self._libgtb = libgtb
        self._paths: List[str] = []
        self._setup_functions()

    def _setup_functions(self) -> None:
        lib = self._libgtb
        try:
            lib.tb_init.restype = ctypes.c_int
            lib.tb_done.restype = None
            lib.tb_probe_hard.restype = ctypes.c_int
            lib.tb_probe_hard.argtypes = [
                ctypes.c_uint, ctypes.c_uint, ctypes.c_uint,
                ctypes.POINTER(ctypes.c_uint), ctypes.POINTER(ctypes.c_uint),
                ctypes.POINTER(ctypes.c_uint), ctypes.POINTER(ctypes.c_uint),
                ctypes.POINTER(ctypes.c_uint), ctypes.POINTER(ctypes.c_uint),
            ]
        except AttributeError:
            pass

    def add_directory(self, directory: str) -> None:
        self._paths.append(directory)

    def _setup(self) -> None:
        lib = self._libgtb
        if not self._paths:
            return

        path_str = ";".join(self._paths)
        scheme = 4

        try:
            paths_ptr = ctypes.c_char_p(path_str.encode())
            lib.tbpaths_init()
            lib.tbpaths_add(paths_ptr)
            initinfo = lib.tb_init(ctypes.c_int(1), ctypes.c_int(scheme), ctypes.c_char_p(b""))
        except Exception:
            pass

    def close(self) -> None:
        try:
            self._libgtb.tb_done()
        except Exception:
            pass
        self._paths.clear()

    def __enter__(self) -> NativeTablebase:
        return self

    def __exit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[TracebackType],
    ) -> None:
        self.close()

    def _board_to_native(self, board: _Board) -> Tuple:
        stm = 0 if board.turn else 1
        ep = board.ep_square if board.ep_square is not None else 64

        wsqs: List[int] = []
        wpc: List[int] = []
        bsqs: List[int] = []
        bpc: List[int] = []

        piece_map = {KING: 1, QUEEN: 2, ROOK: 3, BISHOP: 4, KNIGHT: 5, PAWN: 6}

        for sq in range(64):
            piece = board.piece_at(sq)
            if piece is None:
                continue
            if piece.color:
                wsqs.append(sq)
                wpc.append(piece_map.get(piece.piece_type, 0))
            else:
                bsqs.append(sq)
                bpc.append(piece_map.get(piece.piece_type, 0))

        return stm, ep, wsqs, wpc, bsqs, bpc

    def probe_dtm(self, board: _Board) -> int:
        stm, ep, wsqs, wpc, bsqs, bpc = self._board_to_native(board)

        n_white = len(wsqs)
        n_black = len(bsqs)

        c_uint_arr_w = (ctypes.c_uint * (n_white + 1))
        c_uint_arr_b = (ctypes.c_uint * (n_black + 1))

        ws = c_uint_arr_w(*(wsqs + [64]))
        wp = c_uint_arr_w(*(wpc + [0]))
        bs = c_uint_arr_b(*(bsqs + [64]))
        bp = c_uint_arr_b(*(bpc + [0]))

        info = ctypes.c_uint(0)
        plies = ctypes.c_uint(0)

        result = self._libgtb.tb_probe_hard(
            ctypes.c_uint(stm), ctypes.c_uint(ep), ctypes.c_uint(0),
            ws, wp, bs, bp,
            ctypes.byref(info), ctypes.byref(plies),
        )

        info_val = info.value
        plies_val = plies.value

        if info_val == tb_WMATE:
            dtm = plies_val
        elif info_val == tb_BMATE:
            dtm = -int(plies_val)
        elif info_val == tb_DRAW:
            dtm = 0
        else:
            dtm = 0

        if not board.turn:
            dtm = -dtm

        return dtm

    def get_dtm(self, board: _Board, default: Optional[int] = None) -> Optional[int]:
        try:
            return self.probe_dtm(board)
        except Exception:
            return default

    def probe_wdl(self, board: _Board) -> int:
        dtm = self.probe_dtm(board)
        if dtm > 0:
            return 2
        elif dtm < 0:
            return -2
        return 0

    def get_wdl(self, board: _Board, default: Optional[int] = None) -> Optional[int]:
        try:
            return self.probe_wdl(board)
        except Exception:
            return default


# ---------------------------------------------------------------------------
# Factory functions
# ---------------------------------------------------------------------------

def open_tablebase(
    directory: str,
    *,
    libgtb: Optional[str] = None,
    LibraryLoader: Any = ctypes.cdll,
) -> Union[NativeTablebase, PythonTablebase]:
    """Open a Gaviota tablebase directory, trying native first."""
    try:
        return open_tablebase_native(directory, libgtb=libgtb, LibraryLoader=LibraryLoader)
    except (OSError, RuntimeError):
        tb = PythonTablebase()
        tb.add_directory(directory)
        return tb


def open_tablebase_native(
    directory: str,
    *,
    libgtb: Optional[str] = None,
    LibraryLoader: Any = ctypes.cdll,
) -> NativeTablebase:
    """Open a Gaviota tablebase directory using the native libgtb."""
    if libgtb is None:
        libpath = ctypes.util.find_library("gtb")
        if libpath is None:
            raise RuntimeError("libgtb not found")
        libgtb = LibraryLoader.LoadLibrary(libpath)

    tb = NativeTablebase(libgtb)
    tb.add_directory(directory)
    tb._setup()
    return tb


def setup_tablebase(directory: str) -> PythonTablebase:
    """Convenience alias for :func:`open_tablebase`."""
    return open_tablebase(directory)
