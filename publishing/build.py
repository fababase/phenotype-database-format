# /// script
# requires-python = "==3.12.*"
# dependencies = [
#     "numpy==2.0.2",
#     "openpyxl==3.1.5",
#     "pandas==2.2.3",
#     "PyYAML==6.0.2",
# ]
# ///
"""
Builds the README of a version of a dataset, and its metadata for Zenodo, from the folder of the version.

Run it in the dataset folder, which holds the copy of this repository and the versions, as docs/publish-data.md lays
it out:

    uv run phenotheca/publishing/build.py Versions/<date>

It reads, in the dataset folder:

    zenodo.yaml        the dataset's title, who may download its files, and who looks after it; and, written by
                       publish.py, its DOI of all versions and the versions uploaded so far

and, in the folder of the version:

    zenodo/<Table>.csv        the merged tables, one file per table of the format, written by merge.py
    zenodo/contributors.yaml  who to credit, written by merge.py
    crosswalk.csv             the IDs that merge.py changed in each contribution
    changes.md                what changed in this version, and why, for the people who use the data

and the folder of the last version, to say what changed since it, which follows from the tables and the crosswalks
of the two. It checks the tables with the validator, and writes README.md in zenodo/ in the folder of the version,
which then holds exactly what goes on Zenodo: the README, the tables and contributors.yaml, and nothing else.

Run on its own, it builds a preview: the date and DOI of a version are only known when publish.py uploads it, and
publish.py then builds the README again with them. A preview never replaces the README of a version that is on
Zenodo.
"""
import argparse
import csv
import html
import re
import subprocess
import sys
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

import pandas as pd
import yaml

HERE = Path(__file__).resolve().parent
REPOSITORY_FOLDER = HERE.parent
sys.path.insert(0, str(REPOSITORY_FOLDER / "app"))
sys.path.insert(0, str(REPOSITORY_FOLDER / "schema"))

from collection_sheet import REPOSITORY, SITE  # noqa: E402
from schema_md import TYPE_NAMES, link, markdown_table  # noqa: E402
from validation import (CONTRIBUTORS_FILE, NONE, Checked, Grant, Person, Schema, TableDef,  # noqa: E402
                        ValidationError, at, joined, load_schema, orcid_problem, read_affiliations, read_yaml,
                        same_version, validate_files, yaml_id, yaml_mapping, yaml_text)

TEMPLATE = HERE / "README_TEMPLATE.md"

# In the dataset folder
ZENODO_FILE = "zenodo.yaml"
VERSIONS = "Versions"
# In the folder of a version
CROSSWALK = "crosswalk.csv"
CHANGES = "changes.md"
# The subfolder that holds exactly what goes on Zenodo: the README, the tables and contributors.yaml
FILES = "zenodo"
README = "README.md"

DATASET_KEYS = ("title", "access")
DATASET_OPTIONAL = ("curator", "doi", "versions")
# Who can download the files of the dataset: anyone, or only those given access on Zenodo
ACCESS = ("open", "restricted")
CURATOR_KEYS = ("family_name", "given_names", "orcid", "affiliations")
VERSION_KEYS = ("version", "folder", "id", "date", "format")
CROSSWALK_HEADER = ["Contribution", "Table", "OldID", "NewID"]
DOI = re.compile(r"10\.[0-9]{4,9}/\S+")

# What a preview shows where the date or a DOI of the version will be
NOT_YET = "(set when published)"
# In what changed, the IDs of rows are listed up to this many; beyond it, only their number
LIMIT = 20

# {{name}} in the template, and the names listed in the comment at its top, one per line
PLACEHOLDER = re.compile(r"\{\{(\w+)\}\}")
COMMENT = re.compile(r"<!--.*?-->\n*", re.DOTALL)
LISTED = re.compile(r"^ +\{\{(\w+)\}\}", re.MULTILINE)


class BuildError(ValueError):
    """Raised when what the build reads is missing or does not fit together. The message says what to do."""


# ---------------------------------------------------------------- What it reads

@dataclass
class Version:
    """A version on Zenodo, as zenodo.yaml lists it: a draft, or published."""
    number: int
    folder: str      # the name of its folder in Versions/
    id: str          # the ID of its record on Zenodo
    doi: str | None  # reserved when the draft is made
    date: str        # YYYY-MM-DD, the date it was uploaded, which is its publication date
    format: str      # the version of the format its tables follow


@dataclass
class Dataset:
    """A dataset, from zenodo.yaml in its folder."""
    folder: Path
    title: str
    access: str              # one of ACCESS
    curator: Person | None   # who looks after it, with no experiments
    doi: str | None          # the DOI of all versions; None until the first version is uploaded
    versions: list[Version]  # in order, the first first
    state: str               # the file that holds the DOI and the versions: ZENODO_FILE, or the sandbox's
    text: dict               # zenodo.yaml as plain Python, every value as text, to write it back


@dataclass
class Release:
    """What only publishing settles. publish.py gives it to build()."""
    publication_date: str  # YYYY-MM-DD
    doi: str               # of this version
    concept_doi: str       # of all versions


@dataclass
class Previous:
    """The last version, as its folder holds it."""
    version: Version
    tables: dict[str, pd.DataFrame]  # by the name of each CSV file, without .csv
    people: list[Person]             # from its contributors.yaml
    funding: list[Grant]
    crosswalk: dict[tuple[str, str, str], str]  # from its crosswalk.csv, as read_crosswalk gives it


@dataclass
class Built:
    """What build() made."""
    dataset: Dataset
    version: int
    readme: str
    metadata: dict   # the record's metadata, as Zenodo takes it
    lines: list[str]  # what was built, to print


class Dumper(yaml.SafeDumper):
    """Writes a list under its key indented, as the templates in the guides do, rather than level with it."""

    def increase_indent(self, flow: bool = False, indentless: bool = False):
        return super().increase_indent(flow, False)


