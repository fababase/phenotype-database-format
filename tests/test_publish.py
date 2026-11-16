"""
publishing/publish.py, which uploads a version of a dataset to a draft on Zenodo. Each test publishes a merge of the
valid dataset to a fake Zenodo, which keeps its records in memory and serves the part of Zenodo's REST API that
publish.py uses on a local port, so that the requests are sent and answered as they are with Zenodo.
"""
import hashlib
import json
import re
import subprocess
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

import publish
import build
from helpers import COMMIT, ROOT, SCHEMA, SCORE, Merge
from validation import ValidationError

TOKEN = "secret-token-0123456789"
TODAY = "2026-11-20"
NAMES = ["README.md"] + [f"{name}.csv" for name in SCHEMA.tables]
# The IDs and DOIs of the first dataset made on a fake Zenodo, and of its first two versions
PARENT, FIRST, SECOND = "1000", "1001", "1002"
CONCEPT = f"10.5072/zenodo.{PARENT}"
NEXT_STEPS = [
    "Look at the draft on Zenodo: the files, the README and the metadata. To change something, correct the merge, and "
    "run publish.py again, which updates the same draft.",
    "When all is right, press Publish on Zenodo. A published version cannot be changed or taken back. Then run "
    "publish.py again, which checks what was published.",
]


class Answer(Exception):
    """An answer of the fake Zenodo other than the usual one."""

    def __init__(self, status: int, message: str):
        super().__init__(message)
        self.status = status
        self.message = message


