#!/usr/bin/env python3
"""Generate publications.html from a cached Zotero export.

Zotero's local API does not return creatorSummary, so dump your own items with:

    python3 - <<'EOF'
    import json, urllib.request
    items, start = [], 0
    while True:
        d = json.load(urllib.request.urlopen(
            f"http://127.0.0.1:23119/api/users/0/items/top?limit=100&start={start}"))
        if not d:
            break
        items += d
        start += len(d)
    mine = [x["data"] for x in items
            if any((c.get("lastName") or "") == "Liu" and (c.get("firstName") or "").startswith("Tong")
                   for c in x["data"].get("creators", []))]
    json.dump(mine, open("_tools/zotero-mine.json", "w"), ensure_ascii=False)
    EOF

Then run: python3 _tools/build_pubs.py
"""

import html
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SELF = ("Liu", "Tong")

# DOIs of records where Tong Liu is the corresponding author (confirmed by CV).
CORRESPONDING = {
    "10.1016/j.susmat.2025.e01460",
    "10.1016/j.marpolbul.2025.118205",
    "10.1016/j.watres.2026.126137",
}

# Duplicate preprints of already published articles, and other noise.
SKIP_DOIS = {
    "10.2139/ssrn.4379128",   # -> Chem. Eng. J. 2023
    "10.2139/ssrn.3967291",   # -> J. Water Process Eng. 2022
    "10.2139/ssrn.4074368",   # -> Appl. Surf. Sci. 2025
    "10.1101/2020.02.17.952168",
    "10.5281/zenodo.5112147",  # software release
}

# Extra records not in the Zotero library (manual entries).
EXTRA = [
    dict(date="2025", publicationTitle="Earth Science Frontiers", title="生物可利用性煤源有机质：机制、影响因素与应用前景",
         creators=[dict(lastName="刘", firstName="通")], DOI=None,
         volume=None, pages=None, extra_authors="孟令子, 葛潇, 刘菲菲, 丁竑瑞, 鲁安怀",
         note="in Chinese"),
]

JOURNAL_ABBREV = {
    "Nature Communications": "Nat. Commun.",
    "Environmental Science & Technology": "Environ. Sci. Technol.",
    "Water Research": "Water Res.",
    "Journal of Hazardous Materials": "J. Hazard. Mater.",
    "Chemical Engineering Journal": "Chem. Eng. J.",
    "Applied Surface Science": "Appl. Surf. Sci.",
    "Electrochimica Acta": "Electrochim. Acta",
    "Science of The Total Environment": "Sci. Total Environ.",
    "Science of the Total Environment": "Sci. Total Environ.",
    "Environmental Research": "Environ. Res.",
    "Bioresource Technology": "Bioresour. Technol.",
    "Journal of Cleaner Production": "J. Clean. Prod.",
    "Journal of Cleaner Production": "J. Clean. Prod.",
    "Chemosphere": "Chemosphere",
    "Journal of Environmental Management": "J. Environ. Manage.",
    "Journal of Environmental Sciences": "J. Environ. Sci.",
    "Communications Earth & Environment": "Commun. Earth Environ.",
    "Marine Pollution Bulletin": "Mar. Pollut. Bull.",
    "Sustainable Materials and Technologies": "Sustain. Mater. Technol.",
    "Materials Letters": "Mater. Lett.",
    "Geomicrobiology Journal": "Geomicrobiol. J.",
    "Water, Air, & Soil Pollution": "Water Air Soil Pollut.",
    "Catalysts": "Catalysts",
    "Water Science and Engineering": "Water Sci. Eng.",
    "Separation and Purification Technology": "Sep. Purif. Technol.",
    "RSC Advances": "RSC Adv.",
    "PLOS ONE": "PLoS ONE",
    "Environmental Engineering Science": "Environ. Eng. Sci.",
    "Journal of Water Process Engineering": "J. Water Process Eng.",
    "Journal of Chemical Technology and Biotechnology": "J. Chem. Technol. Biotechnol.",
    "Journal of Chemical Technology & Biotechnology": "J. Chem. Technol. Biotechnol.",
    "Nitrogen Cycling": "Nitrogen Cycling",
    "Earth Science Frontiers": "Earth Sci. Front.",
}


def initials(first):
    parts = re.split(r"[\s.\-]+", first.strip())
    return " ".join(p[0].upper() + "." for p in parts if p)


def author_list(creators):
    out = []
    for c in creators:
        if c.get("creatorType") not in (None, "author"):
            continue
        last = (c.get("lastName") or "").strip()
        first = (c.get("firstName") or "").strip()
        if not last and c.get("name"):
            out.append(c["name"])
        elif re.search(r"[\u4e00-\u9fff]", last):
            out.append(last + first)          # CJK: keep as written
        else:
            out.append(f"{last}, {initials(first)}" if first else last)
    return out


def clean(text):
    text = re.sub(r"<[^>]+>", "", text or "")
    return html.unescape(text).strip()


def fmt_journal(name):
    name = clean(name)
    return JOURNAL_ABBREV.get(name, name)


