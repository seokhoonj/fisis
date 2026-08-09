"""API-key resolution order: explicit argument, environment, credentials file."""

from __future__ import annotations

import json

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
