"""
Broken datasets: the valid dataset with one thing changed, so that it breaks exactly one rule. Each has to fail
with exactly the message the validator gives for that rule.
"""
from datetime import datetime, time

import pytest

from helpers import (GREENHOUSE, POT, SCHEMA, SCORE, SPECTRUM, TRIAL, UNIT, Dataset, edit_workbook, error, fails,
                     make_workbook, passes, set_sheet_cell)
from validation import READ_ME_SHEET, READ_ME_TITLE

TABLES = ("Germplasm, SeedLot, Experiment, ExperimentalUnit, ExperimentIntervention, Management, "
          "PhenotypeDescription, Phenotype, ClimateDescription, Climate, Features")
ID_RULE = "IDs can only hold the letters a-z and A-Z without accents, the digits 0-9 and '_'."
START_RULE = "IDs have to start with a letter, a-z or A-Z."
NOT_A_NUMBER = ("is not a number. Write only the number, with '.' as the decimal mark and no thousands separator, "
                "units or words, e.g. 3.5.")
INFINITE = "is too large a number: it would be read as infinity."
NOT_A_LIST = ("is not a list written value1;value2. Separate the values with ';', with no spaces around it and no "
              "empty values.")
SYMBOLS = ("the symbols of a US keyboard, apart from ';' and '=', which have meanings of their own. Write other "
           "symbols in words, such as 'degrees' for '°'.")
TEXT_RULE = f"Text can only hold letters, the digits 0-9, spaces and {SYMBOLS}"
LONG_TEXT_RULE = f"Text can only hold letters, the digits 0-9, spaces, line breaks and {SYMBOLS}"
NOT_ONE_TABLE = "Give either one collection sheet (.xlsx) or CSV files, not both or several workbooks."
QUOTES = "Check its quote marks: a value that starts with \" has to end with \" too."
NO_VALUES = "has no values, but rows after it do. Delete the row. If the rows below it are not part of the table, " \
            "delete them too."
SWAPPED = "With day and month swapped, it would be {}, which fits. Check which is meant."


# ---------------------------------------------------------------- Files

def test_no_files():
    fails([], "No files given.")


@pytest.mark.parametrize("name", ["Germplasm.xls", "Germplasm.xlsm", "Germplasm.ods", "Germplasm.txt", "Germplasm"])
def test_file_of_another_type(dataset, name):
    dataset.rename_file("Germplasm", name)
    fails(dataset.files(), f"{name} is not a CSV or .xlsx file. "
                           "Give one CSV file per table, or one collection sheet (.xlsx).")


def test_csv_files_and_a_workbook(dataset, tmp_path):
    workbook = make_workbook(dataset, tmp_path / "sheet.xlsx")
    fails(dataset.files() + [("sheet.xlsx", workbook)], NOT_ONE_TABLE)


def test_two_workbooks(dataset, tmp_path):
    workbook = make_workbook(dataset, tmp_path / "sheet.xlsx")
    fails([("sheet.xlsx", workbook), ("copy.xlsx", workbook)], NOT_ONE_TABLE)


def test_file_not_named_after_a_table(dataset):
    dataset.rename_file("Germplasm", "Germplasm_2025.csv")
    fails(dataset.files(), "Germplasm_2025.csv is not named after a table of the schema. Name each file after its "
                           "table: Germplasm.csv, SeedLot.csv, Experiment.csv, ExperimentalUnit.csv, "
                           "ExperimentIntervention.csv, Management.csv, PhenotypeDescription.csv, Phenotype.csv, "
                           "ClimateDescription.csv, Climate.csv, Features.csv.")


def test_two_files_for_one_table(dataset):
    (dataset.folder / "GP.csv").write_bytes(dataset.path("Germplasm").read_bytes())
    fails(dataset.files(), "Germplasm.csv and GP.csv are both the Germplasm table. Keep only one.")


def test_empty_file(dataset):
    dataset.path("Germplasm").write_bytes(b"")
    fails(dataset.files(), "Germplasm.csv is empty. Its first row has to hold the column names.")


@pytest.mark.parametrize("saved_as", ["UTF-16", "workbook"])
def test_file_that_is_not_plain_text(dataset, tmp_path, saved_as):
    """Excel's 'Unicode Text' is UTF-16, and a workbook can be renamed to .csv by mistake."""
    if saved_as == "UTF-16":
        dataset.write("Germplasm", dataset.read("Germplasm"), encoding="utf-16")
    else:
        dataset.path("Germplasm").write_bytes(make_workbook(dataset, tmp_path / "sheet.xlsx").read_bytes())
    fails(dataset.files(), "Germplasm.csv contains null characters, so it is not a plain CSV file. "
                           "Save it as 'CSV UTF-8'.")


def test_file_in_an_unknown_encoding(dataset):
    """Byte 0x81 is not a character in UTF-8, nor in Windows encoding."""
    path = dataset.path("Germplasm")
    path.write_bytes(path.read_bytes().replace(b"Egypt", b"Egypt\x81"))
    fails(dataset.files(), "Germplasm.csv: could not read the text of the file. Save it as 'CSV UTF-8'.")


@pytest.mark.parametrize("delimiter, word", [(",", "commas"), (";", "semicolons"), ("\t", "tabs")])
def test_row_with_too_many_cells(dataset, delimiter, word):
    rows = dataset.read("Germplasm")
    rows[2].append("extra")
    dataset.write("Germplasm", rows, delimiter=delimiter)
    fails(dataset.files(), f"Germplasm.csv, row 3 has 9 cells, but row 1 has 8. Put quotes around any value with "
                           f"{word} in it, or add the missing column names to row 1.")


