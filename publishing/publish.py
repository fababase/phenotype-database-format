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
Uploads a version of a dataset to Zenodo, as a draft, for the data manager to look at and publish.

Run it in the dataset folder, which holds the copy of this repository and the versions, as docs/publish-data.md lays
it out, once the merge is finished:

    uv run phenotype-database-format/publishing/publish.py Versions/<date> --token-file <file> [--sandbox]

The token file holds a personal access token of the Zenodo account that owns the dataset, with the scopes
deposit:write and deposit:actions, and nothing else. The token is never shown. --sandbox uploads to
sandbox.zenodo.org, which is for trying things out, in place of zenodo.org; the versions there are listed in
sandbox.yaml in the dataset folder, in place of zenodo.yaml.

It first checks everything it can without Zenodo: it builds the README as build.py does, in a folder of its own, and
checks that the copy of this repository has no changes, that its commit is on GitHub and that the diagram of the
format's version is online, as the README links to both. For a later version, it checks that the latest version on
Zenodo is the last one in zenodo.yaml, with the files in its folder and the same access.

Then it makes a draft of the version on Zenodo, reserves its DOI, lists the version in zenodo.yaml, builds README.md
with the date and the DOIs, uploads it with the tables, and sets the metadata. Run again, it takes up the same draft,
and uploads only the files that changed.

It never publishes. The data manager looks at the draft on Zenodo, and presses Publish there, as a published version
cannot be changed or taken back. Run once more after that, it checks that what Zenodo published is what the folder
holds.
"""
import argparse
import hashlib
import json
import subprocess
import sys
import tempfile
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable
from datetime import date
from pathlib import Path

from build import (FILES, LIMIT, README, REPOSITORY_FOLDER, VERSIONS, ZENODO_FILE, BuildError, Dataset, Release,
                   Version, build, repository_commit, sentence, write_dataset)
from collection_sheet import REPOSITORY, SITE
from validation import CONTRIBUTORS_FILE, Schema, ValidationError, load_schema

ZENODO = "https://zenodo.org"
SANDBOX = "https://sandbox.zenodo.org"
# In the dataset folder: the versions on the sandbox, as zenodo.yaml lists those on Zenodo
SANDBOX_FILE = "sandbox.yaml"
# The access to the files on Zenodo, for each access in zenodo.yaml. The record's page is always public.
FILES_ACCESS = {"open": "public", "restricted": "restricted"}
# Seconds to wait for Zenodo, or GitHub, to answer
TIMEOUT = 300


class PublishError(ValueError):
    """Raised when something on Zenodo, or the copy of the repository, does not fit. The message says what to do."""


class ZenodoError(PublishError):
    """Zenodo answered a request with an error."""

    def __init__(self, message: str, status: int):
        super().__init__(message)
        self.status = status


class Zenodo:
    """Zenodo's REST API for records, at an address, with a personal access token, which is never shown."""

    def __init__(self, address: str, token: str):
        self.address = address.rstrip("/")
        self._token = token

    def request(self, method: str, path: str, body: dict | list | None = None, upload: Path | None = None) -> dict:
        """
        Sends a request, with body as JSON, or the content of the file upload, and returns the JSON of the answer,
        or {} if it has none.
        """
        headers = {"Authorization": f"Bearer {self._token}", "Accept": "application/json"}
        data = None
        if body is not None:
            data = json.dumps(body).encode("utf-8")
            headers["Content-Type"] = "application/json"
        file = upload.open("rb") if upload else None
        if upload:
            data = file
            headers["Content-Type"] = "application/octet-stream"
            headers["Content-Length"] = str(upload.stat().st_size)
        try:
            request = urllib.request.Request(self.address + path, data=data, method=method, headers=headers)
            with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
                content = response.read()
        except urllib.error.HTTPError as e:
            raise ZenodoError(f"Zenodo answered {method} {path} with {e.code} {e.reason}{explained(e.read())}",
                              e.code) from None
        except (urllib.error.URLError, OSError) as e:
            raise PublishError(f"Could not reach {self.address}: {getattr(e, 'reason', e)}. Check the connection, "
                               "and run publish.py again.") from None
        finally:
            if file:
                file.close()
        return json.loads(content) if content.strip() else {}

    def find(self, path: str) -> dict | None:
        """What a GET of path answers, or None if there is nothing there."""
        try:
            return self.request("GET", path)
        except ZenodoError as e:
            if e.status in (404, 410):
                return None
            raise


