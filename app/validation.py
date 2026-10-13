"""
Checks phenotype database tables against the schema in schema.yaml.

The tables come either as CSV files, one per table and named after it (Germplasm.csv, SeedLot.csv, ...),
or as one filled-in collection sheet (.xlsx). Checking stops at the first error, with a message that says
where it is and how to fix it.

From the command line:
    python validation.py <CSV files, a folder of CSV files, or a .xlsx file> [--out FOLDER]
"""
import argparse
import csv
import difflib
import io
import re
import sys
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

import openpyxl
import pandas as pd
import yaml

HERE = Path(__file__).resolve().parent

COLUMN_TYPES = {"id", "text", "long_text", "integer", "number", "date", "coordinates", "features"}
# Feature types: c = text, I = whole number, d = real number. An empty Type means c.
FEATURE_TYPES = ("c", "I", "d")

DECIMAL = r"-?\d+(?:\.\d+)?"
INTEGER = re.compile(r"-?\d+")
NUMBER = re.compile(rf"{DECIMAL}(?:[eE][-+]?\d+)?")
DATE = re.compile(r"\d{4}-\d{2}-\d{2}")
COORDINATES = re.compile(rf"{DECIMAL};{DECIMAL}")
RANGE = re.compile(rf"({NUMBER.pattern})\.\.({NUMBER.pattern})")
ID = re.compile(r"[A-Za-z0-9_]+")

# CSV separators to recognise, and how to name them in notices
DELIMITERS = {",": "commas", ";": "semicolons", "\t": "tabs"}


class ValidationError(ValueError):
    """
    Raised when the data breaks a rule of the schema.
    Any other exception from the validation is a bug in the validator, not a problem with the data.
    """


# ---------------------------------------------------------------- Schema

@dataclass
class Column:
    name: str
    type: str
    required: bool = False
    unique: bool = False
    links_to: str | None = None


@dataclass
class TableDef:
    name: str
    code: str
    required: bool
    columns: dict[str, Column]
    sheet: str       # sheet name in the collection sheet
    descriptor: str  # first cell of the collection sheet's row of column descriptions

    @property
    def id_column(self) -> str:
        """The ID column, which is always the first column."""
        return next(iter(self.columns))

    def add_hint(self) -> str:
        return f"Add {self.name}.csv, or the sheet '{self.sheet}' to the workbook."


@dataclass
class Schema:
    version: str
    missing_values: set[str]  # lower case, including "" for an empty cell
    tables: dict[str, TableDef]
    rules: list[str]
    ignored_sheets: set[str]  # lower case

    def match(self, name: str) -> str | None:
        """The table that a file stem or sheet name stands for: its table name, code or sheet name, in any case."""
        key = name.strip().lower()
        for table in self.tables.values():
            if key in (table.name.lower(), table.code.lower(), table.sheet.lower()):
                return table.name
        return None


def default_schema_file() -> Path:
    """schema.yaml next to this file (as when deployed), or else in the repository's schema folder."""
    for path in (HERE / "schema.yaml", HERE.parent / "schema" / "schema.yaml"):
        if path.exists():
            return path
    raise FileNotFoundError("Could not find schema.yaml next to validation.py or in ../schema/")


def load_schema(path: Path | None = None) -> Schema:
    """Reads the schema from schema.yaml. Raises ValueError if the file itself is inconsistent."""
    raw = yaml.safe_load((path or default_schema_file()).read_text(encoding="utf-8"))
    sheets = raw["collection_sheet"]["sheets"]
    tables = {}
    for name, table in raw["tables"].items():
        columns = {column: Column(column, **spec) for column, spec in table["columns"].items()}
        tables[name] = TableDef(name, table["code"], table.get("required", False), columns,
                                sheets[name]["name"], sheets[name]["descriptor"])
    for table in tables.values():
        for column in table.columns.values():
            if column.type not in COLUMN_TYPES:
                raise ValueError(f"schema.yaml: unknown type '{column.type}' of {table.name}.{column.name}")
            if column.links_to and column.links_to not in tables:
                raise ValueError(f"schema.yaml: {table.name}.{column.name} links to unknown table '{column.links_to}'")
    for rule in raw.get("rules", []):
        if rule not in RULES:
            raise ValueError(f"schema.yaml: unknown rule '{rule}'")
    return Schema(
        version=str(raw["version"]),
        missing_values={""} | {str(value).strip().lower() for value in raw["missing_values"]},
        tables=tables,
        rules=raw.get("rules", []),
        ignored_sheets={str(sheet).lower() for sheet in raw["collection_sheet"].get("ignore", [])},
    )


