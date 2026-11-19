"""
contributors.yaml, which says who to credit. The valid dataset's passes, and is read exactly as written. Each broken
one is it with one thing changed, and has to fail with exactly the message the validator gives for that mistake.
"""
import pytest

from helpers import GREENHOUSE, TRIAL, check, fails, passes
from validation import YAML_HINT, Affiliation, Grant, Person

RHEA = "0000-0002-1825-0097"
NOT_A_LIST = "has to be a list of at least one item, each on a line of its own that starts with '- '"


# ---------------------------------------------------------------- Passes

def test_read_as_written(dataset):
    checked, notices = check(dataset.files())
    assert notices == []
    credit = checked.contributors
    assert credit.source == "contributors.yaml"
    assert credit.people == [
        Person("Ova", "Ann", None, [Affiliation("Northfield Agricultural College", None)], [GREENHOUSE],
               [GREENHOUSE]),
        Person("Plicate", "Rhea", RHEA, [Affiliation("Northfield Agricultural College", None),
                                         Affiliation("Nordbean Breeding Programme", None)], [TRIAL, GREENHOUSE],
               [TRIAL, GREENHOUSE]),
    ]
    assert credit.funding == [Grant("Nordic Bean Foundation", None, "NBF-2024-117", "Drought tolerance in faba bean",
                                    [TRIAL])]
    assert credit.text == dataset.contributors.read_text(encoding="utf-8")


@pytest.mark.parametrize("value", ["0123", "no", "Yes", "true", "1e5", "1.50", "2025-01-01", "12:30"])
def test_values_are_kept_as_written(dataset, value):
    """YAML would otherwise read these as numbers, true or false, or dates."""
    dataset.edit_contributors("NBF-2024-117", value)
    checked, _ = check(dataset.files())
    assert checked.contributors.funding[0].grant_number == value


def test_ror_ids_and_an_orcid_id_ending_in_x(dataset):
    dataset.edit_contributors("        ror: none", "        ror: 01aj84f44")
    dataset.edit_contributors("    ror: none\n    grant_number", "    ror: 05gq02987\n    grant_number")
    dataset.edit_contributors("orcid: none", "orcid: 0000-0002-1694-233X")
    credit, _ = check(dataset.files())
    assert credit.contributors.people[0].affiliations[0].ror == "01aj84f44"
    assert credit.contributors.people[0].orcid == "0000-0002-1694-233X"
    assert credit.contributors.funding[0].ror == "05gq02987"


def test_none_where_something_does_not_exist(dataset):
    dataset.edit_contributors("given_names: Ann", "given_names: none")
    dataset.edit_contributors("    affiliations:\n      - name: Northfield Agricultural College\n        ror: none\n"
                              "    experiments:\n      - nordbean_leaf",
                              "    affiliations: none\n    experiments:\n      - nordbean_leaf")
    dataset.edit_contributors(f"    contact_for:\n      - {GREENHOUSE}\n  - family",
                              "    contact_for: none\n  - family")
    dataset.edit_contributors("    grant_number: NBF-2024-117\n    grant_title: Drought tolerance in faba bean",
                              "    grant_number: none\n    grant_title: none")
    checked, _ = check(dataset.files())
    assert checked.contributors.people[0] == Person("Ova", None, None, [], [GREENHOUSE], [])
    assert checked.contributors.funding[0] == Grant("Nordic Bean Foundation", None, None, None, [TRIAL])


def test_no_funding(dataset):
    text = dataset.contributors.read_text(encoding="utf-8")
    dataset.contributors.write_text(text[:text.index("funding:")] + "funding: none\n", encoding="utf-8")
    checked, _ = check(dataset.files())
    assert checked.contributors.funding == []


def test_keys_in_any_order(dataset):
    dataset.edit_contributors("    given_names: Ann\n    orcid: none\n", "    orcid: none\n    given_names: Ann\n")
    passes(dataset.files())


def test_quotes_and_comments(dataset):
    dataset.edit_contributors("Drought tolerance in faba bean", '"Faba beans: drought, #2"  # the full title')
    checked, _ = check(dataset.files())
    assert checked.contributors.funding[0].grant_title == "Faba beans: drought, #2"


def test_letters_with_accents_and_a_byte_order_mark(dataset):
    dataset.edit_contributors("family_name: Ova", "family_name: Østergård")
    text = dataset.contributors.read_text(encoding="utf-8")
    dataset.contributors.write_text(text, encoding="utf-8-sig")
    checked, _ = check(dataset.files())
    assert checked.contributors.people[0].family_name == "Østergård"
    assert checked.contributors.text == text


