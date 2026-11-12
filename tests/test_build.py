"""
publishing/build.py, which builds what goes to Zenodo from a merge: the tables, their README and the record's
metadata. Each test builds from a merge folder whose merged tables are the valid dataset, changed where the test
says, and the code in the README's Quick start is run on what it builds.
"""
import csv
import json
import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest

import build
from helpers import COMMIT, GREENHOUSE, ROOT, SCHEMA, SCORE, TRIAL, Merge
import validation
from validation import CONTRIBUTORS_FILE, ValidationError

CONCEPT = "10.5281/zenodo.100"
FIRST = build.Release("2026-11-01", "10.5281/zenodo.101", CONCEPT)
SECOND = build.Release("2026-12-01", "10.5281/zenodo.102", CONCEPT)
HEIGHT = "plant_height_mean_of_5_plants_cm"
# The contribution the valid dataset comes from, as the crosswalk names it, by its folder
NORDBEAN = "2026_10_01_nordbean"
@pytest.fixture
def merge(tmp_path: Path) -> Merge:
    return Merge(tmp_path / "merge")


def published(tmp_path: Path) -> Merge:
    """A merge of the valid dataset, published as the first version."""
    first = Merge(tmp_path / "first")
    first.run(release=FIRST)
    return first


def fails(merge: Merge, previous: Merge | None = None, release: build.Release | None = None) -> str:
    with pytest.raises(build.BuildError) as e:
        merge.run(previous, release)
    return str(e.value)


# ---------------------------------------------------------------- The files

def test_preview_of_the_first_version(merge):
    assert merge.run() == [
        f"Built version 1 of Nordbean test dataset, in schema version 1.0, in {merge.folder / 'publish'}.",
        "It is the first version.",
        "It is a preview: the date and DOI of the version are set when publish.py publishes it.",
    ]
    assert sorted(path.name for path in merge.files.iterdir()) == sorted(
        [f"{name}.csv" for name in SCHEMA.tables] + ["README.md"])
    assert merge.release() == {"version": 1, "publication_date": None, "doi": None, "concept_doi": None,
                               "schema_version": SCHEMA.version, "commit": COMMIT}
    assert "- **Version:** 1, published (set when published).\n" in merge.readme()
    assert "- **DOI:** (set when published). The DOI (set when published) always leads" in merge.readme()
    assert merge.section("What changed in this version") == "This is the first version."


def test_published_version(merge):
    assert merge.run(release=FIRST)[-1] == "It is the first version."
    assert merge.release() == {"version": 1, "publication_date": "2026-11-01", "doi": "10.5281/zenodo.101",
                               "concept_doi": CONCEPT, "schema_version": SCHEMA.version, "commit": COMMIT}
    readme = merge.readme()
    assert "- **Version:** 1, published 2026-11-01.\n" in readme
    assert ("- **DOI:** [10.5281/zenodo.101](https://doi.org/10.5281/zenodo.101). The DOI "
            "[10.5281/zenodo.100](https://doi.org/10.5281/zenodo.100) always leads to the latest version.") in readme
    assert merge.metadata()["publication_date"] == "2026-11-01"


def test_the_tables_are_published_as_merged(merge):
    merge.run()
    for name in SCHEMA.tables:
        assert (merge.files / f"{name}.csv").read_bytes() == merge.tables.path(name).read_bytes(), name


def test_missing_values_are_empty_and_every_table_is_there(merge):
    merge.tables.set("Germplasm", "ostrin", "Comments", "NA")
    merge.tables.drop_column("Germplasm", "Donor")
    merge.tables.drop_table("Management")
    merge.run()
    assert [row["Comments"] for row in merge.rows("Germplasm") if row["GPID"] == "ostrin"] == [""]
    assert {row["Donor"] for row in merge.rows("Germplasm")} == {""}
    assert (merge.files / "Management.csv").read_text(encoding="utf-8") == \
        ",".join(SCHEMA.tables["Management"].columns) + "\n"


def test_the_same_every_time(merge):
    merge.run()
    first = {path.name: path.read_bytes() for path in merge.folder.joinpath("publish").rglob("*") if path.is_file()}
    merge.run()
    again = {path.name: path.read_bytes() for path in merge.folder.joinpath("publish").rglob("*") if path.is_file()}
    assert first == again


# ---------------------------------------------------------------- The README

def test_every_place_in_the_template_is_filled_in(merge):
    merge.run()
    readme = merge.readme()
    assert readme.startswith("# Nordbean test dataset\n\nPhenotype data from plant experiments")
    assert "{{" not in readme
    assert "<!--" not in readme
    assert readme.endswith(f"[https://github.com/fababase/phenotype-database-format]"
                           f"(https://github.com/fababase/phenotype-database-format/tree/{COMMIT}).\n")
    assert "[diagram](https://fababase.github.io/phenotype-database-format/diagram/#1.0)" in readme


