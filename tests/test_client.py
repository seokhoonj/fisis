"""Client behavior against a mocked FISIS, exercised without a network."""

from __future__ import annotations

import json
import traceback
from typing import Any

import httpx
import pytest

from fisis import (
    FISIS,
    Category,
    Data,
    FISISAuthError,
    FISISConfigError,
    FISISNetworkError,
    FISISRateLimitError,
    FISISResponseError,
    Lang,
    Sector,
    Term,
)
from fisis.client import _to_enum


def _success(rows: list[dict[str, Any]], **extra: Any) -> dict[str, Any]:
    """A well-formed FISIS success payload carrying ``rows``."""
    result: dict[str, Any] = {
        "err_cd": "000",
        "err_msg": "정상",
        "total_count": str(len(rows)),
        "list": rows,
    }
    result.update(extra)
    return {"result": result}


def _error(code: str, message: str) -> dict[str, Any]:
    return {"result": {"err_cd": code, "err_msg": message}}


def _handler(
    responses: list[dict[str, Any]], recorded: list[httpx.Request]
) -> httpx.MockTransport:
    """Return a MockTransport handler that replays ``responses`` in order."""
    remaining = list(responses)

    def handle(request: httpx.Request) -> httpx.Response:
        recorded.append(request)
        return httpx.Response(200, json=remaining.pop(0))

    return httpx.MockTransport(handle)


def _client(
    responses: list[dict[str, Any]],
    recorded: list[httpx.Request] | None = None,
) -> FISIS:
    recorded = [] if recorded is None else recorded
    return FISIS("TESTKEY", transport=_handler(responses, recorded))


# -- config ----------------------------------------------------------------


def test_missing_api_key_raises_config_error(monkeypatch, tmp_path):
    monkeypatch.delenv("FISIS_API_KEY", raising=False)
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))  # empty -- no credentials
    with pytest.raises(FISISConfigError):
        FISIS()


def test_api_key_read_from_environment(monkeypatch):
    monkeypatch.setenv("FISIS_API_KEY", "FROMENV")
    fisis = FISIS(transport=_handler([_success([])], []))
    assert fisis._api_key == "FROMENV"


def test_repr_never_shows_key():
    assert "TESTKEY" not in repr(_client([_success([])]))


# -- list_companies ---------------------------------------------------------


def test_list_companies_builds_request_and_parses_rows():
    recorded: list[httpx.Request] = []
    fisis = _client(
        [_success([{"finance_cd": "0010001", "finance_nm": "생보사",
                    "finance_path": "생명보험>생명보험사"}])],
        recorded)
    rows = fisis.list_companies(sector=Sector.LIFE)

    assert rows == [{"finance_cd": "0010001", "finance_nm": "생보사",
                     "finance_path": "생명보험>생명보험사"}]
    url = recorded[0].url
    assert url.host == "fisis.fss.or.kr"
    assert url.path == "/openapi/companySearch.json"
    assert url.params["partDiv"] == "H"
    assert url.params["auth"] == "TESTKEY"
    assert url.params["lang"] == "kr"
    assert "financeCd" not in url.params  # optional filter dropped when unset


def test_list_companies_optional_finance_cd_filter():
    recorded: list[httpx.Request] = []
    fisis = _client([_success([])], recorded)
    fisis.list_companies(sector="A", finance_cd="0010001")
    url = recorded[0].url
    assert url.params["partDiv"] == "A"
    assert url.params["financeCd"] == "0010001"


# -- list_statistics ---------------------------------------------------------


def test_list_statistics_builds_request_and_parses_rows():
    recorded: list[httpx.Request] = []
    fisis = _client(
        [_success([{"lrg_div_nm": "생명보험", "sml_div_nm": "재무현황",
                    "list_no": "SH002", "list_nm": "재무상태표"}])],
        recorded)
    rows = fisis.list_statistics(sector=Sector.LIFE)

    assert rows[0]["list_no"] == "SH002"
    url = recorded[0].url
    assert url.path == "/openapi/statisticsListSearch.json"
    assert url.params["lrgDiv"] == "H"
    assert "smlDiv" not in url.params  # optional category dropped when unset


