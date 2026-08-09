"""Row shapes and enumerations for the FISIS Open API.

Rows come back as plain dicts (``TypedDict``) so a caller can turn them into a
DataFrame in one line -- ``pd.DataFrame(rows)`` -- without this package importing
pandas at import time (the :class:`Table` converters import it lazily, only when
called). Each row type is ``total=False`` because the response parser
passes through *every* key the vendor sends, so a field new to the API still
arrives in the dict even before it is declared here. FISIS already keys its JSON
fields in lower snake_case (``finance_cd``, ``base_month``), so the field names
stay 1:1 with the FISIS documentation.

The enums carry the FISIS request codes: the value is the code that goes on the
wire, the member name is its meaning. A bare code string (``"H"``) is accepted
anywhere an enum is, because ``StrEnum`` members compare equal to their value.
"""

from __future__ import annotations

import importlib
from dataclasses import dataclass
from enum import StrEnum
from types import ModuleType
from typing import TYPE_CHECKING, TypedDict

if TYPE_CHECKING:
    import pandas
    import polars


class Sector(StrEnum):
    """A FISIS financial-sector (금융권역) code.

    Used both to list a sector's companies (the ``partDiv`` of
    :meth:`FISIS.list_companies`) and to browse its statistics catalog (the
    ``lrgDiv`` of :meth:`FISIS.list_statistics`). The value is the one-char code
    FISIS expects; the member name is its English meaning.
    """

    BANK                = "A"  # 은행
    FOREIGN_BANK        = "J"  # 외국은행지점
    LIFE                = "H"  # 생명보험
    NONLIFE             = "I"  # 손해보험
    SECURITIES          = "F"  # 증권
    FUTURES             = "W"  # 선물
    ASSET_MANAGEMENT    = "G"  # 자산운용
    INVESTMENT_ADVISORY = "X"  # 투자자문
    MERCHANT_BANK       = "D"  # 종합금융
    CARD                = "C"  # 신용카드
    LEASING             = "K"  # 리스
    CAPITAL             = "T"  # 할부금융 (여신전문 "캐피탈")
    NEW_TECH            = "N"  # 신기술금융
    SAVINGS_BANK        = "E"  # 상호저축은행
    CREDIT_UNION        = "O"  # 신용협동조합
    NONGHYUP            = "Q"  # 농업협동조합
    SUHYUP              = "P"  # 수산업협동조합
    FORESTRY_COOP       = "S"  # 산림조합
    REAL_ESTATE_TRUST   = "M"  # 부동산신탁
    HOLDING             = "L"  # 금융지주회사
    TRUST_COMMON        = "B"  # 신탁 (권역 공통)
    DERIVATIVES_COMMON  = "R"  # 파생상품 (권역 공통)


class Category(StrEnum):
    """A statistics-catalog category (통계표분류) -- the ``smlDiv`` of
    :meth:`FISIS.list_statistics`.

    These are the codes shared across sectors. A few sectors add codes of their
    own -- real-estate trust (부동산신탁) files its key-metrics tables under
    ``"E"`` -- so :meth:`FISIS.list_statistics` also passes a raw one-letter code
    outside this enum through verbatim.
    """

    GENERAL     = "A"  # 일반현황
    FINANCIAL   = "B"  # 재무현황
    KEY_METRICS = "C"  # 주요경영지표
    OPERATIONS  = "D"  # 영업현황
    PRESS       = "P"  # 보도자료


class Term(StrEnum):
    """How often a statistic is reported -- the ``term`` of :meth:`FISIS.fetch_data`.

    The window bounds (``start_month`` / ``end_month``) are always calendar months
    in YYYYMM regardless of the term; the term picks which base months carry an
    observation (annual: fiscal year-ends; quarterly: quarter-ends).
    """

    ANNUAL      = "Y"
    HALF_YEARLY = "H"
    QUARTERLY   = "Q"


class Lang(StrEnum):
    """The response language -- the ``lang`` sent with every FISIS request.

    The values are FISIS's own codes (Korean is ``"kr"``, not ISO 639-1 ``"ko"``);
    the member names follow the ISO spelling, so ``lang="ko"`` also resolves via
    the member name.
    """

    KO = "kr"
    EN = "en"


class CompanyRow(TypedDict, total=False):
    """One company from :meth:`FISIS.list_companies` (operation companySearch)."""

    finance_cd: str    # company code -- what fetch_data identifies a company by
    finance_nm: str    # company name
    finance_path: str  # classification path within the sector