class FakeZenodo:
    """
    Zenodo's REST API for records, as far as publish.py uses it, kept in memory. It behaves as Zenodo does where it
    matters: setting the metadata of a draft replaces the whole draft, so a reserved DOI that is not sent back is lost,
    and no other can be reserved; a new version starts with no files and no DOI; and the DOI of all versions is given
    when the first version is published.
    """
    PREFIX = "10.5072"

    def __init__(self):
        self.next_id = int(PARENT)
        self.records: dict[str, dict] = {}
        self.parents: dict[str, dict] = {}
        self.requests: list[tuple[str, str]] = []
        self.errors: list[dict] = []  # given back when the metadata of a draft is set
        fake = self

        class Handler(BaseHTTPRequestHandler):
            def answer(self):
                body = self.rfile.read(int(self.headers.get("Content-Length") or 0))
                status, payload, location = fake.handle(self.command, self.path, self.headers, body)
                content = json.dumps(payload).encode() if payload is not None else b""
                self.send_response(status)
                if location:
                    self.send_header("Location", location)
                if content:
                    self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(content)))
                self.end_headers()
                self.wfile.write(content)

            do_GET = do_POST = do_PUT = do_DELETE = answer

            def log_message(self, *args):
                pass

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.address = f"http://127.0.0.1:{self.server.server_address[1]}"

    def close(self) -> None:
        self.server.shutdown()
        self.server.server_close()

    # ------------------------------------------------ Answering requests

    ROUTES = [
        ("POST", r"/api/records", "create"),
        ("GET", r"/api/records/(\w+)", "get_record"),
        ("GET", r"/api/records/(\w+)/draft", "get_draft"),
        ("PUT", r"/api/records/(\w+)/draft", "update"),
        ("POST", r"/api/records/(\w+)/draft/pids/doi", "reserve"),
        ("GET", r"/api/records/(\w+)/draft/files", "draft_files"),
        ("POST", r"/api/records/(\w+)/draft/files", "start_files"),
        ("PUT", r"/api/records/(\w+)/draft/files/([^/]+)/content", "upload"),
        ("POST", r"/api/records/(\w+)/draft/files/([^/]+)/commit", "commit"),
        ("DELETE", r"/api/records/(\w+)/draft/files/([^/]+)", "delete_file"),
        ("POST", r"/api/records/(\w+)/versions", "new_version"),
        ("GET", r"/api/records/(\w+)/versions/latest", "latest"),
        ("GET", r"/api/records/(\w+)/files", "files"),
    ]

    def handle(self, method: str, path: str, headers, body: bytes) -> tuple[int, dict | None, str | None]:
        self.requests.append((method, path))
        if headers.get("Authorization") != f"Bearer {TOKEN}":
            return 403, {"status": 403, "message": "Permission denied."}, None
        for route_method, pattern, name in self.ROUTES:
            match = re.fullmatch(pattern, path)
            if match and method == route_method:
                arguments = list(match.groups())
                if name == "upload":
                    arguments.append(body)
                elif body:
                    arguments.append(json.loads(body))
                try:
                    return getattr(self, name)(*arguments)
                except Answer as e:
                    return e.status, {"status": e.status, "message": e.message}, None
        return 404, {"status": 404, "message": "The requested URL was not found on the server."}, None

    def new_id(self) -> str:
        """The next ID, for a record or a parent: 1000, 1001 and so on."""
        new = str(self.next_id)
        self.next_id += 1
        return new

    def view(self, rid: str) -> dict:
        record = self.records[rid]
        parent = self.parents[record["parent"]]
        page = "records" if record["published"] else "uploads"
        return {"id": rid, "is_published": record["published"],
                "parent": {"id": record["parent"],
                           "pids": {"doi": {"identifier": parent["doi"], "provider": "datacite"}} if parent["doi"]
                           else {}},
                "pids": json.loads(json.dumps(record["pids"])), "access": record["access"],
                "metadata": record["metadata"], "files": record["settings"],
                "links": {"self_html": f"{self.address}/{page}/{rid}"}}

    def draft(self, rid: str) -> dict:
        if rid not in self.records or self.records[rid]["published"]:
            raise Answer(404, "The draft was not found.")
        return self.records[rid]

    def add(self, parent: str, access: dict, metadata: dict) -> str:
        rid = self.new_id()
        self.records[rid] = {"parent": parent, "published": False, "pids": {}, "lost": False, "access": access,
                             "metadata": metadata, "files": {}, "settings": {"enabled": True}}
        self.parents[parent]["draft"] = rid
        return rid

    def create(self, body):
        parent = self.new_id()
        self.parents[parent] = {"versions": [], "draft": None, "doi": None}
        return 201, self.view(self.add(parent, body["access"], body.get("metadata", {}))), None

    def get_record(self, rid):
        if rid not in self.records or not self.records[rid]["published"]:
            raise Answer(404, "The persistent identifier is not registered.")
        return 200, self.view(rid), None

    def get_draft(self, rid):
        self.draft(rid)
        return 200, self.view(rid), None

    def update(self, rid, body):
        record = self.draft(rid)
        record["access"] = body["access"]
        record["metadata"] = body["metadata"]
        record["settings"] = body["files"]
        reserved = record["pids"].get("doi")
        if reserved and body.get("pids", {}).get("doi") != reserved:
            record["lost"] = True
        record["pids"] = body.get("pids", {}) if not record["lost"] else {}
        return 200, self.view(rid) | ({"errors": self.errors} if self.errors else {}), None

    def reserve(self, rid):
        record = self.draft(rid)
        if record["pids"].get("doi") or record["lost"]:
            raise Answer(400, "A PID already exists for type doi.")
        record["pids"]["doi"] = {"identifier": f"{self.PREFIX}/zenodo.{rid}", "provider": "datacite",
                                 "client": "datacite"}
        return 201, self.view(rid), None

    @staticmethod
    def entry(key: str, file: dict) -> dict:
        entry = {"key": key, "status": "completed" if file["checksum"] else "pending"}
        if file["checksum"]:
            entry |= {"checksum": file["checksum"], "size": len(file["data"])}
        return entry

    def draft_files(self, rid):
        files = self.draft(rid)["files"]
        return 200, {"enabled": True, "entries": [self.entry(key, file) for key, file in files.items()]}, None

    def start_files(self, rid, body):
        files = self.draft(rid)["files"]
        for item in body:
            if item["key"] in files:
                raise Answer(400, f"File with key {item['key']} already exists.")
            files[item["key"]] = {"data": None, "checksum": None}
        return 201, {"entries": [self.entry(item["key"], files[item["key"]]) for item in body]}, None

    def upload(self, rid, key, data):
        file = self.draft(rid)["files"][key]
        file["data"] = data
        return 200, self.entry(key, file), None

    def commit(self, rid, key):
        file = self.draft(rid)["files"][key]
        file["checksum"] = f"md5:{hashlib.md5(file['data']).hexdigest()}"
        return 200, self.entry(key, file), None

    def delete_file(self, rid, key):
        del self.draft(rid)["files"][key]
        return 204, None, None

    def new_version(self, rid):
        record = self.records[rid]
        parent = self.parents[record["parent"]]
        if parent["draft"]:
            return 201, self.view(parent["draft"]), None
        metadata = {k: v for k, v in record["metadata"].items() if k not in ("publication_date", "version")}
        return 201, self.view(self.add(record["parent"], record["access"], metadata)), None

    def latest(self, rid):
        if rid not in self.records:
            raise Answer(404, "The persistent identifier is not registered.")
        versions = self.parents[self.records[rid]["parent"]]["versions"]
        if not versions:
            raise Answer(404, "No published version was found.")
        return 302, None, f"/api/records/{versions[-1]}"

    def files(self, rid):
        record = self.records[rid]
        return 200, {"entries": [self.entry(key, file) for key, file in record["files"].items()]}, None

    # ------------------------------------------------ What the data manager does on Zenodo's pages

    def publish(self, rid: str) -> None:
        """Presses Publish on a draft."""
        record = self.draft(rid)
        assert record["pids"].get("doi"), "Zenodo does not publish a draft without a DOI"
        record["published"] = True
        parent = self.parents[record["parent"]]
        parent["versions"].append(rid)
        parent["draft"] = None
        parent["doi"] = parent["doi"] or f"{self.PREFIX}/zenodo.{record['parent']}"

    def publish_by_hand(self, rid: str) -> str:
        """Makes a new version of a published record, with its files, and publishes it."""
        _, view, _ = self.new_version(rid)
        self.reserve(view["id"])
        self.draft(view["id"])["files"] = dict(self.records[rid]["files"])
        self.publish(view["id"])
        return view["id"]

    def delete(self, rid: str) -> None:
        """Deletes a draft that was never published."""
        record = self.draft(rid)
        self.parents[record["parent"]]["draft"] = None
        del self.records[rid]

    def drafts(self) -> list[str]:
        return [rid for rid, record in self.records.items() if not record["published"]]

    def content(self, rid: str) -> dict[str, bytes]:
        return {key: file["data"] for key, file in self.records[rid]["files"].items()}