def plain(node: yaml.Node):
    """A YAML node as plain Python, with every value as text."""
    if isinstance(node, yaml.MappingNode):
        return {plain(key): plain(value) for key, value in node.value}
    if isinstance(node, yaml.SequenceNode):
        return [plain(item) for item in node.value]
    return node.value


def read_dataset(folder: Path, state: str = ZENODO_FILE) -> Dataset:
    """
    zenodo.yaml in the dataset folder, which says what the dataset is called, who can download its files, and who
    looks after it, if someone does, in the same way as a person in contributors.yaml, without experiments:

        title: <title>
        access: <open, for anyone, or restricted, for only those given access on Zenodo>
        curator:
          family_name: …
          given_names: …
          orcid: …
          affiliations:
            - name: …
              ror: …

    publish.py adds the DOI of all versions and the versions, as read_versions says. With --sandbox, it keeps them in
    another file, state, in the same folder, and leaves zenodo.yaml as it is.
    """
    path = folder / ZENODO_FILE
    if not path.is_file():
        raise BuildError(f"There is no {ZENODO_FILE} in {folder}, the folder above {VERSIONS}. Write the title of "
                         "the dataset and its access in it, as docs/publish-data.md says.")
    try:
        _, root = read_yaml(ZENODO_FILE, path.read_bytes())
        if root is None:
            raise BuildError(f"{ZENODO_FILE} is empty. Write the title of the dataset and its access in it.")
        values = yaml_mapping(ZENODO_FILE, root, DATASET_KEYS, "the file", DATASET_OPTIONAL)
        title = yaml_text(ZENODO_FILE, values["title"], "title")
        access = yaml_text(ZENODO_FILE, values["access"], "access")
        if access not in ACCESS:
            raise BuildError(f"{at(ZENODO_FILE, values['access'])}: '{access}' is not a kind of access. Write open, "
                             "if anyone may download the files, or restricted, if only those given access on Zenodo "
                             "may.")
        curator = None
        if "curator" in values:
            person = yaml_mapping(ZENODO_FILE, values["curator"], CURATOR_KEYS, "the curator")
            curator = Person(yaml_text(ZENODO_FILE, person["family_name"], "family_name"),
                             yaml_text(ZENODO_FILE, person["given_names"], "given_names"),
                             yaml_id(ZENODO_FILE, person["orcid"], "orcid", orcid_problem),
                             read_affiliations(ZENODO_FILE, person["affiliations"]), [], [])
        doi, versions = None, []
        if state == ZENODO_FILE:
            doi, versions = read_versions(ZENODO_FILE, values)
        elif (folder / state).is_file():
            _, found = read_yaml(state, (folder / state).read_bytes())
            if found is not None:
                doi, versions = read_versions(state, yaml_mapping(state, found, (), "the file", ("doi", "versions")))
    except ValidationError as e:
        raise BuildError(str(e)) from None
    return Dataset(folder, title, access, curator, doi, versions, state, plain(root))


def read_versions(source: str, values: dict[str, yaml.Node]) -> tuple[str | None, list[Version]]:
    """
    The DOI of all versions and the versions, as publish.py writes them in the file: doi, and under versions a
    list with, for each, its number, folder, ID on Zenodo, DOI, date and the version of the format.
    """
    doi = None
    if "doi" in values:
        doi = yaml_text(source, values["doi"], "doi")
        if not DOI.fullmatch(doi):
            raise BuildError(f"{at(source, values['doi'])}: '{doi}' is not a DOI, which starts with 10. and a '/'. "
                             "publish.py writes it, so leave it as it was.")
    versions = []
    if "versions" in values:
        node = values["versions"]
        if not isinstance(node, yaml.SequenceNode):
            raise BuildError(f"{at(source, node)}: versions has to be a list, as publish.py writes it.")
        for item in node.value:
            entry = yaml_mapping(source, item, VERSION_KEYS, "a version", ("doi",))
            number = yaml_text(source, entry["version"], "version")
            if not number.isdigit() or int(number) != len(versions) + 1:
                raise BuildError(f"{at(source, entry['version'])}: the versions have to be numbered 1, 2, … in "
                                 "order, as publish.py writes them.")
            versions.append(Version(int(number), yaml_text(source, entry["folder"], "folder"),
                                    yaml_text(source, entry["id"], "id"),
                                    yaml_text(source, entry["doi"], "doi") if "doi" in entry else None,
                                    yaml_text(source, entry["date"], "date"),
                                    yaml_text(source, entry["format"], "format")))
    return doi, versions


def write_dataset(dataset: Dataset) -> None:
    """
    Writes the DOI of all versions and the versions into the dataset's state file: zenodo.yaml, with the rest of it
    as it was, or the sandbox's file, which holds nothing else.
    """
    state = {}
    if dataset.doi:
        state["doi"] = dataset.doi
    state["versions"] = []
    for version in dataset.versions:
        entry = {"version": version.number, "folder": version.folder, "id": version.id}
        if version.doi:
            entry["doi"] = version.doi
        state["versions"].append(entry | {"date": version.date, "format": version.format})
    if dataset.state == ZENODO_FILE:
        state = {key: value for key, value in dataset.text.items() if key not in ("doi", "versions")} | state
    (dataset.folder / dataset.state).write_text(yaml.dump(state, Dumper=Dumper, sort_keys=False, allow_unicode=True,
                                                          width=120), encoding="utf-8", newline="")


def read_csv(path: Path) -> pd.DataFrame:
    """A published table: every value as text, as written, with an empty cell as ''."""
    return pd.read_csv(path, dtype=str, keep_default_na=False, na_filter=False, encoding="utf-8")


