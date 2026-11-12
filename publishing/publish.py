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

Run it in the merge folder, which holds the copy of this repository, once the merge is finished:

    uv run phenotype-database-format/publishing/publish.py [--previous <folder of the last merge>] [--sandbox]

--previous is as for build.py. --sandbox uploads to sandbox.zenodo.org, which is for trying things out, in place of
zenodo.org.

It needs a personal access token of the Zenodo account that owns the dataset, with the scopes deposit:write and
deposit:actions, in the environment variable ZENODO_TOKEN, or ZENODO_SANDBOX_TOKEN with --sandbox. The token is never
shown or saved.

It first checks everything it can without Zenodo: it builds the version as build.py does, in a folder of its own, and
checks that the copy of this repository has no changes, that its commit is on GitHub and that the diagram of the
format's version is online, as the README links to both. For a later version, it checks that the latest version on
Zenodo is the one that the last merge published, with the same files and the same access.

Then it makes a draft of the version on Zenodo, reserves its DOI, builds publish/ with the date and the DOIs, uploads
publish/files/, and sets the metadata in publish/metadata.json. It writes in publish/zenodo.json the ID of the draft on
each Zenodo it was uploaded to. Run again, it takes up the same draft, and uploads only the files that changed. The next
merge finds the dataset on Zenodo from it.