def explained(content: bytes) -> str:
    """What Zenodo says is wrong, from the JSON of an error, as the end of a sentence."""
    try:
        data = json.loads(content)
    except ValueError:
        return "."
    parts = [str(data["message"])] if isinstance(data, dict) and data.get("message") else []
    parts += problems(data.get("errors", []) if isinstance(data, dict) else [])
    return f": {sentence('; '.join(parts))}" if parts else "."


def problems(errors: list) -> list[str]:
    """Zenodo's errors, as field: message."""
    found = []
    for error in errors:
        messages = error.get("messages", [])
        text = " ".join(str(m) for m in messages) if isinstance(messages, list) else json.dumps(messages)
        found.append(f"{error.get('field', '')}: {text}")
    return found


def is_online(address: str) -> bool:
    """Whether a page answers."""
    try:
        request = urllib.request.Request(address, headers={"User-Agent": "publish.py"})
        with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
            return response.status == 200
    except (urllib.error.URLError, OSError, ValueError):
        return False


def clean_commit(repository: Path = REPOSITORY_FOLDER) -> str:
    """The commit that the copy of this repository is at, after checking that nothing in it is changed or added."""
    commit = repository_commit(repository)
    result = subprocess.run(["git", "-C", str(repository), "status", "--porcelain"], capture_output=True, text=True)
    if result.returncode or result.stdout.strip():
        changed = [line[3:] for line in result.stdout.splitlines()]
        raise PublishError(f"The copy of the repository in {repository} has changes that are not committed: "
                           f"{', '.join(changed[:LIMIT]) or result.stderr.strip()}. The README links to its commit, "
                           "so it has to be as that commit is on GitHub. Undo the changes, or clone the repository "
                           "again.")
    return commit


# ---------------------------------------------------------------- What is where

def doi_of(record: dict) -> str | None:
    """The DOI of a version on Zenodo, reserved or published."""
    return record.get("pids", {}).get("doi", {}).get("identifier")


def parent_doi(record: dict) -> str | None:
    """The DOI of all versions, once the first version is published."""
    return record.get("parent", {}).get("pids", {}).get("doi", {}).get("identifier") or record.get("conceptdoi")


def concept_doi(draft: dict, doi: str) -> str:
    """
    The DOI of all versions. Zenodo gives it when the first version is published, in the same form as the DOI of each
    version, <prefix>/zenodo.<ID>, with the ID of the parent that all versions share.
    """
    known = parent_doi(draft)
    if known:
        return known
    prefix, _, suffix = doi.partition("/")
    if suffix != f"zenodo.{draft['id']}":
        raise PublishError(f"Zenodo reserved the DOI {doi}, which is not <prefix>/zenodo.{draft['id']}, so the DOI of "
                           "all versions cannot be worked out before the first version is published. publish.py has "
                           "to be changed to fit how Zenodo makes DOIs now.")
    return f"{prefix}/zenodo.{draft['parent']['id']}"


def link(zenodo: Zenodo, draft: dict) -> str:
    """The page of a draft on Zenodo."""
    return draft.get("links", {}).get("self_html") or f"{zenodo.address}/uploads/{draft['id']}"


def file_names(schema: Schema) -> list[str]:
    """The files of a version, in the order Zenodo shows them: the README, the tables, and who to credit."""
    return [README] + [f"{name}.csv" for name in schema.tables] + [CONTRIBUTORS_FILE]


def md5(path: Path) -> str:
    """The checksum of a file, as Zenodo gives it."""
    digest = hashlib.md5()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            digest.update(chunk)
    return f"md5:{digest.hexdigest()}"


def local_files(folder: Path, names: list[str]) -> dict[str, str]:
    """The files of a version in its folder, by name, with their checksums; a file that is not there is left out."""
    return {name: md5(folder / name) for name in names if (folder / name).is_file()}


def zenodo_files(zenodo: Zenodo, record_id: str) -> dict[str, str | None]:
    """The files of a published version on Zenodo, with their checksums."""
    entries = zenodo.request("GET", f"/api/records/{record_id}/files").get("entries", [])
    return {entry["key"]: entry.get("checksum") for entry in entries}


