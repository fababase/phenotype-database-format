# FabaBase phenotype database: format and validation

This repository describes and checks the format of the FabaBase phenotype database: a set of linked tables for phenotype data from plant experiments. It holds the schema, a collection sheet for filling in by hand, and an app that checks data against the schema. The data itself is not stored here; it will be published on Zenodo.

> [!NOTE]
> This repository is being restructured. See the [roadmap](docs/ROADMAP.md) for what is planned and what is done.

## What is here

| Path | What it is |
|---|---|
| [schema/schema.md](schema/schema.md) | The schema: every table and column, the conventions and the special rules. **Start here.** |
| [schema/schema.yaml](schema/schema.yaml) | The same schema in machine-readable form, with its version number and a description of every column. The validator reads it, and the collection sheet, the diagram and the tables in `schema.md` that list the tables and columns are made from it. |
| [Schema diagram](https://fababase.github.io/phenotype-database-format/diagram/) | How the tables link together. Point at a column to see its description, drag the tables around, and click one to highlight its links. Also as a picture: [PNG](https://fababase.github.io/phenotype-database-format/diagram/diagram.png), [SVG](https://fababase.github.io/phenotype-database-format/diagram/diagram.svg). |
| Collection sheet | A workbook with one sheet per table, for filling in by hand. Download a blank one from the [app](https://fababase.github.io/phenotype-database-format/). |
| [app/](app/) | The validator. `validation.py` holds the checks and runs from the command line; `app.py` is the app around it; `collection_sheet.py` builds the blank collection sheet. |
| [docs/datasets.md](docs/datasets.md) | Every known dataset in the format, by DOI. Look here for IDs to reuse. |
| [docs/deploy-app.md](docs/deploy-app.md) | How the app is published, and how to refresh it. |
| [docs/ROADMAP.md](docs/ROADMAP.md) | Decisions, planned work and open questions. |

## Checking your data

The validator checks a set of tables against the [schema](schema/schema.yaml). Give it either:

- one CSV file per table, named after the table: `Germplasm.csv`, `SeedLot.csv`.
- or one filled-in collection sheet.

It stops at the first problem it finds and says where it is and sometimes how to fix it, for example:

```
Climate.csv, row 2, column Score: '11,7167' has ','. Numbers have '.' as the decimal mark and no thousands separator, so write 11.7167
```

When everything passes, it can hand back the tables as clean CSV files, (hopefully) ready for upload to the database.

**From the command line** (see [Running locally](#running-locally) for the setup):

```
python app/validation.py path/to/folder-of-csv-files
python app/validation.py collection-sheet.xlsx --out path/to/new-folder
```

**In the app**: <https://fababase.github.io/phenotype-database-format/>. It runs in your browser, so your data never leaves your computer. The first visit takes a while, as your browser downloads what the app needs to run.

## Contributing data

1. Read the [schema](schema/schema.md).
2. Look up the IDs already used for your germplasm, seed lots, traits, climate variables and features in the [known datasets](docs/datasets.md) that you have access to, and reuse them.
3. Fill in a collection sheet, which you can download from the [app](https://fababase.github.io/phenotype-database-format/), or convert your data into the same tables. The sheet's *READ ME 1st* explains how to fill it in.
4. Check it with the [validation app](#checking-your-data) and fix what it reports.

A step-by-step guide, including how to convert messy raw data with the help of an AI, is planned (see the [roadmap](docs/ROADMAP.md#phase-2-schema-doc-example-and-ai-kit)).

## Running locally

With [Anaconda](https://www.anaconda.com/), from the repository folder:

```
conda create -n fababase python=3.12
conda activate fababase
pip install -r app/requirements.txt
```

Then either check files from the command line (`python app/validation.py --help` lists the options), or start the app with `shiny run app/app.py` and open the address it prints (usually <http://127.0.0.1:8000>). `python app/collection_sheet.py collection-sheet.xlsx` builds a blank collection sheet.

After you push a change to `schema/schema.yaml`, the *Update schema.md* Action writes the tables in `schema.md` that list the tables and columns, and commits them. Pull afterwards (*Pull origin* in GitHub Desktop) to get that commit. To see the tables before pushing, run `python schema/schema_md.py`.

## Licences

- **Code** (everything in `app/`, and future scripts and tests): GPL-3.0, see [LICENSE](LICENSE).
- **Content** (the schema documentation and diagram, the collection sheet and the published data): CC-BY-4.0, see [LICENSE-CONTENT](LICENSE-CONTENT).