# ---------------------------------------------------------------- Tables

@dataclass
class RawTable:
    """A table as read from a file or sheet, before any checks."""
    source: str             # "Germplasm.csv" or "sheet 'Germplasm GP'", for messages
    header: list[str]
    records: list[list[str]]
    row_numbers: list[int]  # row number of each record in the file or sheet; the header is row 1


@dataclass
class Table:
    """A table whose columns match the schema. All values are text, in the schema's column order."""
    definition: TableDef
    source: str
    data: pd.DataFrame
    missing: pd.DataFrame  # True where a cell counts as missing
    row_numbers: list[int]

    @property
    def name(self) -> str:
        return self.definition.name

    def where(self, i: int, column: str) -> str:
        return f"{self.source}, row {self.row_numbers[i]}, column {column}"

    def values(self, column: str) -> pd.Series:
        """The values of a column that are not missing."""
        return self.data[column][~self.missing[column]]

    def to_csv(self) -> str:
        """The table as CSV: comma-separated, a header row, dates YYYY-MM-DD and missing values as empty cells."""
        return self.data.mask(self.missing, "").to_csv(index=False, lineterminator="\n")


def cell_text(value) -> str:
    """The text of an Excel cell. Dates become YYYY-MM-DD, and numbers are written without exponents."""
    if value is None:
        return ""
    if isinstance(value, datetime):
        return value.date().isoformat() if value.time() == datetime.min.time() else value.isoformat(sep=" ")
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, float):
        return format(Decimal(repr(value)), "f")
    return str(value)


def read_csv(name: str, path: Path, notice: Callable[[str], None]) -> RawTable:
    """Reads a CSV file in UTF-8 or Windows encoding, separated by commas, semicolons or tabs."""
    content = path.read_bytes()
    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError:
        try:
            text = content.decode("cp1252")
        except UnicodeDecodeError:
            raise ValidationError(f"{name}: could not read the text of the file. Save it as 'CSV UTF-8'.") from None
        notice(f"{name} is not UTF-8, so it was read as Windows text.")
    first_line = text.split("\n", 1)[0]
    delimiter = max(DELIMITERS, key=first_line.count)
    if delimiter != ",":
        notice(f"{name} is separated by {DELIMITERS[delimiter]}.")
    try:
        rows = list(csv.reader(io.StringIO(text, newline=""), delimiter=delimiter))
    except csv.Error as e:
        raise ValidationError(f"{name}: could not read the file as CSV ({e}).") from None
    if not rows:
        raise ValidationError(f"{name} is empty. Its first row has to hold the column names.")
    return RawTable(name, rows[0], rows[1:], list(range(2, len(rows) + 1)))


def read_workbook(name: str, path: Path, schema: Schema) -> list[tuple[str, RawTable]]:
    """Reads the sheets of a collection sheet. Returns (table name, table) for each sheet that is a table."""
    try:
        wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    except Exception as e:
        raise ValidationError(f"Could not open {name} as an Excel workbook ({e}).") from None
    try:
        found = []
        for ws in wb.worksheets:
            if ws.title.strip().lower() in schema.ignored_sheets:
                continue
            source = f"sheet '{ws.title}'"
            table = schema.match(ws.title)
            if table is None:
                raise ValidationError(f"{source} is not a table of the schema. Rename it after its table "
                                      f"({', '.join(schema.tables)}), or delete it.")
            rows = [[cell_text(value) for value in row] for row in ws.iter_rows(values_only=True)]
            if not rows:
                raise ValidationError(f"{source} is empty. Put the column names in row 1, or delete the sheet.")
            # Skip the row of column descriptions under the header, if the sheet has it
            start = 1
            if len(rows) > 1 and rows[1] and rows[1][0].strip().lower() == schema.tables[table].descriptor.lower():
                start = 2
            found.append((table, RawTable(source, rows[0], rows[start:], list(range(start + 1, len(rows) + 1)))))
        return found
    finally:
        wb.close()


