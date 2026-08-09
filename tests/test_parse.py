"""The result-payload parser: shape normalization and value-column resolution."""

from __future__ import annotations

import pytest

from fisis import Column, FISISResponseError
from fisis._parse import data_rows, list_rows, make_table

# -- list_rows ---------------------------------------------------------------


def test_list_rows_absent_list_is_empty():
    assert list_rows({"err_cd": "000", "total_count": "0"}) == []


def test_list_rows_single_object_normalized_to_one_row():
    # A single record may arrive as a bare object rather than a one-element array.
    result = {"list": {"finance_cd": "0010001", "finance_nm": "생보사"}}
    assert list_rows(result) == [{"finance_cd": "0010001", "finance_nm": "생보사"}]


def test_list_rows_rejects_non_dict_entries():
    with pytest.raises(FISISResponseError):
        list_rows({"list": ["not-a-row"]})


# -- data_rows ---------------------------------------------------------------


def _balance_result() -> dict:
    # The live statisticsInfoSearch shape: description is a BARE LIST of
    # {column_id, column_nm}, and date_of_settlement / unit are its siblings at
    # the result top level (confirmed against a real call).
    return {
        "description": [{"column_id": "a", "column_nm": "말잔"},
                        {"column_id": "b", "column_nm": "평잔"}],
        "date_of_settlement": "12/31",
        "unit": "백만원",
        "list": [{"base_month": "202403", "finance_cd": "0010001",
                  "finance_nm": "생보사", "account_cd": "B",
                  "account_nm": "자산총계", "a": "100", "b": "90"}],
    }


def test_data_rows_resolves_value_columns():
    rows = data_rows(_balance_result())
    assert rows == [{"base_month": "202403", "finance_cd": "0010001",
                     "finance_nm": "생보사", "account_cd": "B",
                     "account_nm": "자산총계", "말잔": "100", "평잔": "90"}]


def test_data_rows_single_column_description_normalized():
    # A one-column legend may arrive as a bare object rather than a one-item list.
    result = _balance_result()
    result["description"] = {"column_id": "a", "column_nm": "말잔"}
    rows = data_rows(result)
    assert rows[0]["말잔"] == "100"
    assert rows[0]["b"] == "90"  # undescribed column passes through untouched


def test_data_rows_wrapped_column_description_still_resolves():
    # Defensive fallback: an older {"column": [...]} wrapper must still resolve,
    # so the http-era shape does not regress.
    result = _balance_result()
    result["description"] = {"column": [{"column_id": "a", "column_nm": "말잔"},
                                        {"column_id": "b", "column_nm": "평잔"}]}
    rows = data_rows(result)
    assert rows[0]["말잔"] == "100"
    assert rows[0]["평잔"] == "90"


def test_data_rows_without_description_keeps_raw_keys():
    result = _balance_result()
    del result["description"]
    rows = data_rows(result)
    assert rows[0]["a"] == "100"  # no legend -- nothing to resolve with


def test_data_rows_never_renames_identifying_fields():
    # Even a legend entry that reuses an identifying field name must not clobber it.
    result = _balance_result()
    result["description"].append({"column_id": "base_month", "column_nm": "기준월"})
    rows = data_rows(result)
    assert rows[0]["base_month"] == "202403"
    assert "기준월" not in rows[0]


# -- make_table (rows + column/unit legend + settlement) ---------------------


def test_make_table_pairs_names_with_units_positionally():
    result = {
        "description": [{"column_id": "a", "column_nm": "금액"},
                        {"column_id": "b", "column_nm": "구성비"}],
        "unit": "원,%",  # comma-joined, aligned position-wise with the columns
        "date_of_settlement": "12/31",
        "list": [{"base_month": "202403", "finance_cd": "0010001",
                  "account_cd": "A", "account_nm": "자산", "a": "1000", "b": "55.5"}],
    }
    table = make_table(result)
    assert table.columns == (Column("a", "금액", "원"), Column("b", "구성비", "%"))
    assert table.date_of_settlement == "12/31"
    assert table.rows[0]["금액"] == "1000"
    assert table.rows[0]["구성비"] == "55.5"


def test_make_table_single_column_single_unit():
    result = {
        "description": [{"column_id": "a", "column_nm": "영업이익률"}],
        "unit": "%",
        "list": [{"base_month": "202212", "finance_cd": "0010597",
                  "account_cd": "A", "account_nm": "영업이익률", "a": "2.65"}],
    }
    table = make_table(result)
    assert table.columns == (Column("a", "영업이익률", "%"),)
    assert table.date_of_settlement is None  # absent -- passes through as None


def test_make_table_unit_count_mismatch_sets_every_unit_none():
    result = {
        "description": [{"column_id": "a", "column_nm": "금액"},
                        {"column_id": "b", "column_nm": "구성비"}],
        "unit": "원",  # one token for two columns -- alignment is unknowable
        "list": [{"base_month": "202403", "a": "1000", "b": "55.5"}],
    }
    table = make_table(result)
    assert [column.name for column in table.columns] == ["금액", "구성비"]
    assert all(column.unit is None for column in table.columns)


def test_make_table_missing_unit_sets_unit_none():
    result = {
        "description": [{"column_id": "a", "column_nm": "금액"}],
        "list": [{"base_month": "202403", "a": "1000"}],
    }
    assert make_table(result).columns == (Column("a", "금액", None),)


def test_make_table_wrapped_description_still_resolves_columns():
    # Defensive: the {"column": [...]} fallback also produces the unit-paired legend.
    result = {
        "description": {"column": [{"column_id": "a", "column_nm": "금액"}]},
        "unit": "원",
        "list": [{"base_month": "202403", "a": "1000"}],
    }
    assert make_table(result).columns == (Column("a", "금액", "원"),)


def _two_column_result(unit: str) -> dict:
    return {
        "description": [{"column_id": "a", "column_nm": "금액"},
                        {"column_id": "b", "column_nm": "구성비"}],
        "unit": unit,
        "list": [{"base_month": "202403", "a": "1000", "b": "55.5"}],
    }


def test_make_table_strips_whitespace_around_unit_tokens():
    # A "원, %" with a space after the comma must yield stripped units.
    columns = make_table(_two_column_result("원, %")).columns
    assert [(column.name, column.unit) for column in columns] == [
        ("금액", "원"), ("구성비", "%")]


def test_make_table_empty_unit_token_becomes_none():
    # "원," aligns token-wise with two columns; the empty second token is None,
    # not an empty string.
    columns = make_table(_two_column_result("원,")).columns
    assert [(column.name, column.unit) for column in columns] == [
        ("금액", "원"), ("구성비", None)]
