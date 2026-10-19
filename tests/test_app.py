"""
The app loads, and says which schema version it checks against.
"""
import importlib.util

from helpers import ROOT, SCHEMA


def test_app_loads():
    spec = importlib.util.spec_from_file_location("app", ROOT / "app" / "app.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert f"Checks against schema version {SCHEMA.version}." in str(module.app_ui)