def load_files(files: list[tuple[str, Path]], schema: Schema, notice: Callable[[str], None]) -> dict[str, RawTable]:
    """
    Reads the tables from CSV files or one collection sheet.
    Parameters:
        files: (file name, path) of each file. The file name says which table a CSV file is.
    Returns:
        dict: table name -> table as read.
    """
    if not files:
        raise ValidationError("No files given.")
    for name, _ in files:
        if Path(name).suffix.lower() not in (".csv", ".xlsx"):
            raise ValidationError(f"{name} is not a CSV or .xlsx file. "
                                  "Give one CSV file per table, or one collection sheet (.xlsx).")
    workbooks = [file for file in files if Path(file[0]).suffix.lower() == ".xlsx"]
    if workbooks and len(files) > 1:
        raise ValidationError("Give either one collection sheet (.xlsx) or CSV files, not both or several workbooks.")

    if workbooks:
        found = read_workbook(*workbooks[0], schema)
    else:
        found = []
        for name, path in files:
            table = schema.match(Path(name).stem)
            if table is None:
                raise ValidationError(f"{name} is not named after a table of the schema. Name each file after "
                                      f"its table: {', '.join(f'{t}.csv' for t in schema.tables)}.")
            found.append((table, read_csv(name, path, notice)))

    raws = {}
    for table, raw in found:
        if table in raws:
            raise ValidationError(f"{raw.source} and {raws[table].source} are both the {table} table. Keep only one.")
        raws[table] = raw
    return raws


def build_table(definition: TableDef, raw: RawTable, schema: Schema) -> Table:
    """
    Matches the columns of a table to the schema: in any order, optional columns may be left out,
    and unknown columns are an error. Rows in which every cell is missing are dropped.
    """
    width = max([len(raw.header)] + [len(record) for record in raw.records])
    header = [name.strip() for name in raw.header] + [""] * (width - len(raw.header))
    records = [record + [""] * (width - len(record)) for record in raw.records]
    keep = [i for i, record in enumerate(records)
            if any(value.strip().lower() not in schema.missing_values for value in record)]
    records = [records[i] for i in keep]
    row_numbers = [raw.row_numbers[i] for i in keep]

    positions = {}
    for j, name in enumerate(header):
        if not name:
            if any(record[j].strip() for record in records):
                raise ValidationError(f"{raw.source}, column {j + 1} has values but no column name in row 1. "
                                      "Add the column name, or delete the column.")
            continue
        if name not in definition.columns:
            close = difflib.get_close_matches(name, definition.columns, n=1)
            hint = (f"Did you mean '{close[0]}'?" if close
                    else f"The columns of {definition.name} are: {', '.join(definition.columns)}.")
            raise ValidationError(f"{raw.source}: '{name}' is not a column of {definition.name}. {hint}")
        if name in positions:
            raise ValidationError(f"{raw.source}: the column '{name}' appears twice.")
        positions[name] = j
    for column in definition.columns.values():
        if column.required and column.name not in positions:
            raise ValidationError(f"{raw.source}: the column '{column.name}' is missing. "
                                  f"It is required in {definition.name}.")

    data = pd.DataFrame({name: [record[positions[name]] if name in positions else "" for record in records]
                         for name in definition.columns}, dtype=str)
    missing = pd.DataFrame({name: data[name].str.strip().str.lower().isin(schema.missing_values)
                            for name in definition.columns})
    return Table(definition, raw.source, data, missing, row_numbers)


# ---------------------------------------------------------------- Checks

