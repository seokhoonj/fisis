"""Command-line shell over ``FISIS`` -- ``fisis companies`` / ``statistics`` / ...

The shell over the shell: it parses ``argv``, runs one library call, and renders the
returned rows as aligned text (or ``--json``). All request and parsing knowledge stays
in the library -- this only formats what the library returns -- and it is stdlib-only,
so the package's single runtime dependency (``httpx``) is not widened by having a CLI.

    $ export FISIS_API_KEY=...
    $ fisis companies --sector life
    $ fisis statistics --sector life --category financial
    $ fisis accounts SH002
    $ fisis data 0010001 SH002 --term Q --start 202403 --end 202412
    $ fisis data 0010001 SH150 --term Q --start 202403 --end 202403 --table

The ``sector`` / ``category`` / ``term`` / ``lang`` flags take either the enum member
name (``life``, ``quarterly``) or the vendor code (``H``, ``Q``); the client coerces
them, so a bad value surfaces as a one-line ``fisis: <message>`` naming the accepted
words rather than a traceback.
"""

from __future__ import annotations

import argparse
import contextlib
import json
import os
import sys
from collections.abc import Callable, Mapping, Sequence
from typing import TypeAlias

from . import __version__
from .client import FISIS
from .exceptions import FISISError
from .types import Data

# How many rows the text view of `data` prints; the full result is always in --json.
_MAX_DATA_ROWS = 40

# The command name, single-sourced: the argparse prog, the --version banner, and the
# stderr error prefix all derive from it, so a rename touches one line.
_PROG = "fisis"
_ERROR_PREFIX = f"{_PROG}: "

Row: TypeAlias = Mapping[str, object]


def main(argv: Sequence[str] | None = None) -> int:
    """Parse ``argv``, run one call, and return a process exit code.

    A failure -- a missing API key, a rejected key, a vendor error, or a transport
    problem -- is printed as a one-line ``fisis: <message>`` to stderr and returns 1, so
    a shell caller sees a clean error rather than a traceback. A usage error -- a bad
    flag, a missing subcommand (both via argparse), or an unrecognized sector / category
    / term / lang word (a library ``ValueError``) -- returns 2.
    """
    args = _make_parser().parse_args(argv)
    run: Callable[[argparse.Namespace], int] = args.run
    try:
        return run(args)
    except FISISError as err:
        print(f"{_ERROR_PREFIX}{err}", file=sys.stderr)
        return 1
    except ValueError as err:
        # An unrecognized sector / category / term / lang word surfaces as a library
        # ValueError naming the accepted words; relay it as a clean usage error rather
        # than a raw traceback.
        print(f"{_ERROR_PREFIX}{err}", file=sys.stderr)
        return 2
    except BrokenPipeError:
        # A downstream reader closed the pipe early (`fisis data ... | head`). Redirect
        # stdout to devnull so the interpreter does not print its own BrokenPipeError
        # while flushing at exit, and report the truncated write as a failure. This is
        # the idiom from the CPython docs' note on BrokenPipeError.
        with contextlib.suppress(OSError):
            os.dup2(os.open(os.devnull, os.O_WRONLY), sys.stdout.fileno())
        return 1


