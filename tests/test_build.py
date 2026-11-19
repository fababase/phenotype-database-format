"""
publishing/build.py, which builds the README of a version of a dataset, and its metadata for Zenodo, from the folder
of the version. Each test builds from a version folder whose tables are the valid dataset, changed where the test
says, and the code in the README's Quick start is run on what it builds.
"""
import csv
import os
import re
import shutil
import subprocess
from pathlib import Path

import pandas as pd
import pytest

import build
from helpers import COMMIT, GREENHOUSE, ROOT, SCHEMA, SCORE, TRIAL, Dataset, Merge
import validation
from validation import CONTRIBUTORS_FILE, ValidationError

CONCEPT = "10.5281/zenodo.100"
FIRST = build.Release("2026-11-01", "10.5281/zenodo.101", CONCEPT)
SECOND = build.Release("2026-12-01", "10.5281/zenodo.102", CONCEPT)
HEIGHT = "plant_height_mean_of_5_plants_cm"
# The contribution the valid dataset comes from, as the crosswalk names it, by its folder in Sources/
NORDBEAN = "Nordbean"
LINK = "[10.5281/zenodo.101](https://doi.org/10.5281/zenodo.101)"
# The first sentence of the Description of each experiment in the valid dataset
TRIAL_SENTENCE = ("Field trial at the Northfield research farm, on a field of mostly sandy loam that grew spring "
                  "barley the year before")
GREENHOUSE_SENTENCE = ("Pot experiment in a greenhouse compartment at the Northfield research farm, comparing lines "
                       "with no factors tested")


@pytest.fixture
def merge(tmp_path: Path) -> Merge:
    return Merge(tmp_path / "dataset")


def published(tmp_path: Path) -> Merge:
    """The valid dataset, uploaded as the first version, from the folder 2026-11-01."""
    first = Merge(tmp_path / "dataset", "2026-11-01")
    first.upload(FIRST)
    return first


def second_merge(tmp_path: Path) -> Merge:
    """The folder of the version after the first, with no IDs changed."""
    return Merge(tmp_path / "dataset", "2026-12-01", changes="Corrections after review.\n")


def fails(merge: Merge, release: build.Release | None = None) -> str:
    with pytest.raises(build.BuildError) as e:
        merge.run(release)
    return str(e.value)


def compared(merge: Merge) -> str:
    """What changed in the tables since the last version, as the README says it after what changes.md says."""
    return merge.section("What changed in this version").split("\n\n", 1)[1]


# ---------------------------------------------------------------- The files

def test_preview_of_the_first_version(merge):
    assert merge.run().lines == [
        f"Built version 1 of Nordbean test dataset, in schema version 1.0: {merge.files / 'README.md'}.",
        "It is the first version.",
        "It is a preview: the date and DOI of the version are set when publish.py uploads it.",
    ]
    assert "- **Version:** 1, published (set when published).\n" in merge.readme()
    assert "- **DOI:** (set when published). The DOI (set when published) always leads" in merge.readme()
    assert merge.section("What changed in this version") == "The first version."


def test_published_version(merge):
    built = merge.run(release=FIRST)
    assert built.lines[-1] == "It is the first version."
    assert built.version == 1
    readme = merge.readme()
    assert "- **Version:** 1, published 2026-11-01.\n" in readme
    assert (f"- **DOI:** {LINK}. The DOI [10.5281/zenodo.100](https://doi.org/10.5281/zenodo.100) always leads to "
            "the latest version.") in readme
    assert merge.section("What changed in this version") == "The first version."
    assert built.metadata["publication_date"] == "2026-11-01"
    assert built.readme == readme


def test_only_the_readme_is_written(merge):
    before = {path.relative_to(merge.folder): path.read_bytes() for path in merge.folder.rglob("*") if path.is_file()}
    merge.run()
    after = {path.relative_to(merge.folder): path.read_bytes() for path in merge.folder.rglob("*") if path.is_file()}
    assert after.pop(Path("zenodo") / "README.md")
    assert after == before


def test_the_zenodo_folder_has_to_be_there(merge):
    shutil.rmtree(merge.files)
    assert fails(merge) == (f"There is no zenodo folder in {merge.folder}. merge.py writes the tables and "
                            "contributors.yaml in it, and build.py the README: it holds exactly what goes on Zenodo.")


def test_every_table_has_to_be_there(merge):
    merge.tables.drop_table("Management")
    assert fails(merge) == (f"There is no Management.csv in {merge.files}. merge.py writes every table of the "
                            "format there, a table without rows as a file with only the column names.")


