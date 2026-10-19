"""
The schema itself: there is exactly one schema.yaml, mistakes in it are reported, and the collection sheet
matches it.
"""
import io
import os
import shutil
import subprocess
import sys

import openpyxl
import pytest
import yaml

from helpers import ROOT, SCHEMA, TEMPLATE_BYTES, VALID
from validation import SCHEMA_FILE, cell_text, load_schema


def test_schema_yaml_has_only_one_copy():
    """schema/schema.yaml is never copied, e.g. into app/, so nothing can be checked against a stale copy."""
    copies = []
    for folder, subfolders, files in os.walk(ROOT):
        subfolders[:] = [name for name in subfolders if name != ".git"]
        copies += [(os.path.relpath(folder, ROOT), name) for name in files
                   if name.lower() in ("schema.yaml", "schema.yml")]
    assert copies == [("schema", "schema.yaml")]
    assert SCHEMA_FILE == ROOT / "schema" / "schema.yaml"


def test_schema_yaml_next_to_the_validator(tmp_path):
    """The browser app has schema.yaml next to validation.py, outside the repository: the deploy Action puts it there."""
    for path in (ROOT / "app" / "validation.py", ROOT / "app" / "requirements.txt", SCHEMA_FILE):
        shutil.copy(path, tmp_path)
    result = subprocess.run([sys.executable, str(tmp_path / "validation.py"), str(VALID)],
                            capture_output=True, text=True)
    assert result.returncode == 0, result.stderr


@pytest.mark.parametrize("change, message", [
    (lambda raw: raw["tables"]["Germplasm"]["columns"]["Name"].update(type="string"),
     "schema.yaml: unknown type 'string' of Germplasm.Name"),
    (lambda raw: raw["tables"]["SeedLot"]["columns"]["GPID"].update(links_to="Germplasms"),
     "schema.yaml: SeedLot.GPID links to unknown table 'Germplasms'"),
    (lambda raw: raw["collection_sheet"]["sheets"].pop("Germplasm"),
     "schema.yaml: Germplasm is required, so it needs a sheet in collection_sheet"),
    (lambda raw: raw["rules"].append("every_unit_has_a_score"),
     "schema.yaml: unknown rule 'every_unit_has_a_score'"),
], ids=["unknown type", "link to unknown table", "required table without a sheet", "unknown rule"])
def test_mistake_in_schema_yaml(tmp_path, change, message):
    raw = yaml.safe_load(SCHEMA_FILE.read_text(encoding="utf-8"))
    change(raw)
    path = tmp_path / "schema.yaml"
    path.write_text(yaml.safe_dump(raw, sort_keys=False), encoding="utf-8")
    with pytest.raises(ValueError) as raised:
        load_schema(path)
    assert str(raised.value) == message


def test_collection_sheet_matches_schema():
    """
    The collection sheet has a sheet for each table, named as in schema.yaml, plus the sheets the validator
    ignores. Each sheet has the table's columns in row 1, in the schema's order, and the row of column
    descriptions in row 2.
    """
    wb = openpyxl.load_workbook(io.BytesIO(TEMPLATE_BYTES), read_only=True)
    titles = [ws.title for ws in wb.worksheets]
    assert sorted(title for title in titles if title.lower() not in SCHEMA.ignored_sheets) == \
           sorted(table.sheet for table in SCHEMA.tables.values())
    assert sorted(title.lower() for title in titles if title.lower() in SCHEMA.ignored_sheets) == \
           sorted(SCHEMA.ignored_sheets)
    for name, table in SCHEMA.tables.items():
        header, descriptions = ([cell_text(value) for value in row]
                                for row in wb[table.sheet].iter_rows(max_row=2, values_only=True))
        columns = list(table.columns)
        assert header[:len(columns)] == columns, name
        assert not any(header[len(columns):]), name
        assert descriptions[0] == table.descriptor, name
    wb.close()
