---
name: accounts
description: "List a FISIS statistic's account items and their account_cd codes. Holds no logic of its own -- it calls the fisis package's CLI (`fisis accounts`) and shows the result to the user. Use this to find the account_cd that narrows a data fetch to one line item. Trigger phrases: FISIS 계정 목록, 계정 항목 코드, account_cd 찾아, 자산총계 계정, 통계표 계정 항목, list FISIS accounts, account items for, account_cd for, line items of a statistic."
---

# fisis -- accounts (a statistic's account items)

Discover the account code that narrows a FISIS fetch to one line item. FISIS keys a time
series by a company (`finance_cd`), a statistic (`list_no`), and optionally an account item
(`account_cd`); `fisis accounts` lists one statistic's account items so you can pick the
`account_cd`. The listing and parsing live in the fisis package (on PyPI); this skill is a
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

The key can also be stored in `~/.config/fisis/credentials.json` as
`{"FISIS_API_KEY": "..."}`. Without a key the CLI exits with `fisis: no FISIS API key ...`;
relay that and point the user at the FISIS site.

**Never print, log, quote, or echo the `FISIS_API_KEY` value itself** -- confirm only that a key is set.

## Running

```
fisis accounts <LIST_NO> [--lang kr|en] [--json]
```

- `<LIST_NO>` (required) -- the statistic code, from the **statistics** skill (e.g. `SH002`).
- `--lang kr|en` -- response language (default: kr).
- `--json` -- the full result as JSON instead of the aligned text table.

## Procedure

1. **Get the code.** You need a `list_no`. If the user gave a concept ("재무상태표") but no
   code, use the **statistics** skill first, then come back here.
2. **Run.**
   ```bash
   fisis accounts SH002
   ```
3. **Relay the result.** Show the CLI's stdout (aligned columns + row count). Each row's
   `account_cd` is what the **data** skill takes as `--account-cd` to narrow to one account.
4. **Error handling.** When the CLI exits non-zero, relay the one-line `fisis: <message>`
   from stderr as-is. Common ones:
   - `command not found: fisis` -> not installed; point the user at `pipx install fisis`.
   - `no FISIS API key ...` -> no key was found (env var and config file both empty).
   - `[020] ...` -> the daily search quota is exhausted; it resets with the calendar day.
   - other `[code] ...` -> a vendor error (often a wrong statistic code).
   An empty result (no rows) is not an error.

## What this skill does not do

- It does not re-implement listing or parsing (the package does); it always calls the CLI.
- It lists account items only -- for a sector's companies use **companies**, for its
  statistics catalog use **statistics**, and to fetch the numbers use **data**.
