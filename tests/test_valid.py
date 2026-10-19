"""
The valid dataset passes, as CSV files and as a filled-in collection sheet, and so does every variation of it
that the validator accepts.
"""
from datetime import date, datetime

import pytest

from helpers import OPTIONAL_TABLES, SCHEMA, SCORE, TRIAL, UNIT, as_csv, make_workbook, passes, rename_sheet
from validation import cell_text, summary


def test_csv_files_pass(dataset):
    tables, notices = passes(dataset.files())
    assert notices == []
    assert summary(tables, SCHEMA) == [
        "Validation successful! All 11 tables pass schema version 1.0.0.",
        "Germplasm: 3 rows, from Germplasm.csv",
        "SeedLot: 4 rows, from SeedLot.csv",
        "Experiment: 2 rows, from Experiment.csv",
        "ExperimentalUnit: 12 rows, from ExperimentalUnit.csv",
        "ExperimentIntervention: 8 rows, from ExperimentIntervention.csv",
        "Management: 2 rows, from Management.csv",
        "PhenotypeDescription: 3 rows, from PhenotypeDescription.csv",
        "Phenotype: 20 rows, from Phenotype.csv",
        "ClimateDescription: 4 rows, from ClimateDescription.csv",
        "Climate: 6 rows, from Climate.csv",
        "Features: 5 rows, from Features.csv",
    ]


def test_summary_of_one_row(dataset):
    dataset.delete_row("Management", f"{TRIAL}_002")
    tables, _ = passes(dataset.files())
    assert "Management: 1 row, from Management.csv" in summary(tables, SCHEMA)


def test_rows_where_every_cell_is_missing_are_dropped(dataset, tmp_path):
    """
    An empty row and a row of only missing values, as rows 5 and 6 of Phenotype, are dropped, and the rows after
    keep their numbers. In the collection sheet, every row is one further down, below the row of descriptions.
    """
    rows = dataset.read("Phenotype")
    rows[4:4] = [[], ["NA", "", "null", "N/A", "", "None", "", "not applicable"]]
    dataset.write("Phenotype", rows)
    expected = [2, 3, 4, *range(7, 24)]
    tables, _ = passes(dataset.files())
    assert tables["Phenotype"].row_numbers == expected
    workbook = make_workbook(dataset, tmp_path / "sheet.xlsx")
    tables, _ = passes([("sheet.xlsx", workbook)])
    assert tables["Phenotype"].row_numbers == [row + 1 for row in expected]


@pytest.mark.parametrize("value", ["NA", "na", " NA ", "N/A", "n/a", "NULL", "Null", "None", "none",
                                   "Not applicable", "NOT APPLICABLE", " not applicable "])
def test_missing_values_become_empty_cells(dataset, value):
    dataset.set("Germplasm", "ostrin", "Comments", value)
    tables, _ = passes(dataset.files())
    assert tables["Germplasm"].missing["Comments"].iat[1]
    assert tables["Germplasm"].to_csv().splitlines()[2] == "ostrin,Ostrin,,Vicia faba,,Egypt,Nordbean genebank,"


# ---------------------------------------------------------------- Collection sheet

@pytest.mark.parametrize("descriptor_row", [True, False], ids=["with descriptions", "without descriptions"])
def test_collection_sheet_passes_with_the_same_tables(dataset, tmp_path, descriptor_row):
    from_csv, _ = passes(dataset.files())
    workbook = make_workbook(dataset, tmp_path / "sheet.xlsx", descriptor_row)
    from_sheet, notices = passes([("sheet.xlsx", workbook)])
    assert notices == []
    assert as_csv(from_sheet) == as_csv(from_csv)
    offset = 1 if descriptor_row else 0
    for name, table in from_sheet.items():
        assert table.source == f"sheet '{SCHEMA.tables[name].sheet}'"
        assert table.row_numbers == [row + offset for row in from_csv[name].row_numbers]


@pytest.mark.parametrize("title", ["Germplasm", "germplasm", "GP", "gp", "GERMPLASM GP"])
def test_sheet_named_after_table_code_or_sheet(dataset, tmp_path, title):
    workbook = make_workbook(dataset, tmp_path / "sheet.xlsx")
    rename_sheet(workbook, "Germplasm GP", title)
    tables, _ = passes([("sheet.xlsx", workbook)])
    assert tables["Germplasm"].source == f"sheet '{title}'"


