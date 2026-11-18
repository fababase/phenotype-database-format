# Roadmap

The decisions behind this repository, the work still to do, and the questions still open. When an item is done, remove it, and add any decision it made to the table.

## Decisions

| Topic | Decision |
|---|---|
| Repository | One **public** GitHub repository for the format, the validator and its app, the guides, the AI instructions and the publishing scripts. They change together, so they are versioned together. |
| Source of truth | **`schema/schema.yaml`**: the tables, columns, types and links, and one description per column. The validator reads it, and the collection sheet, the diagram and the tables in `schema.md` that list the tables and columns are made from it. The rest of `schema.md` is written by hand. |
| One schema.yaml | There is only ever **one** `schema.yaml`, in `schema/`. It is never copied anywhere in the repository, and a test fails if a second one appears. |
| Versions of the format | **major.minor**: major when data that passed may fail, or mean something else; minor when all that passed still passes. Fixes to the validator and rewording are not new versions, as they would only draw the same diagram again. 1.0 was first written 1.0.0, and everything reads the two as one. Each version is listed in [CHANGELOG.md](../CHANGELOG.md). |
| Validator | Checks one CSV file per table, or a filled-in collection sheet, and `contributors.yaml`. **Stops at the first error**, as later ones are often knock-on effects of it. Each message names the table, row, column and value. Warnings point out what is allowed but often a mistake. |
| App | **Shinylive on GitHub Pages**: it runs in the visitor's browser, so their data never leaves their computer. It hands out the blank collection sheet. The schema diagram, with every version of the schema in the git history, is published with it. See [maintainers.md](maintainers.md#the-app). |
| Conversion | Done by **contributors**, with an AI, with a `conversion.py` of their own, or in the collection sheet, as in [submit-data.md](submit-data.md). A fresh AI session or a colleague reviews each finished run, as in [review-data.md](review-data.md). |
| Credit | **`contributors.yaml`**, handed over with the tables, as in [Who to credit](submit-data.md#who-to-credit), and checked by the validator. Everyone in it is a creator of the dataset on Zenodo, in alphabetical order of family name. Whoever looks after the dataset is a contributor, as data curator. |
| Merging | An **AI merges** the contributions for the data manager, who decides every change, as in [merging/AI_INSTRUCTIONS.md](../merging/AI_INSTRUCTIONS.md). |
| Data | **On Zenodo**: one public dataset, and a restricted dataset for each project whose data are not public yet. A restricted dataset's page and DOI are public, and its files are only for those given access. Each merge becomes a new version. |
| Datasets on disk | **One folder per dataset**: a copy of the repository, `zenodo.yaml`, the contributions in `Sources/`, and one folder per version in `Versions/`, which keeps the sources as merged, the merge, the tables and the README, as in [publish-data.md](publish-data.md). Nothing of a version is changed or deleted. |
| What is published | **Only the merged tables, `contributors.yaml` and the README.** The README holds all that people using the data need, so `schema.md` and `schema.yaml` are not published. Raw files, scripts and notes are kept privately. |
| Publishing | `publishing/build.py` builds the README and the metadata from a merge, and `publishing/publish.py` uploads them to a draft on Zenodo. The data manager presses Publish, as in [publish-data.md](publish-data.md). |
| Existing data | The IDs to reuse are in the datasets themselves. [datasets.md](datasets.md) lists every known dataset by DOI. |
| Guides | One per role, for the contributor, the reviewer, the data manager and the maintainers, written for people, and read by AIs too. Only the AI instructions are written for the AI alone. |
| Licences | Code: GPL-3.0. The schema documentation, the collection sheet and the published data: CC-BY-4.0. |

## To do

- [ ] Publish the first version of the public dataset, as in [publish-data.md](publish-data.md): on the sandbox first.
- [ ] Decide how contributors hand over their tables, and say so in step 10 of [submit-data.md](submit-data.md#10-hand-over).

### Validator plots

The app's right-hand panel is kept for plots that show data that passes the validator but is wrong. Which plots is still to be decided. Ideas:

- the range or distribution of each trait
- the number of scores per unit
- a trait plotted over Row × Column of the field, where a shifted row stands out
- the Phenotype, Management and Climate dates against each experiment's StartDate–EndDate

### A central AI agent

To be explored later: instead of each contributor setting up an AI, a central AI agent with the AI instructions already loaded, so that contributors only bring their raw data.

## Open questions

None at the moment.
