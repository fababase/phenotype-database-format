"""
Package versions: the tests run with the versions in app/requirements.txt, which the browser app runs with too,
and the validator and the app say when another version is installed.
"""
import importlib.util
from importlib import metadata

import validation
from helpers import ROOT
from validation import main, version_notices

NOTICE = "This validator is tested with pandas 0.0.1, but pandas 2.2.3 is installed, so results may differ."


def test_installed_versions_are_the_ones_in_requirements_txt():
    """If this fails, install the tested versions: pip install -r app/requirements.txt"""
    assert version_notices() == []


def test_other_version_installed(tmp_path):
    requirements = tmp_path / "requirements.txt"
    requirements.write_text("# A comment\n\n"
                            "pandas==0.0.1\n"
                            f"PyYAML=={metadata.version('PyYAML')}\n"
                            "not-installed==1.0\n", encoding="utf-8")
    assert version_notices(requirements) == [
        f"This validator is tested with pandas 0.0.1, but pandas {metadata.version('pandas')} is installed, "
        "so results may differ."]


def test_command_line_shows_notice(dataset, capsys, monkeypatch):
    monkeypatch.setattr(validation, "version_notices", lambda: [NOTICE])
    assert main([str(dataset.folder)]) == 0
    assert capsys.readouterr().out.splitlines()[1] == f"Notice: {NOTICE}"


def test_app_shows_notice(monkeypatch):
    monkeypatch.setattr(validation, "version_notices", lambda: [NOTICE])
    spec = importlib.util.spec_from_file_location("app", ROOT / "app" / "app.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert f"Notice: {NOTICE}" in str(module.app_ui)