@pytest.fixture
def no_proxy(monkeypatch):
    """Requests to this computer, where the fake Zenodo is, never go through a proxy."""
    for variable in ("no_proxy", "NO_PROXY"):
        monkeypatch.setenv(variable, "127.0.0.1")


@pytest.fixture
def zenodo(no_proxy):
    fake = FakeZenodo()
    yield fake
    fake.close()


@pytest.fixture
def merge(tmp_path: Path) -> Merge:
    return Merge(tmp_path / "dataset")


def run(merge: Merge, zenodo: FakeZenodo, token: str = TOKEN, state: str = "zenodo.yaml",
        online=lambda address: True, said: list[str] | None = None) -> list[str]:
    return publish.publish(merge.folder, publish.Zenodo(zenodo.address, token), COMMIT, TODAY, state, online=online,
                           say=said.append if said is not None else lambda message: None)


def fails(merge: Merge, zenodo: FakeZenodo, **options) -> str:
    with pytest.raises(publish.PublishError) as e:
        run(merge, zenodo, **options)
    return str(e.value)


def versions(merge: Merge, state: str = "zenodo.yaml") -> list[dict]:
    return merge.state(state).get("versions", [])


def published_first(tmp_path: Path, zenodo: FakeZenodo, access: str = "open") -> Merge:
    """The valid dataset, uploaded and published as the first version, from the folder 2026-11-01."""
    first = Merge(tmp_path / "dataset", "2026-11-01", access=access)
    run(first, zenodo)
    zenodo.publish(FIRST)
    return first


def next_merge(tmp_path: Path) -> Merge:
    """The folder of the version after the first, with no IDs changed."""
    return Merge(tmp_path / "dataset", "2026-12-01", changes="Corrections.\n")


def metadata(merge: Merge, release: publish.Release) -> dict:
    """The metadata of the version, as build.py makes it with the version's date and DOIs."""
    return build.build(merge.folder, COMMIT, release).metadata


# ---------------------------------------------------------------- The first version

