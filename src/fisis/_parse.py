"""Turn a FISIS ``result`` payload into row dicts, resolving the value columns.

FISIS keys its JSON fields in lower snake_case already (``finance_cd``,
``base_month``), so no key renaming happens at the field level -- the names stay
1:1 with the FISIS documentation. What does need work:

- ``list`` (the rows) and ``description.column`` (the value-column legend) are
  normalized to lists: an absent ``list`` means "no rows", and a single record may
  arrive as a bare object rather than a one-element array.
- statisticsInfoSearch rows carry their observations in opaque columns named
  ``a``, ``b``, ``c``, ``d``, ... whose meaning lives in ``description.column``
  (``column_id`` -> ``column_nm``). :func:`data_rows` renames each present value
  column to its human name, so a row arrives as ``{"base_month": ..., "말잔":
  ...}`` instead of ``{"base_month": ..., "a": ...}`` -- the bare letters are
  meaningless without the legend.
"""

from __future__ import annotations

from typing import Any, cast

from .exceptions import FISISResponseError
from .types import Column, Data, DataRow

# The identifying fields of a statisticsInfoSearch row. Never renamed, even if a
# legend entry happened to reuse one of these as a column_id.
_FIXED_DATA_KEYS = frozenset(
    {"base_month", "finance_cd", "finance_nm", "account_cd", "account_nm"})


def list_rows(result: dict[str, Any]) -> list[dict[str, Any]]:
    """The ``list`` rows of ``result`` as a list of raw vendor dicts."""
    return _as_row_list(result.get("list"))


def data_rows(result: dict[str, Any]) -> list[dict[str, Any]]:
    """The statisticsInfoSearch rows, value columns resolved to their human names.

    Builds ``column_id -> column_nm`` from the ``result["description"]`` legend
    and renames each row's value columns accordingly; the identifying fields
    (``base_month``, ``finance_cd``, ...) pass through untouched, as do rows'
    values. Without a legend (a ``description`` absent or empty), rows pass
    through with their vendor keys as-is.
    """
    name_by_column_id = _column_names(result.get("description"))
    return [
        _resolve_row(row, name_by_column_id)
        for row in _as_row_list(result.get("list"))
    ]


def make_data(result: dict[str, Any]) -> Data:
    """Build a :class:`Data` from a statisticsInfoSearch ``result``.

    ``rows`` reuse :func:`data_rows` (value columns resolved to their names);
    ``columns`` pair each value column with its unit (see :func:`_columns`);
    ``date_of_settlement`` passes through, ``None`` when absent or non-string.
    """
    settlement = result.get("date_of_settlement")
    return Data(
        rows=cast("list[DataRow]", data_rows(result)),
        columns=_columns(result.get("description"), result.get("unit")),
        date_of_settlement=settlement if isinstance(settlement, str) else None,
    )


def _resolve_row(
    raw: dict[str, Any], name_by_column_id: dict[str, str]
) -> dict[str, Any]:
    row = {}
    for key, value in raw.items():
        if key in name_by_column_id and key not in _FIXED_DATA_KEYS:
            row[name_by_column_id[key]] = value
        else:
            row[key] = value
    return row


def _column_names(description: Any) -> dict[str, str]:
    """``column_id -> column_nm`` from the value-column legend; {} when absent."""
    return dict(_legend_entries(description))


def _legend_entries(description: Any) -> list[tuple[str, str]]:
    """Ordered ``(column_id, column_nm)`` pairs from the value-column legend.

    FISIS ships the legend as ``result["description"]`` -- a list of
    ``{column_id, column_nm}`` objects (confirmed against a live call). A
    single-column statistic may arrive as one bare object, and a
    ``{"column": [...]}`` wrapper is accepted defensively; ``_as_row_list``
    normalizes all three to a list. Order is preserved so a positional unit
    list can be aligned against it.
    """
    if isinstance(description, dict) and "column_id" not in description:
        description = description.get("column")  # unwrap a {"column": [...]} form
    entries = []
    for column in _as_row_list(description):
        column_id = column.get("column_id")
        column_nm = column.get("column_nm")
        if isinstance(column_id, str) and isinstance(column_nm, str):
            entries.append((column_id, column_nm))
    return entries


def _columns(description: Any, unit: Any) -> tuple[Column, ...]:
    """The value-column legend paired with units, in order.

    Units arrive as one comma-joined string aligned position-wise with the
    columns (``"원,%"`` -> 원, %); a single-column table gives one token
    (``"%"``). If the token count does not match the column count, every unit is
    ``None`` -- the alignment is unknowable, so it is not guessed. Returned as a
    tuple so the legend on a frozen ``Data`` is honestly immutable.
    """
    entries = _legend_entries(description)
    units = _split_units(unit, len(entries))
    return tuple(
        Column(column_id=column_id, name=name, unit=unit_token)
        for (column_id, name), unit_token in zip(entries, units, strict=True)
    )


def _split_units(unit: Any, count: int) -> list[str | None]:
    """``unit`` split on "," into ``count`` stripped tokens; ``None`` for an empty
    token, and ``count`` ``None`` on a length mismatch (alignment unknowable)."""
    if isinstance(unit, str):
        tokens = [token.strip() for token in unit.split(",")]
        if len(tokens) == count:
            return [token or None for token in tokens]
    return [None] * count


def _as_row_list(value: Any) -> list[dict[str, Any]]:
    """``value`` as a list of dict rows: ``None`` -> ``[]``, one object -> ``[it]``."""
    if value is None:
        return []
    if isinstance(value, dict):
        return [value]  # a single record rendered unwrapped
    if isinstance(value, list):
        rows = [row for row in value if isinstance(row, dict)]
        if len(rows) != len(value):
            raise FISISResponseError("UNKNOWN", f"unexpected FISIS rows: {value!r}")
        return rows
    raise FISISResponseError("UNKNOWN", f"unexpected FISIS rows: {value!r}")