def fail_first(table: Table, column: str, mask: pd.Series, describe: Callable[[int], str]) -> None:
    """Raises a ValidationError for the first row where mask is True. describe(i) says what is wrong in row i."""
    rows = mask.to_numpy().nonzero()[0]
    if len(rows) == 0:
        return
    i = int(rows[0])
    others = len(rows) - 1
    more = ""
    if others == 1:
        more = " (1 more row in this column has the same problem.)"
    elif others > 1:
        more = f" ({others} more rows in this column have the same problem.)"
    raise ValidationError(f"{table.where(i, column)}: {describe(i)}{more}")


def id_problem(value: str) -> str | None:
    if ID.fullmatch(value):
        return None
    if ID.fullmatch(value.strip()):
        return f"'{value}' has spaces before or after it. Remove them."
    bad = list(dict.fromkeys(c for c in value.strip() if not ID.fullmatch(c)))
    names = ["a space" if c.isspace() else f"'{c}'" for c in bad]
    named = names[0] if len(names) == 1 else f"{', '.join(names[:-1])} and {names[-1]}"
    message = (f"'{value}' contains {named}. IDs can only hold the letters a-z and A-Z without accents, "
               "the digits 0-9 and '_'.")
    # Letters such as 'ø' have no obvious replacement, so a fix is only suggested for other characters
    if any(c.isalpha() for c in bad):
        return message
    return f"{message} Use '_' instead: {re.sub(r'[^A-Za-z0-9_]+', '_', value.strip())}"


def integer_problem(value: str) -> str | None:
    if INTEGER.fullmatch(value):
        return None
    return f"'{value}' is not a whole number. Write digits only, e.g. 12."


def number_problem(value: str) -> str | None:
    if NUMBER.fullmatch(value):
        return None
    if NUMBER.fullmatch(value.replace(",", ".")):
        return f"'{value}' has ',' as the decimal mark. Use '.' instead: {value.replace(',', '.')}"
    return f"'{value}' is not a number. Write only the number, with '.' as the decimal mark and no units or words, e.g. 3.5."


def date_problem(value: str) -> str | None:
    if DATE.fullmatch(value):
        try:
            date.fromisoformat(value)
            return None
        except ValueError:
            return f"'{value}' is not a real date."
    if DATE.match(value):
        return f"'{value}' holds more than a date. Write only the date, as YYYY-MM-DD."
    return f"'{value}' is not a date written YYYY-MM-DD, e.g. 2023-05-17."


def coordinates_problem(value: str) -> str | None:
    if COORDINATES.fullmatch(value):
        return None
    hint = " Remove the spaces." if COORDINATES.fullmatch(re.sub(r"\s", "", value)) else ""
    return f"'{value}' is not written latitude;longitude in decimal degrees, e.g. 56.170308;10.207013.{hint}"


# What is wrong with a value of a type, or None if nothing is. Features cells are checked separately.
TYPE_PROBLEMS: dict[str, Callable[[str], str | None]] = {
    "id": id_problem,
    "integer": integer_problem,
    "number": number_problem,
    "date": date_problem,
    "coordinates": coordinates_problem,
}


def check_cells(table: Table) -> None:
    """Checks each column: required values, types and unique values. IDs are unique ignoring case."""
    for column in table.definition.columns.values():
        values = table.data[column.name]
        missing = table.missing[column.name]
        if column.required:
            fail_first(table, column.name, missing, lambda i: (
                f"'{values.iat[i]}' counts as a missing value" if values.iat[i].strip() else "the cell is empty"
            ) + f", but {column.name} is required. Fill it in.")
        problem = TYPE_PROBLEMS.get(column.type)
        if problem:
            problems = pd.Series([None if m else problem(v) for v, m in zip(values, missing)], dtype=object)
            fail_first(table, column.name, problems.notna(), lambda i: problems.iat[i])
        if column.unique:
            keys = values.str.lower() if column.type == "id" else values

            def describe(i: int) -> str:
                first = int((keys == keys.iat[i]).to_numpy().nonzero()[0][0])
                where = f"'{values.iat[i]}' is also in row {table.row_numbers[first]}"
                if values.iat[first] == values.iat[i]:
                    return f"{where}. Each {column.name} has to be unique."
                return (f"{where}, written '{values.iat[first]}'. Each {column.name} has to be unique, "
                        "and upper and lower case do not count as different.")
            fail_first(table, column.name, keys.duplicated() & ~missing, describe)