def test_first_version(merge, zenodo):
    doi = f"10.5072/zenodo.{FIRST}"
    assert run(merge, zenodo) == [
        f"Uploaded version 1 of Nordbean test dataset to a draft on {zenodo.address}: "
        f"{zenodo.address}/uploads/{FIRST}",
        f"Its DOI will be {doi}, and the DOI of all versions {CONCEPT}. They work once it is published.",
    ] + NEXT_STEPS
    assert merge.state() == {
        "title": "Nordbean test dataset", "access": "open",
        "curator": {"family_name": "Keeper", "given_names": "Dana", "orcid": "none",
                    "affiliations": [{"name": "Northfield Agricultural College", "ror": "none"}]},
        "doi": CONCEPT,
        "versions": [{"version": "1", "folder": merge.folder.name, "id": FIRST, "doi": doi, "date": TODAY,
                      "format": SCHEMA.version}]}
    assert zenodo.drafts() == [FIRST]
    draft = zenodo.records[FIRST]
    assert zenodo.content(FIRST) == {name: (merge.files / name).read_bytes() for name in NAMES}
    assert draft["metadata"] == metadata(merge, publish.Release(TODAY, doi, CONCEPT))
    assert draft["access"] == {"record": "public", "files": "public"}
    assert draft["settings"] == {"enabled": True, "default_preview": "README.md", "order": NAMES}
    assert draft["pids"]["doi"]["identifier"] == doi
    assert (f"- **DOI:** [{doi}](https://doi.org/{doi}). The DOI [{CONCEPT}](https://doi.org/{CONCEPT})"
            in merge.readme())
    assert f"- **Version:** 1, published {TODAY}.\n" in merge.readme()


def test_a_restricted_dataset(tmp_path, zenodo):
    merge = Merge(tmp_path / "dataset", access="restricted")
    run(merge, zenodo)
    assert zenodo.records[FIRST]["access"] == {"record": "public", "files": "restricted"}


def test_running_again_takes_up_the_same_draft(merge, zenodo):
    run(merge, zenodo)
    merge.tables.set("Phenotype", SCORE, "Score", "95")
    zenodo.requests.clear()
    said = []
    lines = run(merge, zenodo, said=said)
    assert lines[0].endswith(f"/uploads/{FIRST}")
    assert zenodo.drafts() == [FIRST]
    assert said == [f"Uploading Phenotype.csv, {(merge.files / 'Phenotype.csv').stat().st_size:,} bytes."]
    assert zenodo.content(FIRST) == {name: (merge.files / name).read_bytes() for name in NAMES}
    assert [request for request in zenodo.requests if request[0] != "GET"] == [
        ("DELETE", f"/api/records/{FIRST}/draft/files/Phenotype.csv"),
        ("POST", f"/api/records/{FIRST}/draft/files"),
        ("PUT", f"/api/records/{FIRST}/draft/files/Phenotype.csv/content"),
        ("POST", f"/api/records/{FIRST}/draft/files/Phenotype.csv/commit"),
        ("PUT", f"/api/records/{FIRST}/draft"),
    ]
    assert zenodo.records[FIRST]["pids"]["doi"]["identifier"] == f"10.5072/zenodo.{FIRST}"
    assert len(versions(merge)) == 1


def test_after_publishing(merge, zenodo):
    run(merge, zenodo)
    zenodo.publish(FIRST)
    zenodo.requests.clear()
    assert run(merge, zenodo) == [
        f"Version 1 of Nordbean test dataset is published: https://doi.org/10.5072/zenodo.{FIRST}. Its files are "
        f"those in {merge.files}. There is nothing more to upload.",
        "This was the sandbox, for trying things out.",
    ]
    assert all(method == "GET" for method, _ in zenodo.requests)


def test_after_publishing_on_zenodo_itself(tmp_path, zenodo, monkeypatch):
    monkeypatch.setattr(publish, "ZENODO", zenodo.address)
    first = published_first(tmp_path, zenodo)
    assert run(first, zenodo)[1] == f"Add the dataset to docs/datasets.md, with the DOI of all versions, {CONCEPT}."
    second = next_merge(tmp_path)
    run(second, zenodo)
    zenodo.publish(SECOND)
    assert run(second, zenodo)[1] == ("Update the dataset's row in docs/datasets.md, if the version of the format "
                                      "changed.")


def test_published_files_that_are_not_those_in_the_folder(merge, zenodo):
    run(merge, zenodo)
    zenodo.publish(FIRST)
    (merge.files / "README.md").write_text("Changed after publishing\n", encoding="utf-8")
    assert fails(merge, zenodo) == (f"Version 1 is published on Zenodo, but its files are not those in "
                                    f"{merge.files}: README.md differs. The next version compares with those files, "
                                    "so make them what was published.")


