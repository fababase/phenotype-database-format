# FabaBase phenotype database: format and validation

This repository describes and checks the format of the FabaBase phenotype database: a set of linked tables for phenotype data from plant experiments. It holds the schema, the validator and its app, and the guides and scripts that take data from a contributor's files to Zenodo. The data itself is not stored here, but on Zenodo: see [docs/datasets.md](docs/datasets.md).

## What is here

| Path | What it is |
|---|---|
| [schema/schema.md](schema/schema.md) | The schema: every table and column, the conventions and the special rules. **Start here.** |
| [schema/schema.yaml](schema/schema.yaml) | The same schema in machine-readable form, with its version number and a description of every column. The validator reads it, and the collection sheet, the diagram and the tables in `schema.md` that list the tables and columns are made from it. |
| [Schema diagram](https://fababase.github.io/phenotype-database-format/diagram/) | How the tables link together. Point at a column to see its description, drag the tables around, and click one to highlight its links. Earlier versions of the schema can be chosen at the top. Also as a picture: [PNG](https://fababase.github.io/phenotype-database-format/diagram/diagram.png), [SVG](https://fababase.github.io/phenotype-database-format/diagram/diagram.svg). |
| Collection sheet | A workbook with one sheet per table, for filling in by hand. Download a blank one from the [app](https://fababase.github.io/phenotype-database-format/). |
| [app/](app/) | The validator. `validation.py` holds the checks and runs from the command line; `app.py` is the app around it; `collection_sheet.py` builds the blank collection sheet. |
| [docs/datasets.md](docs/datasets.md) | Every known dataset in the format, by DOI. Look here for IDs to reuse. |
| [docs/submit-data.md](docs/submit-data.md) | For contributors: how to convert your data into the format, with an AI or without, and hand it over. |
| [docs/review-data.md](docs/review-data.md) | For reviewers: what a finished conversion is checked against, and its FAIR score. |
| [conversion/AI_INSTRUCTIONS.md](conversion/AI_INSTRUCTIONS.md) | What the AI follows when it converts a contributor's data. |
| [merging/AI_INSTRUCTIONS.md](merging/AI_INSTRUCTIONS.md) | What the AI follows when it merges contributions into one set of tables, for the data manager. |
| [publishing/](publishing/) | Publishing on Zenodo. `build.py` builds the README and the metadata of a version from a merge, from `README_TEMPLATE.md`, and `publish.py` uploads them to a draft on Zenodo. |
| [docs/deploy-app.md](docs/deploy-app.md) | How the app is published, and how to refresh it. |
| [docs/ROADMAP.md](docs/ROADMAP.md) | Decisions, planned work and open questions. |

## Checking your data

The validator checks a set of tables against the [schema](schema/schema.yaml). Give it either:

- one CSV file per table, named after the table: `Germplasm.csv`, `SeedLot.csv`.
- or one filled-in collection sheet.

With either, give it `contributors.yaml`, which says who to credit (see [Who to credit](docs/submit-data.md#who-to-credit)), and it checks that too.

It stops at the first problem it finds and says where it is and sometimes how to fix it, for example:

```
Climate.csv, row 2, column Score: '11,7167' has ','. Numbers have '.' as the decimal mark and no thousands separator, so write 11.7167
```

When everything passes, it can hand back the tables as clean CSV files, with `contributors.yaml` as it was given.

**From the command line** (see [Running locally](#running-locally) for the setup):

```
python app/validation.py path/to/folder-of-csv-files
python app/validation.py collection-sheet.xlsx --out path/to/new-folder
```

**In the app**: <https://fababase.github.io/phenotype-database-format/>. It runs in your browser, so your data never leaves your computer. The first visit takes a while, as your browser downloads what the app needs to run.

## How data gets to Zenodo

1. **Convert.** A contributor turns their files into the tables, with an AI, with a script of their own, or with the collection sheet, as in [docs/submit-data.md](docs/submit-data.md).
2. **Review.** A fresh AI session or a colleague checks the result and gives it a FAIR score, as in [docs/review-data.md](docs/review-data.md).
3. **Hand over.** How is still to be decided.
4. **Merge.** An AI merges the contributions into one set of tables for the data manager, as in [merging/AI_INSTRUCTIONS.md](merging/AI_INSTRUCTIONS.md).
5. **Publish.** The scripts in [publishing/](publishing/) build the README and upload it with the tables to Zenodo, as a new version of the public dataset or of a project's restricted one.

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

- **Code** (the scripts in `app/`, `schema/` and `publishing/`, and the tests): GPL-3.0, see [LICENSE](LICENSE).
- **Content** (the schema documentation and diagram, the collection sheet and the published data): CC-BY-4.0, see [LICENSE-CONTENT](LICENSE-CONTENT).
