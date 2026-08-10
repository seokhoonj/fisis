"""Sector-specific company views with headline statistics reachable by name.

Each class is a :class:`~fisis._accessor.CompanyView` for one financial sector,
adding explicit methods that name a headline FISIS statistic instead of its code
-- ``f.life.company("삼성생명").persistency(...)`` in place of
``.fetch(list_no="SH025", term="H", ...)``. Every method is a thin wrapper over
:meth:`~fisis._accessor.CompanyView.fetch`, so it returns the same
:class:`~fisis.types.Data` (its ``rows`` for the values, ``columns`` for each
value column's unit, ``date_of_settlement`` for the fiscal date) and no request
logic is duplicated here.

The ``list_no`` code and default ``term`` on each method were confirmed against
live FISIS calls (a term the statistic actually accepts).

The layout mirrors the FISIS statistics catalog (one class per sector, methods
named for the sector's published tables) rather than a semantic regrouping, so a
new headline table lands in the obvious class.
"""

from __future__ import annotations

from ._accessor import CompanyView
from .types import Data, Lang, Term


class _BankCompanyView(CompanyView):
    """A bank company, with its headline statistics reachable by name.

    Each method returns a :class:`~fisis.types.Data`; its ``columns`` carry the
    value columns' units and ``date_of_settlement`` the fiscal date.
    """

    def capital_adequacy(
        self, *, start_month: str, end_month: str, term: Term | str = Term.QUARTERLY,
        account_cd: str | None = None, lang: Lang | str = Lang.KO,
    ) -> Data:
        """자본적정성 (SA014)."""
        return self.fetch(
            list_no="SA014", term=term, start_month=start_month,
            end_month=end_month, account_cd=account_cd, lang=lang)

    def asset_quality(
        self, *, start_month: str, end_month: str, term: Term | str = Term.QUARTERLY,
        account_cd: str | None = None, lang: Lang | str = Lang.KO,
    ) -> Data:
        """자산건전성 (SA015)."""
        return self.fetch(
            list_no="SA015", term=term, start_month=start_month,
            end_month=end_month, account_cd=account_cd, lang=lang)

    def profitability(
        self, *, start_month: str, end_month: str, term: Term | str = Term.QUARTERLY,
        account_cd: str | None = None, lang: Lang | str = Lang.KO,
    ) -> Data:
        """수익성 (SA017)."""
        return self.fetch(
            list_no="SA017", term=term, start_month=start_month,
            end_month=end_month, account_cd=account_cd, lang=lang)

    def liquidity(
        self, *, start_month: str, end_month: str, term: Term | str = Term.QUARTERLY,
        account_cd: str | None = None, lang: Lang | str = Lang.KO,
    ) -> Data:
        """유동성 (SA018)."""
        return self.fetch(
            list_no="SA018", term=term, start_month=start_month,
            end_month=end_month, account_cd=account_cd, lang=lang)

    def productivity(
        self, *, start_month: str, end_month: str, term: Term | str = Term.ANNUAL,
        account_cd: str | None = None, lang: Lang | str = Lang.KO,
    ) -> Data:
        """생산성 (SA019)."""
        return self.fetch(
            list_no="SA019", term=term, start_month=start_month,
            end_month=end_month, account_cd=account_cd, lang=lang)

    def delinquency(
        self, *, start_month: str, end_month: str, term: Term | str = Term.QUARTERLY,
        account_cd: str | None = None, lang: Lang | str = Lang.KO,
    ) -> Data:
        """연체율 (SA040)."""
        return self.fetch(
            list_no="SA040", term=term, start_month=start_month,
            end_month=end_month, account_cd=account_cd, lang=lang)

    def npl_ratio(
        self, *, start_month: str, end_month: str, term: Term | str = Term.QUARTERLY,
        account_cd: str | None = None, lang: Lang | str = Lang.KO,
    ) -> Data:
        """고정이하여신비율 (SA041)."""
        return self.fetch(
            list_no="SA041", term=term, start_month=start_month,
            end_month=end_month, account_cd=account_cd, lang=lang)

    def deposits(
        self, *, start_month: str, end_month: str, term: Term | str = Term.QUARTERLY,
        account_cd: str | None = None, lang: Lang | str = Lang.KO,
    ) -> Data:
        """예수금 (SA028)."""
        return self.fetch(
            list_no="SA028", term=term, start_month=start_month,
            end_month=end_month, account_cd=account_cd, lang=lang)

    def loans(
        self, *, start_month: str, end_month: str, term: Term | str = Term.QUARTERLY,
        account_cd: str | None = None, lang: Lang | str = Lang.KO,
    ) -> Data:
        """대출금 (SA043)."""
        return self.fetch(
            list_no="SA043", term=term, start_month=start_month,
            end_month=end_month, account_cd=account_cd, lang=lang)

    def balance_sheet(
        self, *, start_month: str, end_month: str, term: Term | str = Term.QUARTERLY,
        account_cd: str | None = None, lang: Lang | str = Lang.KO,
    ) -> Data:
        """재무상태표 - 자산 (SA003; 부채·자본 SA004)."""
        return self.fetch(
            list_no="SA003", term=term, start_month=start_month,
            end_month=end_month, account_cd=account_cd, lang=lang)

    def income_statement(
        self, *, start_month: str, end_month: str, term: Term | str = Term.QUARTERLY,
        account_cd: str | None = None, lang: Lang | str = Lang.KO,
    ) -> Data:
        """손익계산서 (SA021)."""
        return self.fetch(
            list_no="SA021", term=term, start_month=start_month,
            end_month=end_month, account_cd=account_cd, lang=lang)