# ---------------------------------------------------------------- Later versions

def test_second_version(tmp_path, zenodo):
    first = published_first(tmp_path, zenodo)
    second = next_merge(tmp_path)
    second.tables.set("Phenotype", SCORE, "Score", "95")
    doi = f"10.5072/zenodo.{SECOND}"
    assert run(second, zenodo)[:2] == [
        f"Uploaded version 2 of Nordbean test dataset to a draft on {zenodo.address}: "
        f"{zenodo.address}/uploads/{SECOND}",
        f"Its DOI will be {doi}, and the DOI of all versions {CONCEPT}. They work once it is published.",
    ]
    assert versions(second) == [
        {"version": "1", "folder": first.folder.name, "id": FIRST, "doi": f"10.5072/zenodo.{FIRST}", "date": TODAY,
         "format": SCHEMA.version},
        {"version": "2", "folder": second.folder.name, "id": SECOND, "doi": doi, "date": TODAY,
         "format": SCHEMA.version}]
    assert zenodo.records[SECOND]["parent"] == PARENT
    assert zenodo.content(SECOND) == {name: (second.files / name).read_bytes() for name in NAMES}
    assert zenodo.records[SECOND]["metadata"] == metadata(second, publish.Release(TODAY, doi, CONCEPT))
    assert second.section("What changed in this version").startswith(
        f"Corrections.\n\nCompared with version 1, published {TODAY}: "
        f"[10.5072/zenodo.{FIRST}](https://doi.org/10.5072/zenodo.{FIRST}).")


def test_another_version_was_published_since(tmp_path, zenodo):
    published_first(tmp_path, zenodo)
    by_hand = zenodo.publish_by_hand(FIRST)
    assert fails(next_merge(tmp_path), zenodo) == (
        f"The latest version on Zenodo has the DOI 10.5072/zenodo.{by_hand}, but the last version in zenodo.yaml, 1, "
        f"has 10.5072/zenodo.{FIRST}. Every version has to be uploaded with publish.py, so that the next one can say "
        "what changed since it.")
    assert zenodo.drafts() == []


def test_the_last_version_does_not_hold_what_was_published(tmp_path, zenodo):
    first = published_first(tmp_path, zenodo)
    (first.files / "Germplasm.csv").write_text("GPID\n", encoding="utf-8")
    (first.files / "README.md").unlink()
    assert fails(next_merge(tmp_path), zenodo) == (
        f"The files of version 1 on Zenodo are not those in {first.files}: Germplasm.csv differs, README.md is only "
        "on Zenodo. What changed since it is worked out from those files, so they have to be what was published.")


def test_access_that_changed(tmp_path, zenodo):
    first = published_first(tmp_path, zenodo)
    text = first.zenodo.read_text(encoding="utf-8")
    first.zenodo.write_text(text.replace("access: open", "access: restricted"), encoding="utf-8")
    assert fails(next_merge(tmp_path), zenodo) == (
        "The files of the latest version are public on Zenodo, but zenodo.yaml has access: restricted. Correct "
        "zenodo.yaml, or, if the access is to change, change it on Zenodo first, by hand.")
    assert zenodo.drafts() == []


def test_the_last_version_is_not_on_this_zenodo(tmp_path, zenodo):
    first = Merge(tmp_path / "dataset", "2026-11-01")
    first.upload(publish.Release("2026-11-01", "10.5072/zenodo.1", "10.5072/zenodo.0"), "1")
    assert fails(next_merge(tmp_path), zenodo) == (
        f"Version 1, in {first.folder}, was uploaded to {zenodo.address} as the draft 1, but no version of it is "
        "published. Publish it first.")


def test_the_last_version_is_not_published_yet(tmp_path, zenodo):
    first = Merge(tmp_path / "dataset", "2026-11-01")
    run(first, zenodo)
    assert fails(next_merge(tmp_path), zenodo) == (
        f"Version 1, in {first.folder}, was uploaded to {zenodo.address} as the draft {FIRST}, but no version of it "
        "is published. Publish it first.")