def test_read_me_sheet_ignored_in_any_case(dataset, tmp_path):
    workbook = make_workbook(dataset, tmp_path / "sheet.xlsx")
    rename_sheet(workbook, "READ ME 1st", "read me 1st")
    passes([("sheet.xlsx", workbook)])


def test_collection_sheet_without_optional_tables(dataset, tmp_path):
    """Optional tables left blank in the sheet are present but empty, so there is no notice."""
    for table in OPTIONAL_TABLES:
        dataset.drop_table(table)
    for table in ("ExperimentalUnit", "Phenotype"):
        dataset.drop_column(table, "Features")
    workbook = make_workbook(dataset, tmp_path / "sheet.xlsx")
    tables, notices = passes([("sheet.xlsx", workbook)])
    assert notices == []
    assert all(tables[table].data.empty for table in OPTIONAL_TABLES)


@pytest.mark.parametrize("value, text", [
    (None, ""),
    ("text", "text"),
    (7, "7"),
    (-2, "-2"),
    (2.5, "2.5"),
    (0.0001, "0.0001"),
    (1e-05, "0.00001"),
    (1e20, "100000000000000000000"),
    (date(2023, 5, 17), "2023-05-17"),
    (datetime(2023, 5, 17), "2023-05-17"),
    (datetime(2023, 5, 17, 12, 30), "2023-05-17 12:30:00"),
])
def test_cell_text(value, text):
    assert cell_text(value) == text


# ---------------------------------------------------------------- CSV files

@pytest.mark.parametrize("name", ["GP.csv", "germplasm.csv", "Germplasm GP.csv", "GERMPLASM.CSV"])
def test_csv_named_after_table_code_or_sheet(dataset, name):
    dataset.rename_file("Germplasm", name)
    tables, _ = passes(dataset.files())
    assert tables["Germplasm"].source == name


def test_columns_in_any_order(dataset):
    original, _ = passes(dataset.files())
    for table in SCHEMA.tables:
        dataset.write(table, [row[::-1] for row in dataset.read(table)])
    tables, _ = passes(dataset.files())
    assert as_csv(tables) == as_csv(original)


def test_optional_columns_left_out(dataset):
    for name, definition in SCHEMA.tables.items():
        for column in definition.columns.values():
            if not column.required:
                dataset.drop_column(name, column.name)
    tables, _ = passes(dataset.files())
    assert list(tables["Germplasm"].data.columns) == list(SCHEMA.tables["Germplasm"].columns)
    assert tables["Germplasm"].missing["Name"].all()


def test_spaces_around_column_names(dataset):
    rows = dataset.read("Germplasm")
    rows[0] = [f" {name} " for name in rows[0]]
    dataset.write("Germplasm", rows)
    passes(dataset.files())


def test_empty_columns_without_a_name(dataset):
    """Like the trailing columns in some sheets of the collection sheet."""
    dataset.add_column("Germplasm", "")
    dataset.add_column("Germplasm", "")
    passes(dataset.files())


def test_optional_tables_left_out(dataset):
    for table in OPTIONAL_TABLES:
        dataset.drop_table(table)
    for table in ("ExperimentalUnit", "Phenotype"):
        dataset.drop_column(table, "Features")
    tables, notices = passes(dataset.files())
    assert list(tables) == [name for name in SCHEMA.tables if name not in OPTIONAL_TABLES]
    assert notices == [f"There is no {table} table. It is optional, so it was skipped." for table in OPTIONAL_TABLES]


def test_empty_table_that_refers_to_a_table_left_out(dataset):
    """Climate refers to ClimateDescription, but an empty Climate table does not need one."""
    dataset.write("Climate", dataset.read("Climate")[:1])
    dataset.drop_table("ClimateDescription")
    passes(dataset.files())


@pytest.mark.parametrize("delimiter, word", [(";", "semicolons"), ("\t", "tabs")])
def test_semicolon_and_tab_separated_files(dataset, delimiter, word):
    original, _ = passes(dataset.files())
    for table in SCHEMA.tables:
        dataset.write(table, dataset.read(table), delimiter=delimiter)
    tables, notices = passes(dataset.files())
    assert notices == [f"{name} is separated by {word}." for name, _ in dataset.files()]
    assert as_csv(tables) == as_csv(original)


