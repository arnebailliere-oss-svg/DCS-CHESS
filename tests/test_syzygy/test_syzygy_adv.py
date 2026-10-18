"""SYZ-001 adversarial test suite — syzygy module differential testing.

Tests all utility functions, lookup tables, API surface, and edge cases
against python-chess. Since actual .rtbw/.rtbz files aren't available,
focuses on everything testable without tablebase data.
"""

from __future__ import annotations

import inspect
import itertools
from typing import List

import chess
import chess.syzygy
import pytest

from dcs_chess.syzygy import (
    TRIANGLE, INVTRIANGLE, DIAG, FLAP, INVFLAP, PTWIST, MTWIST,
    LOWER, KK_IDX, PP_IDX, PAWNIDX, PFACTOR, MULTIDX, MFACTOR,
    WDL_TO_MAP, PA_FLAGS, WDL_TO_DTZ, FILE_TO_FILE, PCHR,
    TBPIECES, TABLENAME_REGEX,
    MissingTableError,
    PairsData, PawnFileData, PawnFileDataDtz,
    Table, WdlTable, DtzTable, Tablebase,
    binom, subfactor, flipdiag, offdiag, test45,
    calc_key, recalc_key, normalize_tablename,
    is_tablename, tablenames, dependencies, all_dependencies,
    dtz_before_zeroing, open_tablebase,
)
from dcs_chess.core.board import Board


# =====================================================================
# 1. Lookup tables — exact match with python-chess
# =====================================================================

class TestLookupTables:
    """All 19 lookup tables must be element-identical to python-chess."""

    def test_triangle(self):
        assert TRIANGLE == chess.syzygy.TRIANGLE

    def test_invtriangle(self):
        assert INVTRIANGLE == chess.syzygy.INVTRIANGLE

    def test_diag(self):
        assert DIAG == chess.syzygy.DIAG

    def test_flap(self):
        assert FLAP == chess.syzygy.FLAP

    def test_invflap(self):
        assert INVFLAP == chess.syzygy.INVFLAP

    def test_ptwist(self):
        assert PTWIST == chess.syzygy.PTWIST

    def test_mtwist(self):
        assert MTWIST == chess.syzygy.MTWIST

    def test_lower(self):
        assert LOWER == chess.syzygy.LOWER

    def test_kk_idx(self):
        assert KK_IDX == chess.syzygy.KK_IDX

    def test_pp_idx(self):
        assert PP_IDX == chess.syzygy.PP_IDX

    def test_pawnidx(self):
        assert PAWNIDX == chess.syzygy.PAWNIDX

    def test_pfactor(self):
        assert PFACTOR == chess.syzygy.PFACTOR

    def test_multidx(self):
        assert MULTIDX == chess.syzygy.MULTIDX

    def test_mfactor(self):
        assert MFACTOR == chess.syzygy.MFACTOR

    def test_wdl_to_map(self):
        assert WDL_TO_MAP == chess.syzygy.WDL_TO_MAP

    def test_pa_flags(self):
        assert PA_FLAGS == chess.syzygy.PA_FLAGS

    def test_wdl_to_dtz(self):
        assert WDL_TO_DTZ == chess.syzygy.WDL_TO_DTZ

    def test_file_to_file(self):
        assert FILE_TO_FILE == chess.syzygy.FILE_TO_FILE

    def test_pchr(self):
        assert PCHR == chess.syzygy.PCHR

    def test_tbpieces(self):
        assert TBPIECES == chess.syzygy.TBPIECES


# =====================================================================
# 2. binom — binomial coefficient
# =====================================================================

class TestBinom:
    CASES = [
        (0, 0), (1, 0), (1, 1), (2, 0), (2, 1), (2, 2),
        (5, 2), (5, 3), (10, 3), (10, 5),
        (64, 2), (64, 3), (64, 4),
        (0, 1), (3, 5), (1, 10),
        (62, 2), (60, 3), (58, 4),
    ]

    @pytest.mark.parametrize("x,y", CASES)
    def test_binom(self, x, y):
        assert binom(x, y) == chess.syzygy.binom(x, y), f"binom({x},{y})"


