# Submitting data

This guide is for researchers who want to add their phenotype data to FabaBase. It goes from your raw files to the tables of the [format](../schema/schema.md), and ends with a folder you keep: the raw data, what turned it into the tables, and notes on what was changed and why. Your AI reads this guide too.

You can make the tables in three ways. An AI agent can read your files, ask you about everything it cannot tell from them, and write a script, `conversion.py`, that turns them into the tables. You can write that script yourself, without an AI. Or you can fill in the [collection sheet](#the-collection-sheet), a workbook with one sheet per table of the format. The first two use the same folder and the same steps, the third one fills data manually and then uses the app to validate.

The steps are written for working with an AI. Where it is different without one, a blue box in the step says what to do instead.

1. [Choose how to make the tables](#1-choose-how-to-make-the-tables)
2. [Install what you need](#2-install-what-you-need)
3. [Gather your data](#3-gather-your-data)
4. [Set up the folder](#4-set-up-the-folder)
5. [Open the folder in your AI tool](#5-open-the-folder-in-your-ai-tool) (only with an AI)
6. [Find what is missing, and fill it in](#6-find-what-is-missing-and-fill-it-in)
7. [Make the tables](#7-make-the-tables)
8. [Check the result](#8-check-the-result)
9. [Have it reviewed](#9-have-it-reviewed)
10. [Hand over](#10-hand-over)

## 1. Choose how to make the tables

Most AI tools send everything the AI reads to the company that runs it. You need permission to share your data that way, and the willingness to. You can limit what the AI sees (step 6).

A script is better than filling in tables by hand: it shows every change made to the raw data, and it can be run again when something turns out to be wrong. An AI writes it for you.

> [!NOTE]
> **Without an AI**, you need to know some Python to write the script yourself. The [collection sheet](#the-collection-sheet) needs no programming, and is separate from these steps. If you would rather not share your data with an AI at all, a colleague can do the review in step 9.

## 2. Install what you need

You install these yourself, as the AI is not allowed to install anything. It checks that uv works when it starts.

> [!NOTE]
> **Without an AI**, you don't need the AI tool, but a script of your own still needs uv.

### An AI tool

It has to work in a folder on your computer, reading the files there and running commands, such as Claude Code, Codex, Gemini CLI or GitHub Copilot in agent mode. A chat in a web browser is not enough.

### uv

[uv](https://docs.astral.sh/uv/) is a small program that runs `conversion.py` and the validator with the right versions of Python and its packages, without installing them onto your computer. Install it as in [its instructions](https://docs.astral.sh/uv/getting-started/installation/), or with this in a terminal:

- Windows (PowerShell): `powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"`
- macOS and Linux: `curl -LsSf https://astral.sh/uv/install.sh | sh`

Then open a new terminal, and check that `uv --version` prints a version number.

### git

git is a program that copies this repository and keeps track of its versions. It is optional, but with a git copy, the notes can say exactly which version of the format your data was converted to.

- Windows: download Git for Windows from <https://git-scm.com/downloads/win>, and install it with the choices it suggests. Or run `winget install --id Git.Git -e --source winget` in a terminal.
- macOS: run `git --version` in Terminal. If git is missing, macOS offers to install it.
- Linux: install it with your package manager, such as `sudo apt install git` on Ubuntu.

Then open a new terminal, and check that `git --version` prints a version number.

If you would rather not use a terminal, [GitHub Desktop](https://desktop.github.com/) can copy the repository too. Without either, download it as a ZIP in step 4.

## 3. Gather your data

Collect your data files, and everything that describes them: protocols, field plans, lab notebooks, reports, theses, papers. They answer many of the questions in step 6, and the tables are checked against them.

The AI can only use what you give it. Every document, note or sheet it can read is a question it does not have to ask, saving you the time or hassle.

## 4. Set up the folder

You make the top-level folder and the `raw_data` folder, and clone the `phenotype-database-format` repository, while the AI makes `runs/`. The AI is not allowed to write in `raw_data` or change the permissions of files.

Make one folder for the data contribution, named after it, such as `nordbean_irrigation_2025`. When the work is done, it looks like this:

```
nordbean_irrigation_2025/
  raw_data/                      everything from you: data, documents, answers, in any format
  phenotype-database-format/     a copy of this repository
  runs/
    2026-10-22/                  one run per handover
      conversion.py              the script: raw_data/ → tables/
      conversion-notes.md        the notes: what was changed, what is missing, what is doubtful
      summary.md                 what the tables hold, written by conversion.py each time it runs
      review.md                  the review: what it found, and the FAIR score
      tables/                    Germplasm.csv … Features.csv
```

1. **Copy this repository into the folder**, as `phenotype-database-format`.
   - With git, open a terminal in the contribution folder, and run `git clone https://github.com/fababase/phenotype-database-format.git`.
   - With GitHub Desktop, choose *File* → *Clone repository*, give it the address <https://github.com/fababase/phenotype-database-format.git>, and choose a local path inside the contribution folder.
   - Without either, download it as a ZIP (*Code* → *Download ZIP* on GitHub), unzip it into the folder, and rename `phenotype-database-format-main` to `phenotype-database-format`.

   To open a terminal in a folder on Windows, right-click inside the folder in File Explorer and choose *Open in Terminal*. On macOS and Linux, open a terminal, type `cd ` with a space after it, drag the folder onto the window, and press Enter.
2. **Make a folder `raw_data`**, and copy into it your data files and the documents that describe them. Copy rather than move them, so that you keep your originals. Subfolders are fine.
3. **Make the files in `raw_data` read-only**, so that nothing can change them by accident. Do it again whenever you add files.
   - Windows: right-click `raw_data`, choose *Properties*, tick *Read-only*, and apply it to all subfolders and files.
   - macOS and Linux: in a terminal, in the contribution folder, run `find raw_data -type f -exec chmod a-w {} +`.

> [!NOTE]
> **Without an AI**, make `runs` yourself, and in it a folder named after today's date, such as `runs/2026-10-22`.

### The rules of the folder

These apply to you and to the AI.

- **Add to `raw_data`; don't change or delete what is there unless the mistake is clear.** If a file turns out to be wrong, prefer (within reason) adding a corrected copy under a new name, or a file that says what is wrong. `conversion.py` checks every file it reads, and stops if one has changed.
- **Everything you tell the AI, or find out yourself, goes in a file in `raw_data`**, never only in a chat, as this cannot be saved for future runs. This includes answers to questions, corrections, how things were measured, what the AI may see. Plain text is fine. Optionally, start the file's name with the date, such as `2026-10-24_measuring_method.txt`. A chat is gone when the session ends, the files stay, so that the conversion can be repeated if another issue is spotted down the line.
- **Only `conversion.py` writes the tables.** Don't edit them by hand, as the edit will be lost the next time the tables are written, and nobody can tell it was made.
- **Don't edit the copy of this repository.** It is the version of the format your data is converted to.
- **One run per handover.** A run ends *stopped*, waiting for something you have to find, or *finished*. A stopped run is carried on in the same folder. A new run is only started for a new handover: corrections or more data after the last one, or a new version of the format.

## 5. Open the folder in your AI tool

The AI works in one folder, its workspace, and sees only what is in it. Make that the contribution folder, so that it sees both `raw_data` and the copy of this repository. Don't open `raw_data` or the copy of the repository on their own, or a bigger folder such as Documents, where the AI could read other files.

- With a tool that runs in a terminal, such as Claude Code, Codex or Gemini CLI, open a terminal in the contribution folder, as in step 4, and type `claude`, `codex` or `gemini`.
- In VS Code, choose *File* → *Open Folder*, and pick the contribution folder. Then open your AI tool there, such as the Claude Code panel, or Copilot Chat in *Agent* mode.

If the tool asks whether you trust the folder, say yes. It also asks before it runs a command or changes a file. Read what it wants to do: it should only ever write in `runs`.

Then type:

> Read `phenotype-database-format/conversion/AI_INSTRUCTIONS.md` and follow it.

Use the same line whenever you come back: in a new session, after a break, or with corrections or more data after a handover. The AI carries on from its notes.

## 6. Find what is missing, and fill it in

The tables need more than the numbers. Someone who wasn't there should be able to use them years from now, so they also need how each trait was measured, what the codes mean, how the trial was laid out, and so on. The descriptions of the columns in [schema.yaml](../schema/schema.yaml) say what each should cover. Anything that looks odd needs explaining too: a gap in the plot numbers, a code nobody explained, a date that could be read two ways.

This step takes the most time, and matters most. You are the only one who can give this information, and it is much easier to get now than later.

Before it opens your data, the AI asks what it may see: everything in `raw_data`, or only part of it. It reads everything it may see, and asks about what it cannot account for, a few questions at a time, as they come up.

Save each answer in a file in `raw_data`, as the rules of the folder say. The AI can draft the file in the chat, but you save it, after reading it and correcting what is wrong. If you don't know an answer, try to find out, from a colleague, the person who ran the trial, a notebook or a protocol, and add what you find as a file. If nobody knows, or the data has been lost, it is noted as missing, and it lowers the FAIR score in the review.

When the AI needs something you have to find or ask for, it stops and notes what it is waiting for. Come back with the same line when you have it.

You have the last word: if the AI still doubts something you confirmed, it notes the doubt and uses your answer.

> [!NOTE]
> **Without an AI**, you look for all of this yourself. [Look at everything](../conversion/AI_INSTRUCTIONS.md#look-at-everything) in the AI's instructions lists what to look for, such as hidden sheets, merged cells and dates that could be read either way round.

### Who to credit

When the data is eventually published, the people behind it should be credited. For this reason, give the name, ORCID and affiliation of each person, contact information, and the funding. Save them in a file in `raw_data`, like any other answer. They go into the Description of the Experiment table. The AI asks for these early.

## 7. Make the tables

The AI writes `runs/<date>/conversion.py`, which turns `raw_data` into the tables. Every decision is written in it, so that the conversion can be repeated and checked. The AI runs the script and the validator, and keeps the notes, `conversion-notes.md` in the run's folder, as it goes. You can read the notes at any time.

In practice, steps 6, 7 and 8 go back and forth: making the tables raises new questions, and checking them can show something to fix.

> [!NOTE]
> **Without an AI**, read the [schema](../schema/schema.md) first, and reuse the IDs already used for germplasm, seed lots, traits, climate variables and features in the [known datasets](datasets.md) you have access to.
>
> To write `conversion.py` yourself, follow these sections of the AI's instructions. They are written to the AI, but the rules are the same for you.
>
> - [Write conversion.py](../conversion/AI_INSTRUCTIONS.md#write-conversionpy): what the script reads and writes, the versions it needs, the checksums of the raw files, and `summary.md`.
> - [Check](../conversion/AI_INSTRUCTIONS.md#check): how to run the validator.
> - [The notes](../conversion/AI_INSTRUCTIONS.md#the-notes): what goes in `conversion-notes.md`, with a template.

## 8. Check the result

The AI asks you to check `summary.md`, and says what to compare it with. `conversion.py` writes it each time it runs. It says what the tables hold: the traits and how many scores each has, the units, experiments and germplasm, the dates, and the range of each trait. Compare it with what you know. It could show a wrong number of plots, or a trait with impossible values.

## 9. Have it reviewed

When the AI says the run is finished, start a fresh session, a new conversation, in the same folder, and type:

> Read `phenotype-database-format/docs/review-data.md` and review the latest run.

The review checks the work using only the files, and writes `review.md` in the run's folder: what it found, and a FAIR score from 1 to 5. [FAIR](https://www.go-fair.org/fair-principles/) stands for Findable, Accessible, Interoperable and Reusable, principles for data that others can find and use. The score says how well the dataset is described for that, and what would raise it.

The review has to be done by someone other than whoever made the tables, which is why it is a fresh session. If the review found problems, or you want to raise the score, start the AI again with the line from step 5. It fixes what it can, and asks you for the rest. Then start another fresh session for a new review.

> [!NOTE]
> **Without an AI**, ask a colleague to review the run, following [review-data.md](review-data.md). A fresh AI session can do it too, if you may share the data with it. Fix what the review finds, and have it reviewed again.

## 10. Hand over

How to hand over the tables is still to be decided. Until then, keep the folder as it is. This step is yours: the AI never sends data anywhere.

Keep the folder after handing over, too: `raw_data`, the script and the notes are what keep the conversion traceable and reproducible. Corrections or more data after a handover go in a new run, as the [rules of the folder](#the-rules-of-the-folder) say.

## The collection sheet

The collection sheet is no longer the recommended way to contribute data, but it is still allowed. It is separate from the steps above: you fill in the tables by hand, with [schema.md](../schema/schema.md) as a guide, and reuse the IDs already used in the [known datasets](datasets.md) you have access to.

1. Download a blank sheet from the [app](https://fababase.github.io/phenotype-database-format/), and fill it in as its *READ ME 1st* sheet says.
2. Check it in the app, and fix what it reports, until it passes.
3. Download the tables from the app (*Download tables as CSV*).
4. (Optionally) Have a colleague review your filled in collection sheet.
5. Hand over data, as detailed in step 10 of the above guide.