@pytest.mark.parametrize("table, change", [
    ("Germplasm", lambda tables: tables.set("Germplasm", "ostrin", "Comments", "NA")),
    ("Germplasm", lambda tables: tables.drop_column("Germplasm", "Donor")),
    ("Features", lambda tables: tables.write("Features", tables.read("Features"), line_end="\r\n")),
])
def test_a_table_not_written_as_the_validator_writes_it(merge, table, change):
    """The files are uploaded as they are, so they have to be in the one form: all columns, missing values empty."""
    change(merge.tables)
    assert fails(merge).startswith(f"{table}.csv in {merge.files} is not written as the validator writes tables "
                                   f"with --out: every column of {table}, in the order of the format, missing values "
                                   "as empty cells, and the rows as pandas writes them")


def test_the_same_every_time(merge):
    merge.run()
    first = merge.readme()
    merge.run()
    assert merge.readme() == first


# ---------------------------------------------------------------- The README

def test_every_place_in_the_template_is_filled_in(merge):
    merge.run()
    readme = merge.readme()
    assert readme.startswith("# Nordbean test dataset\n\nPhenotype data from plant experiments")
    assert "{{" not in readme
    assert "<!--" not in readme
    assert readme.endswith(f"[https://github.com/phenotheca/phenotheca]"
                           f"(https://github.com/phenotheca/phenotheca/tree/{COMMIT}).\n")
    assert "[diagram](https://phenotheca.github.io/phenotheca/diagram/#1.0)" in readme


def test_at_a_glance(merge):
    merge.run()
    assert merge.section("At a glance") == ("- 2 experiments, at 2 places, run in 2025\n- 1 species: Vicia faba\n"
                                            "- 3 germplasm, in 4 seed lots\n- 12 units\n- 3 traits, with 20 scores")


def test_years_of_experiments_over_several_years_or_none(merge):
    merge.tables.set("Experiment", TRIAL, "EndDate", "2026-08-26")
    merge.tables.set("Experiment", GREENHOUSE, "StartDate", "")
    merge.tables.set("Experiment", GREENHOUSE, "EndDate", "")
    built = merge.run()
    assert merge.section("At a glance").splitlines()[0] == "- 2 experiments, at 2 places, run from 2025 to 2026"
    experiments = merge.section("Experiments")
    assert f"| `{TRIAL}` | {TRIAL_SENTENCE} | 2025–2026 | [" in experiments
    assert f"| `{GREENHOUSE}` | {GREENHOUSE_SENTENCE} | | [" in experiments
    assert built.metadata["dates"] == [{"date": "2025-04-08/2026-08-26", "type": {"id": "collected"}}]


def test_experiments(merge):
    merge.tables.set("Experiment", GREENHOUSE, "GPSCoordinates", "")
    merge.run()
    assert merge.section("At a glance").splitlines()[0] == "- 2 experiments, at 1 place, run in 2025"
    assert merge.section("Experiments").split("\n\n")[0] == (
        "| Experiment | Description | Years | Place | Units | Germplasm | Traits |\n"
        "|---|---|---|---|---|---|---|\n"
        f"| `{TRIAL}` | {TRIAL_SENTENCE} | 2025 | [56.091250, 9.552040](https://www.openstreetmap.org/?mlat=56.091250"
        "&mlon=9.552040#map=15/56.091250/9.552040) | 8 | 2 | 1 |\n"
        f"| `{GREENHOUSE}` | {GREENHOUSE_SENTENCE} | 2025 | | 4 | 2 | 2 |")


@pytest.mark.parametrize("text, expected", [
    ("Field trial. Split-plot design.", "Field trial"),
    ("Field trial\nat the farm", "Field trial at the farm"),
    ("", ""),
    ("A " + "long " * 30 + "sentence.", "A " + "long " * 22 + "long…"),
])
def test_the_first_sentence_of_a_description(text, expected):
    assert build.first_sentence(text) == expected


def test_traits_by_experiment(merge):
    merge.run()
    assert ("### Traits by experiment\n\n"
            f"- `{TRIAL}`: `{HEIGHT}`\n"
            f"- `{GREENHOUSE}`: `flower_colour_visual_1to3`, `leaf_absorbance_nirs_dried_powder`\n") in merge.readme()
    frames = {"Experiment": pd.DataFrame({"EXPID": ["a"]}), "ExperimentalUnit": pd.DataFrame({"UNID": [], "EXPID": []}),
              "Phenotype": pd.DataFrame({"UNID": [], "PDID": []})}
    assert build.traits_by_experiment(frames) == "- `a`: no scores"


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
    for table in ("Climate", "ClimateDescription"):
        merge.tables.write(table, [list(SCHEMA.tables[table].columns)])
    merge.run()
    assert "### Climate variables\n\nThere are no climate data in this dataset.\n" in merge.readme()