def read_previous(dataset: Dataset, version: Version) -> Previous:
    """The version, as its folder holds it: its tables, contributors.yaml and crosswalk."""
    folder = dataset.folder / VERSIONS / version.folder
    if not folder.is_dir():
        raise BuildError(f"There is no folder {folder}, which holds version {version.number}, as {dataset.state} "
                         "says. The folder of a version is kept, as the next version compares with it.")
    tables = {path.stem: read_csv(path) for path in sorted((folder / FILES).glob("*.csv"))}
    if not tables:
        raise BuildError(f"There are no tables in {folder / FILES}, which holds version {version.number}. The folder "
                         "of a version is kept as it was, as the next version compares with it.")
    credit_path = folder / FILES / CONTRIBUTORS_FILE
    if not credit_path.is_file():
        raise BuildError(f"There is no {CONTRIBUTORS_FILE} in {folder / FILES}, which says who made version "
                         f"{version.number}.")
    credit = yaml.load(credit_path.read_text(encoding="utf-8-sig"), Loader=yaml.BaseLoader)

    def text(value: str) -> str | None:
        return None if value == NONE else value

    people = [Person(item["family_name"], text(item["given_names"]), text(item["orcid"]), [], [], [])
              for item in credit["people"]]
    funding = [Grant(item["funder"], text(item["ror"]), text(item["grant_number"]), text(item["grant_title"]), [])
               for item in ([] if credit["funding"] == NONE else credit["funding"])]
    crosswalk = read_crosswalk(folder / CROSSWALK, str(folder / CROSSWALK), tables, "the last version")
    return Previous(version, tables, people, funding, crosswalk)


def read_crosswalk(path: Path, source: str, tables: dict[str, pd.DataFrame],
                   which: str) -> dict[tuple[str, str, str], str]:
    """
    The crosswalk.csv of a merge, which merge.py writes: the IDs it changed in each contribution, as (contribution,
    table, the contribution's ID) -> the ID in the merged tables. Each new ID has to be in tables, the tables that
    the merge made, which messages call which. source names the file in messages.
    """
    if not path.is_file():
        raise BuildError(f"There is no {CROSSWALK} in {path.parent}. merge.py writes it, with one row for each ID it "
                         f"changed in each contribution, and the columns {', '.join(CROSSWALK_HEADER)}. When it "
                         "changed none, it holds only that first row.")
    with path.open(encoding="utf-8-sig", newline="") as f:
        rows = list(csv.reader(f))
    if not rows or rows[0] != CROSSWALK_HEADER:
        raise BuildError(f"{source}: the first row has to be {','.join(CROSSWALK_HEADER)}.")
    ids = {name: set(frame[frame.columns[0]]) for name, frame in tables.items()}
    crosswalk = {}
    for number, row in enumerate(rows[1:], start=2):
        where = f"{source}, row {number}"
        if len(row) != len(CROSSWALK_HEADER):
            raise BuildError(f"{where} has {len(row)} values, not {len(CROSSWALK_HEADER)}.")
        contribution, table, old_id, new_id = row
        if not all(row):
            raise BuildError(f"{where} has an empty value. Each row gives the contribution, the table, the ID in the "
                             "contribution and the ID in the merged tables.")
        if table not in tables:
            raise BuildError(f"{where}: '{table}' is not a table in {which}.")
        if new_id not in ids[table]:
            raise BuildError(f"{where}: '{new_id}' is not a {tables[table].columns[0]} in {which}.")
        if (contribution, table, old_id) in crosswalk:
            raise BuildError(f"{where}: the {tables[table].columns[0]} '{old_id}' of {contribution} is listed twice. "
                             "Keep only one.")
        crosswalk[(contribution, table, old_id)] = new_id
    return crosswalk


def renames_since(last: Previous, crosswalk: dict[tuple[str, str, str], str],
                  new: dict[str, pd.DataFrame]) -> dict[str, dict[str, str]]:
    """
    The IDs of the last version that this merge changed, as table -> old ID -> new ID, sorted by old ID, from the
    crosswalks of the last merge and of this one. A row of a contribution had, in the last version, the ID that the
    last crosswalk gave it, or its own ID if that crosswalk did not change it. Where that ID is gone from the merged
    tables, the ID that this crosswalk gives the row took its place. Several old IDs can become one.

    A row that this crosswalk does not change keeps its own ID. As a merge keeps the IDs of the last version, unless
    it makes two of its rows one, each ID of it that changes is in this crosswalk.
    """
    old_ids = {name: set(frame[frame.columns[0]]) for name, frame in last.tables.items()}
    new_ids = {name: set(frame[frame.columns[0]]) for name, frame in new.items()}
    renames: dict[str, dict[str, str]] = {}
    for (contribution, table, own_id), new_id in crosswalk.items():
        before = last.crosswalk.get((contribution, table, own_id), own_id)
        if before == new_id or before not in old_ids.get(table, set()) or before in new_ids[table]:
            continue
        found = renames.setdefault(table, {})
        if found.get(before, new_id) != new_id:
            raise BuildError(f"By the crosswalks, the {new[table].columns[0]} '{before}' of the last version became "
                             f"both '{found[before]}' and '{new_id}'. An ID can become only one: correct merge.py.")
        found[before] = new_id
    return {table: dict(sorted(found.items())) for table, found in renames.items()}


def repository_commit(repository: Path = REPOSITORY_FOLDER) -> str:
    """The commit that the copy of this repository is at."""
    try:
        result = subprocess.run(["git", "-C", str(repository), "rev-parse", "HEAD"], capture_output=True, text=True,
                                check=True)
    except (OSError, subprocess.CalledProcessError):
        raise BuildError(f"Could not find the commit that the copy of the repository in {repository} is at. It has "
                         "to be a clone made with git, as the README links to that commit.") from None
    return result.stdout.strip()


