"""
The guides, the instructions and the other pages of the repository link to each other, and to headings in each other.
Every link leads somewhere.
"""
import re
from pathlib import Path

import pytest

from helpers import ROOT

# Every page but the template of the datasets' README, whose links build.py fills in
PAGES = sorted(path for path in ROOT.rglob("*.md")
               if not path.relative_to(ROOT).parts[0].startswith((".", "site")) and path.name != "README_TEMPLATE.md")
LINK = re.compile(r"\]\(([^)\s]+)\)")
HEADING = re.compile(r"^#{1,6} +(.+?)\s*$", re.MULTILINE)
FENCE = re.compile(r"^(?:```|~~~).*?^(?:```|~~~)[^\n]*$", re.MULTILINE | re.DOTALL)


def prose(page: Path) -> str:
    """The page without its fenced code blocks, in which a link or a heading is only text."""
    return FENCE.sub("", page.read_text(encoding="utf-8"))


def anchors(page: Path) -> set[str]:
    """The anchors of the page's headings, as GitHub makes them: lowercase, punctuation out, spaces as hyphens."""
    found, counts = set(), {}
    for heading in HEADING.findall(prose(page)):
        text = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", heading)
        slug = re.sub(r"[^\w\- ]", "", text.lower()).replace(" ", "-")
        found.add(slug if slug not in counts else f"{slug}-{counts[slug]}")
        counts[slug] = counts.get(slug, 0) + 1
    return found


@pytest.mark.parametrize("page", PAGES, ids=lambda page: str(page.relative_to(ROOT)))
def test_every_link_leads_somewhere(page):
    broken = []
    for target in LINK.findall(prose(page)):
        if target.startswith(("http://", "https://", "mailto:")):
            continue
        path, _, anchor = target.partition("#")
        file = (page.parent / path).resolve() if path else page
        if not file.exists():
            broken.append(f"{target}: there is no {path}")
        elif anchor and file.suffix == ".md" and anchor not in anchors(file):
            broken.append(f"{target}: {file.name} has no heading with the anchor {anchor}")
    assert not broken, "\n".join(broken)
