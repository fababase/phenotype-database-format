"""
The schema diagram shows every table and column in schema.yaml, and every link between them. The drawing itself
happens in a browser, when the deploy Action runs schema/diagram.py.
"""
import json

from diagram import PLACEHOLDER, diagram_data, page_html
from helpers import SCHEMA
from validation import help_text


def test_diagram_has_every_table_column_and_link():
    data = diagram_data(SCHEMA)
    assert {table["name"]: [column["name"] for column in table["columns"]] for table in data["tables"]} == \
           {name: list(table.columns) for name, table in SCHEMA.tables.items()}
    # A Features column holds FTIDs, so it links to the Features table like a links_to column
    expected = {(table.name, column.name, column.links_to or "Features")
                for table in SCHEMA.tables.values() for column in table.columns.values()
                if column.links_to or column.type == "features"}
    assert {(*link["from"], link["to"][0]) for link in data["links"]} == expected
    assert all(link["to"][1] == SCHEMA.tables[link["to"][0]].id_column for link in data["links"])


def test_diagram_says_what_each_table_and_column_is():
    """
    What the tooltips say. A table's: what one row is, when it is needed and filled in. A column's: its help and its
    example, which together are what row 2 of the collection sheet says about it.
    """
    for spec in diagram_data(SCHEMA)["tables"]:
        table = SCHEMA.tables[spec["name"]]
        assert [spec["one_row_is"], spec["needed"], spec["filled_in"]] == [table.one_row_is, table.needed, table.filled_in]
        for column in spec["columns"]:
            definition = table.columns[column["name"]]
            assert column["example"] == definition.example
            example = f"Example: {column['example']}" if column["example"] else ""
            assert " ".join(filter(None, [column["help"], example])) == help_text(definition, SCHEMA)


def test_diagram_page_has_the_schema():
    page = page_html(SCHEMA)
    assert PLACEHOLDER not in page
    assert json.dumps(diagram_data(SCHEMA)) in page