def published_tables(checked: Checked, folder: Path) -> dict[str, pd.DataFrame]:
    """
    Every table of the format, as its file in the folder holds it, after checking that the file is written as the
    validator writes tables with --out: every column of the table, in the order of the format, and missing values as
    empty cells. So the files that merge.py writes are what is uploaded, byte for byte.
    """
    frames = {}
    for name, table in checked.tables.items():
        if (folder / f"{name}.csv").read_bytes() != table.to_csv().encode("utf-8"):
            raise BuildError(f"{name}.csv in {folder} is not written as the validator writes tables with --out: "
                             f"every column of {name}, in the order of the format, missing values as empty cells, "
                             "and the rows as pandas writes them with to_csv(index=False, lineterminator='\\n'). "
                             "Make merge.py write it so, as the file is uploaded as it is.")
        frames[name] = table.data.mask(table.missing, "").reset_index(drop=True)
    return frames


def read_changes(folder: Path) -> str:
    """
    changes.md in the folder of a version: what changed in it, and why, written for the people who use the data. It
    holds paragraphs and lists, but no headings, as the README puts it under a heading of its own.
    """
    path = folder / CHANGES
    if not path.is_file():
        raise BuildError(f"There is no {CHANGES} in {folder}. Write in it what changed in this version of the dataset, "
                         "and why, for the people who use the data; for the first version, that it is the first.")
    text = path.read_text(encoding="utf-8-sig").strip()
    if not text:
        raise BuildError(f"{CHANGES} in {folder} is empty. Write in it what changed in this version of the dataset, "
                         "and why, for the people who use the data; for the first version, that it is the first.")
    if any(line.startswith("#") for line in text.splitlines()):
        raise BuildError(f"{CHANGES} in {folder} has a heading. Write paragraphs and lists only: the README puts it "
                         "under a heading of its own.")
    return text


# ---------------------------------------------------------------- Writing it out

def md(text: str) -> str:
    """Text from the data, with the characters Markdown would act on escaped, so that it shows as it is."""
    return re.sub(r"([\\`*_\[\]<>])", r"\\\1", text)


def code(text: str) -> str:
    """An ID, as code. IDs never hold a backtick."""
    return f"`{text}`"


def count(n: int, one: str, many: str | None = None) -> str:
    return f"{n:,} {one if n == 1 else many or one + 's'}"


def ids_text(ids: list[str]) -> str:
    """The IDs, or how many rows they are, if they are more than LIMIT."""
    return ", ".join(code(i) for i in ids) if len(ids) <= LIMIT else count(len(ids), "row")


def doi_link(doi: str | None) -> str:
    return f"[{doi}](https://doi.org/{doi})" if doi else NOT_YET


def name_of(person: Person) -> str:
    return f"{person.given_names} {person.family_name}" if person.given_names else person.family_name


def orcid_link(orcid: str | None) -> str:
    return f"[{orcid}](https://orcid.org/{orcid})" if orcid else ""


def ror_link(name: str, ror: str | None) -> str:
    return f"[{md(name)}](https://ror.org/{ror})" if ror else md(name)


def same_person(a: Person, b: Person) -> bool:
    """By ORCID iD if both have one, else by name."""
    if a.orcid and b.orcid:
        return a.orcid == b.orcid
    return (a.family_name, a.given_names) == (b.family_name, b.given_names)


def same_grant(a: Grant, b: Grant) -> bool:
    if a.funder != b.funder:
        return False
    if a.grant_number or b.grant_number:
        return a.grant_number == b.grant_number
    return a.grant_title == b.grant_title


def sentence(text: str) -> str:
    """text, ending with a full stop, unless it ends with one already, or with an ellipsis."""
    return text if text.endswith((".", "…")) else f"{text}."


def years(start: str, end: str) -> list[int]:
    """The years from a start date to an end date, either of which can be empty."""
    if start and end:
        return list(range(int(start[:4]), int(end[:4]) + 1))
    return [int(day[:4]) for day in (start, end) if day]


def span(found: list[int]) -> str:
    found = sorted(set(found))
    if not found:
        return ""
    return str(found[0]) if found[0] == found[-1] else f"{found[0]}–{found[-1]}"


def place(coordinates: str) -> str:
    """GPS coordinates, latitude;longitude, as a link to them on a map."""
    if not coordinates:
        return ""
    latitude, longitude = coordinates.split(";")
    return (f"[{latitude}, {longitude}](https://www.openstreetmap.org/?mlat={latitude}&mlon={longitude}"
            f"#map=15/{latitude}/{longitude})")


def unit_experiments(frames: dict[str, pd.DataFrame]) -> dict[str, str]:
    units = frames["ExperimentalUnit"]
    return dict(zip(units["UNID"], units["EXPID"]))


def at_a_glance(frames: dict[str, pd.DataFrame]) -> list[str]:
    """The size of the dataset, a line each, without Markdown."""
    experiments = frames["Experiment"]
    found = sorted({year for start, end in zip(experiments["StartDate"], experiments["EndDate"])
                    for year in years(start, end)})
    places = {coordinates for coordinates in experiments["GPSCoordinates"] if coordinates}
    where = f", at {count(len(places), 'place')}" if places else ""
    run = ""
    if found:
        run = f", run in {found[0]}" if found[0] == found[-1] else f", run from {found[0]} to {found[-1]}"
    species = sorted(set(frames["Germplasm"]["Species"]) - {""})
    lines = [count(len(experiments), "experiment") + where + run]
    if species:
        lines.append(f"{count(len(species), 'species', 'species')}: {', '.join(species)}")
    return lines + [
        f"{count(len(frames['Germplasm']), 'germplasm', 'germplasm')}, in {count(len(frames['SeedLot']), 'seed lot')}",
        count(len(frames["ExperimentalUnit"]), "unit"),
        f"{count(len(frames['PhenotypeDescription']), 'trait')}, with {count(len(frames['Phenotype']), 'score')}",
    ]


def first_sentence(text: str, limit: int = 120) -> str:
    """The first sentence of a description, without its full stop, or the start of it if that is long, in one line."""
    end = re.search(r"\.(\s|$)", text)
    first = " ".join((text[:end.start()] if end else text).split())
    if len(first) > limit:
        first = first[:limit].rsplit(" ", 1)[0] + "…"
    return first


