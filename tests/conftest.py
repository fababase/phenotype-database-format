"""
Setup shared by all tests: makes the modules in app/ and schema/, and tests/helpers.py, importable, and
provides the `dataset` fixture, a copy of the valid dataset to change.
"""
import sys
from pathlib import Path

import pytest

TESTS = Path(__file__).resolve().parent
sys.path.insert(0, str(TESTS.parent / "app"))
sys.path.insert(0, str(TESTS.parent / "schema"))
sys.path.insert(0, str(TESTS))
pytest.register_assert_rewrite("helpers")

from helpers import Dataset  # noqa: E402


@pytest.fixture
def dataset(tmp_path: Path) -> Dataset:
    """A copy of the valid dataset in a temporary folder, to change."""
    return Dataset(tmp_path / "data")