@pytest.mark.parametrize("delimiter, word", [(",", "commas"), (";", "semicolons"), ("\t", "tabs")])
def test_row_with_too_few_cells(dataset, delimiter, word):
    rows = dataset.read("Germplasm")
    rows[2].pop()
    dataset.write("Germplasm", rows, delimiter=delimiter)
    fails(dataset.files(), f"Germplasm.csv, row 3 has 7 cells, but row 1 has 8. Each row needs a cell for every "
                           f"column, with {word} between the cells even when they are empty.")


def test_quote_mark_that_is_never_closed(dataset):
    """
    The value in quotes would run to the end of the file, taking in all the rows after it, and the file would
    pass with fewer rows.
    """
    path = dataset.path("Phenotype")
    lines = path.read_text(encoding="utf-8").split("\n")
    lines[dataset.row("Phenotype", f"{TRIAL}_000008") - 1] += '"Checked twice'  # its Comments cell was empty
    path.write_text("\n".join(lines), encoding="utf-8", newline="")
    fails(dataset.files(), f"Phenotype.csv, row 9: could not read the row as CSV (unexpected end of data). {QUOTES}")


def test_text_after_a_closing_quote_mark(dataset):
    path = dataset.path("Germplasm")
    path.write_text(path.read_text(encoding="utf-8").replace(",Egypt,", ',"Egypt" north,'), encoding="utf-8",
                    newline="")
    fails(dataset.files(), f"Germplasm.csv, row 3: could not read the row as CSV (',' expected after '\"'). {QUOTES}")


def test_value_too_long_for_a_csv_file(dataset):
    """In practice, only a quote mark that is never closed makes a value this long."""
    dataset.set("Germplasm", "ostrin", "Comments", "x" * 131_073)
    fails(dataset.files(), "Germplasm.csv, row 3: could not read the row as CSV "
                           f"(field larger than field limit (131072)). {QUOTES}")


# ---------------------------------------------------------------- Collection sheet

def test_workbook_that_is_not_a_workbook(dataset, tmp_path):
    path = tmp_path / "sheet.xlsx"
    path.write_bytes(dataset.path("Germplasm").read_bytes())
    fails([("sheet.xlsx", path)], "Could not open sheet.xlsx as an Excel workbook (File is not a zip file).")


def test_sheet_that_is_not_a_table(dataset, tmp_path):
    workbook = make_workbook(dataset, tmp_path / "sheet.xlsx")
    edit_workbook(workbook, lambda wb: wb.create_sheet("Notes"))
    fails([("sheet.xlsx", workbook)], f"sheet 'Notes' is not a table of the schema. Rename it after its table "
                                      f"({TABLES}), or delete it.")


def test_empty_sheet(dataset, tmp_path):
    def empty(wb):
        del wb["Management"]
        wb.create_sheet("Management")
    workbook = make_workbook(dataset, tmp_path / "sheet.xlsx")
    edit_workbook(workbook, empty)
    fails([("sheet.xlsx", workbook)], "sheet 'Management' is empty. Put the column names in row 1, "
                                      "or delete the sheet.")


def test_two_sheets_for_one_table(dataset, tmp_path):
    def copy(wb):
        wb.copy_worksheet(wb["Germplasm"]).title = "GP"
    workbook = make_workbook(dataset, tmp_path / "sheet.xlsx")
    edit_workbook(workbook, copy)
    fails([("sheet.xlsx", workbook)], "sheet 'GP' and sheet 'Germplasm' are both the Germplasm table. "
                                      "Keep only one.")


def test_required_sheet_missing(dataset, tmp_path):
    def delete(wb):
        del wb["Germplasm"]
    workbook = make_workbook(dataset, tmp_path / "sheet.xlsx")
    edit_workbook(workbook, delete)
    fails([("sheet.xlsx", workbook)], "The Germplasm table is missing. "
                                      "Add Germplasm.csv, or the sheet 'Germplasm' to the workbook.")


def test_required_sheet_left_blank(dataset, tmp_path):
    dataset.drop_table("Germplasm")
    workbook = make_workbook(dataset, tmp_path / "sheet.xlsx")
    fails([("sheet.xlsx", workbook)], "sheet 'Germplasm' has no rows, but Germplasm needs at least one.")


def test_row_2_that_is_not_help_text_is_data(dataset, tmp_path):
    """Such as the row of column descriptions in the collection sheet before it was built from schema.yaml."""
    workbook = make_workbook(dataset, tmp_path / "sheet.xlsx")
    set_sheet_cell(workbook, "Germplasm", 2, "GPID", "Germplasm ID (required)")
    fails([("sheet.xlsx", workbook)], f"sheet 'Germplasm', row 2, column GPID: 'Germplasm ID (required)' contains "
                                      f"a space, '(' and ')'. {ID_RULE} Use '_' instead: Germplasm_ID_required_")


def test_collection_sheet_of_another_version(dataset, tmp_path):
    """It is checked before anything else, as the columns may have changed since that version."""
    def older(wb):
        wb[READ_ME_SHEET]["A1"] = READ_ME_TITLE.format(version="0.9.0")
    dataset.set("Phenotype", SCORE, "Score", "n.a.")
    workbook = make_workbook(dataset, tmp_path / "sheet.xlsx")
    edit_workbook(workbook, older)
    fails([("sheet.xlsx", workbook)], f"sheet.xlsx is a collection sheet for schema version 0.9.0, but it is checked "
                                      f"against schema version {SCHEMA.version}. Download a new blank collection "
                                      "sheet, and copy your data into it.")


