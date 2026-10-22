"""
The app loads, and offers a blank collection sheet for download.
"""
import importlib.util

from helpers import ROOT


def test_app_loads():
    spec = importlib.util.spec_from_file_location("app", ROOT / "app" / "app.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert "Download a blank collection sheet" in str(module.app_ui)