def test_windows_encoded_file(dataset):
    dataset.set("Germplasm", "ostrin", "Donor", "Søren Højgård")
    dataset.write("Germplasm", dataset.read("Germplasm"), encoding="cp1252")
    tables, notices = passes(dataset.files())
    assert notices == ["Germplasm.csv is not UTF-8, so it was read as Windows text."]
    assert tables["Germplasm"].data["Donor"].iat[1] == "Søren Højgård"


def test_quote_mark_inside_a_value(dataset):
    """A quote mark that does not start a value is part of it, as in 1" for an inch."""
    path = dataset.path("Germplasm")
    path.write_text(path.read_text(encoding="utf-8").replace("Large flat seeds.", 'Seeds about 1" long.'),
                    encoding="utf-8", newline="")
    tables, _ = passes(dataset.files())
    assert tables["Germplasm"].data["Comments"].iat[1].endswith('Seeds about 1" long.')


def test_utf8_file_with_byte_order_mark(dataset):
    """Excel's 'CSV UTF-8' starts the file with a byte order mark."""
    dataset.write("Germplasm", dataset.read("Germplasm"), encoding="utf-8-sig")
    _, notices = passes(dataset.files())
    assert notices == []


def test_windows_line_ends(dataset):
    original, _ = passes(dataset.files())
    for table in SCHEMA.tables:
        dataset.write(table, dataset.read(table), line_end="\r\n")
    tables, notices = passes(dataset.files())
    assert notices == []
    assert as_csv(tables) == as_csv(original)


# ---------------------------------------------------------------- Values

@pytest.mark.parametrize("table, rid, column, value", [
    ("Phenotype", SCORE, "Score", "-3"),
    ("Phenotype", SCORE, "Score", "0"),
    ("Phenotype", SCORE, "Score", "1.5e-3"),
    ("Phenotype", SCORE, "Score", "2E5"),
    ("Phenotype", SCORE, "Score", "-1.5E+3"),
    ("ExperimentalUnit", UNIT, "Block", "-2"),
    ("ExperimentalUnit", UNIT, "Block", "0"),
    ("SeedLot", "vandrel_northfield_2024", "HarvestDate", "2024-02-29"),
    ("Experiment", TRIAL, "GPSCoordinates", "-90;180"),
    ("Experiment", TRIAL, "GPSCoordinates", "56;10"),
    # Missing values in typed columns are not checked against the type
    ("Phenotype", SCORE, "Date", "Not Applicable"),
    ("ExperimentalUnit", UNIT, "Block", "n/a"),
    ("Experiment", TRIAL, "GPSCoordinates", "NULL"),
    # A Climate UNID given as a missing value, so the row applies to all units
    ("Climate", f"{TRIAL}_001", "UNID", "NULL"),
    # A Climate UNID of another unit in the same experiment
    ("Climate", f"{TRIAL}_003", "UNID", f"{TRIAL}_plot204"),
    # Features cells
    ("ExperimentalUnit", UNIT, "Features", "soil_type=clay;soil_ph=7;plant_count=38;tissue=whole plant"),
    ("Phenotype", SCORE, "Features", "tissue=leaf, from the top of the main stem"),
    ("Phenotype", SCORE, "Features", "wavelength=2500"),
    ("Phenotype", SCORE, "Features", "wavelength=4e2"),
    ("Phenotype", SCORE, "Features", "na"),
    # Features without a vocabulary take any value of their type, so these test the type alone
    ("ExperimentalUnit", UNIT, "Features", "plant_count=-1"),
    ("ExperimentalUnit", UNIT, "Features", "soil_ph=-0.5"),
])
def test_accepted_values(dataset, table, rid, column, value):
    dataset.set(table, rid, column, value)
    passes(dataset.files())


def test_feature_without_a_vocabulary_takes_any_value_of_its_type(dataset):
    dataset.set("Features", "soil_type", "Vocabulary", "")
    dataset.set("ExperimentalUnit", UNIT, "Features", "soil_type=peat")
    passes(dataset.files())


@pytest.mark.parametrize("vocabulary, value", [("0..60", "0"), ("0..60", "60"), ("-10..10", "-10")])
def test_whole_number_feature_within_its_range(dataset, vocabulary, value):
    """The range includes both ends."""
    dataset.set("Features", "plant_count", "Vocabulary", vocabulary)
    dataset.set("ExperimentalUnit", UNIT, "Features", f"plant_count={value}")
    passes(dataset.files())


def test_feature_type_given_as_a_missing_value_means_text(dataset):
    dataset.set("Features", "tissue", "Type", "NA")
    passes(dataset.files())