def _make_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog=_PROG,
        description="Read the FISIS (Financial Supervisory Service) Open API "
                    "from the command line.")
    parser.add_argument("--version", action="version", version=f"{_PROG} {__version__}")
    commands = parser.add_subparsers(required=True)

    companies = commands.add_parser(
        "companies", help="list a sector's financial companies (companySearch)")
    companies.add_argument("--sector", required=True, metavar="SECTOR",
                           help="financial sector, by name (life) or code (H)")
    companies.add_argument("--finance-cd", default=None, metavar="CODE",
                           dest="finance_cd",
                           help="narrow to one company code (default: every company)")
    _add_lang_flag(companies)
    _add_json_flag(companies)
    companies.set_defaults(run=_run_companies)

    statistics = commands.add_parser(
        "statistics",
        help="browse a sector's statistics catalog (statisticsListSearch)")
    statistics.add_argument("--sector", required=True, metavar="SECTOR",
                            help="financial sector, by name (life) or code (H)")
    statistics.add_argument("--category", default=None, metavar="CATEGORY",
                            help="narrow to one catalog category, by name "
                                 "(financial) or code (B) (default: every category)")
    _add_lang_flag(statistics)
    _add_json_flag(statistics)
    statistics.set_defaults(run=_run_statistics)

    accounts = commands.add_parser(
        "accounts", help="list a statistic's account items (accountListSearch)")
    accounts.add_argument("list_no", help="statistic code (e.g. SH002)")
    _add_lang_flag(accounts)
    _add_json_flag(accounts)
    accounts.set_defaults(run=_run_accounts)

    data = commands.add_parser(
        "data", help="a statistic's observations (statisticsInfoSearch)")
    data.add_argument("finance_cd", help="company code (e.g. 0010001)")
    data.add_argument("list_no", help="statistic code (e.g. SH002)")
    data.add_argument("--term", required=True, metavar="TERM",
                      help="reporting interval, by name (quarterly) or code (Q)")
    data.add_argument("--start", required=True, metavar="YYYYMM",
                      help="window start month (e.g. 202403)")
    data.add_argument("--end", required=True, metavar="YYYYMM",
                      help="window end month (e.g. 202412)")
    data.add_argument("--account-cd", default=None, metavar="CODE", dest="account_cd",
                      help="narrow to one account item (default: every account)")
    data.add_argument("--table", action="store_true",
                      help="also print each value column's unit and settlement date")
    _add_lang_flag(data)
    _add_json_flag(data)
    data.set_defaults(run=_run_data)

    return parser


def _add_lang_flag(command: argparse.ArgumentParser) -> None:
    command.add_argument("--lang", default=None, metavar="LANG",
                         help="response language, kr or en (default: kr)")


def _add_json_flag(command: argparse.ArgumentParser) -> None:
    command.add_argument("--json", action="store_true",
                         help="emit JSON instead of text")


def _run_companies(args: argparse.Namespace) -> int:
    with FISIS() as fisis:
        rows = fisis.list_companies(sector=args.sector, finance_cd=args.finance_cd,
                                    **_lang_kw(args))
    print(_to_json(rows) if args.json else _render_grid(
        rows, [("finance_cd", "finance_cd"), ("name", "finance_nm"),
               ("path", "finance_path")]))
    return 0


def _run_statistics(args: argparse.Namespace) -> int:
    with FISIS() as fisis:
        rows = fisis.list_statistics(sector=args.sector, category=args.category,
                                     **_lang_kw(args))
    print(_to_json(rows) if args.json else _render_grid(
        rows, [("sector", "lrg_div_nm"), ("category", "sml_div_nm"),
               ("list_no", "list_no"), ("name", "list_nm")]))
    return 0


def _run_accounts(args: argparse.Namespace) -> int:
    with FISIS() as fisis:
        rows = fisis.list_accounts(list_no=args.list_no, **_lang_kw(args))
    print(_to_json(rows) if args.json else _render_grid(
        rows, [("list_no", "list_no"), ("statistic", "list_nm"),
               ("account_cd", "account_cd"), ("account", "account_nm")]))
    return 0


def _run_data(args: argparse.Namespace) -> int:
    account_kw = {"account_cd": args.account_cd} if args.account_cd else {}
    with FISIS() as fisis:
        data = fisis.fetch_data(
            finance_cd=args.finance_cd, list_no=args.list_no, term=args.term,
            start_month=args.start, end_month=args.end, **account_kw, **_lang_kw(args))
    # One fetch always returns the full table; --table only decides how much of it
    # to show: the column/unit legend and settlement date, or just the rows.
    if args.table:
        print(_table_to_json(data) if args.json
              else _render_table(data, args.list_no))
    else:
        print(_to_json(data.rows) if args.json
              else _render_data(data.rows, args.list_no))
    return 0


