"""Fluent sector/company navigation over a mocked FISIS, exercised offline."""

from __future__ import annotations

from typing import Any

import httpx
import pytest

from fisis import FISIS, Category, CompanyView, Data, Sector, SectorView


def _success(rows: list[dict[str, Any]], **extra: Any) -> dict[str, Any]:
    result: dict[str, Any] = {
        "err_cd": "000",
        "err_msg": "정상",
        "total_count": str(len(rows)),
        "list": rows,
    }
    result.update(extra)
    return {"result": result}


def _data_payload() -> dict[str, Any]:
    # Live statisticsInfoSearch shape: description is a bare list, with
    # date_of_settlement / unit as top-level siblings of it.
    return _success(
        [{"base_month": "202403", "finance_cd": "0010001", "finance_nm": "삼성생명",
          "account_cd": "B", "account_nm": "자산총계",
          "a": "497042153", "b": "479913190"}],
        description=[{"column_id": "a", "column_nm": "말잔"},
                     {"column_id": "b", "column_nm": "평잔"}],
        date_of_settlement="12/31",
        unit="백만원",
    )


def _client(
    responses: list[dict[str, Any]],
    recorded: list[httpx.Request] | None = None,
) -> FISIS:
    recorded = [] if recorded is None else recorded
    remaining = list(responses)

    def handle(request: httpx.Request) -> httpx.Response:
        recorded.append(request)
        return httpx.Response(200, json=remaining.pop(0))

    return FISIS("TESTKEY", transport=httpx.MockTransport(handle))


# -- sector attributes are explicit and correctly mapped ---------------------


def test_sector_attributes_are_sector_views_with_the_right_code():
    fisis = _client([])
    assert isinstance(fisis.life, SectorView)
    assert fisis.life._sector is Sector.LIFE
    assert fisis.nonlife._sector is Sector.NONLIFE
    # Spot-check the renamed members reach their vendor codes.
    assert fisis.card._sector == "C"
    assert fisis.holding._sector == "L"
    assert fisis.foreign_bank._sector == "J"
    assert fisis.new_tech._sector == "N"


def test_sector_view_repr_names_the_sector():
    assert repr(_client([]).life) == "SectorView(life)"


# -- SectorView.companies / statistics delegate with the sector filled in -----


def test_companies_issues_companysearch_with_partdiv():
    recorded: list[httpx.Request] = []
    fisis = _client(
        [_success([{"finance_cd": "0010001", "finance_nm": "삼성생명"}])], recorded)
    rows = fisis.life.companies()

    assert rows == [{"finance_cd": "0010001", "finance_nm": "삼성생명"}]
    url = recorded[0].url
    assert url.path == "/openapi/companySearch.json"
    assert url.params["partDiv"] == "H"
    assert url.params["lang"] == "kr"


def test_statistics_issues_statisticslistsearch_with_lrgdiv_and_smldiv():
    recorded: list[httpx.Request] = []
    fisis = _client([_success([{"list_no": "HA001"}])], recorded)
    fisis.life.statistics(category=Category.KEY_METRICS)
    url = recorded[0].url
    assert url.path == "/openapi/statisticsListSearch.json"
    assert url.params["lrgDiv"] == "H"
    assert url.params["smlDiv"] == "C"


# -- SectorView.company resolution -------------------------------------------


def test_company_with_digit_key_skips_lookup():
    recorded: list[httpx.Request] = []
    fisis = _client([], recorded)
    view = fisis.life.company("0010001")

    assert isinstance(view, CompanyView)
    assert view.finance_cd == "0010001"
    assert view.finance_nm is None
    assert recorded == []  # an all-digit key is taken as the code, no request


def test_company_by_name_matches_finance_nm():
    recorded: list[httpx.Request] = []
    fisis = _client(
        [_success([{"finance_cd": "0010001", "finance_nm": "삼성생명"},
                   {"finance_cd": "0010002", "finance_nm": "한화생명"}])],
        recorded)
    view = fisis.life.company("삼성생명")

    assert view.finance_cd == "0010001"
    assert view.finance_nm == "삼성생명"
    assert recorded[0].url.params["partDiv"] == "H"  # the lookup did happen


