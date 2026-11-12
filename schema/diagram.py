"""
Draws how the tables link, for every version of the schema. The deploy Action runs it to publish the diagram next
to the app:

    python schema/diagram.py <folder>

Writes into the folder an interactive page, index.html, that holds every version of the schema. It opens at the
latest version; a menu switches to another, and so does the version after # in the address, as in
index.html#1.0.0. The tables can be dragged around and clicked to highlight their links, and pointing at a column,
table or link says what it is. Also writes pictures of each version as first laid out, in a folder named after the
version: diagram.svg, which keeps what the page says as tooltips, and diagram.png. Those of the latest version are
written in the folder itself too.

The versions come from git: the latest is schema.yaml as it is now, and each earlier version is schema.yaml as it
was in the last commit that had it, so this runs only in a clone with the whole history. Every version is read and
drawn with the code of today. The page is diagram.html with the versions filled in. It lays out the tables itself,
so the pictures are taken in a browser: this needs playwright and its Chromium.
"""
import json
import re
import shutil
import subprocess
import sys
import tempfile
from dataclasses import replace
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT / "app"))

from validation import Schema, help_text, load_schema  # noqa: E402

PAGE = HERE / "diagram.html"
# Where diagram.html takes the versions
PLACEHOLDER = "/* versions */ null"
# schema.yaml, as git names it
SCHEMA_PATH = "schema/schema.yaml"
# A version names a folder of pictures, so it is digits and dots
VERSION = re.compile(r"[0-9]+(?:\.[0-9]+)*")
# Milliseconds to wait for the page to lay out the tables. It loads the layout library from a CDN.
TIMEOUT = 60_000


def git(repository: Path, *args: str) -> str:
    """What a git command prints when run in the repository. Raises ValueError if it fails."""
    done = subprocess.run(["git", "-C", str(repository), *args], capture_output=True)
    if done.returncode:
        raise ValueError(f"git {' '.join(args)} failed: {done.stderr.decode('utf-8', 'replace').strip()}")
    return done.stdout.decode("utf-8")


def schema_version(text: str) -> str | None:
    """The version in the text of a schema.yaml, or None if it cannot be read or is not digits and dots."""
    try:
        version = str(yaml.safe_load(text)["version"])
    except (yaml.YAMLError, TypeError, KeyError):
        return None
    return version if VERSION.fullmatch(version) else None


def version_commits(repository: Path = ROOT) -> list[tuple[str, str | None]]:
    """
    Every version of the schema, the latest first, with the commit to read it from. The latest is schema.yaml as
    it is now, uncommitted changes and all, so its commit is None. Each earlier version is read from the last
    commit that had it: the one just before schema.yaml changed to another version, as the commits after it under
    the same version may have changed other files, such as schema.md. Only the commits of the branch itself count;
    those of a branch merged into it count as its merge commit.

    A commit whose schema.yaml cannot be read, or whose version is not digits and dots, is passed over, as it did
    not pass the tests, so it was never published. Raises ValueError if schema.yaml as it is now is like that, or
    if the history is not all there.
    """
    try:
        shallow = git(repository, "rev-parse", "--is-shallow-repository").strip()
    except (OSError, ValueError) as error:
        raise ValueError(f"The earlier versions of the schema are read from git, but {repository} is not a git "
                         f"repository, or git is not installed. {error}") from error
    if shallow != "false":
        raise ValueError("This clone of the repository holds only part of its history, so earlier versions of the "
                         "schema would be left out. Fetch the rest with: git fetch --unshallow")
    latest = schema_version((repository / SCHEMA_PATH).read_text(encoding="utf-8"))
    if latest is None:
        raise ValueError(f"Either {SCHEMA_PATH} cannot be read, or its version is not digits and dots, such as "
                         "1.0.0, which a version has to be, as it names a folder of the diagram.")
    versions = {latest: None}
    last = "HEAD"  # the last commit that had the schema.yaml of the commit looked at
    for commit in git(repository, "log", "--first-parent", "--format=%H", "--", SCHEMA_PATH).split():
        version = schema_version(git(repository, "show", f"{commit}:{SCHEMA_PATH}"))
        if version and version not in versions:
            versions[version] = git(repository, "rev-parse", last).strip()
        last = f"{commit}^"
    return list(versions.items())


def load_versions(repository: Path = ROOT) -> list[tuple[Schema, str | None]]:
    """
    Every version of the schema, the latest first, read with load_schema, and the commit it was read from.
    Raises ValueError if an earlier version cannot be read with the code of today.
    """
    versions = []
    with tempfile.TemporaryDirectory() as folder:
        for version, commit in version_commits(repository):
            if commit is None:
                versions.append((load_schema(repository / SCHEMA_PATH), None))
                continue
            path = Path(folder) / f"{version}.yaml"
            path.write_text(git(repository, "show", f"{commit}:{SCHEMA_PATH}"), encoding="utf-8")
            try:
                versions.append((load_schema(path), commit))
            except Exception as error:
                raise ValueError(f"Version {version} of the schema, as it was in commit {commit[:7]}, cannot be "
                                 f"read with the code of today: {error!r}. The diagram shows every version, so "
                                 "make the code read it too.") from error
    return versions


