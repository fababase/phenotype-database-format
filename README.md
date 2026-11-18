# Phenotheca

Phenotheca is a collection of phenotype data from plant experiments. This repository holds what builds it: the format the data is kept in, a validator for that format, the guides and the AI instructions that bring data into it, and the scripts that publish the datasets on Zenodo.

The format is 11 linked tables. They hold each score together with everything that someone who was not there needs to use it, years later: the plant material, the experiment and its units, what was done to them, and the climate they grew in.

The data itself is not kept here: [Where the data is](docs/datasets.md) lists the datasets.

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

1. **Convert.** On the contributor's own computer, an AI reads their files, asks about everything the files do not say, and writes a script that turns them into the tables. The contributor saves each answer as a file, and has the last word. Without an AI, the contributor writes the script, or fills in a workbook by hand.
2. **Review.** A fresh AI session, or a colleague, checks the tables against the raw files, and gives them a FAIR score: how well they are described for others to find and use.
3. **Merge.** The contributor hands over the tables, and a file that says who to credit. The data manager's AI finds where the contributions overlap, such as one trait under two IDs, and proposes what to change. The data manager decides every change.
4. **Publish.** Each merge becomes a new version of a dataset on Zenodo, with a DOI: the public dataset, or the restricted one of a project whose data is not public yet. Everyone who made the data is named as a creator, so that they are cited with it.

The raw files, the script and the notes stay with the contributor. Nothing in the tables is edited by hand, so every change can be seen and repeated. A published version is never changed, only followed by a new one. And the same plant material, seed lot or trait gets the same ID in every dataset.

## What is in this repository

- [schema/](schema/): the format. [schema.md](schema/schema.md) describes it for people. `schema.yaml` holds it for programs: the validator reads it, and the collection sheet and the diagram are made from it.
- [app/](app/): the validator, the app around it, and the collection sheet.
- [docs/](docs/): a guide for each role, the list of datasets, and the [roadmap](docs/ROADMAP.md).
- [conversion/](conversion/) and [merging/](merging/): what the AI follows when it converts a contribution, and when it merges contributions.
- [publishing/](publishing/): the scripts that build a version of a dataset and upload it to Zenodo.
- [tests/](tests/): the tests. [tests/valid/](tests/valid/) holds a made-up dataset, the quickest way to see what the tables look like.
- [CHANGELOG.md](CHANGELOG.md): what changed in each version of the format.

## Citing

- **The data:** cite the version of the dataset you used, by its DOI. Its README on Zenodo says how.
- **The format, the tools or the guides:** cite this repository, as [CITATION.cff](CITATION.cff) says. GitHub shows it under *Cite this repository*.

## Questions

Questions about the format, the validator or the guides, and problems with them, go in an [issue](https://github.com/phenotheca/phenotheca/issues) on GitHub. Issues are public, so never put data in one. Questions about a dataset go to its contact in [Where the data is](docs/datasets.md).

## Licences

- **Code** (the scripts in `app/`, `schema/` and `publishing/`, and the tests): GPL-3.0, see [LICENSE](LICENSE).
- **Content** (the schema documentation and diagram, the collection sheet and the published data): CC-BY-4.0, see [LICENSE-CONTENT](LICENSE-CONTENT).