@pytest.mark.parametrize("help_row", [True, False], ids=["with help text", "without help text"])
def test_row_numbers_are_those_of_the_sheet(dataset, tmp_path, help_row):
    dataset.set("Phenotype", SCORE, "Score", "n.a.")
    workbook = make_workbook(dataset, tmp_path / "sheet.xlsx", help_row)
    row = dataset.row("Phenotype", SCORE) + (1 if help_row else 0)
    fails([("sheet.xlsx", workbook)], f"sheet 'Phenotype', row {row}, column Score: 'n.a.' {NOT_A_NUMBER}")


# ---------------------------------------------------------------- Tables

@pytest.mark.parametrize("table", ["Germplasm", "SeedLot", "Experiment", "ExperimentalUnit", "PhenotypeDescription",
                                   "Phenotype"])
def test_required_table_missing(dataset, table):
    dataset.drop_table(table)
    fails(dataset.files(), f"The {table} table is missing. Add {table}.csv, or the sheet '{table}' to the workbook.")


@pytest.mark.parametrize("rows", [[], [["NA"] * 8, [""] * 8]], ids=["header only", "only missing values"])
def test_required_table_without_rows(dataset, rows):
    dataset.write("Germplasm", dataset.read("Germplasm")[:1] + rows)
    fails(dataset.files(), "Germplasm.csv has no rows, but Germplasm needs at least one.")


@pytest.mark.parametrize("row", [[], ["NA", "", "null", "N/A", "", "None", "", "not applicable"]],
                         ids=["empty", "only missing values"])
def test_row_without_values_with_rows_after_it(dataset, tmp_path, row):
    """It may end the table, with something else below it. In the collection sheet, it is one row further down."""
    rows = dataset.read("Phenotype")
    rows.insert(4, row)
    dataset.write("Phenotype", rows)
    fails(dataset.files(), f"Phenotype.csv, row 5 {NO_VALUES}")
    workbook = make_workbook(dataset, tmp_path / "sheet.xlsx")
    fails([("sheet.xlsx", workbook)], f"sheet 'Phenotype', row 6 {NO_VALUES}")


# ---------------------------------------------------------------- Columns

def test_values_in_a_column_without_a_name(dataset):
    dataset.add_column("Germplasm", "", ("x",))
    fails(dataset.files(), "Germplasm.csv, column 9 has values but no column name in row 1. "
                           "Add the column name, or delete the column.")


@pytest.mark.parametrize("name, hint", [
    ("Specie", "Did you mean 'Species'?"),
    # Close names are found ignoring case
    ("SPECIES", "Did you mean 'Species'?"),
    ("species", "Did you mean 'Species'?"),
    ("Yield", "The columns of Germplasm are: GPID, Name, AlternativeName, Species, Donor, GeographicOrigin, "
              "Maintaining, Comments."),
])
def test_unknown_column(dataset, name, hint):
    dataset.rename_column("Germplasm", "Species", name)
    fails(dataset.files(), f"Germplasm.csv: '{name}' is not a column of Germplasm. {hint}")


@pytest.mark.parametrize("name", ["Name", " Name "])
def test_column_twice(dataset, name):
    dataset.add_column("Germplasm", name)
    fails(dataset.files(), "Germplasm.csv: the column 'Name' appears twice.")


@pytest.mark.parametrize("table, column", [("Germplasm", "GPID"), ("Phenotype", "Score"),
                                           ("PhenotypeDescription", "Unit")])
def test_required_column_missing(dataset, table, column):
    dataset.drop_column(table, column)
    fails(dataset.files(), f"{table}.csv: the column '{column}' is missing. It is required in {table}.")


# ---------------------------------------------------------------- Values

@pytest.mark.parametrize("value, problem", [
    ("", "the cell is empty"),
    ("NA", "'NA' counts as a missing value"),
    (" n/a ", "' n/a ' counts as a missing value"),
])
def test_required_value_missing(dataset, value, problem):
    dataset.set("Phenotype", SCORE, "Score", value)
    fails(dataset.files(), f"{dataset.where('Phenotype', SCORE, 'Score')}: {problem}, but Score is required. "
                           "Fill it in.")


@pytest.mark.parametrize("value, problem", [
    (" ostrin", "' ostrin' has spaces before or after it. Remove them."),
    ("ostrin ", "'ostrin ' has spaces before or after it. Remove them."),
    ("ostrin-2", f"'ostrin-2' contains '-'. {ID_RULE} Use '_' instead: ostrin_2"),
    ("ostrin 2.0", f"'ostrin 2.0' contains a space and '.'. {ID_RULE} Use '_' instead: ostrin_2_0"),
    ("ostrin/2-b", f"'ostrin/2-b' contains '/' and '-'. {ID_RULE} Use '_' instead: ostrin_2_b"),
    ("ostrin 2/b", f"'ostrin 2/b' contains a space and '/'. {ID_RULE} Use '_' instead: ostrin_2_b"),
    ("ostrin 2/b-c", f"'ostrin 2/b-c' contains a space, '/' and '-'. {ID_RULE} Use '_' instead: ostrin_2_b_c"),
    # No fix is suggested for letters with accents
    ("Søren", f"'Søren' contains 'ø'. {ID_RULE}"),
    ("Søren-2", f"'Søren-2' contains 'ø' and '-'. {ID_RULE}"),
    # A character that cannot be seen is named
    ("ostrin 2", f"'ostrin 2' contains the invisible character U+00A0 (no-break space). {ID_RULE} "
                      "Use '_' instead: ostrin_2"),
    ("2ostrin", f"'2ostrin' starts with '2'. {START_RULE}"),
    ("_ostrin", f"'_ostrin' starts with '_'. {START_RULE}"),
    # No fix is suggested when it would not start with a letter either
    ("2-ostrin", f"'2-ostrin' contains '-'. {ID_RULE}"),
])
def test_invalid_id(dataset, value, problem):
    where = dataset.where("Germplasm", "ostrin", "GPID")
    dataset.set("Germplasm", "ostrin", "GPID", value)
    fails(dataset.files(), f"{where}: {problem}")


