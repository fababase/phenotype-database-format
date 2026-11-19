# Phenotheca

Phenotheca is a collection of phenotype data from plant experiments. This repository holds the format the data is kept in, a validator for that format, the guides and the AI instructions that bring data into it, and the scripts that publish the datasets on Zenodo.

The format is 11 linked tables. They hold each score together with the plant material, the experiment and its units, what was done to them, and the climate they grew in, so that someone who was not there can use it, years later.

The data itself is not kept here. [Where the data is](docs/datasets.md) lists the datasets.

## Where to start

| You want to | Go to |
|---|---|
| Contribute your data | [Submitting data](docs/submit-data.md) |
| Use the data | [Where the data is](docs/datasets.md). Each dataset comes with a README that says how to read it. |
| Understand the format | [The Phenotheca format](schema/schema.md), and the [diagram](https://phenotheca.github.io/phenotheca/diagram/) of how its tables link |
| Check tables against the format | [The app](https://phenotheca.github.io/phenotheca/). It runs in your browser, so the files never leave your computer. |
| Review a contribution | [Reviewing a contribution](docs/review-data.md) |
| Publish a version of a dataset | [Publishing data](docs/publish-data.md) |
| Work on this repository | [For maintainers](docs/maintainers.md) |

## How data gets into Phenotheca

![On the contributor's computer, the data is converted into the format and curated. The contributor answers and has the last word, an AI asks and writes the script, and a fresh AI or a colleague reviews, while the raw files stay there. The tables and the credit go to the data manager's folder, where the contributions are merged and their overlaps handled. The data manager decides every change, and an AI proposes the merge. The tables, the credit and the README go to Zenodo, into the public dataset or a project's restricted one, which Zenodo shares and stores for the long term, and where data users download and cite them. The IDs already published are reused, so that one thing has one ID across datasets.](docs/images/overview.svg)

1. **Convert.** On the contributor's own computer, an AI reads their files, asks about everything the files do not say, and writes a script that turns them into the tables. The contributor saves each answer as a file, and has the last word. Without an AI, the contributor writes the script, or fills in a workbook by hand.
2. **Review.** A fresh AI session, or a colleague, checks the tables against the raw files, and gives them a FAIR score, for how well they are described for others to find and use.
3. **Merge.** The contributor hands over the tables, and a file that says who to credit. The data manager's AI finds where the contributions overlap, such as one trait under two IDs, and proposes what to change. The data manager decides every change.
4. **Publish.** Each merge becomes a new version, with a DOI, of the public dataset on Zenodo, or of the restricted one of a project whose data is not public yet. Everyone who made the data is named as a creator, so that they are cited with it.

The raw files, the script and the notes stay with the contributor. Nothing in the tables is edited by hand, so every change can be seen and repeated. A published version is never changed, only followed by a new one. And the same plant material, seed lot or trait gets the same ID in every dataset.

## What is in this repository

- [schema/](schema/) holds the format. [schema.md](schema/schema.md) describes it for people, and `schema.yaml` holds it for programs. The validator reads it, and the collection sheet and the diagram are made from it.
- [app/](app/) holds the validator, the app around it, and the collection sheet.
- [docs/](docs/) holds a guide for each role, the list of datasets, the [roadmap](docs/ROADMAP.md), and the pictures, with the script that draws them.
- [conversion/](conversion/) and [merging/](merging/) hold what the AI follows when it converts a contribution, and when it merges contributions.
- [publishing/](publishing/) holds the scripts that build a version of a dataset and upload it to Zenodo.
- [tests/](tests/) holds the tests, and in [tests/valid/](tests/valid/) a made-up dataset, the quickest way to see what the tables look like.
- [CHANGELOG.md](CHANGELOG.md) says what changed in each version of the format.

## Citing

- **The data.** Cite the version of the dataset you used, by its DOI. Its README on Zenodo says how.
- **The format, the tools or the guides.** Cite this repository, as [CITATION.cff](CITATION.cff) says. GitHub shows it under *Cite this repository*.

## Questions

Questions about the format, the validator or the guides, and problems with them, go in an [issue](https://github.com/phenotheca/phenotheca/issues) on GitHub. Issues are public, so never put data in one. Questions about a dataset go to its contact in [Where the data is](docs/datasets.md).

## Licences

- **Code.** The scripts in `app/`, `schema/`, `publishing/` and `docs/images/`, and the tests, are under GPL-3.0, as in [LICENSE](LICENSE).
- **Content.** The schema documentation and diagram, the pictures, the collection sheet and the public dataset are under CC-BY-4.0, as in [LICENSE-CONTENT](LICENSE-CONTENT). The README of a restricted dataset says what its data may be used for.
