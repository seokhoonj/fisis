"""CLI parsing, rendering, and exit codes, with a stubbed client (no network)."""

from __future__ import annotations

import json

import pytest

from fisis import cli
from fisis.exceptions import FISISConfigError, FISISResponseError
from fisis.types import Column, Table


class _FakeFISIS:
    """Stand-in for the client: records calls and returns canned rows or a table.

    The class attributes are set per test; instances are what ``with FISIS() as f``
    yields. The CLI passes the sector / term / lang strings straight through, so the
    fake records them verbatim (the real client's coercion is exercised elsewhere).
    """

    rows: list[dict] = []
    table: Table | None = None
    error: Exception | None = None
    calls: list[tuple[str, dict]] = []

    def __init__(self, *args, **kwargs) -> None:
        pass

    def __enter__(self) -> _FakeFISIS:
        return self

    def __exit__(self, *exc) -> bool:
        return False

    def _run(self, method: str, **kwargs):
        type(self).calls.append((method, kwargs))
        if type(self).error is not None:
            raise type(self).error
        return type(self).rows

    def list_companies(self, **kwargs):
        return self._run("list_companies", **kwargs)

    def list_statistics(self, **kwargs):
        return self._run("list_statistics", **kwargs)

    def list_accounts(self, **kwargs):
        return self._run("list_accounts", **kwargs)

    def fetch_data(self, **kwargs):
        # One fetch returns the full Table; a test sets `.table` for the legend
        # cases, else the rows are wrapped in a column-less, settlement-less Table.
        type(self).calls.append(("fetch_data", kwargs))
        if type(self).error is not None:
            raise type(self).error
        if type(self).table is not None:
            return type(self).table
        return Table(rows=type(self).rows, columns=(), date_of_settlement=None)


@pytest.fixture(autouse=True)
def _stub(monkeypatch):
    _FakeFISIS.rows = []
    _FakeFISIS.table = None
    _FakeFISIS.error = None
    _FakeFISIS.calls = []
    monkeypatch.setattr(cli, "FISIS", _FakeFISIS)


# -- version / usage -------------------------------------------------------


def test_version_exits_zero(capsys):
    with pytest.raises(SystemExit) as info:
        cli.main(["--version"])
    assert info.value.code == 0
    assert "fisis" in capsys.readouterr().out


def test_no_subcommand_is_usage_error():
    with pytest.raises(SystemExit) as info:
        cli.main([])
    assert info.value.code == 2


def test_data_missing_required_flag_is_usage_error():
    # --term / --start / --end are required; argparse rejects the gap with exit 2.
    with pytest.raises(SystemExit) as info:
        cli.main(["data", "0010001", "SH002", "--start", "202403", "--end", "202412"])
    assert info.value.code == 2


# -- rendering -------------------------------------------------------------


def test_companies_text_render(capsys):
    _FakeFISIS.rows = [{"finance_cd": "0010001", "finance_nm": "생보사",
                        "finance_path": "생명보험>생명보험사"}]
    assert cli.main(["companies", "--sector", "life"]) == 0
    out = capsys.readouterr().out
    assert "0010001" in out
    assert "생보사" in out
    assert "(1 rows)" in out
    method_name, kwargs = _FakeFISIS.calls[0]
    assert method_name == "list_companies"
    assert kwargs["sector"] == "life"  # passed straight through for client coercion


def test_statistics_text_render_and_category_passthrough(capsys):
    _FakeFISIS.rows = [{"lrg_div_nm": "생명보험", "sml_div_nm": "재무현황",
                        "list_no": "SH002", "list_nm": "재무상태표"}]
    assert cli.main(
        ["statistics", "--sector", "H", "--category", "financial"]) == 0
    out = capsys.readouterr().out
    assert "SH002" in out
    assert "재무상태표" in out
    _method_name, kwargs = _FakeFISIS.calls[0]
    assert kwargs["sector"] == "H"
    assert kwargs["category"] == "financial"


def test_accounts_text_render(capsys):
    _FakeFISIS.rows = [{"list_no": "SH002", "list_nm": "재무상태표",
                        "account_cd": "B", "account_nm": "자산총계"}]
    assert cli.main(["accounts", "SH002"]) == 0
    out = capsys.readouterr().out
    assert "자산총계" in out
    _method_name, kwargs = _FakeFISIS.calls[0]
    assert kwargs["list_no"] == "SH002"


