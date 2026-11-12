<!--
The README of a dataset on Zenodo, written for people who use the data. The public dataset and the
restricted datasets of projects all use it.

publishing/build.py fills it in, and leaves out comments like this one. It replaces each {{name}} with:

  {{title}}              the title of the dataset, from record.yaml
  {{version}}            the version of the dataset on Zenodo
  {{publication_date}}   the date this version is published, YYYY-MM-DD
  {{doi}}                the DOI of this version
  {{concept_doi}}        the DOI of all versions, which leads to the latest one
  {{schema_version}}     the version of the format the tables follow
  {{diagram}}            the address of the diagram at that version: .../diagram/#<version>
  {{repository}}         the address of the format's repository, at the commit used
  {{at_a_glance}}        how many experiments, years, germplasm, seed lots, units, traits and scores there are
  {{experiments}}        each experiment: its years, place, units, germplasm, traits and people
  {{traits}}             each trait: its PDID, name, unit and class, and its number of scores and experiments
  {{climate_variables}}  each climate variable, in the same way
  {{files}}              each file: what one row of it is, and its number of rows
  {{links}}              every column that holds the ID of another table
  {{tables}}             every table and column, from schema.yaml
  {{changes}}            what changed since the last version
  {{people}}             everyone in contributors.yaml: ORCID, affiliations and experiments
  {{funding}}            every grant in contributors.yaml, with its experiments
  {{curator}}            who looks after the dataset, from record.yaml
  {{citation}}           how to cite this version

Every {{name}} must be filled in. build.py stops if one is not, or if one is not in this list.

The code in Quick start is run on tests/valid by the tests, so that it keeps working.
-->

# {{title}}

Phenotype data from plant experiments: the scores of traits measured on field plots, pots and samples, together with what is needed to interpret them. That is the plant material, the experiments and how they were set up, what was done to each unit, the climate the plants grew in, and other notes on the units and the scores.