def test_file_name_in_any_case(dataset):
    dataset.contributors.rename(dataset.folder / "Contributors.YAML")
    checked, _ = check(dataset.files())
    assert checked.contributors.source == "Contributors.YAML"


def test_without_contributors(dataset):
    dataset.contributors.unlink()
    checked, notices = check(dataset.files())
    assert checked.contributors is None
    assert notices == ["There is no contributors.yaml, so who to credit was not checked."]


# ---------------------------------------------------------------- Files

def test_tables_are_checked_first(dataset):
    dataset.edit_contributors("family_name: Ova", "family_name: none")
    dataset.drop_table("Germplasm")
    fails(dataset.files(), "The Germplasm table is missing. Add Germplasm.csv, or the sheet 'Germplasm' to the "
                           "workbook.")


def test_two_contributors_files(dataset):
    (dataset.folder / "Contributors.yaml").write_bytes(dataset.contributors.read_bytes())
    fails(dataset.files(), "Contributors.yaml and contributors.yaml are both contributors.yaml. Keep only one.")


@pytest.mark.parametrize("name", ["credit.yaml", "contributors.yml"])
def test_yaml_file_of_another_name(dataset, name):
    dataset.contributors.rename(dataset.folder / name)
    fails(dataset.files(), f"{name}: the only YAML file the validator reads is contributors.yaml, which says who "
                           "to credit. Name it so, or leave it out.")


def test_contributors_without_tables(dataset):
    fails(dataset.credit(), "No tables given. Give one CSV file per table, or one collection sheet (.xlsx).")


def test_not_utf8(dataset):
    dataset.edit_contributors("family_name: Ova", "family_name: Østergård")
    text = dataset.contributors.read_text(encoding="utf-8")
    dataset.contributors.write_text(text, encoding="cp1252")
    fails(dataset.files(), "contributors.yaml: could not read the text of the file. Save it as UTF-8.")


@pytest.mark.parametrize("text, message", [
    ("", "contributors.yaml is empty. Write who to credit in it: the people and the funding."),
    ("# Only a comment\n", "contributors.yaml is empty. Write who to credit in it: the people and the funding."),
    ("- Ova\n- Plicate\n", "contributors.yaml, line 1: the file is not written as keys with their values. Write the "
                           "keys people and funding, each on a line of its own, followed by ':' and its value."),
    ("people: none\nfunding: none\n", f"contributors.yaml, line 1: people {NOT_A_LIST}."),
    ("people:\nfunding: none\n", f"contributors.yaml, line 1: people {NOT_A_LIST}."),
    ("people: []\nfunding: none\n", f"contributors.yaml, line 1: people {NOT_A_LIST}."),
])
def test_whole_file(dataset, text, message):
    dataset.contributors.write_text(text, encoding="utf-8")
    fails(dataset.files(), message)


def test_funding_left_out(dataset):
    text = dataset.contributors.read_text(encoding="utf-8")
    dataset.contributors.write_text(text[:text.index("funding:")], encoding="utf-8")
    fails(dataset.files(), f"contributors.yaml, line {dataset.line('people:')}: the file has no 'funding'. Add it, "
                           "or write funding: none if there is none.")


@pytest.mark.parametrize("funding", ["funding:", "funding: []", "funding: None"])
def test_funding_empty(dataset, funding):
    text = dataset.contributors.read_text(encoding="utf-8")
    dataset.contributors.write_text(text[:text.index("funding:")] + funding + "\n", encoding="utf-8")
    fails(dataset.files(), f"contributors.yaml, line {dataset.line('funding')}: funding {NOT_A_LIST}, or none if "
                           "there is none.")


def test_a_second_document(dataset):
    dataset.edit_contributors("funding:", "---\nfunding:")
    fails(dataset.files(), f"contributors.yaml, line {dataset.line('---')}: could not read it as YAML (expected a "
                           f"single document in the stream, but found another document). {YAML_HINT}")


def test_grant_listed_twice(dataset):
    text = dataset.contributors.read_text(encoding="utf-8")
    dataset.contributors.write_text(text + text[text.index("  - funder"):], encoding="utf-8")
    fails(dataset.files(), f"contributors.yaml, line {dataset.line('- funder', 2)}: grant NBF-2024-117 of Nordic "
                           "Bean Foundation is listed twice. List each grant once.")