class _LifeCompanyView(CompanyView):
    """A life-insurance company, with its headline statistics reachable by name.

    Each method returns a :class:`~fisis.types.Data`; its ``columns`` carry the
    value columns' units and ``date_of_settlement`` the fiscal date.
    """

    def solvency(
        self, *, start_month: str, end_month: str, term: Term | str = Term.QUARTERLY,
        account_cd: str | None = None, lang: Lang | str = Lang.KO,
    ) -> Data:
        """지급여력 (SH021)."""
        return self.fetch(
            list_no="SH021", term=term, start_month=start_month,
            end_month=end_month, account_cd=account_cd, lang=lang)

    def asset_quality(
        self, *, start_month: str, end_month: str, term: Term | str = Term.QUARTERLY,
        account_cd: str | None = None, lang: Lang | str = Lang.KO,
    ) -> Data:
        """자산건전성 (SH112)."""
        return self.fetch(
            list_no="SH112", term=term, start_month=start_month,
            end_month=end_month, account_cd=account_cd, lang=lang)

    def liquidity(
        self, *, start_month: str, end_month: str, term: Term | str = Term.QUARTERLY,
        account_cd: str | None = None, lang: Lang | str = Lang.KO,
    ) -> Data:
        """유동성 (SH115)."""
        return self.fetch(
            list_no="SH115", term=term, start_month=start_month,
            end_month=end_month, account_cd=account_cd, lang=lang)

    def efficiency(
        self, *, start_month: str, end_month: str, term: Term | str = Term.QUARTERLY,
        account_cd: str | None = None, lang: Lang | str = Lang.KO,
    ) -> Data:
        """경영효율 (SH114)."""
        return self.fetch(
            list_no="SH114", term=term, start_month=start_month,
            end_month=end_month, account_cd=account_cd, lang=lang)

    def persistency(
        self, *, start_month: str, end_month: str, term: Term | str = Term.HALF_YEARLY,
        account_cd: str | None = None, lang: Lang | str = Lang.KO,
    ) -> Data:
        """계약유지율 (SH025)."""
        return self.fetch(
            list_no="SH025", term=term, start_month=start_month,
            end_month=end_month, account_cd=account_cd, lang=lang)

    def agent_retention(
        self, *, start_month: str, end_month: str, term: Term | str = Term.ANNUAL,
        account_cd: str | None = None, lang: Lang | str = Lang.KO,
    ) -> Data:
        """설계사정착률 (SH022)."""
        return self.fetch(
            list_no="SH022", term=term, start_month=start_month,
            end_month=end_month, account_cd=account_cd, lang=lang)

    def new_business(
        self, *, start_month: str, end_month: str, term: Term | str = Term.QUARTERLY,
        account_cd: str | None = None, lang: Lang | str = Lang.KO,
    ) -> Data:
        """신계약 (SH160)."""
        return self.fetch(
            list_no="SH160", term=term, start_month=start_month,
            end_month=end_month, account_cd=account_cd, lang=lang)

    def in_force(
        self, *, start_month: str, end_month: str, term: Term | str = Term.QUARTERLY,
        account_cd: str | None = None, lang: Lang | str = Lang.KO,
    ) -> Data:
        """보유계약 (SH161)."""
        return self.fetch(
            list_no="SH161", term=term, start_month=start_month,
            end_month=end_month, account_cd=account_cd, lang=lang)

    def premium_income(
        self, *, start_month: str, end_month: str, term: Term | str = Term.QUARTERLY,
        account_cd: str | None = None, lang: Lang | str = Lang.KO,
    ) -> Data:
        """수입보험료 (SH166)."""
        return self.fetch(
            list_no="SH166", term=term, start_month=start_month,
            end_month=end_month, account_cd=account_cd, lang=lang)

    def balance_sheet(
        self, *, start_month: str, end_month: str, term: Term | str = Term.QUARTERLY,
        account_cd: str | None = None, lang: Lang | str = Lang.KO,
    ) -> Data:
        """재무상태표 - 자산 (SH150; 부채·자본 SH151; 2023.3 이후)."""
        return self.fetch(
            list_no="SH150", term=term, start_month=start_month,
            end_month=end_month, account_cd=account_cd, lang=lang)

    def income_statement(
        self, *, start_month: str, end_month: str, term: Term | str = Term.QUARTERLY,
        account_cd: str | None = None, lang: Lang | str = Lang.KO,
    ) -> Data:
        """손익계산서 (SH154; 2023.3 이후)."""
        return self.fetch(
            list_no="SH154", term=term, start_month=start_month,
            end_month=end_month, account_cd=account_cd, lang=lang)