def test_company_by_unique_substring_matches():
    fisis = _client(
        [_success([{"finance_cd": "0010001", "finance_nm": "삼성생명보험"},
                   {"finance_cd": "0010002", "finance_nm": "한화생명보험"}])])
    view = fisis.life.company("삼성")
    assert view.finance_cd == "0010001"


def test_company_empty_key_raises_value_error():
    # An empty key is neither a digit code nor a name to match -- reject it up
    # front rather than issue a companySearch that can only fail.
    recorded: list[httpx.Request] = []
    fisis = _client([], recorded)
    with pytest.raises(ValueError):
        fisis.life.company("")
    assert recorded == []  # rejected before any request


def test_company_no_match_raises_value_error():
    fisis = _client([_success([{"finance_cd": "0010001", "finance_nm": "삼성생명"}])])
    with pytest.raises(ValueError, match="no company matching"):
        fisis.life.company("없는회사")


def test_company_ambiguous_substring_raises_and_names_candidates():
    fisis = _client(
        [_success([{"finance_cd": "0010001", "finance_nm": "삼성생명"},
                   {"finance_cd": "0010009", "finance_nm": "삼성화재"}])])
    with pytest.raises(ValueError) as info:
        fisis.life.company("삼성")
    message = str(info.value)
    assert "삼성생명" in message and "삼성화재" in message


def test_exact_match_wins_over_substring():
    # "생명" is an exact finance_nm and also a substring of "생명나라"; exact wins.
    fisis = _client(
        [_success([{"finance_cd": "0010001", "finance_nm": "생명"},
                   {"finance_cd": "0010002", "finance_nm": "생명나라"}])])
    view = fisis.life.company("생명")
    assert view.finance_cd == "0010001"


# -- CompanyView.fetch / accounts delegate with finance_cd filled in ----------


def test_fetch_issues_statisticsinfosearch_and_resolves_columns():
    recorded: list[httpx.Request] = []
    fisis = _client([_data_payload()], recorded)
    rows = fisis.life.company("0010001").fetch(
        list_no="HA001", term="Q", start_month="202403", end_month="202403").rows

    assert rows[0]["말잔"] == "497042153"  # value columns resolved via the legend
    assert "a" not in rows[0]
    url = recorded[0].url
    assert url.path == "/openapi/statisticsInfoSearch.json"
    assert url.params["financeCd"] == "0010001"
    assert url.params["listNo"] == "HA001"
    assert url.params["term"] == "Q"
    assert url.params["startBaseMm"] == "202403"
    assert url.params["endBaseMm"] == "202403"


def test_fetch_delegates_with_finance_cd_and_carries_units():
    recorded: list[httpx.Request] = []
    payload = _success(
        [{"base_month": "202403", "finance_cd": "0010001", "account_cd": "A",
          "account_nm": "자산", "a": "1000", "b": "55.5"}],
        description=[{"column_id": "a", "column_nm": "금액"},
                     {"column_id": "b", "column_nm": "구성비"}],
        unit="원,%",
        date_of_settlement="12/31",
    )
    fisis = _client([payload], recorded)
    data = fisis.life.company("0010001").fetch(
        list_no="SH150", term="Q", start_month="202403", end_month="202403")

    assert isinstance(data, Data)
    name_units = [(c.name, c.unit) for c in data.columns]
    assert name_units == [("금액", "원"), ("구성비", "%")]
    assert data.date_of_settlement == "12/31"
    assert recorded[0].url.params["financeCd"] == "0010001"
    assert recorded[0].url.params["listNo"] == "SH150"


def test_accounts_issues_accountlistsearch_with_listno():
    recorded: list[httpx.Request] = []
    fisis = _client(
        [_success([{"list_no": "HA001", "account_cd": "B", "account_nm": "자산총계"}])],
        recorded)
    rows = fisis.life.accounts(list_no="HA001")

    assert rows[0]["account_cd"] == "B"
    url = recorded[0].url
    assert url.path == "/openapi/accountListSearch.json"
    assert url.params["listNo"] == "HA001"


def test_company_view_repr_shows_code_and_name():
    view = CompanyView(_client([]), finance_cd="0010001", finance_nm="삼성생명")
    assert repr(view) == "CompanyView(finance_cd='0010001', name='삼성생명')"