- **Version:** {{version}}, published {{publication_date}}.
- **DOI:** {{doi}}. The DOI {{concept_doi}} always leads to the latest version.
- **Format:** version {{schema_version}} of the FabaBase phenotype database format. The [diagram]({{diagram}}) shows how its tables link.
- **Licence:** [CC-BY-4.0](#licence).

This README holds all you need to read the tables and join them.

## At a glance

{{at_a_glance}}

## Contents

- [Experiments](#experiments)
- [What was measured](#what-was-measured)
- [The files](#the-files)
- [How the tables link](#how-the-tables-link)
- [The tables](#the-tables)
- [How values are written](#how-values-are-written)
- [Before you analyse](#before-you-analyse)
- [Quick start](#quick-start)
- [What changed in this version](#what-changed-in-this-version)
- [Who made it](#who-made-it)
- [How to cite](#how-to-cite)
- [Licence](#licence)
- [How the data were made](#how-the-data-were-made)

## Experiments

{{experiments}}

The Description of each experiment, in `Experiment.csv`, says where and how it was run: the site, the growing conditions, the design, the plot layout, the number of replicates and what the blocks are.

## What was measured

### Traits

{{traits}}

### Climate variables

{{climate_variables}}

What each trait and climate variable is, and how it was measured, is in the DescriptionOfMethod column of `PhenotypeDescription.csv` and `ClimateDescription.csv`.

## The files

The dataset is one CSV file per table, and this README.

{{files}}

Every file is written in the same way:

- UTF-8 text, with the values separated by commas.
- The first row holds the column names. Each row after it is one row of the table.
- A value with a comma, a double quote or a line break in it is in double quotes, and a double quote in it is written twice.
- A missing value is an empty cell.
- A table with no rows in this dataset is a file with only the first row.

## How the tables link

Every table has an ID column, its first column, which identifies its rows. A column that refers to another table holds the ID of a row in it. The [diagram]({{diagram}}) shows how the tables link: click a table to highlight its links, and point at a column to see what it holds.

**Plant material.** A row in Germplasm is a variety, line or other genetically distinct plant material. A row in SeedLot is a batch of seed of one germplasm, from one harvest. A seed lot can name the seed lot it was grown from, in ParentSLID, so seed can be traced back through generations.

**Experiments.** A row in Experiment is one trial, with its place, dates and set-up. Its units, the field plots, pots or samples that were scored, are in ExperimentalUnit. Each unit belongs to one experiment and holds plants from one seed lot, so the germplasm of a unit is found through its seed lot. In experiments where units were treated differently on purpose, ExperimentIntervention gives the level each unit received. Management gives the treatments that a whole experiment received.

**Scores.** A row in Phenotype is one score of one trait on one unit. Its PDID leads to PhenotypeDescription, which says what was measured, in which unit and how. A row in Climate is one climate measurement, for an experiment or for one unit in it. Its CDID leads to ClimateDescription.

**Annotations.** Features defines notes on units and on scores that no column holds, such as the tissue a sample came from. They are in the Features columns of ExperimentalUnit and Phenotype.

These are all the links:

{{links}}

## The tables

{{tables}}

## How values are written

| Type | How it is written |
|---|---|
| ID | The letters `a`–`z` and `A`–`Z`, the digits `0`–`9` and `_`, starting with a letter |
| Text | Letters, digits, spaces and the symbols of a US keyboard, apart from `;` and `=` |
| Long text | As text, and line breaks |
| List | Values of text, separated by `;`: `value1;value2` |
| Integer | A whole number |
| Number | A number, with `.` as the decimal mark and no thousands separators |
| Date | `YYYY-MM-DD` |
| Coordinates | `latitude;longitude`, in decimal degrees (WGS 84). Southern latitudes and western longitudes are negative |
| Feature list | `FTID1=value1;FTID2=value2`. See [Features cells](#features-cells) |

- **IDs** are unique within their table, even ignoring case: a table never holds both `hedin_2` and `Hedin_2`. A column that refers to another table holds the ID exactly as it is written there.
- **Text** can hold letters of any language, but no other symbols than those of a US keyboard. So symbols such as the degree sign are written in words: "degrees Celsius", "percent".
- **Scores** are numbers only. The unit is given by the trait or climate variable. Categorical scores are number codes, and the DescriptionOfMethod of their trait or climate variable says what each code means.

### Features cells

The Features cells of ExperimentalUnit and Phenotype hold one or more feature values, each written `FTID=value`, separated by `;`, with no spaces around `=` or `;`. The cell `soil_type=sandy loam;soil_ph=6.4` says that the soil type is sandy loam and the soil pH is 6.4.

- Each FTID is a row in Features, which says what the feature is, and appears at most once in a cell.
- Features on a unit describe the whole unit. Features on a score describe that score only.
- An empty cell means that the unit or score has no features.

In Features, Type says what kind of value a feature takes: `c` for text, `i` for whole numbers and `d` for real numbers. An empty Type means `c`. Unit gives the unit of the values. Vocabulary gives the values allowed: for `c`, a list separated by `;`, and for `i` and `d`, a range written `min..max`, which includes both ends, and where an end left blank has no limit. An empty Vocabulary allows any value of the type.

### Climate rows without a unit

An empty cell means that the value is missing, with one exception: an empty UNID in Climate means that the value applies to **every unit** in the experiment. A UNID that is filled in belongs to the experiment in EXPID. So join Climate to the units on EXPID, not on UNID, as in the [Quick start](#quick-start).

When the climate data come from a weather station, Distance in Experiment says how far away it is.

## Before you analyse

- **A score means nothing without its trait.** A PDID fixes the trait, its method and its unit. The DescriptionOfMethod of the PDID says what was measured, on which part of the plant, at which growth stage, on how many plants, and how the score was calculated, such as a single plant, or a mean of several.
- **One trait can have several PDIDs**: one for each method, unit or level it was scored at. Compare their DescriptionOfMethod before you put their scores together. Scores with the same PDID follow the same description, whichever experiment they are from.
- **A unit can have several scores of the same trait**: on different dates, or with different features, such as the tissue or the wavelength. Look at Date and Features before you average them.
- **Interventions.** In an experiment with interventions, each unit has one row in ExperimentIntervention, with the level it received. When an experiment has several factors, each combination of their levels is a level of its own. The Description defines each level, and says which is the control, if there is one. Experiments without interventions have no rows there.
- **Management** applies to every unit in its experiment.
- **The design.** Block, Column and Row in ExperimentalUnit give each unit's place in the design and the field. The Description of the experiment says what the blocks are.
- **Dates.** Scores can be dated after the experiment's EndDate, as harvested seed is scored later. Management and climate can be dated before its StartDate, such as fertiliser given before sowing.
- **Read the Comments columns.** They say what is known to be unusual about a value, a unit, a seed lot or an experiment.
- **Read IDs as text.** Spreadsheet programs can turn IDs into dates or numbers. The [Quick start](#quick-start) reads every value as text.
- **The same IDs in other datasets.** Other datasets in this format reuse the IDs of the plant material, seed lots, traits, climate variables and features, where they are the same. A GPID in particular is the key to other data on the same plant material, such as genotype data, which is not part of this dataset.

## Quick start

Run it in the folder with the CSV files. It reads every table, and then makes three tables that most analyses start from: each score with its trait, experiment, plant material and intervention level; the features of each unit, one per row; and each climate value, once for every unit it applies to.

**Python**, with pandas:

```python
from pathlib import Path
import pandas as pd

# Every table, by its name. Every value is read as text, so that IDs stay
# as they are written, and only an empty cell is read as missing.
tables = {path.stem: pd.read_csv(path, dtype=str, keep_default_na=False,
                                 na_values=[""])
          for path in Path(".").glob("*.csv")}
for name in ["Phenotype", "Climate"]:
    tables[name]["Score"] = pd.to_numeric(tables[name]["Score"])

# Each score with its trait, experiment, plant material
# and the intervention level of its unit.
scores = (
    tables["Phenotype"][["PHID", "UNID", "PDID", "Date", "Score"]]
    .merge(tables["PhenotypeDescription"][["PDID", "PhenotypeDescription",
                                           "Unit"]], on="PDID")
    .merge(tables["ExperimentalUnit"][["UNID", "EXPID", "SLID", "Block"]],
           on="UNID")
    .merge(tables["SeedLot"][["SLID", "GPID"]], on="SLID")
    .merge(tables["Germplasm"][["GPID", "Name"]], on="GPID")
    .merge(tables["ExperimentIntervention"][["UNID", "Intervention"]],
           on="UNID", how="left")
)

# The Features cells of the units, one feature value per row.
# Those of Phenotype split the same way, with PHID in place of UNID.
unit_features = (
    tables["ExperimentalUnit"][["UNID", "Features"]].dropna()
    .assign(Features=lambda d: d["Features"].str.split(";"))
    .explode("Features", ignore_index=True)
)
unit_features[["FTID", "Value"]] = (
    unit_features.pop("Features").str.split("=", n=1, expand=True))

# Each climate value, once for every unit it applies to.
units = tables["ExperimentalUnit"][["UNID", "EXPID"]]
climate = tables["Climate"]
climate_per_unit = pd.concat([
    climate[climate["UNID"].isna()].drop(columns="UNID")
    .merge(units, on="EXPID"),
    climate[climate["UNID"].notna()],
], ignore_index=True)
```

**R**, with readr, dplyr and tidyr:

```r
library(readr)
library(dplyr)
library(tidyr)

# Every table, by its name. Every value is read as text, so that IDs stay
# as they are written, and only an empty cell is read as missing.
files <- list.files(pattern = "\\.csv$")
tables <- lapply(setNames(files, sub("\\.csv$", "", files)), read_csv,
                 na = "", col_types = cols(.default = col_character()))
tables$Phenotype$Score <- as.numeric(tables$Phenotype$Score)
tables$Climate$Score <- as.numeric(tables$Climate$Score)

# Each score with its trait, experiment, plant material
# and the intervention level of its unit.
scores <- tables$Phenotype |>
  select(PHID, UNID, PDID, Date, Score) |>
  inner_join(select(tables$PhenotypeDescription,
                    PDID, PhenotypeDescription, Unit), by = "PDID") |>
  inner_join(select(tables$ExperimentalUnit, UNID, EXPID, SLID, Block),
             by = "UNID") |>
  inner_join(select(tables$SeedLot, SLID, GPID), by = "SLID") |>
  inner_join(select(tables$Germplasm, GPID, Name), by = "GPID") |>
  left_join(select(tables$ExperimentIntervention, UNID, Intervention),
            by = "UNID")

# The Features cells of the units, one feature value per row.
# Those of Phenotype split the same way, with PHID in place of UNID.
unit_features <- tables$ExperimentalUnit |>
  select(UNID, Features) |>
  filter(!is.na(Features)) |>
  separate_longer_delim(Features, ";") |>
  separate_wider_delim(Features, "=", names = c("FTID", "Value"))

# Each climate value, once for every unit it applies to.
units <- select(tables$ExperimentalUnit, UNID, EXPID)
climate_per_unit <- bind_rows(
  tables$Climate |> filter(is.na(UNID)) |> select(-UNID) |>
    inner_join(units, by = "EXPID", relationship = "many-to-many"),
  tables$Climate |> filter(!is.na(UNID))
)
```

Feature values are read as text. Those of features of type `i` or `d` can be turned into numbers.

## What changed in this version

{{changes}}

## Who made it

{{people}}

### Funding

{{funding}}

The dataset is looked after by {{curator}}.

## How to cite

{{citation}}

Cite the version you used, so that others can get the same data.

## Licence

The data are licensed under [CC-BY-4.0](https://creativecommons.org/licenses/by/4.0/). You may share and adapt them, for any purpose, as long as you give credit, by citing the dataset as above, and say what you changed.

## How the data were made

The data of each experiment were converted into this format from the files of the people who ran it, and checked with the format's validator. The data from all sources were then merged into one set of tables, in which the same plant material, seed lot, trait, climate variable or feature has one ID. The original files are not part of the dataset.

The format, its validator, and the list of known datasets in it, are at {{repository}}.