class _NonlifeCompanyView(CompanyView):
    """A non-life-insurance company, with its headline statistics reachable by name.

    Each method returns a :class:`~fisis.types.Data`; its ``columns`` carry the
    value columns' units and ``date_of_settlement`` the fiscal date.
    """

    def solvency(
        self, *, start_month: str, end_month: str, term: Term | str = Term.QUARTERLY,
        account_cd: str | None = None, lang: Lang | str = Lang.KO,
    ) -> Data:
        """지급여력 (SI021)."""
        return self.fetch(
            list_no="SI021", term=term, start_month=start_month,
            end_month=end_month, account_cd=account_cd, lang=lang)

    def asset_quality(
        self, *, start_month: str, end_month: str, term: Term | str = Term.QUARTERLY,
        account_cd: str | None = None, lang: Lang | str = Lang.KO,
    ) -> Data:
        """자산건전성 (SI112)."""
        return self.fetch(
            list_no="SI112", term=term, start_month=start_month,
            end_month=end_month, account_cd=account_cd, lang=lang)

    def liquidity(
        self, *, start_month: str, end_month: str, term: Term | str = Term.QUARTERLY,
        account_cd: str | None = None, lang: Lang | str = Lang.KO,
    ) -> Data:
        """유동성 (SI115)."""
        return self.fetch(
            list_no="SI115", term=term, start_month=start_month,
            end_month=end_month, account_cd=account_cd, lang=lang)

    def efficiency(
        self, *, start_month: str, end_month: str, term: Term | str = Term.QUARTERLY,
        account_cd: str | None = None, lang: Lang | str = Lang.KO,
    ) -> Data:
        """경영효율 (SI114)."""
        return self.fetch(
            list_no="SI114", term=term, start_month=start_month,
            end_month=end_month, account_cd=account_cd, lang=lang)

    def persistency(
        self, *, start_month: str, end_month: str, term: Term | str = Term.HALF_YEARLY,
        account_cd: str | None = None, lang: Lang | str = Lang.KO,
    ) -> Data:
        """계약유지율 (SI025)."""
        return self.fetch(
            list_no="SI025", term=term, start_month=start_month,
            end_month=end_month, account_cd=account_cd, lang=lang)

    def agent_retention(
        self, *, start_month: str, end_month: str, term: Term | str = Term.ANNUAL,
        account_cd: str | None = None, lang: Lang | str = Lang.KO,
    ) -> Data:
        """설계사정착률 (SI022)."""
        return self.fetch(
            list_no="SI022", term=term, start_month=start_month,
            end_month=end_month, account_cd=account_cd, lang=lang)

    def balance_sheet(
        self, *, start_month: str, end_month: str, term: Term | str = Term.QUARTERLY,
        account_cd: str | None = None, lang: Lang | str = Lang.KO,
    ) -> Data:
        """재무상태표 - 자산 (SI146; 부채·자본 SI147; 2023.3 이후)."""
        return self.fetch(
            list_no="SI146", term=term, start_month=start_month,
            end_month=end_month, account_cd=account_cd, lang=lang)

    def income_statement(
        self, *, start_month: str, end_month: str, term: Term | str = Term.QUARTERLY,
        account_cd: str | None = None, lang: Lang | str = Lang.KO,
    ) -> Data:
        """손익계산서 (SI150; 2023.3 이후)."""
        return self.fetch(
            list_no="SI150", term=term, start_month=start_month,
            end_month=end_month, account_cd=account_cd, lang=lang)


