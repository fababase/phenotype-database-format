"""
The command line: python app/validation.py <CSV files, a folder of CSV files, or a .xlsx file> [--out FOLDER]
"""
import subprocess
import sys

import pytest

from helpers import ROOT, SCHEMA, SCORE, as_csv, error, make_workbook, passes
from validation import main, summary

FIRST_LINE = f"Checking against schema version {SCHEMA.version}"


def test_folder_that_passes(dataset, capsys):
    tables, _ = passes(dataset.files())
    assert main([str(dataset.folder)]) == 0
    assert capsys.readouterr().out.splitlines() == [FIRST_LINE, *summary(tables, SCHEMA)]


def test_files_given_one_by_one(dataset, capsys):
    assert main([str(path) for _, path in dataset.files()]) == 0


def test_collection_sheet(dataset, tmp_path, capsys):
    tables, _ = passes([("sheet.xlsx", make_workbook(dataset, tmp_path / "sheet.xlsx"))])
    assert main([str(tmp_path / "sheet.xlsx")]) == 0
    assert capsys.readouterr().out.splitlines() == [FIRST_LINE, *summary(tables, SCHEMA)]


def test_folder_that_fails(dataset, capsys):
    dataset.set("Phenotype", SCORE, "Score", "n.a.")
    message = error(dataset.files())
    assert main([str(dataset.folder)]) == 1
    assert capsys.readouterr().out.splitlines() == [FIRST_LINE, f"Validation failed: {message}"]


def test_notices(dataset, capsys):
    dataset.write("Germplasm", dataset.read("Germplasm"), delimiter=";")
    assert main([str(dataset.folder)]) == 0
    assert capsys.readouterr().out.splitlines()[1] == "Notice: Germplasm.csv is separated by semicolons."


def test_other_files_in_the_folder_are_skipped(dataset, capsys):
    """Excel's lock files (~$...), and files that are not CSV or .xlsx."""
    (dataset.folder / "~$Germplasm.csv").write_bytes(b"\0")
    (dataset.folder / "~$sheet.xlsx").write_bytes(b"\0")
    (dataset.folder / "notes.txt").write_text("Notes")
    assert main([str(dataset.folder)]) == 0


def test_folder_without_tables(tmp_path, capsys):
    assert main([str(tmp_path)]) == 1
    assert capsys.readouterr().out.splitlines() == [FIRST_LINE, "Validation failed: No files given."]


@pytest.mark.parametrize("source", ["CSV files", "collection sheet"])
def test_out_writes_tables_that_pass_again_unchanged(dataset, tmp_path, capsys, source):
    original, _ = passes(dataset.files())
    path = dataset.folder if source == "CSV files" else make_workbook(dataset, tmp_path / "sheet.xlsx")
    out = tmp_path / "out" / "tables"
    assert main([str(path), "--out", str(out)]) == 0
    assert capsys.readouterr().out.splitlines()[-1] == f"Wrote the tables to {out}"
    assert sorted(path.name for path in out.iterdir()) == sorted(f"{name}.csv" for name in SCHEMA.tables)
    tables, notices = passes([(path.name, path) for path in out.iterdir()])
    assert notices == []
    assert as_csv(tables) == as_csv(original)


def test_out_cannot_be_the_folder_read_from(dataset, capsys):
    with pytest.raises(SystemExit) as raised:
        main([str(dataset.folder), "--out", str(dataset.folder)])
    assert raised.value.code == 2
    assert "--out has to be a different folder than the one the tables are read from" in capsys.readouterr().err


def test_path_that_does_not_exist(tmp_path, capsys):
    missing = tmp_path / "missing"
    with pytest.raises(SystemExit) as raised:
        main([str(missing)])
    assert raised.value.code == 2
    assert f"{missing} does not exist" in capsys.readouterr().err


def test_runs_as_a_script(dataset):
    result = subprocess.run([sys.executable, str(ROOT / "app" / "validation.py"), str(dataset.folder)],
                            capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    assert result.stdout.splitlines()[1].startswith("Validation successful!")
