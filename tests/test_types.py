"""Data.to_polars / to_pandas -- the lazy frame conversions, tested without the
frame libraries installed (the wiring is exercised by monkeypatching the import)."""

from __future__ import annotations

import importlib

import pytest

from fisis.types import Column, Data

_DATA = Data(
    rows=[{"base_month": "202403", "말잔": "1000"},
          {"base_month": "202406", "말잔": "1100"}],
    columns=(Column("a", "말잔", "원"),),
    date_of_settlement="12/31")


class _FakeFrame:
    """Records the rows a stand-in ``DataFrame(...)`` constructor is handed."""

    def __init__(self, rows: object) -> None:
        self.rows = rows


class _RecordingBackend:
    """Stands in for polars / pandas: its ``DataFrame`` records the rows given."""

    DataFrame = _FakeFrame


def test_to_polars_passes_rows_to_dataframe(monkeypatch):
    monkeypatch.setattr(importlib, "import_module", lambda name: _RecordingBackend)
    frame = _DATA.to_polars()
    assert isinstance(frame, _FakeFrame)
    assert frame.rows == _DATA.rows  # the records list, not the Data itself


def test_to_pandas_passes_rows_to_dataframe(monkeypatch):
    monkeypatch.setattr(importlib, "import_module", lambda name: _RecordingBackend)
    frame = _DATA.to_pandas()
    assert isinstance(frame, _FakeFrame)
    assert frame.rows == _DATA.rows


def test_conversion_without_the_library_raises_a_helpful_error(monkeypatch):
    def _absent(name: str):
        raise ModuleNotFoundError(f"No module named {name!r}", name=name)

    monkeypatch.setattr(importlib, "import_module", _absent)
    # The error names the missing library and how to install it, so a caller who
    # never installed polars / pandas is told the fix rather than seeing a bare
    # ModuleNotFoundError from deep in the method.
    with pytest.raises(ImportError, match="pip install polars"):
        _DATA.to_polars()
    with pytest.raises(ImportError, match="pip install pandas"):
        _DATA.to_pandas()


def test_conversion_reraises_when_a_backend_dependency_is_missing(monkeypatch):
    # polars is installed but one of ITS OWN dependencies is not. The real cause
    # (numpy) must surface, not a misleading "polars is not installed".
    def _dependency_missing(name: str):
        raise ModuleNotFoundError("No module named 'numpy'", name="numpy")

    monkeypatch.setattr(importlib, "import_module", _dependency_missing)
    with pytest.raises(ModuleNotFoundError, match="numpy"):
        _DATA.to_polars()