class _CardCompanyView(CompanyView):
    """A credit-card company, with its headline statistics reachable by name.

    Each method returns a :class:`~fisis.types.Data`; its ``columns`` carry the
    value columns' units and ``date_of_settlement`` the fiscal date.
    """

    def capital_adequacy(
        self, *, start_month: str, end_month: str, term: Term | str = Term.QUARTERLY,
        account_cd: str | None = None, lang: Lang | str = Lang.KO,
    ) -> Data:
        """자본적정성 (SC007)."""
        return self.fetch(
            list_no="SC007", term=term, start_month=start_month,
            end_month=end_month, account_cd=account_cd, lang=lang)

    def asset_quality(
        self, *, start_month: str, end_month: str, term: Term | str = Term.QUARTERLY,
        account_cd: str | None = None, lang: Lang | str = Lang.KO,
    ) -> Data:
        """자산건전성 (SC008)."""
        return self.fetch(
            list_no="SC008", term=term, start_month=start_month,
            end_month=end_month, account_cd=account_cd, lang=lang)

    def profitability(
        self, *, start_month: str, end_month: str, term: Term | str = Term.QUARTERLY,
        account_cd: str | None = None, lang: Lang | str = Lang.KO,
    ) -> Data:
        """수익성 (SC009)."""
        return self.fetch(
            list_no="SC009", term=term, start_month=start_month,
            end_month=end_month, account_cd=account_cd, lang=lang)

    def liquidity(
        self, *, start_month: str, end_month: str, term: Term | str = Term.QUARTERLY,
        account_cd: str | None = None, lang: Lang | str = Lang.KO,
    ) -> Data:
        """유동성 (SC010)."""
        return self.fetch(
            list_no="SC010", term=term, start_month=start_month,
            end_month=end_month, account_cd=account_cd, lang=lang)

    def delinquency(
        self, *, start_month: str, end_month: str, term: Term | str = Term.QUARTERLY,
        account_cd: str | None = None, lang: Lang | str = Lang.KO,
    ) -> Data:
        """연체율 (SC117)."""
        return self.fetch(
            list_no="SC117", term=term, start_month=start_month,
            end_month=end_month, account_cd=account_cd, lang=lang)

    def credit_card_usage(
        self, *, start_month: str, end_month: str, term: Term | str = Term.QUARTERLY,
        account_cd: str | None = None, lang: Lang | str = Lang.KO,
    ) -> Data:
        """신용카드 이용실적 (SC013)."""
        return self.fetch(
            list_no="SC013", term=term, start_month=start_month,
            end_month=end_month, account_cd=account_cd, lang=lang)

    def debit_card_usage(
        self, *, start_month: str, end_month: str, term: Term | str = Term.QUARTERLY,
        account_cd: str | None = None, lang: Lang | str = Lang.KO,
    ) -> Data:
        """체크카드 이용실적 (SC014)."""
        return self.fetch(
            list_no="SC014", term=term, start_month=start_month,
            end_month=end_month, account_cd=account_cd, lang=lang)

    def purchase_volume(
        self, *, start_month: str, end_month: str, term: Term | str = Term.QUARTERLY,
        account_cd: str | None = None, lang: Lang | str = Lang.KO,
    ) -> Data:
        """카드 구매실적 (SC016)."""
        return self.fetch(
            list_no="SC016", term=term, start_month=start_month,
            end_month=end_month, account_cd=account_cd, lang=lang)

    def balance_sheet(
        self, *, start_month: str, end_month: str, term: Term | str = Term.QUARTERLY,
        account_cd: str | None = None, lang: Lang | str = Lang.KO,
    ) -> Data:
        """재무상태표 - 자산 (SC103; 부채·자본 SC104; 2008.3 이후)."""
        return self.fetch(
            list_no="SC103", term=term, start_month=start_month,
            end_month=end_month, account_cd=account_cd, lang=lang)

    def income_statement(
        self, *, start_month: str, end_month: str, term: Term | str = Term.QUARTERLY,
        account_cd: str | None = None, lang: Lang | str = Lang.KO,
    ) -> Data:
        """손익계산서 (SC218; 2018.12 이후)."""
        return self.fetch(
            list_no="SC218", term=term, start_month=start_month,
            end_month=end_month, account_cd=account_cd, lang=lang)


