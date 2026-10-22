"""
The schema diagram shows every table and column in schema.yaml, and every link between them. The drawing itself
happens in a browser, when the deploy Action runs schema/diagram.py.
"""
import json

from diagram import PLACEHOLDER, diagram_data, page_html
from helpers import SCHEMA


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


def test_diagram_page_has_the_schema():
    page = page_html(SCHEMA)
    assert PLACEHOLDER not in page
    assert json.dumps(diagram_data(SCHEMA)) in page
