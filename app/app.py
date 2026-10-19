import io
import zipfile
from pathlib import Path

from shiny import App, reactive, render, ui

from validation import Table, ValidationError, load_schema, summary, validate_files, version_notices

SCHEMA = load_schema()

app_ui = ui.page_fluid(
    ui.layout_columns(
        # Left column: input and output stacked
        ui.card(
            ui.h2("Phenotype data validator"),
            ui.p("Upload one CSV file per table, named after the table (Germplasm.csv, SeedLot.csv, …), "
                 "or a filled-in collection sheet (.xlsx)."),
            ui.p(f"Checks against schema version {SCHEMA.version}. Stops at the first error."),
            *(ui.p(f"Notice: {notice}") for notice in version_notices()),
            ui.hr(),
            ui.input_file("files", "Choose files", multiple=True, accept=[".csv", ".xlsx"]),
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
    def validation_result() -> tuple[list[str], dict[str, Table]]:
        """Validates the uploaded files. Returns the message lines and the checked tables (empty if validation failed)."""
        uploads = input.files()
        if not uploads:
            return ["Upload your files please."], {}
        lines = []
        files = [(upload["name"], Path(upload["datapath"])) for upload in uploads]
        try:
            tables = validate_files(files, SCHEMA, notice=lambda msg: lines.append(f"Notice: {msg}"))
        except ValidationError as e:
            lines.append(f"Validation failed: {e}")
            return lines, {}
        except Exception as e:
            lines.append(f"An error occurred: {e}")
            lines.append("Please contact the developer.")
            return lines, {}
        return lines + summary(tables, SCHEMA), tables

    # Downloading the checked tables as CSV files
    @render.download(filename="tables.zip")
    def download_zip():
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
            for name, table in validation_result()[1].items():
                archive.writestr(f"{name}.csv", table.to_csv())
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
