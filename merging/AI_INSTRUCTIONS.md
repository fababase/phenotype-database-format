# Instructions for the AI that merges

This file is for the AI that merges the tables of several contributions into one set of tables in the FabaBase phenotype [format](../schema/schema.md), to be published on Zenodo as a version of a dataset: the public one, or the restricted one of a project. Both are merged the same way. You work for the data manager.

You work in the folder of the dataset, which [publish-data.md](../docs/publish-data.md#2-the-dataset-folder) lays out, and only from what is in it: the contributions in `Sources/`, the earlier versions of the dataset in `Versions/`, if there are any, and this copy of the repository. Nothing else is part of a merge.

Your job is to find where the contributions overlap, or write the same thing in different ways, and to propose what to change. The data manager decides every change: you make none without their yes.

## Contents

- [Before you start](#before-you-start)
- [Find the overlaps](#find-the-overlaps)
- [Ask](#ask)
- [Write merge.py](#write-mergepy)
- [Make the values consistent](#make-the-values-consistent)
- [Check](#check)
- [merge-notes.md](#merge-notesmd)
- [changes.md](#changesmd)
- [The README](#the-readme)
- [Finishing](#finishing)
- [Never](#never)

## Before you start

1. **Read these in full:**
   - [docs/publish-data.md](../docs/publish-data.md): the guide for the data manager: the datasets, the dataset folder, and its rules, which hold for you too.
   - [schema/schema.md](../schema/schema.md): the format. [schema/schema.yaml](../schema/schema.yaml) holds the same in machine-readable form, and the description of each column says what it should hold.
   - [Make the values consistent](../conversion/AI_INSTRUCTIONS.md#make-the-values-consistent), in the instructions for converting: how values are written.
   - [Who to credit](../docs/submit-data.md#who-to-credit), in the guide for contributors: what `contributors.yaml` holds, and its format.
2. **Check that uv works** (`uv --version`). If it doesn't, ask the data manager to install it.
3. **Find your way in the dataset folder.** The contributions are the folders in `Sources/`. The last version is the last one that `zenodo.yaml` lists, in its folder in `Versions/`; if there is no `zenodo.yaml`, the dataset is new, so ask the data manager to write it, as [The dataset folder](../docs/publish-data.md#2-the-dataset-folder) says. A folder in `Versions/` with a `merge.py` that `zenodo.yaml` does not list is a merge that was stopped before it was uploaded: carry it on, in its folder, unless the data manager says to leave it. Otherwise, make `Versions/<today's date>` for this merge, and copy `Sources/` into it. These instructions call the folder of this merge the merge folder, and everything you write goes in it. A folder in `Versions/` without a `merge.py` is from before these instructions: leave it alone.
4. **If there was a last version,** start from copies of its `merge.py` and `merge-notes.md`. Its decisions are carried out again without asking, unless a file that a decision rests on has changed. Then ask about that decision again. Compare the copy of `Sources/` in the merge folder with the last version's, by checksums, row counts and IDs: a contribution that differs was handed over again, with corrections or more data. Ask the data manager what changed in it, and why, for [changes.md](#changesmd).
5. **Validate each contribution's folder in the merge folder's `Sources/` on its own**, with this copy of the repository, from the dataset folder:

   ```
   uv run --no-project --python 3.12 --with-requirements phenotype-database-format/app/requirements.txt phenotype-database-format/app/validation.py Versions/<date>/Sources/<contribution>
   ```

   The validator checks its `contributors.yaml` too, and says if there is none. If one fails, or has no `contributors.yaml`, stop, and tell the data manager which one and why. It may have been made for an older version of the format.

Write your scripts for looking at the tables in `scratch/`, in the merge folder, and run them with uv.

## Find the overlaps

Compare the contributions with each other, table by table, and with the tables of the last version. Look at every row, not just the IDs: what each row says.

### Traits, climate variables and features

In PhenotypeDescription, ClimateDescription and Features, find for every row the rows in the other contributions that share its ID, ignoring case, and those that may describe the same thing under another ID. Compare everything they say: the name, the unit, the method, the level the value is taken at, the meaning of every code, and, for features, the Type.

Two rows are the same thing only when they agree in all of this, apart from a unit that converts exactly, as below. When one row leaves out something that the other gives, the tables cannot show that they are the same, so they are not.

For each overlap, propose:

- **Same ID, different things:** a new ID for one of them. If one is in the last merge, it keeps its ID.
- **Same thing, different IDs:** one row, with one ID. Keep an ID that is in the last merge over one that is not; otherwise, propose the one that follows [Identifiers](../schema/schema.md#identifiers) best. Write its description from what the rows say, so that it holds for every score that uses it, and add nothing.
- **Same thing, different units:** one row, as above, with the scores in the other unit converted. Propose it only when the conversion is exact: the two units measure the same quantity, and one is a fixed multiple of the other. Every other conversion is not exact, and neither is one between values of which one set is more specific than the other. Then the rows stay apart, and nothing is converted. Convert into the unit of the row in the last merge, if one of them is in it.
- **Features that are the same thing, with different Vocabularies:** one row, whose Vocabulary allows every value that either allowed.

### Germplasm and seed lots

GPIDs link the scores to genotype data. So a GPID is never changed, and two GPIDs are never made one, nor proposed to be, however alike their rows are.

- **The same GPID in more than one contribution** is the same germplasm, as contributors reuse the GPIDs of known datasets. Propose one row. Where their rows differ, propose what the one row holds, and ask about each difference.
- **GPIDs that differ only in case** cannot both stay, as the validator does not allow it, and neither can be renamed. Stop, and ask the data manager, without proposing anything.

SLIDs, in SeedLot, are handled in the same way.

### Experiments and what belongs to them

The IDs of Experiment, ExperimentalUnit, ExperimentIntervention, Management, Phenotype and Climate each belong to one contribution. When one is in more than one contribution, ignoring case, show the data manager the rows, without their scores, say whether they look like the same thing, and ask.

### People and funding

Compare the `contributors.yaml` of the contributions with each other, and with that of the last merge.

- **People with the same ORCID** are one person. Propose one entry, and ask about each difference in how they are written.
- **A person keeps every affiliation** they have in any of the contributions, each once. Institutions with the same ROR ID are one institution: where they are written differently, ask which way to write them.
- **Grants with the same funder and grant number** are one grant. Propose one entry, and ask about each difference in how they are written.
- **People, institutions and grants that may be the same**, without an ORCID, a ROR ID or a grant number to show it: show both, and ask whether they are one.

## Ask

- **Ask about every change before you make it**, unless merge-notes.md already holds the answer: every ID you would change, every two rows, people, institutions or grants you would make one, every score you would convert, and every value you would write differently. Without the data manager's yes, nothing changes.
- **Look into a question before you ask it.** Check what the tables say about it, and run the analyses that could answer it or narrow it down.
- **Say what you propose, and what it rests on:** the contribution, table, column, ID and value; what you would change it to; and what in the tables shows it. When two rows may be the same thing, show both.
- **Ask in plain words, and number the questions. Never ask more than three at once.** Changes of the same kind that one answer settles can be one question, as long as each of them is listed in it.
- **Carry on only with what does not depend on the answer**, never on a guess.
- **Write every answer in merge-notes.md**, yes or no, so that it is not asked again.
- **When the data manager does not know, change nothing.**
- **Never write anything the contributions do not say**, even to make two rows fit together.

## Write merge.py

`merge.py` turns the contributions' tables and `contributors.yaml` into the merged ones. Every decision is in it, so that the merge can be repeated and checked.

- **It reads only the folders in `Sources/` in the merge folder, and writes only the tables, `contributors.yaml` and `crosswalk.csv`**, next to itself, or in the folder given with `--out`. It finds `Sources/` from its own location, so that it runs from any folder.
- **It starts with the Python version and the exact version of every package it needs**, in the form uv reads, as in [Write conversion.py](../conversion/AI_INSTRUCTIONS.md#write-conversionpy). Run it with `uv run`.
- **It checks what it reads first.** It lists every table and `contributors.yaml` it reads, with its SHA-256 checksum, and stops with a clear message if one is missing or has changed. When one has changed, stop, and ask the data manager why.
- **Every decision has a comment** saying what it does, and the number of the decision in merge-notes.md that it carries out.
- **When it changes an ID, it changes every reference to it**: in every column that links to that table, as schema.yaml gives them, and in the FTIDs inside Features cells.
- **It keeps every score as the contribution gives it**, except where a decision converts it. Then it converts it exactly, in decimal arithmetic: no rounding, and no floating-point artefacts.
- **It gives the same output every time**: rows in a fixed order, and no date or time of the run in what it writes.
- **It writes every table of the format, as the validator writes them with `--out`**: every column, in the order of the format, missing values as empty cells, and a table without rows as a file with only the column names, as in [Files](../schema/schema.md#files). The files are uploaded as they are, and build.py refuses one written otherwise. It follows schema.md in everything else.
- **It writes `contributors.yaml`**, next to the tables, in the format in [Who to credit](../docs/submit-data.md#who-to-credit), the same as a contribution's, with the keys in the order of its template. It holds every person and every grant once: the people in alphabetical order of family name, then given names, and the grants in alphabetical order of funder, then grant number. The experiments of each are those it is behind in any of the contributions, each once, by its EXPID in the merged tables, in alphabetical order.
- **It writes `crosswalk.csv`**, with one row for every ID it changed in every contribution, and the columns Contribution, Table, OldID and NewID, and only the first row when it changed none. Contribution is the name of the contribution's folder in `Sources/`, which is the same in every merge: `publishing/build.py` follows each ID of the last version through the crosswalk of the last merge and of this one, to say which of them changed.

## Make the values consistent

Each contribution was made consistent on its own, but not with the others. Each time `merge.py` has written the tables, go through every column of every table but the Score columns, across all the contributions, as [Make the values consistent](../conversion/AI_INSTRUCTIONS.md#make-the-values-consistent) says: the same thing is written the same way in every row, whichever contribution it comes from.

A merge changes only how a value is written, never what it says, and fills in nothing. Unlike in converting, you ask about every change, as in [Ask](#ask). `merge.py` writes out each value and what it becomes.

## Check

- **Build the version** with `publishing/build.py`, from the dataset folder:

  ```
  uv run phenotype-database-format/publishing/build.py Versions/<date>
  ```

  It runs the validator on the tables and `contributors.yaml`, and stops at the first error. Then it checks that the tables are written as the validator writes them, reads `crosswalk.csv` and `changes.md`, and writes `README.md` in the merge folder. Fix `merge.py`, run it again, and build again, until it builds.
- **Run `merge.py` again**, into `scratch/` with `--out`, and check that it writes the same files, byte for byte.
- **Nothing is lost.** Every row of every contribution is in the merged tables, and every person and grant in its `contributors.yaml` is in the merged one, or was made one with another by a decision in merge-notes.md.
- **Nothing in the last version changes unnoticed.** Every ID in the tables of the last version should still be in the merged tables, with the same row, and every person and grant in its `contributors.yaml` should still be in the merged one, unless a decision in merge-notes.md changed it, or the contributor changed it in a new handover. Tell the data manager about every one that is not.

## merge-notes.md

Keep `merge-notes.md`, in the merge folder, as you go. It holds the decisions of this merge, and the next merge starts from it, so write each decision so that it can be carried out again without this chat.

Number the decisions, and never renumber them or use a number again: `merge.py` refers to them by their numbers, and so does every later merge that starts from these notes. A new decision takes the number after the highest in merge-notes.md. When an answer changes a decision, rewrite its item. When a decision no longer applies, replace its item with one line saying that it was removed, when, and why, and take out of `merge.py` what carries it out.

Start from this template. Keep its fields, its heading and the line in italics as they are here, and write only the values and the items:

```markdown
# Merge notes

- **Last updated:** YYYY-MM-DD
- **Version of the format:** the version in schema.yaml, and the commit the copy of the repository is at
- **Contributions:** the folders in Sources/ that this merge reads

## Decisions

*Every change asked about, and the answer, yes or no. Each item has its number and the date of the answer, and says what changes, where, and what in the tables it rests on, or that it was removed, when, and why.*
```

## changes.md

Write `changes.md`, in the merge folder, for the people who use the data: what changed in this version of the dataset, and why, in a few lines, as paragraphs or a list, with no headings. build.py puts it in the README, under *What changed in this version*, so write it to be read years from now, without this chat. It says, for the first version, that it is the first, and which contributions it holds; after that, which contributions were handed over again, and what the contributor corrected or added, as the data manager says; what the decisions of this merge changed that users of the data would notice, in plain words; and that the format changed, if it did. Write it with the data manager, who has the last word on it.

## The README

You don't write the README of the dataset, or its metadata on Zenodo: `publishing/build.py` builds them from the tables, `contributors.yaml`, `crosswalk.csv`, `changes.md` and `zenodo.yaml`, which the data manager keeps. Once the checks pass, read `README.md` in the merge folder in full. Under *What changed in this version*, every ID that a decision in merge-notes.md changed is renamed, nothing is renamed or removed that no decision explains, and what `changes.md` says agrees with the rest. Tell the data manager about anything in the README that is wrong or looks odd.

## Finishing

Whenever you stop, finished or not, update merge-notes.md, and delete `scratch/`.

The merge is finished when every change has been asked about and answered, the checks pass, you have read the README, and merge-notes.md and changes.md are up to date. Then tell the data manager that the merge is finished, and that the next step is to upload the version, as [Publish a version](../docs/publish-data.md#3-publish-a-version) says. `publishing/publish.py` does that with their Zenodo token, so they run it, never you.

## Never

Write only in the merge folder. When something blocks you, stop and ask; never work around it. Never:

- read the Score column of Phenotype or Climate: never print, summarise, plot or sample it. Merging rests on what the rows say, not on the values measured; the validator and `merge.py` handle the scores without you;
- change anything in the dataset's `Sources/`, or anything of an earlier version;
- write in `zenodo.yaml` or `sandbox.yaml`, which the data manager and publish.py keep;
- make a change the data manager has not said yes to;
- change a GPID or an SLID, or make two of them one;
- change a score, except by an exact conversion the data manager has said yes to;
- change the permissions or attributes of any file (chmod, attrib, icacls and the like);
- edit the copy of this repository;
- install anything, anywhere. Everything runs through uv, with the versions in `merge.py` or in `app/requirements.txt` of this repository;
- send data anywhere or publish anything: no uploads, pushes, pull requests, issues, web forms or pastes into other services. The data manager publishes;
- save anything as AI memory: no memories, no memory files, and no files your tool reads when a session starts. What must last goes in merge-notes.md.
