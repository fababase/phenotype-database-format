"""
The schema diagram shows every table and column in schema.yaml, and every link between them, for every version of
the schema in the git history. The drawing itself happens in a browser, when the deploy Action runs
schema/diagram.py.
"""
import json
import subprocess
from dataclasses import replace
from pathlib import Path

import pytest

from diagram import PLACEHOLDER, SCHEMA_PATH, diagram_data, load_versions, page_html, version_commits
from helpers import ROOT, SCHEMA
from validation import help_text


def test_diagram_has_every_table_column_and_link():
    data = diagram_data(SCHEMA)
    assert {table["name"]: [column["name"] for column in table["columns"]] for table in data["tables"]} == \
           {name: list(table.columns) for name, table in SCHEMA.tables.items()}
    # A Features column holds FTIDs, so it links to the Features table like a links_to column
    expected = {(table.name, column.name, column.links_to or "Features")
                for table in SCHEMA.tables.values() for column in table.columns.values()
                if column.links_to or column.type == "features"}
    assert {(*link["from"], link["to"][0]) for link in data["links"]} == expected
    assert all(link["to"][1] == SCHEMA.tables[link["to"][0]].id_column for link in data["links"])


def test_diagram_says_what_each_table_and_column_is():
    """
    What the tooltips say. A table's: what one row is, when it is needed and filled in. A column's: its help and its
    example, which together are what row 2 of the collection sheet says about it.
    """
    for spec in diagram_data(SCHEMA)["tables"]:
        table = SCHEMA.tables[spec["name"]]
        assert [spec["one_row_is"], spec["needed"], spec["filled_in"]] == [table.one_row_is, table.needed, table.filled_in]
        for column in spec["columns"]:
            definition = table.columns[column["name"]]
            assert column["example"] == definition.example
            example = f"Example: {column['example']}" if column["example"] else ""
            assert " ".join(filter(None, [column["help"], example])) == help_text(definition, SCHEMA)


def test_diagram_page_has_every_version():
    versions = [diagram_data(SCHEMA), diagram_data(replace(SCHEMA, version="0.9.0"), "0" * 40)]
    page = page_html(versions)
    assert PLACEHOLDER not in page
    assert json.dumps(versions) in page


@pytest.mark.skipif(not (ROOT / ".git").exists(), reason="not a clone of the repository, so it has no history")
def test_every_version_in_the_history_can_be_drawn():
    """
    The diagram reads every version of the schema in the history with the code of today. If this fails after a
    change to the code or to how schema.yaml is laid out, make the code read the earlier version too.
    """
    versions = load_versions()
    assert versions[0][0].version == SCHEMA.version and versions[0][1] is None
    for schema, commit in versions:
        diagram_data(schema, commit)


class History:
    """A git repository in a folder, with nothing but schema.yaml and a file of notes, to make a history in."""

    def __init__(self, folder: Path):
        folder.mkdir()
        self.folder = folder
        self.changes = 0
        self.git("init")

    def git(self, *args: str) -> str:
        done = subprocess.run(["git", "-C", str(self.folder), "-c", "user.name=Test", "-c", "user.email=test@example.org",
                               "-c", "commit.gpgsign=false", *args], capture_output=True, text=True, check=True)
        return done.stdout.strip()

    def write(self, text: str) -> None:
        path = self.folder / SCHEMA_PATH
        path.parent.mkdir(exist_ok=True)
        path.write_text(text, encoding="utf-8")

    def set_version(self, version: str) -> None:
        """Writes schema.yaml with this version, and with something new, so that it differs from before."""
        self.changes += 1
        self.write(f'version: "{version}"\nchange: {self.changes}\n')

    def commit(self, version: str | None = None, text: str | None = None) -> str:
        """
        Commits schema.yaml with this version, or with this text, or, with neither, a change to the file of notes.
        Returns the commit.
        """
        if text is not None:
            self.write(text)
        elif version is not None:
            self.set_version(version)
        else:
            self.changes += 1
            (self.folder / "notes.md").write_text(str(self.changes), encoding="utf-8")
        self.git("add", "--all")
        self.git("commit", "--quiet", "--message", "A change")
        return self.git("rev-parse", "HEAD")


def test_versions_come_from_the_history(tmp_path):
    """
    The latest version is schema.yaml as it is now. An earlier one is read from the last commit that had it: the
    one before schema.yaml changed to a newer version, even if that commit changed another file.
    """
    history = History(tmp_path / "repository")
    history.commit("1.0.0")
    history.commit("1.0.0")
    last_of_1_0_0 = history.commit()
    history.commit("1.1.0")
    head = history.commit()
    assert version_commits(history.folder) == [("1.1.0", None), ("1.0.0", last_of_1_0_0)]
    # A new version that is not committed yet is the latest, and the one before it is the last commit's
    history.set_version("2.0.0")
    assert version_commits(history.folder) == [("2.0.0", None), ("1.1.0", head), ("1.0.0", last_of_1_0_0)]


def test_a_version_that_comes_back_is_the_latest(tmp_path):
    history = History(tmp_path / "repository")
    history.commit("1.0.0")
    history.commit("1.1.0")
    last_of_1_1_0 = history.commit()
    history.commit("1.0.0")
    assert version_commits(history.folder) == [("1.0.0", None), ("1.1.0", last_of_1_1_0)]


def test_commits_that_failed_the_tests_are_passed_over(tmp_path):
    """
    A schema.yaml that cannot be read, or whose version is not digits and dots, did not pass the tests, so it was
    never published.
    """
    history = History(tmp_path / "repository")
    last_of_1_0_0 = history.commit("1.0.0")
    history.commit(text='version: "1.1.0\n')
    history.commit("1.1.0 beta")
    history.commit("1.1.0")
    assert version_commits(history.folder) == [("1.1.0", None), ("1.0.0", last_of_1_0_0)]


@pytest.mark.parametrize("text", ['version: "1.1.0 beta"\n', 'version: "1.1.0\n', "tables: {}\n"])
def test_the_latest_version_has_to_be_digits_and_dots(tmp_path, text):
    """A version names a folder of the diagram."""
    history = History(tmp_path / "repository")
    history.commit("1.0.0")
    history.write(text)
    with pytest.raises(ValueError, match="digits and dots"):
        version_commits(history.folder)


def test_a_shallow_clone_is_refused(tmp_path):
    """It lacks the earlier commits, so the earlier versions would be left out."""
    history = History(tmp_path / "repository")
    history.commit("1.0.0")
    history.commit("1.1.0")
    clone = tmp_path / "clone"
    subprocess.run(["git", "clone", "--quiet", "--depth", "1", history.folder.as_uri(), str(clone)],
                   capture_output=True, check=True)
    with pytest.raises(ValueError, match="git fetch --unshallow"):
        version_commits(clone)


def test_a_folder_outside_git_is_refused(tmp_path, monkeypatch):
    folder = tmp_path / "copy"
    (folder / "schema").mkdir(parents=True)
    (folder / SCHEMA_PATH).write_text('version: "1.0.0"\n', encoding="utf-8")
    # git does not look for a repository above the folder
    monkeypatch.setenv("GIT_CEILING_DIRECTORIES", str(tmp_path))
    with pytest.raises(ValueError, match="not a git repository"):
        version_commits(folder)