@pytest.mark.parametrize("value", ["1.5", "+3", "two"])
def test_not_a_whole_number(dataset, value):
    dataset.set("ExperimentalUnit", UNIT, "Block", value)
    fails(dataset.files(), f"{dataset.where('ExperimentalUnit', UNIT, 'Block')}: '{value}' is not a whole number. "
                           "Write digits only, e.g. 12.")


@pytest.mark.parametrize("value, problem", [
    # ',' can only be a decimal mark
    ("94,5", "'94,5' has ','. Numbers have '.' as the decimal mark and no thousands separator, so write 94.5"),
    ("0,468", "'0,468' has ','. Numbers have '.' as the decimal mark and no thousands separator, so write 0.468"),
    ("1234,5", "'1234,5' has ','. Numbers have '.' as the decimal mark and no thousands separator, so write 1234.5"),
    # ',' could also separate thousands, so either number could be meant
    ("1,234", "'1,234' has ','. Numbers have '.' as the decimal mark and no separator between thousands. "
              "Write 1.234 if ',' is the decimal mark, or 1234 if it separates thousands. These are different "
              "numbers, so check which one is meant."),
    ("-12,345", "'-12,345' has ','. Numbers have '.' as the decimal mark and no separator between thousands. "
                "Write -12.345 if ',' is the decimal mark, or -12345 if it separates thousands. These are different "
                "numbers, so check which one is meant."),
    # Anything else
    ("1,234,567", f"'1,234,567' {NOT_A_NUMBER}"),
    ("1.234,5", f"'1.234,5' {NOT_A_NUMBER}"),
    ("1 234", f"'1 234' {NOT_A_NUMBER}"),
    ("94 cm", f"'94 cm' {NOT_A_NUMBER}"),
    ("n.a.", f"'n.a.' {NOT_A_NUMBER}"),
    (".5", f"'.5' {NOT_A_NUMBER}"),
    ("5.", f"'5.' {NOT_A_NUMBER}"),
    ("+3", f"'+3' {NOT_A_NUMBER}"),
    # Read as infinity
    ("1e999", f"'1e999' {INFINITE}"),
    ("-1e999", f"'-1e999' {INFINITE}"),
])
def test_not_a_number(dataset, value, problem):
    dataset.set("Phenotype", SCORE, "Score", value)
    fails(dataset.files(), f"{dataset.where('Phenotype', SCORE, 'Score')}: {problem}")


@pytest.mark.parametrize("table, rid, column, value, digits", [
    ("Phenotype", SCORE, "Score", "１２", "'１' and '２'"),  # full-width
    ("Phenotype", SCORE, "Score", "٣", "'٣'"),  # Arabic-Indic
    ("ExperimentalUnit", UNIT, "Block", "٣", "'٣'"),
    ("Phenotype", SCORE, "Date", "٢٠٢٥-06-30", "'٢', '٠' and '٥'"),
    ("Experiment", TRIAL, "GPSCoordinates", "٥٦;١٠", "'٥', '٦', '١' and '٠'"),
])
def test_digits_other_than_0_to_9(dataset, table, rid, column, value, digits):
    dataset.set(table, rid, column, value)
    fails(dataset.files(), f"{dataset.where(table, rid, column)}: '{value}' has digits other than 0-9: {digits}. "
                           "Write them as 0-9.")


@pytest.mark.parametrize("column, value, named", [
    ("Comments", "Germinates best at 20 °C.", "'°'"),
    ("Comments", "Large seeds; flat.", "';'"),
    ("Comments", "“Large” seeds.", "'“' and '”'"),
    ("Comments", "Large seeds.", "the invisible character U+00A0 (no-break space)"),
    ("Comments", "Large​seeds.", "the invisible character U+200B (zero width space)"),
    ("Comments", "Large\tseeds.", "a tab"),
    ("Comments", "Seeds ١٢ mm long.", "'١' and '٢'"),
    ("Name", "Ostrin\nOS", "a line break"),
    ("AlternativeName", "OS=2", "'='"),
])
def test_text_with_characters_it_cannot_hold(dataset, column, value, named):
    """Comments is long text, which can hold line breaks too, Name is text and AlternativeName a list."""
    dataset.set("Germplasm", "ostrin", column, value)
    rule = LONG_TEXT_RULE if column == "Comments" else TEXT_RULE
    fails(dataset.files(), f"{dataset.where('Germplasm', 'ostrin', column)}: the text contains {named}. {rule}")


@pytest.mark.parametrize("table, rid, column, value", [
    ("Germplasm", "vandrel", "AlternativeName", "NB 117; Nordbean 117"),
    ("Germplasm", "vandrel", "AlternativeName", "NB 117;"),
    ("Features", "soil_type", "Vocabulary", "clay; loam;sandy loam"),
    ("Features", "soil_type", "Vocabulary", "clay ;loam"),
    ("Features", "soil_type", "Vocabulary", "clay;;loam"),
    ("Features", "soil_type", "Vocabulary", "clay;loam;"),
    ("Features", "soil_type", "Vocabulary", ";clay"),
])
def test_not_a_list(dataset, table, rid, column, value):
    dataset.set(table, rid, column, value)
    fails(dataset.files(), f"{dataset.where(table, rid, column)}: '{value}' {NOT_A_LIST}")