def test_list_statistics_passes_category():
    recorded: list[httpx.Request] = []
    fisis = _client([_success([])], recorded)
    fisis.list_statistics(sector="H", category=Category.KEY_METRICS)
    assert recorded[0].url.params["smlDiv"] == "C"


def test_list_statistics_accepts_raw_category_code_off_the_enum():
    # Real-estate trust files its key-metrics tables under "E", which no Category
    # member carries; the raw one-letter code must pass through verbatim.
    recorded: list[httpx.Request] = []
    fisis = _client([_success([])], recorded)
    fisis.list_statistics(sector=Sector.REAL_ESTATE_TRUST, category="E")
    assert recorded[0].url.params["lrgDiv"] == "M"
    assert recorded[0].url.params["smlDiv"] == "E"


# -- list_accounts -----------------------------------------------------------


def test_list_accounts_builds_request_and_parses_rows():
    recorded: list[httpx.Request] = []
    fisis = _client(
        [_success([{"list_no": "SH002", "list_nm": "재무상태표",
                    "account_cd": "B", "account_nm": "자산총계"}])],
        recorded)
    rows = fisis.list_accounts(list_no="SH002")

    assert rows[0]["account_cd"] == "B"
    url = recorded[0].url
    assert url.path == "/openapi/accountListSearch.json"
    assert url.params["listNo"] == "SH002"
    assert url.params["auth"] == "TESTKEY"


# -- fetch_data --------------------------------------------------------------


def _data_payload() -> dict[str, Any]:
    # Live statisticsInfoSearch shape: description is a bare list, with
    # date_of_settlement / unit as top-level siblings of it.
    return _success(
        [{"base_month": "202403", "finance_cd": "0010001", "finance_nm": "생보사",
          "account_cd": "B", "account_nm": "자산총계",
          "a": "497042153", "b": "479913190"}],
        description=[{"column_id": "a", "column_nm": "말잔"},
                     {"column_id": "b", "column_nm": "평잔"}],
        date_of_settlement="12/31",
        unit="백만원",
    )


def test_fetch_data_builds_request():
    recorded: list[httpx.Request] = []
    fisis = _client([_data_payload()], recorded)
    fisis.fetch_data(finance_cd="0010001", list_no="SH002", term=Term.QUARTERLY,
                     start_month="202403", end_month="202412")
    url = recorded[0].url
    assert url.path == "/openapi/statisticsInfoSearch.json"
    assert url.params["financeCd"] == "0010001"
    assert url.params["listNo"] == "SH002"
    assert url.params["term"] == "Q"
    assert url.params["startBaseMm"] == "202403"
    assert url.params["endBaseMm"] == "202412"
    assert url.params["auth"] == "TESTKEY"
    assert "accountCd" not in url.params  # omitted: every account is returned


def test_fetch_data_resolves_value_columns_to_names():
    fisis = _client([_data_payload()])
    rows = fisis.fetch_data(finance_cd="0010001", list_no="SH002", term="Q",
                            start_month="202403", end_month="202412").rows

    assert rows[0]["말잔"] == "497042153"
    assert rows[0]["평잔"] == "479913190"
    assert "a" not in rows[0] and "b" not in rows[0]  # opaque keys are resolved
    assert rows[0]["base_month"] == "202403"  # identifying fields untouched
    assert rows[0]["account_nm"] == "자산총계"


def test_fetch_data_account_cd_narrows():
    recorded: list[httpx.Request] = []
    fisis = _client([_data_payload()], recorded)
    fisis.fetch_data(finance_cd="0010001", list_no="SH002", term="Y",
                     start_month="202312", end_month="202412", account_cd="B")
    assert recorded[0].url.params["accountCd"] == "B"
    assert recorded[0].url.params["term"] == "Y"


def test_fetch_data_empty_result_has_no_rows():
    payload = {"result": {"err_cd": "000", "err_msg": "정상", "total_count": "0"}}
    fisis = _client([payload])
    table = fisis.fetch_data(finance_cd="0010001", list_no="SH002", term="Q",
                             start_month="202403", end_month="202412")
    assert table.rows == []
    assert table.columns == ()


