"""
Draws the pictures in the README and the guides, as SVG, so that their words and layout are changed here, in one
place, and drawn again:

    overview.svg      in the README: who does what, where, what moves between them, and who uses the data
    contribution.svg  in docs/submit-data.md: the contribution folder, and whose each part of it is

It needs nothing beyond Python, and writes the pictures next to itself. It stops if a text is wider than the room
it has, so that a change of words never runs out of its box unseen.
"""
from pathlib import Path
from xml.sax.saxutils import escape

HERE = Path(__file__).resolve().parent
FONT = "Arial, 'Liberation Sans', Helvetica, sans-serif"
MONO = "Consolas, 'Liberation Mono', Menlo, monospace"

C = dict(
    ink="#1F2328", muted="#5B6672", line="#9AA4AE", paper="#FFFFFF", box_stroke="#B9C2CB", tool="#3B4452",
    contributor="#2B6CB0", manager="#B9620F", zenodo="#2F7D4F", ai="#7A3FD1", ai_fill="#F3ECFC", user="#4E5968",
    z_contrib="#EBF2FB", z_manager="#FDF2E7", z_zenodo="#EAF6EE", z_github="#F1F3F5",
)

# Widths of Arial, per 1000 em, for the characters from space to ~
ARIAL = [278, 278, 355, 556, 556, 889, 667, 191, 333, 333, 389, 584, 278, 333, 278, 278,
         556, 556, 556, 556, 556, 556, 556, 556, 556, 556, 278, 278, 584, 584, 584, 556,
         1015, 667, 667, 722, 722, 667, 611, 778, 722, 278, 500, 667, 556, 833, 722, 778,
         667, 778, 722, 667, 611, 722, 667, 944, 667, 667, 611, 278, 278, 278, 469, 556,
         333, 556, 556, 500, 556, 556, 278, 556, 556, 222, 222, 500, 222, 833, 556, 556,
         556, 556, 333, 500, 278, 556, 500, 722, 500, 500, 500, 334, 260, 334, 584]


def width(s: str, size: float, bold: bool = False, mono: bool = False) -> float:
    """The width of a text in px, as Arial or a monospaced font draws it, roughly."""
    if mono:
        return len(s) * 0.6 * size
    em = sum(ARIAL[ord(c) - 32] if 32 <= ord(c) <= 126 else 556 for c in s) / 1000
    return em * size * (1.07 if bold else 1)


