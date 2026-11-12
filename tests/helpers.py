"""
Helpers shared by the tests.

valid/ holds one valid dataset, one CSV file per table, and contributors.yaml. Each test works on a copy of it, and a
broken dataset is that copy with one thing changed, so that it breaks exactly one rule. The dataset is also the source of the
examples in schema.yaml and of the worked example in schema.md, which are copied from it: change them with it.
"""
import csv
import io
import json
from collections.abc import Callable
from datetime import datetime
from pathlib import Path

import openpyxl
import pytest

import build
import collection_sheet
from validation import CONTRIBUTORS_FILE, DATE, Checked, Table, ValidationError, cell_text, load_schema, validate_files

ROOT = Path(__file__).resolve().parent.parent
SCHEMA = load_schema()
VALID = Path(__file__).resolve().parent / "valid"

OPTIONAL_TABLES = ["ExperimentIntervention", "Management", "ClimateDescription", "Climate", "Features"]

# The two experiments in the valid dataset, and rows of them that tests change
TRIAL = "nordbean_irrigation_northfield_2025"
UNIT = f"{TRIAL}_plot101"
SCORE = f"{TRIAL}_000001"
GREENHOUSE = "nordbean_leaf_spectra_greenhouse_2025"
POT = f"{GREENHOUSE}_pot01"
SPECTRUM = f"{GREENHOUSE}_000005"  # a Phenotype row with Features wavelength=1450;tissue=young leaf

# The commit that a merge is built with in the tests
COMMIT = "0123456789abcdef0123456789abcdef01234567"

# Read once rather than for every test, which is slow when the repository is on a network drive
VALID_FILES = {path.name: path.read_bytes() for path in VALID.iterdir()}
BLANK_SHEET = collection_sheet.build(SCHEMA)


class Dataset:
    """A copy of the valid dataset in a folder, with ways to change its CSV files."""

    def __init__(self, folder: Path):
        folder.mkdir()
        for name, content in VALID_FILES.items():
            (folder / name).write_bytes(content)
        self.folder = folder

    def path(self, table: str) -> Path:
        return self.folder / f"{table}.csv"

    def files(self) -> list[tuple[str, Path]]:
        """(file name, path) of each file in the folder, sorted by name, as validate_files takes them."""
        return [(path.name, path) for path in sorted(self.folder.iterdir(), key=lambda path: path.name)]

    def read(self, table: str) -> list[list[str]]:
        """The rows of a table's file, header first."""
        with self.path(table).open(encoding="utf-8", newline="") as f:
            return list(csv.reader(f))

    def write(self, table: str, rows: list[list[str]], delimiter: str = ",", encoding: str = "utf-8",
              line_end: str = "\n") -> None:
        with self.path(table).open("w", encoding=encoding, newline="") as f:
            csv.writer(f, delimiter=delimiter, lineterminator=line_end).writerows(rows)

    def ids(self, table: str) -> list[str]:
        """The value in the first column of each row below the header."""
        return [row[0] if row else "" for row in self.read(table)[1:]]

    def row(self, table: str, rid: str) -> int:
        """The row number in the file of the row with this ID. The header is row 1."""
        return self.ids(table).index(rid) + 2

    def where(self, table: str, rid: str, column: str) -> str:
        """Where a cell is, as the validator's messages say it, e.g. "Phenotype.csv, row 2, column Score"."""
        return f"{table}.csv, row {self.row(table, rid)}, column {column}"

    def get(self, table: str, rid: str, column: str) -> str:
        rows = self.read(table)
        return rows[self.row(table, rid) - 1][rows[0].index(column)]

    def set(self, table: str, rid: str, column: str, value: str) -> None:
        """Sets the cell in the given column of the row with this ID."""
        rows = self.read(table)
        rows[self.row(table, rid) - 1][rows[0].index(column)] = value
        self.write(table, rows)

    def add_row(self, table: str, **values: str) -> None:
        """Adds a row at the end, with the given values and the other cells empty."""
        rows = self.read(table)
        rows.append([values.get(column, "") for column in rows[0]])
        self.write(table, rows)

    def delete_row(self, table: str, rid: str) -> None:
        rows = self.read(table)
        del rows[self.row(table, rid) - 1]
        self.write(table, rows)

    def add_column(self, table: str, name: str, values: tuple[str, ...] = ()) -> None:
        """Adds a column at the end, with the given values in the first rows and the other cells empty."""
        rows = self.read(table)
        rows[0].append(name)
        for i, row in enumerate(rows[1:]):
            row.append(values[i] if i < len(values) else "")
        self.write(table, rows)

    def drop_column(self, table: str, column: str) -> None:
        rows = self.read(table)
        j = rows[0].index(column)
        self.write(table, [row[:j] + row[j + 1:] for row in rows])

    def rename_column(self, table: str, old: str, new: str) -> None:
        rows = self.read(table)
        rows[0][rows[0].index(old)] = new
        self.write(table, rows)

    def rename_file(self, table: str, name: str) -> None:
        self.path(table).rename(self.folder / name)

    def drop_table(self, table: str) -> None:
        self.path(table).unlink()

    @property
    def contributors(self) -> Path:
        return self.folder / CONTRIBUTORS_FILE

    def credit(self) -> list[tuple[str, Path]]:
        """contributors.yaml, as validate_files takes it, to give with a collection sheet."""
        return [(CONTRIBUTORS_FILE, self.contributors)]

    def edit_contributors(self, old: str, new: str) -> None:
        """Replaces the first occurrence of old in contributors.yaml with new."""
        text = self.contributors.read_text(encoding="utf-8")
        assert old in text, old
        self.contributors.write_text(text.replace(old, new, 1), encoding="utf-8", newline="")

    def credit_experiment(self, expid: str) -> None:
        """Adds an experiment to the experiments of the last person in contributors.yaml."""
        self.edit_contributors("\nfunding:", f"\n      - {expid}\nfunding:")

    def line(self, text: str, occurrence: int = 1) -> int:
        """The number of the line of contributors.yaml that holds text, the first one or a later one."""
        lines = self.contributors.read_text(encoding="utf-8").splitlines()
        return [number for number, line in enumerate(lines, start=1) if text in line][occurrence - 1]


