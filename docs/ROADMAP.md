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
| Source of truth | `schema/schema.yaml`. The validator reads it, and tests check the collection sheet against it. `schema.md` is for people to read, so it is kept in step by hand, not by tests. |
| One schema.yaml | There is only ever **one** `schema.yaml`, in `schema/`. It is never copied into `app/` or anywhere else in the repository, and a test fails if a second one appears. |
| Validator input | A set of **CSV files**, one per table, or a filled-in **collection sheet** (.xlsx). Either way, the tables that pass can be written out as CSV files. |
| Validator errors | **Stops at the first error.** Later errors are often knock-on effects of the first one, so they are not reported. Each message names the table, row, column and value. |
| Dates | Written as `YYYY-MM-DD` everywhere, including the validator's output. |
| IDs | Only `a`–`z`, `A`–`Z`, `0`–`9` and `_`, and unique within their table ignoring case. The validator checks both. Suggested forms for each ID are in the schema doc. |
| Schema diagram | **Drawn from `schema.yaml`** by `schema/diagram.py` each time the app is published, so it never goes out of date: an interactive page next to the app, where tables can be dragged around and clicking a table highlights its links, plus a PNG and an SVG picture. No hand-drawn copy (dbdiagram.io) is kept. See [deploy-app.md](deploy-app.md#the-schema-diagram). |
| App hosting | **Shinylive on GitHub Pages**: the app runs in the visitor's browser, so data never leaves their computer, and it redeploys automatically. Replaces shinyapps.io. `schema.yaml` is bundled into the app when it is built, not copied into the repository, and not offered for download on the site. See [deploy-app.md](deploy-app.md). |
| Python | 3.12, with the package versions pinned to those of the browser app, so the tests, the command line and the app run the same ones. The app and the command line say when another version is installed. |
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
  diagram.py          draws the diagram of how the tables link from schema.yaml, for publishing with the app
  diagram.html        the interactive diagram page that diagram.py fills in
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
2. The AI asks what it needs to know, then writes a script that converts the raw data into one CSV per table. As it goes, it reports what it sees in the data (traits, number of scores, units, ranges), so the contributor can confirm it or catch mistakes early.
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

## Phase 1: Validator and app

- [x] Tests in `tests/`: one valid dataset, and one broken dataset per rule, each expected to fail with the right message.
- [x] GitHub Action that runs the tests on every push. See `.github/workflows/tests.yml`.
- [ ] Deploy with Shinylive on GitHub Pages: a GitHub Action exports the app with Shinylive and publishes it to Pages on every push to `main`, once the tests pass. See `.github/workflows/deploy-app.yml`. Tick once the first run has published the app.
  - [x] `schema.yaml` reaches the browser without a second copy in the repository: the Action builds the app from a folder outside the repository, holding `app/` and `schema.yaml`.
  - [x] The pinned versions in `app/requirements.txt` are now those of Shinylive's browser Python (pandas 2.2.3, numpy 2.0.2, PyYAML 6.0.2), as the app does not start with others. All tests pass with them.
- [x] Check that file upload works in the browser version. The Action checks it in a browser before every deploy: `tests/check_browser_app.py`.
- [ ] Once the new app works, retire the old shinyapps.io app (`n2crop-validation`), or replace it with a page pointing to the new address.
- [x] Write `docs/deploy-app.md`. Refreshing the app should be: commit and push to `main` in GitHub Desktop, then wait for the Action to finish. Include where to see whether the Action failed.

## Phase 2: Schema doc, example and AI kit

- [ ] Fill in the TODOs in `schema/schema.md` (examples, worked example) from the worked example below.
- [ ] Add a section on the files themselves: one CSV per table, named after the table, UTF-8, comma-separated, `.` as the decimal mark, one header row with the column names.
- [x] Add ID rules: only letters, digits and `_`, and unique ignoring case, both checked by the validator. The schema doc suggests a form for each ID, with experiment-level IDs (UNID, PHID, IID, MMID, CLID) starting with their EXPID, so IDs never clash when contributions are merged. See [Identifiers](../schema/schema.md#identifiers).
- [ ] Draw the diagram from `schema.yaml` on every deploy, instead of keeping a dbdiagram.io copy: `schema/diagram.py` and `schema/diagram.html`, published at <https://fababase.github.io/phenotype-database-format/diagram/>. The README and `schema.md` link to it. Tick once the first run has published it.
- [ ] Build the worked example in `examples/demo/`: a fake but realistically messy raw Excel file (wide format, coloured rows, merged cells), the script that converts it, the resulting tables and the NOTES.md.
- [ ] Start the shared reference tables in `reference/`, from the N2CROP data.
- [ ] Write `conversion/AI_INSTRUCTIONS.md`, telling the AI to:
  - **Inspect before coding:** every sheet, hidden rows and columns, merged cells, multi-row headers, cell colours, comments, notes below tables, decimal commas and home-made "NA" markers. Use openpyxl, since pandas cannot see colours or merged cells.
  - **Ask, don't guess:** what a unit is, what colours and formatting mean, the unit and method of each trait, what categorical codes mean, which rows to leave out. Never invent metadata; leave it empty and list it in NOTES.md.
  - **Reuse IDs:** map germplasm, traits, climate variables and features to the reference tables, and list any new ones it proposes so they can be approved.
  - **Deliver a script, not just tables:** the AI writes `convert.py`, a script that turns the messy raw Excel file into the correct CSV files, one per table. The script is saved with the contribution, so the conversion can be rerun and checked later. Raw files are read-only, every decision is in the code, and nothing is edited by hand afterwards.
  - **Report what it sees** while it writes and runs the script, so the contributor can say "yes, that's right" or spot at once that something is badly wrong. For example: which traits were scored and how many scores each has, how many units, experiments and germplasm there are, the date range, the value range of each trait, and which rows were left out and why.
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

- **IDs that start with a digit.** The schema doc recommends against them. Decide whether to make it a rule the validator checks.
- **Special symbols.** We may restrict special symbols in values where possible, so that each one has a single defined meaning, and any other use is an error.
- **Dates that make sense.** The validator only checks that a date is real and written YYYY-MM-DD. Possible additions:
  - No dates in the future.
  - A warning, not an error, for very early dates.
  - An experiment's StartDate is not after its EndDate.
  - One warning per table, not per row, when Phenotype, Management or Climate dates fall outside their experiment's StartDate–EndDate.
  - Maybe stricter: Management dates are not after their experiment's EndDate, and Phenotype dates are not before its StartDate.
  - When a date falls outside its experiment but swapping day and month would bring it inside, say so.
  - A parent seed lot (ParentSLID) is harvested before its child.
  - A seed lot is harvested before the phenotype dates of the units sown from it.
  - A Phase 4 plot of the Phenotype, Management and Climate dates against each experiment's StartDate–EndDate.
- **ParentSLID loops.** Check that ParentSLID chains never loop back on themselves (A → A, or A → B → A).
- **Coordinates in range.** `91;181` passes. Decide whether to check latitude −90 to 90 and longitude −180 to 180.
- **Infinite numbers.** `1e999` passes as a number, though it is read as infinity.
- **Digits other than 0–9.** Digits such as `１２` (full-width) and `٣` (Arabic-Indic) pass as numbers.
- **Hidden sheets.** A hidden sheet in the collection sheet, such as one holding dropdown lists, is an error. Decide whether to skip hidden sheets.
- **Case in column names.** `species` gets "Did you mean 'Species'?", but `gpid` gets no suggestion for `GPID`. Decide whether to ignore case when suggesting, or when matching column names.
- **Blank lines in CSV files.** They are dropped. Decide whether they should be an error.
