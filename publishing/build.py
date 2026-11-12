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
Builds what goes to Zenodo from a merge: the tables, their README, and the record's metadata.

Run it in the merge folder, which holds the copy of this repository:

    uv run phenotype-database-format/publishing/build.py [--previous <folder of the last merge>]

It reads, in the merge folder:

    tables/        the merged tables and contributors.yaml, written by merge.py
    record.yaml    the dataset's title, its DOI of all versions, and who looks after it
    renames.csv    the IDs of the last version that this merge changed, written by merge.py; only with --previous

and, with --previous, the last merge's publish/ folder and tables/contributors.yaml, to say what changed since the
version it published. It checks the tables with the validator, and writes publish/ in the merge folder:

    files/         README.md and one CSV file per table: exactly what is uploaded
    metadata.json  the metadata of the record on Zenodo
    release.json   the number, date and DOIs of the version, and the version of the format and the commit of the
                   repository it was built with. The next merge reads it, with --previous.

publish.py keeps zenodo.json in publish/ too, which build.py leaves as it is.

Run on its own, it builds a preview: the date and DOI of a version are only known when publish.py publishes it, and
publish.py then builds it again with them. A preview never replaces a publish/ folder that has a DOI.
"""
import argparse
import csv
import html
import json
import re
import shutil
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
                        ValidationError, at, load_schema, orcid_problem, read_affiliations, read_yaml, validate_files,
                        yaml_id, yaml_mapping, yaml_text)

TEMPLATE = HERE / "README_TEMPLATE.md"

# In the merge folder
TABLES = "tables"
RECORD = "record.yaml"
RENAMES = "renames.csv"
PUBLISH = "publish"
# In publish/
FILES = "files"
README = "README.md"
METADATA = "metadata.json"
RELEASE = "release.json"

RECORD_KEYS = ("title", "doi", "access", "curator")
# Who can download the files of the dataset: anyone, or only those given access on Zenodo
ACCESS = ("open", "restricted")
CURATOR_KEYS = ("family_name", "given_names", "orcid", "affiliations")
RENAMES_HEADER = ["Table", "OldID", "NewID"]
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
class Record:
    """The dataset, from record.yaml."""
    title: str
    doi: str | None  # the DOI of all versions; None until the first version is published
    access: str      # one of ACCESS
    curator: Person  # who looks after the dataset, with no experiments


@dataclass
class Release:
    """What only publishing settles. publish.py gives it to build()."""
    publication_date: str  # YYYY-MM-DD
    doi: str               # of this version
    concept_doi: str       # of all versions


@dataclass
class Previous:
    """The last version, as the last merge published it."""
    version: int
    publication_date: str
    doi: str
    concept_doi: str
    schema_version: str
    tables: dict[str, pd.DataFrame]  # by the name of each CSV file, without .csv
    people: list[Person]             # from its contributors.yaml
    funding: list[Grant]


def read_record(path: Path) -> Record:
    """
    record.yaml, which says what the dataset is called, its DOI of all versions, who can download its files, and who
    looks after it, in the same way as a person in contributors.yaml, without experiments:

        title: <title>
        doi: <DOI of all versions, or none before the first version is published>
        access: <open, for anyone, or restricted, for only those given access on Zenodo>
        curator:
          family_name: …
          given_names: …
          orcid: …
          affiliations:
            - name: …
              ror: …
    """
    if not path.is_file():
        raise BuildError(f"There is no {RECORD} in {path.parent}. Copy it from the last merge, or write it for the "
                         "first version: see the docstring of read_record in publishing/build.py.")
    try:
        _, root = read_yaml(RECORD, path.read_bytes())
        if root is None:
            raise BuildError(f"{RECORD} is empty. Write the title, the DOI and the curator in it.")
        values = yaml_mapping(RECORD, root, RECORD_KEYS, "the file")
        title = yaml_text(RECORD, values["title"], "title")
        node = values["doi"]
        doi = None
        if not (isinstance(node, yaml.ScalarNode) and node.value == NONE):
            doi = yaml_text(RECORD, node, "doi")
            if not DOI.fullmatch(doi):
                raise BuildError(f"{at(RECORD, node)}: '{doi}' is not a DOI, which starts with 10. and a '/'. Write "
                                 "it without https://doi.org/ in front, or write none before the first version is "
                                 "published.")
        access = yaml_text(RECORD, values["access"], "access")
        if access not in ACCESS:
            raise BuildError(f"{at(RECORD, values['access'])}: '{access}' is not a kind of access. Write open, if "
                             "anyone may download the files, or restricted, if only those given access on Zenodo may.")
        person = yaml_mapping(RECORD, values["curator"], CURATOR_KEYS, "the curator")
        curator = Person(yaml_text(RECORD, person["family_name"], "family_name"),
                         yaml_text(RECORD, person["given_names"], "given_names"),
                         yaml_id(RECORD, person["orcid"], "orcid", orcid_problem),
                         read_affiliations(RECORD, person["affiliations"]), [])
    except ValidationError as e:
        raise BuildError(str(e)) from None
    return Record(title, doi, access, curator)


def read_csv(path: Path) -> pd.DataFrame:
    """A published table: every value as text, as written, with an empty cell as ''."""
    return pd.read_csv(path, dtype=str, keep_default_na=False, na_filter=False, encoding="utf-8")


def read_previous(folder: Path) -> Previous:
    """The version that the merge in folder published: its release.json, tables and contributors.yaml."""
    release_path = folder / PUBLISH / RELEASE
    if not release_path.is_file():
        raise BuildError(f"{folder} has no {PUBLISH}/{RELEASE}, so it is not a merge that was published. Give "
                         "the folder of the merge that was published as the last version.")
    release = json.loads(release_path.read_text(encoding="utf-8"))
    if not release["doi"] or not release["publication_date"]:
        raise BuildError(f"The merge in {folder} was not published: {PUBLISH}/{RELEASE} has no DOI or date. Give "
                         "the folder of the merge that was published as the last version.")
    tables = {path.stem: read_csv(path) for path in sorted((folder / PUBLISH / FILES).glob("*.csv"))}
    credit_path = folder / TABLES / CONTRIBUTORS_FILE
    if not credit_path.is_file():
        raise BuildError(f"The last merge, in {folder}, has no {TABLES}/{CONTRIBUTORS_FILE}, which says who made the "
                         "last version.")
    credit = yaml.load(credit_path.read_text(encoding="utf-8-sig"), Loader=yaml.BaseLoader)

    def text(value: str) -> str | None:
        return None if value == NONE else value

    people = [Person(item["family_name"], text(item["given_names"]), text(item["orcid"]), [], [])
              for item in credit["people"]]
    funding = [Grant(item["funder"], text(item["ror"]), text(item["grant_number"]), text(item["grant_title"]), [])
               for item in ([] if credit["funding"] == NONE else credit["funding"])]
    return Previous(release["version"], release["publication_date"], release["doi"], release["concept_doi"],
                    release["schema_version"], tables, people, funding)


def read_renames(path: Path, schema: Schema, old: dict[str, pd.DataFrame],
                 new: dict[str, pd.DataFrame]) -> dict[str, dict[str, str]]:
    """
    renames.csv: the IDs of the last version that this merge changed, as table -> old ID -> new ID. Each old ID is in
    the last version and not in the new one, and each new ID is in the new one. Several old IDs can become one.
    """
    if not path.is_file():
        raise BuildError(f"There is no {RENAMES} in {path.parent}. merge.py writes it, with one row for each ID of "
                         f"the last version that this merge changed, and the columns {', '.join(RENAMES_HEADER)}. "
                         "When it changed none, it holds only that first row.")
    with path.open(encoding="utf-8-sig", newline="") as f:
        rows = list(csv.reader(f))
    if not rows or rows[0] != RENAMES_HEADER:
        raise BuildError(f"{RENAMES}: the first row has to be {','.join(RENAMES_HEADER)}.")
    renames: dict[str, dict[str, str]] = {}
    for number, row in enumerate(rows[1:], start=2):
        where = f"{RENAMES}, row {number}"
        if len(row) != len(RENAMES_HEADER):
            raise BuildError(f"{where} has {len(row)} values, not {len(RENAMES_HEADER)}.")
        table, old_id, new_id = row
        if table not in schema.tables:
            raise BuildError(f"{where}: '{table}' is not a table of the format.")
        column = schema.tables[table].id_column
        if table not in old or old_id not in set(old[table][column]):
            raise BuildError(f"{where}: '{old_id}' is not a {column} in the last version.")
        if old_id in set(new[table][column]):
            raise BuildError(f"{where}: '{old_id}' is still a {column} in the merged tables, so it did not change.")
        if new_id not in set(new[table][column]):
            raise BuildError(f"{where}: '{new_id}' is not a {column} in the merged tables.")
        if old_id in renames.setdefault(table, {}):
            raise BuildError(f"{where}: '{old_id}' is listed twice. Keep only one.")
        renames[table][old_id] = new_id
    return renames


def repository_commit(repository: Path = REPOSITORY_FOLDER) -> str:
    """The commit that the copy of this repository is at."""
    try:
        result = subprocess.run(["git", "-C", str(repository), "rev-parse", "HEAD"], capture_output=True, text=True,
                                check=True)
    except (OSError, subprocess.CalledProcessError):
        raise BuildError(f"Could not find the commit that the copy of the repository in {repository} is at. It has "
                         "to be a clone made with git, as the README links to that commit.") from None
    return result.stdout.strip()


def published_tables(checked: Checked, schema: Schema) -> dict[str, pd.DataFrame]:
    """
    Every table of the format, as it is published: every column, in the schema's order, missing values as empty
    cells, and a table that is not there as one without rows.
    """
    frames = {}
    for name, definition in schema.tables.items():
        if name in checked.tables:
            table = checked.tables[name]
            frames[name] = table.data.mask(table.missing, "").reset_index(drop=True)
        else:
            frames[name] = pd.DataFrame({column: pd.Series(dtype=str) for column in definition.columns})
    return frames


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
    run = ""
    if found:
        run = f", run in {found[0]}" if found[0] == found[-1] else f", run from {found[0]} to {found[-1]}"
    return [
        count(len(experiments), "experiment") + run,
        f"{count(len(frames['Germplasm']), 'germplasm', 'germplasm')}, in {count(len(frames['SeedLot']), 'seed lot')}",
        count(len(frames["ExperimentalUnit"]), "unit"),
        f"{count(len(frames['PhenotypeDescription']), 'trait')}, with {count(len(frames['Phenotype']), 'score')}",
    ]


def experiments_table(frames: dict[str, pd.DataFrame], people: list[Person]) -> str:
    units = frames["ExperimentalUnit"]
    germplasm = dict(zip(frames["SeedLot"]["SLID"], frames["SeedLot"]["GPID"]))
    scores = frames["Phenotype"]
    traits = scores["PDID"].groupby(scores["UNID"].map(unit_experiments(frames))).nunique()
    rows = [["Experiment", "Years", "Place", "Units", "Germplasm", "Traits", "People"]]
    for experiment in frames["Experiment"].itertuples(index=False):
        own = units[units["EXPID"] == experiment.EXPID]
        rows.append([code(experiment.EXPID), span(years(experiment.StartDate, experiment.EndDate)),
                     place(experiment.GPSCoordinates), f"{len(own):,}", f"{own['SLID'].map(germplasm).nunique():,}",
                     f"{traits.get(experiment.EXPID, 0):,}",
                     ", ".join(md(name_of(person)) for person in people if experiment.EXPID in person.experiments)])
    return markdown_table(rows)


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


def links_table(schema: Schema) -> str:
    rows = [["Column", "Holds the ID of"]]
    for table in schema.tables.values():
        for column in table.columns.values():
            if column.links_to:
                rows.append([code(f"{table.name}.{column.name}"), link(column.links_to)])
            elif column.type == "features":
                rows.append([code(f"{table.name}.{column.name}"),
                             f"{link('Features')}, one or more: see [Features cells](#features-cells)"])
    return markdown_table(rows)


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


def people_table(people: list[Person]) -> str:
    rows = [["Name", "ORCID", "Affiliations", "Experiments"]]
    for person in people:
        rows.append([md(name_of(person)), orcid_link(person.orcid),
                     "; ".join(ror_link(a.name, a.ror) for a in person.affiliations),
                     ", ".join(code(expid) for expid in person.experiments)])
    return markdown_table(rows)


def funding_table(funding: list[Grant]) -> str:
    if not funding:
        return "There was no specific funding."
    rows = [["Funder", "Grant number", "Grant title", "Experiments"]]
    for grant in funding:
        rows.append([ror_link(grant.funder, grant.ror), md(grant.grant_number or ""), md(grant.grant_title or ""),
                     ", ".join(code(expid) for expid in grant.experiments)])
    return markdown_table(rows)


def curator_text(curator: Person) -> str:
    details = [ror_link(a.name, a.ror) for a in curator.affiliations]
    if curator.orcid:
        details.append(f"ORCID {orcid_link(curator.orcid)}")
    return md(name_of(curator)) + (f" ({'; '.join(details)})" if details else "")


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
    """The rows of the last version, with the IDs of other rows that they hold renamed as in renames.csv."""
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
    """What changed since the last version: in the format, in each table, and in who made it."""
    if last is None:
        return "This is the first version."
    parts = [f"Compared with version {last.version}, published {last.publication_date}: {doi_link(last.doi)}."]
    if last.schema_version != schema.version:
        parts.append(f"The format changed from version {last.schema_version} to version {schema.version}. The "
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
    lines.append(f'<p>The tables follow version {schema.version} of the FabaBase phenotype database format, whose '
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


def metadata(record: Record, version: int, release: Release | None, people: list[Person], funding: list[Grant],
             frames: dict[str, pd.DataFrame], description: str, commit: str) -> dict:
    """
    The record's metadata, as Zenodo takes it. Everyone in contributors.yaml is a creator, and the curator is a
    contributor, unless they are a creator already.
    """
    data = {"resource_type": {"id": "dataset"}, "title": record.title, "creators": [creator(p) for p in people]}
    if not any(same_person(record.curator, person) for person in people):
        data["contributors"] = [creator(record.curator) | {"role": {"id": "datacurator"}}]
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


def as_json(data: dict) -> str:
    return json.dumps(data, indent=2, ensure_ascii=False) + "\n"


# ---------------------------------------------------------------- Building

def build(merge: Path, commit: str, previous: Path | None = None, release: Release | None = None,
          notice: Callable[[str], None] = lambda message: None,
          warning: Callable[[str], None] = lambda message: None, out: Path | None = None) -> list[str]:
    """
    Builds publish/ in the merge folder, and returns lines saying what it built.
    Parameters:
        merge: the merge folder.
        commit: the commit that the copy of this repository is at.
        previous: the folder of the last merge, which published the last version; None for the first version.
        release: the date and DOIs of this version, which publish.py gives; None for a preview.
        notice, warning: called with the validator's notices and warnings.
        out: the folder to build in, in place of publish/; publish.py builds in another one first, as a check.
    Raises:
        ValidationError: if the tables or contributors.yaml do not pass the validator.
        BuildError: if something else is missing or does not fit together.
    """
    schema = load_schema()
    record = read_record(merge / RECORD)
    if record.doi and not previous:
        raise BuildError(f"{RECORD} gives the DOI {record.doi}, so the dataset has been published before. Give the "
                         "folder of the merge that published the last version, with --previous.")
    if previous and not record.doi:
        raise BuildError(f"{RECORD} has doi: none, so this would be the first version, but a last merge was given. "
                         "If the dataset has been published, write its DOI of all versions in it.")
    if release and record.doi and release.concept_doi != record.doi:
        raise BuildError(f"The DOI of all versions is {release.concept_doi} on Zenodo, but {record.doi} in "
                         f"{RECORD}.")
    last = read_previous(previous) if previous else None
    if last and last.concept_doi != record.doi:
        raise BuildError(f"The last merge, in {previous}, published a version of {last.concept_doi}, but {RECORD} "
                         f"gives {record.doi}. Give the last merge of this dataset.")

    folder = merge / TABLES
    if not folder.is_dir():
        raise BuildError(f"There is no {TABLES} folder in {merge}. merge.py writes the merged tables in it.")
    files = [(path.name, path) for path in sorted(folder.iterdir())
             if path.suffix.lower() == ".csv" or path.name == CONTRIBUTORS_FILE]
    checked = validate_files(files, schema, notice, warning)
    if checked.contributors is None:
        raise BuildError(f"There is no {CONTRIBUTORS_FILE} in {folder}. merge.py writes it, with who to credit.")
    frames = published_tables(checked, schema)
    people = sorted(checked.contributors.people,
                    key=lambda p: (p.family_name.casefold(), (p.given_names or "").casefold()))
    funding = checked.contributors.funding
    renames = read_renames(merge / RENAMES, schema, last.tables, frames) if last else {}

    out = out or merge / PUBLISH
    if not release and (out / RELEASE).is_file() and json.loads((out / RELEASE).read_text(encoding="utf-8"))["doi"]:
        raise BuildError(f"{out} holds a version with a DOI, which a preview would replace. It is kept as it is, "
                         "as the next merge compares with it. Build a new version in a new merge folder.")

    version = last.version + 1 if last else 1
    concept_doi = release.concept_doi if release else record.doi
    diagram = f"{SITE}diagram/#{schema.version}"
    glance = at_a_glance(frames)
    values = {
        "title": md(record.title),
        "version": str(version),
        "publication_date": release.publication_date if release else NOT_YET,
        "doi": doi_link(release.doi if release else None),
        "concept_doi": doi_link(concept_doi),
        "schema_version": schema.version,
        "diagram": diagram,
        "repository": f"[{REPOSITORY}]({REPOSITORY}/tree/{commit})",
        "at_a_glance": "\n".join(f"- {md(item)}" for item in glance),
        "experiments": experiments_table(frames, people),
        "traits": traits_table(frames),
        "climate_variables": climate_table(frames),
        "files": files_table(frames, schema),
        "links": links_table(schema),
        "tables": tables_section(schema),
        "changes": changes_text(last, frames, schema, renames, people, funding, diagram),
        "people": people_table(people),
        "funding": funding_table(funding),
        "curator": curator_text(record.curator),
        "citation": citation(people, release.publication_date[:4] if release else NOT_YET.strip("()"), record.title,
                             version, release.doi if release else None),
    }
    readme = render(TEMPLATE.read_text(encoding="utf-8"), values)
    description = description_html(readme, glance, schema, diagram)

    # Only what it writes is replaced: publish.py keeps zenodo.json here too
    if (out / FILES).exists():
        shutil.rmtree(out / FILES)
    for name in (METADATA, RELEASE):
        (out / name).unlink(missing_ok=True)
    (out / FILES).mkdir(parents=True)
    for name, frame in frames.items():
        (out / FILES / f"{name}.csv").write_text(frame.to_csv(index=False, lineterminator="\n"), encoding="utf-8",
                                                 newline="")
    (out / FILES / README).write_text(readme, encoding="utf-8", newline="")
    (out / METADATA).write_text(as_json(metadata(record, version, release, people, funding, frames, description,
                                                 commit)), encoding="utf-8", newline="")
    (out / RELEASE).write_text(as_json({
        "version": version,
        "publication_date": release.publication_date if release else None,
        "doi": release.doi if release else None,
        "concept_doi": concept_doi,
        "schema_version": schema.version,
        "commit": commit,
    }), encoding="utf-8", newline="")

    lines = [f"Built version {version} of {record.title}, in schema version {schema.version}, in {out}.",
             f"Compared with version {last.version}." if last else "It is the first version."]
    if not release:
        lines.append("It is a preview: the date and DOI of the version are set when publish.py publishes it.")
    return lines


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build the README, the tables and the metadata of a version of the "
                                                 "dataset on Zenodo, from a merge, as a preview.")
    parser.add_argument("--previous", type=Path,
                        help="the folder of the merge that published the last version; leave it out for the first "
                             "version")
    parser.add_argument("--merge", type=Path, default=REPOSITORY_FOLDER.parent,
                        help="the merge folder; by default the folder that holds this copy of the repository")
    args = parser.parse_args(argv)
    try:
        lines = build(args.merge, repository_commit(), args.previous,
                      notice=lambda message: print(f"Notice: {message}"),
                      warning=lambda message: print(f"Warning: {message}"))
    except ValidationError as e:
        print(f"Validation failed: {e}")
        return 1
    except BuildError as e:
        print(f"Stopped: {e}")
        return 1
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    sys.exit(main())