# =====================================================================
# 3. subfactor
# =====================================================================

class TestSubfactor:
    CASES = [
        (0, 64), (1, 64), (2, 64), (3, 62), (4, 60),
        (0, 1), (1, 1), (1, 10), (2, 10), (3, 10),
        (5, 50), (2, 48), (0, 0),
    ]

    @pytest.mark.parametrize("k,n", CASES)
    def test_subfactor(self, k, n):
        assert subfactor(k, n) == chess.syzygy.subfactor(k, n), f"subfactor({k},{n})"


# =====================================================================
# 4. flipdiag / offdiag / test45
# =====================================================================

class TestSquareUtilities:
    def test_flipdiag_all_squares(self):
        for sq in range(64):
            assert flipdiag(sq) == chess.syzygy.flipdiag(sq), f"flipdiag({sq})"

    def test_flipdiag_involution(self):
        for sq in range(64):
            assert flipdiag(flipdiag(sq)) == sq

    def test_offdiag_all_squares(self):
        for sq in range(64):
            assert offdiag(sq) == chess.syzygy.offdiag(sq), f"offdiag({sq})"

    def test_offdiag_diagonal_is_zero(self):
        for i in range(8):
            assert offdiag(i * 9) == 0

    def test_test45_all_squares(self):
        for sq in range(64):
            assert test45(sq) == chess.syzygy.test45(sq), f"test45({sq})"


# =====================================================================
# 5. calc_key — board → table key
# =====================================================================

class TestCalcKey:
    FENS = [
        "8/8/8/8/8/8/8/KQk5 w - - 0 1",
        "8/8/8/8/8/8/8/KRk5 w - - 0 1",
        "8/8/8/8/8/8/8/KBNk4 w - - 0 1",
        "4k3/8/8/8/8/8/P7/4K3 w - - 0 1",
        "4k3/8/8/8/8/8/8/4KQR1 w - - 0 1",
        "4k3/p7/8/8/8/8/P7/4K3 w - - 0 1",
        chess.STARTING_FEN,
        "8/8/8/8/8/8/8/Kk6 w - - 0 1",
        "4k3/8/8/8/8/8/8/4K2R w - - 0 1",
        "8/8/4k3/8/8/8/8/4K2Q w - - 0 1",
    ]

    @pytest.mark.parametrize("fen", FENS)
    def test_calc_key(self, fen):
        ours = Board(fen)
        ref = chess.Board(fen)
        assert calc_key(ours) == chess.syzygy.calc_key(ref), f"calc_key({fen})"

    @pytest.mark.parametrize("fen", FENS)
    def test_calc_key_mirror(self, fen):
        ours = Board(fen)
        ref = chess.Board(fen)
        assert calc_key(ours, mirror=True) == chess.syzygy.calc_key(ref, mirror=True), \
            f"calc_key({fen}, mirror=True)"

    def test_calc_key_symmetry(self):
        """For symmetric positions, key == mirrored key."""
        b = Board("4k3/8/8/8/8/8/8/4K3 w - - 0 1")
        assert calc_key(b) == calc_key(b, mirror=True)


# =====================================================================
# 6. recalc_key
# =====================================================================

class TestRecalcKey:
    PIECE_LISTS: List[List[int]] = [
        [1, 1],
        [1, 2, 1],
        [1, 5, 1],
        [1, 2, 3, 4, 5, 6, 1],
        [1, 1, 1],
        [1, 2, 3, 1, 2, 3],
    ]

    @pytest.mark.parametrize("pieces", PIECE_LISTS)
    def test_recalc_key(self, pieces):
        assert recalc_key(pieces) == chess.syzygy.recalc_key(pieces), \
            f"recalc_key({pieces})"

    @pytest.mark.parametrize("pieces", PIECE_LISTS)
    def test_recalc_key_mirror(self, pieces):
        assert recalc_key(pieces, mirror=True) == chess.syzygy.recalc_key(pieces, mirror=True), \
            f"recalc_key({pieces}, mirror=True)"