def _lang_kw(args: argparse.Namespace) -> dict[str, str]:
    """A ``{"lang": ...}`` kwarg only when --lang was given (else client default)."""
    return {"lang": args.lang} if args.lang else {}


def _to_json(rows: Sequence[Row]) -> str:
    """The full row list as indented JSON, Korean names kept unescaped."""
    return json.dumps(list(rows), ensure_ascii=False, indent=2)


def _table_to_json(data: Data) -> str:
    """A --table result as JSON: settlement date, column legend, and full rows."""
    payload = {
        "date_of_settlement": data.date_of_settlement,
        "columns": [{"name": column.name, "unit": column.unit}
                    for column in data.columns],
        "rows": list(data.rows),
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)


def _render_data(rows: Sequence[Row], list_no: str) -> str:
    """A one-line summary, then the most recent observations as an aligned text grid."""
    if not rows:
        label = f"{list_no}  " if list_no else ""
        return f"{label}(no observations)"
    head = f"{list_no}  {len(rows)} obs"
    shown = rows[-_MAX_DATA_ROWS:]
    if len(rows) > _MAX_DATA_ROWS:
        head += f"  (showing last {_MAX_DATA_ROWS}; use --json for all)"
    return f"{head}\n{_render_grid_auto(shown)}"


def _render_table(data: Data, list_no: str) -> str:
    """The --table view: a summary with settlement date, the column/unit legend,
    then the most recent observations as an aligned text grid."""
    head = f"{list_no}  {len(data.rows)} obs"
    if data.date_of_settlement:
        head += f"  settlement {data.date_of_settlement}"
    legend = "  ".join(
        f"{column.name} ({column.unit})" if column.unit else column.name
        for column in data.columns)
    parts = [head]
    if legend:
        parts.append(f"columns: {legend}")
    if not data.rows:
        parts.append("(no observations)")
    else:
        if len(data.rows) > _MAX_DATA_ROWS:
            parts[0] += f"  (showing last {_MAX_DATA_ROWS}; use --json for all)"
        parts.append(_render_grid_auto(data.rows[-_MAX_DATA_ROWS:]))
    return "\n".join(parts)


def _render_grid_auto(rows: Sequence[Row]) -> str:
    """An aligned text grid over every column present, in first-seen order."""
    columns = [(key, key) for key in _ordered_keys(rows)]
    return _render_grid(rows, columns)


def _render_grid(rows: Sequence[Row], columns: list[tuple[str, str]]) -> str:
    """Rows as an aligned text grid over ``columns`` (label, key), one row per line.

    A missing or None cell prints as ``-``; an empty result prints ``(no rows)``. A
    trailing ``(N rows)`` count follows a non-empty grid. Columns with no value in any
    row are dropped, so a fixed column list stays readable on a narrow grid.
    """
    if not rows:
        return "(no rows)"
    present = [(label, key) for label, key in columns
               if any(row.get(key) not in (None, "") for row in rows)]
    if not present:
        return f"({len(rows)} rows)"
    labels = [label for label, _ in present]
    cells = [[_cell(row.get(key)) for _, key in present] for row in rows]
    by_column = list(zip(labels, *cells, strict=True))  # each: header then its cells
    widths = [max(len(text) for text in column) for column in by_column]
    header = "  ".join(label.ljust(w) for label, w in zip(labels, widths, strict=True))
    body = "\n".join(
        "  ".join(cell.ljust(w) for cell, w in zip(row, widths, strict=True))
        for row in cells)
    return f"{header}\n{body}\n({len(rows)} rows)"


def _cell(value: object) -> str:
    return "-" if value is None else str(value)


def _ordered_keys(rows: Sequence[Row]) -> list[str]:
    keys: list[str] = []
    seen: set[str] = set()
    for row in rows:
        for key in row:
            if key not in seen:
                seen.add(key)
                keys.append(key)
    return keys


if __name__ == "__main__":
    raise SystemExit(main())