def is_self(creator):
    last = creator.get("lastName") or ""
    first = creator.get("firstName") or ""
    if last == "刘":
        return first.startswith("通")
    # exact given name only: "Liu, Tongxu" and "Liu, Tongyi" are different people
    return last == SELF[0] and first.strip() in ("Tong", "T")


def role_of(item):
    authors = [c for c in item.get("creators", []) if c.get("creatorType") in (None, "author")]
    if not authors:
        return "co"
    if is_self(authors[0]):
        return "first"
    if item.get("DOI") in CORRESPONDING or is_self(authors[-1]):
        return "corr" if item.get("DOI") in CORRESPONDING else "co"
    return "co"


def entry(item):
    authors = author_list(item.get("creators", []))
    if item.get("extra_authors"):
        authors = authors + item["extra_authors"].split(", ")
    marked = []
    for a in authors:
        if a.startswith("刘通") or a.startswith("Liu, T."):
            marked.append(f'<span class="me">{html.escape(a)}</span>')
        else:
            marked.append(html.escape(a))
    role = role_of(item)
    badge = {"first": '<span class="role">first</span>',
             "corr": '<span class="role">corresp.</span>'}.get(role, "")
    year = (item.get("date") or "")[:4]
    journal = fmt_journal(item.get("publicationTitle", ""))
    vol = item.get("volume")
    pages = clean(item.get("pages", ""))
    tail = ""
    if vol:
        tail = f" <strong>{html.escape(str(vol))}</strong>"
        if pages:
            tail += f", {html.escape(pages)}"
    elif pages:
        tail = f" {html.escape(pages)}"
    doi = item.get("DOI")
    doi_html = ""
    if doi:
        doi_html = f' <a href="https://doi.org/{html.escape(doi)}">doi</a>'
    title = html.escape(clean(item.get("title"))).replace("&lt;i&gt;", "").replace("&lt;/i&gt;", "")
    zh = " (in Chinese)" if item.get("note") == "in Chinese" else ""
    auth = ", ".join(marked).rstrip(".")
    ref = f'<span class="jr">{html.escape(journal)}</span>{tail}'
    visible_tail = (tail or journal).strip()
    if not visible_tail.endswith("."):
        ref += "."
    return (f'<li><span class="yr">{html.escape(year)}</span>'
            f'{auth}. {title}. {ref}{zh}{doi_html}{(" " + badge) if badge else ""}</li>')


PAGE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Publications — Tong Liu</title>
<meta name="description" content="Publications by Tong Liu on pyrite oxidation, mineral photocatalysis, iron cycling, and mineral-interface reactivity.">
<link rel="stylesheet" href="assets/style.css">
</head>
<body>

<header class="site">
  <div class="wrap">
    <a class="site-name" href="index.html">Tong Liu <span>刘通</span></a>
    <nav class="site">
      <a href="index.html">About</a>
      <a href="research.html">Research</a>
      <a class="here" href="publications.html">Publications</a>
      <a href="cv.html">CV</a>
      <a href="notes/index.html">Notes</a>
    </nav>
  </div>
</header>

<main class="wrap">

  <h1>Publications</h1>

  <p class="note">
    {n_lead} papers as first or corresponding author, {n_co} as co-author. Regenerated from my Zotero
    library; also indexed on <a href="https://orcid.org/0000-0001-6829-0727">ORCID</a>.
  </p>

  <h2>First and corresponding author</h2>

  <ol class="pubs">
{lead}
  </ol>

  <h2>Co-authored</h2>

  <ol class="pubs">
{rest}
  </ol>

  <p class="note">
    Conference presentations and invited talks are listed on the <a href="cv.html">CV</a> page.
  </p>

</main>

<footer class="site">
  <div class="wrap">
    <span>© 2026 Tong Liu</span>
    <span>Last updated October 2026</span>
  </div>
</footer>

</body>
</html>
"""


def main():
    data = json.loads((ROOT / "_tools/zotero-mine.json").read_text())
    items = [x for x in data
             if any(is_self(c) for c in x.get("creators", []))
             and x.get("itemType") == "journalArticle"
             and x.get("publicationTitle")
             and x.get("DOI") not in SKIP_DOIS]
    items += EXTRA
    items.sort(key=lambda x: (x.get("date") or "", x.get("publicationTitle") or ""), reverse=True)

    first = [i for i in items if role_of(i) == "first"]
    corr = [i for i in items if role_of(i) == "corr"]
    co = [i for i in items if role_of(i) == "co"]

    print("first:", len(first), "corr:", len(corr), "co:", len(co), "total:", len(items))
    for label, group in (("FIRST", first), ("CORR", corr)):
        print(f"--- {label}")
        for i in group:
            print("  ", (i.get('date') or '')[:4], clean(i.get('publicationTitle')), "|", clean(i.get('title'))[:60])

    lead = "\n".join(entry(i) for i in first + corr)
    rest = "\n".join(entry(i) for i in co)

    page = PAGE.format(
        lead=lead,
        rest=rest,
        n_lead=len(first) + len(corr),
        n_co=len(co),
    )
    (ROOT / "publications.html").write_text(page)
    print(f"wrote publications.html ({len(first)+len(corr)} lead, {len(co)} co-authored)")


if __name__ == "__main__":
    main()
