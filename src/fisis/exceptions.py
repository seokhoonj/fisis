"""Exception hierarchy for fisis.

Every *operational* error raised by this package derives from ``FISISError``, so a
caller can catch all of them with one ``except FISISError``. The subclasses separate
the failure modes a caller handles differently: a misconfiguration caught before any
request, a rejected API key, an exhausted quota, a vendor-reported error inside a
well-formed response, and a transport failure that never reached FISIS. An *invalid
argument* -- an unknown ``sector`` or ``term`` value -- raises the standard
``ValueError`` instead, the usual signal for a caller mistake rather than a runtime
failure.
"""

from __future__ import annotations


class FISISError(Exception):
    """Base class for every error raised by fisis."""


class FISISConfigError(FISISError):
    """The client is misconfigured; raised before any request goes out.

    The usual cause is a missing API key -- neither passed to ``FISIS(...)`` nor
    present in the ``FISIS_API_KEY`` environment variable nor the credentials file.
    """


class FISISResponseError(FISISError):
    """FISIS returned a well-formed response carrying an error code.

    FISIS reports a failure inside an otherwise-200 JSON body, as ``err_cd`` /
    ``err_msg`` on the response's ``result`` object rather than an HTTP error
    status; ``code`` and ``message`` are the vendor's own, so a caller can branch
    on the code without parsing the message text. Common codes: ``100`` (a
    required parameter is missing), ``101`` (an invalid parameter value), ``102``
    (start month after end month), ``103`` (the window spans more than 40
    quarters). ``code`` is the vendor ``err_cd`` except ``"429"`` (an HTTP rate
    limit, on :class:`FISISRateLimitError`) and ``"UNKNOWN"`` (a malformed or
    non-JSON response).
    """

    def __init__(self, code: str, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(f"[{code}] {message}")


class FISISAuthError(FISISResponseError):
    """FISIS rejected the API key.

    Raised for an unregistered (``err_cd`` 010), suspended (011), or deleted (012)
    key, and for the sample key used outside its sample query (013). Subclasses
    :class:`FISISResponseError` so it carries the vendor ``code``/``message`` and
    ``except FISISResponseError`` catches it, while a caller can still catch an
    auth failure distinctly.
    """


class FISISRateLimitError(FISISResponseError):
    """FISIS is rate-limiting the caller.

    Raised when the key's daily search quota is exhausted (``err_cd`` 020) or on
    an HTTP 429 (Too Many Requests). Neither is retried: the daily quota resets
    with the calendar day, not by backing off. It subclasses
    :class:`FISISResponseError`, so ``except FISISResponseError`` still catches
    it, but a caller can catch this distinctly to stop a bulk run for the day
    rather than fail call by call.
    """


class FISISNetworkError(FISISError):
    """The request failed at the transport or HTTP layer.

    A timeout, DNS failure, connection reset, or a non-success HTTP status that
    FISIS never turned into an error body. The underlying transport exception is
    deliberately NOT chained: its string embeds the request URL, which carries
    the API key.
    """