def test_experiment_nobody_is_behind(dataset):
    dataset.edit_contributors(f"    experiments:\n      - {TRIAL}\n      - {GREENHOUSE}\n"
                              f"    contact_for:\n      - {TRIAL}\n      - {GREENHOUSE}\nfunding",
                              f"    experiments:\n      - {GREENHOUSE}\n    contact_for:\n      - {GREENHOUSE}\n"
                              "funding")
    fails(dataset.files(), f"{dataset.where('Experiment', TRIAL, 'EXPID')}: nobody in contributors.yaml is behind "
                           f"experiment '{TRIAL}'. List it under the experiments of each person behind it.")


def test_experiment_nobody_is_the_contact_for(dataset):
    dataset.edit_contributors(f"    contact_for:\n      - {TRIAL}\n      - {GREENHOUSE}\nfunding",
                              f"    contact_for:\n      - {GREENHOUSE}\nfunding")
    fails(dataset.files(), f"{dataset.where('Experiment', TRIAL, 'EXPID')}: nobody in contributors.yaml is the "
                           f"contact for experiment '{TRIAL}'. List it under contact_for of each person to ask "
                           "about it.")


def test_a_contact_for_an_experiment_is_behind_it(dataset):
    dataset.edit_contributors(f"    contact_for:\n      - {GREENHOUSE}\n  - family",
                              f"    contact_for:\n      - {TRIAL}\n  - family")
    fails(dataset.files(), f"contributors.yaml, line {dataset.line('contact_for:') + 1}: '{TRIAL}' is under "
                           "contact_for, but not under the experiments of this person. A contact for an experiment "
                           "is behind it, so list it under experiments too.")


# ---------------------------------------------------------------- Values

