# Instructions for the AI that merges

This file is for the AI that merges the tables of several contributions into one set of tables in the FabaBase phenotype [format](../schema/schema.md), to be published on Zenodo, as a public record or as a restricted record of a project. Both are merged the same way. You work for the data manager, who tells you which contributions to merge.

You work only from what is in the `tables/` folders: the tables and `contributors.md` of each contribution, and those of the last merge for the same record, if there is one. Nothing else is part of a merge.

Your job is to find where the contributions overlap, or write the same thing in different ways, and to propose what to change. The data manager decides every change: you make none without their yes.

## Contents

- [Before you start](#before-you-start)
- [Find the overlaps](#find-the-overlaps)
- [Ask](#ask)
- [Write merge.py](#write-mergepy)
- [Make the values consistent](#make-the-values-consistent)
- [Check](#check)
- [merge-notes.md](#merge-notesmd)
- [The Zenodo README](#the-zenodo-readme)
- [Finishing](#finishing)
- [Never](#never)

## Before you start

1. **Read these in full:**
   - [schema/schema.md](../schema/schema.md): the format. [schema/schema.yaml](../schema/schema.yaml) holds the same in machine-readable form, and the description of each column says what it should hold.
   - [Make the values consistent](../conversion/AI_INSTRUCTIONS.md#make-the-values-consistent), in the instructions for converting: how values are written.
   - [Who to credit](../docs/submit-data.md#who-to-credit), in the guide for contributors: what `contributors.md` holds, and its template.
2. **Check that uv works** (`uv --version`). If it doesn't, ask the data manager to install it.
3. **Ask the data manager what you cannot tell from the folder you are in:**
   - which contributions to merge, and where their tables are;
   - whether the record has been merged before, and where that last merge is;
   - which folder this merge is written in. These instructions call it the merge folder, and everything you write goes in it.
4. **If there was a last merge,** start from copies of its `merge.py` and `merge-notes.md`. Its decisions are carried out again without asking, unless a file that a decision rests on has changed. Then ask about that decision again.
5. **Validate each contribution's tables on their own**, as in [Check](#check), and check that its `contributors.md` follows the template. If one fails, stop, and tell the data manager which one fails and why. It may have been made for an older version of the format.

Write your scripts for looking at the tables in `scratch/`, in the merge folder, and run them with uv.

## Find the overlaps

Compare the contributions with each other, table by table, and with the tables of the last merge. Look at every row, not just the IDs: what each row says, and the scores that use it.

### Traits, climate variables and features

In PhenotypeDescription, ClimateDescription and Features, find for every row the rows in the other contributions that share its ID, ignoring case, and those that may describe the same thing under another ID. Compare everything they say: the name, the unit, the method, the level the value is taken at, the meaning of every code, and, for features, the Type. Compare the scores that use them too: their range and spread in each contribution.

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

The IDs of Experiment, ExperimentalUnit, ExperimentIntervention, Management, Phenotype and Climate each belong to one contribution. When one is in more than one contribution, ignoring case, show the data manager the rows, say whether they look like the same thing, and ask.

### People and funding

Compare the `contributors.md` of the contributions with each other, and with that of the last merge.

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

`merge.py` turns the contributions' tables and `contributors.md` into the merged ones. Every decision is in it, so that the merge can be repeated and checked.

- **It reads only the contributions' `tables/` folders, and writes only `tables/` and `crosswalk.csv`**, next to itself in the merge folder, or in the folder given with `--out`. It finds the files it reads from its own location, so that it runs from any folder.
- **It starts with the Python version and the exact version of every package it needs**, in the form uv reads, as in [Write conversion.py](../conversion/AI_INSTRUCTIONS.md#write-conversionpy). Run it with `uv run`.
- **It checks what it reads first.** It lists every table and `contributors.md` it reads, with its SHA-256 checksum, and stops with a clear message if one is missing or has changed. When one has changed, stop, and ask the data manager why.
- **Every decision has a comment** saying what it does, and the number of the decision in merge-notes.md that it carries out.
- **When it changes an ID, it changes every reference to it**: in every column that links to that table, as schema.yaml gives them, and in the FTIDs inside Features cells.
- **It keeps every score as the contribution gives it**, except where a decision converts it. Then it converts it exactly, in decimal arithmetic: no rounding, and no floating-point artefacts.
- **It gives the same output every time**: rows in a fixed order, and no date or time of the run in what it writes.
- **It writes the tables as in [Files](../schema/schema.md#files)**, and follows schema.md in everything else.
- **It writes `tables/contributors.md`** in the template in [Who to credit](../docs/submit-data.md#who-to-credit), with every person and every grant once: the people in alphabetical order of family name, then given names, and the grants in alphabetical order of funder, then grant number. Each person and each grant ends with a line `- **Experiments:** …`, which lists the EXPIDs, as in the merged tables, of the experiments in the contributions they are in.
- **It writes `crosswalk.csv`**, with one row for every ID it changed in every contribution, and the columns Contribution, Table, OldID and NewID.

## Make the values consistent

Each contribution was made consistent on its own, but not with the others. Each time `merge.py` has written the tables, go through every column of every table, across all the contributions, as [Make the values consistent](../conversion/AI_INSTRUCTIONS.md#make-the-values-consistent) says: the same thing is written the same way in every row, whichever contribution it comes from.

A merge changes only how a value is written, never what it says, and fills in nothing. Unlike in converting, you ask about every change, as in [Ask](#ask). `merge.py` writes out each value and what it becomes.

## Check

- **Run the validator** on the merged tables, with the copy of this repository that holds this file:

  ```
  uv run --no-project --python 3.12 --with-requirements <repository>/app/requirements.txt <repository>/app/validation.py <merge folder>/tables
  ```

  It stops at the first error. Fix `merge.py`, run it again, and validate again, until it says "Validation successful!".
- **Run `merge.py` again**, into `scratch/` with `--out`, and check that it writes the same files, byte for byte.
- **Nothing is lost.** Every row of every contribution is in the merged tables, and every person and grant in its `contributors.md` is in the merged one, or was made one with another by a decision in merge-notes.md.
- **Nothing in the last merge changes unnoticed.** Every ID in the tables of the last merge should still be in the merged tables, with the same row, and every person and grant in its `contributors.md` should still be in the merged one, unless a decision in merge-notes.md changed it. Tell the data manager about every one that is not.

## merge-notes.md

Keep `merge-notes.md`, in the merge folder, as you go. It holds the decisions of this merge, and the next merge starts from it, so write each decision so that it can be carried out again without this chat.

Number the decisions, and never renumber them or use a number again: `merge.py` refers to them by their numbers, and so does every later merge that starts from these notes. A new decision takes the number after the highest in merge-notes.md. When an answer changes a decision, rewrite its item. When a decision no longer applies, replace its item with one line saying that it was removed, when, and why, and take out of `merge.py` what carries it out.

Start from this template. Keep its fields, its heading and the line in italics as they are here, and write only the values and the items:

```markdown
# Merge notes

- **Last updated:** YYYY-MM-DD
- **Version of the format:** the version in schema.yaml, and the commit if the copy of the repository is a git clone
- **Contributions:** …

## Decisions

*Every change asked about, and the answer, yes or no. Each item has its number and the date of the answer, and says what changes, where, and what in the tables it rests on, or that it was removed, when, and why.*
```

## The Zenodo README

**Not written yet: skip this section.** The README template for the Zenodo record is still to be made. Once it is, this section says how to fill it in from the merged tables and `contributors.md`, with nothing they do not say.

## Finishing

Whenever you stop, finished or not, update merge-notes.md, and delete `scratch/`.

The merge is finished when every change has been asked about and answered, the checks pass, and merge-notes.md is up to date. Then tell the data manager that the merge is finished, and point them to the command that publishes it on Zenodo. **Not written yet:** until that command exists, tell them that the merged tables are ready to publish.

## Never

Write only in the merge folder. When something blocks you, stop and ask; never work around it. Never:

- change anything in a contribution's `tables/` folder, or anything of an earlier merge;
- make a change the data manager has not said yes to;
- change a GPID or an SLID, or make two of them one;
- change a score, except by an exact conversion the data manager has said yes to;
- change the permissions or attributes of any file (chmod, attrib, icacls and the like);
- edit the copy of this repository;
- install anything, anywhere. Everything runs through uv, with the versions in `merge.py` or in `app/requirements.txt` of this repository;
- send data anywhere or publish anything: no uploads, pushes, pull requests, issues, web forms or pastes into other services. The data manager publishes;
- save anything as AI memory: no memories, no memory files, and no files your tool reads when a session starts. What must last goes in merge-notes.md.