def experiments_table(frames: dict[str, pd.DataFrame]) -> str:
    units = frames["ExperimentalUnit"]
    germplasm = dict(zip(frames["SeedLot"]["SLID"], frames["SeedLot"]["GPID"]))
    scores = frames["Phenotype"]
    traits = scores["PDID"].groupby(scores["UNID"].map(unit_experiments(frames))).nunique()
    rows = [["Experiment", "Description", "Years", "Place", "Units", "Germplasm", "Traits"]]
    for experiment in frames["Experiment"].itertuples(index=False):
        own = units[units["EXPID"] == experiment.EXPID]
        rows.append([code(experiment.EXPID), md(first_sentence(experiment.Description)),
                     span(years(experiment.StartDate, experiment.EndDate)), place(experiment.GPSCoordinates),
                     f"{len(own):,}", f"{own['SLID'].map(germplasm).nunique():,}",
                     f"{traits.get(experiment.EXPID, 0):,}"])
    return markdown_table(rows)


def traits_by_experiment(frames: dict[str, pd.DataFrame]) -> str:
    """Each experiment with the PDIDs of the traits scored in it, one line each."""
    scores = frames["Phenotype"]
    found = scores.groupby(scores["UNID"].map(unit_experiments(frames)))["PDID"].agg(set)
    lines = []
    for expid in frames["Experiment"]["EXPID"]:
        pdids = sorted(found.get(expid, set()), key=str.casefold)
        lines.append(f"- {code(expid)}: {', '.join(code(pdid) for pdid in pdids) if pdids else 'no scores'}")
    return "\n".join(lines)


def measured_table(descriptions: pd.DataFrame, key: str, name: str, values: pd.DataFrame, experiments: pd.Series,
                   header: list[str]) -> str:
    """
    The traits or climate variables, by name: each with its ID, name, unit and group, and the number of values and
    of experiments that have them. experiments gives the experiment of each row of values.
    """
    numbers = values[key].value_counts()
    spread = experiments.groupby(values[key]).nunique()
    order = sorted(range(len(descriptions)),
                   key=lambda i: (descriptions[name].iat[i].casefold(), descriptions[key].iat[i]))
    rows = [header]
    for i in order:
        row = descriptions.iloc[i]
        rows.append([code(row[key]), md(row[name]), md(row["Unit"]), md(row["Grouping"]),
                     f"{numbers.get(row[key], 0):,}", f"{spread.get(row[key], 0):,}"])
    return markdown_table(rows)


def traits_table(frames: dict[str, pd.DataFrame]) -> str:
    scores = frames["Phenotype"]
    return measured_table(frames["PhenotypeDescription"], "PDID", "PhenotypeDescription", scores,
                          scores["UNID"].map(unit_experiments(frames)),
                          ["PDID", "Trait", "Unit", "Class", "Scores", "Experiments"])


def climate_table(frames: dict[str, pd.DataFrame]) -> str:
    if frames["ClimateDescription"].empty:
        return "There are no climate data in this dataset."
    climate = frames["Climate"]
    return measured_table(frames["ClimateDescription"], "CDID", "Name", climate, climate["EXPID"],
                          ["CDID", "Variable", "Unit", "Group", "Measurements", "Experiments"])


def files_table(frames: dict[str, pd.DataFrame], schema: Schema) -> str:
    return markdown_table([["File", "One row is", "Rows"]] + [
        [f"[`{name}.csv`](#{name.lower()})", table.one_row_is, f"{len(frames[name]):,}"]
        for name, table in schema.tables.items()])


def tables_section(schema: Schema) -> str:
    """Every table, under a heading of its own, with its columns."""
    parts = []
    for table in schema.tables.values():
        rows = [["Column", "Type", "Always filled in", "Links to", "Description"]]
        for column in table.columns.values():
            links = link(column.links_to) if column.links_to else ""
            description = column.description
            if column.type == "features":
                links = link("Features")
                description += " See [Features cells](#features-cells)."
            rows.append([column.name, TYPE_NAMES[column.type], "Yes" if column.required else "No", links,
                         description])
        parts.append(f"### {table.name}\n\n`{table.name}.csv`: one row is {sentence(table.one_row_is)}\n\n"
                     f"{markdown_table(rows)}")
    return "\n\n".join(parts)


def person_text(person: Person) -> str:
    """A person by name, with their institutions and ORCID iD in brackets, if they have any."""
    details = [ror_link(a.name, a.ror) for a in person.affiliations]
    if person.orcid:
        details.append(f"ORCID {orcid_link(person.orcid)}")
    return md(name_of(person)) + (f" ({'; '.join(details)})" if details else "")


def curator_sentence(curator: Person | None) -> str:
    """Who looks after the dataset, as a sentence, or nothing if no one is named."""
    return f"The dataset is looked after by {person_text(curator)}." if curator else ""


def contacts_list(frames: dict[str, pd.DataFrame], people: list[Person]) -> str:
    """Each experiment with its contacts, one line each. The validator sees to it that every experiment has one."""
    lines = []
    for expid in frames["Experiment"]["EXPID"]:
        contacts = [person_text(person) for person in people if expid in person.contact_for]
        lines.append(f"- {code(expid)}: {joined(contacts)}")
    return "\n".join(lines)


def citation(people: list[Person], year: str, title: str, version: int, doi: str | None) -> str:
    """How to cite this version, in the style of APA, as Zenodo cites it."""
    def initials(given: str) -> str:
        return " ".join("-".join(f"{piece[0]}." for piece in part.split("-") if piece) for part in given.split())

    names = [f"{p.family_name}, {initials(p.given_names)}" if p.given_names else p.family_name for p in people]
    if len(names) == 1:
        authors = names[0]
    elif len(names) <= 20:
        authors = ", ".join(names[:-1]) + ", & " + names[-1]
    else:
        authors = ", ".join(names[:19]) + ", . . . " + names[-1]
    address = f"https://doi.org/{doi}" if doi else NOT_YET
    return f"> {md(authors)} ({year}). *{md(title)}* (Version {version}) [Data set]. Zenodo. {address}"


