# fisis

[![check](https://github.com/seokhoonj/fisis/actions/workflows/check.yml/badge.svg)](https://github.com/seokhoonj/fisis/actions/workflows/check.yml)
[![PyPI](https://img.shields.io/pypi/v/fisis)](https://pypi.org/project/fisis/)
[![Python](https://img.shields.io/pypi/pyversions/fisis)](https://pypi.org/project/fisis/)
[![License](https://img.shields.io/pypi/l/fisis)](https://github.com/seokhoonj/fisis/blob/main/LICENSE)

[English](https://github.com/seokhoonj/fisis/blob/main/README.en.md) | **한국어**

금융감독원 **금융통계정보시스템(FISIS)** 의 금융회사 감독통계를 읽어옵니다.

은행·생명보험·손해보험·증권·카드·저축은행·여신전문 등 금융권역별 회사 목록과
통계표·계정항목, 그리고 분기·반기·연간 시계열 통계자료를 다룹니다. FISIS가 담는 것은
금융회사가 감독당국에 제출하는 **업무보고서 기반 감독통계**입니다. 기업 공시서류를 모으는
**DART(전자공시)** 와 달리, 여기서만 구조화되어 나오는 **감독지표**가 핵심입니다.

| 권역 | 대표 감독지표 |
|---|---|
| 은행 | BIS 자기자본비율, 고정이하여신비율, 연체율, 예대금리차, ROA·ROE |
| 증권 | 영업용순자본비율(NCR), 자산건전성, 레버리지 |
| 카드 | 연체채권비율, 신용·직불·선불 카드이용실적 |
| 생명보험 | 지급여력비율(RBC/K-ICS), 13·25회 계약유지율, 경영효율지표, 신계약·보유계약·보험료수입 |
| 손해보험 | 지급여력비율, 계약유지율, 경영효율지표, 보험료수입·보유보험료(장기·자동차·일반) |

**DART와 함께** — 재무제표는 DART(전자공시)가 더 충실(주석·XBRL·연결/별도)하고, fisis는 같은
**감독 별도** 기준으로 재무제표와 감독지표를 한 소스에서 봅니다. 재무제표성 지표만 DART와
겹치고(삼성생명 별도 자산총계는 두 소스가 일치), 나머지 감독지표는 fisis 전용입니다. DART 숫자와 교차 검증하려면 [opendart-client](https://github.com/seokhoonj/opendart-client)를 함께 쓰세요.

| group | indicator | dart | fisis |
|---|---|---|---|
| 공통 | `balance_sheet_assets` · `balance_sheet_liabilities` · `income_statement` | ✅ | ✅ |
| bank | `capital_adequacy` · `delinquency` · `npl_ratio` · `productivity` | ❌ | ✅ |
| securities | `net_capital_ratio` · `leverage` | ❌ | ✅ |
| card | `delinquency` · `credit_card_usage` · `purchase_volume` | ❌ | ✅ |
| life · nonlife | `solvency` (RBC/K-ICS) · `persistency` · `efficiency` · `premium_income` · `retained_premium` (손보) | ❌ | ✅ |

자주 쓰는 지표는 **접근자**(`fisis.life.company("삼성생명").persistency(start_month="202312",
end_month="202312")`)로 바로 꺼내고, 그 밖의 통계는 통계표 코드로 조회합니다.

## 1. 설치

```bash
pip install fisis          # 코어
pip install fisis[pandas]  # + Data.to_pandas()
pip install fisis[polars]  # + Data.to_polars()
```

이 패키지는 FISIS API 키가 필요합니다. <https://fisis.fss.or.kr/> 의 오픈API 신청에서
무료로 발급받으세요(비영리는 즉시 발급). 발급하신 키를 넣는 방법은 다음과 같습니다.

**방법 1 — 코드에서 직접 넣기** (바로 한 번 써볼 때)

```python
from fisis import FISIS

fisis = FISIS(api_key="발급받은-키")
```

**방법 2 — 파일에 저장해서 계속 쓰기** (권장 — 한 번 저장하면 매번 안 넣어도 됩니다)

`~/.config/fisis/credentials.json` 파일을 만들고 아래를 넣으세요.

```json
{ "FISIS_API_KEY": "발급받은-키" }
```

그러면 이후로는 인자 없이 `FISIS()`만 써도 이 키를 자동으로 찾습니다.
탐색 순서는 생성자 인자 → 환경변수 → 파일입니다.

> 환경변수를 선호하면, macOS·Linux는 터미널에서 `export FISIS_API_KEY="발급받은-키"`,
> Windows는 PowerShell에서 `setx FISIS_API_KEY "발급받은-키"`.

## 2. 빠른 시작

```python
from fisis import FISIS

fisis = FISIS()                      # 저장한 키를 자동으로 찾음
sl = fisis.life.company("삼성생명")  # 회사 손잡이 (코드 "0010595" 도 가능)
table = sl.persistency(start_month="202312", end_month="202312")   # 13·25회 계약유지율
```

반환은 `Data` — 값은 `.rows`(`dict`의 목록), 열별 단위는 `.columns`, 결산일은
`.date_of_settlement`. 행은 표(DataFrame)로 한 줄에 바뀝니다(pandas는 필수가 아닙니다).

```python
table.rows                    # [{'base_month': ..., '말잔': ...}, ...]

# pandas / polars — 설치돼 있으면 변환 헬퍼로 바로
table.to_pandas()
table.to_polars()

# 또는 직접
import pandas as pd
pd.DataFrame(table.rows)
```

`sector`·`category`·`term`·`lang`은 열거형 멤버, 벤더 코드(`"H"`, `"Q"`), 멤버 이름
(`"life"`, `"quarterly"`) 어느 쪽으로 넣어도 됩니다.

## 3. 권역 접근자

권역(`fisis.life`, `fisis.bank`, ...)은 명시적으로 정의돼 있어 편집기에서 점(`.`)을 치면
자동완성됩니다. 권역에서 회사를 고르고, 회사 손잡이에서 지표를 부릅니다.

```text
FISIS()                                               # 5개 권역은 이름 붙은 지표, 나머지 17개는 코드로만
│  각 권역: .company("<name>" | "<code>") 로 회사(CompanyView)를 얻어 지표를 이름으로 호출
│
├─ bank
│   ├─ .capital_adequacy()                            # 자본적정성 (BIS)
│   ├─ .delinquency()  .npl_ratio()                   # 연체율 · 고정이하여신
│   ├─ .deposits()  .loans()                          # 예수금 · 대출금
│   ├─ .balance_sheet_assets()  .balance_sheet_liabilities()  .income_statement()
│   └─ ...                                            # 전체 지표는 아래 권역별 표
├─ life
│   ├─ .solvency()                                    # 지급여력 (RBC/K-ICS)
│   ├─ .persistency()  .agent_retention()             # 계약유지율 · 설계사정착률
│   ├─ .new_business()  .premium_income()             # 신계약 · 보험료수입
│   ├─ .balance_sheet_assets()  .balance_sheet_liabilities()  .income_statement()
│   └─ ...
├─ nonlife
│   ├─ .solvency()  .persistency()  .efficiency()     # 지급여력 · 유지율 · 경영효율
│   ├─ .premium_income()  .retained_premium()         # 보험료수입 · 보유보험료(장기·자동차·일반)
│   ├─ .balance_sheet_assets()  .balance_sheet_liabilities()  .income_statement()
│   └─ ...
├─ securities
│   ├─ .net_capital_ratio()  .leverage()              # NCR · 레버리지
│   ├─ .securities_trading()  .derivatives_trading()  # 증권 · 파생 거래현황
│   ├─ .balance_sheet_assets()  .balance_sheet_liabilities()  .income_statement()
│   └─ ...
├─ card
│   ├─ .delinquency()                                 # 연체채권
│   ├─ .credit_card_usage()  .purchase_volume()       # 카드이용 · 구매실적
│   ├─ .balance_sheet_assets()  .balance_sheet_liabilities()  .income_statement()
│   └─ ...
│
│  * 모든 회사 공통: .fetch(list_no=..., term=..., ...)  ->  Data(행 + 단위 + 결산일)
│
└─ (+17 sectors)                                      # foreign_bank · savings_bank · capital · futures ...
    └─ .company("<code>").fetch(list_no=...)          # 이름 붙은 지표 없이 코드로만
```

`company(key)`는 `key`가 전부 숫자면 그것을 `finance_cd`로 바로 쓰고(조회 없음), 아니면
회사 목록을 받아 `finance_nm`으로 맞춥니다(정확히 일치 우선, 없으면 유일한 부분일치).
일치가 없거나 부분일치가 둘 이상이면 후보(이름·코드)를 알려주며 `ValueError`가 납니다.
이름 매칭은 요청한 `lang`의 회사 목록을 사용합니다(기본값은 한국어). 영문 회사명은
`lang="en"`으로 찾거나, 언어와 무관한 숫자 코드를 쓰세요.

각 지표 메서드는 `start_month`·`end_month`(YYYYMM)를 받고, `term`은 그 지표가 실제로
받는 값을 기본값으로 둡니다(대부분 분기 `Q`, 유지율은 반기 `H`, 정착률은 연간 `Y`).
반환값은 `Data` 하나입니다 — 값은 `.rows`, 열별 **단위**는 `.columns`, **결산일**은
`.date_of_settlement`에 담겨 옵니다.

### 은행 `fisis.bank`

| 메서드 | 지표 | 코드 |
|---|---|---|
| `capital_adequacy` | 자본적정성 (BIS) | SA014 |
| `asset_quality` | 여신건전성 | SA015 |
| `profitability` | 수익성 (ROA·ROE·예대금리차) | SA017 |
| `liquidity` | 유동성 | SA018 |
| `productivity` | 생산성 | SA019 |
| `delinquency` | 연체율 | SA040 |
| `npl_ratio` | 고정이하여신 | SA041 |
| `deposits` `loans` | 예수금·대출금 | SA028 · SA043 |
| `balance_sheet_assets` `balance_sheet_liabilities` `income_statement` | 재무상태표(자산 / 부채·자본)·손익 | SA003 · SA004 · SA021 |

### 증권 `fisis.securities`

| 메서드 | 지표 | 코드 |
|---|---|---|
| `net_capital_ratio` | 영업용순자본비율 (NCR) | SF308 |
| `leverage` | 레버리지 비율 | SF331 |
| `asset_quality` `liquidity` `profitability` | 자산건전성·유동성·수익성 | SF311 · SF209 · SF210 |
| `securities_trading` `derivatives_trading` | 증권·파생상품 거래현황 | SF316 · SF317 |
| `balance_sheet_assets` `balance_sheet_liabilities` `income_statement` | 재무상태표(자산 / 부채·자본)·손익 | SF303 · SF304 · SF307 |

### 신용카드 `fisis.card`

| 메서드 | 지표 | 코드 |
|---|---|---|
| `capital_adequacy` `asset_quality` `profitability` `liquidity` | 자본적정성·여신건전성·수익성·유동성 | SC007 · SC008 · SC009 · SC010 |
| `delinquency` | 연체채권비율 | SC117 |
| `credit_card_usage` `debit_card_usage` `purchase_volume` | 신용·직불 카드이용실적·구매실적 | SC013 · SC014 · SC016 |
| `balance_sheet_assets` `balance_sheet_liabilities` `income_statement` | 재무상태표(자산 / 부채·자본)·손익 | SC103 · SC104 · SC218 |

### 생명보험 `fisis.life` / 손해보험 `fisis.nonlife`

| 메서드 | 지표 | 코드(생·손보) |
|---|---|---|
| `solvency` | 지급여력비율 (RBC/K-ICS) | SH021 / SI021 |
| `efficiency` | 경영효율지표 | SH114 / SI114 |
| `persistency` | 계약유지율 (13·25회) | SH025 / SI025 |
| `agent_retention` | 설계사정착률 | SH022 / SI022 |
| `asset_quality` | 자산건전성 | SH112 / SI112 |
| `liquidity` | 유동성 | SH115 / SI115 |
| `balance_sheet_assets` | 요약재무상태표 (자산) | SH150 / SI146 |
| `balance_sheet_liabilities` | 요약재무상태표 (부채·자본) | SH151 / SI147 |
| `income_statement` | 요약손익계산서 | SH154 / SI150 |
| `new_business` `in_force` `premium_income` | 신계약·보유계약·보험료수입 | SH160 · SH161 · SH166 (생보) |
| `premium_income` `retained_premium` | 보험료수입(수납형태)·보유보험료(장기·자동차·일반) | SI027 · SI138 (손보) |

권역 속성 이름: `bank`, `foreign_bank`, `life`, `nonlife`, `securities`, `futures`,
`asset_management`, `investment_advisory`, `merchant_bank`, `card`, `leasing`,
`capital`, `new_tech`, `savings_bank`, `credit_union`, `nonghyup`, `suhyup`,
`forestry_coop`, `real_estate_trust`, `holding`, `trust_common`, `derivatives_common`.

## 4. 평면 메서드 — 탐색 흐름

이름 붙은 지표가 없는 통계표나 다른 권역은, 코드를 한 단계씩 찾아 내려갑니다. FISIS는
시계열을 **회사(`finance_cd`) + 통계표(`list_no`) + 계정항목(`account_cd`)** 으로
식별합니다.

```python
from fisis import FISIS, Sector, Term

fisis = FISIS()

companies  = fisis.list_companies(sector=Sector.LIFE)                 # 회사 -> finance_cd
statistics = fisis.list_statistics(sector=Sector.LIFE)                # 통계표 -> list_no
accounts   = fisis.list_accounts(list_no=statistics[0]["list_no"])    # 계정항목 -> account_cd

table = fisis.fetch_data(                                             # 통계자료 (YYYYMM, 최대 40분기)
    finance_cd=companies[0]["finance_cd"],
    list_no=statistics[0]["list_no"],
    term=Term.QUARTERLY, start_month="202403", end_month="202412",
)
```

FISIS 원본 응답의 값 열은 `a`·`b`·`c`·`d` 같은 무의미한 이름이지만, `fetch_data`가 응답의
컬럼 설명으로 자동 해석해 사람이 읽는 이름(예: `말잔`·`평잔`)으로 돌려줍니다. 반환값은
행에 더해 열별 이름·단위(`Column`)와 결산일을 담은 `Data` 하나입니다.

```python
table.rows                                   # [{'base_month': '202403', '말잔': ...}, ...]
[(c.name, c.unit) for c in table.columns]    # 예: [('금액', '원'), ('구성비', '%')]
table.date_of_settlement                     # 예: '12/31'

# 행은 pandas·polars가 바로 먹는 records 형식입니다(값은 FISIS가 주는 대로 문자열 —
# 필요한 열만 캐스팅하세요). 변환 헬퍼는 해당 라이브러리가 설치돼 있을 때 씁니다:
table.to_polars()                            # polars.DataFrame
table.to_pandas()                            # pandas.DataFrame
```

## 5. 커맨드라인

설치하면 `fisis` 명령이 함께 깔립니다.

```sh
fisis companies --sector life                                          # 권역의 회사 목록
fisis statistics --sector life --category key_metrics                  # 통계표 목록
fisis accounts SH025                                                   # 통계표의 계정항목
fisis data 0010595 SH025 --term H --start 202312 --end 202312          # 통계자료 (유지율)
fisis data 0010595 SH150 --term Q --start 202403 --end 202403 --table  # + 열별 단위·결산일
```

`--json`으로 전체 결과를, `fisis <명령> --help`로 옵션을 봅니다.

## 6. AI 코딩 에이전트에서 사용

- 이 저장소는 Claude Code·Codex용 플러그인 마켓플레이스도 겸합니다.
- `companies`·`statistics`·`accounts`·`data` 스킬을 제공하며, 각각 같은 이름의 `fisis` 명령에
  대응합니다.
- 먼저 패키지를 설치하고 API 키를 설정하세요.

### 6.1 Claude Code

Claude Code 채팅창에서 마켓플레이스를 추가하고 설치합니다:

```
/plugin marketplace add seokhoonj/fisis
/plugin install fisis@fisis
```

설치 후 평범하게 물어보거나("생명보험사 목록 보여줘", "삼성생명 유지율 가져와"), 스킬을 직접
부르세요 — `/fisis:companies --sector life`, `/fisis:data 0010595 SH025 --term H ...`.

### 6.2 Codex

터미널에서 마켓플레이스를 추가하고 설치합니다:

```
codex plugin marketplace add seokhoonj/fisis
codex plugin add fisis@fisis
```

### 6.3 플러그인 없이 (symlink)

플러그인으로 설치하지 않고 쓰려면, 스킬을 각 에이전트의 스킬 디렉터리에 symlink합니다.

```sh
ln -s "$PWD/plugins/fisis/skills/data" ~/.claude/skills/data   # Claude Code → /data
ln -s "$PWD/plugins/fisis/skills/data" ~/.codex/skills/data    # Codex → $fisis:data
```

Claude Code는 바로 인식하고, Codex는 재시작해야 로딩됩니다.

## 7. 에러

| 예외 | 언제 |
|---|---|
| `FISISConfigError` | API 키를 찾지 못했을 때 |
| `FISISAuthError` | FISIS가 키를 거부했을 때 (미등록·중지·삭제·샘플 키) |
| `FISISRateLimitError` | 일일검색 허용횟수 초과(err 020) 또는 HTTP 429 |
| `FISISResponseError` | FISIS가 에러를 돌려줬을 때 (`.code`·`.message`, 예: 40분기 초과 = 103) |
| `FISISNetworkError` | 네트워크가 끝내 안 됐을 때 |

- 모든 예외는 `FISISError`의 하위입니다.
- 조회 결과가 없으면 에러가 아니라 빈 결과로 옵니다 (카탈로그 조회는 빈 목록, `fetch_data`·지표 메서드는 행이 빈 `Data`).
- 여러 회사·통계표를 잇달아 읽을 때는 `FISIS(delay_seconds=0.3)`으로 간격을 둡니다.
- 에러 메시지와 표현에는 API 키가 절대 담기지 않습니다.

## 8. 라이선스

코드: MIT © Seokhoon Joo.

데이터: FISIS 통계정보의 출처는 금융감독원 금융통계정보시스템이며, 국가승인통계가 아닌
업무보고서 기반 자료입니다. 데이터 이용 시 FISIS 이용약관과 출처 표기를 따르세요.