def test_the_sandbox_and_zenodo_keep_their_versions_apart(merge, zenodo):
    """The same folder can be uploaded to both: each lists it in its own file, and makes its own draft."""
    run(merge, zenodo, state="sandbox.yaml")
    assert [version["id"] for version in versions(merge, "sandbox.yaml")] == [FIRST]
    assert "versions" not in merge.state()
    run(merge, zenodo)
    on_sandbox, on_zenodo = zenodo.drafts()
    assert on_sandbox == FIRST and on_zenodo != FIRST
    assert [version["id"] for version in versions(merge)] == [on_zenodo]
    assert zenodo.records[on_zenodo]["parent"] != zenodo.records[on_sandbox]["parent"]
    assert merge.state()["doi"] != merge.state("sandbox.yaml")["doi"]


# ---------------------------------------------------------------- What goes wrong on Zenodo

def test_zenodo_finds_problems_in_the_metadata(merge, zenodo):
    zenodo.errors = [{"field": "metadata.creators.0.affiliations.0.id", "messages": ["Invalid value."]},
                     {"field": "metadata.funding.0.funder.id", "messages": ["Invalid value.", "Unknown funder."]}]
    assert fails(merge, zenodo) == (
        f"The draft is on Zenodo, at {zenodo.address}/uploads/{FIRST}, but Zenodo found problems in its metadata, so "
        "it cannot be published: metadata.creators.0.affiliations.0.id: Invalid value.; metadata.funding.0.funder.id: "
        "Invalid value. Unknown funder. Correct zenodo.yaml or the merge, or build.py if it builds the metadata "
        "wrong, and run publish.py again.")
    assert [version["id"] for version in versions(merge)] == [FIRST]


def test_a_lost_doi(merge, zenodo):
    run(merge, zenodo)
    zenodo.records[FIRST]["pids"] = {}
    zenodo.records[FIRST]["lost"] = True
    assert fails(merge, zenodo) == (
        f"The draft has no DOI, and Zenodo will not reserve one: Zenodo answered POST /api/records/{FIRST}/draft/pids/"
        "doi with 400 Bad Request: A PID already exists for type doi. This happens when a DOI was reserved, and then "
        f"lost. Delete the draft on Zenodo, at {zenodo.address}/uploads/{FIRST}, and run publish.py again, which makes "
        "a new one.")
    zenodo.delete(FIRST)
    said = []
    run(merge, zenodo, said=said)
    assert said[0] == f"The draft {FIRST} is no longer on {zenodo.address}, so a new one is made."
    new = versions(merge)[0]["id"]
    assert zenodo.drafts() == [new] and new != FIRST
    assert len(versions(merge)) == 1
    assert f"10.5072/zenodo.{new}" in merge.readme()


def test_a_wrong_token(merge, zenodo):
    message = fails(merge, zenodo, token="wrong-token")
    assert message == "Zenodo answered POST /api/records with 403 Forbidden: Permission denied."
    assert TOKEN not in message and "wrong-token" not in message


def test_zenodo_cannot_be_reached(merge, no_proxy):
    with pytest.raises(publish.PublishError) as e:
        publish.publish(merge.folder, publish.Zenodo("http://127.0.0.1:9", TOKEN), COMMIT, TODAY,
                        online=lambda address: True)
    assert str(e.value).startswith("Could not reach http://127.0.0.1:9: ")
    assert str(e.value).endswith(". Check the connection, and run publish.py again.")


def test_the_doi_of_all_versions():
    draft = {"id": "17", "parent": {"id": "16"}}
    assert publish.concept_doi(draft, "10.5281/zenodo.17") == "10.5281/zenodo.16"
    known = draft | {"parent": {"id": "16", "pids": {"doi": {"identifier": "10.5281/zenodo.16"}}}}
    assert publish.concept_doi(known, "10.5281/other.17") == "10.5281/zenodo.16"
    with pytest.raises(publish.PublishError) as e:
        publish.concept_doi(draft, "10.5281/other.17")
    assert str(e.value).startswith("Zenodo reserved the DOI 10.5281/other.17, which is not <prefix>/zenodo.17, so")


# ---------------------------------------------------------------- What is checked before anything is sent

def test_tables_that_do_not_pass(merge, zenodo):
    merge.tables.set("Phenotype", SCORE, "Score", "high")
    with pytest.raises(ValidationError):
        run(merge, zenodo)
    assert zenodo.requests == []
    assert "versions" not in merge.state()


COMMIT_PAGE = f"https://github.com/fababase/phenotype-database-format/tree/{COMMIT}"
DIAGRAM_PICTURE = f"https://fababase.github.io/phenotype-database-format/diagram/{SCHEMA.version}/diagram.png"