class StatisticsRow(TypedDict, total=False):
    """One catalog entry from :meth:`FISIS.list_statistics` (statisticsListSearch)."""

    lrg_div_nm: str  # sector name
    sml_div_nm: str  # category name
    list_no: str     # statistic code -- what list_accounts / fetch_data take
    list_nm: str     # statistic name


class AccountRow(TypedDict, total=False):
    """One account item from :meth:`FISIS.list_accounts` (accountListSearch)."""

    list_no: str     # statistic code
    list_nm: str     # statistic name
    account_cd: str  # account code -- narrows fetch_data to one account
    account_nm: str  # account name


class DataRow(TypedDict, total=False):
    """One observation from :meth:`FISIS.fetch_data` (statisticsInfoSearch).

    Besides the five fixed keys below, each row carries **one additional key per
    value column the statistic defines**: FISIS ships the values in opaque
    columns (``a``, ``b``, ``c``, ``d``, ...) plus a legend naming them
    (the ``description`` list), and :meth:`FISIS.fetch_data` renames each value
    column to its human name (``column_nm``) -- so a balance statistic's row
    reads ``{"base_month": ..., "말잔": ..., "평잔": ...}``. Those keys vary by
    statistic and response language, so they cannot be declared here; their
    values pass through exactly as the vendor sends them.
    """

    base_month: str  # observation month, YYYYMM
    finance_cd: str
    finance_nm: str
    account_cd: str
    account_nm: str


@dataclass(frozen=True, slots=True)
class Column:
    """One value column of a statisticsInfoSearch table -- its id, name, and unit.

    ``column_id`` is the opaque key FISIS ships the value under (``"a"``,
    ``"b"``, ...); ``name`` is the human name it resolves to (the vendor
    ``column_nm``); ``unit`` is the column's unit (``"원"``, ``"%"``), ``None``
    when FISIS gave no unit or its unit list did not align with the columns.
    """

    column_id: str
    name: str
    unit: str | None


def _optional_import(module_name: str) -> ModuleType:
    """Import a conversion backend on demand, or raise a helpful ImportError.

    ``polars`` / ``pandas`` are not dependencies of this package -- its only one
    is httpx -- so :meth:`Table.to_polars` / :meth:`Table.to_pandas` import them
    here, at call time. Only the requested module being absent yields the install
    hint; if the backend is installed but one of *its own* dependencies is
    missing, that real cause is re-raised rather than mislabelled "not installed".
    """
    try:
        return importlib.import_module(module_name)
    except ModuleNotFoundError as err:
        if err.name != module_name:
            raise  # a dependency of the backend is missing -- surface the real cause
        raise ImportError(
            f"{module_name} is not installed; run `pip install {module_name}` to "
            f"use this method, or build a frame yourself from Table.rows."
        ) from err


@dataclass(slots=True)
class Table:
    """One statisticsInfoSearch result: resolved rows plus their column legend.

    ``rows`` are the value-column-resolved dicts, one per observation (see
    :class:`DataRow`) -- every value is a string, as FISIS sends it, so cast the
    numeric columns yourself; ``columns`` is the value-column legend, pairing each
    column's human name with its unit; ``date_of_settlement`` is the fiscal
    reporting date the values settle on (e.g. ``"12/31"``), ``None`` when absent.
    Returned by :meth:`FISIS.fetch_data`.

    ``rows`` is the plain records format ``pd.DataFrame(rows)`` /
    ``pl.DataFrame(rows)`` consume directly; :meth:`to_pandas` / :meth:`to_polars`
    are the same conversion (raising ``ImportError`` if that library is absent).
    """

    rows: list[DataRow]
    columns: tuple[Column, ...]
    date_of_settlement: str | None

    def to_polars(self) -> polars.DataFrame:
        """These rows as a ``polars.DataFrame`` (needs polars installed).

        Values arrive as strings, as FISIS sends them, so numeric columns land as
        strings -- cast the ones you need, e.g.
        ``df.with_columns(polars.col("말잔").cast(polars.Int64))``. A column's unit
        lives on :attr:`columns`, not on the frame. Raises ``ImportError`` (with an
        install hint) when polars is not installed.
        """
        return _optional_import("polars").DataFrame(self.rows)

    def to_pandas(self) -> pandas.DataFrame:
        """These rows as a ``pandas.DataFrame`` (needs pandas installed).

        Values arrive as strings (FISIS sends them so); cast the numeric columns
        you need. A column's unit lives on :attr:`columns`, not on the frame.
        Raises ``ImportError`` (with an install hint) when pandas is not installed.
        """
        return _optional_import("pandas").DataFrame(self.rows)
