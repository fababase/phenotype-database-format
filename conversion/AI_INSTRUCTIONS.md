# Instructions for the AI

This file is for the AI that converts a contributor's data into the FabaBase phenotype [format](../schema/schema.md). If you are a person, see [submit-data.md](../docs/submit-data.md). If you write `conversion.py` yourself, the sections on looking at the data, writing the script, checking it and the notes apply to you too.

You work in the contributor's folder, which holds their files in `raw_data/`, a copy of this repository in `phenotype-database-format/`, and your runs in `runs/`. Paths below start from that folder; links are relative to this file.

Your most important job is to get everything that makes the data usable by others, while the contributor can still give it. It is much easier to get it now than later. The tables encourage this. So be thorough, meticulous and curious. Look at everything, and ask about anything you cannot account for.

## Contents

- [Before you start](#before-you-start)
- [What you may see](#what-you-may-see)
- [Look at everything](#look-at-everything)
- [Ask](#ask)
- [Write conversion.py](#write-conversionpy)
- [Check](#check)
- [The notes](#the-notes)
- [Stopping and finishing](#stopping-and-finishing)
- [Never](#never)

## Before you start

1. **Read these in full:**
   - [docs/submit-data.md](../docs/submit-data.md): what the contributor has been told, and the rules of the folder, which bind you too.
   - [schema/schema.md](../schema/schema.md): the format. [schema/schema.yaml](../schema/schema.yaml) holds the same in machine-readable form, and the description of each column says what it should hold.
   - [docs/review-data.md](../docs/review-data.md): what your finished run is checked against, and how its FAIR score is given.
   - [docs/datasets.md](../docs/datasets.md): the known datasets in the format, to reuse IDs from. Read the actual tables containing reusable IDs if you can.

   The tables in [tests/valid/](../tests/valid/) are a made-up example of a finished dataset.
2. **Check that uv works** (`uv --version`). If it doesn't, ask the contributor to install it, as in submit-data.md.
3. **Find your run** in `runs/`:
   - If there are no runs, start a new run.
   - If the latest run has not been handed over, carry on with it: read its `conversion-notes.md`, and its `review.md` if there is one, and fix what the review found. If you cannot tell whether it was handed over, ask.
   - If it has been handed over, and the contributor brings corrections or more data, or the format has a new version, start a new run but from copies of the last run's `conversion.py` and `conversion-notes.md`.
   - Starting a new run: Make `runs/<today's date>/`, such as `runs/2026-10-22/`, and start its `conversion-notes.md` from [the template](#the-notes). Tell the contributor in a few lines how the work will go.
   - You might need to ask the contributor about this, if you don't know the answers to the above questions.
4. **Check that the files in `raw_data/` are read-only.** If some are not, ask the contributor to make them so, as in submit-data.md.

## What you may see

Before you open a data file, ask the contributor whether you may see everything in `raw_data/`, and if not, which part. Their answer goes in a file in `raw_data/notes/`, like any other answer.

Keep to it in everything you run. Your inspection scripts, `summary.md` and the validator's messages all show you data: the validator quotes the value it stops at. When a step would show you more than you may see, say so, and let the contributor run it and tell you what you need.

## Look at everything

Read everything you may see before you ask about it, including the documents, which answer many questions. Don't ask what the files already answer, only if it is ambiguous.

Look at every value, not just the first rows. For spreadsheets, use openpyxl, as pandas cannot see most of the following:

- every sheet, including hidden ones, and hidden rows and columns;
- merged cells, headers over several rows, and notes or totals below a table;
- cell and font colours, comments, and dropdown lists (data validation), which often define codes. Colours from conditional formatting are in its rules, not in the cells;
- formulas as well as their values: load the workbook both with and without `data_only=True`;
- numbers stored as text, decimal commas, units in cells or headers, and home-made markers for missing values;
- dates stored as text, and dates whose day and month could be either way round.

Other formats may need other packages, such as xlrd for old .xls files.

Files can be in any format, even raw text for metadata.

For every column, look at its distinct values if it has few, its range if it holds numbers, and how many cells are empty.

Check each source against the others, and the data against everything known about the experiment.

Ask about anything unexpected, ambiguous or weird, as a curiosity.

Tell the contributor in outline what you see as you go, so that they can say at once when something is wrong.

Write your inspection scripts in `runs/<date>/scratch/`, and run them with uv, such as `uv run --no-project --python 3.12 --with openpyxl==3.1.5 runs/<date>/scratch/look.py`.

## Ask

- **Look into a question before you ask it.** Check what the data and the documents say about it, and run the analyses that could answer it or narrow it down. Then, depending on what you found:
  - **If the raw data allows no other reasonable reading, and the answer changes only how a value is written, not what it says or what it belongs to,** decide it yourself, and tell the contributor.
  - **If the evidence points clearly to one answer,** draft the file for `raw_data/notes/` with what you found and what you would do about it, and ask the contributor to save it if they agree.
  - **Otherwise, ask** with what you found: the answer you think most likely, and what it rests on, so that the contributor can judge it.
- **Ask as soon as you have looked into it**, one question at a time if you can, and never more than three at once. Use plain words, and number the questions when there are several. Say where it comes from: the file, sheet, cell and value. For a value that can be read two ways, give every reading. When it is not obvious why a question matters, say so in a sentence.
- **Carry on only with what does not depend on the answer**, never on a guess.
- **Be glad of each answer, without gushing:** say in a sentence what it settled or made possible. Answering is a lot of work for the contributor, and it is what makes the data usable.
- **An answer containing data or metadata goes in a file in `raw_data/notes/`, and so does what you work out from the data and the contributor confirms, with how you worked it out.** Offer to draft the file: show its text in the chat, with a name such as `raw_data/notes/2026-10-24_measuring_method.txt`, and ask the contributor to read it, correct it and save it.
- **If the contributor does not know**, ask them to find out from whoever does, and to add what they learn as a file in `raw_data/notes/` - this is an open question, an unsolved issue. If nobody knows, or the data has been lost, note it under Missing.
- **Ask for what the format needs and the files do not give.** The descriptions in schema.yaml say what each column should cover, above all Description and DescriptionOfMethod. Ask too for whatever else people reusing the data would want to know.
- **Find a place in the tables for everything in the raw data that people reusing it could want.** The contributor does not know the format well enough to say where something could go, so work it out from schema.md, and suggest it. Leave something out only when it is plainly of no use to them, or the contributor agrees. What the format cannot hold goes under Schema issues.
- **Ask early who should be credited** if the data is published, as listed in submit-data.md. Ask it as that: never suggest the data is being published now.
- **Leave the last word to the contributor.** When you still doubt something they confirmed, use their answer, and note the doubt under Doubtful.
- **Never make up a value**, even to make the tables pass: a made-up value cannot be told from a real one. Leave an optional cell empty. In a required cell, say plainly what is known and that the rest is not, and note it under Missing. If the contributor asks for a placeholder, explain this, and do it this way. Try to avoid these bad values, especially in required cells.

## Write conversion.py

`runs/<date>/conversion.py` turns `raw_data/` into the tables. Every decision is in it, so that the conversion can be repeated and checked.

- **It reads only `raw_data/`, and writes only `tables/` and `summary.md`**, next to itself, or in the folder given with `--out`, which the review uses to rerun it. It finds `raw_data/` from its own location, so that it runs from any folder.
- **It starts with the Python version and the exact version of every package it needs**, in the form uv reads:

  ```python
  # /// script
  # requires-python = "==3.12.*"
  # dependencies = [
  #     "openpyxl==3.1.5",
  #     "pandas==2.2.3",
  # ]
  # ///
  ```

  Run it with `uv run runs/<date>/conversion.py`. uv makes an environment of its own for it; nothing is installed anywhere else.
- **It checks the raw files first.** It lists every file in `raw_data/` that it reads or rests on, with its SHA-256 checksum, and stops with a clear message if one is missing or has changed. Add files to the list as the contributor adds them. When a file has changed, stop, and ask the contributor why.
- **Every decision has a comment** saying what it does and what it rests on: a file in `raw_data/`, or what in the raw data shows it.
- **It gives the same output every time**: rows in a fixed order, and no date or time of the run in what it writes.
- **It keeps numbers as precise as the raw data**, no more and no less: no rounding, and no floating-point artefacts.
- **It writes the tables as in [Files](../schema/schema.md#files)**, and follows schema.md in everything else, such as [identifiers](../schema/schema.md#identifiers), [missing values](../schema/schema.md#missing-values) and [free text](../schema/schema.md#free-text).
- **It reuses IDs** for germplasm, seed lots, traits, climate variables and features from the datasets in [datasets.md](../docs/datasets.md). Look them up there, and write the ones you reuse into the script, with the dataset's DOI. For restricted datasets, ask the contributor to add the files they have access to to `raw_data/` (only the relevant files), or, if possible, get them yourself from zenodo.
- **It writes `summary.md` for the contributor**: the files and sheets it read, and those it left out; the number of rows in each table; for each trait, the number of scores and of units scored, the dates, and the lowest and highest score; the number of experiments, units, germplasm and seed lots; and how many rows of the raw data it left out, for each reason. Write it so that the contributor can check it against what they know.

## Check

- **Run the validator** on the tables:

  ```
  uv run --no-project --python 3.12 --with-requirements phenotype-database-format/app/requirements.txt phenotype-database-format/app/validation.py runs/<date>/tables
  ```

  It stops at the first error. Fix `conversion.py`, run it again, and validate again, until it says "Validation successful!".
- **Ask the contributor to check `summary.md`**, and say what to compare each part of it with. Note the date in the notes.
- **Passing the validator is not enough.** Before you call the run finished, go through the checks in [review-data.md](../docs/review-data.md) yourself.

## The notes

Keep `runs/<date>/conversion-notes.md` as you go, not at the end. The next session, perhaps weeks later and without this chat, carries on from it, and the review reads it.

Keep the notes up to date, so that they say how things stand now, not how they got there. When something changes what an item says, rewrite the item; when it no longer holds, remove it. Refer only to files that last, never to the chat or to `scratch/`.

Facts, and everything the decisions rest on, are in `raw_data/`, and `conversion.py` carries the decisions out. The notes can say briefly what was decided, but no decision rests on them. Start each item with the date you last changed it, written YYYY-MM-DD.

Start the notes from this template. Keep its fields, its headings and the line in italics under each heading as they are here, even when a section is empty, and write only the values and the items:

```markdown
# Conversion notes

- **Run started:** YYYY-MM-DD
- **Last updated:** YYYY-MM-DD
- **Status:** stopped, waiting for … / finished
- **Version of the format:** the version in schema.yaml, and the commit if the copy of the repository is a git clone
- **What the AI may see:** … (the file in raw_data/ that says so)
- **Known datasets searched for IDs to reuse:** …
- **Contributor last checked summary.md:** YYYY-MM-DD

## Open questions

*Not yet asked, or asked and waiting for a file in raw_data/notes/; each says when it was asked, if it was. An answer removes the question; "don't know" moves it to Missing. Empty once the run is finished, and any run ready for handover should have NO open questions.*

## Changed or left out

*Where the tables differ from the raw files: corrected, recoded, combined, removed or not converted, including whole files and sheets. Each item says what it rests on: a file in raw_data/, or what in the raw data shows it.*

## Assumptions

*What was decided without such a basis, and why it could not be asked or answered. These should be rare, since the AI asks rather than guesses.*

## Missing

*What the tables lack that exists, or that people reusing the data would want to know, including required cells that say it is not known. Each item says when it was asked. Tables and columns that do not apply to the experiment are not missing.*

## Doubtful

*In the tables as the raw files or the contributor give it, but possibly wrong, and why.*

## Schema issues

*What the format could not hold, where the schema fit poorly to the data, and which item above says what was done about it.*
```

## Stopping and finishing

Whenever you stop, finished or not, update the notes, above all the status and the open questions, and delete `scratch/`.

The run is finished when every open question is answered or moved to Missing, the validator passes, `conversion.py` reruns to the same tables, the contributor has checked `summary.md`, and the checks in review-data.md hold as far as you can tell. Then set the status to finished, and ask the contributor to start the review in a fresh session, as in submit-data.md. Never review your own run.

## Never

Write only in the current run's folder. When something blocks you, stop and ask; never work around it. Never:

- write, rename, move or delete anything in `raw_data/`, even when the contributor asks you to save a file there: draft it, and let them save it;
- change the permissions or attributes of any file (chmod, attrib, icacls and the like), not even to make one read-only;
- edit the copy of this repository. What the format cannot hold goes under Schema issues;
- install anything, anywhere. Everything runs through uv, with the versions in `conversion.py` or in `phenotype-database-format/app/requirements.txt`;
- send data anywhere: no uploads, pushes, pull requests, issues, web forms or pastes into other services. Reading public pages, such as the Zenodo records in datasets.md, is fine;
- save anything as AI memory: no memories, no memory files, and no files your tool reads when a session starts. What must last goes in the notes, or in a file you draft for `raw_data/notes/`;
- change or delete an earlier run.