# ---------------------------------------------------------------- What changed

@dataclass
class TableChanges:
    added: list[str]               # IDs
    changed: dict[str, list[str]]  # column -> IDs of the rows whose value in it changed
    changed_rows: int
    renamed: list[tuple[str, str]]  # old ID, new ID
    removed: list[str]             # IDs
    new_columns: list[str]
    gone_columns: list[str]

    def any(self) -> bool:
        return bool(self.added or self.changed or self.renamed or self.removed or self.new_columns
                    or self.gone_columns)


def rename_links(definition: TableDef, frame: pd.DataFrame, renames: dict[str, dict[str, str]]) -> pd.DataFrame:
    """The rows of the last version, with the IDs of other rows that they hold renamed as this merge renamed them."""
    frame = frame.copy()
    features = renames.get("Features", {})

    def rename_features(cell: str) -> str:
        pairs = [pair.partition("=") for pair in cell.split(";")] if cell else []
        return ";".join(features.get(ftid, ftid) + equals + value for ftid, equals, value in pairs)

    for column in definition.columns.values():
        if column.name not in frame.columns:
            continue
        if column.links_to and renames.get(column.links_to):
            mapping = renames[column.links_to]
            frame[column.name] = frame[column.name].map(lambda value: mapping.get(value, value))
        elif column.type == "features" and features:
            frame[column.name] = frame[column.name].map(rename_features)
    return frame


def table_changes(definition: TableDef, old: pd.DataFrame, new: pd.DataFrame,
                  renames: dict[str, dict[str, str]]) -> TableChanges:
    """
    How a table changed since the last version. A renamed row is compared with the row it became, if that is new,
    and links to renamed rows are followed, so that renaming a row does not change the rows that link to it.
    """
    key = definition.id_column
    own = renames.get(definition.name, {})
    old = rename_links(definition, old, renames)
    old_ids = set(old[key])
    became = {}  # new ID -> the old ID renamed to it, where the new ID was not in the last version
    for old_id, new_id in own.items():
        if new_id not in old_ids:
            became.setdefault(new_id, old_id)
    pairs = [(i if i in old_ids else became[i], i) for i in new[key] if i in old_ids or i in became]
    columns = [column for column in definition.columns if column != key and column in old.columns]
    changed = {}
    changed_rows = 0
    if pairs and columns:
        before = old.set_index(key).loc[[old_id for old_id, _ in pairs], columns].reset_index(drop=True)
        after = new.set_index(key).loc[[new_id for _, new_id in pairs], columns].reset_index(drop=True)
        differs = before.ne(after)
        for column in columns:
            ids = [pairs[i][1] for i in differs.index[differs[column]]]
            if ids:
                changed[column] = ids
        changed_rows = int(differs.any(axis=1).sum())
    targets = set(own.values())
    new_ids = set(new[key])
    return TableChanges(
        added=[i for i in new[key] if i not in old_ids and i not in targets],
        changed=changed,
        changed_rows=changed_rows,
        renamed=list(own.items()),
        removed=[i for i in old[key] if i not in new_ids and i not in own],
        new_columns=[column for column in definition.columns if column not in old.columns],
        gone_columns=[column for column in old.columns if column not in definition.columns],
    )


def changes_text(last: Previous | None, frames: dict[str, pd.DataFrame], schema: Schema,
                 renames: dict[str, dict[str, str]], people: list[Person], funding: list[Grant], diagram: str) -> str:
    """What changed since the last version: in the format, in each table, and in who made it. Nothing for the
    first version."""
    if last is None:
        return ""
    parts = [f"Compared with version {last.version.number}, published {last.version.date}: "
             f"{doi_link(last.version.doi)}."]
    if not same_version(last.version.format, schema.version):
        parts.append(f"The format changed from version {last.version.format} to version {schema.version}. The "
                     f"[diagram]({diagram}) shows each version: choose one in its menu.")

    summary = [["Table", "Added", "Changed", "Renamed", "Removed"]]
    details = []
    for name, definition in schema.tables.items():
        new_table = name not in last.tables
        old = (pd.DataFrame({column: pd.Series(dtype=str) for column in definition.columns}) if new_table
               else last.tables[name])
        found = table_changes(definition, old, frames[name], renames)
        if not found.any() and not new_table:
            continue
        summary.append([name, f"{len(found.added):,}", f"{found.changed_rows:,}", f"{len(found.renamed):,}",
                        f"{len(found.removed):,}"])
        items = ["The table is new in this version of the format."] if new_table else []
        if found.new_columns:
            items.append(f"New columns: {', '.join(found.new_columns)}.")
        if found.gone_columns:
            items.append(f"Columns no longer in the format: {', '.join(found.gone_columns)}.")
        if found.added:
            items.append(f"Added: {ids_text(found.added)}.")
        if found.changed:
            items.append("Changed: " + "; ".join(f"{column} in {ids_text(ids)}"
                                                 for column, ids in found.changed.items()) + ".")
        if found.renamed:
            items.append("Renamed: " + ", ".join(f"{code(old_id)} to {code(new_id)}"
                                                 for old_id, new_id in found.renamed) + ".")
        if found.removed:
            items.append(f"Removed: {ids_text(found.removed)}.")
        details.append(f"- **{name}.** {' '.join(items)}")
    for name in last.tables:
        if name not in schema.tables:
            details.append(f"- **{name}.** The table is no longer in the format, so its "
                           f"{count(len(last.tables[name]), 'row')} are not in this version.")

    if len(summary) == 1 and not details:
        parts.append("The tables did not change.")
    else:
        parts.append(markdown_table(summary) if len(summary) > 1 else "")
        parts.append("\n".join(details))

    credit = []
    for what, new_items, old_items, same, show in [
            ("People", people, last.people, same_person, lambda p: md(name_of(p))),
            ("Funding", funding, last.funding, same_grant, grant_name)]:
        added = [show(item) for item in new_items if not any(same(item, other) for other in old_items)]
        removed = [show(item) for item in old_items if not any(same(item, other) for other in new_items)]
        said = [f"Added: {'; '.join(added)}."] if added else []
        said += [f"Removed: {'; '.join(removed)}."] if removed else []
        if said:
            credit.append(f"**{what}.** {' '.join(said)}")
    parts += credit
    return "\n\n".join(part for part in parts if part)