def test_files_links_and_tables(merge):
    merge.run()
    files = merge.section("The files")
    assert "| [`Phenotype.csv`](#phenotype) | one score of one trait on one unit | 20 |" in files
    assert ("| [`ExperimentalUnit.csv`](#experimentalunit) | a unit in an experiment: a field plot, a pot, a "
            "sample, … | 12 |") in files
    assert "one CSV file per table, `contributors.yaml`, which says who made the data, and this README." in files
    links = merge.section("How the tables link")
    assert "[The tables](#the-tables) marks each such column with the table it links to." in links
    assert "|" not in links
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


RHEA = ("Rhea Plicate (Northfield Agricultural College; Nordbean Breeding Programme; ORCID "
        "[0000-0002-1825-0097](https://orcid.org/0000-0002-1825-0097))")


def test_who_made_it(merge):
    """The people and the funding are on the record's page and in contributors.yaml, which is uploaded."""
    merge.run()
    assert merge.section("Who made it") == (
        "Everyone who made the data is a creator of this record: their names, ORCIDs and affiliations are on its "
        "page on Zenodo, and so is the funding. `contributors.yaml` says which experiments each person and each "
        "grant is behind.\n\n"
        "Each experiment has one or more contacts, who answer questions about it and about using its data. Reach "
        "them through their institution, or through their ORCID record if they have moved.\n\n"
        f"- `{TRIAL}`: {RHEA}\n"
        f"- `{GREENHOUSE}`: Ann Ova (Northfield Agricultural College) and {RHEA}\n\n"
        "The dataset is looked after by Dana Keeper (Northfield Agricultural College).")
    assert "Ann Ova" not in merge.readme().split("## Who made it")[0]


def test_no_funding_and_a_curator_with_an_orcid_id(tmp_path):
    merge = Merge(tmp_path / "dataset", orcid="0000-0002-1825-0097")
    text = merge.tables.contributors.read_text(encoding="utf-8")
    merge.tables.contributors.write_text(text[:text.index("funding:")] + "funding: none\n", encoding="utf-8")
    assert "funding" not in merge.run().metadata
    assert ("The dataset is looked after by Dana Keeper (Northfield Agricultural College; ORCID "
            "[0000-0002-1825-0097](https://orcid.org/0000-0002-1825-0097)).") in merge.readme()


def test_no_curator(merge):
    """Naming who looks after the public dataset is optional."""
    text = merge.zenodo.read_text(encoding="utf-8")
    merge.zenodo.write_text(text[:text.index("curator:")], encoding="utf-8")
    built = merge.run()
    assert "looked after" not in merge.readme()
    assert "contributors" not in built.metadata


def test_a_restricted_dataset_needs_a_curator(tmp_path):
    merge = Merge(tmp_path / "dataset", access="restricted")
    text = merge.zenodo.read_text(encoding="utf-8")
    merge.zenodo.write_text(text[:text.index("curator:")], encoding="utf-8")
    with pytest.raises(build.BuildError) as found:
        merge.run()
    assert str(found.value) == ("zenodo.yaml names no curator. A restricted dataset needs one, as the contact for the "
                                "dataset in its README. Add it, as docs/publish-data.md says.")


def test_licence_of_the_public_dataset(merge):
    built = merge.run()
    assert "- **Licence:** [CC-BY-4.0](#licence).\n" in merge.readme()
    assert merge.section("Licence") == (
        "The data are licensed under [CC-BY-4.0](https://creativecommons.org/licenses/by/4.0/). You may share and "
        "adapt them, for any purpose, as long as you give credit, by citing the dataset as above, and say what you "
        "changed.")
    assert built.metadata["rights"] == [{"id": "cc-by-4.0"}]


