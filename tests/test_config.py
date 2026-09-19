"""API-key resolution order: explicit argument, environment, credentials file."""

from __future__ import annotations

import json
import os

import pytest

from fisis import FISISConfigError
from fisis._config import credentials_path, resolve_api_key


def _write_credentials(tmp_path, mapping) -> None:
    config_dir = tmp_path / "fisis"
    config_dir.mkdir(parents=True)
    (config_dir / "credentials.json").write_text(
        json.dumps(mapping), encoding="utf-8")


def test_explicit_key_wins_over_environment(monkeypatch):
    monkeypatch.setenv("FISIS_API_KEY", "FROMENV")
    assert resolve_api_key("EXPLICIT") == "EXPLICIT"


def test_environment_beats_credentials_file(monkeypatch, tmp_path):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    monkeypatch.setenv("FISIS_API_KEY", "FROMENV")
    _write_credentials(tmp_path, {"FISIS_API_KEY": "FROMFILE"})
    assert resolve_api_key(None) == "FROMENV"


def test_key_read_from_credentials_file(monkeypatch, tmp_path):
    monkeypatch.delenv("FISIS_API_KEY", raising=False)
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    _write_credentials(tmp_path, {"FISIS_API_KEY": "FROMFILE"})
    assert resolve_api_key(None) == "FROMFILE"


def test_missing_everywhere_raises_config_error(monkeypatch, tmp_path):
    monkeypatch.delenv("FISIS_API_KEY", raising=False)
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))  # empty -- no file
    with pytest.raises(FISISConfigError):
        resolve_api_key(None)


def test_invalid_json_credentials_file_raises(monkeypatch, tmp_path):
    monkeypatch.delenv("FISIS_API_KEY", raising=False)
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    config_dir = tmp_path / "fisis"
    config_dir.mkdir(parents=True)
    (config_dir / "credentials.json").write_text("not json", encoding="utf-8")
    with pytest.raises(FISISConfigError):
        resolve_api_key(None)


def test_non_object_credentials_file_raises(monkeypatch, tmp_path):
    monkeypatch.delenv("FISIS_API_KEY", raising=False)
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    config_dir = tmp_path / "fisis"
    config_dir.mkdir(parents=True)
    (config_dir / "credentials.json").write_text('["a-list"]', encoding="utf-8")
    with pytest.raises(FISISConfigError):
        resolve_api_key(None)


def test_credentials_path_honors_xdg_config_home(monkeypatch, tmp_path):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    assert credentials_path() == tmp_path / "fisis" / "credentials.json"


def test_store_binding_redirects_to_a_host_namespace(monkeypatch, tmp_path):
    # A host embedding fisis redirects the store via FISIS_STORE_APP + FISIS_NAMESPACE,
    # so fisis's key lives in the host's store under a fisis section.
    monkeypatch.delenv("FISIS_API_KEY", raising=False)
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    monkeypatch.setenv("FISIS_STORE_APP", "host")
    monkeypatch.setenv("FISIS_NAMESPACE", "fisis")
    host = tmp_path / "host"
    host.mkdir(parents=True)
    (host / "credentials.json").write_text(
        json.dumps({"fisis": {"FISIS_API_KEY": "HOSTKEY"}}), encoding="utf-8")
    assert resolve_api_key(None) == "HOSTKEY"


def test_env_wins_before_an_invalid_binding_is_validated(monkeypatch):
    # env resolves before the binding is validated (lazy) -- even a bad binding is fine.
    monkeypatch.setenv("FISIS_STORE_APP", "../invalid")
    monkeypatch.setenv("FISIS_API_KEY", "FROMENV")
    assert resolve_api_key(None) == "FROMENV"


def test_invalid_store_binding_raises_config_error(monkeypatch):
    # A malformed binding surfaces as fisis's FISISConfigError on first store touch.
    monkeypatch.delenv("FISIS_API_KEY", raising=False)
    monkeypatch.setenv("FISIS_STORE_APP", "../invalid")
    with pytest.raises(FISISConfigError):
        resolve_api_key(None)


def test_empty_stored_key_is_treated_as_missing(monkeypatch, tmp_path):
    # A blank stored value is "no key" (credbox treats blank as absent): raises.
    monkeypatch.delenv("FISIS_API_KEY", raising=False)
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    _write_credentials(tmp_path, {"FISIS_API_KEY": ""})
    with pytest.raises(FISISConfigError):
        resolve_api_key(None)


@pytest.mark.parametrize("source", ["explicit", "environment", "stored"])
def test_api_key_is_trimmed_at_every_tier(monkeypatch, tmp_path, source):
    # credbox strips surrounding whitespace at every tier (a pasted trailing newline no
    # longer breaks auth); pinned so a future change cannot silently return padding.
    monkeypatch.delenv("FISIS_API_KEY", raising=False)
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    explicit = None
    if source == "explicit":
        explicit = "  KEY  "
    elif source == "environment":
        monkeypatch.setenv("FISIS_API_KEY", "  KEY  ")
    else:
        _write_credentials(tmp_path, {"FISIS_API_KEY": "  KEY  "})
    assert resolve_api_key(explicit) == "KEY"


@pytest.mark.skipif(os.name == "nt", reason="POSIX permission bits required")
def test_loose_permission_file_warns_and_still_reads(monkeypatch, tmp_path, capsys):
    # A group/other-readable file is warned about (chmod 600 nudge), not refused.
    monkeypatch.delenv("FISIS_API_KEY", raising=False)
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    _write_credentials(tmp_path, {"FISIS_API_KEY": "FROMFILE"})
    (tmp_path / "fisis" / "credentials.json").chmod(0o644)
    assert resolve_api_key(None) == "FROMFILE"
    assert "chmod 600" in capsys.readouterr().err
