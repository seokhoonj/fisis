"""Sector-specific company views: subclass dispatch and named-statistic requests."""

from __future__ import annotations

from typing import Any

import httpx
import pytest

from fisis import FISIS, CompanyView
from fisis._companies import (
    _BankCompanyView,
    _CardCompanyView,
    _LifeCompanyView,
    _NonlifeCompanyView,
    _SecuritiesCompanyView,
)


def _success(rows: list[dict[str, Any]], **extra: Any) -> dict[str, Any]:
    result: dict[str, Any] = {
        "err_cd": "000", "err_msg": "정상", "total_count": str(len(rows)),
        "list": rows,
    }
    result.update(extra)
    return {"result": result}


def _client(
    responses: list[dict[str, Any]], recorded: list[httpx.Request] | None = None
) -> FISIS:
    recorded = [] if recorded is None else recorded
    remaining = list(responses)

    def handle(request: httpx.Request) -> httpx.Response:
        recorded.append(request)
        return httpx.Response(200, json=remaining.pop(0))

    return FISIS("TESTKEY", transport=httpx.MockTransport(handle))


# The authoritative (sector, method, list_no, term) table -- one row per shipped
# named method, mirroring _companies.py exactly. A typo'd code or default term in
# any method fails here. Default term is "Q" except where the statistic only
# accepts another (bank productivity Y; the insurers' persistency H and
# agent_retention Y), matching the live-verified defaults in the source.
_NAMED_METHODS: list[tuple[str, str, str, str]] = [
    # BANK (12)
    ("bank", "capital_adequacy", "SA014", "Q"),
    ("bank", "asset_quality", "SA015", "Q"),
    ("bank", "profitability", "SA017", "Q"),
    ("bank", "liquidity", "SA018", "Q"),
    ("bank", "productivity", "SA019", "Y"),
    ("bank", "delinquency", "SA040", "Q"),
    ("bank", "npl_ratio", "SA041", "Q"),
    ("bank", "deposits", "SA028", "Q"),
    ("bank", "loans", "SA043", "Q"),
    ("bank", "balance_sheet_assets", "SA003", "Q"),
    ("bank", "balance_sheet_liabilities", "SA004", "Q"),
    ("bank", "income_statement", "SA021", "Q"),
    # LIFE (12)
    ("life", "solvency", "SH021", "Q"),
    ("life", "asset_quality", "SH112", "Q"),
    ("life", "liquidity", "SH115", "Q"),
    ("life", "efficiency", "SH114", "Q"),
    ("life", "persistency", "SH025", "H"),
    ("life", "agent_retention", "SH022", "Y"),
    ("life", "new_business", "SH160", "Q"),
    ("life", "in_force", "SH161", "Q"),
    ("life", "premium_income", "SH166", "Q"),
    ("life", "balance_sheet_assets", "SH150", "Q"),
    ("life", "balance_sheet_liabilities", "SH151", "Q"),
    ("life", "income_statement", "SH154", "Q"),
    # NONLIFE (11)
    ("nonlife", "solvency", "SI021", "Q"),
    ("nonlife", "asset_quality", "SI112", "Q"),
    ("nonlife", "liquidity", "SI115", "Q"),
    ("nonlife", "efficiency", "SI114", "Q"),
    ("nonlife", "persistency", "SI025", "H"),
    ("nonlife", "agent_retention", "SI022", "Y"),
    ("nonlife", "premium_income", "SI027", "Q"),
    ("nonlife", "retained_premium", "SI138", "Q"),
    ("nonlife", "balance_sheet_assets", "SI146", "Q"),
    ("nonlife", "balance_sheet_liabilities", "SI147", "Q"),
    ("nonlife", "income_statement", "SI150", "Q"),
    # CARD (11)
    ("card", "capital_adequacy", "SC007", "Q"),
    ("card", "asset_quality", "SC008", "Q"),
    ("card", "profitability", "SC009", "Q"),
    ("card", "liquidity", "SC010", "Q"),
    ("card", "delinquency", "SC117", "Q"),
    ("card", "credit_card_usage", "SC013", "Q"),
    ("card", "debit_card_usage", "SC014", "Q"),
    ("card", "purchase_volume", "SC016", "Q"),
    ("card", "balance_sheet_assets", "SC103", "Q"),
    ("card", "balance_sheet_liabilities", "SC104", "Q"),
    ("card", "income_statement", "SC218", "Q"),
    # SECURITIES (10)
    ("securities", "net_capital_ratio", "SF308", "Q"),
    ("securities", "leverage", "SF331", "Q"),
    ("securities", "asset_quality", "SF311", "Q"),
    ("securities", "liquidity", "SF209", "Q"),
    ("securities", "profitability", "SF210", "Q"),
    ("securities", "securities_trading", "SF316", "Q"),
    ("securities", "derivatives_trading", "SF317", "Q"),
    ("securities", "balance_sheet_assets", "SF303", "Q"),
    ("securities", "balance_sheet_liabilities", "SF304", "Q"),
    ("securities", "income_statement", "SF307", "Q"),
]

# The 5 sectors with a named-statistic subclass, and the 17 that stay base views.
_SPECIAL_SECTORS: list[tuple[str, type[CompanyView]]] = [
    ("bank", _BankCompanyView),
    ("life", _LifeCompanyView),
    ("nonlife", _NonlifeCompanyView),
    ("card", _CardCompanyView),
    ("securities", _SecuritiesCompanyView),
]
_PLAIN_SECTORS: list[str] = [
    "foreign_bank", "futures", "asset_management", "investment_advisory",
    "merchant_bank", "leasing", "capital", "new_tech", "savings_bank",
    "credit_union", "nonghyup", "suhyup", "forestry_coop", "real_estate_trust",
    "holding", "trust_common", "derivatives_common",
]