# =====================================================================
# 7. normalize_tablename
# =====================================================================

class TestNormalizeTablename:
    NAMES = [
        "KQvK", "KvKQ", "KRPvKR", "KRvKRP",
        "KQRBNPvKQRBNP", "KBBvKN", "KNvKBB",
        "KPPvKP", "KPvKPP", "KQvKR", "KRvKQ",
        "KRRvKR", "KRvKRR",
    ]

    @pytest.mark.parametrize("name", NAMES)
    def test_normalize(self, name):
        assert normalize_tablename(name) == chess.syzygy.normalize_tablename(name), \
            f"normalize_tablename({name})"

    @pytest.mark.parametrize("name", NAMES)
    def test_normalize_mirror(self, name):
        assert normalize_tablename(name, mirror=True) == chess.syzygy.normalize_tablename(name, mirror=True), \
            f"normalize_tablename({name}, mirror=True)"

    def test_normalize_idempotent(self):
        for name in self.NAMES:
            n = normalize_tablename(name)
            assert normalize_tablename(n) == n


# =====================================================================
# 8. is_tablename
# =====================================================================

class TestIsTablename:
    VALID = ["KQvK", "KRvK", "KBvK", "KNvK", "KPvK", "KQvKQ",
             "KRPvKR", "KBBvKN", "KQRBNPvK", "KPPPPvKP"]
    INVALID = ["hello", "KvK", "", "QvK", "KQv", "vKQ",
               "KQRBNPPPvKQRBNPPP", "k v k"]

    @pytest.mark.parametrize("name", VALID)
    def test_valid(self, name):
        assert is_tablename(name) == chess.syzygy.is_tablename(name), \
            f"is_tablename({name})"

    @pytest.mark.parametrize("name", INVALID)
    def test_invalid(self, name):
        assert is_tablename(name) == chess.syzygy.is_tablename(name), \
            f"is_tablename({name})"

    def test_one_king_false(self):
        assert is_tablename("KvK", one_king=False) == chess.syzygy.is_tablename("KvK", one_king=False)

    def test_piece_count_none(self):
        name = "KQRBNPPvKQRBNPP"
        assert is_tablename(name, piece_count=None) == chess.syzygy.is_tablename(name, piece_count=None)

    def test_normalized_false(self):
        assert is_tablename("KvKQ", normalized=False) == chess.syzygy.is_tablename("KvKQ", normalized=False)
        assert is_tablename("KQvK", normalized=False) == chess.syzygy.is_tablename("KQvK", normalized=False)


# =====================================================================
# 9. tablenames
# =====================================================================

class TestTablenames:
    @pytest.mark.parametrize("piece_count", [3, 4, 5, 6])
    def test_tablenames_count(self, piece_count):
        ours = sorted(tablenames(piece_count=piece_count))
        ref = sorted(chess.syzygy.tablenames(piece_count=piece_count))
        assert ours == ref, f"tablenames(piece_count={piece_count}) differs"

    def test_tablenames_one_king_false(self):
        ours = sorted(tablenames(one_king=False, piece_count=4))
        ref = sorted(chess.syzygy.tablenames(one_king=False, piece_count=4))
        assert ours == ref

    def test_all_normalized(self):
        for name in tablenames(piece_count=6):
            assert normalize_tablename(name) == name

    def test_no_duplicates(self):
        names = list(tablenames(piece_count=6))
        assert len(names) == len(set(names))


# =====================================================================
# 10. dependencies / all_dependencies
# =====================================================================