# (what to replace, what to replace it with, text on the line the message names, and the message after the line)
BROKEN = [
    # Not YAML
    ("    given_names: Ann", "\tgiven_names: Ann", "given_names: Ann",
     "could not read it as YAML (while scanning for the next token, found character '\\t' that cannot start any "
     f"token). {YAML_HINT}"),
    ("    given_names: Ann", "   given_names: Ann", "given_names: Ann",
     "could not read it as YAML (while parsing a block collection, expected <block end>, but found '<block mapping "
     f"start>'). {YAML_HINT}"),
    ("Drought tolerance in faba bean", "Faba beans: drought tolerance", "Faba beans",
     f"could not read it as YAML (mapping values are not allowed here). {YAML_HINT}"),
    # Keys
    ("people:", "peopel:", "peopel", "'peopel' is not a key of the file. Did you mean 'people'?"),
    ("people:", "persons:", "persons",
     "'persons' is not a key of the file. The keys of the file are people and funding."),
    ("family_name: Ova", "familyname: Ova", "familyname",
     "'familyname' is not a key of a person. Did you mean 'family_name'?"),
    ("    given_names: Ann\n", "    given_names: Ann\n    given_names: Ann\n", ("given_names: Ann", 2),
     "'given_names' appears twice in a person. Keep only one."),
    ("    orcid: none\n", "", "family_name: Ova",
     "a person has no 'orcid'. Add it, or write orcid: none if there is none."),
    ("    grant_title: Drought tolerance in faba bean\n", "", "- funder",
     "a grant has no 'grant_title'. Add it, or write grant_title: none if there is none."),
    ("  - family_name: Ova", "  - Ova\n  - family_name: Ova", "- Ova",
     "a person is not written as keys with their values. Write the keys family_name, given_names, orcid, "
     "affiliations, experiments and contact_for, each on a line of its own, followed by ':' and its value."),
    ("      - name: Northfield Agricultural College\n        ror: none\n    experiments:\n      - nordbean_leaf",
     "      - Northfield Agricultural College\n    experiments:\n      - nordbean_leaf", "- Northfield",
     "an affiliation is not written as keys with their values. Write the keys name and ror, each on a line of its "
     "own, followed by ':' and its value."),
    # Text
    ("given_names: Ann", "given_names:", "given_names", "given_names is empty. Fill it in, or write none if there is "
                                                         "none."),
    ("family_name: Ova", 'family_name: ""', "family_name", "family_name is empty. Fill it in."),
    ("family_name: Ova", "family_name: none", "family_name", "family_name cannot be none. Fill it in."),
    ("orcid: none", "orcid: None", "orcid", "write 'None' as none, in small letters."),
    ("family_name: Ova", 'family_name: " Ova"', "family_name", "' Ova' has spaces before or after it. Remove them."),
    ("family_name: Ova", 'family_name: "Ova\\nOva"', "family_name",
     "family_name contains a line break. Write it on one line, without such characters."),
    ("family_name: Ova", "family_name: [Ova]", "family_name",
     "family_name has to be one value, on the same line as 'family_name:'."),
    # ORCID iDs
    (RHEA, "0000-0002-1825-0098", "0000-0002-1825-0098",
     "'0000-0002-1825-0098' is not an ORCID iD: its last character, which checks the others, does not fit them. "
     "Copy it again from orcid.org."),
    (RHEA, f"https://orcid.org/{RHEA}", "orcid.org",
     f"'https://orcid.org/{RHEA}' is a link. Write the ORCID iD alone: {RHEA}"),
    (RHEA, "0000-0002-1694-233x", "233x",
     "'0000-0002-1694-233x' ends in a small x. Write it as a capital: 0000-0002-1694-233X"),
    (RHEA, "0000000218250097", "0000000218250097",
     "'0000000218250097' is not an ORCID iD, which is four groups of four digits joined by '-', where the last "
     "character can also be X. Write none if the person has none."),
    ("orcid: none", f"orcid: {RHEA}", "family_name: Plicate",
     f"the ORCID iD {RHEA} is also that of the person on line 4. List each person once."),
    # ROR IDs
    ("        ror: none", "        ror: 01aj84f45", "01aj84f45",
     "'01aj84f45' is not a ROR ID: its last two digits, which check the others, do not fit them. Copy it again "
     "from ror.org."),
    ("        ror: none", "        ror: https://ror.org/01aj84f44", "ror.org",
     "'https://ror.org/01aj84f44' is a link. Write the ROR ID alone: 01aj84f44"),
    ("        ror: none", "        ror: 01AJ84F44", "01AJ84F44",
     "'01AJ84F44' has capital letters. Write it in small letters: 01aj84f44"),
    ("    ror: none\n    grant_number", "    ror: Nordic Bean Foundation\n    grant_number", "ror: Nordic",
     "'Nordic Bean Foundation' is not a ROR ID, which is 9 characters: 0, six letters and digits, and two digits. "
     "Look it up at ror.org, or write none if there is none."),
    # Lists
    ("    affiliations:\n      - name: Northfield Agricultural College\n        ror: none\n    experiments:\n"
     "      - nordbean_leaf", "    affiliations: []\n    experiments:\n      - nordbean_leaf", "affiliations",
     f"affiliations {NOT_A_LIST}, or none if there is none."),
    ("Nordbean Breeding Programme", "Northfield Agricultural College", ("Northfield Agricultural College", 3),
     "Northfield Agricultural College is listed twice for this person. Keep only one."),
    (f"      - {GREENHOUSE}\n  - family", "      - nordbean_leaf_greenhouse_2025\n  - family", "leaf_greenhouse",
     "'nordbean_leaf_greenhouse_2025' is not an EXPID in Experiment.csv. EXPIDs have to match exactly, character "
     "for character. Check the spelling."),
    (f"      - {GREENHOUSE}\n  - family", f"      - N{GREENHOUSE[1:]}\n  - family", "Nordbean_leaf",
     f"'N{GREENHOUSE[1:]}' is not an EXPID in Experiment.csv. EXPIDs have to match exactly, character for "
     f"character. Did you mean '{GREENHOUSE}'?"),
    (f"      - {TRIAL}\n      - {GREENHOUSE}", f"      - {TRIAL}\n      - {TRIAL}\n      - {GREENHOUSE}", (TRIAL, 2),
     f"'{TRIAL}' is listed twice. Keep only one."),
]


@pytest.mark.parametrize("old, new, on_line, message", BROKEN)
def test_broken(dataset, old, new, on_line, message):
    """on_line is the text on the line the message names, or (text, n) for the nth line that holds it."""
    dataset.edit_contributors(old, new)
    text, occurrence = on_line if isinstance(on_line, tuple) else (on_line, 1)
    fails(dataset.files(), f"contributors.yaml, line {dataset.line(text, occurrence)}: {message}")


def test_empty_item_of_a_list(dataset):
    dataset.edit_contributors(f"      - {GREENHOUSE}\n  - family", "      -\n  - family")
    fails(dataset.files(), f"contributors.yaml, line {dataset.line('contact_for:') + 1}: an item of contact_for is "
                           "empty. Fill it in.")
