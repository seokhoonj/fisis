"""The ``FISIS`` client -- the one public handle to the FISIS Open API.

One object holds the API key and a pooled HTTP connection; its methods mirror the
FISIS operations one-to-one, each taking named arguments. The catalog methods
(``list_*``) return a list of dict rows; :meth:`FISIS.fetch_data` returns a
:class:`~fisis.types.Data`. Which operation URL a method calls, and the vendor's
parameter spelling
(``partDiv``, ``lrgDiv``, ``startBaseMm``), stay in this module and never surface
to the caller.
"""

from __future__ import annotations

from enum import StrEnum
from types import TracebackType
from typing import Any, Self, TypeVar, cast

import httpx

from . import _parse
from ._accessor import CompanyView, SectorView
from ._companies import (
    _BankCompanyView,
    _CardCompanyView,
    _LifeCompanyView,
    _NonlifeCompanyView,
    _SecuritiesCompanyView,
)
from ._config import resolve_api_key
from ._transport import _Transport
from .types import (
    AccountRow,
    Category,
    CompanyRow,
    Data,
    Lang,
    Sector,
    StatisticsRow,
    Term,
)

_DEFAULT_TIMEOUT = 30.0

# One host, one operation per path; the ``.json`` suffix selects the JSON format.
_URL_COMPANY = "https://fisis.fss.or.kr/openapi/companySearch.json"
_URL_STATISTICS = "https://fisis.fss.or.kr/openapi/statisticsListSearch.json"
_URL_ACCOUNT = "https://fisis.fss.or.kr/openapi/accountListSearch.json"
_URL_DATA = "https://fisis.fss.or.kr/openapi/statisticsInfoSearch.json"

_E = TypeVar("_E", bound=StrEnum)


def _to_enum(enum_cls: type[_E], value: _E | str) -> _E:
    """Coerce ``value`` to an ``enum_cls`` member, forgiving three spellings.

    Accepts the member itself, its vendor code value (``"H"``, ``"Q"``), or its
    member name case-insensitively (``"life"``, ``"quarterly"``) -- so
    both ``fetch_data(term="quarterly")`` and ``fetch_data(term="Q")`` work.
    Raises ``ValueError`` naming the accepted words otherwise.
    """
    if isinstance(value, enum_cls):
        return value
    try:
        return enum_cls(value)  # by vendor code value
    except ValueError:
        pass
    try:
        return enum_cls[value.upper()]  # by member name
    except KeyError:
        words = ", ".join(member.name.lower() for member in enum_cls)
        raise ValueError(
            f"{value!r} is not a valid {enum_cls.__name__}; use one of: {words}"
        ) from None


