"""
Checks the browser app that the deploy Action builds, before it is published. Not run by pytest:

    python tests/check_browser_app.py <folder of the built site>

Checks that the packages bundled with the app are the versions in app/requirements.txt. Then opens the app in a
browser and checks that it starts without notices, so it runs those versions, and that it shows the same messages
as the validator run here: for the valid dataset as CSV files, whose tables it then downloads, and for the blank
collection sheet. Needs playwright and its Chromium.
"""
import functools
import http.server
import json
import sys
import threading
import zipfile
from pathlib import Path

from playwright.sync_api import expect, sync_playwright

TESTS = Path(__file__).resolve().parent
sys.path.insert(0, str(TESTS.parent / "app"))

from validation import (Table, ValidationError, load_schema, summary, tested_versions,  # noqa: E402
                        validate_files)

SCHEMA = load_schema()
UPLOADS = [sorted((TESTS / "valid").iterdir()), [TESTS.parent / "template" / "collection-sheet.xlsx"]]
# Milliseconds to wait for the app. The first start downloads Python and the packages.
TIMEOUT = 180_000


class QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args) -> None:
        pass


def expected(paths: list[Path]) -> tuple[list[str], dict[str, Table]]:
    """The message lines the app should show for these files, and the tables it should hand back."""
    lines = []
    try:
        tables = validate_files([(path.name, path) for path in paths], SCHEMA,
                                notice=lambda message: lines.append(f"Notice: {message}"))
    except ValidationError as e:
        return lines + [f"Validation failed: {e}"], {}
    return lines + summary(tables, SCHEMA), tables


def check_bundled_versions(site: str) -> None:
    """The packages bundled with the app are the versions in requirements.txt. The others are installed as pinned."""
    lock = json.loads((Path(site) / "shinylive" / "pyodide" / "pyodide-lock.json").read_text(encoding="utf-8"))
    tested = tested_versions()
    bundled = {package: lock["packages"][package.lower()]["version"]
               for package in tested if package.lower() in lock["packages"]}
    differ = [f"{package}=={version}" for package, version in bundled.items() if version != tested[package]]
    assert not differ, ("The browser app has other package versions than app/requirements.txt. "
                        f"Put these in it: {', '.join(differ)}")
    print(f"The bundled packages are the versions in app/requirements.txt: {', '.join(bundled)}.")


def main(site: str) -> None:
    check_bundled_versions(site)
    server = http.server.ThreadingHTTPServer(("localhost", 0), functools.partial(QuietHandler, directory=site))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page()
        page.goto(f"http://localhost:{server.server_port}/")
        app = page.frame_locator("iframe")
        intro = app.locator(".card").first
        try:
            expect(intro).to_contain_text(f"Checks against schema version {SCHEMA.version}.", timeout=TIMEOUT)
        except AssertionError:
            # If the app does not start, e.g. as a package in requirements.txt has no browser version, the page says why
            print(page.locator("body").inner_text())
            raise
        assert "Notice:" not in intro.inner_text(), intro.inner_text()
        print("The app starts, with the package versions in app/requirements.txt.")

        for paths in UPLOADS:
            lines, tables = expected(paths)
            app.locator("input[type=file]").set_input_files(paths)
            expect(app.locator("#reactive_message > div")).to_have_text(lines, timeout=TIMEOUT)
            if tables:
                with page.expect_download(timeout=TIMEOUT) as download:
                    app.get_by_text("Download tables as CSV").click()
                with zipfile.ZipFile(download.value.path()) as archive:
                    downloaded = {name: archive.read(name).decode("utf-8") for name in archive.namelist()}
                assert downloaded == {f"{name}.csv": table.to_csv() for name, table in tables.items()}
            print(f"{len(paths)} file(s): {next(line for line in lines if line.startswith('Validation'))}")
        browser.close()
    server.shutdown()


if __name__ == "__main__":
    main(sys.argv[1])
