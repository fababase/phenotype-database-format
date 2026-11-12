# Deploying the app

The validation app is at **<https://fababase.github.io/phenotype-database-format/>**.

GitHub Pages only hands out the app's files. The app itself runs in each visitor's browser, with [Shinylive](https://shiny.posit.co/py/docs/shinylive.html), so the files they check never leave their computer. The first visit takes a while, as the browser downloads Python and the packages; later visits use its cached copy.

## Refreshing the app

Commit and push to `main` in GitHub Desktop. The *Deploy app* Action ([.github/workflows/deploy-app.yml](../.github/workflows/deploy-app.yml)) then:

1. runs the tests;
2. builds the app from `app/` and `schema/schema.yaml`;
3. draws the [schema diagram](#the-schema-diagram), with every version of `schema/schema.yaml` in the history;
4. opens the built app in a browser and checks it ([tests/check_browser_app.py](../tests/check_browser_app.py));
5. publishes both.

This takes a few minutes. If any step fails, nothing is published and the previous app stays up.

**Did it work?** On the repository's GitHub page, open the **Actions** tab. Each push has a *Deploy app* run with a green tick (published) or a red cross (failed). To see why a run failed, click it, then the job with the red cross, then the step with the red cross. GitHub also emails whoever pushed when a run fails.

To publish again without changing anything, go to **Actions → Deploy app → Run workflow**.

## What is checked before publishing

- All tests pass.
- The schema diagram draws every version of the schema without errors, with all its tables and links. The menu and the address switch between versions, and pointing at a column shows its description.
- The packages bundled with the app are the versions in `app/requirements.txt`.
- The app starts in a browser and shows no notices, so it runs the package versions in `app/requirements.txt`.
- The app hands out a blank collection sheet with the same contents as one built on the command line.
- The app gives the same messages as the command line for the valid test dataset and for that blank collection sheet, and the tables it hands back are the same.

## Package versions

The app runs on the browser's own Python, which has fixed versions of pandas, numpy, PyYAML and Shiny. They are set by the shinylive version in `deploy-app.yml`. `app/requirements.txt` pins the same versions, so the tests, the command line and the browser app all run the same ones. openpyxl is not part of the browser's Python; the app installs the version pinned in `app/requirements.txt` each time it starts.

The app and the command line both show a notice when they run another version than `app/requirements.txt`, for example:

```
Notice: This validator is tested with pandas 2.2.3, but pandas 3.0.6 is installed, so results may differ.
```

On your own computer, `pip install -r app/requirements.txt` installs the tested versions.

### Upgrading shinylive

Only upgrade when there is a reason to, such as a fix in Shiny that the app needs.

1. Change `shinylive==…` in `deploy-app.yml` to the new version, which is listed on [PyPI](https://pypi.org/project/shinylive/).
2. Push. If the new version brings other package versions, the browser check fails and says which versions to put in `app/requirements.txt`.
3. Change them, install them on your computer (`pip install -r app/requirements.txt`), check that the tests pass, and push again.

## The schema

`schema.yaml` stays in `schema/`. The Action copies it next to `validation.py` in a folder outside the repository and builds the app from there, so the repository never holds a second copy; a test checks this. The schema is bundled into the app, which reads it from there. The site has no page or link to download it.

## The schema diagram

The diagram of how the tables link is at **<https://fababase.github.io/phenotype-database-format/diagram/>**. [schema/diagram.py](../schema/diagram.py) draws it each time the app is published, with every version of the schema:

- It opens at the latest version. The menu at the top switches to an earlier one.
- An address can name a version after `#`, as in `diagram/#1.0.0`, to open the diagram at that version. Link this way wherever the version matters: the *READ ME 1st* sheet of the collection sheet does, and so will the README of the Zenodo record.
- Pictures of each version are at `diagram/<version>/diagram.png` and `diagram/<version>/diagram.svg`, and those of the latest also at `diagram/diagram.png` and `diagram/diagram.svg`.

### Where the versions come from

No copy of an earlier version is kept: the versions come from the git history. The latest version is `schema/schema.yaml` as it is. Each earlier version is `schema.yaml` as it was in the last commit that had that version, so the changes pushed under a version, such as a reworded description, show in the diagram of that version. Every version is read and drawn with the code of today.

So:

- **A version stays in the diagram for good once a commit with it is pushed.** Change the version in `schema.yaml` only when the format changes, and commit it only when the new version is final.
- **Never rewrite the history of `main`**, for example by force-pushing, or by squashing commits that are pushed: the earlier versions are in it.
- **The code has to read every earlier version.** A test reads each version in the history with today's `load_schema`. If a change to the code, or to how `schema.yaml` is laid out, makes an earlier version unreadable, that test fails, and nothing is published. Then make the code read the earlier version too; never leave it out.

The diagram needs the whole history, so the Actions fetch all of it (`fetch-depth: 0` in the workflows), and `diagram.py` will not run in a clone that holds only part of it.

To see a change before pushing it, draw the diagram on your own computer, in a clone of the repository:

```
pip install playwright==1.63.0
playwright install chromium
python schema/diagram.py site/diagram
```

and open `site/diagram/index.html`. The `site/` folder is not committed.

## The collection sheet

The app's *Download a blank collection sheet* button builds the sheet from `schema.yaml` when it is clicked, with [app/collection_sheet.py](../app/collection_sheet.py), so it always matches the schema the app checks against. Nothing else needs publishing. To build one on your own computer:

```
python app/collection_sheet.py collection-sheet.xlsx
```

## Setup, done once

In the repository's **Settings → Pages**, under *Build and deployment*, *Source* is set to **GitHub Actions**. Only an admin of the repository can change this.

The address contains the repository's name. If the repository is renamed, the address changes and the old one stops working, so update the links in `README.md`, this file, the *READ ME 1st* sheet (`SITE` and `SCHEMA_DOC` in `app/collection_sheet.py`), the diagram (`REPOSITORY` in `schema/diagram.html`) and anywhere else the address was shared.
