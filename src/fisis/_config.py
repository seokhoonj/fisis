"""Resolve the FISIS API key from the caller, the environment, or the config file.

The key is looked up in a fixed order, so an explicit value always wins and a set
environment variable beats a file on disk:

1. the ``api_key`` passed to ``FISIS(...)``
2. the ``FISIS_API_KEY`` environment variable
3. ``"FISIS_API_KEY"`` in ``$XDG_CONFIG_HOME/fisis/credentials.json``
   (``$XDG_CONFIG_HOME`` defaults to ``~/.config``)

The resolution, the permission handling (a group/other-readable file is warned about,
not refused), and the storage backend are delegated to credbox. The store binding is not
hardcoded: ``Credentials.for_app("fisis")`` lets a host embedding fisis redirect it via
``FISIS_STORE_APP`` / ``FISIS_NAMESPACE``; standalone it is exactly the flat
``~/.config/fisis/credentials.json`` fisis has always read. A file that is present but
unreadable, not JSON, or not a JSON object is still an error rather than a silent skip.
"""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

from credbox import CredBoxError, Credentials

from .exceptions import FISISConfigError

_ENV_VAR = "FISIS_API_KEY"
_STORE_APP = "fisis"
_CONFIG_FILE = "credentials.json"


def resolve_api_key(explicit: str | None) -> str:
    """Return the first key found across the three sources, or raise if none exists."""
    try:
        found = _get_credentials().secret(_ENV_VAR, override=explicit)
    except CredBoxError as err:
        # credbox's message already names the store path + fault; don't prepend
        # credentials_path() (wrong under a FISIS_STORE_APP redirect).
        raise FISISConfigError(f"could not read the credential store: {err}") from err
    if found is None:
        # Binding validated cleanly above (None, not error), so store_location() is
        # safe and gives the real store (the host's under a redirect).
        raise FISISConfigError(
            f"no FISIS API key: pass api_key=, set the {_ENV_VAR} environment "
            f"variable, or put it in {_get_credentials().store_location()}"
        )
    return found.reveal()


def credentials_path() -> Path:
    """The standalone/default path fisis reads a stored key from (honoring
    ``$XDG_CONFIG_HOME``); not redirect-aware. Under a ``FISIS_STORE_APP`` redirect the
    real store differs -- ``_get_credentials().store_location()`` reports it."""
    config_home = os.environ.get("XDG_CONFIG_HOME") or str(Path.home() / ".config")
    return Path(config_home) / _STORE_APP / _CONFIG_FILE


@lru_cache(maxsize=1)
def _get_credentials() -> Credentials:
    """fisis's credbox credential store, built on first use and cached.

    Built via ``for_app`` (not the bare ``Credentials(...)``) so a host embedding fisis
    can redirect the binding with ``FISIS_STORE_APP`` / ``FISIS_NAMESPACE`` before the
    first lookup. credbox re-resolves the store *path* per call (honouring a later
    ``XDG_CONFIG_HOME``); the binding is read from the environment once, when this
    facade is built, and a malformed one surfaces as ``FISISConfigError`` on first use.
    """
    return Credentials.for_app(_STORE_APP)