def test_data_json_render(capsys):
    _FakeFISIS.rows = [{"base_month": "202403", "account_nm": "자산총계",
                        "말잔": "497042153"}]
    assert cli.main(["data", "0010001", "SH002", "--term", "Q",
                     "--start", "202403", "--end", "202412", "--json"]) == 0
    out = capsys.readouterr().out
    assert '"말잔": "497042153"' in out
    assert "자산총계" in out  # non-ASCII kept unescaped


def test_data_text_render_summary(capsys):
    _FakeFISIS.rows = [{"base_month": "202403", "말잔": "497042153"},
                       {"base_month": "202406", "말잔": "500000000"}]
    assert cli.main(["data", "0010001", "SH002", "--term", "Q",
                     "--start", "202403", "--end", "202412"]) == 0
    out = capsys.readouterr().out
    assert "SH002  2 obs" in out
    assert "497042153" in out
    method_name, kwargs = _FakeFISIS.calls[0]
    assert method_name == "fetch_data"
    assert kwargs["term"] == "Q"
    assert kwargs["start_month"] == "202403"
    assert kwargs["end_month"] == "202412"
    assert "account_cd" not in kwargs  # omitted when --account-cd is unset


def test_data_account_cd_forwarded():
    _FakeFISIS.rows = []
    cli.main(["data", "0010001", "SH002", "--term", "Y", "--start", "202312",
              "--end", "202412", "--account-cd", "B"])
    _method_name, kwargs = _FakeFISIS.calls[0]
    assert kwargs["account_cd"] == "B"


def test_data_table_renders_legend_and_settlement(capsys):
    _FakeFISIS.table = Table(
        rows=[{"base_month": "202403", "금액": "1000", "구성비": "55.5"}],
        columns=(Column("a", "금액", "원"), Column("b", "구성비", "%")),
        date_of_settlement="12/31")
    assert cli.main(["data", "0010001", "SH150", "--term", "Q",
                     "--start", "202403", "--end", "202403", "--table"]) == 0
    out = capsys.readouterr().out
    assert "settlement 12/31" in out
    assert "금액 (원)" in out
    assert "구성비 (%)" in out
    assert "1000" in out
    assert _FakeFISIS.calls[0][0] == "fetch_data"


def test_data_table_json_shape(capsys):
    _FakeFISIS.table = Table(
        rows=[{"base_month": "202403", "금액": "1000"}],
        columns=(Column("a", "금액", "원"),),
        date_of_settlement="12/31")
    assert cli.main(["data", "0010001", "SH150", "--term", "Q", "--start", "202403",
                     "--end", "202403", "--table", "--json"]) == 0
    out = capsys.readouterr().out
    assert '"date_of_settlement": "12/31"' in out
    assert '"unit": "원"' in out
    assert '"금액": "1000"' in out


def test_lang_forwarded_only_when_given():
    _FakeFISIS.rows = []
    cli.main(["companies", "--sector", "life"])
    assert "lang" not in _FakeFISIS.calls[0][1]  # client default kicks in
    _FakeFISIS.calls = []
    cli.main(["companies", "--sector", "life", "--lang", "en"])
    assert _FakeFISIS.calls[0][1]["lang"] == "en"


def test_empty_result_render(capsys):
    _FakeFISIS.rows = []
    assert cli.main(["companies", "--sector", "life"]) == 0
    assert "(no rows)" in capsys.readouterr().out


# -- error handling --------------------------------------------------------


def test_vendor_error_reported_as_one_line(capsys):
    _FakeFISIS.error = FISISResponseError("100", "필수 요청변수가 누락되었습니다.")
    assert cli.main(["data", "0010001", "SH002", "--term", "Q",
                     "--start", "202403", "--end", "202412"]) == 1
    err = capsys.readouterr().err
    assert err.startswith("fisis: ")
    assert "[100]" in err


def test_broken_pipe_is_swallowed(capsys):
    # `fisis data ... | head` closes the pipe early; the CLI must return 1 without
    # letting BrokenPipeError escape as a traceback.
    _FakeFISIS.error = BrokenPipeError()
    assert cli.main(["companies", "--sector", "life"]) == 1