def test_missing_result_wrapper_is_tolerated():
    # The documented shape nests everything under "result"; a payload that is
    # itself the result object must still parse.
    payload = {"err_cd": "000", "err_msg": "정상", "total_count": "1",
               "list": [{"finance_cd": "0010001"}]}
    fisis = _client([payload])
    assert fisis.list_companies(sector="H") == [{"finance_cd": "0010001"}]


# -- fetch_data returns the full Data (rows + per-column units + settlement) -


def test_fetch_data_returns_columns_units_settlement_and_builds_request():
    recorded: list[httpx.Request] = []
    payload = _success(
        [{"base_month": "202403", "finance_cd": "0010001", "finance_nm": "생보사",
          "account_cd": "A", "account_nm": "자산", "a": "1000", "b": "55.5"}],
        description=[{"column_id": "a", "column_nm": "금액"},
                     {"column_id": "b", "column_nm": "구성비"}],
        unit="원,%",
        date_of_settlement="12/31",
    )
    fisis = _client([payload], recorded)
    table = fisis.fetch_data(finance_cd="0010001", list_no="SH150", term="Q",
                             start_month="202403", end_month="202403")

    assert isinstance(table, Data)
    name_units = [(c.name, c.unit) for c in table.columns]
    assert name_units == [("금액", "원"), ("구성비", "%")]
    assert table.date_of_settlement == "12/31"
    assert table.rows[0]["금액"] == "1000"  # rows carry the same resolved names
    url = recorded[0].url
    assert url.path == "/openapi/statisticsInfoSearch.json"
    assert url.params["financeCd"] == "0010001"
    assert url.params["listNo"] == "SH150"
    assert url.params["term"] == "Q"


# -- vendor error mapping ----------------------------------------------------


@pytest.mark.parametrize(
    ("code", "message"),
    [
        ("010", "등록되지 않은 인증키입니다."),
        ("011", "중지된 인증키입니다."),
        ("012", "삭제된 인증키입니다."),
        ("013", "샘플 인증키입니다."),
    ],
)
def test_rejected_key_raises_auth_error(code, message):
    fisis = _client([_error(code, message)])
    with pytest.raises(FISISAuthError) as info:
        fisis.list_companies(sector="H")
    assert info.value.code == code


def test_daily_quota_raises_rate_limit_and_is_not_retried():
    recorded: list[httpx.Request] = []
    fisis = _client([_error("020", "일일검색 허용횟수를 초과하였습니다.")], recorded)
    with pytest.raises(FISISRateLimitError) as info:
        fisis.list_companies(sector="H")
    assert info.value.code == "020"
    assert len(recorded) == 1  # the quota resets by the day, retrying cannot help


@pytest.mark.parametrize(
    ("code", "message"),
    [
        ("021", "허용된 IP가 아닙니다."),
        ("022", "허용된 언어가 아닙니다."),
        ("100", "필수 요청변수가 누락되었습니다."),
        ("101", "요청변수의 값이 부적절합니다."),
        ("102", "조회시작일이 조회종료일보다 큽니다."),
        ("103", "조회기간이 40분기를 초과하였습니다."),
        ("777", "알 수 없는 오류"),  # any unknown code stays a response error
    ],
)
def test_request_mistakes_raise_response_error_with_code(code, message):
    fisis = _client([_error(code, message)])
    with pytest.raises(FISISResponseError) as info:
        fisis.list_companies(sector="H")
    assert type(info.value) is FISISResponseError  # not an auth/rate-limit subclass
    assert info.value.code == code


def test_internal_error_900_retried_then_raises(monkeypatch):
    monkeypatch.setattr("fisis._transport.time.sleep", lambda _seconds: None)
    recorded: list[httpx.Request] = []
    fisis = _client([_error("900", "정의되지 않은 오류가 발생하였습니다.")] * 3,
                    recorded)
    with pytest.raises(FISISResponseError) as info:
        fisis.list_companies(sector="H")
    assert info.value.code == "900"
    assert len(recorded) == 3  # one try plus two retries


