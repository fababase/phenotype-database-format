"""
Writes the tables in schema.md that list the tables and their columns, from schema.yaml. The Update schema.md Action
runs it on every push to main and commits schema.md if it changed. To see the tables before pushing:

    python schema/schema_md.py

Each of these tables sits between two comments, <!-- BEGIN ... --> and <!-- END ... -->, and only what is between
them is rewritten. The rest of schema.md is written by hand.
"""
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "app"))

from validation import Schema, TableDef, load_schema  # noqa: E402

SCHEMA_MD = HERE / "schema.md"
# A table written by this script: <!-- BEGIN key: note -->, the table, <!-- END key -->
BLOCK = re.compile(r"(?P<begin><!-- BEGIN (?P<key>[^:>]+): [^>]*-->\n)(?P<table>.*?)(?P<end><!-- END (?P=key) -->)",
                   re.DOTALL)
NOTE = "written from schema.yaml by schema/schema_md.py"

# How schema.md names each column type, as in its section on data types
TYPE_NAMES = {"id": "ID", "text": "Text", "long_text": "Long text", "integer": "Integer", "number": "Number",
              "date": "Date", "coordinates": "Coordinates", "features": "Feature list"}
# What follows the description of a column of these types
SEE = {"long_text": "See [Free text](#free-text).",
       "features": "See [Features cells](#features-cells-hold-several-values)."}
# Types whose examples are shown as code, as they are written exactly so. Examples of text are shown as text.
CODE_TYPES = {"id", "integer", "number", "date", "coordinates", "features"}


def markdown_table(rows: list[list[str]]) -> str:
    """A Markdown table with the first row as its header. A | in a cell is escaped, so it does not end the cell."""
    def line(cells: list[str]) -> str:
        cells = [cell.replace("|", "\\|") for cell in cells]
        return "|" + "|".join(f" {cell} " if cell else " " for cell in cells) + "|"
    return "\n".join([line(rows[0]), "|" + "---|" * len(rows[0])] + [line(row) for row in rows[1:]])


def link(table: str) -> str:
    return f"[{table}](#{table.lower()})"


def tables_table(schema: Schema) -> str:
    """The tables at a glance."""
    return markdown_table([["Table", "ID column", "One row is", "Filled in", "Needed"]] + [
        [link(table.name), table.id_column, table.one_row_is, table.filled_in, table.needed]
        for table in schema.tables.values()])


def columns_table(table: TableDef) -> str:
    """The columns of a table, in its section of the table reference."""
    rows = [["Column", "Type", "Required", "Links to", "Description", "Example"]]
    for column in table.columns.values():
        required = ("Yes" if column.required else "No") + (", unique" if column.unique else "")
        if column.type == "features":
            links = f"{link('Features')}, one or more"
        else:
            links = link(column.links_to) if column.links_to else ""
        description = " ".join(part for part in (column.description, SEE.get(column.type)) if part)
        example = column.example or ""
        if example and column.type in CODE_TYPES:
            example = f"`{example}`"
        rows.append([column.name, TYPE_NAMES[column.type], required, links, description, example])
    return markdown_table(rows)


def update(text: str, schema: Schema) -> str:
    """
    schema.md with the tables between the comments written anew from the schema.
    Raises ValueError if a table has no comments to go between, or comments are left over or doubled.
    """
    tables = {"tables": tables_table(schema)}
    tables |= {f"columns of {name}": columns_table(table) for name, table in schema.tables.items()}
    keys = [match["key"] for match in BLOCK.finditer(text)]
    for key in tables:
        if key not in keys:
            raise ValueError(f"schema.md has no place for the table '{key}'. Put "
                             f"'<!-- BEGIN {key}: {NOTE} -->' and '<!-- END {key} -->' where it goes.")
    for key in keys:
        if key not in tables:
            raise ValueError(f"schema.md has a place for the table '{key}', but schema.yaml has nothing to put "
                             "there. Remove its comments.")
        if keys.count(key) > 1:
            raise ValueError(f"schema.md has more than one place for the table '{key}'. Keep only one.")
    return BLOCK.sub(lambda match: f"{match['begin']}{tables[match['key']]}\n{match['end']}", text)


def main() -> None:
    raw =SCHEMA_MD.read_bytes().decode("utf-8")
    newline = "\r\n" if "\r\n" in raw else "\n"
    text = raw.replace("\r\n", "\n")
    updated = update(text, load_schema())
    if updated == text:
        print("schema.md is up to date.")
        return
    SCHEMA_MD.write_bytes(updated.replace("\n", newline).encode("utf-8"))
    print("Wrote the tables in schema.md from schema.yaml.")


if __name__ == "__main__":
    main()
