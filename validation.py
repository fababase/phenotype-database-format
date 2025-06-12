import openpyxl
import pandas as pd
import numpy as np
from datetime import datetime
import re
import warnings
# Load the workbook
def perform_validation(wb):
    """
    Validates the structure and content of an Excel workbook according to a predefined schema.
    This function checks that the workbook contains the expected sheets in the correct order and that each sheet
    adheres to specific column requirements. It also validates the integrity of links between tables (e.g., foreign keys).
    The function relies on helper functions `validate_table` and `check_links` to perform detailed validation.
    Args:
        wb: An openpyxl Workbook object representing the Excel workbook to be validated.
    Returns:
        list: A list containing the validated tables for each sheet, in the following order:
            [GP, SL, EXP, UN, I, PD, PH, CD, CL, MM]
            where each element corresponds to a validated table from the respective sheet.
    Raises:
        ValueError: If any sheet is missing or out of order, or if validation checks fail.
        Any exceptions raised by `validate_table` or `check_links` for invalid data.
    Sheet and Table Details:
        - "READ ME 1st": Introductory sheet (no validation).
        - "1) Germplasm GP": Germplasm information.
        - "2) Seed Lot SL": Seed lot information.
        - "3) Experiment information EXP": Experiment metadata.
        - "4) Experimental Unit UN": Experimental unit details.
        - "5) Experiment intervention I": Experiment interventions.
        - "6) Phenotype Description PD": Phenotype description metadata.
        - "7) Phenotype scores PH": Phenotype scoring data.
        - "8) Climate Description CD": Climate description metadata.
        - "9) Climate CL": Climate data.
        - "10) Management MM": Management interventions.
    Note:
        This function assumes the existence and correct implementation of `validate_table` and `check_links`.
    """

    
    sheetnames = ['READ ME 1st', '1) Germplasm GP', '2) Seed Lot SL', '3) Experiment information EXP',
        '4) Experimental Unit UN', '5) Experiment intervention I', '6) Phenotype Description PD',
            '7) Phenotype scores PH', '8) Climate Description CD', '9) Climate CL', '10) Management MM']

    for i in range(len(wb._sheets)):
        if wb._sheets[i].title != sheetnames[i]:
            raise ValueError(f"Expected sheet {sheetnames[i]} at index {i} but got " +
                f"{wb._sheets[i].title} in excel workbook. Please check the order of the sheets.")

    # Germplasm

    GP = wb[sheetnames[1]]
    GP = validate_table(GP, ["GPID", "Name", "AlternativeName", "Species", "Donor", "GeographicOrigin", "Maintaining", "Comments"],
        "Germplasm ID (required)","GP table", [0], [], [0], [], [], [])

    # Seed lot

    SL = wb[sheetnames[2]]
    SL = validate_table(SL, ["SLID", "GPID", "HarvestDate", "HarvestLocation", "ParentSLID", "Comments"],
        "Seed lot ID (Required)","SL table", [0], [], [0, 1], [2], [], [])


    # Experiment information

    EXP = wb[sheetnames[3]]
    EXP = validate_table(EXP, ["EXPID", "GPSCoordinates", "PlotSize", "PlotSizeIncludingPath", "StartDate", "EndDate",
        "Description", "Manager", "Distance", "Comments"],
        "Experiment ID (Required)","EXP table", [0], [], [0], [4,5], [], [1])


    # Experimental unit

    UN = wb[sheetnames[4]]
    UN = validate_table(UN, ["UNID", "EXPID", "SLID", "GPSCoordinates", "Block", "Column",
        "Row", "Comments"], "Unit ID (Required)","UN table", [0], [], [0,1,2], [], [5,6], [3])


    # Intervention

    I = wb[sheetnames[5]]
    I = validate_table(I, ["IID", "UNID", "Intervention", "Description", "Comments"],
        "Intervention ID (required)", "I table", [0], [], [0,1,2,3], [], [], [])


    # Phenotype Description

    PD = wb[sheetnames[6]]
    PD = validate_table(PD, ["PDID", "PhenotypeDescription", "Unit", "Grouping", "DescriptionOfMethod", "Comments"],
        "Phenotype ID (Required)", "PD table", [0, 1, 4], [], [0,1,2,4], [], [], [])


    # Phenotype scores

    PH = wb[sheetnames[7]]
    PH = validate_table(PH, ["PHID", "UNID", "PDID", "GENEID", "Date", "Score", "GrowthStage", "ScoredBy", "Comments"],
        "Phenotype ID (Required)","PH table", [0], [5], [0,1,2,5], [4], [6], [])


    # Climate Description

    CD = wb[sheetnames[8]]
    CD = validate_table(CD, ["CDID", "Name", "Grouping", "DescriptionOfMethod", "Comments"],
        "Climate Description ID (Required)","CD table", [0,1,3], [], [0,1,3], [], [], [])


    # Climate

    CL = wb[sheetnames[9]]
    CL = validate_table(CL, ["CLID", "EXPID", "UNID", "CDID", "Date", "Score", "Comments"],
        "Climate ID (Required)","CL table", [0], [5], [0,1,3,5], [4], [], [])


    # Management

    MM = wb[sheetnames[10]]
    MM = validate_table(MM, ["MMID", "EXPID", "Treatment", "Description", "Dosage", "Date", "Comments"],
        "Management ID (Required)", "MM table", [0], [], [0,1], [5], [], [])


    # Checking links
    #PDID
    check_links(PH[2], PD[0], "PDID", "PH", "PD")

    #CDID
    check_links(CL[3], CD[0], "CDID", "CL", "CD")

    #UNID
    check_links(I[1], UN[0], "UNID", "I", "UN")
    check_links(CL[2], UN[0], "UNID", "CL", "UN")
    check_links(PH[1], UN[0], "UNID", "PH", "UN")
    check_links(MM[2], UN[0], "UNID", "MM", "UN")
    
    #EXPID
    check_links(CL[1], EXP[0], "EXPID", "CL", "EXP", len(CL[1]) > 1)
    check_links(MM[1], EXP[0],  "EXPID", "MM", "EXP", len(MM[1]) > 1)
    check_links(UN[1], EXP[0], "EXPID", "UN", "EXP", len(UN[1]) > 1)

    #SLID
    check_links(UN[2], SL[0], "SLID", "UN", "SL")
    check_links(SL[4], SL[0], "ParentSLID", "SL", "SL")

    #GPID
    check_links(SL[1], GP[0], "GPID", "SL", "GP")

    return([GP, SL, EXP, UN, PH, CL, CD, MM, PD, I])