class Picture:
    def __init__(self, w: int, h: int):
        self.w, self.h = w, h
        self.items = []

    def add(self, markup: str) -> None:
        self.items.append(markup)

    def rect(self, x, y, w, h, fill, stroke="none", r=10):
        self.add(f'<rect x="{x:g}" y="{y:g}" width="{w:g}" height="{h:g}" rx="{r:g}" fill="{fill}" '
                 f'stroke="{stroke}" stroke-width="1.5"/>')

    def text(self, x, y, s, size=20, bold=False, mono=False, color=None, anchor="start", room=None):
        """One line of text, with its baseline at y. room is the width it must fit in."""
        if room is not None and width(s, size, bold, mono) > room:
            raise ValueError(f"{s!r} is {width(s, size, bold, mono):.0f} px wide, in {room:g} px of room")
        style = f' font-size="{size}" fill="{color or C["ink"]}"'
        style += ' font-weight="bold"' if bold else ""
        style += f' font-family="{MONO}"' if mono else ""
        style += f' text-anchor="{anchor}"' if anchor != "start" else ""
        self.add(f'<text x="{x:g}" y="{y:g}"{style}>{escape(s)}</text>')

    def arrow(self, points, color=None, dash=None):
        color = color or C["ink"]
        d = "M" + " L".join(f"{x:g},{y:g}" for x, y in points)
        dashed = f' stroke-dasharray="{dash}"' if dash else ""
        self.add(f'<path d="{d}" fill="none" stroke="{color}" stroke-width="2.6" stroke-linejoin="round" '
                 f'stroke-linecap="round"{dashed} marker-end="url(#head-{color[1:]})"/>')

    def person(self, x, y, h, color=None, ai=False):
        """A figure h px high, with x, y the top of its head. An AI is drawn dashed."""
        if ai:
            style = f'fill="{C["ai_fill"]}" stroke="{C["ai"]}" stroke-width="2" stroke-dasharray="4 3"'
        else:
            style = f'fill="{color or C["ink"]}"'
        r, half = h * 0.2, h * 0.37
        top = y + h * 0.46
        self.add(f'<circle cx="{x:g}" cy="{y + r:.1f}" r="{r:.1f}" {style}/>'
                 f'<path d="M{x - half:.1f},{y + h:g} V{top + half:.1f} A{half:.1f},{half:.1f} 0 0 1 '
                 f'{x + half:.1f},{top + half:.1f} V{y + h:g} Z" {style}/>')

    def lock(self, x, y, s, color=None):
        """A padlock s px wide, with x, y the middle of the top of its body."""
        color = color or C["tool"]
        self.add(f'<rect x="{x - s / 2:.1f}" y="{y:.1f}" width="{s:g}" height="{s * 0.7:.1f}" '
                 f'rx="{s * 0.12:.1f}" fill="{color}"/><path d="M{x - s * 0.3:.1f},{y:.1f} V{y - s * 0.2:.1f} '
                 f'A{s * 0.3:.1f},{s * 0.3:.1f} 0 0 1 {x + s * 0.3:.1f},{y - s * 0.2:.1f} V{y:.1f}" fill="none" '
                 f'stroke="{color}" stroke-width="{s * 0.15:.1f}"/>')

    def folder(self, x, y, w=28, h=22):
        """A folder, with x, y its top left."""
        tab = w * 0.4
        self.add(f'<path d="M{x:g},{y + h:g} V{y:g} H{x + tab:g} L{x + tab + 3:g},{y + 4:g} H{x + w:g} '
                 f'V{y + h:g} Z M{x:g},{y + 7:g} H{x + w:g}" fill="{C["paper"]}" stroke="{C["tool"]}" '
                 f'stroke-width="2" stroke-linejoin="round"/>')

    def page(self, x, y, w=20, h=26):
        """A sheet with a folded corner, with x, y its top left."""
        f = w * 0.32
        self.add(f'<path d="M{x:g},{y:g} H{x + w - f:g} L{x + w:g},{y + f:g} V{y + h:g} H{x:g} Z" '
                 f'fill="{C["paper"]}" stroke="{C["tool"]}" stroke-width="2" stroke-linejoin="round"/>'
                 f'<path d="M{x + w - f:g},{y:g} V{y + f:g} H{x + w:g}" fill="none" stroke="{C["tool"]}" '
                 f'stroke-width="2" stroke-linejoin="round"/>')

    def doi(self, x, y):
        """A DOI badge, with x, y its top left."""
        self.rect(x, y, 46, 22, C["ink"], r=5)
        self.text(x + 23, y + 16, "DOI", 13, bold=True, color=C["paper"], anchor="middle")

    def svg(self, title: str) -> str:
        heads = "".join(f'<marker id="head-{c[1:]}" viewBox="0 0 12 12" refX="10" refY="6" markerWidth="12" '
                        f'markerHeight="12" markerUnits="userSpaceOnUse" orient="auto">'
                        f'<path d="M1,1 L11,6 L1,11 Z" fill="{c}"/></marker>' for c in sorted(set(C.values())))
        return "\n".join([
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{self.w}" height="{self.h}" '
            f'viewBox="0 0 {self.w} {self.h}" font-family="{FONT}" role="img">',
            f"<title>{escape(title)}</title>",
            f"<defs>{heads}</defs>",
            f'<rect width="{self.w}" height="{self.h}" fill="{C["paper"]}"/>',
            *self.items,
            "</svg>",
            "",
        ])