class TestDependencies:
    TARGETS = ["KQvK", "KRvK", "KQRvKR", "KRPvKR", "KBBvKN", "KQvKR"]

    @pytest.mark.parametrize("target", TARGETS)
    def test_dependencies(self, target):
        ours = sorted(dependencies(target))
        ref = sorted(chess.syzygy.dependencies(target))
        assert ours == ref, f"dependencies({target})"

    def test_all_dependencies(self):
        targets = ["KQRvKR", "KRPvKR"]
        ours = sorted(all_dependencies(targets))
        ref = sorted(chess.syzygy.all_dependencies(targets))
        assert ours == ref

    def test_simple_table_no_deps(self):
        deps = list(dependencies("KQvK"))
        ref_deps = list(chess.syzygy.dependencies("KQvK"))
        assert deps == ref_deps

    def test_dependencies_one_king_false(self):
        ours = sorted(dependencies("KQvK", one_king=False))
        ref = sorted(chess.syzygy.dependencies("KQvK", one_king=False))
        assert ours == ref


# =====================================================================
# 11. dtz_before_zeroing
# =====================================================================

class TestDtzBeforeZeroing:
    @pytest.mark.parametrize("wdl", [-2, -1, 0, 1, 2])
    def test_dtz_before_zeroing(self, wdl):
        assert dtz_before_zeroing(wdl) == chess.syzygy.dtz_before_zeroing(wdl), \
            f"dtz_before_zeroing({wdl})"


# =====================================================================
# 12. MissingTableError
# =====================================================================

class TestMissingTableError:
    def test_is_key_error(self):
        assert issubclass(MissingTableError, KeyError)
        assert MissingTableError.__bases__ == chess.syzygy.MissingTableError.__bases__

    def test_raise_catch_key_error(self):
        with pytest.raises(KeyError):
            raise MissingTableError("test")

    def test_message(self):
        err = MissingTableError("missing KQvK")
        assert "missing KQvK" in str(err)


# =====================================================================
# 13. Tablebase API surface
# =====================================================================

class TestTablebaseAPI:
    def test_init_signature(self):
        ref_sig = inspect.signature(chess.syzygy.Tablebase.__init__)
        our_sig = inspect.signature(Tablebase.__init__)
        assert list(our_sig.parameters.keys()) == list(ref_sig.parameters.keys())

    def test_public_methods(self):
        ref_methods = {m for m in dir(chess.syzygy.Tablebase)
                       if not m.startswith("_") and callable(getattr(chess.syzygy.Tablebase, m))}
        our_methods = {m for m in dir(Tablebase)
                       if not m.startswith("_") and callable(getattr(Tablebase, m))}
        assert our_methods >= ref_methods, f"Missing: {ref_methods - our_methods}"

    def test_method_signatures(self):
        methods = ["add_directory", "add_file", "probe_wdl", "probe_dtz",
                    "get_wdl", "get_dtz", "probe_wdl_table", "probe_dtz_table",
                    "probe_dtz_no_ep", "probe_ab", "sprobe_ab", "sprobe_capts",
                    "close"]
        for m in methods:
            ref_sig = inspect.signature(getattr(chess.syzygy.Tablebase, m))
            our_sig = inspect.signature(getattr(Tablebase, m))
            ref_params = list(ref_sig.parameters.keys())
            our_params = list(our_sig.parameters.keys())
            assert our_params == ref_params, f"{m}: {our_params} != {ref_params}"

    def test_context_manager(self):
        tb = Tablebase()
        with tb:
            pass

    def test_close_idempotent(self):
        tb = Tablebase()
        tb.close()
        tb.close()

    def test_add_nonexistent_directory(self):
        """BUG-3: python-chess raises FileNotFoundError for nonexistent directories."""
        tb = Tablebase()
        ref = chess.syzygy.Tablebase()
        try:
            ref_result = ref.add_directory("/nonexistent/path")
            ref_raised = False
        except (FileNotFoundError, OSError):
            ref_raised = True
        try:
            our_result = tb.add_directory("/nonexistent/path")
            our_raised = False
        except (FileNotFoundError, OSError):
            our_raised = True
        assert our_raised == ref_raised, \
            f"Behavior mismatch: ours {'raised' if our_raised else 'returned ' + str(our_result)}, " \
            f"ref {'raised' if ref_raised else 'returned ' + str(ref_result)}"
        tb.close()
        ref.close()

    def test_default_max_fds(self):
        tb = Tablebase()
        ref = chess.syzygy.Tablebase()
        assert tb.max_fds == ref.max_fds
        tb.close()
        ref.close()

    def test_empty_wdl_dtz_dicts(self):
        tb = Tablebase()
        assert isinstance(tb.wdl, dict) and len(tb.wdl) == 0
        assert isinstance(tb.dtz, dict) and len(tb.dtz) == 0
        tb.close()