class FISIS:
    """A client for the FISIS (금융감독원 금융통계정보시스템) Open API.

    Construct it with an API key, or leave it out to resolve one from the
    ``FISIS_API_KEY`` environment variable or
    ``~/.config/fisis/credentials.json``::

        with FISIS() as fisis:
            companies = fisis.list_companies(sector=Sector.LIFE)

    FISIS identifies a time series by a company (``finance_cd``), a statistic
    (``list_no``), and optionally an account item (``account_cd``); discover the
    codes step by step -- :meth:`list_companies` for a sector's companies,
    :meth:`list_statistics` for its statistics catalog, :meth:`list_accounts` for
    one statistic's account items -- then pull the numbers with
    :meth:`fetch_data`, which returns a :class:`Data` (the observation rows plus
    their column/unit legend). The ``list_*`` methods return a list of plain
    dicts, one per row, and a :class:`Data`'s ``rows`` is that same records
    format -- ready for ``pd.DataFrame(rows)`` without this package importing
    pandas (or :meth:`Data.to_pandas` / :meth:`Data.to_polars`).

    The client owns a pooled HTTP connection, so reuse one instance across calls
    and close it when done -- as a context manager, or via :meth:`close`. Set
    ``delay_seconds`` to space out requests when fetching many series in a loop;
    note that FISIS's hard cap is a *daily* search quota, which pacing spreads
    but cannot lift.

    Construction raises :class:`FISISConfigError` if no API key can be resolved.
    Every service method then raises from the :class:`FISISError` family:
    :class:`FISISAuthError` if the key is rejected, :class:`FISISRateLimitError`
    when the daily quota (or an HTTP 429) is hit, :class:`FISISResponseError` on
    any other vendor error (FISIS reports these as ``err_cd`` / ``err_msg`` on
    the response's ``result`` object -- e.g. ``err_cd`` 103 when a window spans
    more than 40 quarters), and :class:`FISISNetworkError` if the request never
    completes (a transient timeout, 5xx, or FISIS-internal error 900 is retried
    with backoff first). A catalog query that matches no data returns an empty
    list; :meth:`fetch_data` returns a :class:`Data` with no rows. A bad argument
    raises the standard ``ValueError`` -- an
    unrecognized ``sector`` / ``category`` / ``term`` / ``lang`` string.
    """

    def __init__(
        self,
        api_key: str | None = None,
        *,
        timeout: float = _DEFAULT_TIMEOUT,
        delay_seconds: float = 0.0,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self._api_key = resolve_api_key(api_key)
        self._client = httpx.Client(timeout=timeout, transport=transport)
        self._transport = _Transport(self._client, delay_seconds=delay_seconds)

        # One explicit handle per sector, so `f.life` autocompletes in an editor
        # and type-checks -- deliberately spelled out rather than looped with
        # setattr, which would be invisible to both. Five sectors pass their
        # company-view subclass, so `f.<sector>.company(...)` also autocompletes
        # named statistics; the other 17 default to the base CompanyView.
        self.bank = SectorView(self, Sector.BANK, _BankCompanyView)
        self.foreign_bank = SectorView(self, Sector.FOREIGN_BANK, CompanyView)
        self.life = SectorView(self, Sector.LIFE, _LifeCompanyView)
        self.nonlife = SectorView(self, Sector.NONLIFE, _NonlifeCompanyView)
        self.securities = SectorView(self, Sector.SECURITIES, _SecuritiesCompanyView)
        self.futures = SectorView(self, Sector.FUTURES, CompanyView)
        self.asset_management = SectorView(self, Sector.ASSET_MANAGEMENT, CompanyView)
        self.investment_advisory = SectorView(
            self, Sector.INVESTMENT_ADVISORY, CompanyView)
        self.merchant_bank = SectorView(self, Sector.MERCHANT_BANK, CompanyView)
        self.card = SectorView(self, Sector.CARD, _CardCompanyView)
        self.leasing = SectorView(self, Sector.LEASING, CompanyView)
        self.capital = SectorView(self, Sector.CAPITAL, CompanyView)
        self.new_tech = SectorView(self, Sector.NEW_TECH, CompanyView)
        self.savings_bank = SectorView(self, Sector.SAVINGS_BANK, CompanyView)
        self.credit_union = SectorView(self, Sector.CREDIT_UNION, CompanyView)
        self.nonghyup = SectorView(self, Sector.NONGHYUP, CompanyView)
        self.suhyup = SectorView(self, Sector.SUHYUP, CompanyView)
        self.forestry_coop = SectorView(self, Sector.FORESTRY_COOP, CompanyView)
        self.real_estate_trust = SectorView(
            self, Sector.REAL_ESTATE_TRUST, CompanyView)
        self.holding = SectorView(self, Sector.HOLDING, CompanyView)
        self.trust_common = SectorView(self, Sector.TRUST_COMMON, CompanyView)
        self.derivatives_common = SectorView(
            self, Sector.DERIVATIVES_COMMON, CompanyView)

    # -- lifecycle ---------------------------------------------------------

    def close(self) -> None:
        """Close the underlying HTTP connection pool."""
        self._client.close()

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self.close()

    def __repr__(self) -> str:
        # Deliberately never shows the API key.
        return "FISIS()"

    # -- operations --------------------------------------------------------

    def list_companies(
        self,
        *,
        sector: Sector | str,
        finance_cd: str | None = None,
        lang: Lang | str = Lang.KO,
    ) -> list[CompanyRow]:
        """List one sector's financial companies (operation companySearch).

        ``sector`` is the financial sector (:class:`Sector` -- banks, life
        insurers, securities firms, ...); ``finance_cd`` optionally narrows to
        one company code. Each row carries the company code (``finance_cd`` --
        what :meth:`fetch_data` identifies a company by), its name, and its
        classification path.
        """
        params = {"partDiv": str(_to_enum(Sector, sector))}
        if finance_cd is not None:
            params["financeCd"] = finance_cd
        params["lang"] = str(_to_enum(Lang, lang))
        return cast(
            "list[CompanyRow]", _parse.list_rows(self._collect(_URL_COMPANY, params)))

    def list_statistics(
        self,
        *,
        sector: Sector | str,
        category: Category | str | None = None,
        lang: Lang | str = Lang.KO,
    ) -> list[StatisticsRow]:
        """Browse one sector's statistics catalog (operation statisticsListSearch).

        ``sector`` takes the same :class:`Sector` codes as
        :meth:`list_companies`; ``category`` optionally narrows to one catalog
        category (:class:`Category`, or a raw one-letter code for a
        sector-specific category outside the enum). Each row's ``list_no`` is the
        statistic code that :meth:`list_accounts` and :meth:`fetch_data` take.
        """
        params = {"lrgDiv": str(_to_enum(Sector, sector))}
        if category is not None:
            params["smlDiv"] = _category_code(category)
        params["lang"] = str(_to_enum(Lang, lang))
        return cast(
            "list[StatisticsRow]",
            _parse.list_rows(self._collect(_URL_STATISTICS, params)))

    def list_accounts(
        self,
        *,
        list_no: str,
        lang: Lang | str = Lang.KO,
    ) -> list[AccountRow]:
        """List one statistic's account items (operation accountListSearch).

        ``list_no`` is the statistic code from :meth:`list_statistics`. Each
        row's ``account_cd`` can narrow :meth:`fetch_data` to one account item.
        """
        params = {
            "listNo": list_no,
            "lang": str(_to_enum(Lang, lang)),
        }
        return cast(
            "list[AccountRow]", _parse.list_rows(self._collect(_URL_ACCOUNT, params)))

    def fetch_data(
        self,
        *,
        finance_cd: str,
        list_no: str,
        term: Term | str,
        start_month: str,
        end_month: str,
        account_cd: str | None = None,
        lang: Lang | str = Lang.KO,
    ) -> Data:
        """Fetch a statistic's observations (operation statisticsInfoSearch).

        Returns a :class:`Data` -- the observation ``rows`` plus the value-column
        legend (each column's human name and unit) and the fiscal
        ``date_of_settlement``. The rows are the common case (``table.rows`` is
        the records list ``pd.DataFrame`` / ``pl.DataFrame`` consume, or
        :meth:`Data.to_pandas` / :meth:`Data.to_polars`); the legend is there
        for when the numbers are meaningless without their units (a table mixing
        ``"원"`` and ``"%"`` columns).

        Identify the series with ``finance_cd`` (the company, from
        :meth:`list_companies`) plus ``list_no`` (the statistic, from
        :meth:`list_statistics`). ``term`` is the reporting interval
        (:class:`Term` -- annual, half-yearly, quarterly); ``start_month`` and
        ``end_month`` bound the window as YYYYMM months (``"202403"``), and the
        window cannot span more than 40 quarters (FISIS refuses a longer one with
        ``err_cd`` 103). ``account_cd`` (from :meth:`list_accounts`) narrows to
        one account item; omitted, every account of the statistic is returned.

        FISIS ships each observation's values in opaque columns (``a``, ``b``,
        ...) plus a legend naming them; the returned rows have those columns
        already resolved to their human names, so a balance statistic's row reads
        ``{"base_month": ..., "말잔": ...}`` (see :class:`DataRow`).
        """
        params = {
            "financeCd": finance_cd,
            "listNo": list_no,
            "term": str(_to_enum(Term, term)),
            "startBaseMm": start_month,
            "endBaseMm": end_month,
        }
        if account_cd is not None:
            params["accountCd"] = account_cd
        params["lang"] = str(_to_enum(Lang, lang))
        return _parse.make_data(self._collect(_URL_DATA, params))

    # -- internals ---------------------------------------------------------

    def _collect(self, base_url: str, params: dict[str, str]) -> dict[str, Any]:
        """Send one authenticated request and return its raw ``result`` payload."""
        request_params = {"auth": self._api_key, **params}
        return self._transport.request(base_url=base_url, params=request_params)


def _category_code(category: Category | str) -> str:
    """The vendor ``smlDiv`` code for ``category``, allowing codes off the enum.

    :class:`Category` covers the codes shared across sectors; a few sectors add
    their own (real-estate trust files its key-metrics tables under ``"E"``), so
    a single uppercase letter passes through verbatim even when no member carries
    it. Anything else must resolve to a member.
    """
    if isinstance(category, str) and len(category) == 1 and category.isupper():
        return category
    return str(_to_enum(Category, category))
