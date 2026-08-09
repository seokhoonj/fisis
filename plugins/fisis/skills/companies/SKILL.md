---
name: companies
description: "List a financial sector's companies from FISIS and their finance_cd codes. Holds no logic of its own -- it calls the fisis package's CLI (`fisis companies`) and shows the result to the user. Use this to turn a sector (life insurers, banks) into the company code the data skill needs. Trigger phrases: FISIS 회사 목록, 금융회사 코드, 보험사 목록, 은행 목록, 생보사 코드 찾아, list FISIS companies, financial company code, finance_cd for, banks in FISIS."
---

# fisis -- companies (financial companies in a sector)

Discover the company code a FISIS statistic is keyed by. FISIS identifies a time series by a
company (`finance_cd`), a statistic (`list_no`), and optionally an account item
(`account_cd`); `fisis companies` lists one sector's companies so you can pick the
`finance_cd`. The listing and parsing live in the fisis package (on PyPI); this skill is a
thin wrapper that calls its CLI and relays the result. A rejected key or a vendor error comes
back as a one-line `fisis: <message>` -- relay it as-is rather than throwing a stack trace at
the user. (A missing or malformed argument is caught earlier by argparse, which prints usage
and exits 2.)

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
fisis companies --sector <SECTOR> [--finance-cd CODE] [--lang kr|en] [--json]
```

- `--sector` (required) -- the financial sector, by name (`life`, `bank`, `nonlife`,
  `securities`, ...) or by the vendor one-letter code (`H`, `A`, `I`, `F`, ...).
- `--finance-cd` -- narrow to one company code; omit to list every company in the sector.
- `--lang kr|en` -- response language (default: kr).
- `--json` -- the full result as JSON instead of the aligned text table.

## Procedure

1. **Run.** Pick the sector and list its companies:
   ```bash
   fisis companies --sector life
   ```
2. **Relay the result.** Show the CLI's stdout (aligned columns + row count). Each row's
   `finance_cd` is what the **data** skill takes as the company code.
3. **Error handling.** When the CLI exits non-zero, relay the one-line `fisis: <message>`
   from stderr as-is. Common ones:
   - `command not found: fisis` -> not installed; point the user at `pipx install fisis`.
   - `no FISIS API key ...` -> no key was found (env var and config file both empty).
   - `[010] ...` / `[011] ...` -> the key was rejected (unregistered/suspended).
   - `[020] ...` -> the daily search quota is exhausted; it resets with the calendar day.
   An empty result (no rows) is not an error.

## What this skill does not do

- It does not re-implement listing or parsing (the package does); it always calls the CLI.
- It lists companies only -- for a sector's statistics catalog use **statistics**, for a
  statistic's account items use **accounts**, and to fetch the numbers use **data**.