def grant_name(grant: Grant) -> str:
    if grant.grant_number:
        return f"{md(grant.funder)}, grant {md(grant.grant_number)}"
    if grant.grant_title:
        return f"{md(grant.funder)}: {md(grant.grant_title)}"
    return md(grant.funder)


# ---------------------------------------------------------------- The README and the metadata

def render(template: str, values: dict[str, str]) -> str:
    """
    The template with each {{name}} replaced by its value, and its comments left out. The names used in it, those
    listed in the comment at its top and those given have to be the same.
    """
    comments = COMMENT.findall(template)
    listed = set(LISTED.findall(comments[0])) if comments else set()
    body = COMMENT.sub("", template).lstrip("\n")
    used = set(PLACEHOLDER.findall(body))
    problems = ([f"it uses {{{{{name}}}}}, which the list at its top does not name" for name in sorted(used - listed)]
                + [f"its list at the top names {{{{{name}}}}}, which it does not use" for name in sorted(listed - used)]
                + [f"it uses {{{{{name}}}}}, which build.py does not fill in" for name in sorted(used - set(values))]
                + [f"build.py fills in {{{{{name}}}}}, which it does not use" for name in sorted(set(values) - used)])
    if problems:
        raise BuildError(f"{TEMPLATE.name}: {'; '.join(problems)}.")
    return PLACEHOLDER.sub(lambda match: values[match[1]], body).rstrip("\n") + "\n"


def inline_html(text: str) -> str:
    """A line of Markdown as HTML: links, bold and code, with everything else escaped."""
    text = html.escape(text, quote=False)
    text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2">\1</a>', text)
    text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
    return re.sub(r"`([^`]+)`", r"<code>\1</code>", text)


def description_html(readme: str, glance: list[str], schema: Schema, diagram: str) -> str:
    """The description on the record's page: the first paragraph of the README, the dataset at a glance, and where
    the rest is."""
    intro = re.match(r"# [^\n]*\n\n(.+?)\n\n", readme, re.DOTALL)
    lines = [f"<p>{inline_html(intro[1])}</p>"] if intro else []
    lines += ["<ul>"] + [f"<li>{html.escape(item)}</li>" for item in glance] + ["</ul>"]
    lines.append(f'<p>The tables follow version {schema.version} of the Phenotheca format, whose '
                 f'<a href="{diagram}">diagram</a> shows how they link. {README} says how to read and join them.</p>')
    return "\n".join(lines)


def creator(person: Person) -> dict:
    """A person, as Zenodo's metadata has them."""
    name = {"type": "personal", "family_name": person.family_name}
    if person.given_names:
        name["given_name"] = person.given_names
    if person.orcid:
        name["identifiers"] = [{"scheme": "orcid", "identifier": person.orcid}]
    entry = {"person_or_org": name}
    if person.affiliations:
        entry["affiliations"] = [{"id": a.ror} if a.ror else {"name": a.name} for a in person.affiliations]
    return entry


def metadata(dataset: Dataset, version: int, release: Release | None, people: list[Person], funding: list[Grant],
             frames: dict[str, pd.DataFrame], description: str, commit: str) -> dict:
    """
    The record's metadata, as Zenodo takes it. Everyone in contributors.yaml is a creator, and the curator, if
    there is one, is a contributor, unless they are a creator already.
    """
    data = {"resource_type": {"id": "dataset"}, "title": dataset.title, "creators": [creator(p) for p in people]}
    if dataset.curator and not any(same_person(dataset.curator, person) for person in people):
        data["contributors"] = [creator(dataset.curator) | {"role": {"id": "datacurator"}}]
    if release:
        data["publication_date"] = release.publication_date
    data |= {"version": str(version), "description": description, "publisher": "Zenodo",
             "rights": [{"id": "cc-by-4.0"}], "languages": [{"id": "eng"}]}

    species = sorted(set(frames["Germplasm"]["Species"]) - {""})
    if species:
        data["subjects"] = [{"subject": name} for name in species]
    experiments = frames["Experiment"]
    dates = sorted((set(experiments["StartDate"]) | set(experiments["EndDate"])) - {""})
    if dates:
        data["dates"] = [{"date": dates[0] if dates[0] == dates[-1] else f"{dates[0]}/{dates[-1]}",
                          "type": {"id": "collected"}}]
    located = experiments[experiments["GPSCoordinates"] != ""]
    if not located.empty:
        data["locations"] = {"features": [
            {"geometry": {"type": "Point",
                          "coordinates": [float(c) for c in reversed(coordinates.split(";"))]},
             "place": expid}
            for expid, coordinates in zip(located["EXPID"], located["GPSCoordinates"])]}
    if funding:
        grants = []
        for grant in funding:
            entry = {"funder": {"id": grant.ror} if grant.ror else {"name": grant.funder}}
            if grant.grant_number and grant.grant_title:
                entry["award"] = {"number": grant.grant_number, "title": {"en": grant.grant_title}}
            grants.append(entry)
        data["funding"] = grants
    data["related_identifiers"] = [{"identifier": f"{REPOSITORY}/tree/{commit}", "scheme": "url",
                                    "relation_type": {"id": "isdocumentedby"}, "resource_type": {"id": "software"}}]
    return data


# ---------------------------------------------------------------- Building