def excel_value(text: str, column_type: str):
    """
    The value someone filling in the collection sheet by hand would leave in the cell: a date as an Excel date,
    and a number as a number, as long as the validator reads it back as the same text.
    """
    if column_type == "date" and DATE.fullmatch(text):
        try:
            return datetime.fromisoformat(text)
        except ValueError:
            return text
    if column_type in ("integer", "number"):
        for convert in (int, float):
            try:
                value = convert(text)
            except ValueError:
                continue
            if cell_text(value) == text:
                return value
    return text


def make_workbook(dataset: Dataset, path: Path, help_row: bool = True) -> Path:
    """
    Fills a blank collection sheet with the dataset's tables, from row 3 (below the row of help text), or from
    row 2 with the help text removed. Tables the dataset lacks keep their blank sheet.
    """
    wb = openpyxl.load_workbook(io.BytesIO(BLANK_SHEET))
    for name, definition in SCHEMA.tables.items():
        ws = wb[name]
        if not help_row:
            ws.delete_rows(2)
        if not dataset.path(name).exists():
            continue
        header = [cell_text(cell.value) for cell in ws[1]]
        rows = dataset.read(name)
        first = 3 if help_row else 2
        for i, record in enumerate(rows[1:]):
            for column, text in zip(rows[0], record):
                if text:
                    value = excel_value(text, definition.columns[column].type)
                    ws.cell(first + i, header.index(column) + 1, value)
    wb.save(path)
    return path


def edit_workbook(path: Path, change: Callable[[openpyxl.Workbook], None]) -> None:
    wb = openpyxl.load_workbook(path)
    change(wb)
    wb.save(path)


def set_sheet_cell(path: Path, table: str, row: int, column: str, value) -> None:
    """Sets a cell in the sheet of a table in a workbook. row is the row number in the sheet."""
    def change(wb: openpyxl.Workbook) -> None:
        ws = wb[table]
        header = [cell_text(cell.value) for cell in ws[1]]
        ws.cell(row, header.index(column) + 1, value)
    edit_workbook(path, change)