def check_links(table: Table, column: Column, tables: dict[str, Table], schema: Schema) -> None:
    """Checks that each value of a column that refers to another table is an ID in that table."""
    values = table.data[column.name]
    filled = ~table.missing[column.name]
    target = tables.get(column.links_to)
    if target is None:
        fail_first(table, column.name, filled, lambda i: (
            f"'{values.iat[i]}' refers to {column.links_to}, but there is no {column.links_to} table. "
            + schema.tables[column.links_to].add_hint()))
        return
    id_column = target.definition.id_column
    ids = set(target.values(id_column))
    loose = {i.strip().lower(): i for i in ids}

    def describe(i: int) -> str:
        value = values.iat[i]
        near = loose.get(value.strip().lower())
        hint = f"Did you mean '{near}'?" if near else f"Check the spelling, or add it to {target.name}."
        return (f"'{value}' is not in column {id_column} of {target.source}. "
                f"IDs have to match exactly, character for character. {hint}")

    fail_first(table, column.name, filled & ~values.isin(ids), describe)


def check_feature_definitions(table: Table | None) -> dict[str, tuple[str, str | None]]:
    """
    Checks the Features table: Type has to be c, I, d or empty, and Vocabulary has to be a ';'-separated
    list for Type c and a min..max range for I and d. FTIDs are checked as IDs by `check_cells`.
    Returns:
        dict: FTID -> (Type, Vocabulary), with an empty Type given as "c" and an empty Vocabulary as None.
    """
    if table is None:
        return {}
    features = {}
    for i in range(len(table.data)):
        row = table.data.iloc[i]
        missing = table.missing.iloc[i]
        ftid = row["FTID"]
        ftype = "c" if missing["Type"] else row["Type"]
        if ftype not in FEATURE_TYPES:
            raise ValidationError(f"{table.where(i, 'Type')}: '{ftype}' is not a feature type. Use c (text), "
                                  "I (whole number) or d (real number), or leave it empty for text.")

        vocabulary = None if missing["Vocabulary"] else row["Vocabulary"]
        if vocabulary is not None:
            if ftype == "c":
                terms = vocabulary.split(";")
                if any(term == "" or term != term.strip() or "=" in term for term in terms):
                    raise ValidationError(f"{table.where(i, 'Vocabulary')}: '{vocabulary}' is not a valid "
                                          "vocabulary. For Type c, list the allowed values separated by ';', "
                                          "without spaces around ';', e.g. leaf;root;stem.")
            else:
                match = RANGE.fullmatch(vocabulary)
                if not match or float(match[1]) > float(match[2]):
                    raise ValidationError(f"{table.where(i, 'Vocabulary')}: '{vocabulary}' is not a valid "
                                          f"vocabulary. For Type {ftype}, give a range min..max with min no "
                                          "larger than max, e.g. 0..100.")

        features[ftid] = (ftype, vocabulary)
    return features


def check_feature_cells(table: Table, column: str, features: dict[str, tuple[str, str | None]],
                        schema: Schema) -> None:
    """
    Checks a Features column. A cell is empty, or holds entries FTID1=value1;FTID2=value2 with no spaces
    around '=' or ';'. Each FTID has to be in the Features table and can appear only once per cell,
    and each value has to fit its feature's Type and Vocabulary.
    """
    for i, (cell, missing) in enumerate(zip(table.data[column], table.missing[column])):
        if missing:
            continue
        where = f"{table.where(i, column)}: invalid Features cell '{cell}'"
        seen = set()
        for entry in cell.split(";"):
            ftid, sep, value = entry.partition("=")
            if not sep or not ftid or not value or "=" in value or ftid != ftid.strip() or value != value.strip():
                raise ValidationError(f"{where}. Write each entry as FTID=value, separated by ';', "
                                      "without spaces around '=' or ';'.")
            if ftid not in features:
                hint = "" if features else f" There is no Features table. {schema.tables['Features'].add_hint()}"
                raise ValidationError(f"{where}. '{ftid}' is not an FTID in the Features table.{hint}")
            if ftid in seen:
                raise ValidationError(f"{where}. '{ftid}' appears more than once.")
            seen.add(ftid)
            problem = feature_value_problem(value, ftid, *features[ftid])
            if problem:
                raise ValidationError(f"{where}. {problem}")