# =====================================================================
# 14. open_tablebase
# =====================================================================

class TestOpenTablebase:
    def test_signature(self):
        ref_sig = inspect.signature(chess.syzygy.open_tablebase)
        our_sig = inspect.signature(open_tablebase)
        assert list(our_sig.parameters.keys()) == list(ref_sig.parameters.keys())

    def test_nonexistent_directory(self):
        with pytest.raises(FileNotFoundError):
            open_tablebase("/nonexistent/path")

    def test_returns_tablebase(self):
        with pytest.raises(FileNotFoundError):
            open_tablebase("/nonexistent")


# =====================================================================
# 15. Table/WdlTable/DtzTable class hierarchy
# =====================================================================

class TestTableClasses:
    def test_wdl_table_is_table(self):
        assert issubclass(WdlTable, Table)
        assert issubclass(chess.syzygy.WdlTable, chess.syzygy.Table)

    def test_dtz_table_is_table(self):
        assert issubclass(DtzTable, Table)
        assert issubclass(chess.syzygy.DtzTable, chess.syzygy.Table)

    def test_pairs_data_exists(self):
        pd = PairsData()
        ref = chess.syzygy.PairsData()
        our_attrs = {a for a in dir(pd) if not a.startswith("_")}
        ref_attrs = {a for a in dir(ref) if not a.startswith("_")}
        assert our_attrs >= ref_attrs, f"PairsData missing: {ref_attrs - our_attrs}"

    def test_pawn_file_data_exists(self):
        pd = PawnFileData()
        ref = chess.syzygy.PawnFileData()
        our_attrs = {a for a in dir(pd) if not a.startswith("_")}
        ref_attrs = {a for a in dir(ref) if not a.startswith("_")}
        assert our_attrs >= ref_attrs, f"PawnFileData missing: {ref_attrs - our_attrs}"

    def test_pawn_file_data_dtz_exists(self):
        pd = PawnFileDataDtz()
        ref = chess.syzygy.PawnFileDataDtz()
        our_attrs = {a for a in dir(pd) if not a.startswith("_")}
        ref_attrs = {a for a in dir(ref) if not a.startswith("_")}
        assert our_attrs >= ref_attrs, f"PawnFileDataDtz missing: {ref_attrs - our_attrs}"

    def test_wdl_magic_constants(self):
        assert WdlTable.WDL_MAGIC == b"\x71\xe8\x23\x5d"
        assert WdlTable.WDL_MAGIC_PAWNLESS == b"\x71\xe8\x23\x5d"

    def test_dtz_magic_constants(self):
        assert DtzTable.DTZ_MAGIC == b"\xd7\x66\x0c\xa5"
        assert DtzTable.DTZ_MAGIC_PAWNLESS == b"\xd7\x66\x0c\xa5"


# =====================================================================
# 16. TABLENAME_REGEX
# =====================================================================