def differences(there: dict[str, str | None], here: dict[str, str]) -> list[str]:
    found = [f"{key} differs" for key in sorted(here) if key in there and there[key] != here[key]]
    found += [f"{key} is not on Zenodo" for key in sorted(here) if key not in there]
    found += [f"{key} is only on Zenodo" for key in sorted(there) if key not in here]
    return found


# ---------------------------------------------------------------- Publishing

def check_last(zenodo: Zenodo, dataset: Dataset, last: Version, names: list[str]) -> str:
    """
    The ID of the latest version on Zenodo, after checking that it is the last version that the dataset's file
    lists, with the files in its folder's zenodo/, and with the access that zenodo.yaml gives.
    """
    folder = dataset.folder / VERSIONS / last.folder
    latest = zenodo.find(f"/api/records/{last.id}/versions/latest")
    if latest is None:
        raise PublishError(f"Version {last.number}, in {folder}, was uploaded to {zenodo.address} as the draft "
                           f"{last.id}, but no version of it is published. Publish it first.")
    if doi_of(latest) != last.doi:
        raise PublishError(f"The latest version on Zenodo has the DOI {doi_of(latest)}, but the last version in "
                           f"{dataset.state}, {last.number}, has {last.doi}. Every version has to be uploaded with "
                           "publish.py, so that the next one can say what changed since it.")
    found = differences(zenodo_files(zenodo, latest["id"]), local_files(folder / FILES, names))
    if found:
        raise PublishError(f"The files of version {last.number} on Zenodo are not those in {folder / FILES}: "
                           f"{', '.join(found)}. What changed since it is worked out from those files, so they have "
                           "to be what was published.")
    files_access = latest.get("access", {}).get("files")
    if files_access != FILES_ACCESS[dataset.access]:
        raise PublishError(f"The files of the latest version are {files_access} on Zenodo, but {ZENODO_FILE} has "
                           f"access: {dataset.access}. Correct {ZENODO_FILE}, or, if the access is to change, change "
                           "it on Zenodo first, by hand.")
    return latest["id"]


def upload_files(zenodo: Zenodo, draft_id: str, folder: Path, names: list[str], say: Callable[[str], None]) -> None:
    """
    Makes the files of the draft those in folder: it keeps a file that is there already, with the same checksum, and
    deletes or replaces every other one.
    """
    base = f"/api/records/{draft_id}/draft/files"
    here = {name: md5(folder / name) for name in names}
    there = {entry["key"]: entry.get("checksum") if entry.get("status") == "completed" else None
             for entry in zenodo.request("GET", base).get("entries", [])}
    for key, checksum in there.items():
        if here.get(key) != checksum:
            zenodo.request("DELETE", f"{base}/{urllib.parse.quote(key)}")
    new = [name for name in names if there.get(name) != here[name]]
    if new:
        zenodo.request("POST", base, [{"key": name} for name in new])
    for name in new:
        path = folder / name
        say(f"Uploading {name}, {path.stat().st_size:,} bytes.")
        zenodo.request("PUT", f"{base}/{urllib.parse.quote(name)}/content", upload=path)
        entry = zenodo.request("POST", f"{base}/{urllib.parse.quote(name)}/commit")
        if entry.get("checksum") != here[name]:
            raise PublishError(f"{name} did not arrive whole on Zenodo: its checksum there is {entry.get('checksum')}, "
                               f"not {here[name]}. Run publish.py again.")


def published(zenodo: Zenodo, done: dict, dataset: Dataset, this: Version, folder: Path,
              names: list[str]) -> list[str]:
    """
    Lines saying that the version is published, and what to do next, after checking that Zenodo published what the
    folder of the version holds.
    """
    doi, concept = doi_of(done), parent_doi(done)
    if (doi, concept) != (this.doi, dataset.doi):
        raise PublishError(f"Version {this.number} is published on Zenodo, with the DOI {doi}, and the DOI of all "
                           f"versions {concept}, but {dataset.state} has {this.doi} and {dataset.doi}, which its "
                           "README gives. Correct it with a new version.")
    found = differences(zenodo_files(zenodo, done["id"]), local_files(folder / FILES, names))
    if found:
        raise PublishError(f"Version {this.number} is published on Zenodo, but its files are not those in "
                           f"{folder / FILES}: {', '.join(found)}. The next version compares with those files, so "
                           "make them what was published.")
    lines = [f"Version {this.number} of {dataset.title} is published: https://doi.org/{doi}. Its files are those "
             f"in {folder / FILES}. There is nothing more to upload."]
    if zenodo.address != ZENODO:
        lines.append("This was the sandbox, for trying things out.")
    elif this.number == 1:
        lines.append(f"Add the dataset to docs/datasets.md, with the DOI of all versions, {concept}.")
    else:
        lines.append("Update the dataset's row in docs/datasets.md, if the version of the format changed.")
    return lines