@pytest.mark.parametrize("value, problem", [
    ("2025-02-30", "'2025-02-30' is not a real date."),
    ("2025-13-01", "'2025-13-01' is not a real date."),
    ("2025-06-30 12:30:00", "'2025-06-30 12:30:00' holds more than a date. Write only the date, as YYYY-MM-DD."),
    ("2025-06-30T12:30", "'2025-06-30T12:30' holds more than a date. Write only the date, as YYYY-MM-DD."),
    ("30/06/2025", "'30/06/2025' is not a date written YYYY-MM-DD, e.g. 2023-05-17."),
    ("2025-6-30", "'2025-6-30' is not a date written YYYY-MM-DD, e.g. 2023-05-17."),
    ("20250630", "'20250630' is not a date written YYYY-MM-DD, e.g. 2023-05-17."),
    ("2999-12-31", "'2999-12-31' is in the future."),
])
def test_not_a_date(dataset, value, problem):
    dataset.set("Phenotype", SCORE, "Date", value)
    fails(dataset.files(), f"{dataset.where('Phenotype', SCORE, 'Date')}: {problem}")


def test_end_of_an_experiment_in_the_future(dataset):
    """Even one that is still running: data is only added once an experiment has ended."""
    dataset.set("Experiment", TRIAL, "EndDate", "2999-08-26")
    fails(dataset.files(), f"{dataset.where('Experiment', TRIAL, 'EndDate')}: '2999-08-26' is in the future.")


@pytest.mark.parametrize("value, hint", [
    ("56.09125; 9.55204", " Remove the spaces."),
    ("56.09125 ;9.55204", " Remove the spaces."),
    ("56.09125,9.55204", ""),
    ("56,09125;9,55204", ""),
    ("56.09125", ""),
    ("56°05'N;9°33'E", ""),
])
def test_not_coordinates(dataset, value, hint):
    dataset.set("Experiment", TRIAL, "GPSCoordinates", value)
    fails(dataset.files(), f"{dataset.where('Experiment', TRIAL, 'GPSCoordinates')}: '{value}' is not written "
                           f"latitude;longitude in decimal degrees, e.g. 56.170308;10.207013.{hint}")


@pytest.mark.parametrize("value", ["91;9.55204", "-90.5;9.55204", "56.09125;181", "56.09125;-180.1"])
def test_coordinates_out_of_range(dataset, value):
    dataset.set("Experiment", TRIAL, "GPSCoordinates", value)
    fails(dataset.files(), f"{dataset.where('Experiment', TRIAL, 'GPSCoordinates')}: '{value}' is outside the range "
                           "of coordinates: latitude goes from -90 to 90, and longitude from -180 to 180.")


@pytest.mark.parametrize("gpid, problem", [
    ("ostrin", "'ostrin' is also in row 3. Each GPID has to be unique."),
    ("Ostrin", "'Ostrin' is also in row 3, written 'ostrin'. Each GPID has to be unique, "
               "and upper and lower case do not count as different."),
])
def test_id_twice(dataset, gpid, problem):
    dataset.add_row("Germplasm", GPID=gpid)
    fails(dataset.files(), f"Germplasm.csv, row 5, column GPID: {problem}")


def test_unit_with_two_interventions(dataset):
    iid = f"{TRIAL}_002"
    dataset.set("ExperimentIntervention", iid, "UNID", UNIT)
    fails(dataset.files(), f"{dataset.where('ExperimentIntervention', iid, 'UNID')}: '{UNIT}' is also in row 2. "
                           "Each UNID has to be unique.")


@pytest.mark.parametrize("rows, more", [
    (1, ""),
    (2, " (1 more row in this column has the same problem.)"),
    (4, " (3 more rows in this column have the same problem.)"),
])
def test_how_many_more_rows_have_the_problem(dataset, rows, more):
    for i in range(1, rows + 1):
        dataset.set("Phenotype", f"{TRIAL}_00000{i}", "Score", "n.a.")
    fails(dataset.files(), f"{dataset.where('Phenotype', SCORE, 'Score')}: 'n.a.' {NOT_A_NUMBER}{more}")


# ---------------------------------------------------------------- Features table

@pytest.mark.parametrize("value, hint", [
    ("C", " Types are written in lower case: c."),
    ("D", " Types are written in lower case: d."),
    ("x", " Use c (text), i (whole number) or d (real number), or leave it empty for text."),
    ("text", " Use c (text), i (whole number) or d (real number), or leave it empty for text."),
])
def test_unknown_feature_type(dataset, value, hint):
    dataset.set("Features", "soil_type", "Type", value)
    fails(dataset.files(), f"{dataset.where('Features', 'soil_type', 'Type')}: '{value}' is not a feature type."
                           f"{hint}")


@pytest.mark.parametrize("ftid, ftype, vocabulary", [
    ("wavelength", "d", "400-2500"),
    ("wavelength", "d", "2500..400"),
    ("wavelength", "d", "400 .. 2500"),
    ("wavelength", "d", "low..high"),
    # An end without a limit is left blank, not written as a number so large that it is read as infinity
    ("wavelength", "d", "400..1e999"),
    ("plant_count", "i", "0-60"),
])
def test_invalid_range(dataset, ftid, ftype, vocabulary):
    dataset.set("Features", ftid, "Vocabulary", vocabulary)
    fails(dataset.files(), f"{dataset.where('Features', ftid, 'Vocabulary')}: '{vocabulary}' is not a valid "
                           f"vocabulary. For Type {ftype}, give a range min..max with min no larger than max, "
                           "e.g. 0..100. Leave an end blank for no limit, e.g. 0..")