class TestTablenameRegex:
    VALID = ["KQvK", "KRvK", "KPvK", "KQRBNPvKQRBNP", "KPPPPPPPPvK"]
    INVALID = ["", "KvK", "hello", "K v K", "KQ-vK", "kqvk", "123v456"]

    @pytest.mark.parametrize("name", VALID)
    def test_valid(self, name):
        ours = bool(TABLENAME_REGEX.match(name))
        ref = bool(chess.syzygy.TABLENAME_REGEX.match(name))
        assert ours == ref, f"TABLENAME_REGEX.match({name!r})"

    @pytest.mark.parametrize("name", INVALID)
    def test_invalid(self, name):
        ours = bool(TABLENAME_REGEX.match(name))
        ref = bool(chess.syzygy.TABLENAME_REGEX.match(name))
        assert ours == ref, f"TABLENAME_REGEX.match({name!r})"


# =====================================================================
# 17. Module exports — completeness check
# =====================================================================

class TestModuleExports:
    def test_all_public_names(self):
        import dcs_chess.syzygy as ours
        PUBLIC = {
            "TRIANGLE", "INVTRIANGLE", "DIAG", "FLAP", "INVFLAP",
            "PTWIST", "MTWIST", "LOWER", "KK_IDX", "PP_IDX",
            "PAWNIDX", "PFACTOR", "MULTIDX", "MFACTOR",
            "WDL_TO_MAP", "PA_FLAGS", "WDL_TO_DTZ", "FILE_TO_FILE", "PCHR",
            "TBPIECES", "TABLENAME_REGEX",
            "MissingTableError",
            "PairsData", "PawnFileData", "PawnFileDataDtz",
            "Table", "WdlTable", "DtzTable", "Tablebase",
            "binom", "subfactor", "flipdiag", "offdiag", "test45",
            "calc_key", "recalc_key", "normalize_tablename",
            "is_tablename", "tablenames", "dependencies", "all_dependencies",
            "dtz_before_zeroing", "open_tablebase",
        }
        for name in PUBLIC:
            assert hasattr(ours, name), f"Missing export: {name}"
            assert hasattr(chess.syzygy, name), f"Not in ref: {name}"


# =====================================================================
# 18. Edge cases and boundary probes
# =====================================================================

class TestEdgeCases:
    def test_probe_wdl_missing_table(self):
        tb = Tablebase()
        board = Board("8/8/8/8/8/8/8/KQk5 w - - 0 1")
        with pytest.raises(MissingTableError):
            tb.probe_wdl(board)
        tb.close()

    def test_probe_dtz_missing_table(self):
        tb = Tablebase()
        board = Board("8/8/8/8/8/8/8/KQk5 w - - 0 1")
        with pytest.raises(MissingTableError):
            tb.probe_dtz(board)
        tb.close()

    def test_get_wdl_default(self):
        tb = Tablebase()
        board = Board("8/8/8/8/8/8/8/KQk5 w - - 0 1")
        assert tb.get_wdl(board) is None
        assert tb.get_wdl(board, default=-99) == -99
        tb.close()

    def test_get_dtz_default(self):
        tb = Tablebase()
        board = Board("8/8/8/8/8/8/8/KQk5 w - - 0 1")
        assert tb.get_dtz(board) is None
        assert tb.get_dtz(board, default=-99) == -99
        tb.close()

    def test_probe_wdl_too_many_pieces(self):
        """Position with >7 pieces (no castling) must raise MissingTableError."""
        tb = Tablebase()
        board = Board("4k3/pppppppp/8/8/8/8/PPPPPPPP/4K3 w - - 0 1")
        with pytest.raises(MissingTableError):
            tb.probe_wdl(board)
        tb.close()

    def test_tablenames_3_piece(self):
        names = list(tablenames(piece_count=3))
        ref = list(chess.syzygy.tablenames(piece_count=3))
        assert sorted(names) == sorted(ref)

    def test_normalize_already_normalized(self):
        for name in tablenames(piece_count=5):
            assert normalize_tablename(name) == name