def overview() -> str:
    """The README: the three places, who works in each, what moves between them, and what comes back."""
    p = Picture(1360, 604)
    top, height = 120, 356
    contributor, manager, zenodo = (24, 444), (556, 360), (1024, 312)  # where each place starts, and its width

    # The repository, copied into the folders of the contributor and the data manager
    p.rect(24, 18, 1312, 60, C["z_github"], r=12)
    p.text(48, 56, "This repository", 23, bold=True)
    p.text(48 + width("This repository", 23, bold=True) + 14, 56,
           "the format, the tools and the guides, copied into each folder below", 20, color=C["muted"], room=1050)
    for x, w in (contributor, manager):
        p.arrow([(x + w / 2, 78), (x + w / 2, top - 4)], color=C["line"], dash="7 6")

    places = [  # where, title, what is done there, background, colour, who works there, what holds there
        (contributor, "The contributor's computer", "conversion into the format, and data curation",
         C["z_contrib"], C["contributor"],
         [(C["contributor"], "Answers, and has the last word"), (None, "An AI asks, and writes the script"),
          (None, "A fresh AI or a colleague reviews")], "The raw files stay here."),
        (manager, "The data manager's folder", "merging the contributions", C["z_manager"], C["manager"],
         [(C["manager"], "Decides every change"), (None, "An AI proposes the merge")], "Overlaps are handled."),
    ]
    for (x, w), title, about, fill, colour, people, rule in places:
        p.rect(x, top, w, height, fill, r=16)
        p.text(x + 22, top + 42, title, 25, bold=True, room=w - 44)
        p.text(x + 22, top + 70, about, 19, color=C["muted"], room=w - 44)
        for i, (person, what) in enumerate(people):
            y = top + 94 + 62 * i
            p.person(x + 50, y, 42, color=person, ai=person is None)
            p.text(x + 88, y + 29, what, 21, room=w - 88 - 20)
        indent = 22
        if (x, w) == contributor:
            p.lock(x + 34, top + height - 44, 18, color=colour)
            indent = 56
        p.text(x + indent, top + height - 26, rule, 21, bold=True, color=colour, room=w - indent - 22)

    # Zenodo, with a record for the public dataset and one for each project, and the people who use them
    x, w = zenodo
    card = w - 54
    p.rect(x, top, w, height, C["z_zenodo"], r=16)
    p.text(x + 22, top + 42, "Zenodo", 25, bold=True, room=w - 44)
    p.text(x + 22, top + 70, "sharing, and long-term storage", 19, color=C["muted"], room=w - 44)
    for y, name, access, behind in ((top + 92, "the public dataset", "open", 0),
                                    (top + 190, "a dataset per project", "restricted", 2)):
        for back in range(behind, 0, -1):
            p.rect(x + 20 + 7 * back, y - 7 * back, card, 74, C["paper"], C["box_stroke"])
        p.rect(x + 20, y, card, 74, C["paper"], C["box_stroke"])
        p.text(x + 34, y + 29, name, 20, bold=True, room=card - 28)
        p.doi(x + 34, y + 40)
        p.text(x + 92, y + 57, access, 18, color=C["muted"], room=card - 72)
        if access == "restricted":
            p.lock(x + w - 52, y + 42, 16)
    p.person(x + 44, top + 284, 40, color=C["user"])
    p.text(x + 78, top + 302, "Data users", 20, bold=True, room=w - 78 - 16)
    p.text(x + 78, top + 326, "download and cite it", 19, room=w - 78 - 16)

    # What moves from place to place
    middle = top + 168
    for (a, aw), (b, _), lines in ((contributor, manager, ("tables", "+ credit")),
                                   (manager, zenodo, ("tables", "+ credit", "+ README"))):
        left, right = a + aw, b
        centre = (left + right) / 2
        p.page(centre - 10, middle - 52)
        p.arrow([(left + 6, middle), (right - 8, middle)])
        for i, line in enumerate(lines):
            p.text(centre, middle + 30 + 22 * i, line, 18, bold=True, anchor="middle", room=right - left - 8)

    # The IDs that come back
    loop = top + height + 52
    start, end = zenodo[0] + zenodo[1] / 2, contributor[0] + contributor[1] / 2
    p.arrow([(start, top + height), (start, loop), (end, loop), (end, top + height + 6)], color=C["muted"],
            dash="7 6")
    p.text(680, loop + 34, "The IDs already published are reused, so that one thing has one ID across datasets.",
           20, anchor="middle", room=1200)
    return p.svg("On the contributor's computer, the data is converted into the format and curated. The contributor "
                 "answers and has the last word, an AI asks and writes the script, and a fresh AI or a colleague "
                 "reviews, while the raw files stay there. The tables and the credit go to the data manager's folder, "
                 "where the contributions are merged and their overlaps handled. The data manager decides every "
                 "change, and an AI proposes the merge. The tables, the credit and the README go to Zenodo, into the "
                 "public dataset or a project's restricted one, which Zenodo shares and stores for the long term, "
                 "and where data users download and cite them. The IDs already published are reused, so that one "
                 "thing has one ID across datasets.")


