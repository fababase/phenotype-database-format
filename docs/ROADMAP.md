# Roadmap

This repository holds everything that describes and checks the phenotype database format: the schema, the collection sheet, the validation app, the list of datasets in the format and the guide for converting messy data with an AI. The data itself is published on Zenodo.

This roadmap records the decisions made so far, the work in order, and the questions still open. Tick items off as they are done.

## Contents

- [Decisions](#decisions)
- [Target layout](#target-layout)
- [How data flows](#how-data-flows)
- [Phase 2: Schema doc, example and AI kit](#phase-2-schema-doc-example-and-ai-kit)
- [Phase 3: Publish on Zenodo](#phase-3-publish-on-zenodo)
- [Phase 4: Validator plots](#phase-4-validator-plots)
- [Phase 5: A central AI agent](#phase-5-a-central-ai-agent)
- [Open questions](#open-questions)

## Decisions

| Topic | Decision |
|---|---|
| Repository | One **public** GitHub repo for the schema, collection sheet, validator, app, list of datasets and AI guide. They change together, so they are versioned together. |
| Data | **On Zenodo.** Contributions are kept in private records until published on a public record. |
| Zenodo | **One record** for the whole public database, several private records for each project group of unpublished data. New contributions and corrections become new versions of those records. |
| What is published | **Only the formatted tables**, plus the README and the schema doc. Raw files, conversion scripts and AI notes are kept privately, not published. |
| Source of truth | `schema/schema.yaml`, including one description per column, and what one row of each table is. The validator reads it. Almost everything that lists the tables or columns is made from it, so it cannot go out of step: the collection sheet, the diagram, and the tables in `schema.md` that list the tables and columns. Those tables are written between marker comments by the *Update schema.md* Action on every push to main, with `schema/schema_md.py`, and committed back. The rest of `schema.md` is written by hand. |
| Collection sheet | **Built from `schema.yaml` by the app**, which offers it for download. One sheet per table, named after it. Row 2 says what goes in each column: required or optional, the description and a hint for the type. The validator skips row 2 when its first cell starts with that help text. A short *READ ME 1st* sheet gives the schema version, how to fill it in, links, and the list of tables; it is generated from `schema/schema.yaml`. |
| One schema.yaml | There is only ever **one** `schema.yaml`, in `schema/`, so there is no confusion about format, **ever**. It is never copied into `app/` or anywhere else in the repository, and a test fails if a second one appears. |
| Validator input | A set of **CSV files**, one per table, or a filled-in **collection sheet** (.xlsx). Either way, the tables that pass can be written out as CSV files. |
| Validator errors | **Stops at the first error.** Later errors are often knock-on effects of the first one, so they are not reported. Each message names the table, row, column and value, and hint where possible. |
| Format | All written in `schema/schema.yaml`. |
| Schema diagram | **Drawn from `schema.yaml`** by `schema/diagram.py` each time the app is published: an interactive page next to the app, where tables can be dragged around, clicking a table highlights its links, and pointing at a column, a table's name or a link says what it is (a column's description, type hint and example, as in row 2 of the collection sheet), plus a PNG and an SVG picture, which keeps that text as tooltips. See [deploy-app.md](deploy-app.md#the-schema-diagram). |
| App hosting | **Shinylive on GitHub Pages**: the app runs in the visitor's browser, so data never leaves their computer, and it redeploys automatically on push. `schema.yaml` is bundled into the app when it is built. See [deploy-app.md](deploy-app.md). |
| Packages | See requirements.txt. |
| AI conversion | Done by **contributors**, using the AI kit in this repo. A central AI agent may follow later ([Phase 5](#phase-5-a-central-ai-agent)). |
| Existing data | The IDs to reuse across datasets and even projects are in the datasets themselves, on Zenodo. [docs/datasets.md](datasets.md) lists every known dataset in the format by DOI: the published FabaBase record, and the records of ongoing projects, which may be restricted. A restricted record's page is public, so people and AIs are pointed to it, and those with access can get the files. |
| Licences | Code: GPL-3.0. Schema doc, collection sheet and published data: CC-BY-4.0. |

## Target layout

```
README.md             start here: what this is, links to schema, app, how to contribute data
LICENSE               GPL-3.0 (code)
LICENSE-CONTENT       CC-BY-4.0 (schema doc, collection sheet)
CITATION.cff          how to cite
CHANGELOG.md          what changed in each schema version
.gitignore
schema/
  schema.md           the schema description (was phenotype-database-schema.md)
  schema.yaml         machine-readable copy: tables, columns, types, required, unique, links, descriptions
  schema_md.py        writes the tables in schema.md that list the tables and columns, from schema.yaml
  diagram.py          draws the diagram of how the tables link from schema.yaml, for publishing with the app
  diagram.html        the interactive diagram page that diagram.py fills in
app/                  exactly what gets deployed
  app.py              UI only
  validation.py       all checks; also runs from the command line
  collection_sheet.py builds the blank collection sheet from schema.yaml, for download from the app
  requirements.txt    pinned versions
conversion/
  AI_INSTRUCTIONS.md  the prompt contributors give an AI along with the schema and their raw data
zenodo/
  README_TEMPLATE.md  README for the Zenodo record
docs/
  ROADMAP.md          this file
  datasets.md         every known dataset in the format, by DOI, to reuse IDs from
  deploy-app.md       how the app is deployed and how to refresh it
  submit-data.md      raw data → AI → script → validate → hand over
  release.md          how to release a new schema version and a new Zenodo version
tests/                one valid dataset plus deliberately broken ones; run on every push
.github/workflows/    run tests on every push; deploy the app when they pass; write the tables in schema.md
```

## How data flows

1. A contributor gives an AI the AI kit (the schema doc, `schema.yaml`, `AI_INSTRUCTIONS.md`, the datasets in `docs/datasets.md` and the example dataset in `tests/valid/`) and (a perhaps trimmed copy of) their raw data.
2. The AI asks what it needs to know, then writes a script that converts the raw data into one CSV per table. As it goes, it reports what it sees in the data (traits, number of scores, units, ranges), so the contributor can confirm it or catch mistakes early.
3. The AI and the contributor runs the script on the full data and checks the CSVs with the validator, fixing the script until they pass.
4. The contributor hands over the bundle below. It is kept privately, by a data manager.
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

## Phase 2: Schema doc, example and AI kit

- [x] Fill in the TODOs in `schema/schema.md` (examples, worked example) from the valid test dataset, `tests/valid/`, instead of building a separate worked example with a fake messy Excel file and a script to convert it. The example of each column is copied into `schema.yaml` (`example:`), from where it reaches `schema.md` and row 2 of the collection sheet; a test checks that each is a valid value.
- [x] One description per column, in `schema.yaml`, replacing the separate descriptions in `schema.md`, its "What each column covers" table and the collection sheet. The tables in `schema.md` that list the tables and columns are written from it by an Action (`.github/workflows/schema-md.yml`), and the app builds the collection sheet from it.
- [x] Add a section on the files themselves to `schema.md`: one CSV per table, named after the table, UTF-8, comma-separated, one header row with the column names. See [Files](../schema/schema.md#files).
- [x] Add ID rules: only letters, digits and `_`, and unique ignoring case, both checked by the validator. The schema doc suggests a form for each ID, with experiment-level IDs (UNID, PHID, IID, MMID, CLID) starting with their EXPID, so IDs never clash when contributions are merged. See [Identifiers](../schema/schema.md#identifiers).
- [x] Draw the diagram from `schema.yaml` on every deploy, instead of keeping a dbdiagram.io copy: `schema/diagram.py` and `schema/diagram.html`, published at <https://fababase.github.io/phenotype-database-format/diagram/>. The README and `schema.md` link to it. Tick once the first run has published it.
- [x] Write `docs/datasets.md`, the list of every known dataset in the format, by DOI, instead of keeping shared reference tables in `reference/`.
- [ ] Write `conversion/AI_INSTRUCTIONS.md`, telling the AI to:
  - **Inspect before coding:** every sheet, hidden rows and columns, merged cells, multi-row headers, cell colours, comments, notes below tables, decimal commas and home-made "NA" markers. Use openpyxl, since pandas cannot see colours or merged cells.
  - **Ask, don't guess:** what a unit is, what colours and formatting mean, the unit and method of each trait, what categorical codes mean, which rows to leave out. Never invent metadata; leave it empty and list it in NOTES.md.
  - **Reuse IDs:** map germplasm, seed lots, traits, climate variables and features to the tables of the datasets in `docs/datasets.md`, restricted ones too if the person has access, and list any new IDs in NOTES.md.
  - **Deliver a script, not just tables:** the AI writes `convert.py`, a script that turns the messy raw Excel file into the correct CSV files, one per table. The script is saved with the contribution, so the conversion can be rerun and checked later. Raw files are read-only, every decision is in the code, and nothing is edited by hand afterwards.
  - **Report what it sees** while it writes and runs the script, so the contributor can say "yes, that's right" or spot at once that something is badly wrong. For example: which traits were scored and how many scores each has, how many units, experiments and germplasm there are, the date range, the value range of each trait, and which rows were left out and why.
  - **Run the validator** and fix the script until the tables pass.
  - **Write NOTES.md:** the questions asked and the answers, the assumptions made, and row counts in the raw data vs. in the tables.
  - Work from a trimmed copy of the raw data (headers and some rows) where possible, so the full data does not have to be uploaded to an AI service.
- [ ] Write `docs/submit-data.md` for contributors: the steps in [How data flows](#how-data-flows), what to hand over, best practices etc.
- [ ] Pilot the kit on 2–3 real messy datasets, and improve the instructions based on what the AI gets wrong.

## Phase 3: Publish on Zenodo

- [ ] Write `zenodo/README_TEMPLATE.md` for the record: what the database is, the contributions it contains and who made them, experiments and locations, the schema version, the list of files, how the tables link, licence, how to cite, contact.
- [ ] Write a merge script that combines the tables of all contributions into one set of tables, and validate the merged set.
- [ ] Decide what goes into each version of the record: the merged tables, the README, and `schema.md`, `schema.yaml` and the diagram for the schema version used, so the record makes sense without GitHub.
- [ ] Before publishing, check for personal names (ScoredBy, Manager) and confidential breeding lines. Zenodo records are effectively permanent.
- [ ] Do a first upload on [sandbox.zenodo.org](https://sandbox.zenodo.org), then publish the real record.
- [ ] Add `CITATION.cff`.
- [ ] Write `docs/release.md`: how to release a new schema version (update `schema.yaml`, the hand-written parts of `schema.md` and `CHANGELOG.md`, run the tests, tag a release once the Action has written the tables in `schema.md`) and how to publish a new version of the Zenodo record.

## Phase 4: Validator plots

The app's right-hand panel is reserved for plots that help spot data that passes validation but is wrong. Which plots to show is still to be decided. Ideas:

- the range or distribution of each trait
- the number of scores per unit
- a trait plotted over Row × Column of the field, where a shifted row stands out

## Phase 5: A central AI agent

To be explored later: instead of each contributor setting up an AI themselves, a central AI agent that already has the AI kit loaded, so contributors only bring their raw data. This phase is about finding out what form that could take.

## Open questions

- **Documentation by role.** Split the docs by who reads them, with the README as the shared front door and `schema.md` shared by all:
  - *Contributors*, or their AI: get their data into the format and through the validator.
  - *Data users*: read and join the published tables.
  - *Data reviewers and managers*: review contributions, approve new reference IDs, publish on Zenodo, and keep at least two people with access to GitHub and Zenodo.
  - *Developers*: change the schema, validator, app and Actions; how the pieces fit, and which files are generated.

  Each guide is written once, concisely, for people. AIs read the same files; an `AGENTS.md` only points them to the right guide for their task. The Decisions table above could move to its own file then, so it outlives this roadmap.
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
- **ParentSLID loops.** Check that ParentSLID chains never loop back on themselves (A → A, or A → B → A or any variation thereof).
- **Coordinates in range.** `91;181` passes. Decide whether to check latitude −90 to 90 and longitude −180 to 180.
- **Infinite numbers.** `1e999` passes as a number, though it is read as infinity.
- **Digits other than 0–9.** Digits such as `１２` (full-width) and `٣` (Arabic-Indic) pass as numbers.
- **Hidden sheets.** A hidden sheet in the collection sheet, such as one holding dropdown lists, is an error. Decide whether to skip hidden sheets.
- **More help in the collection sheet.** Now that it is built from `schema.yaml`, it could also get dropdowns (Type in Features; IDs from the sheet a column links to), ID and text columns formatted as text so Excel does not turn `1-2` into a date, and required columns highlighted.
- **Version of a filled-in sheet.** The *READ ME 1st* sheet says which schema version a blank sheet was built for. The validator could read it and say when a sheet is from an older version.
- **Case in column names.** `species` gets "Did you mean 'Species'?", but `gpid` gets no suggestion for `GPID`. Decide whether to ignore case when suggesting, or when matching column names.
- **Blank lines in CSV files.** They are dropped. Decide whether they should be an error.
