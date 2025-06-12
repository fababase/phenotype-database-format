from shiny import ui, App, reactive, render
from validation import perform_validation
import os
import tempfile
import shutil
import openpyxl
import warnings

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
            msg_lines = ["Attempting validation..."]
            warn_msgs = []
            try:
                # Attempt to read the Excel file
                wb = openpyxl.load_workbook(input.file1()[0]["datapath"])
                # Capture warnings from perform_validation
                with warnings.catch_warnings(record=True) as wlist:
                    warnings.simplefilter("always")
                    dfs = perform_validation(wb)
                    # Collect warning messages
                    for w in wlist:
                        warn_msgs.append(f"Warning: {str(w.message)}")
                msg_lines.extend(warn_msgs)
                msg_lines.append("Validation successful!")
                message.set("\n".join(msg_lines))
                dataframes.set(dfs)
            except ValueError as e:
                msg_lines.extend(warn_msgs)
                msg_lines.append(str(e))
                message.set("\n".join(msg_lines))
                dataframes.set([])
            except Exception as e:
                msg_lines.extend(warn_msgs)
                msg_lines.append(f"An error occurred: {str(e)}")
                msg_lines.append("Please contact the developer.")
                message.set("\n".join(msg_lines))
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