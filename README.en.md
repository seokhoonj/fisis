# fisis

[![check](https://github.com/seokhoonj/fisis/actions/workflows/check.yml/badge.svg)](https://github.com/seokhoonj/fisis/actions/workflows/check.yml)
[![PyPI](https://img.shields.io/pypi/v/fisis)](https://pypi.org/project/fisis/)
[![Python](https://img.shields.io/pypi/pyversions/fisis)](https://pypi.org/project/fisis/)
[![License](https://img.shields.io/pypi/l/fisis)](https://github.com/seokhoonj/fisis/blob/main/LICENSE)

**English** | [한국어](https://github.com/seokhoonj/fisis/blob/main/README.md)

Read financial-institution statistics from Korea's **FISIS** (the Financial Supervisory
Service's Financial Statistics Information System).

Banks, life insurers, non-life insurers, securities firms, credit-card companies, savings
banks, credit-specialized firms and more — their company lists, statistics catalog and
account items, and quarterly / half-yearly / annual time series. What FISIS holds is
**supervisory statistics** compiled from the business reports institutions file with the
regulator. Unlike **DART** (the electronic *disclosure* system), its value is the
**supervisory ratios** that appear here in structured form and almost nowhere else.

| Sector | Headline supervisory metrics |
|---|---|
| Bank | BIS capital ratio, substandard-and-below loan ratio, delinquency, deposit–loan spread, ROA·ROE |
| Securities | net capital ratio (NCR), asset soundness, leverage |
| Card | delinquent-receivable ratio, credit / debit / prepaid card usage |
| Life insurance | solvency (RBC/K-ICS), 13- & 25-month persistency, management-efficiency ratios, new business · in-force · premium income |
| Non-life insurance | solvency, persistency, management-efficiency ratios, premium income · retained premium (long-term / auto / general) |

**With DART** — financial statements are richer on DART (the disclosure system: notes, XBRL,
consolidated / separate); fisis reads them on the same **supervisory separate** basis
alongside the supervisory ratios, from one source. Only the financial-statement metrics
overlap with DART (Samsung Life's separate total assets match across both sources); the
rest are fisis-only. Cross-check the DART figures with [opendart-client](https://github.com/seokhoonj/opendart-client).

| group | indicator | dart | fisis |
|---|---|---|---|
| common | `balance_sheet_assets` · `balance_sheet_liabilities` · `income_statement` | ✅ | ✅ |
| bank | `capital_adequacy` · `delinquency` · `npl_ratio` · `productivity` | ❌ | ✅ |
| securities | `net_capital_ratio` · `leverage` | ❌ | ✅ |
| card | `delinquency` · `credit_card_usage` · `purchase_volume` | ❌ | ✅ |
| life · nonlife | `solvency` (RBC/K-ICS) · `persistency` · `efficiency` · `premium_income` · `retained_premium` (nonlife) | ❌ | ✅ |

Frequently-used figures are reached through an **accessor**
(`fisis.life.company("Samsung Life", lang="en").persistency(start_month="202312",
end_month="202312")`); everything else by statistics code.

## 1. Install

```bash
pip install fisis          # core
pip install fisis[pandas]  # + Data.to_pandas()
pip install fisis[polars]  # + Data.to_polars()
```

fisis needs a FISIS API key. Get one free at <https://fisis.fss.or.kr/> (a non-profit key
is issued instantly). Supply the key as follows.

**Option 1 — pass it in code** (to try it once)

```python
from fisis import FISIS

fisis = FISIS(api_key="your-key")
```

**Option 2 — save it to a file** (recommended — save once, never pass it again)

Create `~/.config/fisis/credentials.json` with:

```json
{ "FISIS_API_KEY": "your-key" }
```

After that, a bare `FISIS()` finds this key on its own. The search order is
constructor argument → environment variable → file.

> Prefer an environment variable? On macOS/Linux, in the terminal:
> `export FISIS_API_KEY="your-key"`. On Windows, in PowerShell:
> `setx FISIS_API_KEY "your-key"`.

## 2. Quickstart

```python
from fisis import FISIS

fisis = FISIS()                                     # finds your saved key
sl = fisis.life.company("Samsung Life", lang="en")  # a company handle (or the code "0010595")
data = sl.persistency(start_month="202312", end_month="202312")   # 13- & 25-month persistency
```

The return is a `Data` — the values on `.rows` (a `list` of `dict`), per-column units on
`.columns`, the settlement date on `.date_of_settlement`. The rows are a table (DataFrame)
one line away (pandas optional).

```python
data.rows                    # [{'base_month': ..., 'account_nm': '13회차 계약유지율', '비율': ...}, ...]

# pandas / polars -- the converters, when the library is installed
data.to_pandas()
data.to_polars()

# or build it yourself
import pandas as pd
pd.DataFrame(data.rows)
```

`sector`, `category`, `term` and `lang` accept the enum member, the vendor code (`"H"`,
`"Q"`), or the member name (`"life"`, `"quarterly"`) — whichever you pass.

## 3. Sector accessors

Sectors (`fisis.life`, `fisis.bank`, ...) are explicit attributes, so an editor autocompletes them
when you type `.`. Pick a company on a sector, then call a statistic on the company handle.

```text
FISIS()                                               # 5 sectors have named statistics; the other 17 are code-only
│  each sector: .company("<name>" | "<code>") gives a company handle (CompanyView) whose statistics are named
│
├─ bank
│   ├─ .capital_adequacy()                            # capital adequacy (BIS)
│   ├─ .delinquency()  .npl_ratio()                   # delinquency · non-performing loans
│   ├─ .deposits()  .loans()                          # deposits · loans
│   ├─ .balance_sheet_assets()                        # balance sheet (assets)
│   ├─ .balance_sheet_liabilities()                   # balance sheet (liabilities & equity)
│   ├─ .income_statement()                            # income
│   └─ ...                                            # full metric list in the tables below
├─ life
│   ├─ .solvency()                                    # solvency (RBC/K-ICS)
│   ├─ .persistency()  .agent_retention()             # persistency · agent retention
│   ├─ .new_business()  .premium_income()             # new business · premium income
│   ├─ .balance_sheet_assets()                        # balance sheet (assets)
│   ├─ .balance_sheet_liabilities()                   # balance sheet (liabilities & equity)
│   ├─ .income_statement()                            # income
│   └─ ...
├─ nonlife
│   ├─ .solvency()  .persistency()  .efficiency()     # solvency · persistency · efficiency
│   ├─ .premium_income()  .retained_premium()         # premium income · retained premium (long-term/auto/general)
│   ├─ .balance_sheet_assets()                        # balance sheet (assets)
│   ├─ .balance_sheet_liabilities()                   # balance sheet (liabilities & equity)
│   ├─ .income_statement()                            # income
│   └─ ...
├─ securities
│   ├─ .net_capital_ratio()  .leverage()              # NCR · leverage
│   ├─ .securities_trading()  .derivatives_trading()  # securities · derivatives trading
│   ├─ .balance_sheet_assets()                        # balance sheet (assets)
│   ├─ .balance_sheet_liabilities()                   # balance sheet (liabilities & equity)
│   ├─ .income_statement()                            # income
│   └─ ...
├─ card
│   ├─ .delinquency()                                 # delinquent receivables
│   ├─ .credit_card_usage()  .purchase_volume()       # card usage · purchase volume
│   ├─ .balance_sheet_assets()                        # balance sheet (assets)
│   ├─ .balance_sheet_liabilities()                   # balance sheet (liabilities & equity)
│   ├─ .income_statement()                            # income
│   └─ ...
│
│  * every handle also has: .fetch(list_no=..., term=..., ...)  ->  Data(rows + units + settlement)
│
└─ (+17 sectors)                                      # foreign_bank · savings_bank · capital · futures ...
    └─ .company("<code>").fetch(list_no=...)          # by code only, no named statistics
```

`company(key)` takes an all-digit `key` as the `finance_cd` directly (no lookup);
otherwise it fetches the sector's companies and matches on `finance_nm` (exact match
first, else a unique substring). No match, or a substring matching more than one company,
raises `ValueError` naming the candidates (name and code). The match reads the sector's
company list in the requested `lang` (Korean by default), so pass `lang="en"` to match an
English name, or use the numeric code, which is language-independent.

Each statistic method takes `start_month` / `end_month` (YYYYMM); its `term` defaults to a
value the statistic actually accepts (mostly quarterly `Q`; persistency half-yearly `H`;
agent retention annual `Y`). Each returns a `Data` -- the values on `.rows`, per-column
**units** on `.columns`, the **settlement date** on `.date_of_settlement`.

### Bank `fisis.bank`

| Method | Metric | Code |
|---|---|---|
| `capital_adequacy` | capital adequacy (BIS) | SA014 |
| `asset_quality` | loan soundness | SA015 |
| `profitability` | profitability (ROA·ROE·spread) | SA017 |
| `liquidity` | liquidity | SA018 |
| `productivity` | productivity | SA019 |
| `delinquency` | delinquency ratio | SA040 |
| `npl_ratio` | substandard-and-below loans | SA041 |
| `deposits` `loans` | deposits · loans | SA028 · SA043 |
| `balance_sheet_assets` `balance_sheet_liabilities` `income_statement` | balance sheet (assets / liabilities & equity) · income | SA003 · SA004 · SA021 |

### Securities `fisis.securities`

| Method | Metric | Code |
|---|---|---|
| `net_capital_ratio` | net capital ratio (NCR) | SF308 |
| `leverage` | leverage ratio | SF331 |
| `asset_quality` `liquidity` `profitability` | asset soundness · liquidity · profitability | SF311 · SF209 · SF210 |
| `securities_trading` `derivatives_trading` | securities · derivatives trading | SF316 · SF317 |
| `balance_sheet_assets` `balance_sheet_liabilities` `income_statement` | balance sheet (assets / liabilities & equity) · income | SF303 · SF304 · SF307 |

### Card `fisis.card`

| Method | Metric | Code |
|---|---|---|
| `capital_adequacy` `asset_quality` `profitability` `liquidity` | capital adequacy · loan soundness · profitability · liquidity | SC007 · SC008 · SC009 · SC010 |
| `delinquency` | delinquent-receivable ratio | SC117 |
| `credit_card_usage` `debit_card_usage` `purchase_volume` | credit / debit card usage · purchase volume | SC013 · SC014 · SC016 |
| `balance_sheet_assets` `balance_sheet_liabilities` `income_statement` | balance sheet (assets / liabilities & equity) · income | SC103 · SC104 · SC218 |

### Life `fisis.life` / Non-life `fisis.nonlife`

| Method | Metric | Code (life / non-life) |
|---|---|---|
| `solvency` | solvency ratio (RBC/K-ICS) | SH021 / SI021 |
| `efficiency` | management-efficiency ratios | SH114 / SI114 |
| `persistency` | contract persistency (13-/25-month) | SH025 / SI025 |
| `agent_retention` | agent retention rate | SH022 / SI022 |
| `asset_quality` | asset soundness | SH112 / SI112 |
| `liquidity` | liquidity | SH115 / SI115 |
| `balance_sheet_assets` | summary balance sheet (assets) | SH150 / SI146 |
| `balance_sheet_liabilities` | summary balance sheet (liabilities & equity) | SH151 / SI147 |
| `income_statement` | summary income statement | SH154 / SI150 |
| `new_business` `in_force` `premium_income` | new business · in-force · premium income | SH160 · SH161 · SH166 (life) |
| `premium_income` `retained_premium` | premium income (by collection form) · retained premium (long-term / auto / general) | SI027 · SI138 (nonlife) |

Sector attributes — **the 5 with named statistics**: `bank` `life` `nonlife` `securities` `card`.
**the 17 reached by code only**: `foreign_bank` `futures` `asset_management` `investment_advisory`
`merchant_bank` `leasing` `capital` `new_tech` `savings_bank` `credit_union` `nonghyup`
`suhyup` `forestry_coop` `real_estate_trust` `holding` `trust_common` `derivatives_common`.

## 4. Flat methods — the discovery flow

For statistics without a named method, or another sector, find the codes step by step.
FISIS identifies a time series by a **company (`finance_cd`) + statistic (`list_no`) +
account item (`account_cd`)**.

```python
from fisis import FISIS, Sector, Term

fisis = FISIS()

companies  = fisis.list_companies(sector=Sector.LIFE)                 # company -> finance_cd
statistics = fisis.list_statistics(sector=Sector.LIFE)                # statistic -> list_no
accounts   = fisis.list_accounts(list_no=statistics[0]["list_no"])    # account item -> account_cd

data = fisis.fetch_data(                                              # observations (YYYYMM, max 40 quarters)
    finance_cd=companies[0]["finance_cd"],
    list_no=statistics[0]["list_no"],
    term=Term.QUARTERLY, start_month="202403", end_month="202412",
)
```

FISIS ships each observation's value columns under opaque names (`a`, `b`, `c`, `d`);
`fetch_data` resolves them to their human names (e.g. `말잔` / `평잔`) from the response
legend. It returns a single `Data` -- the rows plus the per-column name/unit (`Column`)
and the settlement date.

```python
data.rows                                   # [{'base_month': '202403', '말잔': ...}, ...]
[(c.name, c.unit) for c in data.columns]    # e.g. [('금액', '원'), ('구성비', '%')]
data.date_of_settlement                     # e.g. '12/31'

# The rows are the records format pandas / polars consume directly (values arrive as
# strings, as FISIS sends them -- cast the columns you need). The converters are there
# when the frame library is installed:
data.to_polars()                            # polars.DataFrame
data.to_pandas()                            # pandas.DataFrame
```

## 5. Command line

Installing fisis also installs the `fisis` command.

```sh
fisis companies --sector life                                          # a sector's companies
fisis statistics --sector life --category key_metrics                  # its statistics catalog
fisis accounts SH025                                                   # a statistic's account items
fisis data 0010595 SH025 --term H --start 202312 --end 202312          # observations (persistency)
fisis data 0010595 SH150 --term Q --start 202403 --end 202403 --table  # + per-column units & settlement
```

`--json` prints the full result; `fisis <command> --help` lists the options.

## 6. Use from AI coding agents

- This repo doubles as a plugin marketplace for Claude Code and Codex.
- It provides `companies`, `statistics`, `accounts`, and `data` skills, each named after the
  matching `fisis` command.
- Install the package and set an API key first.

### 6.1 Claude Code

In the Claude Code chat, add the marketplace and install:

```
/plugin marketplace add seokhoonj/fisis
/plugin install fisis@fisis
```

Then just ask ("list the life insurers", "fetch Samsung Life's persistency"), or call a
skill directly -- `/fisis:companies --sector life`, `/fisis:data 0010595 SH025 --term H ...`.

### 6.2 Codex

In your terminal, add the marketplace and install:

```
codex plugin marketplace add seokhoonj/fisis
codex plugin add fisis@fisis
```

### 6.3 Without the plugin (symlink)

To use a skill without installing the plugin, symlink it into the agent's skills directory.

```sh
ln -s "$PWD/plugins/fisis/skills/data" ~/.claude/skills/data   # Claude Code -> /data
ln -s "$PWD/plugins/fisis/skills/data" ~/.codex/skills/data    # Codex -> $fisis:data
```

Claude Code picks it up immediately; Codex needs a restart to load it.

## 7. Errors

| Error | When |
|---|---|
| `FISISConfigError` | No usable API key was found |
| `FISISAuthError` | FISIS rejected the key (unregistered / suspended / deleted / sample) |
| `FISISRateLimitError` | Daily search quota exceeded (err 020) or HTTP 429 |
| `FISISResponseError` | FISIS returned another error (`.code` · `.message`, e.g. 103 = span over 40 quarters) |
| `FISISNetworkError` | The request never completed |

- Every error derives from `FISISError`.
- A query with no data returns an empty result, not an error (a catalog query an empty list; `fetch_data` and the statistic methods a `Data` with no rows).
- For heavy use, `FISIS(delay_seconds=0.3)` paces requests under the limit.
- Error messages and representations never include the API key.

## 8. License

Code: MIT © Seokhoon Joo.

Data: FISIS statistics are sourced from the Financial Supervisory Service's Financial Statistics
Information System — business-report data, not government-approved official statistics.
When using the data, follow the FISIS terms of use and its source-attribution requirement.