@pytest.mark.parametrize("missing, asked, message", [
    (COMMIT_PAGE, [COMMIT_PAGE],
     f"The commit {COMMIT}, which the copy of the repository is at, is not on GitHub, at "
     "https://github.com/fababase/phenotype-database-format. The README links to it, so push it first, or clone the "
     "repository again."),
    (DIAGRAM_PICTURE, [COMMIT_PAGE, DIAGRAM_PICTURE],
     f"The diagram of version {SCHEMA.version} of the format is not online, at "
     f"https://fababase.github.io/phenotype-database-format/diagram/#{SCHEMA.version}. The README links to it, so "
     "publish the app first: see docs/deploy-app.md."),
])
def test_what_the_readme_links_to_is_online(merge, zenodo, missing, asked, message):
    addresses = []

    def online(address: str) -> bool:
        addresses.append(address)
        return address != missing

    assert fails(merge, zenodo, online=online) == message
    assert addresses == asked
    assert zenodo.requests == []


def git(folder: Path, *arguments: str) -> None:
    subprocess.run(["git", "-C", str(folder), "-c", "user.name=Test", "-c", "user.email=test@example.org",
                    *arguments], check=True, capture_output=True)


def test_the_copy_of_the_repository_has_no_changes(tmp_path):
    folder = tmp_path / "repository"
    folder.mkdir()
    git(folder, "init")
    (folder / "a.txt").write_text("a\n", encoding="utf-8")
    git(folder, "add", "a.txt")
    git(folder, "commit", "-m", "First")
    assert re.fullmatch(r"[0-9a-f]{40}", publish.clean_commit(folder))
    (folder / "a.txt").write_text("b\n", encoding="utf-8")
    (folder / "b.txt").write_text("b\n", encoding="utf-8")
    with pytest.raises(publish.PublishError) as e:
        publish.clean_commit(folder)
    assert str(e.value) == (f"The copy of the repository in {folder} has changes that are not committed: a.txt, "
                            "b.txt. The README links to its commit, so it has to be as that commit is on GitHub. Undo "
                            "the changes, or clone the repository again.")


# ---------------------------------------------------------------- Running it

def test_command_line(merge, zenodo, tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(publish, "SANDBOX", zenodo.address)
    monkeypatch.setattr(publish, "clean_commit", lambda: COMMIT)
    monkeypatch.setattr(publish, "is_online", lambda address: True)
    token_file = tmp_path / "token"
    token_file.write_text(f"{TOKEN}\n", encoding="utf-8")
    assert publish.main([str(merge.folder), "--token-file", str(token_file), "--sandbox"]) == 0
    out = capsys.readouterr().out
    assert out.splitlines()[-4].startswith(f"Uploaded version 1 of Nordbean test dataset to a draft on "
                                           f"{zenodo.address}: ")
    assert "Uploading Phenotype.csv, " in out
    assert TOKEN not in out
    assert [version["id"] for version in versions(merge, "sandbox.yaml")] == [FIRST]
    assert "versions" not in merge.state()

    assert publish.main([str(merge.folder), "--token-file", str(tmp_path / "none")]) == 1
    assert capsys.readouterr().out == (
        f"Stopped: Could not read the token file {tmp_path / 'none'}: No such file or directory. Make a personal "
        "access token on https://zenodo.org/account/settings/applications/tokens/new/, with the scopes deposit:write "
        "and deposit:actions, and save it in a file, on its own.\n")
    token_file.write_text("token: secret\n", encoding="utf-8")
    assert publish.main([str(merge.folder), "--token-file", str(token_file)]) == 1
    assert capsys.readouterr().out == f"Stopped: The token file {token_file} has to hold the token, and nothing else.\n"

    token_file.write_text(TOKEN, encoding="utf-8")
    merge.zenodo.unlink()
    assert publish.main([str(merge.folder), "--token-file", str(token_file), "--sandbox"]) == 1
    assert capsys.readouterr().out.startswith("Stopped: There is no zenodo.yaml")


def test_the_script_runs_with_the_validators_packages():
    """uv runs publish.py with the packages listed at its top, which are those of build.py."""
    def block(name: str) -> str:
        text = (ROOT / "publishing" / name).read_text(encoding="utf-8")
        return re.search(r"# /// script\n(.*?)# ///\n", text, re.DOTALL)[1]

    assert block("publish.py") == block("build.py")
