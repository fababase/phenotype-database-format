"""
Draws how the tables link, from schema.yaml. The deploy Action runs it to publish the diagram next to the app:

    python schema/diagram.py <folder>

Writes into the folder an interactive page, index.html, where the tables can be dragged around and clicked to
highlight their links, and pointing at a column, table or link says what it is. Also writes pictures of the page
as first laid out: diagram.svg, which keeps what the page says as tooltips, and diagram.png. The page is
diagram.html with the schema filled in. It lays out the tables itself, so the pictures are taken in a browser:
this needs playwright and its Chromium.
"""
import json
import sys
from dataclasses import replace
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "app"))

from validation import Schema, help_text, load_schema  # noqa: E402

PAGE = HERE / "diagram.html"
# Where diagram.html takes the schema
PLACEHOLDER = "/* schema */ null"
# Milliseconds to wait for the page to lay out the tables. It loads the layout library from a CDN.
TIMEOUT = 60_000


def diagram_data(schema: Schema) -> dict:
    """
    The tables and the links to draw, and what to say about each. A column's help is what row 2 of the collection
    sheet says about it, with its example apart. A Features column links to the Features table, as it holds FTIDs.
    """
    tables, links = [], []
    for table in schema.tables.values():
        columns = [{"name": column.name, "type": column.type, "required": column.required, "unique": column.unique,
                    "help": help_text(replace(column, example=None), schema), "example": column.example}
                   for column in table.columns.values()]
        tables.append({"name": table.name, "required": table.required, "one_row_is": table.one_row_is,
                       "needed": table.needed, "filled_in": table.filled_in, "columns": columns})
        for column in table.columns.values():
            target = "Features" if column.type == "features" else column.links_to
            if target:
                links.append({"from": [table.name, column.name], "to": [target, schema.tables[target].id_column],
                              "required": column.required, "unique": column.unique})
    return {"version": schema.version, "tables": tables, "links": links}


def page_html(schema: Schema) -> str:
    """diagram.html with the schema filled in."""
    page = PAGE.read_text(encoding="utf-8")
    assert page.count(PLACEHOLDER) == 1, f"diagram.html needs '{PLACEHOLDER}' exactly once"
    # "</" would end the <script> early
    return page.replace(PLACEHOLDER, json.dumps(diagram_data(schema)).replace("</", "<\\/"))


def main(folder: str) -> None:
    from playwright.sync_api import expect, sync_playwright

    schema = load_schema()
    out = Path(folder)
    out.mkdir(parents=True, exist_ok=True)
    (out / "index.html").write_text(page_html(schema), encoding="utf-8")
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page(viewport={"width": 1600, "height": 1000})
        errors = []
        page.on("pageerror", lambda error: errors.append(error))
        page.goto((out / "index.html").resolve().as_uri())
        page.wait_for_function("window.diagramSvg || window.diagramError", timeout=TIMEOUT)
        error = page.evaluate("window.diagramError")
        assert not error and not errors, f"The diagram could not be drawn: {error or errors}"
        svg = page.evaluate("diagramSvg()")
        (out / "diagram.svg").write_text(svg, encoding="utf-8")
        picture = browser.new_page(device_scale_factor=2)
        picture.set_content(f'<body style="margin:0">{svg}</body>')
        picture.locator("svg").screenshot(path=out / "diagram.png")
        # Pointing at a column says what it holds
        page.locator(".row").first.hover()
        expect(page.locator("#tip")).to_contain_text(diagram_data(schema)["tables"][0]["columns"][0]["help"])
        browser.close()
    print(f"Drew the diagram in {out}: index.html, diagram.svg and diagram.png.")


if __name__ == "__main__":
    main(sys.argv[1])
