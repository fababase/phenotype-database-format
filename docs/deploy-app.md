# Deploying the app

The validation app is at **<https://fababase.github.io/phenotype-database-format/>**.

GitHub Pages only hands out the app's files. The app itself runs in each visitor's browser, with [Shinylive](https://shiny.posit.co/py/docs/shinylive.html), so the files they check never leave their computer. The first visit takes a while, as the browser downloads Python and the packages; later visits use its cached copy.

## Refreshing the app

Commit and push to `main` in GitHub Desktop. The *Deploy app* Action ([.github/workflows/deploy-app.yml](../.github/workflows/deploy-app.yml)) then:

1. runs the tests;
2. builds the app from `app/` and `schema/schema.yaml`;
3. draws the [schema diagram](#the-schema-diagram) from `schema/schema.yaml`;
4. opens the built app in a browser and checks it ([tests/check_browser_app.py](../tests/check_browser_app.py));
5. publishes both.

This takes a few minutes. If any step fails, nothing is published and the previous app stays up.

**Did it work?** On the repository's GitHub page, open the **Actions** tab. Each push has a *Deploy app* run with a green tick (published) or a red cross (failed). To see why a run failed, click it, then the job with the red cross, then the step with the red cross. GitHub also emails whoever pushed when a run fails.

To publish again without changing anything, go to **Actions → Deploy app → Run workflow**.

## What is checked before publishing

- All tests pass.
- The schema diagram is drawn without errors.
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

The diagram of how the tables link is at **<https://fababase.github.io/phenotype-database-format/diagram/>**, with pictures of it at `diagram/diagram.png` and `diagram/diagram.svg`. [schema/diagram.py](../schema/diagram.py) draws it from `schema.yaml` each time the app is published.

To see a change before pushing it, draw the diagram on your own computer:

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

The address contains the repository's name. If the repository is renamed, the address changes and the old one stops working, so update the links in `README.md`, this file, the *READ ME 1st* sheet (`SITE` and `SCHEMA_DOC` in `app/collection_sheet.py`) and anywhere else the address was shared.
