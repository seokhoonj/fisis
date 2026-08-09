"""One request over the wire: build the FISIS query URL, GET it, surface errors.

FISIS is a query-string API with one host and one operation per path; the ``.json``
suffix selects the JSON output format and the API key rides as the ``auth`` param:

    http://fisis.fss.or.kr/openapi/{operation}.json?auth=...&lang=kr&...

``_Transport`` holds the HTTP client and the pacing clock. It spaces consecutive
requests (``delay_seconds``) so a bulk run stays polite, and retries a transient
failure -- a timeout, connection reset, HTTP 5xx, or the FISIS internal error code
900 -- with backoff.

FISIS signals a *vendor* error not with an HTTP status but inside an otherwise-200
JSON body: every response is ``{"result": {"err_cd": ..., "err_msg": ..., ...}}``
and ``err_cd`` "000" means success. This module unwraps ``result``, tells success
from failure, and raises the failures through the :class:`FISISError` hierarchy.
"""

from __future__ import annotations

import json
import time
from typing import Any, NoReturn
from urllib.parse import urlencode

import httpx

from .exceptions import (
    FISISAuthError,
    FISISNetworkError,
    FISISRateLimitError,
    FISISResponseError,
)

# A transient failure (timeout, reset, 5xx, vendor 900) is a glitch worth retrying.
# This counts total attempts, not retries -- 3 is one try plus two retries.
_MAX_ATTEMPTS = 3
_RETRY_BACKOFF_SECONDS = 1.0
_RETRY_BACKOFF_FACTOR = 2  # each retry waits this many times the last

_SUCCESS_CODE = "000"
# A rejected key: unregistered (010), suspended (011), deleted (012), or the sample
# key used outside its sample query (013).
_AUTH_ERR_CODES = frozenset({"010", "011", "012", "013"})
# The daily search quota (일일검색 허용횟수 초과). Exhausted for the calendar day, so
# a retry cannot help -- raised immediately, like an HTTP 429.
_DAILY_QUOTA_CODE = "020"
# "정의되지 않은 오류가 발생하였습니다" -- an internal FISIS hiccup, retried like a
# 5xx; if it persists through every attempt it surfaces as a FISISResponseError.
_INTERNAL_ERROR_CODE = "900"


class _Transport:
    """The HTTP client plus its pacing clock -- one per :class:`FISIS`.

    ``delay_seconds`` spaces consecutive requests so a bulk run (many companies or
    statistics in a loop) does not hammer FISIS; the default is 0 because a handful
    of calls needs no pacing, and pacing every call would only slow the common
    case. FISIS's own cap is a *daily* search quota, which pacing cannot lift --
    it only spreads the load.

    Not thread-safe: the pacing clock (``_next_request_at``) is shared mutable
    state, so use one client -- hence one transport -- per thread.
    """

    def __init__(
        self,
        client: httpx.Client,
        *,
        delay_seconds: float = 0.0,
        max_attempts: int = _MAX_ATTEMPTS,
    ) -> None:
        self._client = client
        self._delay_seconds = delay_seconds
        self._max_attempts = max_attempts
        self._next_request_at = 0.0

    def request(self, *, base_url: str, params: dict[str, str]) -> dict[str, Any]:
        """Fetch one call and return its ``result`` payload as a raw vendor dict.

        Retries a transient failure -- a transport error (timeout, connection
        reset), an HTTP 5xx, or the FISIS internal error code 900 -- with backoff.
        Raises :class:`FISISNetworkError` if the transport never completes,
        :class:`FISISAuthError` on a rejected key, :class:`FISISRateLimitError`
        when the daily quota (``err_cd`` 020) or an HTTP 429 is hit, and
        :class:`FISISResponseError` on any other vendor error code.
        """
        url = f"{base_url}?{urlencode(params)}"
        last_error: FISISNetworkError | FISISResponseError | None = None
        for attempt in range(self._max_attempts):
            self._wait_for_next_slot()
            try:
                response = self._client.get(url)
                response.raise_for_status()
                payload = response.json()
            except httpx.HTTPStatusError as err:
                # Message from the status line ONLY. ``str(err)`` -- and the httpx
                # exception chained as a cause -- embed the request URL, which
                # carries ``auth=<key>``. Never surface either; ``from None`` also
                # keeps that URL out of a printed traceback.
                status = err.response.status_code
                detail = f"HTTP {status} {err.response.reason_phrase}".rstrip()
                if status == 429:  # Too Many Requests -- the rate cap, not retried
                    raise FISISRateLimitError("429", detail) from None
                if status < 500:  # any other 4xx is the server's answer
                    raise FISISNetworkError(detail) from None
                last_error = FISISNetworkError(detail)  # 5xx: retry
            except httpx.HTTPError as err:  # timeout, connection reset, ...
                # Report the failure kind, not ``str(err)``/the cause -- same reason.
                last_error = FISISNetworkError(f"request failed ({type(err).__name__})")
            except json.JSONDecodeError as err:
                # A 200 whose body is not JSON (a proxy/maintenance HTML page) must
                # surface through the FISISError hierarchy, not as a raw decode
                # error. Safe to chain: a decode error is about the response body,
                # not the key-bearing request URL.
                raise FISISResponseError(
                    "UNKNOWN", f"non-JSON response from FISIS: {err}") from err
            else:
                result = _unwrap_result(payload)
                code = str(result.get("err_cd", _SUCCESS_CODE))
                if code == _SUCCESS_CODE:
                    return result
                message = str(result.get("err_msg", ""))
                if code == _INTERNAL_ERROR_CODE:  # FISIS-internal hiccup: retry
                    last_error = FISISResponseError(code, message)
                else:
                    _raise_vendor_error(code, message)
            if attempt + 1 < self._max_attempts:
                time.sleep(_RETRY_BACKOFF_SECONDS * _RETRY_BACKOFF_FACTOR**attempt)
        if last_error is not None:
            raise last_error
        raise FISISNetworkError("request failed")

    def _wait_for_next_slot(self) -> None:
        if self._delay_seconds <= 0:
            return
        now = time.monotonic()
        if now < self._next_request_at:
            time.sleep(self._next_request_at - now)
        self._next_request_at = time.monotonic() + self._delay_seconds


def _unwrap_result(payload: Any) -> dict[str, Any]:
    """The ``result`` object of a FISIS payload, tolerating a missing wrapper.

    Every documented response nests the body under ``"result"``; a payload that is
    itself the result object (no wrapper) is accepted as-is, so a vendor-side
    format loosening does not break the client. Anything that is not a JSON object
    raises :class:`FISISResponseError`.
    """
    if isinstance(payload, dict):
        result = payload.get("result", payload)
        if isinstance(result, dict):
            return result
    raise FISISResponseError("UNKNOWN", f"unexpected FISIS response: {payload!r}")


def _raise_vendor_error(code: str, message: str) -> NoReturn:
    """Raise the :class:`FISISError` subclass a vendor ``err_cd`` maps to.

    Auth codes (010-013) become :class:`FISISAuthError`; the daily quota (020)
    becomes :class:`FISISRateLimitError`; everything else -- known request
    mistakes (021, 022, 100-103) and unknown codes alike -- stays a
    :class:`FISISResponseError` carrying the vendor's code verbatim.
    """
    if code in _AUTH_ERR_CODES:
        raise FISISAuthError(code, message or "invalid FISIS API key")
    if code == _DAILY_QUOTA_CODE:
        raise FISISRateLimitError(code, message or "daily search quota exceeded")
    raise FISISResponseError(code, message)