def test_terms_of_a_restricted_dataset(tmp_path):
    merge = Merge(tmp_path / "dataset", access="restricted")
    built = merge.run()
    assert "- **Licence:** [Other (Not Open)](#licence). The data are not public yet.\n" in merge.readme()
    assert merge.section("Licence") == (
        "These data belong to a project and are not public yet, so their licence on Zenodo is Other (Not Open). They "
        "are for the people given access on Zenodo, for the project's work. Passing the files on, publishing anything "
        "from the data, or using them outside the project needs the permission of everyone who made them. For the "
        "data of an experiment, that is everyone behind it in `contributors.yaml`, and its contacts, under [Who made "
        "it](#who-made-it), are who to ask. Cite the version you used. When the data are published in the public "
        "dataset, they will be licensed under [CC-BY-4.0](https://creativecommons.org/licenses/by/4.0/) there.")
    assert built.metadata["rights"] == [{"id": "other-closed"}]


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
    found = build.citation([build.Person(family, given, None, [], [], []) for family, given in people], "2026", "T",
                           1,
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


def downloaded(merge: Merge, folder: Path) -> Path:
    """The files of the version as someone who downloads them from Zenodo has them: the README and the tables."""
    folder.mkdir()
    for name in ["README.md"] + [f"{table}.csv" for table in SCHEMA.tables] + [CONTRIBUTORS_FILE]:
        shutil.copyfile(merge.files / name, folder / name)
    return folder


def expected_counts(merge: Merge) -> list[int]:
    """How many scores, feature values of units, and climate values for each unit there are, counted by hand."""
    units = merge.rows("ExperimentalUnit")
    climate = merge.rows("Climate")
    features = sum(len(unit["Features"].split(";")) for unit in units if unit["Features"])
    per_unit = sum(1 if row["UNID"] else sum(unit["EXPID"] == row["EXPID"] for unit in units) for row in climate)
    return [len(merge.rows("Phenotype")), features, per_unit]


def test_quick_start_in_python(merge, tmp_path, monkeypatch):
    merge.run()
    monkeypatch.chdir(downloaded(merge, tmp_path / "downloaded"))
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
    result = subprocess.run([rscript, str(script)], cwd=downloaded(merge, tmp_path / "downloaded"),
                            capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    assert result.stdout.split() == [str(n) for n in expected_counts(merge) + [8]]


# ---------------------------------------------------------------- The metadata

def test_metadata(merge):
    merge.tables.edit_contributors("        ror: none", "        ror: 01aj84f44")
    merge.tables.edit_contributors("    ror: none\n    grant_number", "    ror: 05gq02987\n    grant_number")
    data = merge.run().metadata
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
        {"identifier": f"https://github.com/phenotheca/phenotheca/tree/{COMMIT}", "scheme": "url",
         "relation_type": {"id": "isdocumentedby"}, "resource_type": {"id": "software"}}]
    assert data["description"].startswith("<p>Phenotype data from plant experiments: the scores of traits")
    assert ("<li>2 experiments, at 2 places, run in 2025</li>\n<li>1 species: Vicia faba</li>\n"
            "<li>3 germplasm, in 4 seed lots</li>") in data["description"]


def test_the_curator_is_a_contributor_only_if_not_a_creator(tmp_path):
    merge = Merge(tmp_path / "dataset", orcid="0000-0002-1825-0097")
    assert "contributors" not in merge.run().metadata


def test_a_grant_without_a_number_has_no_award(merge):
    merge.tables.edit_contributors("grant_number: NBF-2024-117", "grant_number: none")
    assert merge.run().metadata["funding"] == [{"funder": {"name": "Nordic Bean Foundation"}}]


# ---------------------------------------------------------------- The versions

def test_what_changed(tmp_path):
    published(tmp_path)
    second = second_merge(tmp_path)
    tables = second.tables
    tables.set("Phenotype", SCORE, "Score", "95")
    tables.delete_row("Phenotype", f"{TRIAL}_000002")
    tables.add_row("Germplasm", GPID="kelda", Name="Kelda")
    rename_trait(second, HEIGHT, "plant_height_cm")
    tables.edit_contributors("\nfunding:", f"\n  - family_name: Nym\n    given_names: Ano\n    orcid: none\n"
                                           f"    affiliations: none\n    experiments:\n      - {TRIAL}\n"
                                           "    contact_for: none\nfunding:")
    second.crosswalk((NORDBEAN, "PhenotypeDescription", HEIGHT, "plant_height_cm"))
    built = second.run(SECOND)
    assert built.lines[1] == "Compared with version 1."
    assert built.version == 2
    assert built.metadata["version"] == "2"
    assert second.section("What changed in this version") == (
        "Corrections after review.\n\n"
        f"Compared with version 1, published 2026-11-01: {LINK}.\n\n"
        "| Table | Added | Changed | Renamed | Removed |\n|---|---|---|---|---|\n"
        "| Germplasm | 1 | 0 | 0 | 0 |\n"
        "| PhenotypeDescription | 0 | 0 | 1 | 0 |\n"
        "| Phenotype | 0 | 1 | 0 | 1 |\n\n"
        "- **Germplasm.** Added: `kelda`.\n"
        f"- **PhenotypeDescription.** Renamed: `{HEIGHT}` to `plant_height_cm`.\n"
        f"- **Phenotype.** Changed: Score in `{SCORE}`. Removed: `{TRIAL}_000002`.\n\n"
        "**People.** Added: Ano Nym.")


def test_only_this_versions_changes_are_in_its_readme(tmp_path):
    """What changed in an earlier version is in that version's README, on Zenodo, not repeated in later ones."""
    published(tmp_path)
    second = second_merge(tmp_path)
    second.upload(SECOND, "102")
    third = Merge(tmp_path / "dataset", "2027-01-01", changes="- More data from the 2026 trials.\n- A trait renamed.\n")
    assert third.run().version == 3
    assert third.section("What changed in this version") == (
        "- More data from the 2026 trials.\n- A trait renamed.\n\n"
        "Compared with version 2, published 2026-12-01: [10.5281/zenodo.102](https://doi.org/10.5281/zenodo.102).\n\n"
        "The tables did not change.")
    assert "Corrections after review." not in third.readme() and "The first version." not in third.readme()


def test_nothing_changed(tmp_path):
    published(tmp_path)
    second = second_merge(tmp_path)
    second.run()
    assert compared(second) == f"Compared with version 1, published 2026-11-01: {LINK}.\n\nThe tables did not change."


def test_two_rows_made_one_and_a_renamed_feature(tmp_path):
    """
    Two traits of the last version become one, so the scores of one now link to the other. A feature is renamed in
    Features and in the Features cells. Only the renames show, as the rows that link to them did not change.
    """
    published(tmp_path)
    second = second_merge(tmp_path)
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
    second.run()
    assert compared(second).split("\n\n")[1:] == [
        "| Table | Added | Changed | Renamed | Removed |\n|---|---|---|---|---|\n"
        "| PhenotypeDescription | 0 | 0 | 1 | 0 |\n"
        "| Features | 0 | 0 | 1 | 0 |",
        f"- **PhenotypeDescription.** Renamed: `flower_colour_visual_1to3` to `{HEIGHT}`.\n"
        "- **Features.** Renamed: `soil_ph` to `topsoil_ph`.",
    ]


def test_many_changes_are_counted(tmp_path, monkeypatch):
    monkeypatch.setattr(build, "LIMIT", 2)
    published(tmp_path)
    second = second_merge(tmp_path)
    for phid in second.tables.ids("Phenotype")[:3]:
        second.tables.set("Phenotype", phid, "Comments", "Checked again.")
    second.tables.set("Phenotype", SCORE, "Score", "95")
    second.run()
    assert f"- **Phenotype.** Changed: Score in `{SCORE}`; Comments in 3 rows.\n" in second.readme()


def test_people_and_funding_that_left(tmp_path):
    published(tmp_path)
    second = second_merge(tmp_path)
    text = second.tables.contributors.read_text(encoding="utf-8")
    text = text[:text.index("  - family_name: Ova")] + text[text.index("  - family_name: Plicate"):]
    second.tables.contributors.write_text(text[:text.index("funding:")] + "funding: none\n", encoding="utf-8")
    second.run()
    assert compared(second).split("\n\n")[1:] == [
        "The tables did not change.",
        "**People.** Removed: Ann Ova.",
        "**Funding.** Removed: Nordic Bean Foundation, grant NBF-2024-117.",
    ]


def set_format(merge: Merge, version: str) -> None:
    """Changes the version of the format that zenodo.yaml gives for the one version listed in it."""
    text = merge.zenodo.read_text(encoding="utf-8")
    assert text.count("format:") == 1
    merge.zenodo.write_text(re.sub(r"format: .*", f"format: '{version}'", text), encoding="utf-8")


def test_the_version_of_the_format_with_a_zero_at_the_end_is_the_same(tmp_path):
    """The last version was published when version 1.0 of the format was written 1.0.0."""
    first = published(tmp_path)
    set_format(first, f"{SCHEMA.version}.0")
    second = second_merge(tmp_path)
    second.run()
    assert "The format changed" not in second.readme()


def test_a_new_version_of_the_format(tmp_path):
    """The last version followed another version of the format, which had a column that is gone, and not one."""
    first = published(tmp_path)
    set_format(first, "0.9")
    germplasm = first.files / "Germplasm.csv"
    with germplasm.open(encoding="utf-8", newline="") as f:
        rows = [{column: value for column, value in row.items() if column != "Maintaining"} | {"Pedigree": ""}
                for row in csv.DictReader(f)]
    with germplasm.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    second = second_merge(tmp_path)
    second.run()
    assert compared(second).split("\n\n")[1:] == [
        "The format changed from version 0.9 to version 1.0. The [diagram]"
        "(https://phenotheca.github.io/phenotheca/diagram/#1.0) shows each version: choose one in its "
        "menu.",
        "| Table | Added | Changed | Renamed | Removed |\n|---|---|---|---|---|\n| Germplasm | 0 | 0 | 0 | 0 |",
        "- **Germplasm.** New columns: Maintaining. Columns no longer in the format: Pedigree.",
    ]


# ---------------------------------------------------------------- zenodo.yaml

def test_the_versions_are_written_as_read(merge):
    """publish.py lists each version in zenodo.yaml, after what was written by hand, and build.py reads them back."""
    merge.upload(FIRST)
    assert merge.state() == {
        "title": "Nordbean test dataset", "access": "open",
        "curator": {"family_name": "Keeper", "given_names": "Dana", "orcid": "none",
                    "affiliations": [{"name": "Northfield Agricultural College", "ror": "none"}]},
        "doi": CONCEPT,
        "versions": [{"version": "1", "folder": merge.folder.name, "id": "101", "doi": "10.5281/zenodo.101",
                      "date": "2026-11-01", "format": SCHEMA.version}]}
    assert merge.zenodo.read_text(encoding="utf-8").endswith(
        "doi: 10.5281/zenodo.100\nversions:\n  - version: 1\n    folder: '2026-11-20'\n    id: '101'\n"
        "    doi: 10.5281/zenodo.101\n    date: '2026-11-01'\n    format: '1.0'\n")
    dataset = build.read_dataset(merge.dataset)
    assert dataset.doi == CONCEPT
    assert dataset.versions == [build.Version(1, merge.folder.name, "101", "10.5281/zenodo.101", "2026-11-01",
                                              SCHEMA.version)]
    assert dataset.curator.family_name == "Keeper"
    assert dataset.text["curator"]["affiliations"] == [{"name": "Northfield Agricultural College", "ror": "none"}]


def test_a_draft_without_a_doi_is_listed_too(merge):
    """publish.py lists the draft as soon as Zenodo makes it, before its DOI is reserved, so that it is not lost."""
    dataset = build.read_dataset(merge.dataset)
    dataset.versions.append(build.Version(1, merge.folder.name, "101", None, "2026-11-01", SCHEMA.version))
    build.write_dataset(dataset)
    assert merge.state()["versions"] == [{"version": "1", "folder": merge.folder.name, "id": "101",
                                          "date": "2026-11-01", "format": SCHEMA.version}]
    assert build.read_dataset(merge.dataset).versions == dataset.versions


def test_the_sandbox_lists_its_versions_in_another_file(merge):
    dataset = build.read_dataset(merge.dataset, "sandbox.yaml")
    assert (dataset.doi, dataset.versions, dataset.title) == (None, [], "Nordbean test dataset")
    dataset.doi = "10.5072/zenodo.100"
    dataset.versions.append(build.Version(1, merge.folder.name, "101", "10.5072/zenodo.101", "2026-11-01",
                                          SCHEMA.version))
    build.write_dataset(dataset)
    assert merge.state("sandbox.yaml") == {
        "doi": "10.5072/zenodo.100",
        "versions": [{"version": "1", "folder": merge.folder.name, "id": "101", "doi": "10.5072/zenodo.101",
                      "date": "2026-11-01", "format": SCHEMA.version}]}
    assert "versions" not in merge.state()
    assert build.read_dataset(merge.dataset, "sandbox.yaml").versions == dataset.versions
    # On Zenodo itself, the version is not uploaded yet, so a preview is fine; on the sandbox it is
    assert merge.run().version == 1
    with pytest.raises(build.BuildError) as e:
        merge.run(state="sandbox.yaml")
    assert str(e.value).startswith(f"Version 1, in {merge.folder}, is on Zenodo, as sandbox.yaml says")


# ---------------------------------------------------------------- What it stops at

def test_no_zenodo_file(merge):
    merge.zenodo.unlink()
    assert fails(merge) == (f"There is no zenodo.yaml in {merge.dataset}, the folder above Versions. Write the title "
                            "of the dataset and its access in it, as docs/publish-data.md says.")


def test_a_folder_that_is_not_in_versions(tmp_path):
    Dataset(tmp_path / "elsewhere")
    with pytest.raises(build.BuildError) as e:
        build.build(tmp_path / "elsewhere", COMMIT)
    assert str(e.value) == (f"{tmp_path / 'elsewhere'} is not a folder in Versions. A version is built from "
                            "Versions/<date> in the dataset folder, as docs/publish-data.md lays it out.")


@pytest.mark.parametrize("old, new, message", [
    ("title: Nordbean test dataset\n", "", "zenodo.yaml, line 1: the file has no 'title'. Add it."),
    ("access: open\n", "", "zenodo.yaml, line 1: the file has no 'access'. Add it."),
    ("access: open", "access: public",
     "zenodo.yaml, line 2: 'public' is not a kind of access. Write open, if anyone may download the files, or "
     "restricted, if only those given access on Zenodo may."),
    ("orcid: none", "orcid: 0000-0002-1825-0098",
     "zenodo.yaml, line 6: '0000-0002-1825-0098' is not an ORCID iD: its last character, which checks the others, "
     "does not fit them. Copy it again from orcid.org."),
    ("      ror: none\n", "      ror: none\nowner: me\n",
     "zenodo.yaml, line 10: 'owner' is not a key of the file. The keys of the file are title, access, curator, doi "
     "and versions."),
    ("      ror: none\n", "      ror: none\ndoi: https://doi.org/10.5281/zenodo.100\n",
     "zenodo.yaml, line 10: 'https://doi.org/10.5281/zenodo.100' is not a DOI, which starts with 10. and a '/'. "
     "publish.py writes it, so leave it as it was."),
    ("      ror: none\n", "      ror: none\nversions: 1\n",
     "zenodo.yaml, line 10: versions has to be a list, as publish.py writes it."),
    ("      ror: none\n", "      ror: none\nversions:\n  - version: 2\n    folder: x\n    id: '1'\n    date: d\n"
                          "    format: '1.0'\n",
     "zenodo.yaml, line 11: the versions have to be numbered 1, 2, … in order, as publish.py writes them."),
])
def test_zenodo_file_that_does_not_fit_its_format(merge, old, new, message):
    merge.zenodo.write_text(merge.zenodo.read_text(encoding="utf-8").replace(old, new, 1), encoding="utf-8")
    assert fails(merge) == message


def test_tables_that_do_not_pass(merge):
    merge.tables.set("Phenotype", SCORE, "Score", "high")
    with pytest.raises(ValidationError):
        merge.run()
    assert not (merge.files / "README.md").exists()


def test_no_contributors_file(merge):
    merge.tables.contributors.unlink()
    assert fails(merge) == (f"There is no contributors.yaml in {merge.files}. merge.py writes it there, with who to "
                            "credit.")


@pytest.mark.parametrize("text, message", [
    (None, "There is no changes.md in {folder}. Write in it what changed in this version of the dataset, and why, "
           "for the people who use the data; for the first version, that it is the first."),
    ("\n", "changes.md in {folder} is empty. Write in it what changed in this version of the dataset, and why, for "
           "the people who use the data; for the first version, that it is the first."),
    ("## Changes\n\nThe first version.\n", "changes.md in {folder} has a heading. Write paragraphs and lists only: "
                                           "the README puts it under a heading of its own."),
])
def test_changes_that_do_not_fit(merge, text, message):
    if text is None:
        merge.changes.unlink()
    else:
        merge.changes.write_text(text, encoding="utf-8")
    assert fails(merge) == message.format(folder=merge.folder)


def test_the_last_version_has_no_folder(tmp_path):
    first = published(tmp_path)
    shutil.rmtree(first.folder)
    assert fails(second_merge(tmp_path)) == (
        f"There is no folder {first.folder}, which holds version 1, as zenodo.yaml says. The folder of a version is "
        "kept, as the next version compares with it.")


def test_the_last_version_has_no_tables(tmp_path):
    first = published(tmp_path)
    for name in SCHEMA.tables:
        first.tables.drop_table(name)
    assert fails(second_merge(tmp_path)) == (
        f"There are no tables in {first.files}, which holds version 1. The folder of a version is kept as it was, "
        "as the next version compares with it.")


def test_the_last_version_has_no_contributors_file(tmp_path):
    first = published(tmp_path)
    first.tables.contributors.unlink()
    assert fails(second_merge(tmp_path)) == (f"There is no contributors.yaml in {first.files}, which says who made "
                                             "version 1.")


def test_zenodo_has_another_doi_for_the_dataset(tmp_path):
    published(tmp_path)
    release = build.Release("2026-12-01", "10.5281/zenodo.202", "10.5281/zenodo.200")
    assert fails(second_merge(tmp_path), release) == (f"The DOI of all versions is 10.5281/zenodo.200 on Zenodo, but "
                                                      f"{CONCEPT} in zenodo.yaml.")


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


def test_the_last_version_has_no_crosswalk(tmp_path):
    first = published(tmp_path)
    (first.folder / "crosswalk.csv").unlink()
    assert fails(second_merge(tmp_path)).startswith(f"There is no crosswalk.csv in {first.folder}. merge.py writes it")


def test_the_crosswalk_of_the_last_version_does_not_fit(tmp_path):
    first = published(tmp_path)
    first.crosswalk((NORDBEAN, "Germplasm", "ostrin", "kelda"))
    assert fails(second_merge(tmp_path)) == (f"{first.folder / 'crosswalk.csv'}, row 2: 'kelda' is not a GPID in the "
                                             "last version.")


def test_an_id_renamed_again_is_followed_through_both_crosswalks(tmp_path):
    """
    The contribution's trait plant_height was published as HEIGHT, and this merge makes it plant_height_cm. What
    changed is HEIGHT, not plant_height, which was never published.
    """
    first = Merge(tmp_path / "dataset", "2026-11-01")
    first.crosswalk((NORDBEAN, "PhenotypeDescription", "plant_height", HEIGHT))
    first.upload(FIRST)
    second = second_merge(tmp_path)
    rename_trait(second, HEIGHT, "plant_height_cm")
    second.crosswalk((NORDBEAN, "PhenotypeDescription", "plant_height", "plant_height_cm"))
    second.run()
    assert f"- **PhenotypeDescription.** Renamed: `{HEIGHT}` to `plant_height_cm`." in compared(second)


def test_an_id_changed_in_the_last_merge_only_did_not_change(tmp_path):
    first = Merge(tmp_path / "dataset", "2026-11-01")
    first.crosswalk((NORDBEAN, "PhenotypeDescription", "plant_height", HEIGHT))
    first.upload(FIRST)
    second = second_merge(tmp_path)
    second.crosswalk((NORDBEAN, "PhenotypeDescription", "plant_height", HEIGHT))
    second.run()
    assert compared(second).endswith("The tables did not change.")


def test_a_new_contribution_with_an_id_of_the_last_version(tmp_path):
    """
    A new contribution has a trait with the ID of another trait of the last version, which keeps it, so the new one
    gets another ID. Nothing of the last version was renamed: a trait was added.
    """
    published(tmp_path)
    second = second_merge(tmp_path)
    second.tables.add_row("PhenotypeDescription", PDID="plant_height_2", PhenotypeDescription="Plant height",
                          Unit="cm", DescriptionOfMethod="Height of the main stem of one plant.")
    second.crosswalk(("Faba", "PhenotypeDescription", HEIGHT, "plant_height_2"))
    second.run()
    assert compared(second).split("\n\n")[2] == "- **PhenotypeDescription.** Added: `plant_height_2`."


def test_an_id_that_becomes_two(tmp_path):
    published(tmp_path)
    second = second_merge(tmp_path)
    rename_trait(second, HEIGHT, "plant_height_cm")
    second.tables.add_row("PhenotypeDescription", PDID="plant_height_2", PhenotypeDescription="Plant height",
                          Unit="cm", DescriptionOfMethod="Height of the main stem of one plant.")
    second.crosswalk((NORDBEAN, "PhenotypeDescription", HEIGHT, "plant_height_cm"),
                     ("Faba", "PhenotypeDescription", HEIGHT, "plant_height_2"))
    assert fails(second) == (f"By the crosswalks, the PDID '{HEIGHT}' of the last version became both "
                             "'plant_height_cm' and 'plant_height_2'. An ID can become only one: correct merge.py.")


def rename_trait(merge: Merge, old: str, new: str) -> None:
    """Gives a trait in the merged tables a new PDID, in PhenotypeDescription and in the scores."""
    merge.tables.set("PhenotypeDescription", old, "PDID", new)
    for phid in merge.tables.ids("Phenotype"):
        if merge.tables.get("Phenotype", phid, "PDID") == old:
            merge.tables.set("Phenotype", phid, "PDID", new)


def test_a_preview_keeps_what_was_uploaded(tmp_path):
    first = published(tmp_path)
    readme = first.readme()
    assert fails(first) == (f"Version 1, in {first.folder}, is on Zenodo, as zenodo.yaml says, so a preview would "
                            "replace the README that was uploaded. Build a new version in a new folder, or run "
                            "publish.py, which builds the README with the version's date and DOI.")
    assert first.readme() == readme
    first.run(release=FIRST)
    assert first.readme() == readme


def test_building_in_another_folder(tmp_path):
    first = published(tmp_path)
    readme = first.readme()
    assert first.run(out=tmp_path / "check").lines == [
        f"Built version 1 of Nordbean test dataset, in schema version 1.0: {tmp_path / 'check' / 'README.md'}.",
        "It is the first version.",
        "It is a preview: the date and DOI of the version are set when publish.py uploads it.",
    ]
    assert (tmp_path / "check" / "README.md").is_file()
    assert first.readme() == readme


# ---------------------------------------------------------------- Running it

def test_command_line(merge, capsys):
    assert build.main([str(merge.folder)]) == 0
    assert capsys.readouterr().out.splitlines()[1:] == ["It is the first version.", "It is a preview: the date and "
                                                        "DOI of the version are set when publish.py uploads it."]
    merge.tables.set("Phenotype", SCORE, "Score", "high")
    assert build.main([str(merge.folder)]) == 1
    assert capsys.readouterr().out.startswith("Validation failed: Phenotype.csv, row 2, column Score:")
    merge.zenodo.unlink()
    assert build.main([str(merge.folder)]) == 1
    assert capsys.readouterr().out.startswith("Stopped: There is no zenodo.yaml")


def test_the_script_runs_with_the_validators_packages():
    """uv runs build.py with the packages listed at its top, which are those of the validator, without Shiny."""
    text = (ROOT / "publishing" / "build.py").read_text(encoding="utf-8")
    block = re.search(r"# /// script\n(.*?)# ///\n", text, re.DOTALL)[1]
    assert '# requires-python = "==3.12.*"' in block
    assert set(re.findall(r'"([^"]+==[^"]+)"', block)) == {
        f"{package}=={version}" for package, version in validation.tested_versions().items() if package != "shiny"}