def publish(folder: Path, zenodo: Zenodo, commit: str, today: str, state: str = ZENODO_FILE,
            online: Callable[[str], bool] = is_online, say: Callable[[str], None] = lambda message: None,
            notice: Callable[[str], None] = lambda message: None,
            warning: Callable[[str], None] = lambda message: None) -> list[str]:
    """
    Uploads the version that the folder holds to a draft on Zenodo, and returns lines saying what to do next. If the
    draft has been published, it checks what was published instead.
    Parameters:
        folder: the folder of the version, Versions/<date> in the dataset folder.
        zenodo: the Zenodo to upload to.
        commit: the commit that the copy of this repository is at.
        today: the date of the version, YYYY-MM-DD.
        state: the file in the dataset folder that lists the versions on this Zenodo: zenodo.yaml, or the sandbox's.
        online: says whether a page answers; the README links to the commit on GitHub and the diagram.
        say: called with what it is doing, while it uploads.
        notice, warning: called with the validator's notices and warnings.
    Raises:
        ValidationError: if the tables or contributors.yaml do not pass the validator.
        BuildError: if something else in the folders is missing or does not fit together.
        PublishError: if something on Zenodo or GitHub does not fit, or Zenodo answers with an error.
    """
    schema = load_schema()
    folder = folder.resolve()
    names = file_names(schema)

    # Everything that can be checked without Zenodo, before anything is sent to it
    with tempfile.TemporaryDirectory() as check:
        dataset = build(folder, commit, state=state, notice=notice, warning=warning, out=Path(check)).dataset
    if not online(f"{REPOSITORY}/tree/{commit}"):
        raise PublishError(f"The commit {commit}, which the copy of the repository is at, is not on GitHub, at "
                           f"{REPOSITORY}. The README links to it, so push it first, or clone the repository again.")
    if not online(f"{SITE}diagram/{schema.version}/diagram.png"):
        raise PublishError(f"The diagram of version {schema.version} of the format is not online, at "
                           f"{SITE}diagram/#{schema.version}. The README links to it, so publish the app first: see "
                           "docs/maintainers.md.")

    # The draft: the one made before, if it is still there, or a new one
    this = next((version for version in dataset.versions if version.folder == folder.name), None)
    draft = None
    if this:
        done = zenodo.find(f"/api/records/{this.id}")
        if done:
            return published(zenodo, done, dataset, this, folder, names)
        draft = zenodo.find(f"/api/records/{this.id}/draft")
        if draft is None:
            say(f"The draft {this.id} is no longer on {zenodo.address}, so a new one is made.")
    earlier = [version for version in dataset.versions if this is None or version.number < this.number]
    last_id = check_last(zenodo, dataset, earlier[-1], names) if earlier else None
    access = {"record": "public", "files": FILES_ACCESS[dataset.access]}
    if draft is None:
        if last_id:
            draft = zenodo.request("POST", f"/api/records/{last_id}/versions")
        else:
            # A first version: Zenodo gives it a new DOI of all versions, so one from a draft that is gone is forgotten
            draft = zenodo.request("POST", "/api/records", {
                "access": access, "files": {"enabled": True},
                "metadata": {"resource_type": {"id": "dataset"}, "title": dataset.title}})
            dataset.doi = None
        this = Version(earlier[-1].number + 1 if earlier else 1, folder.name, draft["id"], doi_of(draft), today,
                       schema.version)
        dataset.versions = earlier + [this]
        write_dataset(dataset)
    draft_id = draft["id"]

    # Its DOI, which the README gives, so it is reserved before the version is built
    doi = doi_of(draft)
    if not doi:
        try:
            draft = zenodo.request("POST", f"/api/records/{draft_id}/draft/pids/doi")
        except ZenodoError as e:
            if e.status != 400:
                raise
            raise PublishError(f"The draft has no DOI, and Zenodo will not reserve one: {e} This happens when a DOI "
                               "was reserved, and then lost. Delete the draft on Zenodo, at "
                               f"{link(zenodo, draft)}, and run publish.py again, which makes a new one.") from None
        doi = doi_of(draft)
    concept = concept_doi(draft, doi)
    this.doi, this.date, this.format = doi, today, schema.version
    dataset.doi = dataset.doi or concept
    write_dataset(dataset)
    built = build(folder, commit, Release(today, doi, concept), state, notice=notice, warning=warning)

    upload_files(zenodo, draft_id, folder / FILES, names, say)
    # Setting the metadata replaces the whole draft, so the DOI is sent back as it is, or it would be lost
    updated = zenodo.request("PUT", f"/api/records/{draft_id}/draft", {
        "access": access, "files": {"enabled": True, "default_preview": README, "order": names},
        "metadata": built.metadata, "pids": draft.get("pids", {})})
    if doi_of(updated) != doi:
        raise PublishError(f"Zenodo lost the DOI of the draft when its metadata was set. Delete the draft on Zenodo, "
                           f"at {link(zenodo, draft)}, and run publish.py again, which makes a new one.")
    if updated.get("errors"):
        raise PublishError(f"The draft is on Zenodo, at {link(zenodo, draft)}, but Zenodo found problems in its "
                           f"metadata, so it cannot be published: {sentence('; '.join(problems(updated['errors'])))} "
                           f"Correct {ZENODO_FILE} or the merge, or build.py if it builds the metadata wrong, and run "
                           "publish.py again.")

    return [
        f"Uploaded version {built.version} of {dataset.title} to a draft on {zenodo.address}: "
        f"{link(zenodo, updated)}",
        f"Its DOI will be {doi}, and the DOI of all versions {concept}. They work once it is published.",
        "Look at the draft on Zenodo: the files, the README and the metadata. To change something, correct the merge, "
        "and run publish.py again, which updates the same draft.",
        "When all is right, press Publish on Zenodo. A published version cannot be changed or taken back. Then run "
        "publish.py again, which checks what was published.",
    ]