It never publishes. The data manager looks at the draft on Zenodo, and presses Publish there, as a published version
cannot be changed or taken back. Run once more after that, it checks that what Zenodo published is what publish/ holds.
"""
import argparse
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable
from datetime import date
from pathlib import Path

from build import (FILES, LIMIT, METADATA, PUBLISH, README, RECORD, RELEASE, REPOSITORY_FOLDER, BuildError, Record,
                   Release, as_json, build, read_record, repository_commit, sentence)
from collection_sheet import REPOSITORY, SITE
from validation import Schema, ValidationError, load_schema

ZENODO = "https://zenodo.org"
SANDBOX = "https://sandbox.zenodo.org"
TOKEN = "ZENODO_TOKEN"
SANDBOX_TOKEN = "ZENODO_SANDBOX_TOKEN"
# In publish/: the ID of the draft of this version on each Zenodo, by its address
STATE = "zenodo.json"
# The access to the files on Zenodo, for each access in record.yaml. The record's page is always public.
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


def read_state(merge: Path) -> dict[str, str]:
    path = merge / PUBLISH / STATE
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}


def write_state(merge: Path, state: dict[str, str]) -> None:
    (merge / PUBLISH).mkdir(parents=True, exist_ok=True)
    (merge / PUBLISH / STATE).write_text(as_json(state), encoding="utf-8", newline="")


def file_names(schema: Schema) -> list[str]:
    """The files of a version, in the order Zenodo shows them: the README first, then the tables."""
    return [README] + [f"{name}.csv" for name in schema.tables]


def md5(path: Path) -> str:
    """The checksum of a file, as Zenodo gives it."""
    digest = hashlib.md5()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            digest.update(chunk)
    return f"md5:{digest.hexdigest()}"


def local_files(folder: Path) -> dict[str, str]:
    return {path.name: md5(path) for path in sorted(folder.iterdir()) if path.is_file()}


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

def check_last(zenodo: Zenodo, previous: Path, record: Record) -> str:
    """
    The ID of the latest version on Zenodo, after checking that it is the one that the last merge published, with
    the files in its publish/files/, and with the access that record.yaml gives.
    """
    state = read_state(previous)
    if zenodo.address not in state:
        raise PublishError(f"The last merge, in {previous}, has no draft on {zenodo.address} in {PUBLISH}/{STATE}, "
                           "so it was not published there with publish.py. Give the merge that was, with --previous.")
    last = json.loads((previous / PUBLISH / RELEASE).read_text(encoding="utf-8"))
    latest = zenodo.find(f"/api/records/{state[zenodo.address]}/versions/latest")
    if latest is None:
        raise PublishError(f"The last merge, in {previous}, made the draft {state[zenodo.address]} on "
                           f"{zenodo.address}, but no version of it is published. Publish it first, or give the merge "
                           "that published the latest version, with --previous.")
    if doi_of(latest) != last["doi"]:
        raise PublishError(f"The latest version on Zenodo has the DOI {doi_of(latest)}, but the last merge, in "
                           f"{previous}, published {last['doi']}. Give the merge that published the latest version, "
                           "with --previous.")
    found = differences(zenodo_files(zenodo, latest["id"]), local_files(previous / PUBLISH / FILES))
    if found:
        raise PublishError(f"The files of the latest version on Zenodo are not those in "
                           f"{previous / PUBLISH / FILES}: {', '.join(found)}. What changed since the latest version "
                           "is worked out from those files, so they have to be what was published.")
    files_access = latest.get("access", {}).get("files")
    if files_access != FILES_ACCESS[record.access]:
        raise PublishError(f"The files of the latest version are {files_access} on Zenodo, but {RECORD} has access: "
                           f"{record.access}. Correct {RECORD}, or, if the access is to change, change it on Zenodo "
                           "first, by hand.")
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


def published(zenodo: Zenodo, done: dict, merge: Path, record: Record) -> list[str]:
    """
    Lines saying that the version is published, and what to do next, after checking that Zenodo published what
    publish/ holds.
    """
    release = json.loads((merge / PUBLISH / RELEASE).read_text(encoding="utf-8")) if (
        merge / PUBLISH / RELEASE).is_file() else {}
    version = release.get("version", "")
    doi, concept = doi_of(done), parent_doi(done)
    if (doi, concept) != (release.get("doi"), release.get("concept_doi")):
        raise PublishError(f"Version {version} is published on Zenodo, with the DOI {doi}, and the DOI of all "
                           f"versions {concept}, but its README, in {merge / PUBLISH}, gives {release.get('doi')} and "
                           f"{release.get('concept_doi')}. Correct it with a new version.")
    found = differences(zenodo_files(zenodo, done["id"]), local_files(merge / PUBLISH / FILES))
    if found:
        raise PublishError(f"Version {version} is published on Zenodo, but its files are not those in "
                           f"{merge / PUBLISH / FILES}: {', '.join(found)}. The next merge compares with those files, "
                           "so make them what was published.")
    lines = [f"Version {version} of {record.title} is published: https://doi.org/{doi}. Its files are those in "
             f"{merge / PUBLISH / FILES}. There is nothing more to upload."]
    if zenodo.address != ZENODO:
        lines.append("This was the sandbox, for trying things out.")
    elif record.doi is None:
        lines.append(f"Write doi: {concept} in the {RECORD} of the next merge, and add the dataset to "
                     "docs/datasets.md, with that DOI.")
    else:
        lines.append("Update the dataset's row in docs/datasets.md, if the version of the format changed.")
    return lines


def publish(merge: Path, zenodo: Zenodo, commit: str, today: str, previous: Path | None = None,
            online: Callable[[str], bool] = is_online, say: Callable[[str], None] = lambda message: None,
            notice: Callable[[str], None] = lambda message: None,
            warning: Callable[[str], None] = lambda message: None) -> list[str]:
    """
    Uploads the version that the merge folder holds to a draft on Zenodo, and returns lines saying what to do next.
    If the draft has been published, it checks what was published instead.
    Parameters:
        merge: the merge folder.
        zenodo: the Zenodo to upload to.
        commit: the commit that the copy of this repository is at.
        today: the date of the version, YYYY-MM-DD.
        previous: the folder of the last merge, which published the last version; None for the first version.
        online: says whether a page answers; the README links to the commit on GitHub and the diagram.
        say: called with what it is doing, while it uploads.
        notice, warning: called with the validator's notices and warnings.
    Raises:
        ValidationError: if the tables or contributors.yaml do not pass the validator.
        BuildError: if something else in the merge folder is missing or does not fit together.
        PublishError: if something on Zenodo or GitHub does not fit, or Zenodo answers with an error.
    """
    schema = load_schema()
    record = read_record(merge / RECORD)

    # Everything that can be checked without Zenodo, before anything is sent to it
    with tempfile.TemporaryDirectory() as folder:
        build(merge, commit, previous, notice=notice, warning=warning, out=Path(folder))
    if not online(f"{REPOSITORY}/tree/{commit}"):
        raise PublishError(f"The commit {commit}, which the copy of the repository is at, is not on GitHub, at "
                           f"{REPOSITORY}. The README links to it, so push it first, or clone the repository again.")
    if not online(f"{SITE}diagram/{schema.version}/diagram.png"):
        raise PublishError(f"The diagram of version {schema.version} of the format is not online, at "
                           f"{SITE}diagram/#{schema.version}. The README links to it, so publish the app first: see "
                           "docs/deploy-app.md.")

    # The draft: the one made before, if it is still there, or a new one
    state = read_state(merge)
    draft = None
    if zenodo.address in state:
        draft_id = state[zenodo.address]
        done = zenodo.find(f"/api/records/{draft_id}")
        if done:
            return published(zenodo, done, merge, record)
        draft = zenodo.find(f"/api/records/{draft_id}/draft")
        if draft is None:
            say(f"The draft {draft_id} is no longer on {zenodo.address}, so a new one is made.")
    last_id = check_last(zenodo, previous, record) if previous else None
    access = {"record": "public", "files": FILES_ACCESS[record.access]}
    if draft is None:
        if last_id:
            draft = zenodo.request("POST", f"/api/records/{last_id}/versions")
        else:
            draft = zenodo.request("POST", "/api/records", {
                "access": access, "files": {"enabled": True},
                "metadata": {"resource_type": {"id": "dataset"}, "title": record.title}})
        state[zenodo.address] = draft["id"]
        write_state(merge, state)
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
    build(merge, commit, previous, Release(today, doi, concept_doi(draft, doi)))

    names = file_names(schema)
    upload_files(zenodo, draft_id, merge / PUBLISH / FILES, names, say)
    # Setting the metadata replaces the whole draft, so the DOI is sent back as it is, or it would be lost
    metadata = json.loads((merge / PUBLISH / METADATA).read_text(encoding="utf-8"))
    updated = zenodo.request("PUT", f"/api/records/{draft_id}/draft", {
        "access": access, "files": {"enabled": True, "default_preview": README, "order": names},
        "metadata": metadata, "pids": draft.get("pids", {})})
    if doi_of(updated) != doi:
        raise PublishError(f"Zenodo lost the DOI of the draft when its metadata was set. Delete the draft on Zenodo, "
                           f"at {link(zenodo, draft)}, and run publish.py again, which makes a new one.")
    if updated.get("errors"):
        raise PublishError(f"The draft is on Zenodo, at {link(zenodo, draft)}, but Zenodo found problems in its "
                           f"metadata, so it cannot be published: {sentence('; '.join(problems(updated['errors'])))} "
                           f"Correct {RECORD} or the merge, or build.py if it builds the metadata wrong, and run "
                           "publish.py again.")

    release = json.loads((merge / PUBLISH / RELEASE).read_text(encoding="utf-8"))
    return [
        f"Uploaded version {release['version']} of {record.title} to a draft on {zenodo.address}: "
        f"{link(zenodo, updated)}",
        f"Its DOI will be {doi}, and the DOI of all versions {release['concept_doi']}. They work once it is published.",
        "Look at the draft on Zenodo: the files, the README and the metadata. To change something, correct the merge, "
        "and run publish.py again, which updates the same draft.",
        "When all is right, press Publish on Zenodo. A published version cannot be changed or taken back. Then run "
        "publish.py again, which checks what was published.",
    ]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Upload a version of the dataset from a merge to a draft on Zenodo, "
                                                 "for the data manager to look at and publish.")
    parser.add_argument("--previous", type=Path,
                        help="the folder of the merge that published the last version; leave it out for the first "
                             "version")
    parser.add_argument("--merge", type=Path, default=REPOSITORY_FOLDER.parent,
                        help="the merge folder; by default the folder that holds this copy of the repository")
    parser.add_argument("--sandbox", action="store_true",
                        help=f"upload to {SANDBOX}, which is for trying things out, in place of {ZENODO}")
    args = parser.parse_args(argv)
    address, variable = (SANDBOX, SANDBOX_TOKEN) if args.sandbox else (ZENODO, TOKEN)
    token = os.environ.get(variable, "").strip()
    if not token:
        print(f"Stopped: There is no token in the environment variable {variable}. Make a personal access token on "
              f"{address}/account/settings/applications/tokens/new/, with the scopes deposit:write and "
              f"deposit:actions. Then type read -s {variable} && export {variable} in this terminal, paste the token, "
              "and press Enter, so that it is neither shown nor saved in the history.")
        return 1
    try:
        lines = publish(args.merge, Zenodo(address, token), clean_commit(), date.today().isoformat(), args.previous,
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