def feature_value_problem(value: str, ftid: str, ftype: str, vocabulary: str | None) -> str | None:
    """
    Returns what is wrong with a value of a feature, or None if it fits the feature's Type and Vocabulary.
    The Vocabulary is assumed to have passed `check_feature_definitions`.
    """
    if ftype == "I" and not INTEGER.fullmatch(value):
        return f"'{value}' is not a whole number, as feature {ftid} (Type I) needs."
    if ftype == "d" and not NUMBER.fullmatch(value):
        return f"'{value}' is not a number with '.' as the decimal mark, as feature {ftid} (Type d) needs."
    if vocabulary is None:
        return None
    if ftype == "c":
        if value not in vocabulary.split(";"):
            return f"'{value}' is not in the vocabulary of feature {ftid} ({vocabulary})."
    else:
        low, high = (float(end) for end in RANGE.fullmatch(vocabulary).groups())
        if not low <= float(value) <= high:
            return f"{value} is outside the range of feature {ftid} ({vocabulary})."
    return None


# ---------------------------------------------------------------- Rules that span tables

def climate_unit_in_experiment(tables: dict[str, Table]) -> None:
    """A Climate UNID that is filled in has to belong to the row's EXPID."""
    climate = tables.get("Climate")
    if climate is None:
        return
    units = tables["ExperimentalUnit"]
    unit_experiment = dict(zip(units.data["UNID"], units.data["EXPID"]))
    unids = climate.data["UNID"]
    expids = climate.data["EXPID"]
    wrong = ~climate.missing["UNID"] & (unids.map(unit_experiment) != expids)
    fail_first(climate, "UNID", wrong, lambda i: (
        f"unit '{unids.iat[i]}' belongs to experiment '{unit_experiment[unids.iat[i]]}', but this row's EXPID "
        f"is '{expids.iat[i]}'. Fix the EXPID or the UNID, or leave UNID empty if the value applies to all "
        "units in the experiment."))


def one_intervention_per_unit(tables: dict[str, Table]) -> None:
    """
    In an experiment with interventions, every unit has a row in ExperimentIntervention.
    That it has no more than one is checked by UNID being unique there.
    """
    interventions = tables.get("ExperimentIntervention")
    if interventions is None:
        return
    units = tables["ExperimentalUnit"]
    unit_experiment = dict(zip(units.data["UNID"], units.data["EXPID"]))
    with_row = set(interventions.values("UNID"))
    experiments = {unit_experiment[unid] for unid in with_row}
    lacking = units.data["EXPID"].isin(experiments) & ~units.data["UNID"].isin(with_row)
    fail_first(units, "UNID", lacking, lambda i: (
        f"unit '{units.data['UNID'].iat[i]}' has no row in {interventions.source}, but other units in "
        f"experiment '{units.data['EXPID'].iat[i]}' do. In experiments with interventions, every unit needs "
        "one row, control units included."))


def every_experiment_has_a_unit(tables: dict[str, Table]) -> None:
    """Every experiment has at least one unit."""
    experiments = tables["Experiment"]
    units = tables["ExperimentalUnit"]
    expids = experiments.data["EXPID"]
    without = ~experiments.missing["EXPID"] & ~expids.isin(set(units.values("EXPID")))
    fail_first(experiments, "EXPID", without, lambda i: (
        f"experiment '{expids.iat[i]}' has no units in {units.source}. Every experiment needs at least one unit."))