# ---------------------------------------------------------------- Links between tables

def test_id_that_is_not_in_the_table_it_refers_to(dataset):
    unid = f"{TRIAL}_plot999"
    dataset.set("Phenotype", SCORE, "UNID", unid)
    fails(dataset.files(), f"{dataset.where('Phenotype', SCORE, 'UNID')}: '{unid}' is not in column UNID of "
                           "ExperimentalUnit.csv. IDs have to match exactly, character for character. "
                           "Check the spelling, or add it to ExperimentalUnit.")


def test_id_that_differs_only_in_case(dataset):
    slid = "ostrin_greenhouse_2024"
    dataset.set("SeedLot", slid, "GPID", "Ostrin")
    fails(dataset.files(), f"{dataset.where('SeedLot', slid, 'GPID')}: 'Ostrin' is not in column GPID of "
                           "Germplasm.csv. IDs have to match exactly, character for character. "
                           "Did you mean 'ostrin'?")


def test_parent_seed_lot_that_is_not_in_seedlot(dataset):
    slid = "vandrel_northfield_2024"
    dataset.set("SeedLot", slid, "ParentSLID", "vandrel_northfield_2022")
    fails(dataset.files(), f"{dataset.where('SeedLot', slid, 'ParentSLID')}: 'vandrel_northfield_2022' is not in "
                           "column SLID of SeedLot.csv. IDs have to match exactly, character for character. "
                           "Check the spelling, or add it to SeedLot.")


def test_link_to_a_table_that_is_left_out(dataset):
    dataset.drop_table("ClimateDescription")
    fails(dataset.files(), f"{dataset.where('Climate', f'{TRIAL}_001', 'CDID')}: 'air_temperature_daily_mean_2m_c' "
                           "refers to ClimateDescription, but there is no ClimateDescription table. Add "
                           "ClimateDescription.csv, or the sheet 'ClimateDescription' to the workbook. "
                           "(5 more rows in this column have the same problem.)")


# ---------------------------------------------------------------- Features cells

@pytest.mark.parametrize("cell", [
    "soil_type = loam;soil_ph=6.4",
    "soil_type=loam; soil_ph=6.4",
    "soil_type=loam ;soil_ph=6.4",
    "soil_type=loam;",
    "soil_type=loam;;soil_ph=6.4",
    "soil_type",
    "=loam",
    "soil_type=",
    "soil_type=loam,soil_ph=6.4",
    "soil_type:loam",
])
def test_features_cell_not_written_ftid_is_value(dataset, cell):
    dataset.set("ExperimentalUnit", UNIT, "Features", cell)
    fails(dataset.files(), f"{dataset.where('ExperimentalUnit', UNIT, 'Features')}: invalid Features cell '{cell}'. "
                           "Write each entry as FTID=value, separated by ';', without spaces around '=' or ';'.")


@pytest.mark.parametrize("cell, problem", [
    ("soil_colour=brown", "'soil_colour' is not an FTID in the Features table."),
    ("Soil_type=loam", "'Soil_type' is not an FTID in the Features table."),
    ("soil_type=loam;soil_type=clay", "'soil_type' appears more than once."),
    ("soil_type=silt", "'silt' is not in the vocabulary of feature soil_type (clay;loam;sandy loam)."),
    ("soil_type=Loam", "'Loam' is not in the vocabulary of feature soil_type (clay;loam;sandy loam)."),
    ("soil_ph=6,4", "'6,4' is not a number with '.' as the decimal mark, as feature soil_ph (Type d) needs."),
    ("plant_count=2.5", "'2.5' is not a whole number, as feature plant_count (Type i) needs."),
    ("plant_count=three", "'three' is not a whole number, as feature plant_count (Type i) needs."),
    ("wavelength=1450nm", "'1450nm' is not a number with '.' as the decimal mark, as feature wavelength (Type d) "
                          "needs."),
    ("wavelength=399", "399 is outside the range of feature wavelength (400..2500)."),
    ("wavelength=2500.5", "2500.5 is outside the range of feature wavelength (400..2500)."),
    ("soil_ph=1e999", f"'1e999' {INFINITE}"),
    ("plant_count=١٢", "'١٢' has digits other than 0-9: '١' and '٢'. Write them as 0-9."),
    ("tissue=leaf °", f"'leaf °' contains '°'. {TEXT_RULE}"),
])
def test_feature_value_that_does_not_fit(dataset, cell, problem):
    dataset.set("ExperimentalUnit", UNIT, "Features", cell)
    fails(dataset.files(), f"{dataset.where('ExperimentalUnit', UNIT, 'Features')}: invalid Features cell '{cell}'. "
                           f"{problem}")


def test_feature_value_outside_an_open_range(dataset):
    dataset.set("Features", "plant_count", "Vocabulary", "0..")
    dataset.set("ExperimentalUnit", UNIT, "Features", "plant_count=-1")
    fails(dataset.files(), f"{dataset.where('ExperimentalUnit', UNIT, 'Features')}: invalid Features cell "
                           "'plant_count=-1'. -1 is outside the range of feature plant_count (0..).")


def test_features_cell_without_a_features_table(dataset):
    dataset.drop_table("Features")
    cell = dataset.get("ExperimentalUnit", UNIT, "Features")
    fails(dataset.files(), f"{dataset.where('ExperimentalUnit', UNIT, 'Features')}: invalid Features cell '{cell}'. "
                           "'soil_type' is not an FTID in the Features table. There is no Features table. "
                           "Add Features.csv, or the sheet 'Features' to the workbook.")


