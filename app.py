from shiny import ui, App, reactive, render
from validation import perform_validation
import os
import tempfile
import shutil
import openpyxl

app_ui = ui.page_fluid(
    ui.input_file("file1", "Choose Excel File", multiple = False, accept=".xlsx"),
    ui.output_ui("reactive_message"),
    ui.output_ui("download_ui")
)

def server(input, output, session):

    message = reactive.Value("Input excel file please.")

    dataframes = reactive.Value([])

    # Reactive function to read the Excel file when it's uploaded
    @reactive.Effect
    def upload():
        if input.file1():
            try:
                # Attempt to read the Excel file
                wb = openpyxl.load_workbook(input.file1()[0]["datapath"])
                message.set("Attempting validation...")
                dfs = perform_validation(wb)
                message.set("Validation successful!")
                dataframes.set(dfs)
            except AssertionError as e:
                # Set the error message if there's an error reading the file
                message.set(str(e))
                dataframes.set([])

    # Downloading data
    @session.download()
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
    @render.text
    def reactive_message():
        return message.get()
    
     # Render the download button UI conditionally
    @output
    @render.ui
    def download_ui():
        if dataframes.get():
            return ui.download_button("download_zip", "Download")

# Combine into a Shiny app
app = App(app_ui, server)