RULES: dict[str, Callable[[dict[str, Table]], None]] = {
    "climate_unit_in_experiment": climate_unit_in_experiment,
    "one_intervention_per_unit": one_intervention_per_unit,
    "every_experiment_has_a_unit": every_experiment_has_a_unit,
}


# ---------------------------------------------------------------- Validation

def validate(raws: dict[str, RawTable], schema: Schema,
             notice: Callable[[str], None] = lambda message: None) -> dict[str, Table]:
    """
    Checks the tables against the schema, in this order, and stops at the first error:
    which tables there are, their columns, the values in each column, the Features table,
    the links between tables, the Features cells, and the rules that span tables.
    Returns:
        dict: table name -> checked table, in the schema's order.
    Raises:
        ValidationError: At the first error, saying where it is and how to fix it.
    """
    for definition in schema.tables.values():
        if definition.name not in raws:
            if definition.required:
                raise ValidationError(f"The {definition.name} table is missing. {definition.add_hint()}")
            notice(f"There is no {definition.name} table. It is optional, so it was skipped.")

    tables = {name: build_table(definition, raws[name], schema)
              for name, definition in schema.tables.items() if name in raws}
    for table in tables.values():
        if table.definition.required and table.data.empty:
            raise ValidationError(f"{table.source} has no rows, but {table.name} needs at least one.")

    for table in tables.values():
        check_cells(table)
    features = check_feature_definitions(tables.get("Features"))
    for table in tables.values():
        for column in table.definition.columns.values():
            if column.links_to:
                check_links(table, column, tables, schema)
    for table in tables.values():
        for column in table.definition.columns.values():
            if column.type == "features":
                check_feature_cells(table, column.name, features, schema)
    for rule in schema.rules:
        RULES[rule](tables)
    return tables


def validate_files(files: list[tuple[str, Path]], schema: Schema | None = None,
                   notice: Callable[[str], None] = lambda message: None) -> dict[str, Table]:
    """Reads the tables from CSV files or one collection sheet, and checks them. See `load_files` and `validate`."""
    schema = schema or load_schema()
    return validate(load_files(files, schema, notice), schema, notice)


def summary(tables: dict[str, Table], schema: Schema) -> list[str]:
    """Lines saying that the tables passed, and how many rows each has."""
    return ([f"Validation successful! All {len(tables)} tables pass schema version {schema.version}."]
            + [f"{table.name}: {len(table.data)} row{'' if len(table.data) == 1 else 's'}, from {table.source}"
               for table in tables.values()])


def write_tables(tables: dict[str, Table], folder: Path) -> None:
    """Writes each table to <folder>/<table>.csv, in UTF-8."""
    folder.mkdir(parents=True, exist_ok=True)
    for name, table in tables.items():
        (folder / f"{name}.csv").write_text(table.to_csv(), encoding="utf-8", newline="")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Check phenotype database tables against the schema. "
                                                 "Stops at the first error.")
    parser.add_argument("paths", nargs="+", type=Path,
                        help="CSV files named after their tables, a folder of them, or one collection sheet (.xlsx)")
    parser.add_argument("--out", type=Path,
                        help="if the tables pass, write them to this folder as CSV files "
                             "(UTF-8, comma-separated, dates YYYY-MM-DD)")
    args = parser.parse_args(argv)

    files = []
    for path in args.paths:
        if path.is_dir():
            files += [(p.name, p) for p in sorted(path.iterdir())
                      if p.suffix.lower() in (".csv", ".xlsx") and not p.name.startswith("~$")]
        elif path.is_file():
            files.append((path.name, path))
        else:
            parser.error(f"{path} does not exist")
    if args.out and any(path.parent.resolve() == args.out.resolve() for _, path in files):
        parser.error("--out has to be a different folder than the one the tables are read from")

    schema = load_schema()
    print(f"Checking against schema version {schema.version}")
    try:
        tables = validate_files(files, schema, notice=lambda message: print(f"Notice: {message}"))
    except ValidationError as e:
        print(f"Validation failed: {e}")
        return 1
    print("\n".join(summary(tables, schema)))
    if args.out:
        write_tables(tables, args.out)
        print(f"Wrote the tables to {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