def test_config_error_reported(capsys):
    _FakeFISIS.error = FISISConfigError("no FISIS API key")
    assert cli.main(["companies", "--sector", "life"]) == 1
    assert "no FISIS API key" in capsys.readouterr().err


def test_value_error_reported_as_usage_error(capsys):
    # An unrecognized enum word surfaces from the client as a ValueError; relay it as a
    # clean one-line error with exit 2, not a raw traceback.
    _FakeFISIS.error = ValueError("'weekly' is not a valid Term")
    assert cli.main(["data", "0010001", "SH002", "--term", "weekly",
                     "--start", "202403", "--end", "202412"]) == 2
    err = capsys.readouterr().err
    assert err.startswith("fisis: ")
    assert "Traceback" not in err


def test_api_key_never_appears_in_output(monkeypatch, capsys):
    # A real key lives in the environment; the CLI resolves it inside FISIS() and never
    # renders it. Embedding the key here (rather than a success response that never held
    # it) is what makes this a regression guard: if a later change echoed os.environ or
    # the resolved config, both the success and the error path would expose the token.
    monkeypatch.setenv("FISIS_API_KEY", "SECRETKEY0123456789abcdef0123456789")
    _FakeFISIS.rows = [{"finance_cd": "0010001", "finance_nm": "생보사"}]
    assert cli.main(["companies", "--sector", "life", "--json"]) == 0
    _FakeFISIS.rows = []
    _FakeFISIS.error = FISISResponseError("100", "필수 요청변수가 누락되었습니다.")
    assert cli.main(["companies", "--sector", "life"]) == 1
    captured = capsys.readouterr()
    assert "SECRETKEY0123456789abcdef0123456789" not in (captured.out + captured.err)


def test_companies_json_render(capsys):
    # --json is a per-command flag; prove it on a list command too (not only `data`),
    # and that Korean names stay unescaped and the payload parses.
    _FakeFISIS.rows = [{"finance_cd": "0010001", "finance_nm": "생보사"}]
    assert cli.main(["companies", "--sector", "life", "--json"]) == 0
    out = capsys.readouterr().out
    assert json.loads(out) == _FakeFISIS.rows
    assert "생보사" in out  # non-ASCII kept unescaped


def test_data_text_caps_rows_but_json_keeps_all(capsys):
    # The text view shows only the last _MAX_DATA_ROWS with a "showing last N" note; the
    # full result stays available in --json.
    _FakeFISIS.rows = [{"base_month": f"{2000 + i:04d}01", "말잔": str(i)}
                       for i in range(cli._MAX_DATA_ROWS + 5)]
    base = ["data", "0010001", "SH002", "--term", "Q", "--start", "202403",
            "--end", "202412"]
    assert cli.main(base) == 0
    text = capsys.readouterr().out
    assert f"showing last {cli._MAX_DATA_ROWS}" in text
    assert text.count("말잔") == 1  # header line only; body rows are unlabeled
    assert "(45 rows)" not in text  # capped, not the full count rendered as a grid
    assert cli.main(base + ["--json"]) == 0
    rows = json.loads(capsys.readouterr().out)
    assert len(rows) == cli._MAX_DATA_ROWS + 5  # every observation survives in JSON


def test_missing_cell_renders_dash(capsys):
    # A row missing a column the table lays out prints "-", not a blank or a KeyError.
    _FakeFISIS.rows = [{"finance_cd": "0010001", "finance_nm": "생보사",
                        "finance_path": "생명보험>생명보험사"},
                       {"finance_cd": "0010002", "finance_nm": "손보사"}]  # no path
    assert cli.main(["companies", "--sector", "life"]) == 0
    out = capsys.readouterr().out
    assert "손보사" in out
    assert "-" in out  # the absent finance_path cell


def test_json_flag_on_statistics_and_accounts(capsys):
    # The remaining two list commands also honor --json.
    _FakeFISIS.rows = [{"list_no": "SH002", "list_nm": "재무상태표"}]
    assert cli.main(["statistics", "--sector", "life", "--json"]) == 0
    assert json.loads(capsys.readouterr().out) == _FakeFISIS.rows
    assert cli.main(["accounts", "SH002", "--json"]) == 0
    assert json.loads(capsys.readouterr().out) == _FakeFISIS.rows