CONTRIBUTION = ("The contribution folder, nordbean_irrigation_2025, one folder per contribution, named after it. "
                "raw_data is yours, with your data and documents, read-only, and in it notes, with your answers, one "
                "file per subject. phenotheca is a copy of this repository, which nobody edits. runs is where the AI "
                "writes, one run per handover. In 2026-10-22 are conversion.py, the script from raw_data to tables, "
                "conversion-notes.md, with what was changed and what is missing, summary.md, with what the tables "
                "hold, for you to check, review.md, the review with the FAIR score, and tables, with the tables and "
                "who to credit, written by the script alone.")


def contribution() -> str:
    """docs/submit-data.md: the contribution folder when the work is done, and whose each part of it is."""
    rows = [  # depth, folder or file, name, what it is
        (0, "folder", "nordbean_irrigation_2025/", "one folder per contribution, named after it"),
        (1, "folder", "raw_data/", "your data and documents, read-only"),
        (2, "folder", "notes/", "your answers, one file per subject"),
        (1, "folder", "phenotheca/", "a copy of this repository"),
        (1, "folder", "runs/", "one run per handover"),
        (2, "folder", "2026-10-22/", ""),
        (3, "file", "conversion.py", "the script, from raw_data/ to tables/"),
        (3, "file", "conversion-notes.md", "what was changed, what is missing"),
        (3, "file", "summary.md", "what the tables hold, for you to check"),
        (3, "file", "review.md", "the review, with the FAIR score"),
        (3, "folder", "tables/", "the tables and who to credit, by the script alone"),
    ]
    bands = [  # first row, last row, background, whose it is, colour
        (1, 2, C["z_contrib"], "yours", C["contributor"]),
        (3, 3, C["z_github"], "nobody edits it", C["muted"]),
        (4, 10, C["ai_fill"], "the AI writes here", C["ai"]),
    ]
    w, row, top, about = 1040, 46, 24, 486
    p = Picture(w, top * 2 + row * len(rows))
    labels = {}
    for first, last, fill, whose, colour in bands:
        p.rect(24, top + row * first, w - 48, row * (last - first + 1), fill, r=8)
        p.text(w - 40, top + row * first + 30, whose, 20, bold=True, color=colour, anchor="end")
        labels[first] = w - 40 - width(whose, 20, bold=True)
    for i, (depth, kind, name, what) in enumerate(rows):
        y, x = top + row * i, 40 + 34 * depth
        if kind == "folder":
            p.folder(x, y + 12)
        else:
            p.page(x + 4, y + 10)
        p.text(x + 38, y + 30, name, 21, bold=True, mono=True, room=about - x - 38 - 16)
        if name == "raw_data/":
            p.lock(x + 38 + width(name, 21, mono=True) + 20, y + 20, 16)
        p.text(about, y + 30, what, 20, color=C["muted"], room=labels.get(i, w - 40) - about - 24)
    return p.svg(CONTRIBUTION)


def main() -> None:
    for name, draw in (("overview.svg", overview), ("contribution.svg", contribution)):
        (HERE / name).write_text(draw(), encoding="utf-8")
        print(f"Drew {HERE / name}")


if __name__ == "__main__":
    main()