def build(folder: Path, commit: str, release: Release | None = None, state: str = ZENODO_FILE,
          notice: Callable[[str], None] = lambda message: None,
          warning: Callable[[str], None] = lambda message: None, out: Path | None = None) -> Built:
    """
    Builds README.md in the folder of a version, and returns what it built.
    Parameters:
        folder: the folder of the version, Versions/<date> in the dataset folder.
        commit: the commit that the copy of this repository is at.
        release: the date and DOIs of the version, which publish.py gives; None for a preview.
        state: the file in the dataset folder that lists the versions: zenodo.yaml, or the sandbox's.
        notice, warning: called with the validator's notices and warnings.
        out: the folder to write README.md in, in place of the version's zenodo/; publish.py builds in another one
            first, as a check.
    Raises:
        ValidationError: if the tables or contributors.yaml do not pass the validator.
        BuildError: if something else is missing or does not fit together.
    """
    schema = load_schema()
    folder = folder.resolve()
    if folder.parent.name != VERSIONS:
        raise BuildError(f"{folder} is not a folder in {VERSIONS}. A version is built from {VERSIONS}/<date> in the "
                         "dataset folder, as docs/publish-data.md lays it out.")
    dataset = read_dataset(folder.parent.parent, state)
    this = next((version for version in dataset.versions if version.folder == folder.name), None)
    if this and not release and out is None:
        raise BuildError(f"Version {this.number}, in {folder}, is on Zenodo, as {dataset.state} says, so a preview "
                         "would replace the README that was uploaded. Build a new version in a new folder, or run "
                         "publish.py, which builds the README with the version's date and DOI.")
    earlier = [version for version in dataset.versions if this is None or version.number < this.number]
    number = this.number if this else (earlier[-1].number + 1 if earlier else 1)
    last = read_previous(dataset, earlier[-1]) if earlier else None
    if release and dataset.doi and release.concept_doi != dataset.doi:
        raise BuildError(f"The DOI of all versions is {release.concept_doi} on Zenodo, but {dataset.doi} in "
                         f"{dataset.state}.")

    files_folder = folder / FILES
    if not files_folder.is_dir():
        raise BuildError(f"There is no {FILES} folder in {folder}. merge.py writes the tables and "
                         f"{CONTRIBUTORS_FILE} in it, and build.py the README: it holds exactly what goes on Zenodo.")
    missing = [name for name in schema.tables if not (files_folder / f"{name}.csv").is_file()]
    if missing:
        raise BuildError(f"There is no {missing[0]}.csv in {files_folder}. merge.py writes every table of the format "
                         "there, a table without rows as a file with only the column names.")
    files = [(f"{name}.csv", files_folder / f"{name}.csv") for name in schema.tables]
    if (files_folder / CONTRIBUTORS_FILE).is_file():
        files.append((CONTRIBUTORS_FILE, files_folder / CONTRIBUTORS_FILE))
    checked = validate_files(files, schema, notice, warning)
    if checked.contributors is None:
        raise BuildError(f"There is no {CONTRIBUTORS_FILE} in {files_folder}. merge.py writes it there, with who to "
                         "credit.")
    frames = published_tables(checked, files_folder)
    people = sorted(checked.contributors.people,
                    key=lambda p: (p.family_name.casefold(), (p.given_names or "").casefold()))
    funding = checked.contributors.funding
    crosswalk = read_crosswalk(folder / CROSSWALK, CROSSWALK, frames, "the merged tables")
    renames = renames_since(last, crosswalk, frames) if last else {}
    changes = read_changes(folder)

    diagram = f"{SITE}diagram/#{schema.version}"
    glance = at_a_glance(frames)
    values = {
        "title": md(dataset.title),
        "version": str(number),
        "publication_date": release.publication_date if release else NOT_YET,
        "doi": doi_link(release.doi if release else None),
        "concept_doi": doi_link(release.concept_doi if release else dataset.doi),
        "schema_version": schema.version,
        "diagram": diagram,
        "repository": f"[{REPOSITORY}]({REPOSITORY}/tree/{commit})",
        "at_a_glance": "\n".join(f"- {md(item)}" for item in glance),
        "experiments": experiments_table(frames),
        "traits": traits_table(frames),
        "traits_by_experiment": traits_by_experiment(frames),
        "climate_variables": climate_table(frames),
        "files": files_table(frames, schema),
        "tables": tables_section(schema),
        "changes": "\n\n".join(part for part in (
            changes, changes_text(last, frames, schema, renames, people, funding, diagram)) if part),
        "contacts": contacts_list(frames, people),
        "curator": curator_sentence(dataset.curator),
        "citation": citation(people, release.publication_date[:4] if release else NOT_YET.strip("()"),
                             dataset.title, number, release.doi if release else None),
    }
    readme = render(TEMPLATE.read_text(encoding="utf-8"), values)
    description = description_html(readme, glance, schema, diagram)
    data = metadata(dataset, number, release, people, funding, frames, description, commit)

    where = out or files_folder
    where.mkdir(parents=True, exist_ok=True)
    (where / README).write_text(readme, encoding="utf-8", newline="")
    lines = [f"Built version {number} of {dataset.title}, in schema version {schema.version}: {where / README}.",
             f"Compared with version {last.version.number}." if last else "It is the first version."]
    if not release:
        lines.append("It is a preview: the date and DOI of the version are set when publish.py uploads it.")
    return Built(dataset, number, readme, data, lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build the README of a version of a dataset, from its folder, as a "
                                                 "preview.")
    parser.add_argument("folder", type=Path, help=f"the folder of the version: {VERSIONS}/<date> in the dataset folder")
    args = parser.parse_args(argv)
    try:
        built = build(args.folder, repository_commit(),
                      notice=lambda message: print(f"Notice: {message}"),
                      warning=lambda message: print(f"Warning: {message}"))
    except ValidationError as e:
        print(f"Validation failed: {e}")
        return 1
    except BuildError as e:
        print(f"Stopped: {e}")
        return 1
    print("\n".join(built.lines))
    return 0


if __name__ == "__main__":
    sys.exit(main())