def test_internal_error_900_recovers_on_retry(monkeypatch):
    monkeypatch.setattr("fisis._transport.time.sleep", lambda _seconds: None)
    recorded: list[httpx.Request] = []
    fisis = _client(
        [_error("900", "정의되지 않은 오류가 발생하였습니다."),
         _success([{"finance_cd": "0010001"}])],
        recorded)
    rows = fisis.list_companies(sector="H")
    assert rows == [{"finance_cd": "0010001"}]
    assert len(recorded) == 2


# -- HTTP-layer errors -------------------------------------------------------


def test_http_429_is_rate_limit_not_retried():
    calls = {"n": 0}

    def handle(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        return httpx.Response(429)

    fisis = FISIS("TESTKEY", transport=httpx.MockTransport(handle))
    with pytest.raises(FISISRateLimitError):
        fisis.list_companies(sector="H")
    assert calls["n"] == 1  # Too Many Requests is the server's answer, not retried


def test_other_4xx_is_network_error():
    fisis = FISIS(
        "TESTKEY", transport=httpx.MockTransport(lambda r: httpx.Response(404)))
    with pytest.raises(FISISNetworkError):
        fisis.list_companies(sector="H")


def test_server_error_retries_then_raises_network_error(monkeypatch):
    monkeypatch.setattr("fisis._transport.time.sleep", lambda _seconds: None)
    calls = {"n": 0}

    def handle(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        return httpx.Response(500)

    fisis = FISIS("TESTKEY", transport=httpx.MockTransport(handle))
    with pytest.raises(FISISNetworkError):
        fisis.list_companies(sector="H")
    assert calls["n"] == 3  # one try plus two retries


def test_non_json_success_raises_response_error():
    transport = httpx.MockTransport(
        lambda request: httpx.Response(200, text="<html>maintenance</html>"))
    fisis = FISIS("TESTKEY", transport=transport)
    with pytest.raises(FISISResponseError) as info:
        fisis.list_companies(sector="H")
    assert info.value.code == "UNKNOWN"
    assert isinstance(info.value.__cause__, json.JSONDecodeError)


# -- transport hardening -----------------------------------------------------


def test_requests_use_https_so_the_key_is_not_sent_in_clear():
    # The key rides in the query string (auth=...); over plain http it would go
    # in clear. Pinning https here fails CI if a base URL is reverted to http.
    recorded: list[httpx.Request] = []
    fisis = _client([_success([]), _success([]), _success([]), _data_payload()],
                    recorded)
    fisis.list_companies(sector="H")
    fisis.list_statistics(sector="H")
    fisis.list_accounts(list_no="SH002")
    fisis.fetch_data(finance_cd="0010001", list_no="SH002", term="Q",
                     start_month="202403", end_month="202403")
    assert [request.url.scheme for request in recorded] == ["https"] * 4


def test_http_302_redirect_is_network_error_and_leaks_nothing():
    # httpx does not follow redirects by default; a 302 surfaces as an
    # HTTPStatusError. It is status < 500, so it is not retried (one attempt),
    # and neither the key nor the redirect target (the host) may leak.
    calls = {"n": 0}

    def handle(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        # A realistic http->https bounce: the Location names the host.
        return httpx.Response(
            302, headers={"location": "https://fisis.fss.or.kr/openapi/x.json"})

    fisis = FISIS("SECRETKEY123", transport=httpx.MockTransport(handle))
    with pytest.raises(FISISNetworkError) as info:
        fisis.list_companies(sector="H")
    assert calls["n"] == 1  # a 3xx is the server's answer, not retried
    assert "SECRETKEY123" not in _rendered(info.value)
    assert "fisis.fss.or.kr" not in _rendered(info.value)  # no Location/URL leak


def test_integer_err_cd_is_normalized_to_string_code():
    # Every real fixture sends a string err_cd; guard the str() coercion so an
    # integer code still maps and .code stays a comparable string.
    payload = {"result": {"err_cd": 100, "err_msg": "필수 요청변수가 누락되었습니다."}}
    fisis = _client([payload])
    with pytest.raises(FISISResponseError) as info:
        fisis.list_companies(sector="H")
    assert info.value.code == "100"


# -- security ----------------------------------------------------------------


def _rendered(exc: BaseException) -> str:
    """Everything a caller could print for ``exc``: its message and full traceback."""
    return str(exc) + "".join(
        traceback.format_exception(type(exc), exc, exc.__traceback__))


def test_api_key_never_reaches_an_error_message(monkeypatch):
    # The key rides in the request URL (auth=...). No error path -- a rejected
    # key, rate limit, other 4xx, 5xx after retries, or a transport failure --
    # may surface it, or the key-bearing URL, in the exception message or a
    # printed traceback.
    monkeypatch.setattr("fisis._transport.time.sleep", lambda _seconds: None)

    def _connect_error(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("boom", request=request)

    def _auth_rejected(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=_error("010", "등록되지 않은 인증키입니다."))

    def _quota_exceeded(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=_error("020", "일일검색 초과"))

    def _response_error_100(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=_error("100", "필수변수 누락"))

    def _internal_900(request: httpx.Request) -> httpx.Response:
        # Returned on every attempt -- the three retries all leak-check too.
        return httpx.Response(200, json=_error("900", "정의되지 않은 오류"))

    cases = [
        (_auth_rejected, FISISAuthError),           # vendor err_cd 010
        (_quota_exceeded, FISISRateLimitError),     # vendor err_cd 020
        (_response_error_100, FISISResponseError),  # vendor err_cd 100
        (_internal_900, FISISResponseError),        # vendor err_cd 900, retried
        (lambda r: httpx.Response(429), FISISRateLimitError),
        (lambda r: httpx.Response(404), FISISNetworkError),
        (lambda r: httpx.Response(500), FISISNetworkError),
        (_connect_error, FISISNetworkError),
    ]
    for handler, expected in cases:
        fisis = FISIS("SECRETKEY123", transport=httpx.MockTransport(handler))
        with pytest.raises(expected) as info:
            fisis.fetch_data(finance_cd="0010001", list_no="SH002", term="Q",
                             start_month="202403", end_month="202412")
        assert "SECRETKEY123" not in _rendered(info.value)
        assert "fisis.fss.or.kr" not in _rendered(info.value)  # no request URL


# -- enum coercion (member, vendor code, or member name all work) ------------


def test_to_enum_accepts_member_code_and_name():
    for value in (Sector.LIFE, "H", "life", "LIFE"):
        assert _to_enum(Sector, value) is Sector.LIFE


def test_enum_args_accept_all_three_spellings_via_client():
    recorded: list[httpx.Request] = []
    fisis = _client([_success([]), _success([]), _data_payload()], recorded)
    fisis.list_companies(sector="life")                     # member name
    fisis.list_statistics(sector=Sector.BANK, category="general")
    fisis.fetch_data(finance_cd="0010001", list_no="SH002", term="quarterly",
                     start_month="202403", end_month="202412", lang="ko")
    assert recorded[0].url.params["partDiv"] == "H"
    assert recorded[1].url.params["smlDiv"] == "A"
    assert recorded[2].url.params["term"] == "Q"
    assert recorded[2].url.params["lang"] == "kr"  # vendor code for Korean


def test_enum_arg_rejects_unknown_with_valueerror():
    fisis = _client([_success([])])
    with pytest.raises(ValueError):
        fisis.fetch_data(finance_cd="0010001", list_no="SH002", term="weekly",
                         start_month="202403", end_month="202412")


def test_english_language_sends_lang_en():
    recorded: list[httpx.Request] = []
    fisis = _client([_success([]), _success([])], recorded)
    fisis.list_companies(sector="H", lang=Lang.EN)  # enum member
    fisis.list_companies(sector="H", lang="en")      # member-name string
    assert recorded[0].url.params["lang"] == "en"
    assert recorded[1].url.params["lang"] == "en"


# -- lifecycle ---------------------------------------------------------------


def test_context_manager_closes():
    with _client([_success([])]) as fisis:
        assert fisis.list_companies(sector="H") == []
