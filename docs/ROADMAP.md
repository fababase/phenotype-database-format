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
| Validator errors | **Stops at the first error.** Later errors are often knock-on effects of the first one, so they are not reported. Each message names the table, row, column and value, and hint where possible. **Warnings**, one per column, point out what is allowed but often a mistake, such as a date before 1950; the tables still pass. |
| Format | All written in `schema/schema.yaml`. |
| Schema diagram | **Drawn from `schema.yaml`** by `schema/diagram.py` each time the app is published: an interactive page next to the app, where tables can be dragged around, clicking a table highlights its links, and pointing at a column, a table's name or a link says what it is (a column's description, type hint and example, as in row 2 of the collection sheet), plus a PNG and an SVG picture, which keeps that text as tooltips. See [deploy-app.md](deploy-app.md#the-schema-diagram). |
| App hosting | **Shinylive on GitHub Pages**: the app runs in the visitor's browser, so data never leaves their computer, and it redeploys automatically on push. `schema.yaml` is bundled into the app when it is built. See [deploy-app.md](deploy-app.md). |
| Packages | See requirements.txt. |
| Conversion | Done by **contributors**, following the guides in this repo, in a folder laid out as in [How data flows](#how-data-flows), with an AI, with a `conversion.py` of their own or manually in the collectino sheet. A fresh AI session, a colleague and / or the validation app reviews each finished run. A central AI agent may follow later ([Phase 5](#phase-5-a-central-ai-agent)). |
| Guides | One per role, written once for people, and read by AIs too. |
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
  AI_INSTRUCTIONS.md  Instructions for the AI in how to convert a contributors data into the format of the database schema
zenodo/
  README_TEMPLATE.md  README for the Zenodo record
docs/
  ROADMAP.md          this file
  datasets.md         every known dataset in the format, by DOI, to reuse IDs from
  deploy-app.md       how the app is deployed and how to refresh it
  submit-data.md      for contributors, with an AI or without: from installing and setting up the folder to the review and handing over
  review-data.md      for reviewers: what a finished run must meet, and its FAIR score
  release.md          how to release a new schema version and a new Zenodo version
tests/                one valid dataset plus deliberately broken ones; run on every push
.github/workflows/    run tests on every push; deploy the app when they pass; write the tables in schema.md
```

## How data flows

1. A contributor sets up a folder for their contribution, as below: their files in `raw_data/`, and a copy of this repository next to it. They start an AI in the folder with one line, the same in every session: "Read `phenotype-database-format/conversion/AI_INSTRUCTIONS.md` and follow it."
2. The AI asks whether it may see all the data, and if not, how much. It reads everything it may see, and asks about anything missing, odd or ambiguous as each question comes up. The contributor answers by adding files to `raw_data/`, getting the information from others where needed.
3. The AI writes `conversion.py`, which turns `raw_data/` into one CSV per table, working from `schema.yaml` and `schema.md`. The final data should pass the validator. Each time it runs, `conversion.py` writes `summary.md`: which traits were scored and how many scores each has, how many units, experiments and germplasm there are, the date range, the range of each trait, etc., and which rows, if any, were left out and why. The contributor checks it, so that mistakes are caught early.
4. When the run is finished, the contributor starts a fresh AI session, which reviews it against `docs/review-data.md` and writes `review.md`, with a FAIR score. If the review finds problems, the AI fixes them, and a fresh session reviews the run again.
5. The contributor hands over the properly formatted data, in a way still to be decided, but should keep the raw data and the run for future reference. The formatted data are kept privately, by a data manager.
6. The tables of all contributions are merged and published as a new version of the Zenodo record, either as a restricted project-level record, or a full public record.

Each contribution is worked on in a folder like this, which the contributor keeps for reproducibility:

```
<contribution>/                  one folder per contribution, the workfolder of the AI agent should be set here
  raw_data/                      everything from the contributor: data, documents, metadata, etc., in any format
  phenotype-database-format/     a copy of this repository at a fixed version; never edited
  runs/
    2026-10-22/                  one run per handover
      conversion.py              the script: raw_data/ → tables/
      conversion-notes.md        kept by the AI, from the template in conversion/AI_INSTRUCTIONS.md
      summary.md                 written by conversion.py each time it runs
      review.md                  written only by the review session: findings and FAIR score
      tables/                    Germplasm.csv … Features.csv, written only by conversion.py
      scratch/                   the AI's throwaway scripts; deleted whenever it stops
```

- `raw_data/` is add-only: nothing in it is ever changed or deleted by the AI. Its files are read-only.
- Every bit of information about the experiment, data, metadata, notation, all of it is a file in `raw_data/` - no data is found in `conversion-notes.md` or similar. An AI agent can draft a file in the chat from an answer from the contributor, but only the contributor saves it (after reviewing contents, of course).
- `conversion.py` names each raw file it reads, with its checksum, and stops if one has changed. It lists Python 3.12 and the exact version of each package it needs, so that [uv](https://docs.astral.sh/uv/) can run it in an environment of its own, without touching the contributor's Python. uv runs the validator the same way, with the versions in `app/requirements.txt`.
- A run ends either *stopped*, waiting for information the contributor has to get, or *finished*. A stopped run is carried on in the same folder. A new run is started only for a new handover, such as corrections, more data after the last one, or a new schema version.

Only the tables go to Zenodo.

## Phase 2: Schema doc, example and AI kit

- [x] Fill in the TODOs in `schema/schema.md` (examples, worked example) from the valid test dataset, `tests/valid/`, instead of building a separate worked example with a fake messy Excel file and a script to convert it. The example of each column is copied into `schema.yaml` (`example:`), from where it reaches `schema.md` and row 2 of the collection sheet; a test checks that each is a valid value.
- [x] One description per column, in `schema.yaml`, replacing the separate descriptions in `schema.md`, its "What each column covers" table and the collection sheet. The tables in `schema.md` that list the tables and columns are written from it by an Action (`.github/workflows/schema-md.yml`), and the app builds the collection sheet from it.
- [x] Add a section on the files themselves to `schema.md`: one CSV per table, named after the table, UTF-8, comma-separated, one header row with the column names. See [Files](../schema/schema.md#files).
- [x] Add ID rules: only letters, digits and `_`, and unique ignoring case, both checked by the validator. The schema doc suggests a form for each ID, with experiment-level IDs (UNID, PHID, IID, MMID, CLID) starting with their EXPID, so IDs never clash when contributions are merged. See [Identifiers](../schema/schema.md#identifiers).
- [x] Draw the diagram from `schema.yaml` on every deploy, instead of keeping a dbdiagram.io copy: `schema/diagram.py` and `schema/diagram.html`, published at <https://fababase.github.io/phenotype-database-format/diagram/>. The README and `schema.md` link to it. Tick once the first run has published it.
- [x] Write `docs/datasets.md`, the list of every known dataset in the format, by DOI, instead of keeping shared reference tables in `reference/`.
- [x] Write `docs/submit-data.md` for contributors, which their AI reads too: the folder and its rules from [How data flows](#how-data-flows), how to set it up (a copy of this repository, uv, read-only files), the lines that start the AI and the review, that what the AI reads goes to the AI service they use, the details the AI asks for about them (name, ORCID, affiliation, contact and funding, so that they are credited if the data is published), and how to hand over, once that is decided.
- [x] Write `conversion/AI_INSTRUCTIONS.md`: how the AI works and what it never does. Only this is written for the AI alone; the folder and its rules are in `docs/submit-data.md`, and what a finished run must meet is in `docs/review-data.md`, both of which the AI reads first. It tells the AI to:
  - **Ask first** whether it may see all the data, and if not, how much, and keep to the answer.
  - **Read everything before asking:** every file, sheet and column, and the documents. Don't ask what they already answer.
  - **Look at every value**, not just the first rows: hidden rows and columns, merged cells, multi-row headers, cell colours, comments, notes below tables, decimal commas, home-made "NA" markers, the distinct values of columns that have few, and the range of each number column. Use openpyxl, since pandas cannot see colours or merged cells.
  - **Check each source against the others:** the data against the field plan and the protocol, sheet against sheet, and dates against the season.
  - **Treat anything unexpected or ambiguous as a question:** a gap in the plot numbers, a value far out of line, a format that changes halfway down a column, 39 plots where the design has 40, or a date that could be read either way round.
  - **Ask as soon as a question comes up**, a few at a time and in plain words, and carry on only with what does not depend on the answer. Use an answer only once it is in a file in `raw_data/`.
  - **Leave the last word to the contributor.** When the AI still doubts something, it records the doubt rather than overruling them.
  - **Never make up a value**, even to make the tables pass. An optional cell stays empty; a required one says plainly what is not known.
  - **Reuse IDs** from the datasets in `docs/datasets.md`, restricted ones too if the contributor has access.
  - **Run the validator** and fix `conversion.py` until the tables pass.
  - **Keep the notes as it goes**, so that the next session can carry on from them.
  - **Stop and ask when something blocks it**, never work around it. It never writes in `raw_data/`, changes permissions or file attributes anywhere (chmod, attrib, icacls and the like), edits the copy of this repository, installs anything beyond what `conversion.py` lists, sends data anywhere (uploads, pushes, issues, web forms), or changes or deletes an earlier run.
- [x] Write the template for each run's `conversion-notes.md`, in `conversion/AI_INSTRUCTIONS.md`. Facts are in `raw_data/`, decisions in `conversion.py` and counts in `summary.md`, so the notes hold only what needs judgement, and each item fits one section only. Every item is dated.
  - **Header:** the run's date, when the notes were last updated, the status (stopped, and what it is waiting for; or finished), the version of this repository, what the AI may see, which known datasets were searched for IDs to reuse, and when the contributor last checked `summary.md`.
  - **Open questions:** asked, and waiting for a file in `raw_data/`. An answer removes the question; "don't know" moves it to Missing. Empty once the run is finished.
  - **Changed or left out:** where the tables differ from the raw files: corrected, recoded, combined, removed or not converted. Each item rests on a file in `raw_data/` or on the raw data itself, and says which.
  - **Assumptions:** what the AI decided without such a basis, and why it could not be asked or answered. These should be rare, since the AI asks rather than guesses.
  - **Missing:** what the tables lack that exists, or that people reusing the data would want to know, including required cells that say it is not known, and when each was asked.
  - **Doubtful:** in the tables as the raw files or the contributor give it, but possibly wrong, and why.
  - **Schema issues:** what the format could not hold, pointing to the item that says what was done about it.
- [x] Write `docs/review-data.md` for reviewers. Until a person takes on the role, a fresh AI session reviews each finished run with it, relying only on the files, and writes only `review.md`:
  - **Checks:** `conversion.py` reruns to the same tables, the raw files are unchanged, and the validator passes. A sample of values can be traced back to their cells in the raw files, and every fact in the tables is in `raw_data/`. New IDs in the shared reference tables were checked against the known datasets. There are no open questions and no `scratch/`.
  - **FAIR score**, from 1 to 5: how well the dataset meets the [FAIR principles](https://www.go-fair.org/fair-principles/). Findable and Accessible come from publishing on Zenodo, so in practice it scores how richly the data are described, and whether they reuse shared IDs. It counts what exists, or what people reusing the data would want to know, but is not described. Tables and columns that do not apply, or hardly apply, to the experiment do not count against it. A required value that is not known keeps the score at 2 or below. Each point below 5 names the items in Missing, Assumptions or Doubtful that cost it, so the contributor can see what would raise it.
    - 5: everything people reusing the data would want to know is described, with only minor faults.
    - 4: small but noticeable gaps, which matter only for some uses.
    - 3: significant gaps in data or metadata people would want to know are not described.
    - 2: something needed to read part of the data is not known, such as a required value.
    - 1: most of the data cannot be interpreted.
- [ ] Pilot the kit on 2–3 real messy datasets. Compare the FAIR scores with our own judgement, and improve the guides, the notes template and the score levels based on what goes wrong.

## Phase 3: Publish on Zenodo

- [ ] Write `zenodo/README_TEMPLATE.md` for the record: what the database is, the contributions it contains and who made them, experiments and locations, the schema version, the list of files, how the tables link, licence, how to cite, contact.
- [ ] Write a merge script that combines the tables of all contributions into one set of tables, and validate the merged set.
- [ ] Decide what goes into each version of the record: the merged tables, the README, and `schema.md`, `schema.yaml` and the diagram for the schema version used, so the record makes sense without GitHub.
- [ ] Do a first upload on [sandbox.zenodo.org](https://sandbox.zenodo.org), then publish the real record.
- [ ] Add `CITATION.cff`.
- [ ] Write `docs/release.md`: how to release a new schema version (update `schema.yaml`, the hand-written parts of `schema.md` and `CHANGELOG.md`, run the tests, tag a release once the Action has written the tables in `schema.md`) and how to publish a new version of the Zenodo record.

## Phase 4: Validator plots

The app's right-hand panel is reserved for plots that help spot data that passes validation but is wrong. Which plots to show is still to be decided. Ideas:

- the range or distribution of each trait
- the number of scores per unit
- a trait plotted over Row × Column of the field, where a shifted row stands out
- the Phenotype, Management and Climate dates against each experiment's StartDate–EndDate

## Phase 5: A central AI agent

To be explored later: instead of each contributor setting up an AI themselves, a central AI agent that already has the AI kit loaded, so contributors only bring their raw data. This phase is about finding out what form that could take.

## Open questions

- **Documentation by role.** Split the docs by who reads them, with the README as the shared front door and `schema.md` shared by all:
  - *Contributors*, or their AI: get their data into the format and through the validator.
  - *Data users*: read and join the published tables.
  - *Data reviewers and managers*: review contributions, approve new reference IDs, publish on Zenodo, and keep at least two people with access to GitHub and Zenodo.
  - *Developers*: change the schema, validator, app and Actions; how the pieces fit, and which files are generated.

- The Decisions table above could move to its own file then, so it outlives this roadmap.