def rename_sheet(path: Path, old: str, new: str) -> None:
    """Renames a sheet of a workbook. Goes through a temporary title, as openpyxl ignores case when comparing titles."""
    def rename(wb: openpyxl.Workbook) -> None:
        wb[old].title = "renaming"
        wb["renaming"].title = new
    edit_workbook(path, rename)


def check(files: list[tuple[str, Path]], warnings: tuple[str, ...] = ()) -> tuple[Checked, list[str]]:
    """Validates the files, which have to pass with exactly these warnings. Returns what passed, and the notices."""
    notices = []
    warned = []
    checked = validate_files(files, SCHEMA, notice=notices.append, warning=warned.append)
    assert warned == list(warnings)
    return checked, notices


def passes(files: list[tuple[str, Path]], warnings: tuple[str, ...] = ()) -> tuple[dict[str, Table], list[str]]:
    """Validates the files, which have to pass with exactly these warnings. Returns the checked tables and the notices."""
    checked, notices = check(files, warnings)
    return checked.tables, notices


def error(files: list[tuple[str, Path]]) -> str:
    """Validates the files, which have to fail. Returns the message."""
    with pytest.raises(ValidationError) as raised:
        validate_files(files, SCHEMA)
    return str(raised.value)


def fails(files: list[tuple[str, Path]], message: str) -> None:
    """Checks that validating the files fails with exactly this message."""
    assert error(files) == message


def as_csv(tables: dict[str, Table]) -> dict[str, str]:
    """Each table as the CSV text the validator writes, to compare tables read from different files."""
    return {name: table.to_csv() for name, table in tables.items()}


# The record.yaml of a merge
RECORD = """\
title: Nordbean test dataset
doi: {doi}
access: {access}
curator:
  family_name: Keeper
  given_names: Dana
  orcid: {orcid}
  affiliations:
    - name: Northfield Agricultural College
      ror: none
"""


class Merge:
    """
    A merge folder: the valid dataset as its merged tables, record.yaml, and a crosswalk.csv in which no ID was
    changed.
    """

    def __init__(self, folder: Path, doi: str = "none", orcid: str = "none", access: str = "open"):
        folder.mkdir()
        self.folder = folder
        self.tables = Dataset(folder / "tables")
        self.record = folder / "record.yaml"
        self.record.write_text(RECORD.format(doi=doi, orcid=orcid, access=access), encoding="utf-8")
        self.crosswalk()

    @property
    def files(self) -> Path:
        return self.folder / "publish" / "files"

    def run(self, previous: "Merge | None" = None, release: build.Release | None = None,
            out: Path | None = None) -> list[str]:
        return build.build(self.folder, COMMIT, previous.folder if previous else None, release, out=out)

    def crosswalk(self, *rows: tuple[str, ...],
                  header: tuple[str, ...] = ("Contribution", "Table", "OldID", "NewID")) -> None:
        """Writes crosswalk.csv, as merge.py does, with these rows."""
        with (self.folder / "crosswalk.csv").open("w", encoding="utf-8", newline="") as f:
            csv.writer(f, lineterminator="\n").writerows([header, *rows])

    def readme(self) -> str:
        return (self.files / "README.md").read_text(encoding="utf-8")

    def section(self, heading: str) -> str:
        """The text under a heading of the README, '## heading', up to the next such heading."""
        text = self.readme()
        start = text.index(f"\n## {heading}\n\n") + len(heading) + 6
        end = text.find("\n## ", start)
        return text[start:end if end >= 0 else None].strip()

    def metadata(self) -> dict:
        return json.loads((self.folder / "publish" / "metadata.json").read_text(encoding="utf-8"))

    def release(self) -> dict:
        return json.loads((self.folder / "publish" / "release.json").read_text(encoding="utf-8"))

    def rows(self, table: str) -> list[dict[str, str]]:
        with (self.files / f"{table}.csv").open(encoding="utf-8", newline="") as f:
            return list(csv.DictReader(f))