def check_links(arg1, arg2, name, table1, table2, both=False):
    """
    Checks whether all non-null values in one pandas Series (arg1) exist in another (arg2), and optionally vice versa.
    Parameters:
        arg1 (pd.Series): The first pandas Series to check (typically a column from a DataFrame).
        arg2 (pd.Series): The second pandas Series to check against.
        name (str): The name of the column being checked (used in error messages).
        table1 (str): The name of the first table (used in error messages).
        table2 (str): The name of the second table (used in error messages).
        both (bool, optional): If True, also checks that all non-null values in arg2 exist in arg1. Default is False.
    Raises:
        ValueError: If any non-null value in arg1 is not present in arg2, or (if both=True) if any non-null value in arg2 is not present in arg1. The error message includes the missing values and their indexes.
    """
    
    
    # Remove columnnames and null values
    arg1 = arg1[1:]
    arg2 = arg2[1:]
    arg1 = arg1[~pd.isnull(arg1)]
    arg2 = arg2[~pd.isnull(arg2)]

    # Check if all non-NULL values in arg1 are in arg2
    mask = arg1.isin(arg2)
    if not mask.all():
        missing_values = arg1[~mask]
        missing_indexes = missing_values.index.tolist()
        raise ValueError(f"Not all values in {name} in {table1} table are present in {table2} table \n"
                             f"Missing values: {missing_values.tolist()} at indexes: {missing_indexes}")

    # If both is True and arg2 is not empty, also check if all values in arg2 are in arg1
    if both and len(arg2) > 0:
        reverse_mask = arg2.isin(arg1)
        if not reverse_mask.all():
            missing_values_reverse = arg2[~reverse_mask]
            missing_indexes_reverse = missing_values_reverse.index.tolist()
            raise ValueError(f"Not all values in {name} in {table2} table are present in {table1} table \n"
                                 f"Missing values: {missing_values_reverse.tolist()} at indexes: {missing_indexes_reverse}")