# =====================================================================
# 19. Struct format constants
# =====================================================================

class TestStructConstants:
    def test_uint16(self):
        from dcs_chess.syzygy import UINT16
        assert UINT16.size == 2

    def test_uint32(self):
        from dcs_chess.syzygy import UINT32
        assert UINT32.size == 4

    def test_uint32_be(self):
        from dcs_chess.syzygy import UINT32_BE
        assert UINT32_BE.size == 4

    def test_uint64_be(self):
        from dcs_chess.syzygy import UINT64_BE
        assert UINT64_BE.size == 8


# =====================================================================
# 20. Trivial positions resolved without tables (KvK family)
# =====================================================================

class TestTrivialPositions:
    """Positions the library answers without any loaded tables."""

    KVK_FENS = [
        "8/8/8/8/8/8/4k3/4K3 w - - 0 1",
        "8/8/8/8/8/8/4k3/4K3 b - - 0 1",
        "K7/8/8/8/8/8/8/7k w - - 0 1",
        "K7/8/8/8/8/8/8/7k b - - 0 1",
        "3k4/8/8/8/8/8/8/4K3 w - - 0 1",
        "8/8/8/3k4/4K3/8/8/8 w - - 0 50",
        "8/8/8/3k4/4K3/8/8/8 b - - 0 50",
    ]

    @pytest.mark.parametrize("fen", KVK_FENS)
    def test_probe_wdl_kvk(self, fen):
        tb = Tablebase()
        ref_tb = chess.syzygy.Tablebase()
        b = Board(fen)
        r = chess.Board(fen)
        assert tb.probe_wdl(b) == ref_tb.probe_wdl(r), f"probe_wdl mismatch: {fen}"
        tb.close()
        ref_tb.close()

    @pytest.mark.parametrize("fen", KVK_FENS)
    def test_probe_dtz_kvk(self, fen):
        tb = Tablebase()
        ref_tb = chess.syzygy.Tablebase()
        b = Board(fen)
        r = chess.Board(fen)
        assert tb.probe_dtz(b) == ref_tb.probe_dtz(r), f"probe_dtz mismatch: {fen}"
        tb.close()
        ref_tb.close()

    @pytest.mark.parametrize("fen", KVK_FENS)
    def test_get_wdl_kvk(self, fen):
        tb = Tablebase()
        ref_tb = chess.syzygy.Tablebase()
        b = Board(fen)
        r = chess.Board(fen)
        assert tb.get_wdl(b) == ref_tb.get_wdl(r), f"get_wdl mismatch: {fen}"
        tb.close()
        ref_tb.close()

    @pytest.mark.parametrize("fen", KVK_FENS)
    def test_get_dtz_kvk(self, fen):
        tb = Tablebase()
        ref_tb = chess.syzygy.Tablebase()
        b = Board(fen)
        r = chess.Board(fen)
        assert tb.get_dtz(b) == ref_tb.get_dtz(r), f"get_dtz mismatch: {fen}"
        tb.close()
        ref_tb.close()

    NON_KVK_FENS = [
        "8/8/8/8/8/8/8/KQk5 w - - 0 1",
        "8/8/8/8/8/8/4k3/4K2R w - - 0 1",
        "8/8/8/8/8/4P3/4k3/4K3 w - - 0 1",
        "8/8/8/8/8/8/4k3/3NK3 w - - 0 1",
    ]

    @pytest.mark.parametrize("fen", NON_KVK_FENS)
    def test_non_kvk_still_raises(self, fen):
        """Non-KvK positions must still raise MissingTableError without tables."""
        tb = Tablebase()
        ref_tb = chess.syzygy.Tablebase()
        b = Board(fen)
        r = chess.Board(fen)
        with pytest.raises(MissingTableError):
            tb.probe_wdl(b)
        with pytest.raises(chess.syzygy.MissingTableError):
            ref_tb.probe_wdl(r)
        tb.close()
        ref_tb.close()
