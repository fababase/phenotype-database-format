# Submitting data

This guide is for researchers who want to add their phenotype data to Phenotheca. It goes from your raw files to the tables of the [format](../schema/schema.md), and ends with a folder you keep: the raw data, what turned it into the tables, and notes on what was changed and why. Your AI reads this guide too.

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

### VS Code

[VS Code](https://code.visualstudio.com/download) is a free program for working with the files in a folder. You open the contribution folder in it, work with the AI there, run commands, and read and write the files, all in one window. Download it, and install it with the choices it suggests.

Files whose names end in `.md`, such as the notes and the summary, are written in Markdown: plain text, with marks for headings, lists and tables. VS Code shows them formatted: right-click one in the list of files on the left, and choose *Open Preview*.

### An AI tool

It has to work in a folder on your computer, reading the files there and running commands. A chat in a web browser is not enough. These three work inside VS Code. Install the one you choose from its page, and sign in:

- Claude: [Claude Code](https://code.claude.com/docs/en/vs-code), with a Claude account on a paid plan.
- Gemini: [Google Antigravity](https://antigravity.google/docs/ide/extensions/vscode), with a Google account.
- ChatGPT: [Codex](https://learn.chatgpt.com/docs/codex/ide), with a ChatGPT account.

Install it as it comes. Don't add connectors, plugins, skills or extensions to it, and turn off its memory if it has one.

### uv

[uv](https://docs.astral.sh/uv/) is a small program that runs `conversion.py` and the validator with the right versions of Python and its packages, without installing them onto your computer. Install it as in [its instructions](https://docs.astral.sh/uv/getting-started/installation/), or with a command in a terminal: a window in which you type commands rather than click. In VS Code, choose *Terminal* → *New Terminal*, and one opens at the bottom of the window. Copy the command for your computer into it, and press Enter:

- Windows:

  ```
  powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
  ```
- macOS and Linux:

  ```
  curl -LsSf https://astral.sh/uv/install.sh | sh
  ```

Then close VS Code, open it again, and check in a new terminal that this prints a version number:

```
uv --version
```

### git

git is a program that copies this repository and keeps track of its versions. It is optional, but with a git copy, the notes can say exactly which version of the format your data was converted to.

- Windows: download Git for Windows from <https://git-scm.com/downloads/win>, and install it with the choices it suggests.
- macOS: run the command below in a terminal. If git is missing, macOS offers to install it.
- Linux: install it with your package manager, such as `sudo apt install git` on Ubuntu.

Then close VS Code, open it again, and check in a new terminal that this prints a version number:

```
git --version
```

If you would rather not use a terminal, [GitHub Desktop](https://desktop.github.com/) can copy the repository too. Without either, download it as a ZIP in step 4.

## 3. Gather your data

Collect your data files, and everything that describes them: protocols, field plans, lab notebooks, reports, theses, papers. They answer many of the questions in step 6, and the tables are checked against them.

The AI can only use what you give it. Every document, note or sheet it can read is a question it does not have to ask.

## 4. Set up the folder

You make the top-level folder and the `raw_data` folder, and clone the `phenotheca` repository, while the AI makes `runs/`. The AI is not allowed to write in `raw_data` or change the permissions of files.

Make one folder for the data contribution, named after it, such as `nordbean_irrigation_2025`. When the work is done, it looks like this:

![The contribution folder, nordbean_irrigation_2025, one folder per contribution, named after it. raw_data is yours, with your data and documents, read-only, and in it notes, with your answers, one file per subject. phenotheca is a copy of this repository, which nobody edits. runs is where the AI writes, one run per handover. In 2026-10-22 are conversion.py, the script from raw_data to tables, conversion-notes.md, with what was changed and what is missing, summary.md, with what the tables hold, for you to check, review.md, the review with the FAIR score, and tables, with the tables and who to credit, written by the script alone.](images/contribution.svg)

1. **Open the folder in VS Code**: choose *File* → *Open Folder*, and pick the contribution folder. If VS Code asks whether you trust the authors of the files in it, say yes. A terminal you open in VS Code then starts in this folder.
2. **Copy this repository into the folder**, as `phenotheca`.
   - With git, run this in a terminal in VS Code:

     ```
     git clone https://github.com/phenotheca/phenotheca.git
     ```
   - With GitHub Desktop, choose *File* → *Clone repository*, give it the address <https://github.com/phenotheca/phenotheca.git>, and choose a local path inside the contribution folder.
   - Without either, download it as a ZIP (*Code* → *Download ZIP* on GitHub), unzip it into the folder, and rename `phenotheca-main` to `phenotheca`.
3. **Make a folder `raw_data`**, and copy into it your data files and the documents that describe them. Copy rather than move them, so that you keep your originals. Subfolders are fine. Make one called `notes` as well, for what is written down during the conversion.
4. **Make the files in `raw_data` read-only**, so that nothing can change them by accident. Do it again whenever you add files.
   - Windows: in File Explorer, right-click `raw_data`, choose *Properties*, tick *Read-only*, and apply it to all subfolders and files.
   - macOS and Linux: run this in a terminal in VS Code:

     ```
     find raw_data -type f -exec chmod a-w {} +
     ```

   To correct a file in `raw_data/notes`, make the files there writable first, and read-only again when you are done:
   - Windows: in File Explorer, right-click `notes`, choose *Properties*, untick *Read-only*, and apply it to all subfolders and files.
   - macOS and Linux: run this in a terminal in VS Code:

     ```
     chmod -R u+w raw_data/notes
     ```

> [!NOTE]
> **Without an AI**, make `runs` yourself, and in it a folder named after today's date, such as `runs/2026-10-22`.

### The rules of the folder

These apply to you and to the AI.

- **Add to `raw_data`; don't change or delete what is there unless the mistake is clear.** If a file outside `raw_data/notes` turns out to be wrong, add a corrected copy under a new name, or a file that says what is wrong. `conversion.py` checks every file it reads, and stops if one has changed.
- **Everything you tell the AI, or find out yourself, goes in a file in `raw_data/notes`**, never only in a chat: a chat is gone when the session ends, while the files stay, so that the conversion can be repeated. This includes answers to questions, corrections, how things were measured, and what the AI may see. Plain text is fine. Give each file one subject, name it after that, and number its sections. When something in it changes or turns out wrong, correct that file, rather than adding one that says so: when files disagree, the AI cannot tell which is right.
- **Only `conversion.py` writes in `tables/`.** Don't edit what is there by hand, as the edit will be lost the next time `conversion.py` runs, and nobody can tell it was made.
- **Don't edit the copy of this repository.** It is the version of the format your data is converted to.
- **One run per handover.** A run ends *stopped*, waiting for something you have to find, or *finished*. A stopped run is carried on in the same folder. A new run is only started for a new handover: corrections or more data after the last one, or a new version of the format.

## 5. Open the folder in your AI tool

The AI works in one folder, its workspace, and sees only what is in it. Make that the contribution folder, so that it sees both `raw_data` and the copy of this repository. Don't open `raw_data` or the copy of the repository on their own, or a bigger folder such as Documents, where the AI could read other files.

In VS Code, open the contribution folder, as in step 4, if it is not open already. Then open your AI tool from its icon in the bar on the left.

If the tool asks whether you trust the folder, say yes. It may also ask before it runs a command or changes a file. Read what it wants to do: it should only ever write in `runs`.

Then type:

```
Read phenotheca/conversion/AI_INSTRUCTIONS.md and follow it.
```

Use the same line whenever you come back: in a new session, after a break, or with corrections or more data after a handover. The AI carries on from its notes.

## 6. Find what is missing, and fill it in

The tables need more than the numbers. Someone who wasn't there should be able to use them years from now, so they also need how each trait was measured, what the codes mean, how the trial was laid out, and so on. The descriptions of the columns in [schema.yaml](../schema/schema.yaml) say what each should cover. Anything that looks odd needs explaining too: a gap in the plot numbers, a code nobody explained, a date that could be read two ways.

This step takes the most time, and matters most. You are the only one who can give this information, and it is much easier to get now than later.

Before it opens your data, the AI asks what it may see: everything in `raw_data`, or only part of it. It reads everything it may see, and looks into what it cannot account for. Inconsistencies in how values are written, where the meaning is plain, it fixes itself and tells you. For the rest, it either drafts an answer for you to check and save, or asks you, one question at a time where it can and never more than three at once.

Save each answer in a file in `raw_data/notes`, as the rules of the folder say. The AI can draft the file in the chat, but you save it, after reading it and correcting what is wrong:

1. In VS Code, make a new file in `raw_data/notes`, named after its subject and ending in `.md`.
2. Copy the AI's draft into it, correct it, and save it.
3. Make it read-only, as in [step 4](#4-set-up-the-folder).

To correct a file that is already there, make it writable first, as in step 4.

If you don't know an answer, try to find out, from a colleague, the person who ran the trial, a notebook or a protocol, and add what you find as a file. If nobody knows, or the data has been lost, it is noted as missing, and it lowers the FAIR score in the review.

When the AI needs something you have to find or ask for, it stops and notes what it is waiting for. Come back with the same line when you have it.

You have the last word: if the AI still doubts something you confirmed, it notes the doubt and uses your answer.

> [!NOTE]
> **Without an AI**, you look for all of this yourself. [Look at everything](../conversion/AI_INSTRUCTIONS.md#look-at-everything) in the AI's instructions lists what to look for, such as hidden sheets, merged cells and dates that could be read either way round.

### Who to credit

When the data is eventually published, the people behind it should be credited, and so should its funding. Each experiment also needs someone to ask about it, in the years to come. The AI asks for these details early. Save them in a file in `raw_data/notes`, like any other answer. `conversion.py` writes them into `tables/contributors.yaml`, which is handed over with the tables. Credit goes only there, not in the Description of the Experiment table.

If the data is published, everyone in `contributors.yaml` is named as a creator of the dataset on Zenodo, in alphabetical order of family name, so that they are cited with it. Its funding is listed there too.

`contributors.yaml` is written in [YAML](https://yaml.org), a plain-text format that programs read exactly, and follows this template:

```yaml
people:
  - family_name: <family name>
    given_names: <given names>
    orcid: <ORCID iD>
    affiliations:
      - name: <institution>
        ror: <ROR ID>
    experiments:
      - <EXPID>
    contact_for:
      - <EXPID>
funding:
  - funder: <funder>
    ror: <ROR ID>
    grant_number: <grant number>
    grant_title: <grant title>
    experiments:
      - <EXPID>
```

How it is written:

- **`people:` and `funding:` appear once each.** Under them, each person and each grant starts with `- `. For another person or grant, repeat the lines from its `- ` down.
- **`affiliations:`, `experiments:` and `contact_for:` are lists too**, with a line that starts with `- ` for each institution or experiment.
- **The indentation shows what belongs to what.** Keep it as in the template, and make it with spaces, never tabs.
- **Each value goes on the same line as its key**, after the `:` and a space. Put a value in double quotes if it holds `: ` or ` #`, or starts with a symbol. Everything after a ` #` that is not in quotes is a comment, which programs skip.

What goes in it:

- **People:** everyone who should be credited for this data. Check with each of them that they agree to be listed with these details.
- **Names:** the family name and the given names apart, as the person writes them. Zenodo and citations need them apart, and no program can split a name reliably.
- **ORCID:** the person's ORCID iD, from [orcid.org](https://orcid.org), without `https://orcid.org/` in front of it. The AI checks each one against its public record.
- **Affiliations:** where the person worked when the work on this data was done, not where they are now: one or more. Write each institution as [ROR](https://ror.org), the registry of research organisations, names it, and its ROR ID without `https://ror.org/` in front of it. Only institutions, not departments. The AI can look up the ROR IDs.
- **Experiments:** the EXPIDs of the experiments, as in the Experiment table, that the person is behind, or that the grant paid for. Every experiment needs at least one person.
- **Contact for:** the EXPIDs of the experiments the person is the contact for. A contact answers questions about the experiment and about using its data, also years from now. Every experiment needs at least one contact, and a contact for an experiment is behind it, so it is under their experiments too. Name more than one where one of them may move on, such as a student together with their supervisor.
- **Funding:** every grant that paid for the work on this data: the funder as ROR names it, its ROR ID, and the grant's number and title.
- **Write `none` where something does not exist:** for a person without given names, an ORCID or an affiliation, a person who is the contact for no experiment, an institution or funder without a ROR ID, a grant without a number or a title, and as `funding: none` when there was no specific funding. Then it can be told from something forgotten.

The validator checks `contributors.yaml` along with the tables, and says what to fix. Give it to the validator with them: in the same folder, or uploaded with them in the app.

> [!NOTE]
> **Without an AI**, your `conversion.py` writes `contributors.yaml` in the same way. With the [collection sheet](#the-collection-sheet), you write it by hand.

## 7. Make the tables

The AI writes `runs/<date>/conversion.py`, which turns `raw_data` into the tables. Every decision is written in it, so that the conversion can be repeated and checked. The AI runs the script and the validator, and keeps the notes, `conversion-notes.md` in the run's folder, as it goes. You can read the notes at any time, in VS Code's [preview](#vs-code).

In practice, steps 6, 7 and 8 go back and forth: making the tables raises new questions, and checking them can show something to fix.

> [!NOTE]
> **Without an AI**, read the [schema](../schema/schema.md) first, and reuse the IDs already used for germplasm, seed lots, traits, climate variables and features in the [known datasets](datasets.md) you have access to.
>
> To write `conversion.py` yourself, follow these sections of the AI's instructions. They are written to the AI, but the rules are the same for you.
>
> - [Write conversion.py](../conversion/AI_INSTRUCTIONS.md#write-conversionpy): what the script reads and writes, the versions it needs, the checksums of the raw files, `summary.md` and `contributors.yaml`.
> - [Check](../conversion/AI_INSTRUCTIONS.md#check): how to run the validator.
> - [The notes](../conversion/AI_INSTRUCTIONS.md#the-notes): what goes in `conversion-notes.md`, with a template.

## 8. Check the result

The AI asks you to check `summary.md`, and says what to compare it with. `conversion.py` writes it each time it runs. It says what the tables hold: the traits and how many scores each has, the units, experiments and germplasm, the dates, and the range of each trait. Compare it with what you know. It could show a wrong number of plots, or a trait with impossible values.

The AI asks you to read `tables/contributors.yaml` too: check every name, ORCID, affiliation, grant and experiment in it.

## 9. Have it reviewed

When the AI says the run is finished, start a fresh session, a new conversation, in the same folder, and type:

```
Read phenotheca/docs/review-data.md and review the latest run.
```

The review checks the work using only the files, and writes `review.md` in the run's folder: what it found, and a FAIR score from 1 to 5. [FAIR](https://www.go-fair.org/fair-principles/) stands for Findable, Accessible, Interoperable and Reusable, principles for data that others can find and use. The score says how well the dataset is described for that, and what would raise it.

The review has to be done by someone other than whoever made the tables, which is why it is a fresh session. If the review found problems, or you want to raise the score, start the AI again with the line from step 5. It fixes what it can, and asks you for the rest. Then start another fresh session for a new review.

> [!NOTE]
> **Without an AI**, ask a colleague to review the run, following [review-data.md](review-data.md). A fresh AI session can do it too, if you may share the data with it. Fix what the review finds, and have it reviewed again.

## 10. Hand over

How to hand over the tables is still to be decided. Until then, keep the folder as it is. This step is yours: the AI never sends data anywhere.

Keep the folder after handing over, too: `raw_data`, the script and the notes are what keep the conversion traceable and reproducible. Corrections or more data after a handover go in a new run, as the [rules of the folder](#the-rules-of-the-folder) say.

## The collection sheet

The collection sheet is no longer the recommended way to contribute data, but it is still allowed. It is separate from the steps above: you fill in the tables by hand, with [schema.md](../schema/schema.md) as a guide, and reuse the IDs already used in the [known datasets](datasets.md) you have access to.

1. Download a blank sheet from the [app](https://phenotheca.github.io/phenotheca/), and fill it in as its *READ ME 1st* sheet says.
2. Write `contributors.yaml` by hand, as in [Who to credit](#who-to-credit), in a plain-text editor such as Notepad, not Word.
3. Check both in the app, uploaded together, and fix what it reports, until they pass.
4. Download the tables from the app (*Download tables as CSV*). `contributors.yaml` comes with them.
5. If you can, have a colleague review the filled-in sheet.
6. Hand over, as in [step 10](#10-hand-over).

## When something goes wrong

- **`uv --version` or `git --version` says the command is not recognized, or not found.** Close VS Code, open it again, and try once more in a new terminal. If it still fails, install it again, as in [step 2](#2-install-what-you-need).
- **The AI says that uv does not work.** Do the same, and then start the AI again with the line from [step 5](#5-open-the-folder-in-your-ai-tool).
- **The AI cannot find `AI_INSTRUCTIONS.md`.** Check that VS Code has the contribution folder open, and that the copy of this repository is in it as `phenotheca`, as in [step 4](#4-set-up-the-folder).
- **VS Code cannot save a file in `raw_data/notes`.** The file is read-only: make it writable, save it, and make it read-only again, as in step 4.
- **The AI says that a file in `raw_data` has changed.** `conversion.py` stops when a file it reads is not as it was. If you corrected the file, tell the AI why. If you didn't, find out what changed it before you go on.
- **The AI tool says you have reached a usage limit.** Come back with the line from step 5 when it lets you. The AI carries on from its notes.
