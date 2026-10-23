# Reviewing a contribution

This guide is for data reviewers. A review checks a finished run of a conversion before its tables are handed over, and gives the dataset a FAIR score. A person or a fresh AI session can do it. As of now, started by the contributor as in [submit-data.md](submit-data.md#9-have-it-reviewed). The AI that does the conversion reads this guide too.

## How to review

- **(For AI) Review the latest run** in `runs/`, using only the files in the contribution folder: `raw_data/`, the run, and the copy of this repository. Don't rely on the chat of a conversion, or on memory.
- **Keep to what the AI may see**, as the run's notes say. If that rules out a check, note it under Checks not done.
- **Write only `review.md`**, in the run's folder, replacing any earlier one. Change nothing else. What needs fixing goes in `review.md`, and the AI that does the conversion fixes it.
- **Write for the contributor**, in plain words: for each problem, where it is and what would fix it.

## Checks

1. **The run is finished.** Its status in `conversion-notes.md` is finished, it has no open questions, and it has no `scratch/` folder.
2. **The raw files are unchanged, and the tables are what `conversion.py` writes.** Rerun it into a temporary folder outside the contribution folder, with `uv run runs/<date>/conversion.py --out <folder>`. It checks the raw files first, and stops if one has changed. The `tables/` and `summary.md` it writes must be the same as the run's, byte for byte. Delete the temporary folder afterwards.
3. **The tables pass the validator**, run as in [Check](../conversion/AI_INSTRUCTIONS.md#check).
4. **Every raw file is accounted for.** Each file in `raw_data/` is read by `conversion.py`, referred to in its comments or in the notes, or listed under Changed or left out as not converted.
5. **The values are the raw values.** Pick at least 20 scores at random from Phenotype and Climate, and a few rows from each other table. Find each in the raw files, and check that it is the same value, in the same unit, for the same plot or sample, trait and date. If one does not match, try picking more values and see if it is a general problem.
6. **Every fact is in `raw_data/`.** Read every free-text cell, such as Description, DescriptionOfMethod and Comments, and check each fact in it against the raw files. Nothing may come from the chat, from guessing, or from what is usual but not absolutely standard in such experiments.
7. **The notes hold up.** Each item under Changed or left out rests on a file or on the raw data, as it says. Each assumption says why it could not be asked, and the reason holds. Each item under Missing says when it was asked.
8. **The IDs are right.** IDs follow [Identifiers](../schema/schema.md#identifiers). New IDs in Germplasm, SeedLot, PhenotypeDescription, ClimateDescription and Features were checked against the datasets in [datasets.md](datasets.md), and none is a near-copy of an existing one, such as `hedin2` beside `hedin_2`.
9. **The details of who to credit are there**, as listed in [submit-data.md](submit-data.md#who-to-credit): in a file in `raw_data/`, and in the Description of the Experiment table.

## FAIR score

Give the dataset a score from 1 to 5 for how well it meets the [FAIR principles](https://www.go-fair.org/fair-principles/): data that are Findable, Accessible, Interoperable and Reusable. Findable and Accessible come from publishing on Zenodo, so in practice the score is about how richly the data are described, and whether they reuse shared IDs.

- **Count what is not described**: what exists, or what people reusing the data would want to know, that the tables do not give. The descriptions of the columns in [schema.yaml](../schema/schema.yaml) say what each should cover. For every number, ask: could someone who was not there, years later, use it with only these tables?
- **Don't count what does not apply**: tables and columns that make no or little sense for the experiment, such as ExperimentIntervention in an experiment without interventions, or Row and Column for samples in a lab.
- **A required value that is not known keeps the score at 2 or below.**
- **Be realistic**: neither generous nor harsh.

| Score | Meaning |
|---|---|
| 5 | Everything people reusing the data would want to know is described, with only minor faults. |
| 4 | Small but noticeable gaps, which matter only for some uses. |
| 3 | Significant gaps: data or metadata that a lot of uses would want are not described. |
| 2 | Something needed to read part of the data is not known, such as a required value. |
| 1 | Most of the data cannot be interpreted. |

For every point below 5, name the items in Missing, Assumptions or Doubtful that cost it, so that the contributor can see what would raise the score.

## review.md

Write `review.md` from this template, and keep the line in italics under each heading:

```markdown
# Review

- **Reviewed:** YYYY-MM-DD
- **Run:** runs/YYYY-MM-DD/
- **Result:** passes / problems to fix
- **FAIR score:** N of 5

## Problems

*Each with where it is and what would fix it. Empty if there are none.*

## Checks not done

*What could not be checked, and why.*

## FAIR score

*The score, and for every point below 5, the items that cost it.*
```
