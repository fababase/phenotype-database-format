"""
Builds the blank collection sheet from the schema: a workbook for filling in the tables by hand. The app offers it
for download, built from the same schema.yaml it checks against, so the two always match. From the command line:

    python collection_sheet.py <file.xlsx>

The workbook has a READ ME 1st sheet, then one sheet per table, named after it, with the column names in row 1 and
what goes in each column in row 2. The validator skips the READ ME 1st sheet, and row 2 when it is there.
"""
import io
import sys
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font
from openpyxl.utils import get_column_letter

from validation import READ_ME_SHEET, Schema, help_text, load_schema

# Links in the READ ME 1st sheet. They hold the repository's name, so they change if it is renamed.
SITE = "https://fababase.github.io/phenotype-database-format/"
SCHEMA_DOC = "https://github.com/fababase/phenotype-database-format/blob/main/schema/schema.md"

TITLE = Font(bold=True, size=14)
BOLD = Font(bold=True)
LINK = Font(color="0563C1", underline="single")
HELP = Font(italic=True, color="595959")


def add_read_me(ws, schema: Schema) -> None:
    """
    The READ ME 1st sheet: which schema version the workbook is for, how to fill it in, where to read more, and
    the tables. It is kept short, as schema.md has the rest.
    """
    lines = [
        (f"Collection sheet for the FabaBase phenotype database, schema version {schema.version}", TITLE, None),
        ("", None, None),
        ("How to fill it in", BOLD, None),
        ("Each sheet is a table. Row 1 holds the column names, and row 2 says what goes in each column. "
         "Start your data in row 3.", None, None),
        ("Do not rename the sheets or the columns. Leave row 2 as it is, or delete it.", None, None),
        ("Leave a cell empty when there is no value. Optional columns and tables can be left empty.", None, None),
        ("Then check the workbook with the validator, which says what to fix:", None, SITE),
        ("", None, None),
        ("To read more", BOLD, None),
        ("Every table and column, and the rules they follow:", None, SCHEMA_DOC),
        ("How the tables link:", None, f"{SITE}diagram/"),
        ("", None, None),
        ("The tables", BOLD, None),
    ]
    for row, (text, font, link) in enumerate(lines, start=1):
        cell = ws.cell(row, 1, f"{text} {link}" if link else text or None)
        if link:
            cell.hyperlink = link
            font = LINK
        if font:
            cell.font = font

    ws.append(["Sheet", "One row is", "Needed", "Filled in, relative to the experiment"])
    for cell in ws[ws.max_row]:
        cell.font = BOLD
    for table in schema.tables.values():
        ws.append([table.name, table.one_row_is, table.needed, table.filled_in])
    for column, width in zip("ABCD", (24, 60, 32, 36)):
        ws.column_dimensions[column].width = width


def add_table(ws, table, schema: Schema) -> None:
    """A table's sheet: the column names in row 1, and what goes in each column in row 2."""
    columns = list(table.columns.values())
    ws.append([column.name for column in columns])
    ws.append([help_text(column, schema) for column in columns])
    for j, column in enumerate(columns, start=1):
        ws.cell(1, j).font = BOLD
        ws.cell(2, j).font = HELP
        ws.cell(2, j).alignment = Alignment(wrap_text=True, vertical="top")
        ws.column_dimensions[get_column_letter(j)].width = 50 if column.type == "long_text" else 25
    # Only row 1 stays in view, as row 2 can be tall
    ws.freeze_panes = "A2"


def build(schema: Schema) -> bytes:
    """The blank collection sheet, as the bytes of an .xlsx file."""
    wb = Workbook()
    wb.active.title = READ_ME_SHEET
    add_read_me(wb.active, schema)
    for table in schema.tables.values():
        add_table(wb.create_sheet(table.name), table, schema)
    buffer = io.BytesIO()
    wb.save(buffer)
    return buffer.getvalue()


def main(path: str) -> None:
    Path(path).write_bytes(build(load_schema()))
    print(f"Wrote the blank collection sheet to {path}.")


if __name__ == "__main__":
    main(sys.argv[1])
