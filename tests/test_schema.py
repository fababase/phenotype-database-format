"""
The schema itself: there is exactly one schema.yaml, and the validator reads it.
"""
import os

from helpers import ROOT
from validation import SCHEMA_FILE


def test_schema_yaml_has_only_one_copy():
    """schema/schema.yaml is never copied, e.g. into app/, so nothing can be checked against a stale copy."""
    copies = []
    for folder, subfolders, files in os.walk(ROOT):
        subfolders[:] = [name for name in subfolders if name != ".git"]
        copies += [(os.path.relpath(folder, ROOT), name) for name in files
                   if name.lower() in ("schema.yaml", "schema.yml")]
    assert copies == [("schema", "schema.yaml")]
    assert SCHEMA_FILE == ROOT / "schema" / "schema.yaml"
