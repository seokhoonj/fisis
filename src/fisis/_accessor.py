"""Fluent, IDE-navigable views over the FISIS client's flat operations.

The :class:`FISIS` client exposes four flat primitives keyed by codes
(``list_companies(sector=...)``, ``fetch_data(finance_cd=..., ...)``). These two
views bind those codes so a caller can navigate instead of repeating them:
``f.life.company("0010001").fetch(list_no=..., ...)`` reads left to right --
sector, then company, then the pull -- and every step is a plain attribute or
method an editor can autocomplete.

Both views are thin: they hold identifying state (a sector, a company code) and
delegate every request to the client's primitives, so there is no second copy of
the HTTP or parsing logic here. The client is taken as a duck-typed
:class:`_ClientProtocol` to keep this module free of an import cycle with
``client.py``.
"""

from __future__ import annotations

from typing import Generic, Protocol, Self, TypeVar

from .types import (
    AccountRow,
    Category,
    CompanyRow,
    Lang,
    Sector,
    StatisticsRow,
    Table,
    Term,
)

# The company-view type a sector yields: the base :class:`CompanyView`, or a
# sector-specific subclass (see ``_companies``) carrying named-statistic methods.
_C = TypeVar("_C", bound="CompanyView")


class _ClientProtocol(Protocol):
    """The client surface the views delegate to -- the four flat primitives.

    Declared structurally so :class:`SectorView` / :class:`CompanyView` depend on
    the *shape* of :class:`FISIS`, not the class itself, which would import-cycle
    (``client`` imports this module to build its per-sector attributes).
    """

    def list_companies(
        self, *, sector: Sector | str, finance_cd: str | None = ...,
        lang: Lang | str = ...,
    ) -> list[CompanyRow]: ...

    def list_statistics(
        self, *, sector: Sector | str, category: Category | str | None = ...,
        lang: Lang | str = ...,
    ) -> list[StatisticsRow]: ...

    def list_accounts(
        self, *, list_no: str, lang: Lang | str = ...,
    ) -> list[AccountRow]: ...

    def fetch_data(
        self, *, finance_cd: str, list_no: str, term: Term | str,
        start_month: str, end_month: str, account_cd: str | None = ...,
        lang: Lang | str = ...,
    ) -> Table: ...


class SectorView(Generic[_C]):
    """One financial sector, bound to a client -- the ``f.<sector>`` handle.

    Delegates :meth:`companies` / :meth:`statistics` to the client's flat
    primitives with the sector already filled in, and :meth:`company` resolves a
    company (by code or name) into a :class:`CompanyView` for the next step.

    Generic over the company-view type it yields: a plain sector produces the
    base :class:`CompanyView`, while a sector with headline named-statistic
    methods (banks, insurers, ...) produces its subclass, so an editor
    autocompletes those methods off ``sector.company(...)``.
    """

    def __init__(
        self,
        client: _ClientProtocol,
        sector: Sector,
        company_cls: type[_C],
    ) -> None:
        self._client = client
        self._sector = sector
        self._company_cls = company_cls

    def companies(
        self,
        *,
        finance_cd: str | None = None,
        lang: Lang | str = Lang.KO,
    ) -> list[CompanyRow]:
        """List this sector's companies (delegates to ``list_companies``)."""
        return self._client.list_companies(
            sector=self._sector, finance_cd=finance_cd, lang=lang)

    def statistics(
        self,
        *,
        category: Category | str | None = None,
        lang: Lang | str = Lang.KO,
    ) -> list[StatisticsRow]:
        """Browse this sector's statistics catalog (via ``list_statistics``)."""
        return self._client.list_statistics(
            sector=self._sector, category=category, lang=lang)

    def accounts(
        self,
        *,
        list_no: str,
        lang: Lang | str = Lang.KO,
    ) -> list[AccountRow]:
        """List a statistic's account items (delegates to ``list_accounts``).

        The account items belong to the statistic (``list_no``), not to any one
        company, so they are listed at the sector level; pick a company only to
        :meth:`CompanyView.fetch` the actual observations.
        """
        return self._client.list_accounts(list_no=list_no, lang=lang)

    def company(self, key: str, *, lang: Lang | str = Lang.KO) -> _C:
        """Resolve ``key`` to this sector's company-view type for the given company.

        An all-digit ``key`` is taken as the ``finance_cd`` directly, with no
        lookup. Otherwise the sector's companies are fetched and ``key`` is
        matched against ``finance_nm`` -- an exact match wins; failing that, a
        substring match wins only if it is unique. Raises ``ValueError`` if
        nothing matches, or if a substring matches more than one company (the
        message names the candidates so the caller can disambiguate). The result
        is the sector's specific :class:`CompanyView` subclass where one exists,
        so its named-statistic methods are reachable.
        """
        if not key:
            raise ValueError("company key must be a non-empty finance_cd or name")
        if key.isascii() and key.isdigit():
            return self._company_cls(self._client, finance_cd=key, finance_nm=None)
        companies = self.companies(lang=lang)
        return self._company_cls._from_name_match(self._client, key, companies)

    def __repr__(self) -> str:
        return f"SectorView({self._sector.name.lower()})"


