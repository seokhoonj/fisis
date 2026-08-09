---
name: statistics
description: "Browse a financial sector's statistics catalog from FISIS and its list_no codes. Holds no logic of its own -- it calls the fisis package's CLI (`fisis statistics`) and shows the result to the user. Use this to turn a sector into the statistic code the accounts and data skills need. Trigger phrases: FISIS 통계 목록, 통계표 코드, list_no 찾아, 재무현황 통계, 주요경영지표 목록, browse FISIS statistics, statistics catalog, list_no for, financial-statistics tables."
---

# fisis -- statistics (a sector's statistics catalog)

Discover the statistic code a FISIS series is stored under. FISIS keys a time series by a
company (`finance_cd`), a statistic (`list_no`), and optionally an account item
(`account_cd`); `fisis statistics` browses one sector's statistics catalog so you can pick the
`list_no`. The listing and parsing live in the fisis package (on PyPI); this skill is a thin
wrapper that calls its CLI and relays the result. A rejected key or a vendor error comes back
as a one-line `fisis: <message>` -- relay it as-is rather than throwing a stack trace at the
user. (A missing or malformed argument is caught earlier by argparse, which prints usage and
exits 2.)

## Prerequisite

This plugin calls the `fisis` CLI, so the package must be installed and an API key set:

```
pipx install fisis            # or: pip install fisis
export FISIS_API_KEY=...       # a free key from https://fisis.fss.or.kr/openapi/
```

The key can also be stored in `~/.config/fisis/credentials.json` as
`{"FISIS_API_KEY": "..."}`. Without a key the CLI exits with `fisis: no FISIS API key ...`;
relay that and point the user at the FISIS site.

**Never print, log, quote, or echo the `FISIS_API_KEY` value itself** -- confirm only that a key is set.

## Running

```
fisis statistics --sector <SECTOR> [--category CATEGORY] [--lang kr|en] [--json]
```

- `--sector` (required) -- the financial sector, by name (`life`, `bank`, ...) or by the
  vendor one-letter code (`H`, `A`, ...); the same codes the **companies** skill takes.
- `--category` -- narrow to one catalog category, by name (`general`, `financial`,
  `key_metrics`, `operations`, `press`) or by code (`A`, `B`, `C`, `D`, `P`). A few sectors
  file tables under a sector-specific one-letter code (real-estate trust uses `E`), which
  passes through verbatim. Omit to list every category.
- `--lang kr|en` -- response language (default: kr).
- `--json` -- the full result as JSON instead of the aligned text table.

## Procedure

1. **Run.** Pick the sector (and optionally a category) and browse its catalog:
   ```bash
   fisis statistics --sector life --category financial
   ```
2. **Relay the result.** Show the CLI's stdout (aligned columns + row count). Each row's
   `list_no` is what the **accounts** and **data** skills take as the statistic code.
3. **Error handling.** When the CLI exits non-zero, relay the one-line `fisis: <message>`
   from stderr as-is. Common ones:
   - `command not found: fisis` -> not installed; point the user at `pipx install fisis`.
   - `no FISIS API key ...` -> no key was found (env var and config file both empty).
   - `[020] ...` -> the daily search quota is exhausted; it resets with the calendar day.
   - other `[code] ...` -> a vendor error (often a wrong sector or category code).
   An empty result (no rows) is not an error.

## What this skill does not do

- It does not re-implement the catalog or parsing (the package does); it always calls the CLI.
- It browses statistics only -- for a sector's companies use **companies**, for a statistic's
  account items use **accounts**, and to fetch the numbers use **data**.