def validate_table(table, colnames, coldescrip, tablename,
                   unique, numeric, notnull, date, integer, coordinate):
    """
    Validates the structure and content of a table (e.g., from an Excel worksheet) against specified rules.
    Parameters:
        table: An object representing the table to validate (e.g., an openpyxl worksheet).
        colnames (list of str): Expected column names in order.
        coldescrip (str): The descriptor string used for column descriptions.
        tablename (str): Name of the table (used in error messages).
        unique (list of int): Indices of columns that must have unique values.
        numeric (list of int): Indices of columns that must contain only numeric values.
        notnull (list of int): Indices of columns that must not contain null or NA values.
        date (list of int): Indices of columns that must contain dates in yyyy-mm-dd format.
        integer (list of int): Indices of columns that must contain only integer values.
        coordinate (list of int): Indices of columns that must contain coordinates in the format "number; number".
    Returns:
        pandas.DataFrame: The validated table as a DataFrame with cleaned and checked data.
    Raises:
        ValueError: If any validation check fails, with a descriptive error message indicating the issue and its location.
    """
    
    
    width = len(colnames)
    
    # Check columnnames
    colnames_real = [table.cell(row=1, column = i).value for i in range(1, width + 1)]
    for i in range(len(colnames)):
        if colnames[i] is not colnames_real[i]:
            raise ValueError(f"Expected column name '{colnames[i]}' in column {i + 1} " +
                             f"but got '{colnames_real[i]}' in {tablename}. Please check the column names.")
    
    
    if table.cell(row = 2, column = 1).value == coldescrip:
        warnings.warn(f"Skipping first row in {tablename} as it contains column descriptors.")
        data = list(table.values)
        data = data[0] + data[2:]  # Skip the first row
    else:
        data = table.values
        
    # Convert sheet to DataFrame for easier processing
    df = pd.DataFrame(data)
    df = df.iloc[:, 0:width]

    # Remove all rows where all values are null
    null_values = ["na", "NA", "N/A", "N/a", "Na", "n/a", "not applicable", "Not applicable", "null", "NULL", "Null", "none", "NONE", "None"]
    df.replace(null_values, np.nan, inplace=True)

    df = df.dropna(how='all')
    
    # If only the header row remains (or DataFrame is empty), return early
    if df.shape[0] <= 1:
        return df
    
    # Assert NULL or NA is not allowed in specified indices
    for index in notnull:
        null_rows = df[index].isnull()
        if null_rows.any():
            row_numbers = np.where(null_rows)[0]
            raise ValueError(
                f"NULL or NA values found in column {index + 1} of " +
                f"{tablename} \n at rows {row_numbers} where they are not allowed"
            )
    # Assert all values have to be unique in specified indices
    for index in unique:
        duplicate_rows = df[df[index].notnull()].duplicated(subset=index)
        if duplicate_rows.any():
            row_numbers = np.where(duplicate_rows)[0]
            raise ValueError(
                f"Duplicate values found in column {index + 1} " +
                f"of {tablename} \n at rows {row_numbers} where values have to be unique"
            )
    # Assert values have to be numeric in specified indices
    for index in numeric:
        non_numeric_rows = pd.to_numeric(df[df[index].notnull()][index][1:], errors='coerce').isnull()
        if non_numeric_rows.any():
            row_numbers = np.where(non_numeric_rows)[0] + 1  
            raise ValueError(
                f"Non-numeric values found in column {index + 1} " +
                f"of {tablename} \n at rows {row_numbers} where values have to be numeric"
            )
    # Assert values have to be dates of format yyyy-mm-dd in specified indices
    for index in date:
        invalid_rows = df[index][1:].apply(lambda x: not pd.isnull(x) and not isinstance(x, datetime))
        if invalid_rows.any():
            row_numbers = np.where(invalid_rows)[0] + 1
            raise ValueError(
                f"Invalid date format found in column {index + 1} " +
                     f"of {tablename} \n at rows {row_numbers} where date format yyyy-mm-dd is expected"
            )
    # Assert values have to be integers in specified indices
    for index in integer:
        invalid_rows = df[index][1:].apply(lambda x: not pd.isnull(x) and not str(x).isdigit())
        if invalid_rows.any():
            row_numbers = np.where(invalid_rows)[0] + 1
            raise ValueError(
                f"Non-integer values found in column {index + 1} " +
                     f"of {tablename} \n at rows {row_numbers} where integer values are expected"
            )
    # Assert values have to be coordinates of format numeric number ; numeric number in specified indices
    for index in coordinate:
        invalid_rows = df[index][1:].apply(lambda x: not pd.isnull(x) and not re.match(r'^-?\d+(\.\d+)?\s*;\s*-?\d+(\.\d+)?$', x))
        if invalid_rows.any():
            row_numbers = np.where(invalid_rows)[0] + 1
            raise ValueError(
                f"Invalid coordinate format found in column {index + 1} " +
                     f"of {tablename} \n at rows {row_numbers} where coordinate format xx.xxxx..;yy.yyyy.. is expected"
            )
            
    return df