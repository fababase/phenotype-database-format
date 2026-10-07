# FabaBase phenotype database: format and validation

This repository describes and checks the format of the FabaBase phenotype database: a set of 11 linked tables for phenotype data from plant experiments. It holds the schema, a collection sheet for filling in by hand, and an app that checks data against the schema. The data itself is not stored here; it will be published on Zenodo.

> [!NOTE]
> This repository is being restructured. See the [roadmap](docs/ROADMAP.md) for what is planned and what is done.

## What is here

| Path | What it is |
|---|---|
| [schema/schema.md](schema/schema.md) | The schema: every table and column, the conventions and the special rules. **Start here.** |
| [schema/schema.yaml](schema/schema.yaml) | The same schema in machine-readable form, with its version number. The validator reads it. |
| [schema/diagram.png](schema/diagram.png) | How the tables link together. |
| [template/collection-sheet.xlsx](template/collection-sheet.xlsx) | Blank collection sheet, one sheet per table, for filling in by hand. |
| [app/](app/) | The validator. `validation.py` holds the checks and runs from the command line; `app.py` is the app around it. |
| [docs/ROADMAP.md](docs/ROADMAP.md) | Decisions, planned work and open questions. |

## Checking your data

The validator checks a set of tables against [schema version 1.0.0](schema/schema.yaml). Give it either:

- one CSV file per table, named after the table: `Germplasm.csv`, `SeedLot.csv`, … Columns can be in any order, and optional columns can be left out. Comma-, semicolon- and tab-separated files all work.
- or one filled-in [collection sheet](template/collection-sheet.xlsx).

It stops at the first problem it finds and says where it is and how to fix it, for example:

```
Climate.csv, row 2, column Score: '11,7167' has ',' as the decimal mark. Use '.' instead: 11.7167
```

When everything passes, it can hand back the tables as clean CSV files: UTF-8, comma-separated, dates as `YYYY-MM-DD`.

**From the command line** (see [Running locally](#running-locally) for the setup):

```
python app/validation.py path/to/folder-of-csv-files
python app/validation.py collection-sheet.xlsx --out path/to/new-folder
```

**In the app**: run it locally as below. It is moving to GitHub Pages, where it will run in your browser so your data never leaves your computer; the address will be added here. The old app at <https://troelsmou.shinyapps.io/n2crop-validation/> still runs the previous version, which only takes a collection sheet.

## Contributing data

1. Read the [schema](schema/schema.md).
2. Fill in the [collection sheet](template/collection-sheet.xlsx), or convert your data into the same tables. The *READ ME 1st* sheet explains the steps.
3. Check it with the [validation app](#checking-your-data) and fix what it reports.

A step-by-step guide, including how to convert messy raw data with the help of an AI, is planned (see the [roadmap](docs/ROADMAP.md#phase-2-schema-doc-example-and-ai-kit)).

## Running locally

With [Anaconda](https://www.anaconda.com/), from the repository folder:

```
conda create -n fababase python=3.12
conda activate fababase
pip install -r app/requirements.txt
```

Then either check files from the command line (`python app/validation.py --help` lists the options), or start the app with `shiny run app/app.py` and open the address it prints (usually <http://127.0.0.1:8000>).

## Licences

- **Code** (everything in `app/`, and future scripts and tests): GPL-3.0, see [LICENSE](LICENSE).
- **Content** (the schema documentation and diagram, the collection sheet, the reference tables and the published data): CC-BY-4.0, see [LICENSE-CONTENT](LICENSE-CONTENT).