def _named_methods_on(view_cls: type[CompanyView]) -> set[str]:
    """The statistic-accessor names a sector view class defines *itself*.

    Only the subclass's own ``vars`` -- its named-statistic methods -- not the
    ``CompanyView`` machinery it inherits (``fetch``, ``company``, ...).
    """
    return {name for name, member in vars(view_cls).items()
            if not name.startswith("_") and callable(member)}


def test_named_method_table_matches_every_view_class_exactly():
    # The real guard: for each sector the (method) set in _NAMED_METHODS must equal
    # the methods that view class actually defines. A method shipped on a class but
    # forgotten in the table -- or a table row with no method -- fails here instead
    # of passing silently (a bare len()/count check cannot see either).
    for sector_attr, view_cls in _SPECIAL_SECTORS:
        tabled = {method for sector, method, *_ in _NAMED_METHODS
                  if sector == sector_attr}
        assert _named_methods_on(view_cls) == tabled, sector_attr


# -- every named method builds the right statisticsInfoSearch request ---------


@pytest.mark.parametrize(
    ("sector_attr", "method", "list_no", "term"),
    _NAMED_METHODS,
    ids=[f"{s}.{m}" for s, m, _c, _t in _NAMED_METHODS],
)
def test_named_method_issues_infosearch_with_code_and_default_term(
    sector_attr, method, list_no, term
):
    recorded: list[httpx.Request] = []
    fisis = _client([_success([])], recorded)
    company = getattr(fisis, sector_attr).company("0010001")
    getattr(company, method)(start_month="202401", end_month="202401")
    url = recorded[0].url
    assert url.path == "/openapi/statisticsInfoSearch.json"
    assert url.params["financeCd"] == "0010001"
    assert url.params["listNo"] == list_no
    assert url.params["term"] == term


# -- subclass dispatch: digit-key path ---------------------------------------


@pytest.mark.parametrize(("sector_attr", "expected_cls"), _SPECIAL_SECTORS)
def test_special_sector_company_is_its_subclass(sector_attr, expected_cls):
    fisis = _client([])
    view = getattr(fisis, sector_attr).company("0010001")  # digit-key path
    assert type(view) is expected_cls
    assert view.finance_cd == "0010001"


@pytest.mark.parametrize("sector_attr", _PLAIN_SECTORS)
def test_plain_sector_company_is_base_view(sector_attr):
    fisis = _client([])
    view = getattr(fisis, sector_attr).company("0010001")
    assert type(view) is CompanyView


# -- subclass dispatch: name-match path, over all 5 special sectors -----------


# One representative named method per special sector: the name-match must yield
# the subclass AND its method must then fire statisticsInfoSearch.
_NAME_MATCH_CASES = [
    ("bank", _BankCompanyView, "국민은행", "capital_adequacy", "SA014"),
    ("life", _LifeCompanyView, "삼성생명", "solvency", "SH021"),
    ("nonlife", _NonlifeCompanyView, "디비손해보험", "solvency", "SI021"),
    ("card", _CardCompanyView, "신한카드", "delinquency", "SC117"),
    ("securities", _SecuritiesCompanyView, "비엔케이투자증권",
     "net_capital_ratio", "SF308"),
]


@pytest.mark.parametrize(
    ("sector_attr", "expected_cls", "name", "method", "list_no"),
    _NAME_MATCH_CASES,
    ids=[case[0] for case in _NAME_MATCH_CASES],
)
def test_name_match_yields_subclass_and_named_method_fires(
    sector_attr, expected_cls, name, method, list_no
):
    recorded: list[httpx.Request] = []
    fisis = _client(
        [_success([{"finance_cd": "0010001", "finance_nm": name}]),  # the lookup
         _success([])],                                              # the data pull
        recorded)
    view = getattr(fisis, sector_attr).company(name)  # name-match path
    assert type(view) is expected_cls
    assert view.finance_cd == "0010001"
    getattr(view, method)(start_month="202401", end_month="202401")
    assert recorded[0].url.path == "/openapi/companySearch.json"
    assert recorded[1].url.path == "/openapi/statisticsInfoSearch.json"
    assert recorded[1].url.params["listNo"] == list_no


# -- convenience behaviors ---------------------------------------------------


def test_named_method_term_can_be_overridden():
    recorded: list[httpx.Request] = []
    fisis = _client([_success([])], recorded)
    fisis.life.company("0010595").balance_sheet_assets(
        start_month="202312", end_month="202312", term="Y")
    assert recorded[0].url.params["term"] == "Y"  # caller override wins


def test_named_method_returns_resolved_table():
    row = {"base_month": "202312", "finance_cd": "0010595", "account_cd": "A",
           "account_nm": "지급여력비율", "a": "201.5"}
    payload = _success([row], description=[{"column_id": "a", "column_nm": "비율"}],
                       unit="%")
    fisis = _client([payload])
    data = fisis.life.company("0010595").solvency(
        start_month="202312", end_month="202312")
    assert data.rows[0]["비율"] == "201.5"  # value column resolved
    assert [(c.name, c.unit) for c in data.columns] == [("비율", "%")]  # units carried