def test_at_a_glance(merge):
    merge.run()
    assert merge.section("At a glance") == ("- 2 experiments, run in 2025\n- 3 germplasm, in 4 seed lots\n- 12 units\n"
                                            "- 3 traits, with 20 scores")


def test_years_of_experiments_over_several_years_or_none(merge):
    merge.tables.set("Experiment", TRIAL, "EndDate", "2026-08-26")
    merge.tables.set("Experiment", GREENHOUSE, "StartDate", "")
    merge.tables.set("Experiment", GREENHOUSE, "EndDate", "")
    merge.run()
    assert merge.section("At a glance").splitlines()[0] == "- 2 experiments, run from 2025 to 2026"
    experiments = merge.section("Experiments")
    assert f"| `{TRIAL}` | 2025–2026 | [" in experiments
    assert f"| `{GREENHOUSE}` | | [" in experiments
    assert merge.metadata()["dates"] == [{"date": "2025-04-08/2026-08-26", "type": {"id": "collected"}}]


def test_experiments(merge):
    merge.tables.set("Experiment", GREENHOUSE, "GPSCoordinates", "")
    merge.run()
    assert merge.section("Experiments").split("\n\n")[0] == (
        "| Experiment | Years | Place | Units | Germplasm | Traits | People |\n"
        "|---|---|---|---|---|---|---|\n"
        f"| `{TRIAL}` | 2025 | [56.091250, 9.552040](https://www.openstreetmap.org/?mlat=56.091250&mlon=9.552040"
        "#map=15/56.091250/9.552040) | 8 | 2 | 1 | Rhea Plicate |\n"
        f"| `{GREENHOUSE}` | 2025 | | 4 | 2 | 2 | Ann Ova, Rhea Plicate |")


def test_traits_and_climate_variables(merge):
    merge.run()
    measured = merge.section("What was measured")
    assert ("| PDID | Trait | Unit | Class | Scores | Experiments |\n|---|---|---|---|---|---|\n"
            "| `flower_colour_visual_1to3` | Flower colour | code | Morphological | 4 | 1 |\n"
            "| `leaf_absorbance_nirs_dried_powder` | Leaf absorbance | absorbance | Biochemical | 8 | 1 |\n"
            f"| `{HEIGHT}` | Plant height | cm | Morphological | 8 | 1 |\n") in measured
    assert ("| `soil_water_content_20cm_percent` | Soil water content at 20 cm | percent by volume | Water | 2 | 1 |"
            in measured)


def test_no_climate_data(merge):
    merge.tables.drop_table("Climate")
    merge.tables.drop_table("ClimateDescription")
    merge.run()
    assert "### Climate variables\n\nThere are no climate data in this dataset.\n" in merge.readme()


def test_files_links_and_tables(merge):
    merge.run()
    files = merge.section("The files")
    assert "| [`Phenotype.csv`](#phenotype) | one score of one trait on one unit | 20 |" in files
    assert ("| [`ExperimentalUnit.csv`](#experimentalunit) | a unit in an experiment: a field plot, a pot, a "
            "sample, … | 12 |") in files
    links = merge.section("How the tables link")
    assert "| `SeedLot.ParentSLID` | [SeedLot](#seedlot) |" in links
    assert "| `Phenotype.Features` | [Features](#features), one or more: see [Features cells](#features-cells) |" \
           in links
    tables = merge.section("The tables")
    for name, table in SCHEMA.tables.items():
        assert f"### {name}\n\n`{name}.csv`: one row is " in tables
        for column in table.columns:
            assert f"\n| {column} | " in tables.split(f"### {name}\n")[1].split("\n### ")[0], (name, column)
    assert "`ExperimentalUnit.csv`: one row is a unit in an experiment: a field plot, a pot, a sample, …\n" in tables
    assert "| UNID | ID | No | [ExperimentalUnit](#experimentalunit) | Unit the measurement belongs to. **Empty or " \
           "missing means all units in the experiment.** |" in tables
    assert "| Features | Feature list | No | [Features](#features) | Features of this score. See " \
           "[Features cells](#features-cells). |" in tables


def test_who_made_it(merge):
    merge.tables.edit_contributors("        ror: none", "        ror: 01aj84f44")
    merge.run()
    assert merge.section("Who made it") == (
        "| Name | ORCID | Affiliations | Experiments |\n|---|---|---|---|\n"
        f"| Ann Ova | | [Northfield Agricultural College](https://ror.org/01aj84f44) | `{GREENHOUSE}` |\n"
        "| Rhea Plicate | [0000-0002-1825-0097](https://orcid.org/0000-0002-1825-0097) | Northfield Agricultural "
        f"College; Nordbean Breeding Programme | `{TRIAL}`, `{GREENHOUSE}` |\n\n"
        "### Funding\n\n"
        "| Funder | Grant number | Grant title | Experiments |\n|---|---|---|---|\n"
        f"| Nordic Bean Foundation | NBF-2024-117 | Drought tolerance in faba bean | `{TRIAL}` |\n\n"
        "The dataset is looked after by Dana Keeper (Northfield Agricultural College).")