class CompanyView:
    """One company, bound to a client -- the ``f.<sector>.company(...)`` handle.

    Carries the resolved ``finance_cd`` (and ``finance_nm`` when a name lookup
    supplied it) so :meth:`fetch` needs only the statistic (``list_no``).
    """

    def __init__(
        self, client: _ClientProtocol, *, finance_cd: str, finance_nm: str | None,
    ) -> None:
        self._client = client
        self._finance_cd = finance_cd
        self._finance_nm = finance_nm

    @classmethod
    def _from_name_match(
        cls, client: _ClientProtocol, name: str, companies: list[CompanyRow],
    ) -> Self:
        """Build a view by matching ``name`` against ``companies`` by ``finance_nm``.

        Exact ``finance_nm`` match first; else a unique substring match. Raises
        ``ValueError`` on no match or an ambiguous (multiple) substring match.
        Returns an instance of the calling class, so a subclass stays itself.
        """
        exact = [row for row in companies if row.get("finance_nm") == name]
        if len(exact) == 1:
            return cls._from_row(client, exact[0])

        substring = [
            row for row in companies if name in (row.get("finance_nm") or "")]
        if len(substring) == 1:
            return cls._from_row(client, substring[0])
        if len(substring) > 1:
            candidates = ", ".join(
                f"{row.get('finance_nm')} ({row.get('finance_cd')})"
                for row in substring)
            raise ValueError(
                f"{name!r} matches more than one company: {candidates}")
        raise ValueError(f"no company matching {name!r} in this sector")

    @classmethod
    def _from_row(cls, client: _ClientProtocol, row: CompanyRow) -> Self:
        finance_cd = row.get("finance_cd")
        if not finance_cd:
            raise ValueError(f"matched company has no finance_cd: {row!r}")
        return cls(client, finance_cd=finance_cd, finance_nm=row.get("finance_nm"))

    @property
    def finance_cd(self) -> str:
        """The resolved company code -- what :meth:`fetch` identifies the company by."""
        return self._finance_cd

    @property
    def finance_nm(self) -> str | None:
        """The company name, when a name lookup supplied it; ``None`` for a raw code."""
        return self._finance_nm

    def fetch(
        self,
        *,
        list_no: str,
        term: Term | str,
        start_month: str,
        end_month: str,
        account_cd: str | None = None,
        lang: Lang | str = Lang.KO,
    ) -> Table:
        """Fetch this company's observations (delegates to ``fetch_data``).

        Returns a :class:`Table` -- ``table.rows`` for the values, ``table.columns``
        for each value column's unit, ``table.date_of_settlement`` for the fiscal
        date. See :meth:`FISIS.fetch_data`.
        """
        return self._client.fetch_data(
            finance_cd=self._finance_cd, list_no=list_no, term=term,
            start_month=start_month, end_month=end_month, account_cd=account_cd,
            lang=lang)

    def __repr__(self) -> str:
        return (
            f"CompanyView(finance_cd={self._finance_cd!r}, "
            f"name={self._finance_nm!r})"
        )
