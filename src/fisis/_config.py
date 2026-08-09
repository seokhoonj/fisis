"""Resolve the FISIS API key from the caller, the environment, or the config file.

The key is looked up in a fixed order, so an explicit value always wins and a set
environment variable beats a file on disk:

1. the ``api_key`` passed to ``FISIS(...)``
2. the ``FISIS_API_KEY`` environment variable
3. ``"FISIS_API_KEY"`` in ``$XDG_CONFIG_HOME/fisis/credentials.json``
   (``$XDG_CONFIG_HOME`` defaults to ``~/.config``)

The file is optional -- its absence just means "no key here." But a file that is
present and unreadable, not JSON, or not a JSON object is an error, because a caller
who wrote one meant it to be used and a silent skip would hide the mistake.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

from .exceptions import FISISConfigError

_ENV_VAR = "FISIS_API_KEY"
_CONFIG_DIR = "fisis"
_CONFIG_FILE = "credentials.json"


def resolve_api_key(explicit: str | None) -> str:
    """Return the first key found across the three sources, or raise if none exists."""
    key = explicit or os.environ.get(_ENV_VAR) or _key_from_file()
    if not key:
        raise FISISConfigError(
            f"no FISIS API key: pass api_key=, set the {_ENV_VAR} environment "
            f"variable, or put it in {credentials_path()}"
        )
    return key


def credentials_path() -> Path:
    """The path fisis reads a stored key from (honoring ``$XDG_CONFIG_HOME``)."""
    config_home = os.environ.get("XDG_CONFIG_HOME") or str(Path.home() / ".config")
    return Path(config_home) / _CONFIG_DIR / _CONFIG_FILE


def _key_from_file() -> str | None:
    path = credentials_path()
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return None
    except OSError as err:
        raise FISISConfigError(f"could not read {path}: {err}") from err

    try:
        credentials = json.loads(text)
    except json.JSONDecodeError as err:
        raise FISISConfigError(f"{path} is not valid JSON: {err}") from err
    if not isinstance(credentials, dict):
        raise FISISConfigError(f"{path} must contain a JSON object")

    key = credentials.get(_ENV_VAR)
    return key if isinstance(key, str) and key else None
