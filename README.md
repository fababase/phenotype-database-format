# FabaBase phenotype database: format and validation

This repository describes and checks the format of the FabaBase phenotype database: a set of 11 linked tables for phenotype data from plant experiments. It holds the schema, a collection sheet for filling in by hand, and an app that checks data against the schema. The data itself is not stored here; it will be published on Zenodo.

> [!NOTE]
> This repository is being restructured. See the [roadmap](docs/ROADMAP.md) for what is planned and what is done.

## What is here

| Path | What it is |
|---|---|
| [schema/schema.md](schema/schema.md) | The schema: every table and column, the conventions and the special rules. **Start here.** |
| [schema/diagram.png](schema/diagram.png) | How the tables link together. |
| [template/collection-sheet.xlsx](template/collection-sheet.xlsx) | Blank collection sheet, one sheet per table, for filling in by hand. |
| [app/](app/) | The validation app. `validation.py` holds the checks, `app.py` the user interface. |
| [docs/ROADMAP.md](docs/ROADMAP.md) | Decisions, planned work and open questions. |

## Checking your data

The validation app runs at <https://troelsmou.shinyapps.io/n2crop-validation/>. Upload a filled-in collection sheet and it reports the first problem it finds, such as an ID in one table that is missing from the table it links to.

The app is moving to GitHub Pages, where it will run in your browser so your data never leaves your computer. The address will be added here.

## Contributing data

1. Read the [schema](schema/schema.md).
2. Fill in the [collection sheet](template/collection-sheet.xlsx), or convert your data into the same tables. The *READ ME 1st* sheet explains the steps.
3. Check it with the [validation app](#checking-your-data) and fix what it reports.

A step-by-step guide, including how to convert messy raw data with the help of an AI, is planned (see the [roadmap](docs/ROADMAP.md#phase-2-schema-doc-example-and-ai-kit)).

## Running the app locally

With [Anaconda](https://www.anaconda.com/), from the repository folder:

```
conda create -n fababase python=3.12
conda activate fababase
pip install -r app/requirements.txt
shiny run app/app.py
```

Then open the address it prints (usually <http://127.0.0.1:8000>).

## Licences

- **Code** (everything in `app/`, and future scripts and tests): GPL-3.0, see [LICENSE](LICENSE).
- **Content** (the schema documentation and diagram, the collection sheet, the reference tables and the published data): CC-BY-4.0, see [LICENSE-CONTENT](LICENSE-CONTENT).
