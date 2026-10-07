# Roadmap

This repository holds everything that describes and checks the phenotype database format: the schema, the collection sheet, the validation app, the shared reference tables and the guide for converting messy data with an AI. The data itself is published on Zenodo.

This roadmap records the decisions made so far, the work in order, and the questions still open. Tick items off as they are done.

## Contents

- [Decisions](#decisions)
- [Target layout](#target-layout)
- [How data flows](#how-data-flows)
- [Phase 0: Clean up and restructure](#phase-0-clean-up-and-restructure)
- [Phase 1: Validator and app](#phase-1-validator-and-app)
- [Phase 2: Schema doc, example and AI kit](#phase-2-schema-doc-example-and-ai-kit)
- [Phase 3: Publish on Zenodo](#phase-3-publish-on-zenodo)
- [Phase 4: Validator plots](#phase-4-validator-plots)
- [Phase 5: A central AI agent](#phase-5-a-central-ai-agent)
- [Open questions](#open-questions)

## Decisions

| Topic | Decision |
|---|---|
| Repository | One **public** GitHub repo for the schema, collection sheet, validator, app, shared reference tables, AI guide and worked example. They change together, so they are versioned together. |
| Repository name | May be renamed, since it holds more than the app. Name to be decided; see [Phase 0](#phase-0-clean-up-and-restructure). |
| Data in git | **Never.** Contributions are kept in a private folder until published. |
| Zenodo | **One record** for the whole database. New contributions and corrections become new versions of that record. |
| What is published | **Only the formatted tables**, plus the README and the schema doc. Raw files and conversion scripts are kept privately, not published. |
| Source of truth | `schema/schema.yaml`. The validator reads it, and tests check the doc and the collection sheet against it. |
| Validator input | A set of **CSV files**, one per table. |
| Validator errors | **Stops at the first error.** Later errors are often knock-on effects of the first one, so they are not reported. Each message names the table, row, column and value. |
| Dates | Written as `YYYY-MM-DD` everywhere, including the validator's output. |
| App hosting | **Shinylive on GitHub Pages**: the app runs in the visitor's browser, so data never leaves their computer, and it redeploys automatically. Replaces shinyapps.io. |
| Python | Updated from 3.9 to a current version, with pinned package versions. |
| AI conversion | Done by **contributors**, using the AI kit in this repo. A central AI agent may follow later ([Phase 5](#phase-5-a-central-ai-agent)). |
| Shared reference tables | Curated master lists of Germplasm, PhenotypeDescription, ClimateDescription and Features live in this repo, under `reference/`. |
| Licences | Code: GPL-3.0. Schema doc, collection sheet, reference tables and published data: CC-BY-4.0. |
| Committing | Through GitHub Desktop. |

## Target layout

```
README.md             start here: what this is, links to schema, app, how to contribute data
LICENSE               GPL-3.0 (code)
LICENSE-CONTENT       CC-BY-4.0 (schema doc, collection sheet, reference tables)
CITATION.cff          how to cite
CHANGELOG.md          what changed in each schema version
.gitignore
schema/
  schema.md           the schema description (was phenotype-database-schema.md)
  schema.yaml         machine-readable copy: tables, columns, types, required, unique, links
  diagram.png         relationships between the tables
  diagram.dbml        dbdiagram.io source of the diagram, so it can be redrawn
template/
  collection-sheet.xlsx   blank collection sheet for filling in by hand
reference/            shared master lists: Germplasm, PhenotypeDescription, ClimateDescription, Features
app/                  exactly what gets deployed
  app.py              UI only
  validation.py       all checks; also runs from the command line
  requirements.txt    pinned versions
conversion/
  AI_INSTRUCTIONS.md  the prompt contributors give an AI along with the schema and their raw data
examples/demo/        fake messy raw file → convert.py → validated tables → NOTES.md
zenodo/
  README_TEMPLATE.md  README for the Zenodo record
docs/
  ROADMAP.md          this file
  deploy-app.md       how the app is deployed and how to refresh it
  submit-data.md      raw data → AI → script → validate → hand over
  release.md          how to release a new schema version and a new Zenodo version
tests/                one valid dataset plus deliberately broken ones; run on every push
.github/workflows/    run tests on every push; deploy the app when they pass
```

## How data flows

1. A contributor gives an AI the AI kit (the schema doc, `schema.yaml`, `AI_INSTRUCTIONS.md`, the reference tables and the worked example) and a trimmed copy of their raw data.
2. The AI asks what it needs to know, then writes a script that converts the raw data into one CSV per table.
3. The contributor runs the script on the full data and checks the CSVs with the validator, fixing the script until they pass.
4. The contributor hands over the bundle below. It is kept privately.
5. The tables of all contributions are merged and published as a new version of the Zenodo record.

Each contribution is kept privately as:

```
<contribution>/
  raw/                    exactly as received, never edited
  conversion/convert.py   the script: raw/ → tables/
  conversion/NOTES.md     questions & answers, assumptions, row counts in vs. out
  tables/                 Germplasm.csv … Features.csv
```

Only the tables go to Zenodo.

## Phase 0: Clean up and restructure

Order matters: remove the clutter that is committed now, commit that, and only then add the `.gitignore`.

- [ ] Delete files that should not be in the repo and commit the deletion:
  - `Thumbs.db`
  - `.gitignore.txt` (empty and misnamed; git only reads a file called exactly `.gitignore`)
  - `manifest.json` and `rsconnect-python/` (only used for shinyapps.io deploys, which Shinylive replaces)
- [ ] Add `.gitignore` and commit it. Data is blocked by default and allowed only in known-safe places:

  ```gitignore
  # Data: block by default, allow known-safe places
  *.xlsx
  *.xls
  *.csv
  !template/*.xlsx
  !reference/*.csv
  !examples/**
  !tests/**
  data/

  # Python, environments, build output
  __pycache__/
  .venv/
  site/

  # Windows / Office clutter (~$ = Excel lock files)
  Thumbs.db
  desktop.ini
  ~$*
  .env
  ```

- [ ] Move files into the [target layout](#target-layout):
  - `phenotype-database-schema.md` → `schema/schema.md`
  - `Database_schema.png` → `schema/diagram.png`
  - `Database_collection_N2CROP.xlsx` → `template/collection-sheet.xlsx`, with the FAKE DATA rows removed (they become part of the worked example)
  - `app.py`, `validation.py`, `requirements.txt` → `app/`
- [ ] Decide on a new repository name, and rename the repo **before** setting up GitHub Pages, because the app's address includes the repo name.
  - Rename on GitHub: Settings → General → Repository name. GitHub redirects the old address.
  - In GitHub Desktop: Repository → Repository settings → Remote, and update the URL.
- [ ] Split the licence: keep `LICENSE` (GPL-3.0) for code and add `LICENSE-CONTENT` (CC-BY-4.0) for the schema doc, collection sheet and reference tables. Say which applies to what in the README.
- [ ] Write a first `README.md`: what this is, links to the schema, the app and how to contribute data.
- [ ] Set up a Python environment on a current Python version for running the validator and tests locally.

## Phase 1: Validator and app

- [ ] Write `schema/schema.yaml`: every table and column, with type, required, unique and links, following [schema.md](../schema/schema.md). Give it a schema version number.
- [ ] Rewrite `app/validation.py` to read `schema.yaml` instead of hard-coding columns:
  - [ ] Read a set of CSV files, one per table, named after the table (`Germplasm.csv`, `SeedLot.csv`, …). Tables that are only needed sometimes (ExperimentIntervention, Management, ClimateDescription, Climate, Features) may be missing.
  - [ ] Cover all 11 tables, including Features.
  - [ ] Cover the special rules in the schema doc: Features cells, feature types and vocabularies, Climate's empty UNID meaning all units, a Climate UNID belonging to its EXPID, and one intervention level per unit.
  - [ ] Treat only empty cells and `NULL` as missing, as the schema doc says.
  - [ ] Accept and write dates as `YYYY-MM-DD`.
  - [ ] Stop at the first error, with a message that names the table, row, column and value, and says what was expected.
  - [ ] Say which schema version the data was checked against.
  - [ ] Run from the command line as well (`python validation.py <folder>`), so contributors and AI agents can run it locally.
- [ ] Update `app/app.py`: upload several CSV files at once, show the result, show the schema version.
- [ ] Pin package versions in `app/requirements.txt`.
- [ ] Tests in `tests/`: one valid dataset, and one broken dataset per rule, each expected to fail with the right message.
- [ ] GitHub Action that runs the tests on every push.
- [ ] Deploy with Shinylive on GitHub Pages: a GitHub Action exports the app with Shinylive and publishes it to Pages on every push to `main`, once the tests pass.
- [ ] Check that file upload works in the browser version.
- [ ] Once the new app works, retire the old shinyapps.io app (`n2crop-validation`), or replace it with a page pointing to the new address.
- [ ] Write `docs/deploy-app.md`. Refreshing the app should be: commit and push to `main` in GitHub Desktop, then wait for the Action to finish. Include where to see whether the Action failed.

## Phase 2: Schema doc, example and AI kit

- [ ] Fill in the TODOs in `schema/schema.md` (examples, worked example, diagram link) from the worked example below.
- [ ] Add a section on the files themselves: one CSV per table, named after the table, UTF-8, comma-separated, `.` as the decimal mark, one header row with the column names.
- [ ] Add an ID rule for merging: experiment-level IDs (EXPID, UNID, PHID, IID, MMID, CLID) start with a prefix unique to the contribution, so IDs never clash when contributions are merged.
- [ ] Add `schema/diagram.dbml`, the dbdiagram.io source of the diagram.
- [ ] Build the worked example in `examples/demo/`: a fake but realistically messy raw Excel file (wide format, coloured rows, merged cells), the script that converts it, the resulting tables and the NOTES.md.
- [ ] Start the shared reference tables in `reference/`, from the N2CROP data.
- [ ] Write `conversion/AI_INSTRUCTIONS.md`, telling the AI to:
  - **Inspect before coding:** every sheet, hidden rows and columns, merged cells, multi-row headers, cell colours, comments, notes below tables, decimal commas and home-made "NA" markers. Use openpyxl, since pandas cannot see colours or merged cells.
  - **Ask, don't guess:** what a unit is, what colours and formatting mean, the unit and method of each trait, what categorical codes mean, which rows to leave out. Never invent metadata; leave it empty and list it in NOTES.md.
  - **Reuse IDs:** map germplasm, traits, climate variables and features to the reference tables, and list any new ones it proposes so they can be approved.
  - **Keep everything in the script:** raw files are read-only, every decision is in the code, and nothing is edited by hand afterwards. The script writes one CSV per table.
  - **Run the validator** and fix the script until the tables pass.
  - **Write NOTES.md:** the questions asked and the answers, the assumptions made, and row counts in the raw data vs. in the tables.
  - Work from a trimmed copy of the raw data (headers and some rows) where possible, so the full data does not have to be uploaded to an AI service.
- [ ] Write `docs/submit-data.md` for contributors: the steps in [How data flows](#how-data-flows), what to hand over, and a short list of checks to do by hand, such as tracing about 10 random values back to the raw file.
- [ ] Pilot the kit on 2–3 real messy datasets, and improve the instructions based on what the AI gets wrong.

## Phase 3: Publish on Zenodo

- [ ] Write `zenodo/README_TEMPLATE.md` for the record: what the database is, the contributions it contains and who made them, experiments and locations, the schema version, the list of files, how the tables link, licence, how to cite, contact.
- [ ] Write a merge script that combines the tables of all contributions into one set of tables, and validate the merged set.
- [ ] Decide what goes into each version of the record: the merged tables, the README, and `schema.md`, `schema.yaml` and the diagram for the schema version used, so the record makes sense without GitHub.
- [ ] Before publishing, check for personal names (ScoredBy, Manager) and confidential breeding lines. Zenodo records are effectively permanent.
- [ ] Do a first upload on [sandbox.zenodo.org](https://sandbox.zenodo.org), then publish the real record.
- [ ] Add `CITATION.cff`.
- [ ] Write `docs/release.md`: how to release a new schema version (update `schema.yaml`, `schema.md`, the collection sheet and `CHANGELOG.md`, run the tests, tag a release) and how to publish a new version of the Zenodo record.

## Phase 4: Validator plots

The app's right-hand panel is reserved for plots that help spot data that passes validation but is wrong. Which plots to show is still to be decided. Ideas:

- the range or distribution of each trait
- the number of scores per unit
- a trait plotted over Row × Column of the field, where a shifted row stands out

## Phase 5: A central AI agent

To be explored later: instead of each contributor setting up an AI themselves, a central AI agent that already has the AI kit loaded, so contributors only bring their raw data. This phase is about finding out what form that could take.

## Open questions

- **New repository name.** Needed before Phase 1, since the app's address depends on it.
- **The hand-filled collection sheet.** The validator now takes CSV files, so a filled-in sheet has to become CSVs first. Saving each sheet as CSV from Excel is error-prone: Danish Excel writes `;` as the separator and `,` as the decimal mark. Options:
  - the app turns an uploaded sheet into CSVs before validating (recommended; little code, and the app then also offers the CSVs as a download)
  - a small script that does the same
  - contributors with a filled-in sheet use the AI route too
- **Merged tables or one folder per contribution** in the Zenodo record. Merged tables make one database that is easy to use, and each contribution can still be traced through its experiments (EXPID). This is the recommendation.
- **Confidential germplasm.** If some breeding lines cannot be public, they cannot be in `reference/` either. Decide how to handle them.
