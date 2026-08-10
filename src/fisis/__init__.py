"""fisis -- a Python client for the FISIS Open API (금융감독원 금융통계정보시스템)."""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version

from ._accessor import CompanyView, SectorView
from .client import FISIS
from .exceptions import (
    FISISAuthError,
    FISISConfigError,
    FISISError,
    FISISNetworkError,
    FISISRateLimitError,
    FISISResponseError,
)
from .types import (
    AccountRow,
    Category,
    Column,
    CompanyRow,
    Data,
    DataRow,
    Lang,
    Sector,
    StatisticsRow,
    Term,
)

try:
    __version__ = version("fisis")
except PackageNotFoundError:  # running from a source tree without an install
    __version__ = "0.0.0"

__all__ = [
    "FISIS",
    "SectorView",
    "CompanyView",
    "Sector",
    "Category",
    "Term",
    "Lang",
    "CompanyRow",
    "StatisticsRow",
    "AccountRow",
    "DataRow",
    "Column",
    "Data",
    "FISISError",
    "FISISConfigError",
    "FISISAuthError",
    "FISISRateLimitError",
    "FISISResponseError",
    "FISISNetworkError",
    "__version__",
]
