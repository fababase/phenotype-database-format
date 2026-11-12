import io
import zipfile
from pathlib import Path

from shiny import App, reactive, render, ui

import collection_sheet
from validation import (CONTRIBUTORS_FILE, Checked, ValidationError, load_schema, summary, validate_files,
                        version_notices)

SCHEMA = load_schema()

app_ui = ui.page_fluid(
    ui.layout_columns(
        # Left column: input and output stacked
        ui.card(
            ui.h2("Phenotype data validator"),
            ui.p("Upload one CSV file per table, named after the table (Germplasm.csv, SeedLot.csv, …), "
                 f"or a filled-in collection sheet (.xlsx). Add {CONTRIBUTORS_FILE}, which says who to credit, "
                 "to check it too."),
            ui.div(ui.download_button("download_sheet", "Download a blank collection sheet")),
            *(ui.p(f"Notice: {notice}") for notice in version_notices()),
            ui.hr(),
            ui.input_file("files", "Choose files", multiple=True, accept=[".csv", ".xlsx", ".yaml"]),
            ui.hr(),
            ui.output_ui("reactive_message"),
            ui.output_ui("download_ui"),
            style="background-color: #f8f9fa; padding: 2em; margin-bottom: 2em;"
        ),
        # Right column: main area for future plots
        ui.card(
            ui.h4("Main Area (Future Plots)"),
            ui.p("This area is reserved for future plots and visualizations."),
            style="background-color: #f8f9fa; padding: 2em; margin-bottom: 2em; min-height: 200px;"
        ),
        col_widths = (4, 8)
    ),
    style="background: linear-gradient(135deg, #e0eafc 0%, #cfdef3 100%); min-height: 100vh;"
)

def server(input, output, session):

    @reactive.calc
    def validation_result() -> tuple[list[str], Checked | None]:
        """Validates the uploaded files. Returns the message lines and what passed (None if validation failed)."""
        uploads = input.files()
        if not uploads:
            return ["Upload your files please."], None
        lines = []
        files = [(upload["name"], Path(upload["datapath"])) for upload in uploads]
        try:
            checked = validate_files(files, SCHEMA, notice=lambda msg: lines.append(f"Notice: {msg}"),
                                     warning=lambda msg: lines.append(f"Warning: {msg}"))
        except ValidationError as e:
            lines.append(f"Validation failed: {e}")
            return lines, None
        except Exception as e:
            lines.append(f"An error occurred: {e}")
            lines.append("Please contact the developer.")
            return lines, None
        return lines + summary(checked, SCHEMA), checked

    # Downloading a blank collection sheet, built from the schema the app checks against
    @render.download(filename="collection-sheet.xlsx")
    def download_sheet():
        yield collection_sheet.build(SCHEMA)

    # Downloading the checked tables as CSV files, with contributors.yaml as it was uploaded
    @render.download(filename="tables.zip")
    def download_zip():
        checked = validation_result()[1]
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
            for name, table in checked.tables.items():
                archive.writestr(f"{name}.csv", table.to_csv())
            if checked.contributors:
                archive.writestr(CONTRIBUTORS_FILE, checked.contributors.text)
        yield buffer.getvalue()

    @render.ui
    def reactive_message():
        # One line per message; ui.div escapes the text, which can hold values from the data
        return ui.TagList(*(ui.div(line) for line in validation_result()[0]))

    # Render the download button UI conditionally
    @render.ui
    def download_ui():
        if validation_result()[1]:
            return ui.download_button("download_zip", "Download tables as CSV")

# Combine into a Shiny app
app = App(app_ui, server)