# ---------------------------------------------------------------- Rules that span tables

def test_climate_unit_of_another_experiment(dataset):
    clid = f"{TRIAL}_003"
    dataset.set("Climate", clid, "UNID", POT)
    fails(dataset.files(), f"{dataset.where('Climate', clid, 'UNID')}: unit '{POT}' belongs to experiment "
                           f"'{GREENHOUSE}', but this row's EXPID is '{TRIAL}'. Fix the EXPID or the UNID, or leave "
                           "UNID empty if the value applies to all units in the experiment.")


def test_unit_without_an_intervention(dataset):
    unit = f"{TRIAL}_plot204"
    dataset.delete_row("ExperimentIntervention", f"{TRIAL}_008")
    fails(dataset.files(), f"{dataset.where('ExperimentalUnit', unit, 'UNID')}: unit '{unit}' has no row in "
                           f"ExperimentIntervention.csv, but other units in experiment '{TRIAL}' do. In experiments "
                           "with interventions, every unit needs one row, control units included.")


def test_experiment_without_units(dataset):
    expid = "nordbean_irrigation_southfield_2025"
    dataset.add_row("Experiment", EXPID=expid)
    fails(dataset.files(), f"Experiment.csv, row 4, column EXPID: experiment '{expid}' has no units in "
                           "ExperimentalUnit.csv. Every experiment needs at least one unit.")


@pytest.mark.parametrize("parents, path, more", [
    ({"vandrel_northfield_2023": "vandrel_northfield_2023"}, ["vandrel_northfield_2023"] * 2, ""),
    ({"vandrel_northfield_2023": "vandrel_northfield_2024"},
     ["vandrel_northfield_2023", "vandrel_northfield_2024", "vandrel_northfield_2023"],
     " (1 more row in this column has the same problem.)"),
    # vandrel_northfield_2024 descends from the loop, but is not in it
    ({"vandrel_northfield_2023": "ostrin_greenhouse_2024", "ostrin_greenhouse_2024": "belkar_genebank",
      "belkar_genebank": "vandrel_northfield_2023"},
     ["vandrel_northfield_2023", "ostrin_greenhouse_2024", "belkar_genebank", "vandrel_northfield_2023"],
     " (2 more rows in this column have the same problem.)"),
], ids=["itself", "its child", "a loop of three"])
def test_seed_lot_that_descends_from_itself(dataset, parents, path, more):
    for slid, parent in parents.items():
        dataset.set("SeedLot", slid, "ParentSLID", parent)
    fails(dataset.files(), f"{dataset.where('SeedLot', path[0], 'ParentSLID')}: seed lot '{path[0]}' descends from "
                           f"itself: {' -> '.join(path)}. A seed lot cannot be grown from itself or its own "
                           f"offspring. Fix the ParentSLID of one of these seed lots.{more}")


@pytest.mark.parametrize("harvested, swapped", [("2023-08-24", ""), ("2023-01-09", SWAPPED.format("2023-09-01"))])
def test_seed_lot_harvested_before_its_parent(dataset, harvested, swapped):
    """The parent, vandrel_northfield_2023, was harvested on 2023-08-24."""
    slid = "vandrel_northfield_2024"
    dataset.set("SeedLot", slid, "HarvestDate", harvested)
    fails(dataset.files(), f"{dataset.where('SeedLot', slid, 'HarvestDate')}: '{harvested}' is not after 2023-08-24, "
                           "the HarvestDate of its parent seed lot 'vandrel_northfield_2023'. A seed lot is harvested "
                           f"after the seed lot it was grown from. {swapped}".rstrip())


@pytest.mark.parametrize("start, swapped", [("2025-08-27", ""), ("2025-09-04", SWAPPED.format("2025-04-09"))])
def test_experiment_that_starts_after_it_ends(dataset, start, swapped):
    dataset.set("Experiment", TRIAL, "StartDate", start)
    fails(dataset.files(), f"{dataset.where('Experiment', TRIAL, 'StartDate')}: '{start}' is after the EndDate, "
                           f"2025-08-26. {swapped}".rstrip())


@pytest.mark.parametrize("day, swapped", [("2025-03-31", ""), ("2025-04-07", SWAPPED.format("2025-07-04"))])
def test_score_before_its_experiment_starts(dataset, day, swapped):
    dataset.set("Phenotype", SCORE, "Date", day)
    fails(dataset.files(), f"{dataset.where('Phenotype', SCORE, 'Date')}: '{day}' is before 2025-04-08, the StartDate "
                           f"of experiment '{TRIAL}'. {swapped}".rstrip())


@pytest.mark.parametrize("table, rid, day, swapped", [
    ("Management", f"{TRIAL}_002", "2025-08-27", ""),
    ("Climate", f"{TRIAL}_001", "2025-12-08", SWAPPED.format("2025-08-12")),
])
def test_treatment_or_measurement_after_its_experiment_ends(dataset, table, rid, day, swapped):
    dataset.set(table, rid, "Date", day)
    fails(dataset.files(), f"{dataset.where(table, rid, 'Date')}: '{day}' is after 2025-08-26, the EndDate of "
                           f"experiment '{TRIAL}'. {swapped}".rstrip())