class _SecuritiesCompanyView(CompanyView):
    """A securities company, with its headline statistics reachable by name.

    Each method returns a :class:`~fisis.types.Data`; its ``columns`` carry the
    value columns' units and ``date_of_settlement`` the fiscal date.
    """

    def net_capital_ratio(
        self, *, start_month: str, end_month: str, term: Term | str = Term.QUARTERLY,
        account_cd: str | None = None, lang: Lang | str = Lang.KO,
    ) -> Data:
        """순자본비율 (SF308)."""
        return self.fetch(
            list_no="SF308", term=term, start_month=start_month,
            end_month=end_month, account_cd=account_cd, lang=lang)

    def leverage(
        self, *, start_month: str, end_month: str, term: Term | str = Term.QUARTERLY,
        account_cd: str | None = None, lang: Lang | str = Lang.KO,
    ) -> Data:
        """레버리지비율 (SF331)."""
        return self.fetch(
            list_no="SF331", term=term, start_month=start_month,
            end_month=end_month, account_cd=account_cd, lang=lang)

    def asset_quality(
        self, *, start_month: str, end_month: str, term: Term | str = Term.QUARTERLY,
        account_cd: str | None = None, lang: Lang | str = Lang.KO,
    ) -> Data:
        """자산건전성 (SF311)."""
        return self.fetch(
            list_no="SF311", term=term, start_month=start_month,
            end_month=end_month, account_cd=account_cd, lang=lang)

    def liquidity(
        self, *, start_month: str, end_month: str, term: Term | str = Term.QUARTERLY,
        account_cd: str | None = None, lang: Lang | str = Lang.KO,
    ) -> Data:
        """유동성 (SF209)."""
        return self.fetch(
            list_no="SF209", term=term, start_month=start_month,
            end_month=end_month, account_cd=account_cd, lang=lang)

    def profitability(
        self, *, start_month: str, end_month: str, term: Term | str = Term.QUARTERLY,
        account_cd: str | None = None, lang: Lang | str = Lang.KO,
    ) -> Data:
        """수익성 (SF210)."""
        return self.fetch(
            list_no="SF210", term=term, start_month=start_month,
            end_month=end_month, account_cd=account_cd, lang=lang)

    def securities_trading(
        self, *, start_month: str, end_month: str, term: Term | str = Term.QUARTERLY,
        account_cd: str | None = None, lang: Lang | str = Lang.KO,
    ) -> Data:
        """증권 매매현황 (SF316)."""
        return self.fetch(
            list_no="SF316", term=term, start_month=start_month,
            end_month=end_month, account_cd=account_cd, lang=lang)

    def derivatives_trading(
        self, *, start_month: str, end_month: str, term: Term | str = Term.QUARTERLY,
        account_cd: str | None = None, lang: Lang | str = Lang.KO,
    ) -> Data:
        """파생상품 매매현황 (SF317)."""
        return self.fetch(
            list_no="SF317", term=term, start_month=start_month,
            end_month=end_month, account_cd=account_cd, lang=lang)

    def balance_sheet(
        self, *, start_month: str, end_month: str, term: Term | str = Term.QUARTERLY,
        account_cd: str | None = None, lang: Lang | str = Lang.KO,
    ) -> Data:
        """재무상태표 - 자산 (SF303; 부채·자본 SF304; 2011.6 이후)."""
        return self.fetch(
            list_no="SF303", term=term, start_month=start_month,
            end_month=end_month, account_cd=account_cd, lang=lang)

    def income_statement(
        self, *, start_month: str, end_month: str, term: Term | str = Term.QUARTERLY,
        account_cd: str | None = None, lang: Lang | str = Lang.KO,
    ) -> Data:
        """손익계산서 (SF307; 2011.6 이후)."""
        return self.fetch(
            list_no="SF307", term=term, start_month=start_month,
            end_month=end_month, account_cd=account_cd, lang=lang)
