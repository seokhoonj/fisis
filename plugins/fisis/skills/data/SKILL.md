---
name: data
description: "Fetch a FISIS statistic's observations as a time series, optionally with each value column's unit and the settlement date. Holds no logic of its own -- it calls the fisis package's CLI (`fisis data`) and shows the result to the user. Needs a company code and a statistic code (find them with the companies and statistics skills). Trigger phrases: FISIS 통계자료 가져와, 보험사 지표, 은행 통계, 금융회사 시계열, 재무상태표 데이터, fetch FISIS statistic, financial-institution time series, insurer metrics, bank statistics."
---

# fisis -- statistic observations (time series)

Take a FISIS company code and statistic code and print that statistic's observations. FISIS
keys a time series by a company (`finance_cd`) and a statistic (`list_no`), optionally
narrowed to one account item (`account_cd`). The fetching and parsing live in the fisis
package (on PyPI); this skill is a thin wrapper that calls its CLI and relays the result. A
rejected key or a vendor error comes back as a one-line `fisis: <message>` -- relay it as-is
rather than throwing a stack trace at the user. (A missing or malformed argument is caught
earlier by argparse, which prints usage and exits 2.)

## Prerequisite

This plugin calls the `fisis` CLI, so the package must be installed and an API key set:

```
pipx install fisis            # or: pip install fisis
export FISIS_API_KEY=...       # a free key from https://fisis.fss.or.kr/openapi/
```

That puts the `fisis` command on PATH. The key can also be stored in
`~/.config/fisis/credentials.json` as `{"FISIS_API_KEY": "..."}`. Without a key the CLI exits
with `fisis: no FISIS API key ...`; relay that and point the user at the FISIS site.

**Never print, log, quote, or echo the `FISIS_API_KEY` value itself** -- confirm only that a key is set.

## Running

```
fisis data <FINANCE_CD> <LIST_NO> --term Y|H|Q --start YYYYMM --end YYYYMM [--account-cd CODE] [--table] [--lang kr|en] [--json]
```

Options (`fisis data --help` is the source of truth):
- `<FINANCE_CD>` -- the company code, from the **companies** skill (e.g. `0010001`).
- `<LIST_NO>` -- the statistic code, from the **statistics** skill (e.g. `SH002`).
- `--term` (required) -- reporting interval, by name (`annual`, `half_yearly`, `quarterly`)
  or by code (`Y`, `H`, `Q`).
- `--start` / `--end` (required) -- window bounds as YYYYMM months (`202403`). The window
  cannot span more than 40 quarters (the vendor refuses a longer one with `[103]`).
- `--account-cd` -- narrow to one account item, from the **accounts** skill; omit for every
  account of the statistic.
- `--table` -- also print each value column's unit and the fiscal settlement date (reach for
  this when the numbers mix units like `원` and `%`).
- `--lang kr|en` -- response language (default: kr).
- `--json` -- the full result as JSON instead of the text summary (the text view caps the
  rows shown; `--json` always carries them all).

## Procedure

1. **Get the codes.** You need a `finance_cd` and a `list_no`. If the user gave a concept
   ("생보사 자산총계") but no codes, use the **companies** and **statistics** skills first
   (and **accounts** for a specific line item), then come back here.
2. **Run.** Set the interval with `--term` and the window with `--start`/`--end`; add
   `--account-cd` to focus one account, `--table` for units + settlement date, and `--json`
   when the user wants the whole result.
   ```bash
   fisis data 0010001 SH002 --term Q --start 202403 --end 202412 --table
   ```
3. **Relay the result.** Show the CLI's stdout. You may trim a long result, but keep the
   summary line.
4. **Error handling.** When the CLI exits non-zero, relay the one-line `fisis: <message>`
   from stderr as-is. Common ones:
   - `command not found: fisis` -> not installed; point the user at `pipx install fisis`.
   - `no FISIS API key ...` -> no key was found (env var and config file both empty).
   - `[100] ...` -> a required parameter is missing; `[101] ...` -> an invalid value.
   - `[102] ...` -> start month is after end month; `[103] ...` -> the window spans more
     than 40 quarters (shorten it).
   - `[020] ...` -> the daily search quota is exhausted; it resets with the calendar day.
   An empty result (no rows) is not an error.

## What this skill does not do

- It does not re-implement fetching or parsing (the package does); it always calls the CLI.
- It is the observation data only -- to discover a company code use **companies**, a
  statistic code use **statistics**, and an account code use **accounts**.