def diagram_data(schema: Schema, commit: str | None = None) -> dict:
    """
    The tables and the links to draw for a version of the schema, and what to say about each, with the commit it
    was read from, or None for the latest. A column's help is what row 2 of the collection sheet says about it,
    with its example apart. A Features column links to the Features table, as it holds FTIDs.
    """
    tables, links = [], []
    for table in schema.tables.values():
        columns = [{"name": column.name, "type": column.type, "required": column.required, "unique": column.unique,
                    "help": help_text(replace(column, example=None), schema), "example": column.example}
                   for column in table.columns.values()]
        tables.append({"name": table.name, "required": table.required, "one_row_is": table.one_row_is,
                       "needed": table.needed, "filled_in": table.filled_in, "columns": columns})
        for column in table.columns.values():
            target = "Features" if column.type == "features" else column.links_to
            if target:
                links.append({"from": [table.name, column.name], "to": [target, schema.tables[target].id_column],
                              "required": column.required, "unique": column.unique})
    return {"version": schema.version, "commit": commit, "tables": tables, "links": links}


def page_html(versions: list[dict]) -> str:
    """diagram.html with the versions filled in, the latest first, each as diagram_data gives it."""
    page = PAGE.read_text(encoding="utf-8")
    assert page.count(PLACEHOLDER) == 1, f"diagram.html needs '{PLACEHOLDER}' exactly once"
    # "</" would end the <script> early
    return page.replace(PLACEHOLDER, json.dumps(versions).replace("</", "<\\/"))


def main(folder: str) -> None:
    from playwright.sync_api import expect, sync_playwright

    versions = [diagram_data(schema, commit) for schema, commit in load_versions()]
    latest = versions[0]["version"]
    out = Path(folder)
    out.mkdir(parents=True, exist_ok=True)
    (out / "index.html").write_text(page_html(versions), encoding="utf-8")
    address = (out / "index.html").resolve().as_uri()
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        context = browser.new_context(viewport={"width": 1600, "height": 1000})
        picture = browser.new_page(device_scale_factor=2)
        errors = []

        def open_page(version: str = ""):
            """The page, opened at the version, or with nothing after # in the address."""
            page = context.new_page()
            page.on("pageerror", lambda error: errors.append(error))
            page.goto(f"{address}#{version}" if version else address)
            return page

        def drawn(page, version: str) -> None:
            """Waits until the page has drawn the version, and checks that it is all there."""
            page.wait_for_function("version => window.diagramReady === version || window.diagramError",
                                   arg=version, timeout=TIMEOUT)
            error = page.evaluate("window.diagramError")
            assert not error and not errors, f"Version {version} of the diagram could not be drawn: {error or errors}"
            spec = next(spec for spec in versions if spec["version"] == version)
            expect(page.locator("#version")).to_have_value(version)
            expect(page.locator("#tables .table")).to_have_count(len(spec["tables"]))
            expect(page.locator("#links .link")).to_have_count(len(spec["links"]))

        page = open_page()
        for i, spec in enumerate(versions):
            version = spec["version"]
            if i == 0:
                # The page opens at the latest version, and every version is in the menu, the latest first
                drawn(page, version)
                expect(page.locator("#version option")).to_have_text(
                    [f"{version} (latest)", *(other["version"] for other in versions[1:])])
                expect(page.locator("#notice")).to_be_empty()
            else:
                # Choosing an earlier version in the menu draws it, puts it in the address and says it is earlier
                page.select_option("#version", version)
                drawn(page, version)
                assert page.evaluate("location.hash") == f"#{version}"
                expect(page.locator("#notice")).to_contain_text(f"The latest is {latest}.")
            svg = page.evaluate("diagramSvg()")
            pictures = out / version
            pictures.mkdir(exist_ok=True)
            (pictures / "diagram.svg").write_text(svg, encoding="utf-8")
            picture.set_content(f'<body style="margin:0">{svg}</body>')
            picture.locator("svg").screenshot(path=pictures / "diagram.png")
            if i == 0:
                for name in ("diagram.svg", "diagram.png"):
                    shutil.copyfile(pictures / name, out / name)
                # Pointing at a column says what it holds
                page.locator(".row").first.hover()
                expect(page.locator("#tip")).to_contain_text(spec["tables"][0]["columns"][0]["help"])
        # The address can name a version to open the page at. If it names one that does not exist, the page says
        # so, and shows the latest.
        drawn(open_page(versions[-1]["version"]), versions[-1]["version"])
        page = open_page("0.0.0")
        drawn(page, latest)
        expect(page.locator("#notice")).to_have_text("There is no version 0.0.0 of the schema, so this is the latest.")
        browser.close()
    names = ", ".join(spec["version"] for spec in versions)
    print(f"Drew the diagram in {out}: index.html, and diagram.svg and diagram.png of each version, {names}.")


if __name__ == "__main__":
    main(sys.argv[1])