def test_no_funding_and_a_curator_with_an_orcid_id(tmp_path):
    merge = Merge(tmp_path / "merge", orcid="0000-0002-1825-0097")
    text = merge.tables.contributors.read_text(encoding="utf-8")
    merge.tables.contributors.write_text(text[:text.index("funding:")] + "funding: none\n", encoding="utf-8")
    merge.run()
    assert "### Funding\n\nThere was no specific funding.\n" in merge.readme()
    assert ("The dataset is looked after by Dana Keeper (Northfield Agricultural College; ORCID "
            "[0000-0002-1825-0097](https://orcid.org/0000-0002-1825-0097)).") in merge.readme()


def test_text_from_the_data_is_shown_as_it_is(merge):
    merge.tables.set("PhenotypeDescription", HEIGHT, "PhenotypeDescription", "Plant *height* [main_stem]")
    merge.run()
    assert f"| `{HEIGHT}` | Plant \\*height\\* \\[main\\_stem\\] | cm |" in merge.readme()


def test_citation(merge):
    merge.run(release=FIRST)
    assert merge.section("How to cite").startswith(
        "> Ova, A., & Plicate, R. (2026). *Nordbean test dataset* (Version 1) [Data set]. Zenodo. "
        "https://doi.org/10.5281/zenodo.101\n")


def test_citation_of_a_preview(merge):
    merge.run()
    assert merge.section("How to cite").startswith(
        "> Ova, A., & Plicate, R. (set when published). *Nordbean test dataset* (Version 1) [Data set]. Zenodo. "
        "(set when published)\n")


@pytest.mark.parametrize("people, authors", [
    ([("Plicate", "Rhea")], "Plicate, R."),
    ([("Plicate", "Rhea Ann"), ("Ova", None)], "Plicate, R. A., & Ova"),
    ([("Plicate", "Jean-Luc"), ("Ova", "Ann"), ("Bean", "Fava")], "Plicate, J.-L., Ova, A., & Bean, F."),
    ([(f"P{i}", "Ann") for i in range(21)], ", ".join(f"P{i}, A." for i in range(19)) + ", . . . P20, A."),
])
def test_authors_in_a_citation(people, authors):
    found = build.citation([build.Person(family, given, None, [], []) for family, given in people], "2026", "T", 1,
                           "10.5281/zenodo.1")
    assert found == f"> {authors} (2026). *T* (Version 1) [Data set]. Zenodo. https://doi.org/10.5281/zenodo.1"


# ---------------------------------------------------------------- The template

def test_a_template_is_filled_in():
    template = "<!--\nNames:\n  {{a}}  the first\n  {{b}}  the second\n-->\n\n# {{a}}\n\n{{b}} and {{a}}\n\n"
    assert build.render(template, {"a": "A", "b": "{{a}}"}) == "# A\n\n{{a}} and A\n"


@pytest.mark.parametrize("template, values, problems", [
    ("<!--\n  {{a}}  x\n-->\n# {{a}} {{b}}\n", {"a": ""},
     "it uses {{b}}, which the list at its top does not name; it uses {{b}}, which build.py does not fill in"),
    ("<!--\n  {{a}}  x\n  {{b}}  y\n-->\n# {{a}}\n", {"a": "", "b": ""},
     "its list at the top names {{b}}, which it does not use; build.py fills in {{b}}, which it does not use"),
])
def test_a_template_that_does_not_fit(template, values, problems):
    with pytest.raises(build.BuildError) as e:
        build.render(template, values)
    assert str(e.value) == f"README_TEMPLATE.md: {problems}."


# ---------------------------------------------------------------- Quick start

def quick_start(language: str) -> str:
    """The code in a language in the Quick start of the template."""
    template = build.TEMPLATE.read_text(encoding="utf-8")
    return re.search(rf"```{language}\n(.*?)```", template, re.DOTALL)[1]


def expected_counts(merge: Merge) -> list[int]:
    """How many scores, feature values of units, and climate values for each unit there are, counted by hand."""
    units = merge.rows("ExperimentalUnit")
    climate = merge.rows("Climate")
    features = sum(len(unit["Features"].split(";")) for unit in units if unit["Features"])
    per_unit = sum(1 if row["UNID"] else sum(unit["EXPID"] == row["EXPID"] for unit in units) for row in climate)
    return [len(merge.rows("Phenotype")), features, per_unit]


