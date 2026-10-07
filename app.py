from shiny import ui, App, reactive, render
from validation import perform_validation
import os
import tempfile
import shutil
import openpyxl

app_ui = ui.page_fluid(
    ui.layout_columns(
        # Left column: input and output stacked
        ui.card(
            ui.h2("Excel Validator"),
            ui.p("Upload your Excel (.xlsx) file for validation and conversion."),
            ui.hr(),
            ui.input_file("file1", "Choose Excel File", multiple=False, accept=[".xlsx"]),
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

    message = reactive.Value("Input excel file please.")

    dataframes = reactive.Value([])

    # Reactive function to read the Excel file when it's uploaded
    @reactive.Effect
    def upload():
        if input.file1():
            msg_lines = ["Attempting validation..."]
            message.set("\n".join(msg_lines))
            def warn_callback(msg):
                msg_lines.append(f"Notice: {msg}")
                message.set("\n".join(msg_lines))
            try:
                wb = openpyxl.load_workbook(input.file1()[0]["datapath"])
                dfs = perform_validation(wb, warn_callback=warn_callback)
                msg_lines.append("Validation successful!")
                message.set("\n".join(msg_lines))
                dataframes.set(dfs)
            except ValueError as e:
                msg_lines.append(f"Validation failed: {str(e)}")
                message.set("\n".join(msg_lines))
                dataframes.set([])
            except Exception as e:
                msg_lines.append(f"An error occurred: {str(e)}")
                msg_lines.append("Please contact the developer.")
                message.set("\n".join(msg_lines))
                dataframes.set([])

    # Downloading data
    @output
    @render.download
    def download_zip():
        if dataframes.get() is not None:
            temp_dir = tempfile.mkdtemp()
            file_paths = []  # Keep track of the generated file paths
            names = ["GP", "SL", "EXP", "UN", "PH", "CL", "CD", "MM", "PD", "I"]
            for i, df in enumerate(dataframes.get()):
                file_path = os.path.join(temp_dir, f"{names[i]}.csv")
                df.to_csv(file_path, index=False, header = False)
                file_paths.append(file_path)

            zip_path = os.path.join(temp_dir, "files")
            shutil.make_archive(zip_path, 'zip', temp_dir)
            return zip_path + ".zip"
    
    @output
    @render.ui
    def reactive_message():
        # Replace newlines with <br> for HTML rendering
        return ui.HTML(message.get().replace("\n", "<br>"))
    
     # Render the download button UI conditionally
    @output
    @render.ui
    def download_ui():
        if dataframes.get():
            return ui.download_button("download_zip", "Download")
# Combine into a Shiny app
app = App(app_ui, server)