def read_token(path: Path, address: str) -> str:
    """The token in a file, which holds nothing else. It is never shown."""
    try:
        token = path.read_text(encoding="utf-8").strip()
    except OSError as e:
        raise PublishError(f"Could not read the token file {path}: {e.strerror or e}. Make a personal access token "
                           f"on {address}/account/settings/applications/tokens/new/, with the scopes deposit:write "
                           "and deposit:actions, and save it in a file, on its own.") from None
    if not token or len(token.split()) != 1:
        raise PublishError(f"The token file {path} has to hold the token, and nothing else.")
    return token


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Upload a version of a dataset to a draft on Zenodo, from its "
                                                 "folder, for the data manager to look at and publish.")
    parser.add_argument("folder", type=Path, help=f"the folder of the version: {VERSIONS}/<date> in the dataset folder")
    parser.add_argument("--token-file", type=Path, required=True,
                        help="a file that holds a personal access token of the account that owns the dataset, with "
                             "the scopes deposit:write and deposit:actions, and nothing else")
    parser.add_argument("--sandbox", action="store_true",
                        help=f"upload to {SANDBOX}, which is for trying things out, in place of {ZENODO}, and list "
                             f"the version in {SANDBOX_FILE}")
    args = parser.parse_args(argv)
    address, state = (SANDBOX, SANDBOX_FILE) if args.sandbox else (ZENODO, ZENODO_FILE)
    try:
        token = read_token(args.token_file, address)
        lines = publish(args.folder, Zenodo(address, token), clean_commit(), date.today().isoformat(), state,
                        online=is_online, say=print, notice=lambda message: print(f"Notice: {message}"),
                        warning=lambda message: print(f"Warning: {message}"))
    except ValidationError as e:
        print(f"Validation failed: {e}")
        return 1
    except (BuildError, PublishError) as e:
        print(f"Stopped: {e}")
        return 1
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    sys.exit(main())