def test_score_before_the_seed_lot_was_harvested(dataset):
    """Four scores are of units sown from vandrel_northfield_2024, all on 2025-06-30."""
    dataset.set("SeedLot", "vandrel_northfield_2024", "HarvestDate", "2025-07-01")
    fails(dataset.files(), f"{dataset.where('Phenotype', SCORE, 'Date')}: '2025-06-30' is not after 2025-07-01, the "
                           f"HarvestDate of seed lot 'vandrel_northfield_2024', which unit '{UNIT}' was sown from. "
                           "(3 more rows in this column have the same problem.)")


# ---------------------------------------------------------------- Stops at the first error

def test_columns_are_checked_before_values(dataset):
    """A wrong date in Experiment and a wrong column name in Phenotype, which comes later: the column is reported."""
    dataset.set("Experiment", TRIAL, "StartDate", "2025-04-31")
    dataset.rename_column("Phenotype", "Score", "Scores")
    fails(dataset.files(), "Phenotype.csv: 'Scores' is not a column of Phenotype. Did you mean 'Score'?")


def test_values_are_checked_before_links(dataset):
    """A wrong link in Phenotype and a wrong value in Climate, which comes later: the value is reported."""
    climate = f"{TRIAL}_001"
    dataset.set("Phenotype", SCORE, "UNID", f"{TRIAL}_plot999")
    dataset.set("Climate", climate, "Score", "n.a.")
    fails(dataset.files(), f"{dataset.where('Climate', climate, 'Score')}: 'n.a.' {NOT_A_NUMBER}")


def test_tables_are_checked_in_the_order_of_the_schema(dataset):
    """Climate.csv comes before Phenotype.csv by name, but Phenotype comes first in the schema."""
    dataset.set("Climate", f"{TRIAL}_001", "Score", "n.a.")
    dataset.set("Phenotype", SCORE, "Score", "n.a.")
    fails(dataset.files(), f"{dataset.where('Phenotype', SCORE, 'Score')}: 'n.a.' {NOT_A_NUMBER}")


# ---------------------------------------------------------------- Odd input

@pytest.mark.parametrize("value, text", [
    ("#N/A", "#N/A"),
    ("#DIV/0!", "#DIV/0!"),
    (True, "True"),
    (time(12, 30), "12:30:00"),
    # What Excel makes of 1/7 typed into a cell
    (datetime(2025, 1, 7), "2025-01-07"),
])
def test_odd_excel_cell(dataset, tmp_path, value, text):
    """Error values, TRUE/FALSE, times and dates in the collection sheet give a message, not a crash."""
    workbook = make_workbook(dataset, tmp_path / "sheet.xlsx")
    row = dataset.row("Phenotype", SCORE) + 1
    set_sheet_cell(workbook, "Phenotype", row, "Score", value)
    fails([("sheet.xlsx", workbook)], f"sheet 'Phenotype', row {row}, column Score: '{text}' {NOT_A_NUMBER}")


def test_date_with_a_time_in_the_collection_sheet(dataset, tmp_path):
    workbook = make_workbook(dataset, tmp_path / "sheet.xlsx")
    row = dataset.row("Phenotype", SCORE) + 1
    set_sheet_cell(workbook, "Phenotype", row, "Date", datetime(2025, 6, 30, 12, 30))
    fails([("sheet.xlsx", workbook)], f"sheet 'Phenotype', row {row}, column Date: '2025-06-30 12:30:00' "
                                      "holds more than a date. Write only the date, as YYYY-MM-DD.")


def test_merged_cells(dataset, tmp_path):
    """
    Cells merged across rows keep their value only in the top row, so the rows below are empty. Here the UNID of
    4 rows of the same pot is merged.
    """
    first = dataset.row("Phenotype", SPECTRUM) + 1

    def merge(wb):
        ws = wb["Phenotype"]
        j = [cell.value for cell in ws[1]].index("UNID") + 1
        ws.merge_cells(start_row=first, start_column=j, end_row=first + 3, end_column=j)
    workbook = make_workbook(dataset, tmp_path / "sheet.xlsx")
    edit_workbook(workbook, merge)
    fails([("sheet.xlsx", workbook)], f"sheet 'Phenotype', row {first + 1}, column UNID: the cell is empty, "
                                      "but UNID is required. Fill it in. "
                                      "(2 more rows in this column have the same problem.)")


def test_row_numbers_after_a_value_on_several_lines(dataset):
    """Rows are counted as Excel shows them, so a value on two lines does not shift the row numbers after it."""
    dataset.set("Germplasm", "ostrin", "Comments", "Landrace from the Nile delta.\nLarge flat seeds.")
    dataset.set("Germplasm", "belkar", "GPID", "belkar-1")
    fails(dataset.files(), f"Germplasm.csv, row 4, column GPID: 'belkar-1' contains '-'. {ID_RULE} "
                           "Use '_' instead: belkar_1")


# ---------------------------------------------------------------- Suggested fixes

@pytest.mark.parametrize("table, rid, column, value, fixes", [
    ("Phenotype", SCORE, "PHID", "PH-2025/1", ["PH_2025_1"]),
    ("Phenotype", SCORE, "Score", "94,5", ["94.5"]),
    ("Phenotype", SCORE, "Score", "1,234", ["1.234", "1234"]),
    ("SeedLot", "ostrin_greenhouse_2024", "GPID", "Ostrin", ["ostrin"]),
    ("Features", "soil_type", "Type", "C", ["c"]),
])
def test_suggested_fix_passes(dataset, tmp_path, table, rid, column, value, fixes):
    """Each fix a message suggests makes the data pass."""
    dataset.set(table, rid, column, value)
    message = error(dataset.files())
    for i, fix in enumerate(fixes):
        assert fix in message
        fixed = Dataset(tmp_path / f"fixed_{i}")
        fixed.set(table, rid, column, fix)
        passes(fixed.files())