def test_quick_start_in_python(merge, monkeypatch):
    merge.run()
    monkeypatch.chdir(merge.files)
    found = {}
    exec(quick_start("python"), found)
    assert [len(found["scores"]), len(found["unit_features"]), len(found["climate_per_unit"])] == \
        expected_counts(merge)
    assert list(found["scores"].columns) == ["PHID", "UNID", "PDID", "Date", "Score", "PhenotypeDescription", "Unit",
                                             "EXPID", "SLID", "Block", "GPID", "Name", "Intervention"]
    assert found["scores"]["Intervention"].notna().sum() == 8
    assert list(found["unit_features"].columns) == ["UNID", "FTID", "Value"]


def test_quick_start_in_r(merge, tmp_path):
    rscript = shutil.which("Rscript")
    if not rscript:
        if os.environ.get("CI"):
            pytest.fail("Rscript is not installed, so the R code in the Quick start cannot be run.")
        pytest.skip("Rscript is not installed")
    merge.run()
    script = tmp_path / "quick_start.R"
    script.write_text(quick_start("r") + "\ncat(nrow(scores), nrow(unit_features), nrow(climate_per_unit), "
                                         "sum(!is.na(scores$Intervention)), '\\n')\n", encoding="utf-8")
    result = subprocess.run([rscript, str(script)], cwd=merge.files, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    assert result.stdout.split() == [str(n) for n in expected_counts(merge) + [8]]


# ---------------------------------------------------------------- The metadata

def test_metadata(merge):
    merge.tables.edit_contributors("        ror: none", "        ror: 01aj84f44")
    merge.tables.edit_contributors("    ror: none\n    grant_number", "    ror: 05gq02987\n    grant_number")
    merge.run()
    data = merge.metadata()
    assert list(data) == ["resource_type", "title", "creators", "contributors", "version", "description",
                          "publisher", "rights", "languages", "subjects", "dates", "locations", "funding",
                          "related_identifiers"]
    assert data["creators"] == [
        {"person_or_org": {"type": "personal", "family_name": "Ova", "given_name": "Ann"},
         "affiliations": [{"id": "01aj84f44"}]},
        {"person_or_org": {"type": "personal", "family_name": "Plicate", "given_name": "Rhea",
                           "identifiers": [{"scheme": "orcid", "identifier": "0000-0002-1825-0097"}]},
         "affiliations": [{"name": "Northfield Agricultural College"}, {"name": "Nordbean Breeding Programme"}]},
    ]
    assert data["contributors"] == [
        {"person_or_org": {"type": "personal", "family_name": "Keeper", "given_name": "Dana"},
         "affiliations": [{"name": "Northfield Agricultural College"}], "role": {"id": "datacurator"}}]
    assert data["version"] == "1"
    assert data["title"] == "Nordbean test dataset"
    assert data["subjects"] == [{"subject": "Vicia faba"}]
    assert data["dates"] == [{"date": "2025-03-03/2025-08-26", "type": {"id": "collected"}}]
    assert data["locations"] == {"features": [
        {"geometry": {"type": "Point", "coordinates": [9.55204, 56.09125]}, "place": TRIAL},
        {"geometry": {"type": "Point", "coordinates": [9.5488, 56.0931]}, "place": GREENHOUSE}]}
    assert data["funding"] == [{"funder": {"id": "05gq02987"},
                                "award": {"number": "NBF-2024-117",
                                          "title": {"en": "Drought tolerance in faba bean"}}}]
    assert data["related_identifiers"] == [
        {"identifier": f"https://github.com/fababase/phenotype-database-format/tree/{COMMIT}", "scheme": "url",
         "relation_type": {"id": "isdocumentedby"}, "resource_type": {"id": "software"}}]
    assert data["description"].startswith("<p>Phenotype data from plant experiments: the scores of traits")
    assert "<li>2 experiments, run in 2025</li>\n<li>3 germplasm, in 4 seed lots</li>" in data["description"]


def test_the_curator_is_a_contributor_only_if_not_a_creator(tmp_path):
    merge = Merge(tmp_path / "merge", orcid="0000-0002-1825-0097")
    merge.run()
    assert "contributors" not in merge.metadata()


def test_a_grant_without_a_number_has_no_award(merge):
    merge.tables.edit_contributors("grant_number: NBF-2024-117", "grant_number: none")
    merge.run()
    assert merge.metadata()["funding"] == [{"funder": {"name": "Nordic Bean Foundation"}}]


# ---------------------------------------------------------------- What changed

def test_what_changed(tmp_path):
    first = published(tmp_path)
    second = Merge(tmp_path / "second", doi=CONCEPT)
    tables = second.tables
    tables.set("Phenotype", SCORE, "Score", "95")
    tables.delete_row("Phenotype", f"{TRIAL}_000002")
    tables.add_row("Germplasm", GPID="kelda", Name="Kelda")
    tables.set("PhenotypeDescription", HEIGHT, "PDID", "plant_height_cm")
    for phid in tables.ids("Phenotype"):
        if tables.get("Phenotype", phid, "PDID") == HEIGHT:
            tables.set("Phenotype", phid, "PDID", "plant_height_cm")
    tables.edit_contributors("\nfunding:", f"\n  - family_name: Nym\n    given_names: Ano\n    orcid: none\n"
                                           f"    affiliations: none\n    experiments:\n      - {TRIAL}\nfunding:")
    second.crosswalk((NORDBEAN, "PhenotypeDescription", HEIGHT, "plant_height_cm"))
    assert second.run(first, SECOND)[1] == "Compared with version 1."
    assert second.release()["version"] == 2
    assert second.section("What changed in this version") == (
        "Compared with version 1, published 2026-11-01: [10.5281/zenodo.101](https://doi.org/10.5281/zenodo.101).\n\n"
        "| Table | Added | Changed | Renamed | Removed |\n|---|---|---|---|---|\n"
        "| Germplasm | 1 | 0 | 0 | 0 |\n"
        "| PhenotypeDescription | 0 | 0 | 1 | 0 |\n"
        "| Phenotype | 0 | 1 | 0 | 1 |\n\n"
        "- **Germplasm.** Added: `kelda`.\n"
        f"- **PhenotypeDescription.** Renamed: `{HEIGHT}` to `plant_height_cm`.\n"
        f"- **Phenotype.** Changed: Score in `{SCORE}`. Removed: `{TRIAL}_000002`.\n\n"
        "**People.** Added: Ano Nym.")


def test_nothing_changed(tmp_path):
    first = published(tmp_path)
    second = Merge(tmp_path / "second", doi=CONCEPT)
    second.run(first)
    assert second.section("What changed in this version") == (
        "Compared with version 1, published 2026-11-01: [10.5281/zenodo.101](https://doi.org/10.5281/zenodo.101).\n\n"
        "The tables did not change.")


def test_two_rows_made_one_and_a_renamed_feature(tmp_path):
    """
    Two traits of the last version become one, so the scores of one now link to the other. A feature is renamed in
    Features and in the Features cells. Only the renames show, as the rows that link to them did not change.
    """
    first = published(tmp_path)
    second = Merge(tmp_path / "second", doi=CONCEPT)
    tables = second.tables
    tables.delete_row("PhenotypeDescription", "flower_colour_visual_1to3")
    for phid in tables.ids("Phenotype"):
        if tables.get("Phenotype", phid, "PDID") == "flower_colour_visual_1to3":
            tables.set("Phenotype", phid, "PDID", HEIGHT)
    tables.set("Features", "soil_ph", "FTID", "topsoil_ph")
    for unid in tables.ids("ExperimentalUnit"):
        tables.set("ExperimentalUnit", unid, "Features",
                   tables.get("ExperimentalUnit", unid, "Features").replace("soil_ph=", "topsoil_ph="))
    second.crosswalk((NORDBEAN, "PhenotypeDescription", "flower_colour_visual_1to3", HEIGHT),
                     (NORDBEAN, "Features", "soil_ph", "topsoil_ph"))
    second.run(first)
    assert second.section("What changed in this version").split("\n\n")[1:] == [
        "| Table | Added | Changed | Renamed | Removed |\n|---|---|---|---|---|\n"
        "| PhenotypeDescription | 0 | 0 | 1 | 0 |\n"
        "| Features | 0 | 0 | 1 | 0 |",
        f"- **PhenotypeDescription.** Renamed: `flower_colour_visual_1to3` to `{HEIGHT}`.\n"
        "- **Features.** Renamed: `soil_ph` to `topsoil_ph`.",
    ]


def test_many_changes_are_counted(tmp_path, monkeypatch):
    monkeypatch.setattr(build, "LIMIT", 2)
    first = published(tmp_path)
    second = Merge(tmp_path / "second", doi=CONCEPT)
    for phid in second.tables.ids("Phenotype")[:3]:
        second.tables.set("Phenotype", phid, "Comments", "Checked again.")
    second.tables.set("Phenotype", SCORE, "Score", "95")
    second.run(first)
    assert f"- **Phenotype.** Changed: Score in `{SCORE}`; Comments in 3 rows.\n" in second.readme()


def test_people_and_funding_that_left(tmp_path):
    first = published(tmp_path)
    second = Merge(tmp_path / "second", doi=CONCEPT)
    text = second.tables.contributors.read_text(encoding="utf-8")
    text = text[:text.index("  - family_name: Ova")] + text[text.index("  - family_name: Plicate"):]
    second.tables.contributors.write_text(text[:text.index("funding:")] + "funding: none\n", encoding="utf-8")
    second.run(first)
    assert second.section("What changed in this version").split("\n\n")[1:] == [
        "The tables did not change.",
        "**People.** Removed: Ann Ova.",
        "**Funding.** Removed: Nordic Bean Foundation, grant NBF-2024-117.",
    ]


def test_the_version_of_the_format_with_a_zero_at_the_end_is_the_same(tmp_path):
    """The last version was published when version 1.0 of the format was written 1.0.0."""
    first = published(tmp_path)
    path = first.folder / "publish" / "release.json"
    release = json.loads(path.read_text(encoding="utf-8")) | {"schema_version": f"{SCHEMA.version}.0"}
    path.write_text(json.dumps(release), encoding="utf-8")
    second = Merge(tmp_path / "second", doi=CONCEPT)
    second.run(first)
    assert "The format changed" not in second.readme()


def test_a_new_version_of_the_format(tmp_path):
    """The last version followed another version of the format, which had a column that is gone, and not one."""
    first = published(tmp_path)
    path = first.folder / "publish" / "release.json"
    path.write_text(json.dumps(json.loads(path.read_text(encoding="utf-8")) | {"schema_version": "0.9"}),
                    encoding="utf-8")
    germplasm = first.files / "Germplasm.csv"
    with germplasm.open(encoding="utf-8", newline="") as f:
        rows = [{column: value for column, value in row.items() if column != "Maintaining"} | {"Pedigree": ""}
                for row in csv.DictReader(f)]
    with germplasm.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    second = Merge(tmp_path / "second", doi=CONCEPT)
    second.run(first)
    assert second.section("What changed in this version").split("\n\n")[1:] == [
        "The format changed from version 0.9 to version 1.0. The [diagram]"
        "(https://fababase.github.io/phenotype-database-format/diagram/#1.0) shows each version: choose one in its "
        "menu.",
        "| Table | Added | Changed | Renamed | Removed |\n|---|---|---|---|---|\n| Germplasm | 0 | 0 | 0 | 0 |",
        "- **Germplasm.** New columns: Maintaining. Columns no longer in the format: Pedigree.",
    ]


# ---------------------------------------------------------------- What it stops at

def test_no_record(merge):
    merge.record.unlink()
    assert fails(merge).startswith(f"There is no record.yaml in {merge.folder}. Copy it from the last merge")


@pytest.mark.parametrize("old, new, message", [
    ("title: Nordbean test dataset\n", "", "record.yaml, line 1: the file has no 'title'. Add it."),
    ("doi: none", "doi: https://doi.org/10.5281/zenodo.100",
     "record.yaml, line 2: 'https://doi.org/10.5281/zenodo.100' is not a DOI, which starts with 10. and a '/'. "
     "Write it without https://doi.org/ in front, or write none before the first version is published."),
    ("access: open\n", "", "record.yaml, line 1: the file has no 'access'. Add it."),
    ("access: open", "access: public",
     "record.yaml, line 3: 'public' is not a kind of access. Write open, if anyone may download the files, or "
     "restricted, if only those given access on Zenodo may."),
    ("orcid: none", "orcid: 0000-0002-1825-0098",
     "record.yaml, line 7: '0000-0002-1825-0098' is not an ORCID iD: its last character, which checks the others, "
     "does not fit them. Copy it again from orcid.org."),
])
def test_record_that_does_not_fit_its_format(merge, old, new, message):
    merge.record.write_text(merge.record.read_text(encoding="utf-8").replace(old, new, 1), encoding="utf-8")
    assert fails(merge) == message


def test_tables_that_do_not_pass(merge):
    merge.tables.set("Phenotype", SCORE, "Score", "high")
    with pytest.raises(ValidationError):
        merge.run()
    assert not (merge.folder / "publish").exists()


def test_no_contributors_file(merge):
    (merge.tables.folder / CONTRIBUTORS_FILE).unlink()
    assert fails(merge) == (f"There is no contributors.yaml in {merge.tables.folder}. merge.py writes it, with who to "
                            "credit.")


def test_a_published_dataset_needs_the_last_merge(tmp_path):
    merge = Merge(tmp_path / "merge", doi=CONCEPT)
    assert fails(merge) == (f"record.yaml gives the DOI {CONCEPT}, so the dataset has been published before. Give the "
                            "folder of the merge that published the last version, with --previous.")


def test_a_first_version_has_no_last_merge(tmp_path):
    first = published(tmp_path)
    merge = Merge(tmp_path / "merge")
    assert fails(merge, first) == ("record.yaml has doi: none, so this would be the first version, but a last merge "
                                   "was given. If the dataset has been published, write its DOI of all versions in it.")


def test_the_last_merge_was_not_published(tmp_path):
    first = Merge(tmp_path / "first")
    first.run()
    merge = Merge(tmp_path / "merge", doi=CONCEPT)
    assert fails(merge, first) == (f"The merge in {first.folder} was not published: publish/release.json has no DOI or "
                                   "date. Give the folder of the merge that was published as the last version.")


def test_the_last_merge_has_no_contributors_file(tmp_path):
    first = published(tmp_path)
    (first.tables.folder / CONTRIBUTORS_FILE).unlink()
    merge = Merge(tmp_path / "merge", doi=CONCEPT)
    assert fails(merge, first) == (f"The last merge, in {first.folder}, has no tables/contributors.yaml, which says "
                                   "who made the last version.")


def test_the_last_merge_is_of_another_dataset(tmp_path):
    first = published(tmp_path)
    merge = Merge(tmp_path / "merge", doi="10.5281/zenodo.200")
    assert fails(merge, first) == (f"The last merge, in {first.folder}, published a version of {CONCEPT}, but "
                                   "record.yaml gives 10.5281/zenodo.200. Give the last merge of this dataset.")


def test_zenodo_has_another_doi_for_the_dataset(tmp_path):
    first = published(tmp_path)
    merge = Merge(tmp_path / "merge", doi=CONCEPT)
    release = build.Release("2026-12-01", "10.5281/zenodo.202", "10.5281/zenodo.200")
    assert fails(merge, first, release) == (f"The DOI of all versions is 10.5281/zenodo.200 on Zenodo, but {CONCEPT} "
                                            "in record.yaml.")


@pytest.mark.parametrize("rows, header, message", [
    (None, None, "There is no crosswalk.csv in {folder}. merge.py writes it, with one row for each ID it changed in "
                 "each contribution, and the columns Contribution, Table, OldID, NewID. When it changed none, it "
                 "holds only that first row."),
    ((), ("Table", "OldID", "NewID"), "crosswalk.csv: the first row has to be Contribution,Table,OldID,NewID."),
    (((NORDBEAN, "Germplasm", "ostrin"),), None, "crosswalk.csv, row 2 has 3 values, not 4."),
    ((("", "Germplasm", "ostrin_1", "ostrin"),), None,
     "crosswalk.csv, row 2 has an empty value. Each row gives the contribution, the table, the ID in the "
     "contribution and the ID in the merged tables."),
    (((NORDBEAN, "Seeds", "ostrin_1", "ostrin"),), None,
     "crosswalk.csv, row 2: 'Seeds' is not a table in the merged tables."),
    (((NORDBEAN, "Germplasm", "ostrin", "kelda"),), None,
     "crosswalk.csv, row 2: 'kelda' is not a GPID in the merged tables."),
    (((NORDBEAN, "Germplasm", "ostrin_1", "ostrin"), (NORDBEAN, "Germplasm", "ostrin_1", "vandrel")), None,
     f"crosswalk.csv, row 3: the GPID 'ostrin_1' of {NORDBEAN} is listed twice. Keep only one."),
])
def test_a_crosswalk_that_does_not_fit(merge, rows, header, message):
    if rows is None:
        (merge.folder / "crosswalk.csv").unlink()
    else:
        merge.crosswalk(*rows, **({"header": header} if header else {}))
    assert fails(merge) == message.format(folder=merge.folder)


def test_the_last_merge_has_no_crosswalk(tmp_path):
    first = published(tmp_path)
    (first.folder / "crosswalk.csv").unlink()
    merge = Merge(tmp_path / "merge", doi=CONCEPT)
    assert fails(merge, first).startswith(f"There is no crosswalk.csv in {first.folder}. merge.py writes it")


def test_the_crosswalk_of_the_last_merge_does_not_fit(tmp_path):
    first = published(tmp_path)
    first.crosswalk((NORDBEAN, "Germplasm", "ostrin", "kelda"))
    merge = Merge(tmp_path / "merge", doi=CONCEPT)
    assert fails(merge, first) == (f"{first.folder / 'crosswalk.csv'}, row 2: 'kelda' is not a GPID in the last "
                                   "version.")


def test_an_id_renamed_again_is_followed_through_both_crosswalks(tmp_path):
    """
    The contribution's trait plant_height was published as HEIGHT, and this merge makes it plant_height_cm. What
    changed is HEIGHT, not plant_height, which was never published.
    """
    first = Merge(tmp_path / "first")
    first.crosswalk((NORDBEAN, "PhenotypeDescription", "plant_height", HEIGHT))
    first.run(release=FIRST)
    second = Merge(tmp_path / "second", doi=CONCEPT)
    rename_trait(second, HEIGHT, "plant_height_cm")
    second.crosswalk((NORDBEAN, "PhenotypeDescription", "plant_height", "plant_height_cm"))
    second.run(first)
    assert (f"- **PhenotypeDescription.** Renamed: `{HEIGHT}` to `plant_height_cm`."
            in second.section("What changed in this version"))


def test_an_id_changed_in_the_last_merge_only_did_not_change(tmp_path):
    first = Merge(tmp_path / "first")
    first.crosswalk((NORDBEAN, "PhenotypeDescription", "plant_height", HEIGHT))
    first.run(release=FIRST)
    second = Merge(tmp_path / "second", doi=CONCEPT)
    second.crosswalk((NORDBEAN, "PhenotypeDescription", "plant_height", HEIGHT))
    second.run(first)
    assert second.section("What changed in this version").endswith("The tables did not change.")


def test_a_new_contribution_with_an_id_of_the_last_version(tmp_path):
    """
    A new contribution has a trait with the ID of another trait of the last version, which keeps it, so the new one
    gets another ID. Nothing of the last version was renamed: a trait was added.
    """
    first = published(tmp_path)
    second = Merge(tmp_path / "second", doi=CONCEPT)
    second.tables.add_row("PhenotypeDescription", PDID="plant_height_2", PhenotypeDescription="Plant height",
                          Unit="cm", DescriptionOfMethod="Height of the main stem of one plant.")
    second.crosswalk(("2026_11_01_faba", "PhenotypeDescription", HEIGHT, "plant_height_2"))
    second.run(first)
    assert second.section("What changed in this version").split("\n\n")[2] == (
        "- **PhenotypeDescription.** Added: `plant_height_2`.")


def test_an_id_that_becomes_two(tmp_path):
    first = published(tmp_path)
    second = Merge(tmp_path / "second", doi=CONCEPT)
    rename_trait(second, HEIGHT, "plant_height_cm")
    second.tables.add_row("PhenotypeDescription", PDID="plant_height_2", PhenotypeDescription="Plant height",
                          Unit="cm", DescriptionOfMethod="Height of the main stem of one plant.")
    second.crosswalk((NORDBEAN, "PhenotypeDescription", HEIGHT, "plant_height_cm"),
                     ("2026_11_01_faba", "PhenotypeDescription", HEIGHT, "plant_height_2"))
    assert fails(second, first) == (f"By the crosswalks, the PDID '{HEIGHT}' of the last version became both "
                                    "'plant_height_cm' and 'plant_height_2'. An ID can become only one: correct "
                                    "merge.py.")


def rename_trait(merge: Merge, old: str, new: str) -> None:
    """Gives a trait in the merged tables a new PDID, in PhenotypeDescription and in the scores."""
    merge.tables.set("PhenotypeDescription", old, "PDID", new)
    for phid in merge.tables.ids("Phenotype"):
        if merge.tables.get("Phenotype", phid, "PDID") == old:
            merge.tables.set("Phenotype", phid, "PDID", new)


def test_a_preview_keeps_what_was_published(tmp_path):
    first = published(tmp_path)
    readme = first.readme()
    assert fails(first) == (f"{first.folder / 'publish'} holds a version with a DOI, which a preview would replace. "
                            "It is kept as it is, as the next merge compares with it. Build a new version in a new "
                            "merge folder.")
    assert first.readme() == readme
    first.run(release=FIRST)
    assert first.readme() == readme


def test_what_publish_py_keeps_in_publish_is_left_as_it_is(merge):
    merge.run()
    kept = merge.folder / "publish" / "zenodo.json"
    kept.write_text('{"https://zenodo.org": "101"}\n', encoding="utf-8")
    merge.run(release=FIRST)
    assert kept.read_text(encoding="utf-8") == '{"https://zenodo.org": "101"}\n'


def test_building_in_another_folder(merge, tmp_path):
    merge.run(release=FIRST)
    published = merge.readme()
    assert merge.run(out=tmp_path / "check") == [
        f"Built version 1 of Nordbean test dataset, in schema version 1.0, in {tmp_path / 'check'}.",
        "It is the first version.",
        "It is a preview: the date and DOI of the version are set when publish.py publishes it.",
    ]
    assert (tmp_path / "check" / "files" / "README.md").is_file()
    assert merge.readme() == published


# ---------------------------------------------------------------- Running it

def test_command_line(merge, capsys):
    assert build.main(["--merge", str(merge.folder)]) == 0
    assert capsys.readouterr().out.splitlines()[1:] == ["It is the first version.", "It is a preview: the date and "
                                                        "DOI of the version are set when publish.py publishes it."]
    merge.tables.set("Phenotype", SCORE, "Score", "high")
    assert build.main(["--merge", str(merge.folder)]) == 1
    assert capsys.readouterr().out.startswith("Validation failed: Phenotype.csv, row 2, column Score:")
    merge.record.unlink()
    assert build.main(["--merge", str(merge.folder)]) == 1
    assert capsys.readouterr().out.startswith("Stopped: There is no record.yaml")


def test_the_script_runs_with_the_validators_packages():
    """uv runs build.py with the packages listed at its top, which are those of the validator, without Shiny."""
    text = (ROOT / "publishing" / "build.py").read_text(encoding="utf-8")
    block = re.search(r"# /// script\n(.*?)# ///\n", text, re.DOTALL)[1]
    assert '# requires-python = "==3.12.*"' in block
    assert set(re.findall(r'"([^"]+==[^"]+)"', block)) == {
        f"{package}=={version}" for package, version in validation.tested_versions().items() if package != "shiny"}
